"""Attach the original local clip set to a canonical MPFB game rig.

The source keyframes predate the MPFB pilot and use a Y-up coordinate system.
This module is the narrow adapter: it validates the public clip contract,
converts translation channels to Blender Z-up, and leaves the result explicitly
review-gated. It does not claim motion-capture quality or use external assets.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import bpy
from mathutils import Euler, Vector

from canonical_mpfb_animation_library import (
    ANIMATION_PROFILES,
    DEFAULT_ANIMATION_PROFILE,
    make_canonical_mpfb_actions,
)


PIPELINE_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = PIPELINE_ROOT / "data" / "body-families" / "canonical-animation-pack.json"
SOURCE_PATH = Path(__file__).resolve().parent / "anim_library.py"
MPFB_SOURCE_PATH = Path(__file__).resolve().parent / "canonical_mpfb_animation_library.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_animation_contract() -> dict[str, Any]:
    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _reset_pose(armature: bpy.types.Object) -> None:
    for pose_bone in armature.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def _blender_translation(location: tuple[float, float, float]) -> tuple[float, float, float]:
    """Map legacy (X right, Y up, Z forward) to Blender (X right, Z up, -Y forward)."""
    x, y, z = location
    return (x, -z, y)


def _validate_contract(
    contract: dict[str, Any],
    armature: bpy.types.Object,
    actions: dict[str, Any],
) -> list[dict[str, Any]]:
    if contract.get("skeletonId") != "humanoid_game_v2":
        raise RuntimeError("The local animation pack is not bound to humanoid_game_v2")
    if armature.get("skeletonId") != contract["skeletonId"]:
        raise RuntimeError(
            f"Animation skeleton mismatch: {armature.get('skeletonId')} != {contract['skeletonId']}"
        )
    if armature.get("bindPoseId") != contract.get("bindPoseId"):
        raise RuntimeError(
            f"Animation bind-pose mismatch: {armature.get('bindPoseId')} != {contract.get('bindPoseId')}"
        )

    clips = contract.get("clips") or []
    names = [clip.get("name") for clip in clips]
    if len(names) != len(set(names)):
        raise RuntimeError("The local animation contract contains duplicate clip names")
    if set(names) != set(actions):
        missing = sorted(set(names) - set(actions))
        extra = sorted(set(actions) - set(names))
        raise RuntimeError(f"Animation source/contract mismatch; missing={missing}, extra={extra}")

    available_bones = set(armature.pose.bones.keys())
    for clip in clips:
        source = actions[clip["name"]]
        if source.get("duration_frames") != clip.get("durationFrames"):
            raise RuntimeError(f"Duration mismatch for animation clip {clip['name']}")
        if bool(source.get("loop", True)) != bool(clip.get("loop")):
            raise RuntimeError(f"Loop-policy mismatch for animation clip {clip['name']}")
        missing_bones = sorted(set(source.get("keyframes", {})) - available_bones)
        if missing_bones:
            raise RuntimeError(f"Animation clip {clip['name']} targets missing bones: {missing_bones}")
    return clips


def _armature_space_quaternion(
    pose_bone: bpy.types.PoseBone,
    rotation: tuple[float, float, float],
):
    """Convert an armature-axis rotation delta to the bone's MPFB rest basis."""
    rest_basis = pose_bone.bone.matrix_local.to_3x3().normalized()
    armature_delta = Euler(rotation, "XYZ").to_matrix()
    return (rest_basis.inverted() @ armature_delta @ rest_basis).to_quaternion()


def _armature_space_translation(
    pose_bone: bpy.types.PoseBone,
    location: tuple[float, float, float],
) -> Vector:
    """Convert an armature-axis delta to the bone's MPFB rest basis."""
    rest_basis = pose_bone.bone.matrix_local.to_3x3().normalized()
    return rest_basis.inverted() @ Vector(_blender_translation(location))


def attach_canonical_animation_pack(
    armature: bpy.types.Object,
    profile: str = DEFAULT_ANIMATION_PROFILE,
) -> dict[str, Any]:
    """Create one Blender Action per required runtime clip and return an audit record."""
    if profile not in ANIMATION_PROFILES:
        raise RuntimeError(f"Unsupported canonical animation profile: {profile}")
    contract = load_animation_contract()
    actions = make_canonical_mpfb_actions(profile)
    clips = _validate_contract(contract, armature, actions)
    scene = bpy.context.scene
    scene.render.fps = int(contract["framesPerSecond"])
    scene.render.fps_base = 1.0

    if armature.animation_data is None:
        armature.animation_data_create()
    armature.animation_data.action = None
    for track in list(armature.animation_data.nla_tracks):
        armature.animation_data.nla_tracks.remove(track)

    clip_names = {clip["name"] for clip in clips}
    for action in list(bpy.data.actions):
        if action.name in clip_names:
            bpy.data.actions.remove(action)

    audit_clips = []
    for clip in clips:
        name = clip["name"]
        source = actions[name]
        _reset_pose(armature)
        action = bpy.data.actions.new(name=name)
        action.use_fake_user = True
        action["animationPackId"] = contract["animationPackId"]
        action["skeletonId"] = contract["skeletonId"]
        action["bindPoseId"] = contract["bindPoseId"]
        action["loop"] = bool(clip["loop"])
        action["sourceKind"] = contract["source"]["kind"]
        action["animationProfile"] = profile
        action["rotationSpace"] = source.get("rotation_space", "LOCAL_BONE")
        armature.animation_data.action = action

        keyed_bones = []
        keyframe_count = 0
        for bone_name, keyframes in source["keyframes"].items():
            pose_bone = armature.pose.bones[bone_name]
            armature_space = source.get("rotation_space") == "ARMATURE"
            pose_bone.rotation_mode = "QUATERNION"
            keyed_bones.append(bone_name)
            for frame, location, rotation in keyframes:
                pose_bone.location = (
                    _armature_space_translation(pose_bone, location)
                    if armature_space
                    else _blender_translation(location)
                )
                pose_bone.keyframe_insert(data_path="location", frame=frame, group=bone_name)
                pose_bone.rotation_quaternion = (
                    _armature_space_quaternion(pose_bone, rotation)
                    if armature_space
                    else Euler(rotation, "XYZ").to_quaternion()
                )
                pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=bone_name)
                keyframe_count += 1

        audit_clips.append({
            "name": name,
            "durationFrames": clip["durationFrames"],
            "durationSeconds": clip["durationFrames"] / contract["framesPerSecond"],
            "loop": bool(clip["loop"]),
            "profile": profile,
            "rotationSpace": source.get("rotation_space", "LOCAL_BONE"),
            "keyedBones": sorted(keyed_bones),
            "keyframePoses": keyframe_count,
        })

    armature.animation_data.action = None
    _reset_pose(armature)
    armature["animationPackId"] = contract["animationPackId"]
    armature["animationPackVersion"] = contract["version"]
    armature["animationSourceKind"] = contract["source"]["kind"]
    armature["animationReviewStatus"] = "pending"
    armature["animationProfile"] = profile
    return {
        "animationPackId": contract["animationPackId"],
        "version": contract["version"],
        "framesPerSecond": contract["framesPerSecond"],
        "cost": contract["cost"],
        "source": contract["source"],
        "sourceHashes": [
            {"path": "blender/anim_library.py", "sha256": _sha256(SOURCE_PATH)},
            {
                "path": "blender/canonical_mpfb_animation_library.py",
                "sha256": _sha256(MPFB_SOURCE_PATH),
            },
            {
                "path": "data/body-families/canonical-animation-pack.json",
                "sha256": _sha256(CONTRACT_PATH),
            },
        ],
        "coordinateConversion": contract["coordinateConversion"],
        "profile": profile,
        "clips": audit_clips,
        "lifecycle": contract["lifecycle"],
    }
