"""Sample canonical runtime clips and enforce pose-space motion gates.

This audit runs on the serialized, fully equipped GLB.  It intentionally uses
101 normalized samples per clip so a visually plausible key pose cannot hide a
centerline crossing, lateral leg drift, detached grip, or inert weapon arc
between authored keys.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector


SAMPLE_COUNT = 101
LOCOMOTION_LIMITS = {
    "walk": {
        "maxLateralFootHipDeviationM": 0.14,
        "kneeFlexDegrees": (45.0, 55.0),
        "hipBobM": (0.015, 0.025),
    },
    "run": {
        "maxLateralFootHipDeviationM": 0.17,
        "kneeFlexDegrees": (75.0, 90.0),
        "hipBobM": (0.025, 0.045),
    },
}
ATTACK_LIMITS = {
    "minHammerHeadPathM": 1.20,
    "minVerticalRangeM": 0.60,
    "minForwardRangeM": 0.35,
    "minAnticipationHeadAboveShoulderM": 0.10,
    "minWristAnticipationImpactDegrees": 15.0,
    "maxWristFromBindDegrees": 75.0,
    "maxSocketGripErrorM": 0.005,
    "minImpactHeadDropM": 0.65,
    "minImpactHeadBelowChestM": 0.10,
    "minImpactHeadForwardOfHipsM": 0.20,
    "minImpactGripAboveHeadM": 0.10,
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def action_by_name(name: str) -> bpy.types.Action:
    action = bpy.data.actions.get(name)
    if action is None:
        raise RuntimeError(f"Serialized GLB is missing animation clip: {name}")
    return action


def reset_pose(rig: bpy.types.Object) -> None:
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()


def set_normalized_frame(action: bpy.types.Action, normalized: float) -> None:
    start, end = action.frame_range
    value = float(start) + (float(end) - float(start)) * normalized
    whole = math.floor(value)
    bpy.context.scene.frame_set(whole, subframe=value - whole)
    bpy.context.view_layer.update()


def world_bone_point(rig: bpy.types.Object, bone_name: str, endpoint: str = "head") -> Vector:
    bone = rig.pose.bones[bone_name]
    return rig.matrix_world @ getattr(bone, endpoint)


def world_location(obj: bpy.types.Object) -> Vector:
    return obj.matrix_world.translation.copy()


def mean(points: list[Vector]) -> Vector:
    return sum(points, Vector()) / len(points)


def find_hammer_mesh() -> bpy.types.Object:
    matches = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("assetCategory") == "weapon"
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one serialized weapon mesh; found {len(matches)}")
    return matches[0]


def hammer_head_local_point(mesh: bpy.types.Object) -> Vector:
    z_values = [vertex.co.z for vertex in mesh.data.vertices]
    minimum, maximum = min(z_values), max(z_values)
    cutoff = maximum - (maximum - minimum) * 0.18
    candidates = [vertex.co.copy() for vertex in mesh.data.vertices if vertex.co.z >= cutoff]
    if not candidates:
        raise RuntimeError("Could not identify the hammer head from its shaft axis")
    return mean(candidates)


def quaternion_angle_degrees(left: Quaternion, right: Quaternion) -> float:
    return math.degrees(left.rotation_difference(right).angle)


def audit_locomotion(rig: bpy.types.Object, clip_name: str) -> dict:
    action = action_by_name(clip_name)
    reset_pose(rig)
    rig.animation_data.action = action
    samples = []
    for index in range(SAMPLE_COUNT):
        normalized = index / (SAMPLE_COUNT - 1)
        set_normalized_frame(action, normalized)
        left_hip = world_bone_point(rig, "thigh_L")
        right_hip = world_bone_point(rig, "thigh_R")
        left_foot = world_bone_point(rig, "foot_L")
        right_foot = world_bone_point(rig, "foot_R")
        left_thigh_direction = (
            world_bone_point(rig, "thigh_L", "tail") - left_hip
        ).normalized()
        right_thigh_direction = (
            world_bone_point(rig, "thigh_R", "tail") - right_hip
        ).normalized()
        left_shin_direction = (
            world_bone_point(rig, "shin_L", "tail") - world_bone_point(rig, "shin_L")
        ).normalized()
        right_shin_direction = (
            world_bone_point(rig, "shin_R", "tail") - world_bone_point(rig, "shin_R")
        ).normalized()
        samples.append({
            "normalized": normalized,
            "leftFootX": left_foot.x,
            "rightFootX": right_foot.x,
            "leftDeviation": abs(left_foot.x - left_hip.x),
            "rightDeviation": abs(right_foot.x - right_hip.x),
            "hipZ": world_bone_point(rig, "hips").z,
            "leftKneeFlexDegrees": math.degrees(left_thigh_direction.angle(left_shin_direction)),
            "rightKneeFlexDegrees": math.degrees(right_thigh_direction.angle(right_shin_direction)),
        })

    max_deviation = max(
        max(row["leftDeviation"], row["rightDeviation"])
        for row in samples
    )
    min_left_x = min(row["leftFootX"] for row in samples)
    max_right_x = max(row["rightFootX"] for row in samples)
    policy = LOCOMOTION_LIMITS[clip_name]
    limit = policy["maxLateralFootHipDeviationM"]
    maximum_knee_flex = max(
        max(row["leftKneeFlexDegrees"], row["rightKneeFlexDegrees"])
        for row in samples
    )
    hip_bob = max(row["hipZ"] for row in samples) - min(row["hipZ"] for row in samples)
    knee_minimum, knee_maximum = policy["kneeFlexDegrees"]
    bob_minimum, bob_maximum = policy["hipBobM"]
    checks = {
        "lateralDeviationBounded": max_deviation <= limit,
        "leftFootStaysLeftOfCenterline": min_left_x >= 0.05,
        "rightFootStaysRightOfCenterline": max_right_x <= -0.05,
        "kneeFlexNatural": knee_minimum <= maximum_knee_flex <= knee_maximum,
        "hipBobNatural": bob_minimum <= hip_bob <= bob_maximum,
    }
    return {
        "clip": clip_name,
        "sampleCount": SAMPLE_COUNT,
        "maxLateralFootHipDeviationM": max_deviation,
        "limitM": limit,
        "minLeftFootX": min_left_x,
        "maxRightFootX": max_right_x,
        "maxKneeFlexDegrees": maximum_knee_flex,
        "hipBobM": hip_bob,
        "kneeFlexRangeDegrees": list(policy["kneeFlexDegrees"]),
        "hipBobRangeM": list(policy["hipBobM"]),
        "checks": checks,
        "passed": all(checks.values()),
    }


def pose_attack_sample(
    rig: bpy.types.Object,
    action: bpy.types.Action,
    normalized: float,
    hammer_mesh: bpy.types.Object,
    hammer_head_local: Vector,
    socket: bpy.types.Object,
    grip: bpy.types.Object,
) -> dict:
    set_normalized_frame(action, normalized)
    hand_basis = rig.pose.bones["hand_R"].matrix_basis.to_quaternion().normalized()
    return {
        "normalized": normalized,
        "hammerHead": hammer_mesh.matrix_world @ hammer_head_local,
        "shoulder": world_bone_point(rig, "shoulder_R"),
        "socketGripError": (world_location(socket) - world_location(grip)).length,
        "wristFromBindDegrees": quaternion_angle_degrees(Quaternion(), hand_basis),
        "wrist": hand_basis,
    }


def audit_attack(rig: bpy.types.Object) -> dict:
    action = action_by_name("attack_melee")
    hammer_mesh = find_hammer_mesh()
    hammer_head_local = hammer_head_local_point(hammer_mesh)
    socket = next((obj for obj in bpy.context.scene.objects if obj.name.startswith("socket_hand_R")), None)
    grip = next((obj for obj in bpy.context.scene.objects if obj.name.startswith("weapon_grip_socket_hand_R")), None)
    root = next((obj for obj in bpy.context.scene.objects if obj.name.startswith("battle_prelate_hammer_root")), None)
    if socket is None or grip is None or root is None:
        raise RuntimeError("Serialized hammer attachment nodes are incomplete")

    reset_pose(rig)
    rig.animation_data.action = action
    samples = [
        pose_attack_sample(
            rig,
            action,
            index / (SAMPLE_COUNT - 1),
            hammer_mesh,
            hammer_head_local,
            socket,
            grip,
        )
        for index in range(SAMPLE_COUNT)
    ]
    path_length = sum(
        (samples[index]["hammerHead"] - samples[index - 1]["hammerHead"]).length
        for index in range(1, len(samples))
    )
    z_values = [row["hammerHead"].z for row in samples]
    y_values = [row["hammerHead"].y for row in samples]
    max_grip_error = max(row["socketGripError"] for row in samples)
    max_wrist_from_bind = max(row["wristFromBindDegrees"] for row in samples)
    max_wrist_sample = max(samples, key=lambda row: row["wristFromBindDegrees"])

    anticipation = pose_attack_sample(
        rig, action, 7 / 30, hammer_mesh, hammer_head_local, socket, grip,
    )
    impact = pose_attack_sample(
        rig, action, 14 / 30, hammer_mesh, hammer_head_local, socket, grip,
    )
    wrist_change = quaternion_angle_degrees(anticipation["wrist"], impact["wrist"])
    anticipation_clearance = anticipation["hammerHead"].z - anticipation["shoulder"].z
    set_normalized_frame(action, 14 / 30)
    impact_chest = world_bone_point(rig, "chest")
    impact_hips = world_bone_point(rig, "hips")
    impact_grip = world_location(grip)
    impact_head_drop = anticipation["hammerHead"].z - impact["hammerHead"].z
    impact_below_chest = impact_chest.z - impact["hammerHead"].z
    impact_forward_of_hips = impact_hips.y - impact["hammerHead"].y
    impact_grip_above_head = impact_grip.z - impact["hammerHead"].z
    vertical_range = max(z_values) - min(z_values)
    forward_range = max(y_values) - min(y_values)
    root_scale = root.scale
    limits = ATTACK_LIMITS
    checks = {
        "substantiveHammerArc": path_length >= limits["minHammerHeadPathM"],
        "verticalRange": vertical_range >= limits["minVerticalRangeM"],
        "forwardRange": forward_range >= limits["minForwardRangeM"],
        "anticipationAboveShoulder": anticipation_clearance >= limits["minAnticipationHeadAboveShoulderM"],
        "wristDrivesImpact": wrist_change >= limits["minWristAnticipationImpactDegrees"],
        "wristWithinAnatomicalLimit": max_wrist_from_bind <= limits["maxWristFromBindDegrees"],
        "socketGripAttached": max_grip_error <= limits["maxSocketGripErrorM"],
        "attachmentScaleOne": max(abs(value - 1.0) for value in root_scale) <= 1e-4,
        "impactHeadDropsFromWindup": impact_head_drop >= limits["minImpactHeadDropM"],
        "impactHeadBelowChest": impact_below_chest >= limits["minImpactHeadBelowChestM"],
        "impactHeadForwardOfHips": impact_forward_of_hips >= limits["minImpactHeadForwardOfHipsM"],
        "impactGripAboveHead": impact_grip_above_head >= limits["minImpactGripAboveHeadM"],
    }
    return {
        "clip": "attack_melee",
        "sampleCount": SAMPLE_COUNT,
        "hammerHeadPathM": path_length,
        "verticalRangeM": vertical_range,
        "forwardRangeM": forward_range,
        "anticipationHeadAboveShoulderM": anticipation_clearance,
        "wristAnticipationImpactDegrees": wrist_change,
        "maxWristFromBindDegrees": max_wrist_from_bind,
        "maxWristNormalized": max_wrist_sample["normalized"],
        "maxSocketGripErrorM": max_grip_error,
        "impactHeadDropM": impact_head_drop,
        "impactHeadBelowChestM": impact_below_chest,
        "impactHeadForwardOfHipsM": impact_forward_of_hips,
        "impactGripAboveHeadM": impact_grip_above_head,
        "attachmentRootScale": list(root_scale),
        "limits": limits,
        "checks": checks,
        "passed": all(checks.values()),
    }


def audit_secondary_grip_advisory(rig: bpy.types.Object) -> dict:
    """Report, but do not gate, the absent second-hand grip contract."""
    root = next(obj for obj in bpy.context.scene.objects if obj.name.startswith("battle_prelate_hammer_root"))
    left_socket = next(obj for obj in bpy.context.scene.objects if obj.name.startswith("socket_hand_L"))
    secondary_local = Vector((0.0, 0.0, 0.30))
    rows = {}
    for clip_name, normalized, limit in (("idle", 0.5, 0.04), ("attack_melee", 14 / 30, 0.06)):
        action = action_by_name(clip_name)
        reset_pose(rig)
        rig.animation_data.action = action
        set_normalized_frame(action, normalized)
        distance = (world_location(left_socket) - (root.matrix_world @ secondary_local)).length
        rows[clip_name] = {"distanceM": distance, "advisoryLimitM": limit, "passed": distance <= limit}
    return {
        "status": "advisory_until_secondary_grip_node_is_part_of_weapon_contract",
        "clips": rows,
        "passed": all(row["passed"] for row in rows.values()),
    }


def main() -> None:
    args = parse_args()
    model = Path(args.model).resolve()
    output = Path(args.output).resolve()
    if not model.is_file() or model.suffix.lower() != ".glb":
        raise FileNotFoundError(model)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(model))
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(rigs) != 1:
        raise RuntimeError(f"Expected one canonical armature; found {len(rigs)}")
    rig = rigs[0]
    walk = audit_locomotion(rig, "walk")
    run = audit_locomotion(rig, "run")
    attack = audit_attack(rig)
    secondary = audit_secondary_grip_advisory(rig)
    report = {
        "schemaVersion": 1,
        "model": str(model),
        "sampleCountPerClip": SAMPLE_COUNT,
        "locomotion": {"walk": walk, "run": run},
        "attackMelee": attack,
        "secondaryGrip": secondary,
        "passed": walk["passed"] and run["passed"] and attack["passed"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("[canonical-motion-audit] " + json.dumps({
        "output": str(output),
        "passed": report["passed"],
        "walkMaxLateralM": walk["maxLateralFootHipDeviationM"],
        "runMaxLateralM": run["maxLateralFootHipDeviationM"],
        "hammerPathM": attack["hammerHeadPathM"],
        "secondaryGripAdvisoryPassed": secondary["passed"],
    }))
    if not report["passed"]:
        raise RuntimeError("Canonical animation pose-space audit failed")


if __name__ == "__main__":
    main()
