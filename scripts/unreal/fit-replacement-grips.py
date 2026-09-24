"""Character-specific supplied two-handed fitting, preserving segment lengths."""
import json
import math
from pathlib import Path
import unreal
import os
if os.environ.get('WAR_ANIMATION_PROFILE','civic_battle_prelate_m')!='civic_battle_prelate_m':
    raise SystemExit(0)
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/unreal/animation-replacement"
all_sets = json.loads((OUT / "retarget.json").read_text())
entry = all_sets["profiles"]["civic_battle_prelate_m"]
receipt = dict(targetMesh=entry["mesh"], clips=entry["clips"])
weapon = json.loads((ROOT / "scripts/unreal/animation-recipes/corrections/prelate-grip.json").read_text())
target = unreal.load_asset(receipt["targetMesh"])
import sys
sys.path.insert(0,str(Path(__file__).parent))
from native_animation_settings import compression_settings
compression=compression_settings()
equipment=json.loads((OUT/'bodies.json').read_text())['profiles']['civic_battle_prelate_m']['weapon']['mesh']
description=unreal.load_asset(equipment).get_static_mesh_description(0)
hammer_vertices=[description.get_vertex_position(unreal.VertexID(i)) for i in range(description.get_vertex_count())]
def inverse(q):
    return unreal.Quat(-q.x, -q.y, -q.z, q.w)


def unit(v):
    return v / max(v.length(), 1e-9)


def between(a, b):
    a, b = unit(a), unit(b)
    cross = a.cross(b)
    dot = max(-1., min(1., a.dot(b)))
    if dot < -.999999:
        cross = unit(a.cross(unreal.Vector(1, 0, 0) if abs(a.x) < .9 else unreal.Vector(0, 1, 0)))
        return unreal.Quat(cross.x, cross.y, cross.z, 0)
    q = unreal.Quat(cross.x, cross.y, cross.z, 1 + dot)
    q.normalize()
    return q


def world_point(xyz):
    return unreal.Vector(xyz[0] * 100, -xyz[1] * 100, xyz[2] * 100)


report = {}
for key, clip in receipt["clips"].items():
    if not key.startswith("two.") or key == "two.invocation": continue
    animation = unreal.load_asset(clip["animation"])
    if unreal.EditorAssetLibrary.get_metadata_tag(animation, "WarPrelateGrip") == "v1":
        raise RuntimeError("Re-run the retarget importer before fitting grips again")
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property("optional_skeletal_mesh", target)
    rate = 30
    count = round(clip["duration"] * rate) + 1
    poses = [unreal.AnimPoseExtensions.get_anim_pose_at_time(animation, min(i / rate, clip["duration"]), options)
             for i in range(count)]
    ref_r = unreal.AnimPoseExtensions.get_ref_bone_pose(poses[0], "hand_R", unreal.AnimPoseSpaces.WORLD)
    ref_l = unreal.AnimPoseExtensions.get_ref_bone_pose(poses[0], "hand_L", unreal.AnimPoseSpaces.WORLD)
    primary = ref_r.inverse_transform_location(world_point(weapon["gripsWorld"]["primary_grip_local"])) * 100
    head = ref_r.inverse_transform_location(world_point(weapon["gripsWorld"]["head_center_local"])) * 100
    palm = ref_l.inverse_transform_location(world_point(weapon["leftPalmWorld"])) * 100
    shaft = unit(head - primary)
    grip_vertices=[ref_r.inverse_transform_location(v)*100 for v in hammer_vertices]
    tracks = {name: [] for name in ("hand_R", "upper_arm_L", "forearm_L", "hand_L", "hips")}
    maximum_correction = 0.
    maximum_reach_error = 0.
    for i, pose in enumerate(poses):
        def global_bone(name):
            return unreal.AnimPoseExtensions.get_bone_pose(pose, name, unreal.AnimPoseSpaces.WORLD)
        def local_bone(name):
            return unreal.AnimPoseExtensions.get_bone_pose(pose, name, unreal.AnimPoseSpaces.LOCAL)
        right, left = global_bone("hand_R"), global_bone("hand_L")
        # Preserve the supplied grip direction between the hands. Correct the
        # fixed authored hammer axis at the dominant wrist, then fit the support
        # arm with its original elbow plane and unchanged bone lengths.
        r_palm = right.translation + right.rotation.rotate_vector(primary)
        l_palm = left.translation + left.rotation.rotate_vector(palm)
        rotation = between(right.rotation.rotate_vector(shaft), r_palm - l_palm) * right.rotation
        if key=='two.slash':
            # Reorient the longer hammer's follow-through before solving the
            # support arm. Keep every vertex clear without shortening limbs.
            def minimum_height(q):
                vertical=inverse(q).rotate_vector(unreal.Vector(0,0,1))
                return right.translation.z+min(v.dot(vertical) for v in grip_vertices)
            if minimum_height(rotation)<3:
                current_axis=rotation.rotate_vector(shaft)
                horizontal=unit(unreal.Vector(current_axis.x,current_axis.y,0))
                if horizontal.length()<.5: horizontal=unreal.Vector(0,1,0)
                difference=between(current_axis,horizontal)
                level=difference*rotation
                if minimum_height(level)<3: raise RuntimeError('No ground-clear hammer follow-through')
                low,high=0.,1.
                def candidate(alpha):
                    q=unreal.Quat(difference.x*alpha,difference.y*alpha,difference.z*alpha,1-alpha+difference.w*alpha)
                    q.normalize()
                    return q*rotation
                for _ in range(14):
                    middle=(low+high)/2
                    if minimum_height(candidate(middle))<3: low=middle
                    else: high=middle
                rotation=candidate(high)
        r_palm = right.translation + rotation.rotate_vector(primary)
        axis = rotation.rotate_vector(shaft)
        spacing = max(8., min(40., (r_palm - l_palm).dot(axis)))
        shoulder, elbow = global_bone("upper_arm_L"), global_bone("forearm_L")
        start = shoulder.translation
        length_a = (elbow.translation - start).length()
        length_b = (left.translation - elbow.translation).length()
        # Slide the support grip only along the shaft when proportions demand it.
        # Intersect that line with the arm's reachable sphere; never stretch bones.
        base = r_palm - left.rotation.rotate_vector(palm) - start
        axial = base.dot(axis)
        radius = length_a + length_b - .1
        discriminant = radius * radius - (base.dot(base) - axial * axial)
        if discriminant >= 0:
            lower = max(4., axial - math.sqrt(discriminant))
            upper = min(60., axial + math.sqrt(discriminant))
            if lower <= upper:
                spacing = max(lower, min(upper, spacing))
        contact = r_palm - axis * spacing
        left_rotation = left.rotation
        wrist = contact - left_rotation.rotate_vector(palm)
        # A source wrist bent across the palm can make an otherwise reachable
        # contact miss on different proportions. Straighten only as much as
        # needed toward the forearm; keep the supplied rotation when reachable.
        palm_vector = left_rotation.rotate_vector(palm)
        outward_palm = unit(contact - start) * palm_vector.length()
        for step in range(1, 21):
            if (wrist - start).length() <= radius:
                break
            direction_palm = palm_vector * (1 - step / 20) + outward_palm * (step / 20)
            left_rotation = between(palm_vector, direction_palm) * left.rotation
            wrist = contact - left_rotation.rotate_vector(palm)
        delta = wrist - start
        reach = max(abs(length_a - length_b) + .1, min(length_a + length_b - .1, delta.length()))
        maximum_reach_error = max(maximum_reach_error, abs(reach - delta.length()))
        direction = unit(delta)
        hint = elbow.translation - start
        pole = unit(hint - direction * hint.dot(direction))
        along = (length_a * length_a - length_b * length_b + reach * reach) / (2 * reach)
        new_elbow = start + direction * along + pole * math.sqrt(max(0., length_a * length_a - along * along))
        new_wrist = start + direction * reach
        upper_rotation = between(elbow.translation - start, new_elbow - start) * shoulder.rotation
        fore_rotation = between(left.translation - elbow.translation, new_wrist - new_elbow) * elbow.rotation
        rotations = {
            "hand_R": inverse(global_bone("forearm_R").rotation) * rotation,
            "upper_arm_L": inverse(global_bone("shoulder_L").rotation) * upper_rotation,
            "forearm_L": inverse(upper_rotation) * fore_rotation,
            "hand_L": inverse(fore_rotation) * left_rotation,
        }
        maximum_correction = max(maximum_correction, (new_wrist - left.translation).length())
        # The supplied death deliberately releases the support hand. Preserve
        # that release rather than forcing an unreachable two-handed corpse pose.
        if key=='two.death':
            rotations={name:local_bone(name).rotation for name in rotations}
            maximum_reach_error=0.; maximum_correction=0.
        for name, q in rotations.items():
            transform = local_bone(name)
            transform.rotation = q
            tracks[name].append(transform)
        # Root travel was already separated by the shared retarget importer.
        tracks["hips"].append(local_bone("hips"))
    data = animation.controller
    data.open_bracket("Fit support hand to the equipped hammer", False)
    for name, values in tracks.items():
        if not data.set_bone_track_keys(name, [v.translation for v in values], [v.rotation for v in values],
                                       [v.scale3d for v in values], False):
            raise RuntimeError("Could not write fitted track " + name)
    data.close_bracket(False)
    animation.set_editor_property("bone_compression_settings", compression)
    animation.set_editor_property("allow_frame_stripping", False)
    unreal.WarImportLibrary.prepare_compressed_animation(animation)
    unreal.EditorAssetLibrary.set_metadata_tag(animation, "WarPrelateGrip", "v1")
    if not unreal.EditorAssetLibrary.save_loaded_asset(animation, False):
        raise RuntimeError("Could not save fitted animation " + key)
    report[key] = dict(maximumOffhandAdjustmentCm=maximum_correction, maximumUnreachableCm=maximum_reach_error)
(OUT / "grip-fit.json").write_text(json.dumps(report, indent=2))
