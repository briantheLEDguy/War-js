"""Measured grip and boot-support corrections for the authored Battle Prelate.

This operates on an imported humanoid_game_v2 rig. It never edits rest matrices,
mesh data, bone hierarchy, or leg rotations. Hips translation fits boot support.
Diagnostics may be run
in a disposable Blender process; the command-line entry point does not save a blend.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
CLIPS = ("idle", "walk", "run", "combat_idle", "attack_melee", "attack_ranged", "cast", "death", "jump")
VERSION = "authored_hammer_grip_v4_book_clearance"
FINGERS = ("index", "middle", "ring", "pinky", "thumb")
TWO_HANDED = {"combat_idle", "attack_melee"}
FREE_HAND_CLEARANCE = {"idle","walk","run"}
_REPORT_CACHE = {}
_BOOT_SKIN_CACHE = {}

# Artist-specified socket and shaft poses in the canonical upright coordinate
# frame. The imported chest motion carries these poses through the existing turn.
MELEE_POSES = (
    (0.000, (-.120, -.380, 1.390), (-.700, .000, .714)),
    (0.250, (-.110, -.370, 1.520), (-.740, .520, .426)),
    (0.417, (-.080, -.400, 1.580), (-.700, .550, .455)),
    (0.625, (.060, -.410, 1.260), (-.820, -.530, -.220)),
    (0.750, (.090, -.370, 1.200), (-.800, -.520, -.300)),
    (1.000, (-.120, -.380, 1.390), (-.700, .000, .714)),
)


def _curves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def _set_action(rig, action, frame):
    rig.animation_data_create()
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(int(frame), subframe=float(frame) % 1)
    bpy.context.view_layer.update()


def _clear_pose(rig):
    rig.animation_data.action=None
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def _xyz(value):
    return [round(float(n), 6) for n in value]


def _distance_axis(point, origin, axis):
    offset = point - origin
    return (offset - axis * offset.dot(axis)).length


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _curve_digest(action, excluded_bones):
    excluded_paths = {f'pose.bones["{name}"].rotation_quaternion' for name in excluded_bones}
    values = []
    for curve in _curves(action):
        if curve.data_path not in excluded_paths:
            values.append((curve.data_path, curve.array_index,
                           [(list(p.co), list(p.handle_left), list(p.handle_right), p.interpolation) for p in curve.keyframe_points]))
    return _digest(sorted(values))


def _rest_digest(rig):
    return _digest({b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones})


def _remove_rotations(action, bone_names):
    paths = {f'pose.bones["{name}"].rotation_quaternion' for name in bone_names}
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in list(bag.fcurves):
                    if curve.data_path in paths:
                        bag.fcurves.remove(curve)


def _matrix_at(origin, rotation):
    return Matrix.LocRotScale(origin, rotation, Vector((1,1,1)))


def _comfortable_socket(rig, side, position, axis, base_rotation, socket_in_hand, elbow_hint, previous_roll):
    """Choose forearm-aligned palm roll about the held shaft, without moving it."""
    upper = rig.pose.bones[f"upper_arm_{side}"]
    fore = rig.pose.bones[f"forearm_{side}"]
    start = upper.head.copy()
    a,b = upper.length,fore.length
    def candidate(degrees):
        matrix = _matrix_at(position,Quaternion(axis,math.radians(degrees)) @ base_rotation)
        hand = matrix @ socket_in_hand.inverted()
        delta = hand.translation-start
        requested = delta.length
        distance = min(max(requested,abs(a-b)+.002),a+b-.003)
        toward=delta.normalized()
        hint=elbow_hint-start
        outward=(hint-toward*hint.dot(toward)).normalized()
        along=(a*a-b*b+distance*distance)/(2*distance)
        elbow=start+toward*along+outward*math.sqrt(max(0,a*a-along*along))
        fore_direction=(start+toward*distance-elbow).normalized()
        hand_direction=hand.to_3x3() @ Vector((0,1,0))
        bend=fore_direction.angle(hand_direction)
        continuity=0 if previous_roll is None else math.radians(degrees-previous_roll)
        score=bend*bend+300*max(0,requested-(a+b-.003))+.02*continuity*continuity
        return score,matrix,hand,degrees
    center=0 if previous_roll is None else previous_roll
    best=min((candidate(center+offset) for offset in range(-180,181,10)),key=lambda item:item[0])
    best=min((candidate(best[3]+offset) for offset in range(-9,10)),key=lambda item:item[0])
    return best[1],best[2],best[3]


def _solve_arm(rig, side, desired_hand, elbow_hint):
    """Solve two actual bone lengths; preserve joint translation and skeleton."""
    upper = rig.pose.bones[f"upper_arm_{side}"]
    fore = rig.pose.bones[f"forearm_{side}"]
    hand = rig.pose.bones[f"hand_{side}"]
    start = upper.head.copy()
    requested_wrist = desired_hand.translation
    delta = requested_wrist-start
    length_a, length_b = upper.length, fore.length
    requested_length = delta.length
    distance = min(max(requested_length, abs(length_a-length_b)+.002), length_a+length_b-.003)
    axis = delta.normalized()
    hint = elbow_hint-start
    outward = (hint-axis*hint.dot(axis)).normalized()
    along = (length_a*length_a-length_b*length_b+distance*distance)/(2*distance)
    elbow = start+axis*along+outward*math.sqrt(max(0, length_a*length_a-along*along))
    wrist = start+axis*distance
    rotation = (upper.tail-upper.head).rotation_difference(elbow-start) @ upper.matrix.to_quaternion()
    upper.matrix = _matrix_at(start, rotation)
    bpy.context.view_layer.update()
    rotation = (fore.tail-fore.head).rotation_difference(wrist-fore.head) @ fore.matrix.to_quaternion()
    fore.matrix = _matrix_at(fore.head.copy(), rotation)
    bpy.context.view_layer.update()
    hand.matrix = _matrix_at(hand.head.copy(), desired_hand.to_quaternion())
    bpy.context.view_layer.update()
    return {"requested_wrist_reach_m":requested_length,
            "available_reach_m":length_a+length_b,
            "wrist_error_m":(hand.head-requested_wrist).length,
            "wrist_bend_degrees":math.degrees((fore.tail-fore.head).angle(hand.tail-hand.head))}


def _target_pose(name, fraction):
    if name == "attack_melee":
        for left, right in zip(MELEE_POSES, MELEE_POSES[1:]):
            if left[0] <= fraction <= right[0]:
                t = (fraction-left[0])/(right[0]-left[0])
                # Smooth acceleration between authored anticipation, impact, recovery.
                t = t*t*(3-2*t)
                return Vector(left[1]).lerp(Vector(right[1]),t), Vector(left[2]).lerp(Vector(right[2]),t).normalized()
    if name == "combat_idle":
        return Vector((-.120,-.380,1.390)), Vector((-.700,0,.714)).normalized()
    if name in {"cast", "attack_ranged"}:
        return Vector((-.410,-.270,1.220)), Vector((-.150,-.100,.984)).normalized()
    if name == "jump":
        return Vector((-.400,-.275,1.255)), Vector((-.100,-.080,.992)).normalized()
    return Vector((-.420,-.270,1.190)), Vector((0,0,1))


def _frame_times(name, first, last):
    step=.5 if name=="attack_melee" else 1.0
    return [first+index*step for index in range(round((last-first)/step)+1)]


def _arm_sides(name):
    return ("R","L") if name in TWO_HANDED | FREE_HAND_CLEARANCE else () if name=="death" else ("R",)


def _close_hand(rig, side, primary, shaft_axis, shaft_radius):
    """Aim phalanges around the measured shaft, retaining actual joint lengths.

    These targets are grip guides, not collision approval. Finger end-bone tails
    are measured in the report and the resulting surfaces require visual review.
    """
    report = {}
    for finger in FINGERS:
        chain = [rig.pose.bones[f"{finger}_{number:02}_{side}"] for number in (1,2,3)]
        base = chain[0].head.copy()
        axial = (base-primary).dot(shaft_axis)
        center = primary+shaft_axis*axial
        radial = base-center
        if radial.length < .002:
            radial = rig.pose.bones[f"hand_{side}"].matrix.to_3x3() @ Vector((0,0,1))
        radial.normalize()
        # Fingertips close on the opposite side of the rod from their knuckles.
        # The thumb opposes the four fingers rather than following their fan.
        tangent = shaft_axis.cross(radial).normalized()
        direction = 1 if side == "R" else -1
        angle = math.radians(125 if finger not in {"thumb","pinky"} else 80) * direction
        aim_radial = radial*math.cos(angle)+tangent*math.sin(angle)
        target = center+aim_radial*(shaft_radius+.007)
        for _ in range(18):
            for bone in reversed(chain):
                endpoint = chain[-1].tail.copy()
                pivot = bone.head.copy()
                current = endpoint-pivot
                desired = target-pivot
                if current.length < 1e-6 or desired.length < 1e-6:
                    continue
                turn = current.rotation_difference(desired)
                # A partial CCD step avoids abrupt proximal flips at a near target.
                turn = Quaternion().slerp(turn,.60)
                bone.matrix = _matrix_at(pivot,turn @ bone.matrix.to_quaternion())
                bpy.context.view_layer.update()
            if (chain[-1].tail-target).length < .001:
                break
        report[finger] = {"target_error_m":(chain[-1].tail-target).length,
                          "axis_distance_m":_distance_axis(chain[-1].tail,primary,shaft_axis)}
    return report


def _boot_minimum_z(boots):
    """Evaluate the exact linear skinning equation for existing boot vertices."""
    key=boots.as_pointer()
    if key not in _BOOT_SKIN_CACHE:
        modifiers=[modifier for modifier in boots.modifiers if modifier.show_viewport]
        if len(modifiers)!=1 or modifiers[0].type!="ARMATURE" or modifiers[0].use_deform_preserve_volume:
            return _boot_minimum_z_blender(boots)
        rig=modifiers[0].object
        coordinates=np.empty(len(boots.data.vertices)*3,dtype=np.float64)
        boots.data.vertices.foreach_get("co",coordinates)
        coordinates=coordinates.reshape((-1,3))
        groups={group.index:group.name for group in boots.vertex_groups}
        entries={}
        for vertex in boots.data.vertices:
            for group in vertex.groups:
                if group.weight>0:
                    entries.setdefault(groups[group.group],[]).append((vertex.index,group.weight))
        entries={name:(np.array([row[0] for row in rows],dtype=np.int32),np.array([row[1] for row in rows])) for name,rows in entries.items()}
        _BOOT_SKIN_CACHE[key]=(rig,coordinates,entries)
        expected=_boot_minimum_z_blender(boots)
        actual=_boot_minimum_z(boots)
        if abs(expected-actual)>1e-5:
            raise ValueError(f"Boot skin equation disagrees with Blender evaluated geometry: {expected} vs {actual}")
        return actual
    rig,coordinates,entries=_BOOT_SKIN_CACHE[key]
    heights=np.zeros(len(coordinates),dtype=np.float64)
    for name,(indices,weights) in entries.items():
        matrix=rig.matrix_world @ rig.pose.bones[name].matrix @ rig.data.bones[name].matrix_local.inverted() @ rig.matrix_world.inverted() @ boots.matrix_world
        row=np.array(matrix[2],dtype=np.float64)
        heights[indices]+=weights*(coordinates[indices] @ row[:3]+row[3])
    return float(heights.min())


def _boot_minimum_z_blender(boots):
    evaluated=boots.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    try:
        return min((evaluated.matrix_world @ vertex.co).z for vertex in mesh.vertices)
    finally:
        evaluated.to_mesh_clear()


def _ground_hips(rig):
    """Fit actual boot support to Z=1 mm using hips, which Player retains.

    Root and scale tracks are muted while measuring to match Player's animation
    sanitizer. Running/jumping retain intentional positive airborne clearance;
    standing/walking/combat and the authored collapse retain a support contact.
    """
    boots=bpy.data.objects.get("battle_prelate_feet_lod0")
    if boots is None:
        raise ValueError("Actual authored LOD0 boots are required for support correction")
    hips=rig.pose.bones["hips"]
    records={}
    for name in CLIPS:
        action=bpy.data.actions[name]
        muted=[]
        for curve in _curves(action):
            if 'pose.bones["root"]' in curve.data_path or curve.data_path.endswith(".scale"):
                muted.append((curve,curve.mute))
                curve.mute=True
        first,last=action.frame_range
        key_rate=8 if name=="walk" else 4
        _set_action(rig,action,first)
        rig.pose.bones["root"].matrix_basis.identity()
        for bone in rig.pose.bones:
            bone.scale=(1,1,1)
        bpy.context.view_layer.update()
        original={}
        for step in range(round((last-first)*key_rate)+1):
            frame=first+step/key_rate
            bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
            original[frame]=(hips.location.copy(),_boot_minimum_z(boots))
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in list(bag.fcurves):
                        if curve.data_path=='pose.bones["hips"].location':
                            bag.fcurves.remove(curve)
        samples=[]
        for frame,(location,minimum) in original.items():
            bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
            offset=.001-minimum
            if name in {"run","jump"}:
                offset=max(0,offset)
            parent=hips.parent
            basis=parent.matrix @ parent.bone.matrix_local.inverted() @ hips.bone.matrix_local
            hips.location=location+basis.to_3x3().inverted() @ Vector((0,0,offset))
            hips.keyframe_insert("location",frame=frame,group="hips")
            samples.append({"frame":frame,"original_boot_minimum_z_m":minimum,"hips_vertical_offset_m":offset})
        for curve in _curves(action):
            if curve.data_path=='pose.bones["hips"].location':
                for point in curve.keyframe_points:
                    point.interpolation="LINEAR"
        validation=[]
        # Eighth-frame samples fall between the new support keys.
        for step in range(round((last-first)*key_rate*2)+1):
            frame=first+step/(key_rate*2)
            bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
            validation.append(_boot_minimum_z(boots))
        for curve,value in muted:
            curve.mute=value
        records[name]={"changed_curves":[f'pose.bones["hips"].location[{axis}]' for axis in range(3)],
            "policy":"Preserve positive airborne clearance" if name in {"run","jump"} else "Keep lowest authored boot support at 1 mm",
            "samples":samples,"validation_sample_count":len(validation),"minimum_supported_z_m":min(validation),
            "maximum_supported_z_m":max(validation),"minimum_vertical_offset_m":min(s["hips_vertical_offset_m"] for s in samples),
            "maximum_vertical_offset_m":max(s["hips_vertical_offset_m"] for s in samples)}
        if min(validation)<-.002 or (name not in {"run","jump"} and max(validation)>.002):
            raise ValueError(f"Authored boot support failed between keys: {name}: {min(validation)}, {max(validation)}")
        print("GROUND_SUPPORT_CORRECTED",name,min(validation),max(validation),flush=True)
    return {"support_mesh":boots.name,"ground_z_m":0,"target_clearance_m":.001,
            "runtime_sanitizer":"Root and scale animation tracks are ignored; hips translation remains active",
            "clips":records,"rest_matrices_changed":False}


def apply_animation_corrections(rig, weapon_obj):
    """Correct canonical actions once and return before/after evidence.

    Call after weapon calibration and before exporting body animations. The
    weapon must follow the existing right-hand socket via COPY_TRANSFORMS.
    Repeating the call returns the original report without adding keys again.
    """
    if rig.type != "ARMATURE" or any(name not in bpy.data.actions for name in CLIPS):
        raise ValueError("Expected the humanoid_game_v2 rig and all nine canonical actions")
    if rig.get("animation_correction_version") == VERSION:
        report = _REPORT_CACHE.get(rig.as_pointer()) or json.loads(rig["animation_correction_summary"])
        _clear_pose(rig)
        return dict(report, already_applied=True)
    if any(bpy.data.actions[name].get("animation_correction_version") for name in CLIPS):
        raise ValueError("Actions have prior/partial corrections; reimport fresh canonical actions")
    if not all(key in weapon_obj for key in ("primary_grip_local","secondary_grip_local","head_center_local")):
        raise ValueError("Weapon grip calibration is required before animation correction")
    if not any(c.type=="COPY_TRANSFORMS" and c.target==bpy.data.objects.get("socket_hand_R") and not c.mute for c in weapon_obj.constraints):
        raise ValueError("Weapon must follow the existing unmuted right-hand socket")
    rest_hash = _rest_digest(rig)
    before = measure_actions(rig,weapon_obj)
    _clear_pose(rig)
    rest_sockets = {side:bpy.data.objects[f"socket_hand_{side}"].matrix_world.copy() for side in ("R","L")}
    socket_in_hand = {side:rig.pose.bones[f"hand_{side}"].matrix.inverted() @ rest_sockets[side] for side in ("R","L")}
    shaft_rest = (weapon_obj.matrix_world @ Vector(weapon_obj["head_center_local"])-weapon_obj.matrix_world.translation).normalized()
    chest_rest_inverse = rig.data.bones["upper_chest"].matrix_local.inverted()
    original_arms = {}
    untouched_hashes = {}
    ranges = {name:list(bpy.data.actions[name].frame_range) for name in CLIPS}
    for name in CLIPS:
        arm_sides = _arm_sides(name)
        arm_names = [f"{part}_{side}" for side in arm_sides for part in ("upper_arm","forearm","hand")]
        finger_sides = ("R","L") if name in TWO_HANDED else ("R",)
        changed_names = arm_names+[f"{finger}_{i:02}_{side}" for side in finger_sides for finger in FINGERS for i in (1,2,3)]
        untouched_hashes[name] = _curve_digest(bpy.data.actions[name],changed_names)
        original_arms[name] = {}
        first,last = ranges[name]
        for frame in _frame_times(name,first,last):
            _set_action(rig,bpy.data.actions[name],frame)
            original_arms[name][frame] = {bone_name:rig.pose.bones[bone_name].rotation_quaternion.copy() for bone_name in arm_names}
    arm_report = {}
    for name in CLIPS:
        if name=="death":
            continue
        action = bpy.data.actions[name]
        sides = _arm_sides(name)
        names = [f"{part}_{side}" for side in sides for part in ("upper_arm","forearm","hand")]
        _remove_rotations(action,names)
        first,last = ranges[name]
        samples = []
        previous = {}
        previous_roll = {"R":None,"L":None}
        for frame in _frame_times(name,first,last):
            _set_action(rig,action,frame)
            for bone_name,rotation in original_arms[name][frame].items():
                rig.pose.bones[bone_name].rotation_quaternion = rotation
            bpy.context.view_layer.update()
            chest_delta = rig.pose.bones["upper_chest"].matrix @ chest_rest_inverse
            position,axis = _target_pose(name,(frame-first)/(last-first))
            position = chest_delta @ position
            axis = (chest_delta.to_3x3() @ axis).normalized()
            orientation_delta = shaft_rest.rotation_difference(axis)
            right_hint=chest_delta @ Vector((-.48,.01,1.17))
            right_socket,right_hand,previous_roll["R"] = _comfortable_socket(rig,"R",position,axis,
                orientation_delta @ rest_sockets["R"].to_quaternion(),socket_in_hand["R"],right_hint,previous_roll["R"])
            frame_report = {"frame":frame,"R":_solve_arm(rig,"R",right_hand,right_hint)}
            if name in TWO_HANDED:
                bpy.context.view_layer.update()
                secondary = weapon_obj.matrix_world @ Vector(weapon_obj["secondary_grip_local"])
                left_hint=chest_delta @ Vector((.46,.01,1.18))
                left_socket,left_hand,previous_roll["L"] = _comfortable_socket(rig,"L",secondary,axis,
                    (-shaft_rest).rotation_difference(axis) @ rest_sockets["L"].to_quaternion(),socket_in_hand["L"],left_hint,previous_roll["L"])
                frame_report["L"] = _solve_arm(rig,"L",left_hand,left_hint)
            elif name in FREE_HAND_CLEARANCE:
                # Keep the open resting hand in front of the suspended book.
                # The original pose drove its steel cuff through a retaining
                # strap. This authored 65 mm forward / 20 mm outward / 25 mm up offset
                # clears that fixed accessory without changing the book or rig.
                left_hand=rig.pose.bones["hand_L"].matrix.copy()
                left_hand.translation+=chest_delta.to_3x3() @ Vector((.020,-.065,.025))
                frame_report["L"] = _solve_arm(rig,"L",left_hand,chest_delta @ Vector((.46,.01,1.18)))
            for bone_name in names:
                bone = rig.pose.bones[bone_name]
                bone.rotation_mode = "QUATERNION"
                rotation = bone.rotation_quaternion.copy()
                if bone_name in previous and rotation.dot(previous[bone_name]) < 0:
                    rotation.negate()
                    bone.rotation_quaternion = rotation
                previous[bone_name] = rotation
                bone.keyframe_insert("rotation_quaternion",frame=frame,group=bone_name)
            samples.append(frame_report)
        arm_report[name] = samples
    limits={name:{side:{"reach_error_m":max(sample[side]["wrist_error_m"] for sample in samples if side in sample),
                       "wrist_bend_degrees":max(sample[side]["wrist_bend_degrees"] for sample in samples if side in sample)}
                  for side in ("R","L") if any(side in sample for sample in samples)} for name,samples in arm_report.items()}
    print("ARM_SOLVE_LIMITS",json.dumps(limits),flush=True)
    if any(record["reach_error_m"]>.002 or record["wrist_bend_degrees"]>70 for sides in limits.values() for record in sides.values()):
        raise ValueError("Arm correction failed reach/wrist diagnostic: "+json.dumps(limits))
    # The shaft-to-palm transform is constant, so a single contact solve transfers
    # to every corrected arm frame. This avoids adding unnecessary finger curves.
    _set_action(rig,bpy.data.actions["combat_idle"],0)
    primary = weapon_obj.matrix_world.translation.copy()
    axis = (weapon_obj.matrix_world @ Vector(weapon_obj["head_center_local"])-primary).normalized()
    # The binding is thicker than the leather shaft. Use actual evaluated
    # vertices near either contact, not a guessed nominal radius.
    primary_local=Vector(weapon_obj["primary_grip_local"])
    axis_local=(Vector(weapon_obj["head_center_local"])-primary_local).normalized()
    shaft_points=[v.co for v in weapon_obj.data.vertices if -.44<(v.co-primary_local).dot(axis_local)<.05]
    shaft_radius=max(_distance_axis(point,primary_local,axis_local) for point in shaft_points)
    finger_report = {side:_close_hand(rig,side,primary,axis,shaft_radius) for side in ("R","L")}
    finger_rotations = {side:{f"{finger}_{i:02}_{side}":rig.pose.bones[f"{finger}_{i:02}_{side}"].rotation_quaternion.copy()
                              for finger in FINGERS for i in (1,2,3)} for side in ("R","L")}
    for name in CLIPS:
        action = bpy.data.actions[name]
        sides = ("R","L") if name in TWO_HANDED else ("R",)
        names = [n for side in sides for n in finger_rotations[side]]
        _remove_rotations(action,names)
        for frame in ranges[name]:
            _set_action(rig,action,frame)
            for side in sides:
                for bone_name,rotation in finger_rotations[side].items():
                    bone=rig.pose.bones[bone_name]
                    bone.rotation_mode="QUATERNION"
                    bone.rotation_quaternion=rotation
                    bone.keyframe_insert("rotation_quaternion",frame=frame,group=bone_name)
        arm_sides = _arm_sides(name)
        changed = names+[f"{part}_{side}" for side in arm_sides for part in ("upper_arm","forearm","hand")]
        for curve in _curves(action):
            if curve.data_path in {f'pose.bones["{n}"].rotation_quaternion' for n in changed}:
                for point in curve.keyframe_points:
                    point.interpolation="LINEAR"
        if _curve_digest(action,changed) != untouched_hashes[name]:
            raise AssertionError(f"Unrelated animation channels changed in {name}")
        if list(action.frame_range) != ranges[name]:
            raise AssertionError(f"Clip range changed: {name}")
    ground_support=_ground_hips(rig)
    after=measure_actions(rig,weapon_obj)
    interpolated_grips={}
    for name in sorted(TWO_HANDED):
        first,last=ranges[name]
        samples=[]
        for step in range(int((last-first)*4)+1):
            frame=first+step*.25
            _set_action(rig,bpy.data.actions[name],frame)
            secondary=weapon_obj.matrix_world @ Vector(weapon_obj["secondary_grip_local"])
            left=bpy.data.objects["socket_hand_L"].matrix_world.translation
            samples.append({"frame":frame,"gap_m":(left-secondary).length})
        worst=max(samples,key=lambda sample:sample["gap_m"])
        interpolated_grips[name]={"sample_count":len(samples),"maximum_gap_m":worst["gap_m"],"worst_frame":worst["frame"]}
    if _rest_digest(rig) != rest_hash:
        raise AssertionError("Rest matrices changed")
    report={"version":VERSION,"already_applied":False,"status":"grip-corrected; visual review required",
            "two_handed_clips":sorted(TWO_HANDED),"before":before,"after":after,
            "free_hand_book_clearance_clips":sorted(FREE_HAND_CLEARANCE),
            "interpolated_two_hand_contact":interpolated_grips,
            "arm_solve_samples":arm_report,"finger_solve":finger_report,"shaft_radius_m":shaft_radius,"rest_matrices_sha256":rest_hash,
            "body_and_leg_channels_preserved":False,"leg_rotation_channels_preserved":True,
            "changed_non_arm_channels":[f'pose.bones["hips"].location[{axis}]' for axis in range(3)],
            "ground_support":ground_support,"clip_names_and_ranges_preserved":True,
            "limitations":["Off-hand contact is required only in combat idle and melee; other clips carry the hammer in the right hand.",
                           "Death retains canonical arm motion and attached weapon; ground contact is not dynamically simulated.",
                           "Socket and fingertip diagnostics are not a full surface collision or visual acceptance check."]}
    report["maximum_wrist_error_m"] = max(sample[side]["wrist_error_m"] for samples in arm_report.values() for sample in samples for side in ("R","L") if side in sample)
    report["maximum_wrist_bend_degrees"] = max(sample[side]["wrist_bend_degrees"] for samples in arm_report.values() for sample in samples for side in ("R","L") if side in sample)
    report["maximum_two_hand_gap_m"] = max(after[name]["max_secondary_error_m"] for name in TWO_HANDED)
    if report["maximum_wrist_error_m"]>.002 or report["maximum_wrist_bend_degrees"]>70:
        raise ValueError("Arm correction failed reach/wrist diagnostic; see solver report")
    if max(item["maximum_gap_m"] for item in interpolated_grips.values())>.004:
        raise ValueError("Two-hand contact drifts by more than 4 mm between baked frames")
    for name in CLIPS:
        bpy.data.actions[name]["animation_correction_version"]=VERSION
    rig["animation_correction_version"]=VERSION
    rig["animation_correction_summary"] = json.dumps({key:report[key] for key in ("version","status","rest_matrices_sha256",
        "body_and_leg_channels_preserved","changed_non_arm_channels","leg_rotation_channels_preserved","clip_names_and_ranges_preserved",
        "maximum_wrist_error_m","maximum_wrist_bend_degrees","maximum_two_hand_gap_m","limitations")})
    _REPORT_CACHE[rig.as_pointer()] = report
    _clear_pose(rig)
    return report


def measure_actions(rig, weapon):
    """Sample sockets, fingertips, and hammer clearance; sockets are not skin contact."""
    result = {}
    rig.data.pose_position = "POSE"
    for name in CLIPS:
        action = bpy.data.actions[name]
        first, last = action.frame_range
        samples = []
        for fraction in (0, .125, .25, .375, .5, .625, .75, .875, 1):
            frame = first + (last - first) * fraction
            _set_action(rig, action, frame)
            primary = weapon.matrix_world @ Vector(weapon["primary_grip_local"])
            secondary = weapon.matrix_world @ Vector(weapon["secondary_grip_local"])
            head = weapon.matrix_world @ Vector(weapon["head_center_local"])
            axis = (head-primary).normalized()
            right = bpy.data.objects["socket_hand_R"].matrix_world.translation
            left = bpy.data.objects["socket_hand_L"].matrix_world.translation
            tips = {side: {finger: round(_distance_axis(rig.matrix_world @ rig.pose.bones[f"{finger}_03_{side}"].tail, primary, axis), 6)
                           for finger in ("index", "middle", "ring", "pinky", "thumb")} for side in ("R", "L")}
            weapon_min_z=min((weapon.matrix_world @ v.co).z for v in weapon.data.vertices)
            samples.append({"frame":round(frame, 4), "primary_error_m":round((right-primary).length, 6),
                            "secondary_error_m":round((left-secondary).length, 6), "right_socket":_xyz(right),
                            "left_socket":_xyz(left), "secondary":_xyz(secondary), "head":_xyz(head),
                            "shaft_bottom_z_m":round((primary-axis*1.09).z, 6),
                            "weapon_min_z_m":round(weapon_min_z, 6),
                            "fingertip_distance_to_shaft_axis_m":tips})
        result[name] = {"frame_range":list(action.frame_range), "samples":samples,
                        "max_secondary_error_m":max(s["secondary_error_m"] for s in samples)}
    return result


def _render(rig, weapon, action_name, frame, suffix, closeup=False):
    _set_action(rig, bpy.data.actions[action_name], frame)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.background_type = "WORLD"
    scene.world.color = (.035, .035, .035)
    scene.render.resolution_x = 640
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.camera = bpy.data.objects["comparison.full_three_quarter"]
    if closeup:
        camera = scene.camera.copy()
        camera.data=scene.camera.data.copy()
        scene.collection.objects.link(camera)
        target=(bpy.data.objects["socket_hand_R"].matrix_world.translation+bpy.data.objects["socket_hand_L"].matrix_world.translation)*.5
        camera.location=target+Vector((1.6,-3,1.0))
        camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
        camera.data.ortho_scale=.75
        scene.camera=camera
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(ROOT / "review" / f"motion_{action_name}_{suffix}.png")
    bpy.ops.render.render(write_still=True)
    if closeup:
        data=camera.data
        bpy.data.objects.remove(camera,do_unlink=True)
        bpy.data.cameras.remove(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--correct", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--fresh-actions", action="store_true", help="Reload canonical clips in memory for isolated diagnostics; never saves the master")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    rig = bpy.data.objects["humanoid_game_v2"]
    weapon = bpy.data.objects["battle_prelate_weapon_lod0"]
    if args.fresh_actions:
        rig.animation_data.action=None
        for name in CLIPS:
            bpy.data.actions.remove(bpy.data.actions[name],do_unlink=True)
        frozen=ROOT/"source/humanoid_game_v2_animation_contract.blend"
        metadata=json.loads(frozen.with_suffix(".dat").read_text())
        if hashlib.sha256(frozen.read_bytes()).hexdigest()!=metadata["sha256"]:
            raise ValueError("Frozen canonical animation contract hash mismatch")
        with bpy.data.libraries.load(str(frozen),link=False) as (source,target):
            target.actions=source.actions
        for action in target.actions:
            action.use_fake_user=True
        for key in ("animation_correction_version","animation_correction_report","animation_correction_summary"):
            if key in rig:
                del rig[key]
        for bone in rig.pose.bones:
            bone.matrix_basis.identity()
        bpy.context.view_layer.update()
    result = apply_animation_corrections(rig, weapon) if args.correct else {"before":measure_actions(rig, weapon)}
    if args.correct:
        full_hash=_digest({name:_curve_digest(bpy.data.actions[name],[]) for name in CLIPS})
        second=apply_animation_corrections(rig,weapon)
        assert second["already_applied"] and full_hash==_digest({name:_curve_digest(bpy.data.actions[name],[]) for name in CLIPS})
        assert rig.animation_data.action is None and all(max(abs(b.matrix_basis[row][col]-(1 if row==col else 0)) for row in range(4) for col in range(4))<1e-6 for b in rig.pose.bones)
        result["idempotence_verified"]=True
    suffix = "after" if args.correct else "before"
    (ROOT / "review" / f"motion_report_{suffix}.json").write_text(json.dumps(result, indent=2)+"\n")
    if args.render:
        for name in CLIPS:
            start, end = bpy.data.actions[name].frame_range
            _render(rig, weapon, name, start+(end-start)*(.625 if name=="attack_melee" else .25), suffix)
        _render(rig,weapon,"combat_idle",16,suffix+"_grip_closeup",closeup=True)
        _render(rig,weapon,"attack_melee",10,suffix+"_windup")
        _render(rig,weapon,"attack_melee",15,suffix+"_grip_closeup",closeup=True)
        _render(rig,weapon,"death",48,suffix+"_end")
    print("MOTION_DIAGNOSTIC_COMPLETE", suffix)


if __name__ == "__main__":
    main()
