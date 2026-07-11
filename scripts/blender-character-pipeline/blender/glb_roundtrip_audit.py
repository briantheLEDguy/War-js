"""Validate a generated GLB against an anatomical source scene after re-import."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector


def evaluated_model_stats(meshes: list[bpy.types.Object]) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    triangles = 0
    vertices = 0
    skinned_meshes = 0
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            triangles += len(mesh.loop_triangles)
            vertices += len(mesh.vertices)
            points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
        if any(modifier.type == "ARMATURE" for modifier in obj.modifiers):
            skinned_meshes += 1
    if not points:
        raise RuntimeError("Round-trip audit has no evaluated mesh vertices")
    minimum = Vector(tuple(min(point[index] for point in points) for index in range(3)))
    maximum = Vector(tuple(max(point[index] for point in points) for index in range(3)))
    return {
        "meshNames": sorted(obj.name for obj in meshes),
        "meshCount": len(meshes),
        "skinnedMeshCount": skinned_meshes,
        "vertices": vertices,
        "triangles": triangles,
        "boundsMin": list(minimum),
        "boundsMax": list(maximum),
        "boundsCenter": list((minimum + maximum) * 0.5),
        "boundsExtent": list(maximum - minimum),
    }


def reset_armature_to_bind(armature: bpy.types.Object) -> None:
    armature.data.pose_position = "POSE"
    if armature.animation_data:
        armature.animation_data.action = None
        for track in armature.animation_data.nla_tracks:
            track.mute = True
    for pose_bone in armature.pose.bones:
        pose_bone.matrix_basis = Matrix.Identity(4)


def roundtrip_bind_audit(output: Path, source_meshes: list[bpy.types.Object], source_rig: bpy.types.Object) -> dict:
    """Re-import the GLB and compare its evaluated bind silhouette to the source."""
    for armature in [source_rig]:
        reset_armature_to_bind(armature)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    expected = evaluated_model_stats(source_meshes)

    existing_objects = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(output))
    imported_objects = [obj for obj in bpy.data.objects if obj not in existing_objects]
    imported_armatures = [obj for obj in imported_objects if obj.type == "ARMATURE"]
    imported_meshes = [
        obj
        for obj in imported_objects
        if obj.type == "MESH" and any(modifier.type == "ARMATURE" for modifier in obj.modifiers)
    ]
    if len(imported_armatures) != 1:
        raise RuntimeError(f"Round-trip import produced {len(imported_armatures)} armatures; expected one")

    for armature in imported_armatures:
        reset_armature_to_bind(armature)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    observed = evaluated_model_stats(imported_meshes)

    expected_extent = Vector(expected["boundsExtent"])
    observed_extent = Vector(observed["boundsExtent"])
    expected_center = Vector(expected["boundsCenter"])
    observed_center = Vector(observed["boundsCenter"])
    extent_delta = max(abs(expected_extent[index] - observed_extent[index]) for index in range(3))
    center_delta = max(abs(expected_center[index] - observed_center[index]) for index in range(3))
    tolerance = max(0.002, max(expected_extent) * 0.005)
    checks = {
        "meshCountMatches": observed["meshCount"] == expected["meshCount"],
        "allMeshesRemainSkinned": observed["skinnedMeshCount"] == expected["skinnedMeshCount"],
        "triangleCountMatches": observed["triangles"] == expected["triangles"],
        "boneCountMatches": len(imported_armatures[0].data.bones) == len(source_rig.data.bones),
        "bindBoundsMatch": extent_delta <= tolerance and center_delta <= tolerance,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "expected": expected,
        "observed": observed,
        "boneCountExpected": len(source_rig.data.bones),
        "boneCountObserved": len(imported_armatures[0].data.bones),
        "maximumExtentDelta": extent_delta,
        "maximumCenterDelta": center_delta,
        "tolerance": tolerance,
    }


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    source_rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE" and obj.get("skeletonId")]
    source_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.get("assetId")]
    if len(source_rigs) != 1 or not source_meshes:
        raise RuntimeError("The loaded authoring scene does not contain one metadata-bound rig and its meshes")
    report = roundtrip_bind_audit(Path(args.model).resolve(), source_meshes, source_rigs[0])
    report_path = Path(args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("[glb-roundtrip] " + json.dumps({"passed": report["passed"], "report": str(report_path)}))
    if not report["passed"]:
        raise RuntimeError(f"GLB round-trip bind audit failed: {report['checks']}")


if __name__ == "__main__":
    main()
