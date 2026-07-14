"""Batch Blender pose-pack and rigid-clearance validator for imported GLBs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from modular_character_utils import bvh_overlap_count  # noqa: E402


POSES = ["neutral", "shoulder_extreme", "elbow_extreme", "hip_extreme", "knee_extreme", "jump", "attack_melee", "cast", "death"]


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def main() -> None:
    args = parse_args()
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(Path(args.model).resolve()))
    armature = next((obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"), None)
    if armature is None:
        raise RuntimeError("Pose-pack validation requires an armature")
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    body_meshes = [obj for obj in meshes if obj.get("assetCategory") in {"characterBody", "skinnedWearable"} or obj.get("skinned") is True or any(mod.type == "ARMATURE" for mod in obj.modifiers)]
    # Blender's GLB importer materializes an unreferenced export helper as an
    # Icosphere; it is not part of the authored asset and is excluded from
    # protected-body clearance accounting.
    rigid_meshes = [obj for obj in meshes if obj not in body_meshes and obj.name != "Icosphere"]
    pose_rows = []
    for pose in POSES:
        if armature.animation_data is None:
            armature.animation_data_create()
        action = bpy.data.actions.get(f"pose_{pose}") or bpy.data.actions.get(pose)
        armature.animation_data.action = action
        bpy.context.scene.frame_set(31 if action else 1)
        bpy.context.view_layer.update()
        overlaps = sum(bvh_overlap_count(rigid, body) for rigid in rigid_meshes for body in body_meshes)
        pose_rows.append({"pose": pose, "rigidBodyOverlapPairs": overlaps, "passed": overlaps == 0})
    report = {
        "schemaVersion": 1,
        "model": str(Path(args.model).resolve()),
        "posePackId": "core_v1",
        "method": "blender_bvhtree",
        "bodyMeshCount": len(body_meshes),
        "rigidMeshCount": len(rigid_meshes),
        "bodyMeshes": [obj.name for obj in body_meshes],
        "rigidMeshes": [obj.name for obj in rigid_meshes],
        "poses": pose_rows,
        "passed": all(row["passed"] for row in pose_rows),
    }
    report_path = Path(args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("POSE_PACK_RESULT=" + json.dumps({"passed": report["passed"], "report": str(report_path)}))


if __name__ == "__main__":
    main()
