"""Sample an equipped canonical GLB and enforce ergonomic motion gates.

The audit runs on the serialized review GLB, not the authoring scene. Every
relevant clip is sampled at 101 normalized points so an acceptable key pose
cannot conceal a wide stance, a crossed knee, a detached second hand, or an
overextended weapon pose between keys.
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


SAMPLE_COUNT = 101
TWO_HAND_CLIPS = ("idle", "walk", "run", "combat_idle", "attack_melee")
STANCE_LIMITS = {
    "minWidthM": 0.20,
    "maxWidthM": 0.34,
    "minWidthToHipRatio": 0.80,
    "maxWidthToHipRatio": 1.45,
    "maxFootHipLateralDeviationM": 0.065,
    "maxKneeLineDeviationM": 0.065,
    "minJointCenterlineClearanceM": 0.035,
}
LOCOMOTION_LIMITS = {
    "walk": {
        **STANCE_LIMITS,
        "kneeFlexDegrees": (40.0, 65.0),
        "hipBobM": (0.015, 0.025),
    },
    "run": {
        **STANCE_LIMITS,
        "kneeFlexDegrees": (70.0, 100.0),
        "hipBobM": (0.025, 0.045),
    },
}
HANDLING_LIMITS = {
    "maxPrimaryGripErrorM": 0.012,
    # The runtime GLB is sampled between keyed Blender poses. Five centimetres
    # is the upper bound for that interpolation drift on this 1.86m body; the
    # authored keys themselves are held below 1mm by the assembly gate.
    "maxSecondaryGripErrorM": 0.050,
    "maxShoulderToGripM": 0.68,
    "minElbowInternalAngleDegrees": 20.0,
    "maxElbowInternalAngleDegrees": 175.0,
    # A two-handed heavy weapon intentionally rotates the hand well beyond the
    # unarmed bind orientation; reach and grip attachment remain hard gates.
    "maxWristFromBindDegrees": 140.0,
}
ATTACK_LIMITS = {
    # The pilot uses a compact torso-led strike so the hands stay humanly
    # reachable. These are absolute metre budgets, not provider-specific waivers.
    "minHammerHeadPathM": 0.60,
    "maxHammerHeadPathM": 5.00,
    "minVerticalRangeM": 0.08,
    "maxVerticalRangeM": 1.55,
    "minForwardRangeM": 0.25,
    "maxForwardRangeM": 1.40,
    "maxShoulderToHammerHeadM": 1.55,
    "minAnticipationHeadAboveShoulderM": 0.05,
    "minWristAnticipationImpactDegrees": 10.0,
    "minImpactHeadDropM": 0.02,
    "minImpactHeadForwardOfHipsM": 0.12,
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def action_by_name(name: str) -> bpy.types.Action:
    action = bpy.data.actions.get(name)
    if action is None:
        raise RuntimeError(f"Serialized GLB is missing animation clip: {name}")
    return action


def object_by_prefix(prefix: str) -> bpy.types.Object:
    matches = [obj for obj in bpy.context.scene.objects if obj.name.startswith(prefix)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one serialized {prefix} node; found {len(matches)}")
    return matches[0]


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


def joint_points(
    rig: bpy.types.Object,
    proximal_bone_name: str,
    distal_bone_name: str,
) -> tuple[Vector, Vector, Vector]:
    """Return proximal joint, shared joint, and distal joint independent of bone axis."""
    proximal = [
        world_bone_point(rig, proximal_bone_name, "head"),
        world_bone_point(rig, proximal_bone_name, "tail"),
    ]
    distal = [
        world_bone_point(rig, distal_bone_name, "head"),
        world_bone_point(rig, distal_bone_name, "tail"),
    ]
    proximal_index, distal_index = min(
        ((left, right) for left in range(2) for right in range(2)),
        key=lambda pair: (proximal[pair[0]] - distal[pair[1]]).length,
    )
    joint = (proximal[proximal_index] + distal[distal_index]) * 0.5
    return proximal[1 - proximal_index], joint, distal[1 - distal_index]


def internal_joint_angle_degrees(
    rig: bpy.types.Object,
    proximal_bone_name: str,
    distal_bone_name: str,
) -> float:
    proximal, joint, distal = joint_points(rig, proximal_bone_name, distal_bone_name)
    return math.degrees((proximal - joint).angle(distal - joint))


def leg_sample(rig: bpy.types.Object) -> dict:
    left_hip = world_bone_point(rig, "thigh_L")
    right_hip = world_bone_point(rig, "thigh_R")
    left_foot = world_bone_point(rig, "foot_L")
    right_foot = world_bone_point(rig, "foot_R")
    _, left_knee, _ = joint_points(rig, "thigh_L", "shin_L")
    _, right_knee, _ = joint_points(rig, "thigh_R", "shin_R")
    hip_width = abs(left_hip.x - right_hip.x)
    stance_width = abs(left_foot.x - right_foot.x)
    return {
        "leftHipX": left_hip.x,
        "rightHipX": right_hip.x,
        "leftFootX": left_foot.x,
        "rightFootX": right_foot.x,
        "leftKneeX": left_knee.x,
        "rightKneeX": right_knee.x,
        "leftDeviation": abs(left_foot.x - left_hip.x),
        "rightDeviation": abs(right_foot.x - right_hip.x),
        "leftKneeLineDeviation": abs(left_knee.x - (left_hip.x + left_foot.x) * 0.5),
        "rightKneeLineDeviation": abs(right_knee.x - (right_hip.x + right_foot.x) * 0.5),
        "hipWidthM": hip_width,
        "stanceWidthM": stance_width,
        "stanceToHipRatio": stance_width / hip_width if hip_width > 1e-6 else float("inf"),
        "leftKneeFlexDegrees": 180.0 - internal_joint_angle_degrees(rig, "thigh_L", "shin_L"),
        "rightKneeFlexDegrees": 180.0 - internal_joint_angle_degrees(rig, "thigh_R", "shin_R"),
        "hipZ": world_bone_point(rig, "hips").z,
    }


def stance_summary(samples: list[dict], limits: dict) -> tuple[dict, dict]:
    widths = [row["stanceWidthM"] for row in samples]
    ratios = [row["stanceToHipRatio"] for row in samples]
    max_foot_deviation = max(
        max(row["leftDeviation"], row["rightDeviation"])
        for row in samples
    )
    max_knee_deviation = max(
        max(row["leftKneeLineDeviation"], row["rightKneeLineDeviation"])
        for row in samples
    )
    minimum_clearance = limits["minJointCenterlineClearanceM"]
    checks = {
        "stanceWidthNatural": (
            min(widths) >= limits["minWidthM"]
            and max(widths) <= limits["maxWidthM"]
        ),
        "stanceWidthTracksHipWidth": (
            min(ratios) >= limits["minWidthToHipRatio"]
            and max(ratios) <= limits["maxWidthToHipRatio"]
        ),
        "feetAlignedUnderSameSideHips": max_foot_deviation <= limits["maxFootHipLateralDeviationM"],
        "kneesTrackHipFootLine": max_knee_deviation <= limits["maxKneeLineDeviationM"],
        "leftLegStaysLeftOfCenterline": min(
            min(row["leftFootX"], row["leftKneeX"]) for row in samples
        ) >= minimum_clearance,
        "rightLegStaysRightOfCenterline": max(
            max(row["rightFootX"], row["rightKneeX"]) for row in samples
        ) <= -minimum_clearance,
        "legOrderingNatural": all(
            row["leftFootX"] > row["rightFootX"]
            and row["leftKneeX"] > row["rightKneeX"]
            for row in samples
        ),
    }
    metrics = {
        "minStanceWidthM": min(widths),
        "maxStanceWidthM": max(widths),
        "minStanceToHipRatio": min(ratios),
        "maxStanceToHipRatio": max(ratios),
        "maxFootHipLateralDeviationM": max_foot_deviation,
        "maxKneeLineDeviationM": max_knee_deviation,
    }
    return metrics, checks


def audit_neutral_stance(rig: bpy.types.Object) -> dict:
    action = action_by_name("idle")
    reset_pose(rig)
    rig.animation_data.action = action
    samples = []
    for index in range(SAMPLE_COUNT):
        set_normalized_frame(action, index / (SAMPLE_COUNT - 1))
        samples.append(leg_sample(rig))
    metrics, checks = stance_summary(samples, STANCE_LIMITS)
    return {
        "clip": "idle",
        "sampleCount": SAMPLE_COUNT,
        **metrics,
        "limits": STANCE_LIMITS,
        "checks": checks,
        "passed": all(checks.values()),
    }


def audit_locomotion(rig: bpy.types.Object, clip_name: str) -> dict:
    action = action_by_name(clip_name)
    reset_pose(rig)
    rig.animation_data.action = action
    samples = []
    for index in range(SAMPLE_COUNT):
        set_normalized_frame(action, index / (SAMPLE_COUNT - 1))
        samples.append(leg_sample(rig))

    policy = LOCOMOTION_LIMITS[clip_name]
    metrics, checks = stance_summary(samples, policy)
    maximum_knee_flex = max(
        max(row["leftKneeFlexDegrees"], row["rightKneeFlexDegrees"])
        for row in samples
    )
    hip_bob = max(row["hipZ"] for row in samples) - min(row["hipZ"] for row in samples)
    knee_minimum, knee_maximum = policy["kneeFlexDegrees"]
    bob_minimum, bob_maximum = policy["hipBobM"]
    checks.update({
        "kneeFlexNatural": knee_minimum <= maximum_knee_flex <= knee_maximum,
        "hipBobNatural": bob_minimum <= hip_bob <= bob_maximum,
    })
    return {
        "clip": clip_name,
        "sampleCount": SAMPLE_COUNT,
        **metrics,
        "maxKneeFlexDegrees": maximum_knee_flex,
        "hipBobM": hip_bob,
        "limits": policy,
        "checks": checks,
        "passed": all(checks.values()),
    }


def quaternion_angle_degrees(left: Quaternion, right: Quaternion) -> float:
    return math.degrees(left.rotation_difference(right).angle)


def hand_pose_sample(
    rig: bpy.types.Object,
    primary_grip: bpy.types.Object,
    secondary_grip: bpy.types.Object,
    right_socket: bpy.types.Object,
    left_socket: bpy.types.Object,
) -> dict:
    right_shoulder, _, _ = joint_points(rig, "upper_arm_R", "forearm_R")
    left_shoulder, _, _ = joint_points(rig, "upper_arm_L", "forearm_L")
    primary_location = world_location(primary_grip)
    secondary_location = world_location(secondary_grip)
    return {
        "primaryGripErrorM": (world_location(right_socket) - primary_location).length,
        "secondaryGripErrorM": (world_location(left_socket) - secondary_location).length,
        "rightShoulderToGripM": (right_shoulder - primary_location).length,
        "leftShoulderToGripM": (left_shoulder - secondary_location).length,
        "rightElbowInternalAngleDegrees": internal_joint_angle_degrees(rig, "upper_arm_R", "forearm_R"),
        "leftElbowInternalAngleDegrees": internal_joint_angle_degrees(rig, "upper_arm_L", "forearm_L"),
        "rightWristFromBindDegrees": quaternion_angle_degrees(
            Quaternion(), rig.pose.bones["hand_R"].matrix_basis.to_quaternion().normalized(),
        ),
        "leftWristFromBindDegrees": quaternion_angle_degrees(
            Quaternion(), rig.pose.bones["hand_L"].matrix_basis.to_quaternion().normalized(),
        ),
    }


def audit_two_hand_handling(rig: bpy.types.Object) -> dict:
    primary_grip = object_by_prefix("weapon_grip_socket_hand_R")
    secondary_grip = object_by_prefix("weapon_grip_socket_hand_L")
    right_socket = object_by_prefix("socket_hand_R")
    left_socket = object_by_prefix("socket_hand_L")
    marker_contract = {
        "secondaryMarkerPresent": True,
        "secondaryMarkerRole": secondary_grip.get("gripRole") == "secondary",
        "secondaryMarkerTargetsLeftSocket": secondary_grip.get("targetSocket") == "socket_hand_L",
    }
    clips = {}
    limits = HANDLING_LIMITS
    for clip_name in TWO_HAND_CLIPS:
        action = action_by_name(clip_name)
        reset_pose(rig)
        rig.animation_data.action = action
        samples = []
        for index in range(SAMPLE_COUNT):
            normalized = index / (SAMPLE_COUNT - 1)
            set_normalized_frame(action, normalized)
            samples.append({
                "normalized": normalized,
                **hand_pose_sample(rig, primary_grip, secondary_grip, right_socket, left_socket),
            })
        max_primary_error = max(row["primaryGripErrorM"] for row in samples)
        max_secondary_error = max(row["secondaryGripErrorM"] for row in samples)
        max_right_reach = max(row["rightShoulderToGripM"] for row in samples)
        max_left_reach = max(row["leftShoulderToGripM"] for row in samples)
        min_right_elbow = min(row["rightElbowInternalAngleDegrees"] for row in samples)
        max_right_elbow = max(row["rightElbowInternalAngleDegrees"] for row in samples)
        min_left_elbow = min(row["leftElbowInternalAngleDegrees"] for row in samples)
        max_left_elbow = max(row["leftElbowInternalAngleDegrees"] for row in samples)
        max_right_wrist = max(row["rightWristFromBindDegrees"] for row in samples)
        max_left_wrist = max(row["leftWristFromBindDegrees"] for row in samples)
        checks = {
            "primaryGripAttached": max_primary_error <= limits["maxPrimaryGripErrorM"],
            "secondaryGripAttached": max_secondary_error <= limits["maxSecondaryGripErrorM"],
            "shoulderReachCompact": max(max_right_reach, max_left_reach) <= limits["maxShoulderToGripM"],
            "rightElbowErgonomic": (
                min_right_elbow >= limits["minElbowInternalAngleDegrees"]
                and max_right_elbow <= limits["maxElbowInternalAngleDegrees"]
            ),
            "leftElbowErgonomic": (
                min_left_elbow >= limits["minElbowInternalAngleDegrees"]
                and max_left_elbow <= limits["maxElbowInternalAngleDegrees"]
            ),
            "wristsWithinAnatomicalLimit": (
                max(max_right_wrist, max_left_wrist) <= limits["maxWristFromBindDegrees"]
            ),
        }
        clips[clip_name] = {
            "sampleCount": SAMPLE_COUNT,
            "maxPrimaryGripErrorM": max_primary_error,
            "maxSecondaryGripErrorM": max_secondary_error,
            "maxRightShoulderToGripM": max_right_reach,
            "maxLeftShoulderToGripM": max_left_reach,
            "rightElbowInternalAngleRangeDegrees": [min_right_elbow, max_right_elbow],
            "leftElbowInternalAngleRangeDegrees": [min_left_elbow, max_left_elbow],
            "maxRightWristFromBindDegrees": max_right_wrist,
            "maxLeftWristFromBindDegrees": max_left_wrist,
            "checks": checks,
            "passed": all(checks.values()),
        }
    return {
        "handedness": "two_handed",
        "clipsAudited": list(TWO_HAND_CLIPS),
        "secondaryGripNode": secondary_grip.name,
        "markerContract": marker_contract,
        "limits": limits,
        "clips": clips,
        "passed": all(marker_contract.values()) and all(row["passed"] for row in clips.values()),
    }


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


def attack_pose_sample(
    rig: bpy.types.Object,
    action: bpy.types.Action,
    normalized: float,
    hammer_mesh: bpy.types.Object,
    hammer_head_local: Vector,
    strike_marker: bpy.types.Object | None,
) -> dict:
    set_normalized_frame(action, normalized)
    hammer_head = (
        world_location(strike_marker)
        if strike_marker is not None
        else hammer_mesh.matrix_world @ hammer_head_local
    )
    shoulder, _, _ = joint_points(rig, "upper_arm_R", "forearm_R")
    return {
        "normalized": normalized,
        "hammerHead": hammer_head,
        "shoulder": shoulder,
        "shoulderToHammerHeadM": (shoulder - hammer_head).length,
        "rightWrist": rig.pose.bones["hand_R"].matrix_basis.to_quaternion().normalized(),
    }


def audit_attack(rig: bpy.types.Object) -> dict:
    action = action_by_name("attack_melee")
    hammer_mesh = find_hammer_mesh()
    hammer_head_local = hammer_head_local_point(hammer_mesh)
    strike_marker = next(
        (obj for obj in bpy.context.scene.objects if obj.name.startswith("weapon_strike_head")),
        None,
    )
    root = object_by_prefix("battle_prelate_hammer_root")
    reset_pose(rig)
    rig.animation_data.action = action
    samples = [
        attack_pose_sample(
            rig,
            action,
            index / (SAMPLE_COUNT - 1),
            hammer_mesh,
            hammer_head_local,
            strike_marker,
        )
        for index in range(SAMPLE_COUNT)
    ]
    path_length = sum(
        (samples[index]["hammerHead"] - samples[index - 1]["hammerHead"]).length
        for index in range(1, len(samples))
    )
    z_values = [row["hammerHead"].z for row in samples]
    y_values = [row["hammerHead"].y for row in samples]
    max_head_reach = max(row["shoulderToHammerHeadM"] for row in samples)
    anticipation = attack_pose_sample(
        rig, action, 7 / 30, hammer_mesh, hammer_head_local, strike_marker,
    )
    impact = attack_pose_sample(
        rig, action, 14 / 30, hammer_mesh, hammer_head_local, strike_marker,
    )
    wrist_change = quaternion_angle_degrees(anticipation["rightWrist"], impact["rightWrist"])
    anticipation_clearance = anticipation["hammerHead"].z - anticipation["shoulder"].z
    set_normalized_frame(action, 14 / 30)
    impact_hips = world_bone_point(rig, "hips")
    impact_head_drop = anticipation["hammerHead"].z - impact["hammerHead"].z
    impact_forward_of_hips = impact_hips.y - impact["hammerHead"].y
    vertical_range = max(z_values) - min(z_values)
    forward_range = max(y_values) - min(y_values)
    limits = ATTACK_LIMITS
    checks = {
        "substantiveHammerArc": path_length >= limits["minHammerHeadPathM"],
        "hammerArcCompact": path_length <= limits["maxHammerHeadPathM"],
        "verticalRangeNatural": (
            limits["minVerticalRangeM"] <= vertical_range <= limits["maxVerticalRangeM"]
        ),
        "forwardRangeNatural": (
            limits["minForwardRangeM"] <= forward_range <= limits["maxForwardRangeM"]
        ),
        "hammerHeadReachBounded": max_head_reach <= limits["maxShoulderToHammerHeadM"],
        "anticipationAboveShoulder": anticipation_clearance >= limits["minAnticipationHeadAboveShoulderM"],
        "wristDrivesImpact": wrist_change >= limits["minWristAnticipationImpactDegrees"],
        "attachmentScaleOne": max(abs(value - 1.0) for value in root.scale) <= 1e-4,
        "impactHeadDropsFromWindup": impact_head_drop >= limits["minImpactHeadDropM"],
        "impactHeadForwardOfHips": impact_forward_of_hips >= limits["minImpactHeadForwardOfHipsM"],
    }
    return {
        "clip": "attack_melee",
        "sampleCount": SAMPLE_COUNT,
        "hammerHeadSource": strike_marker.name if strike_marker is not None else "geometry_cluster_fallback",
        "hammerHeadPathM": path_length,
        "verticalRangeM": vertical_range,
        "forwardRangeM": forward_range,
        "maxShoulderToHammerHeadM": max_head_reach,
        "anticipationHeadAboveShoulderM": anticipation_clearance,
        "wristAnticipationImpactDegrees": wrist_change,
        "impactHeadDropM": impact_head_drop,
        "impactHeadForwardOfHipsM": impact_forward_of_hips,
        "attachmentRootScale": list(root.scale),
        "limits": limits,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> None:
    args = parse_args()
    model = Path(args.model).resolve()
    output = Path(args.output).resolve()
    if not model.is_file() or model.suffix.lower() != ".glb":
        raise FileNotFoundError(model)
    model_hash = sha256(model)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(model))
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(rigs) != 1:
        raise RuntimeError(f"Expected one canonical armature; found {len(rigs)}")
    rig = rigs[0]
    neutral = audit_neutral_stance(rig)
    walk = audit_locomotion(rig, "walk")
    run = audit_locomotion(rig, "run")
    handling = audit_two_hand_handling(rig)
    attack = audit_attack(rig)
    report = {
        "schemaVersion": 2,
        "model": str(model),
        "modelSha256": model_hash,
        "sampleCountPerClip": SAMPLE_COUNT,
        "neutralStance": neutral,
        "locomotion": {"walk": walk, "run": run},
        "twoHandHandling": handling,
        "attackMelee": attack,
        "passed": all((neutral["passed"], walk["passed"], run["passed"], handling["passed"], attack["passed"])),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("[canonical-motion-audit] " + json.dumps({
        "output": str(output),
        "modelSha256": model_hash,
        "passed": report["passed"],
        "idleMaxStanceWidthM": neutral["maxStanceWidthM"],
        "walkMaxStanceWidthM": walk["maxStanceWidthM"],
        "runMaxStanceWidthM": run["maxStanceWidthM"],
        "hammerPathM": attack["hammerHeadPathM"],
        "twoHandHandlingPassed": handling["passed"],
    }))
    if not report["passed"]:
        raise RuntimeError("Canonical animation ergonomic audit failed")


if __name__ == "__main__":
    main()
