"""Assemble a draft equipped review from already-serialized runtime GLBs.

The verified body GLB owns the only armature and animation set. Each modular
armor GLB is imported independently, checked against that armature's rest pose,
rebound by canonical bone name, and stripped of its duplicate armature before a
combined review GLB is exported. The emitted file is then imported into a clean
scene and rendered in bind and idle poses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector


REQUIRED_CLIPS = (
    "idle",
    "walk",
    "run",
    "combat_idle",
    "attack_melee",
    "attack_ranged",
    "cast",
    "death",
    "jump",
)
EXPECTED_SLOTS = (
    "head",
    "shoulders",
    "chest",
    "hands",
    "waist",
    "legs",
    "feet",
    "back",
    "tabard",
)
RIG_NAME = "humanoid_game_v2"
# The serialized hammer's +Z shaft axis and MPFB's right-hand socket axis do
# not share a grip convention.  This local attachment rotation makes the
# shaft rise from the palm in bind pose; animation remains responsible for
# the carry angle and strike.  It changes no mesh vertices.
HAMMER_GRIP_ROTATION = Quaternion((0.9290, 0.2974, -0.2204, 0.0)).normalized()

# Equipment animation corrections are profile data, separate from generic
# MPFB locomotion.  Future class/weapon profiles can supply their own node,
# local axis, and normalized clip targets without changing the alignment
# algorithm.
EQUIPMENT_ANIMATION_PROFILES = {
    "battle_prelate_hammer": {
        "handedness": "two_handed",
        "massClass": "heavy",
        "anchorBone": "hips",
        "secondaryGripNode": "weapon_grip_socket_hand_L",
        "secondaryGripLocalFallback": (0.0, 0.0, 0.30),
        "rightPoleOffset": (-0.65, 0.45, 0.36),
        "leftPoleOffset": (-1.00, 0.50, -0.49),
        "maxPrimaryGripErrorM": 0.01,
        "maxSecondaryGripErrorM": 0.015,
        "maxDirectionErrorDegrees": 8.0,
        "clips": {
            # normalized phase, primary-grip offset from hips, strike-head axis
            "idle": [
                (0.0, (-0.18, -0.17, 0.06), (0.66, 0.00, 0.75)),
                (0.5, (-0.18, -0.17, 0.065), (0.66, 0.00, 0.75)),
                (1.0, (-0.18, -0.17, 0.06), (0.66, 0.00, 0.75)),
            ],
            "walk": [
                (0.0, (-0.18, -0.17, 0.06), (0.66, 0.00, 0.75)),
                (0.25, (-0.18, -0.17, 0.065), (0.66, 0.00, 0.75)),
                (0.5, (-0.18, -0.17, 0.06), (0.66, 0.00, 0.75)),
                (0.75, (-0.18, -0.17, 0.065), (0.66, 0.00, 0.75)),
                (1.0, (-0.18, -0.17, 0.06), (0.66, 0.00, 0.75)),
            ],
            "run": [
                (0.0, (-0.16, -0.15, 0.11), (0.58, 0.00, 0.81)),
                (0.25, (-0.16, -0.15, 0.12), (0.58, 0.00, 0.81)),
                (0.5, (-0.16, -0.15, 0.11), (0.58, 0.00, 0.81)),
                (0.75, (-0.16, -0.15, 0.12), (0.58, 0.00, 0.81)),
                (1.0, (-0.16, -0.15, 0.11), (0.58, 0.00, 0.81)),
            ],
            "combat_idle": [
                (0.0, (-0.19, -0.23, 0.12), (0.78, -0.08, 0.62)),
                (0.5, (-0.19, -0.23, 0.125), (0.78, -0.08, 0.62)),
                (1.0, (-0.19, -0.23, 0.12), (0.78, -0.08, 0.62)),
            ],
            "attack_melee": [
                (0.0, (-0.19, -0.23, 0.12), (0.78, -0.08, 0.62)),
                (7 / 30, (-0.19, -0.23, 0.12), (0.72, 0.05, 0.69)),
                (12 / 30, (-0.19, -0.23, 0.12), (0.70, -0.15, 0.70)),
                (14 / 30, (-0.19, -0.23, 0.12), (0.72, -0.30, 0.63)),
                (21 / 30, (-0.19, -0.23, 0.12), (0.78, -0.20, 0.60)),
                (1.0, (-0.19, -0.23, 0.12), (0.78, -0.08, 0.62)),
            ],
        },
    },
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-glb", required=True)
    parser.add_argument("--modules-dir", required=True)
    parser.add_argument("--hammer-glb", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--report")
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path: Path) -> list[bpy.types.Object]:
    if not path.is_file():
        raise FileNotFoundError(path)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.context.scene.objects if obj not in before]


def delete_objects(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def armature_modifier(mesh: bpy.types.Object) -> bpy.types.ArmatureModifier:
    modifiers = [modifier for modifier in mesh.modifiers if modifier.type == "ARMATURE"]
    if len(modifiers) != 1:
        raise RuntimeError(f"{mesh.name} must have exactly one armature modifier; found {len(modifiers)}")
    return modifiers[0]


def matrix_max_delta(left: Matrix, right: Matrix) -> float:
    return max(abs(left[row][column] - right[row][column]) for row in range(4) for column in range(4))


def compare_rest_rigs(source: bpy.types.Object, target: bpy.types.Object) -> dict:
    source_names = {bone.name for bone in source.data.bones}
    target_names = {bone.name for bone in target.data.bones}
    missing = sorted(target_names - source_names)
    extra = sorted(source_names - target_names)
    deltas = {
        name: matrix_max_delta(source.data.bones[name].matrix_local, target.data.bones[name].matrix_local)
        for name in sorted(source_names & target_names)
    }
    maximum = max(deltas.values(), default=0.0)
    return {
        "sourceBoneCount": len(source_names),
        "targetBoneCount": len(target_names),
        "missingBones": missing,
        "extraBones": extra,
        "maxRestMatrixDelta": maximum,
        "passed": not missing and not extra and maximum <= 1e-5,
    }


def vertex_influence_audit(mesh: bpy.types.Object, bone_names: set[str]) -> dict:
    bone_groups = {group.index for group in mesh.vertex_groups if group.name in bone_names}
    maximum = 0
    unweighted = 0
    for vertex in mesh.data.vertices:
        count = sum(
            1
            for assignment in vertex.groups
            if assignment.group in bone_groups and assignment.weight > 1e-8
        )
        maximum = max(maximum, count)
        if count == 0:
            unweighted += 1
    return {
        "vertexCount": len(mesh.data.vertices),
        "maxInfluences": maximum,
        "unweightedVertices": unweighted,
        "passed": maximum <= 4 and unweighted == 0,
    }


def rebind_module(
    module_path: Path,
    target_rig: bpy.types.Object,
) -> tuple[bpy.types.Object, dict]:
    imported = import_glb(module_path)
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    meshes = [
        obj
        for obj in imported
        if obj.type == "MESH" and str(obj.get("assetId", "")).startswith("arm.")
    ]
    if len(armatures) != 1 or len(meshes) != 1:
        raise RuntimeError(
            f"{module_path.name} must import one armor mesh and one armature; "
            f"found {len(meshes)} mesh(es), {len(armatures)} armature(s)"
        )
    duplicate_rig = armatures[0]
    mesh = meshes[0]
    rest_audit = compare_rest_rigs(duplicate_rig, target_rig)
    if not rest_audit["passed"]:
        raise RuntimeError(f"Rest rig mismatch for {module_path.name}: {rest_audit}")
    modifier = armature_modifier(mesh)
    if modifier.object != duplicate_rig:
        raise RuntimeError(f"{module_path.name} is not bound to its imported armature")
    world = mesh.matrix_world.copy()
    modifier.object = target_rig
    mesh.parent = target_rig
    mesh.matrix_parent_inverse = target_rig.matrix_world.inverted()
    mesh.matrix_world = world
    influence_audit = vertex_influence_audit(mesh, {bone.name for bone in target_rig.data.bones})
    if not influence_audit["passed"]:
        raise RuntimeError(f"Weight audit failed for {module_path.name}: {influence_audit}")
    slot = str(mesh.get("armorSlot", ""))
    if slot not in EXPECTED_SLOTS:
        raise RuntimeError(f"{module_path.name} has invalid armorSlot metadata: {slot}")
    mesh["assemblySource"] = str(module_path)
    mesh["assemblySourceSha256"] = sha256(module_path)
    mesh["assemblyReboundTo"] = RIG_NAME
    mesh["lifecycleStatus"] = "draft"
    mesh["reviewStatus"] = "pending"
    mesh["promotionEligible"] = False
    delete_objects([obj for obj in imported if obj != mesh])
    bpy.context.view_layer.update()
    if modifier.object != target_rig or mesh.parent != target_rig:
        raise RuntimeError(f"Rebind did not persist for {module_path.name}")
    return mesh, {
        "slot": slot,
        "assetId": mesh.get("assetId"),
        "source": str(module_path),
        "sourceSha256": sha256(module_path),
        "restRig": rest_audit,
        "weights": influence_audit,
    }


def attach_hammer(path: Path, socket: bpy.types.Object) -> tuple[list[bpy.types.Object], dict]:
    imported = import_glb(path)
    roots = [obj for obj in imported if obj.parent not in imported]
    root = next((obj for obj in roots if obj.name.startswith("battle_prelate_hammer_root")), None)
    if not root:
        raise RuntimeError(f"Hammer must expose battle_prelate_hammer_root: {path}")
    world_grip = next((obj for obj in imported if obj.name.startswith("weapon_grip_socket_hand_R")), None)
    if not world_grip:
        raise RuntimeError("Hammer is missing weapon_grip_socket_hand_R")
    root.parent = socket
    root.matrix_parent_inverse = Matrix.Identity(4)
    root.location = (0.0, 0.0, 0.0)
    root.rotation_mode = "QUATERNION"
    root.rotation_quaternion = HAMMER_GRIP_ROTATION
    root.scale = (1.0, 1.0, 1.0)
    secondary_grip = next(
        (obj for obj in imported if obj.name.startswith("weapon_grip_socket_hand_L")),
        None,
    )
    if secondary_grip is None:
        secondary_grip = bpy.data.objects.new("weapon_grip_socket_hand_L", None)
        bpy.context.scene.collection.objects.link(secondary_grip)
        secondary_grip.parent = root
        secondary_grip.location = (0.0, 0.0, 0.30)
        secondary_grip.rotation_euler = (0.0, 0.0, 0.0)
        secondary_grip["targetSocket"] = "socket_hand_L"
        secondary_grip["gripRole"] = "secondary"
        imported.append(secondary_grip)
    for obj in imported:
        obj["assemblySource"] = str(path)
        obj["assemblySourceSha256"] = sha256(path)
        obj["lifecycleStatus"] = "draft"
        obj["reviewStatus"] = "pending"
        obj["promotionEligible"] = False
    bpy.context.view_layer.update()
    return imported, {
        "source": str(path),
        "sourceSha256": sha256(path),
        "targetSocket": socket.name,
        "root": root.name,
        "grip": world_grip.name,
        "secondaryGrip": secondary_grip.name,
        "handedness": "two_handed",
        "massClass": "heavy",
    }


def set_normalized_action_frame(action: bpy.types.Action, normalized: float) -> float:
    start, end = action.frame_range
    value = float(start) + (float(end) - float(start)) * normalized
    whole = math.floor(value)
    bpy.context.scene.frame_set(whole, subframe=value - whole)
    bpy.context.view_layer.update()
    return value


def resolve_weapon_strike_axis(
    weapon_root: bpy.types.Object,
    weapon_objects: list[bpy.types.Object],
) -> tuple[Vector, dict]:
    """Resolve grip-to-striking-head direction without assuming a mesh axis."""
    marker = next(
        (obj for obj in weapon_objects if obj.name.startswith("weapon_strike_head")),
        None,
    )
    inverse_root = weapon_root.matrix_world.inverted()
    if marker is not None:
        local_head = inverse_root @ marker.matrix_world.translation
        axis = local_head.normalized()
        return axis, {
            "source": "weapon_strike_head_marker",
            "marker": marker.name,
            "headLocal": list(local_head),
            "axisLocal": list(axis),
        }

    local_points = []
    for mesh in (obj for obj in weapon_objects if obj.type == "MESH"):
        transform = inverse_root @ mesh.matrix_world
        local_points.extend(transform @ vertex.co for vertex in mesh.data.vertices)
    if not local_points:
        raise RuntimeError("Weapon strike-axis derivation found no mesh vertices")
    ranked = sorted(local_points, key=lambda point: point.length, reverse=True)
    cluster_size = max(8, math.ceil(len(ranked) * 0.05))
    local_head = sum(ranked[:cluster_size], Vector()) / cluster_size
    if local_head.length <= 1e-6:
        raise RuntimeError("Weapon strike-axis derivation produced a zero-length vector")
    axis = local_head.normalized()
    return axis, {
        "source": "farthest_geometry_cluster_from_grip",
        "sampledVertexCount": len(local_points),
        "clusterVertexCount": cluster_size,
        "headLocal": list(local_head),
        "axisLocal": list(axis),
    }


def interpolate_equipment_target(phase_targets: list[tuple], normalized: float) -> tuple[Vector, Vector]:
    phases = sorted(phase_targets, key=lambda row: float(row[0]))
    if normalized <= float(phases[0][0]):
        return Vector(phases[0][1]), Vector(phases[0][2]).normalized()
    if normalized >= float(phases[-1][0]):
        return Vector(phases[-1][1]), Vector(phases[-1][2]).normalized()
    right_index = next(index for index, row in enumerate(phases) if float(row[0]) >= normalized)
    left = phases[right_index - 1]
    right = phases[right_index]
    span = float(right[0]) - float(left[0])
    factor = (normalized - float(left[0])) / max(span, 1e-9)
    offset = Vector(left[1]).lerp(Vector(right[1]), factor)
    direction = Vector(left[2]).lerp(Vector(right[2]), factor).normalized()
    return offset, direction


def world_bone_point(rig: bpy.types.Object, bone_name: str, endpoint: str = "head") -> Vector:
    return rig.matrix_world @ getattr(rig.pose.bones[bone_name], endpoint)


def solve_arm_ik(
    rig: bpy.types.Object,
    side: str,
    target_world: Vector,
    pole_world: Vector,
) -> None:
    """Solve one arm visually, remove the temporary constraint, and retain FK pose data."""
    names = (f"upper_arm_{side}", f"forearm_{side}", f"hand_{side}")
    hand = rig.pose.bones[names[-1]]
    target = bpy.data.objects.new(f"runtime_grip_target_{side}", None)
    pole = bpy.data.objects.new(f"runtime_grip_pole_{side}", None)
    bpy.context.scene.collection.objects.link(target)
    bpy.context.scene.collection.objects.link(pole)
    target.location = target_world
    pole.location = pole_world
    constraint = hand.constraints.new("IK")
    constraint.name = f"runtime_two_hand_ik_{side}"
    constraint.target = target
    constraint.pole_target = pole
    constraint.chain_count = 3
    constraint.use_rotation = False
    bpy.context.view_layer.update()
    solved = {name: rig.pose.bones[name].matrix.copy() for name in names}
    hand.constraints.remove(constraint)
    bpy.data.objects.remove(target, do_unlink=True)
    bpy.data.objects.remove(pole, do_unlink=True)
    for name in names:
        rig.pose.bones[name].matrix = solved[name]
    bpy.context.view_layer.update()
    for name in names:
        bone = rig.pose.bones[name]
        location, rotation, scale = bone.matrix_basis.decompose()
        bone.rotation_mode = "QUATERNION"
        bone.location = location
        bone.rotation_quaternion = rotation.normalized()
        bone.scale = scale
    bpy.context.view_layer.update()


def align_hand_weapon_axis(
    rig: bpy.types.Object,
    hand: bpy.types.PoseBone,
    weapon_root: bpy.types.Object,
    local_axis: Vector,
    target_world: Vector,
) -> None:
    current_world = (weapon_root.matrix_world.to_3x3() @ local_axis).normalized()
    correction_world = current_world.rotation_difference(target_world.normalized())
    rig_rotation = rig.matrix_world.to_3x3().normalized()
    correction_armature = (
        rig_rotation.inverted() @ correction_world.to_matrix() @ rig_rotation
    ).to_quaternion()
    pose_matrix = hand.matrix.copy()
    head = pose_matrix.translation.copy()
    hand.matrix = (
        Matrix.Translation(head)
        @ correction_armature.to_matrix().to_4x4()
        @ Matrix.Translation(-head)
        @ pose_matrix
    )
    location, rotation, scale = hand.matrix_basis.decompose()
    hand.rotation_mode = "QUATERNION"
    hand.location = location
    hand.rotation_quaternion = rotation.normalized()
    hand.scale = scale
    bpy.context.view_layer.update()


def arm_angle_degrees(rig: bpy.types.Object, upper_name: str, lower_name: str) -> float:
    upper = (world_bone_point(rig, upper_name, "tail") - world_bone_point(rig, upper_name)).normalized()
    lower = (world_bone_point(rig, lower_name, "tail") - world_bone_point(rig, lower_name)).normalized()
    return math.degrees(upper.angle(lower))


def set_linear_arm_keys(action: bpy.types.Action, arm_bones: tuple[str, ...]) -> None:
    """Prevent quaternion overshoot between dense two-hand pose keys."""
    curves = getattr(action, "fcurves", None)
    if curves is None:
        # Blender 4.4+ stores curves in layered channel bags.
        curves = []
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    curves.extend(channelbag.fcurves)
    names = set(arm_bones)
    for curve in curves:
        if curve.group and curve.group.name in names:
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"


def align_weapon_axis_animation(
    rig: bpy.types.Object,
    weapon_root: bpy.types.Object,
    profile_name: str,
    local_axis: Vector,
) -> dict:
    """Bake a profile-driven two-hand FK pose against the serialized grip markers."""
    profile = EQUIPMENT_ANIMATION_PROFILES.get(profile_name)
    if profile is None:
        return {"profile": profile_name, "applied": False, "reason": "no_equipment_alignment_policy"}
    if rig.animation_data is None:
        raise RuntimeError("Equipment animation alignment requires armature actions")
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    secondary_grip = next(
        (obj for obj in bpy.context.scene.objects if obj.name.startswith(profile["secondaryGripNode"])),
        None,
    )
    if secondary_grip is None:
        raise RuntimeError(f"Two-hand animation requires {profile['secondaryGripNode']}")
    required_bones = {
        profile["anchorBone"],
        "shoulder_L", "upper_arm_L", "forearm_L", "hand_L",
        "shoulder_R", "upper_arm_R", "forearm_R", "hand_R",
    }
    if not required_bones.issubset(rig.pose.bones.keys()):
        raise RuntimeError(f"Two-hand animation bones are incomplete: {sorted(required_bones - set(rig.pose.bones.keys()))}")
    local_axis = local_axis.normalized()
    rig_rotation = rig.matrix_world.to_3x3().normalized()
    arm_bones = (
        "upper_arm_L", "forearm_L", "hand_L",
        "upper_arm_R", "forearm_R", "hand_R",
    )
    audit_clips = []

    for clip_name, phase_targets in profile["clips"].items():
        action = bpy.data.actions.get(clip_name)
        if action is None:
            raise RuntimeError(f"Equipment alignment clip is missing: {clip_name}")
        rig.animation_data.action = action
        start, end = action.frame_range
        frame_count = max(1, round(float(end) - float(start)))
        sampled = []
        for index in range(frame_count + 1):
            normalized = index / frame_count
            frame = float(start) + index
            bpy.context.scene.frame_set(math.floor(frame), subframe=frame - math.floor(frame))
            bpy.context.view_layer.update()
            offset, target_direction = interpolate_equipment_target(phase_targets, normalized)
            target_world = (rig_rotation @ target_direction).normalized()
            anchor = world_bone_point(rig, profile["anchorBone"])
            desired_primary = anchor + rig_rotation @ offset
            right_pole = anchor + rig_rotation @ Vector(profile["rightPoleOffset"])
            right_target = desired_primary.copy()
            for _ in range(8):
                solve_arm_ik(rig, "R", right_target, right_pole)
                align_hand_weapon_axis(
                    rig,
                    rig.pose.bones["hand_R"],
                    weapon_root,
                    local_axis,
                    target_world,
                )
                primary_delta = desired_primary - weapon_root.matrix_world.translation
                right_target += primary_delta
                if primary_delta.length <= 0.0005:
                    break

            desired_secondary = secondary_grip.matrix_world.translation.copy()
            left_pole = anchor + rig_rotation @ Vector(profile["leftPoleOffset"])
            left_target = desired_secondary.copy()
            left_socket = next(
                obj for obj in bpy.context.scene.objects
                if obj.name.startswith("socket_hand_L")
            )
            for _ in range(8):
                solve_arm_ik(rig, "L", left_target, left_pole)
                secondary_delta = desired_secondary - left_socket.matrix_world.translation
                left_target += secondary_delta
                if secondary_delta.length <= 0.0005:
                    break

            actual_direction = (weapon_root.matrix_world.to_3x3() @ local_axis).normalized()
            primary_error = (weapon_root.matrix_world.translation - desired_primary).length
            secondary_error = (left_socket.matrix_world.translation - desired_secondary).length
            direction_error = math.degrees(actual_direction.angle(target_world))
            sampled.append({
                "normalized": normalized,
                "frame": frame,
                "primaryGripErrorM": primary_error,
                "secondaryGripErrorM": secondary_error,
                "directionErrorDegrees": direction_error,
                "rightElbowFlexDegrees": arm_angle_degrees(rig, "upper_arm_R", "forearm_R"),
                "leftElbowFlexDegrees": arm_angle_degrees(rig, "upper_arm_L", "forearm_L"),
                "rightShoulderToGripM": (
                    world_bone_point(rig, "shoulder_R") - weapon_root.matrix_world.translation
                ).length,
            })
            for bone_name in arm_bones:
                bone = rig.pose.bones[bone_name]
                bone.keyframe_insert(data_path="location", frame=frame, group=bone_name)
                bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=bone_name)

        set_linear_arm_keys(action, arm_bones)

        worst_primary = max(sampled, key=lambda row: row["primaryGripErrorM"])
        worst_secondary = max(sampled, key=lambda row: row["secondaryGripErrorM"])
        straightest_left = min(sampled, key=lambda row: row["leftElbowFlexDegrees"])
        audit_clips.append({
            "clip": clip_name,
            "keyCount": len(sampled),
            "maxPrimaryGripErrorM": max(row["primaryGripErrorM"] for row in sampled),
            "maxSecondaryGripErrorM": max(row["secondaryGripErrorM"] for row in sampled),
            "maxDirectionErrorDegrees": max(row["directionErrorDegrees"] for row in sampled),
            "rightElbowFlexRangeDegrees": [
                min(row["rightElbowFlexDegrees"] for row in sampled),
                max(row["rightElbowFlexDegrees"] for row in sampled),
            ],
            "leftElbowFlexRangeDegrees": [
                min(row["leftElbowFlexDegrees"] for row in sampled),
                max(row["leftElbowFlexDegrees"] for row in sampled),
            ],
            "maxRightShoulderToGripM": max(row["rightShoulderToGripM"] for row in sampled),
            "worstPrimaryGripFrame": {
                "frame": worst_primary["frame"],
                "normalized": worst_primary["normalized"],
            },
            "worstSecondaryGripFrame": {
                "frame": worst_secondary["frame"],
                "normalized": worst_secondary["normalized"],
            },
            "straightestLeftElbowFrame": {
                "frame": straightest_left["frame"],
                "normalized": straightest_left["normalized"],
            },
            "clampedKeyCount": 0,
        })

    rig.animation_data.action = None
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    passed = all(
        row["maxPrimaryGripErrorM"] <= float(profile["maxPrimaryGripErrorM"])
        and row["maxSecondaryGripErrorM"] <= float(profile["maxSecondaryGripErrorM"])
        and row["maxDirectionErrorDegrees"] <= float(profile["maxDirectionErrorDegrees"])
        and row["clampedKeyCount"] == 0
        for row in audit_clips
    )
    return {
        "profile": profile_name,
        "applied": True,
        "handedness": profile["handedness"],
        "massClass": profile["massClass"],
        "secondaryGripNode": secondary_grip.name,
        "weaponAxisLocal": list(local_axis),
        "clips": audit_clips,
        "limits": {
            "maxPrimaryGripErrorM": profile["maxPrimaryGripErrorM"],
            "maxSecondaryGripErrorM": profile["maxSecondaryGripErrorM"],
            "maxDirectionErrorDegrees": profile["maxDirectionErrorDegrees"],
        },
        "passed": passed,
    }


def export_combined(output: Path, objects: list[bpy.types.Object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    options = {
        "filepath": str(output),
        "export_format": "GLB",
        "use_selection": True,
        "export_animations": True,
        "export_skins": True,
        "export_morph": True,
        "export_extras": True,
        "export_yup": True,
        "export_apply": False,
        "export_draco_mesh_compression_enable": False,
    }
    available = {prop.identifier for prop in bpy.ops.export_scene.gltf.get_rna_type().properties}
    if "export_animation_mode" in available:
        options["export_animation_mode"] = "ACTIONS"
    if "export_nla_strips" in available:
        options["export_nla_strips"] = False
    if "export_anim_single_armature" in available:
        options["export_anim_single_armature"] = True
    bpy.ops.export_scene.gltf(**options)
    bpy.ops.object.select_all(action="DESELECT")


def glb_document(path: Path) -> dict:
    payload = path.read_bytes()
    if payload[:4] != b"glTF" or int.from_bytes(payload[4:8], "little") != 2:
        raise RuntimeError(f"Not a GLB 2.0 file: {path}")
    offset = 12
    while offset + 8 <= len(payload):
        length = int.from_bytes(payload[offset : offset + 4], "little")
        kind = payload[offset + 4 : offset + 8]
        chunk = payload[offset + 8 : offset + 8 + length]
        if kind == b"JSON":
            return json.loads(chunk.rstrip(b" \t\r\n\x00").decode("utf-8"))
        offset += 8 + length
    raise RuntimeError(f"GLB JSON chunk missing: {path}")


def evaluated_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points = [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def bounds_snapshot(meshes: list[bpy.types.Object]) -> dict:
    rows = {}
    all_minima = []
    all_maxima = []
    for mesh in meshes:
        minimum, maximum = evaluated_bounds(mesh)
        center = (minimum + maximum) * 0.5
        extent = maximum - minimum
        rows[mesh.name] = {
            "assetId": mesh.get("assetId"),
            "minimum": list(minimum),
            "maximum": list(maximum),
            "center": list(center),
            "extent": list(extent),
        }
        all_minima.append(minimum)
        all_maxima.append(maximum)
    minimum = Vector(tuple(min(point[index] for point in all_minima) for index in range(3)))
    maximum = Vector(tuple(max(point[index] for point in all_maxima) for index in range(3)))
    return {
        "meshes": rows,
        "combined": {
            "minimum": list(minimum),
            "maximum": list(maximum),
            "center": list((minimum + maximum) * 0.5),
            "extent": list(maximum - minimum),
        },
    }


def vector(row: list[float]) -> Vector:
    return Vector(tuple(row))


def compare_pose_bounds(bind: dict, idle: dict) -> dict:
    bind_center = vector(bind["combined"]["center"])
    idle_center = vector(idle["combined"]["center"])
    bind_extent = vector(bind["combined"]["extent"])
    idle_extent = vector(idle["combined"]["extent"])
    character_height = max(bind_extent.z, 1e-6)
    combined_center_delta = (idle_center - bind_center).length
    combined_ratios = [idle_extent[index] / max(bind_extent[index], 1e-6) for index in range(3)]
    mesh_rows = []
    for name, bind_row in bind["meshes"].items():
        idle_row = idle["meshes"].get(name)
        if not idle_row:
            mesh_rows.append({"mesh": name, "missingInIdle": True, "passed": False})
            continue
        center_delta = (vector(idle_row["center"]) - vector(bind_row["center"])).length
        bind_mesh_extent = vector(bind_row["extent"])
        idle_mesh_extent = vector(idle_row["extent"])
        ratios = [
            idle_mesh_extent[index] / max(bind_mesh_extent[index], 1e-6)
            for index in range(3)
        ]
        passed = center_delta <= character_height * 0.20 and all(0.45 <= ratio <= 1.75 for ratio in ratios)
        mesh_rows.append({
            "mesh": name,
            "assetId": bind_row["assetId"],
            "centerDelta": center_delta,
            "extentRatios": ratios,
            "passed": passed,
        })
    passed = (
        combined_center_delta <= character_height * 0.12
        and all(0.50 <= ratio <= 1.40 for ratio in combined_ratios)
        and all(row["passed"] for row in mesh_rows)
    )
    return {
        "characterBindHeight": character_height,
        "combinedCenterDelta": combined_center_delta,
        "combinedExtentRatios": combined_ratios,
        "meshDeltas": mesh_rows,
        "thresholds": {
            "combinedCenterFractionOfHeight": 0.12,
            "combinedExtentRatio": [0.50, 1.40],
            "meshCenterFractionOfHeight": 0.20,
            "meshExtentRatio": [0.45, 1.75],
        },
        "passed": passed,
    }


def aim(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_views(meshes: list[bpy.types.Object], output_dir: Path) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for obj in list(bpy.context.scene.objects):
        if obj.get("runtimeAssemblyRenderSupport"):
            bpy.data.objects.remove(obj, do_unlink=True)
    snapshot = bounds_snapshot(meshes)
    minimum = vector(snapshot["combined"]["minimum"])
    maximum = vector(snapshot["combined"]["maximum"])
    center = vector(snapshot["combined"]["center"])
    extent = vector(snapshot["combined"]["extent"])
    distance = max(extent.x, extent.y, extent.z) * 2.25
    camera_data = bpy.data.cameras.new("runtime_assembly_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(extent.z * 1.12, extent.x * 1.18)
    camera = bpy.data.objects.new("runtime_assembly_camera", camera_data)
    camera["runtimeAssemblyRenderSupport"] = True
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    for name, location, energy, size in (
        ("runtime_assembly_key", (-2.6, -3.4, maximum.z + 1.2), 1050, 2.2),
        ("runtime_assembly_fill", (2.8, -1.5, center.z + 0.4), 700, 2.6),
        ("runtime_assembly_rim", (0.6, 3.2, maximum.z + 0.8), 900, 2.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        light["runtimeAssemblyRenderSupport"] = True
        light.location = location
        bpy.context.scene.collection.objects.link(light)
        aim(light, center)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("runtime_assembly_world")
    scene.world.color = (0.025, 0.03, 0.04)
    views = {
        "front": Vector((center.x, minimum.y - distance, center.z)),
        "side": Vector((maximum.x + distance, center.y, center.z)),
        "back": Vector((center.x, maximum.y + distance, center.z)),
        "isometric": Vector((maximum.x + distance * 0.72, minimum.y - distance * 0.72, center.z + extent.z * 0.10)),
    }
    evidence = []
    for name, position in views.items():
        camera.location = position
        aim(camera, center)
        output = output_dir / f"{name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        evidence.append({"view": name, "path": str(output), "sha256": sha256(output)})
    return evidence


def reset_bind_pose(rig: bpy.types.Object) -> None:
    rig.animation_data_create()
    rig.animation_data.action = None
    for pose_bone in rig.pose.bones:
        pose_bone.matrix_basis = Matrix.Identity(4)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()


def set_idle_pose(rig: bpy.types.Object) -> dict:
    action = bpy.data.actions.get("idle")
    if not action:
        raise RuntimeError("Imported combined GLB is missing idle action")
    rig.animation_data_create()
    rig.animation_data.action = action
    first, last = action.frame_range
    frame = round((first + last) * 0.5)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {"action": action.name, "frame": frame, "frameRange": [first, last]}


def post_import_audit(output: Path, review_dir: Path, expected_bones: list[str]) -> dict:
    clear_scene()
    imported = import_glb(output)
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Combined GLB must import one armature; found {len(armatures)}")
    rig = armatures[0]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    module_meshes = [obj for obj in meshes if str(obj.get("assetId", "")).startswith("arm.")]
    body_meshes = [obj for obj in meshes if str(obj.get("assetId", "")).startswith("body_")]
    weapon_meshes = [obj for obj in meshes if str(obj.get("assetId", "")).startswith("wep.")]
    actual_bones = sorted(bone.name for bone in rig.data.bones)
    clips = sorted(action.name for action in bpy.data.actions)
    bind_checks = {
        "singleArmature": len(armatures) == 1,
        "canonicalBones": actual_bones == sorted(expected_bones),
        "nineModules": len(module_meshes) == 9,
        "fourBodyMeshes": len(body_meshes) == 4,
        "weaponPresent": len(weapon_meshes) == 1,
        "nineRequiredClips": clips == sorted(REQUIRED_CLIPS),
        "allModulesBoundToBodyRig": all(
            armature_modifier(mesh).object == rig for mesh in module_meshes
        ),
    }
    reset_bind_pose(rig)
    bind_snapshot = bounds_snapshot(meshes)
    pose_meshes = [
        mesh for mesh in meshes
        if str(mesh.get("assetId", "")).startswith(("arm.", "body_"))
    ]
    pose_bind_snapshot = bounds_snapshot(pose_meshes)
    bind_evidence = render_views(meshes, review_dir / "bind")
    idle_info = set_idle_pose(rig)
    idle_snapshot = bounds_snapshot(meshes)
    pose_idle_snapshot = bounds_snapshot(pose_meshes)
    idle_evidence = render_views(meshes, review_dir / "idle")
    # Weapon orientation is intentionally allowed to change substantially between
    # bind and idle (that is the point of the carry profile). Compare the body and
    # armor envelope for deformation regressions; weapon bounds are still retained
    # in the review evidence and audited separately by the handling profile.
    pose_delta = compare_pose_bounds(
        pose_bind_snapshot,
        pose_idle_snapshot,
    )
    document = glb_document(output)
    json_checks = {
        "singleSkin": len(document.get("skins", [])) == 1,
        "nineAnimations": sorted(animation.get("name", "") for animation in document.get("animations", []))
        == sorted(REQUIRED_CLIPS),
    }
    passed = all(bind_checks.values()) and all(json_checks.values()) and pose_delta["passed"]
    return {
        "importedObjectCount": len(imported),
        "meshCount": len(meshes),
        "bodyMeshCount": len(body_meshes),
        "moduleMeshCount": len(module_meshes),
        "weaponMeshCount": len(weapon_meshes),
        "boneCount": len(actual_bones),
        "animationClips": clips,
        "checks": bind_checks,
        "glbJsonChecks": json_checks,
        "bindPose": {"bounds": bind_snapshot, "previews": bind_evidence},
        "idlePose": {"info": idle_info, "bounds": idle_snapshot, "previews": idle_evidence},
        "idleDeltaAudit": pose_delta,
        "passed": passed,
    }


def main() -> None:
    args = parse_args()
    body_glb = Path(args.body_glb).resolve()
    modules_dir = Path(args.modules_dir).resolve()
    hammer_glb = Path(args.hammer_glb).resolve()
    output = Path(args.output).resolve()
    review_dir = Path(args.review_dir).resolve()
    report_path = Path(args.report).resolve() if args.report else output.with_suffix(".qc.json")
    clear_scene()
    body_import = import_glb(body_glb)
    body_rigs = [obj for obj in body_import if obj.type == "ARMATURE"]
    body_meshes = [
        obj
        for obj in body_import
        if obj.type == "MESH" and str(obj.get("assetId", "")).startswith("body_")
    ]
    sockets = [obj for obj in body_import if obj.type == "EMPTY" and obj.name.startswith("socket_")]
    if len(body_rigs) != 1 or len(body_meshes) != 4:
        raise RuntimeError(
            f"Verified runtime body must import one armature and four body meshes; "
            f"found {len(body_rigs)} armature(s), {len(body_meshes)} mesh(es)"
        )
    body_rig = body_rigs[0]
    body_rig.name = RIG_NAME
    expected_bones = sorted(bone.name for bone in body_rig.data.bones)
    if sorted(action.name for action in bpy.data.actions) != sorted(REQUIRED_CLIPS):
        raise RuntimeError("Verified runtime body does not contain the canonical nine actions")
    delete_objects([obj for obj in body_import if obj not in [body_rig, *body_meshes, *sockets]])

    module_paths = sorted(modules_dir.glob("arm_civic_humanoid_v2_battle_prelate_v1_*_m.glb"))
    if len(module_paths) != 9:
        raise RuntimeError(f"Expected exactly nine module GLBs in {modules_dir}; found {len(module_paths)}")
    module_meshes = []
    module_audits = []
    for module_path in module_paths:
        mesh, audit = rebind_module(module_path, body_rig)
        module_meshes.append(mesh)
        module_audits.append(audit)
    slots = sorted(audit["slot"] for audit in module_audits)
    if slots != sorted(EXPECTED_SLOTS):
        raise RuntimeError(f"Module slots do not match the nine-slot contract: {slots}")
    if len([obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]) != 1:
        raise RuntimeError("Duplicate module armatures remain after rebind")

    socket = next((obj for obj in sockets if obj.name == "socket_hand_R"), None)
    if not socket:
        raise RuntimeError("Verified runtime body is missing socket_hand_R")
    hammer_objects, hammer_audit = attach_hammer(hammer_glb, socket)
    hammer_root = next(obj for obj in hammer_objects if obj.name.startswith("battle_prelate_hammer_root"))
    strike_axis, strike_axis_audit = resolve_weapon_strike_axis(hammer_root, hammer_objects)
    hammer_audit["strikeAxis"] = strike_axis_audit
    animation_profile = str(body_rig.get("animationProfile", ""))
    hammer_audit["animationAlignment"] = align_weapon_axis_animation(
        body_rig,
        hammer_root,
        animation_profile,
        strike_axis,
    )
    if hammer_audit["animationAlignment"].get("applied") is not True:
        raise RuntimeError(f"Missing equipment animation policy for profile: {animation_profile}")
    if hammer_audit["animationAlignment"].get("passed") is not True:
        raise RuntimeError(f"Equipment animation alignment failed: {hammer_audit['animationAlignment']}")
    body_rig["assetId"] = "chr.civic_humanoid_v2.battle_prelate_m.runtime_assembled_review"
    body_rig["assetCategory"] = "characterReview"
    body_rig["lifecycleStatus"] = "draft"
    body_rig["reviewStatus"] = "pending"
    body_rig["promotionEligible"] = False
    export_objects = [body_rig, *body_meshes, *module_meshes, *sockets, *hammer_objects]
    export_combined(output, export_objects)
    pre_export_checks = {
        "singleArmature": len([obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]) == 1,
        "fourBodyMeshes": len(body_meshes) == 4,
        "nineModuleMeshes": len(module_meshes) == 9,
        "nineSlots": slots == sorted(EXPECTED_SLOTS),
        "allModulesRebound": all(armature_modifier(mesh).object == body_rig for mesh in module_meshes),
        "nineClips": sorted(action.name for action in bpy.data.actions) == sorted(REQUIRED_CLIPS),
    }
    roundtrip = post_import_audit(output, review_dir, expected_bones)
    report = {
        "schemaVersion": 1,
        "assetId": "chr.civic_humanoid_v2.battle_prelate_m.runtime_assembled_review",
        "model": str(output),
        "modelSha256": sha256(output),
        "fileSizeBytes": output.stat().st_size,
        "lifecycleStatus": "draft",
        "reviewStatus": "pending_human_visual_review",
        "promotionEligible": False,
        "sources": {
            "body": {"path": str(body_glb), "sha256": sha256(body_glb)},
            "modules": module_audits,
            "hammer": hammer_audit,
        },
        "preExportChecks": pre_export_checks,
        "roundTrip": roundtrip,
        "technicalRoundTripPassed": all(pre_export_checks.values()) and roundtrip["passed"],
        "visualApprovalPassed": False,
        "blockingReasons": [
            "human_bind_and_idle_visual_approval_missing",
            "stress_pose_review_missing",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("[runtime-equipped-assembly] " + json.dumps({
        "output": str(output),
        "report": str(report_path),
        "moduleCount": len(module_meshes),
        "boneCount": len(expected_bones),
        "clipCount": len(REQUIRED_CLIPS),
        "idleDeltaPassed": roundtrip["idleDeltaAudit"]["passed"],
        "technicalRoundTripPassed": report["technicalRoundTripPassed"],
    }))
    if not report["technicalRoundTripPassed"]:
        raise RuntimeError(f"Runtime equipped assembly audit failed; see {report_path}")


if __name__ == "__main__":
    main()
