"""Audit equipped-character penetrations after GLB serialization.

This is deliberately separate from generation and promotion. It imports the
same combined runtime GLB used for review, evaluates bind and animated poses,
and emits measurements without repairing or deleting an asset.

Two complementary checks are used:

* Armor-to-body penetration samples evaluated armor vertices against the
  nearest outward-facing triangle on the primary skin mesh. Small isolated
  signed-distance errors are tolerated; deep or widespread incursions fail.
* Armor-to-armor intersections use exact BVH triangle overlap. Named adjacent
  layers have a larger seam allowance, but extensive crossings still fail.

The signed-distance method assumes consistently outward body normals and is a
surface-clearance screen, not a full volumetric collision simulation. Visual
stress-pose review remains required before promotion.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


DEFAULT_POLICY = (
    Path(__file__).resolve().parent.parent / "data" / "armor-clearance-policy.json"
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Combined equipped runtime GLB")
    parser.add_argument("--report", required=True, help="JSON report destination")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument(
        "--poses",
        default="bind,idle",
        help="Comma-separated bind pose and/or imported action names",
    )
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pair_key(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted((left, right)))


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    bpy.ops.import_scene.gltf(filepath=str(path))


def set_pose(rig: bpy.types.Object, pose_name: str) -> dict[str, Any]:
    rig.animation_data_create()
    if pose_name == "bind":
        rig.animation_data.action = None
        rig.data.pose_position = "REST"
        for bone in rig.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        bpy.context.scene.frame_set(0)
        bpy.context.view_layer.update()
        return {"name": "bind", "frame": 0, "action": None}

    action = bpy.data.actions.get(pose_name)
    if action is None:
        raise RuntimeError(f"Combined GLB does not contain requested action: {pose_name}")
    rig.data.pose_position = "POSE"
    rig.animation_data.action = action
    first, last = action.frame_range
    frame = round((first + last) * 0.5)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {
        "name": pose_name,
        "frame": frame,
        "action": action.name,
        "frameRange": [first, last],
    }


@dataclass
class WorldMesh:
    name: str
    slot: str | None
    vertices: list[Vector]
    triangles: list[tuple[int, int, int]]
    bvh: BVHTree
    signed_volume: float


def evaluated_world_mesh(obj: bpy.types.Object) -> WorldMesh:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
    try:
        transform = evaluated.matrix_world
        vertices = [transform @ vertex.co for vertex in mesh.vertices]
        mesh.calc_loop_triangles()
        triangles = [tuple(triangle.vertices) for triangle in mesh.loop_triangles]
        triangles = [
            triangle
            for triangle in triangles
            if (
                vertices[triangle[1]] - vertices[triangle[0]]
            ).cross(
                vertices[triangle[2]] - vertices[triangle[0]]
            ).length_squared > 1e-18
        ]
        signed_volume = sum(
            vertices[a].dot(vertices[b].cross(vertices[c]))
            for a, b, c in triangles
        ) / 6.0
        # BVH face normals follow winding. Normalise negative-volume closed
        # meshes so the nearest-surface sign consistently means outside.
        if signed_volume < 0.0:
            triangles = [(a, c, b) for a, b, c in triangles]
        bvh = BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=1e-7)
        if bvh is None:
            raise RuntimeError(f"Could not build BVH for {obj.name}")
        return WorldMesh(
            name=obj.name,
            slot=str(obj.get("armorSlot")) if obj.get("armorSlot") else None,
            vertices=vertices,
            triangles=triangles,
            bvh=bvh,
            signed_volume=signed_volume,
        )
    finally:
        evaluated.to_mesh_clear()


def audit_body_penetration(
    armor: WorldMesh,
    body: WorldMesh,
    policy: dict[str, Any],
) -> dict[str, Any]:
    severe_depth = float(policy["severeDepthMeters"])
    hard_depth = float(policy["hardMaxDepthMeters"])
    probe_distance = float(policy["maxProbeDistanceMeters"])
    severe_depths: list[float] = []
    probed = 0
    for point in armor.vertices:
        nearest = body.bvh.find_nearest(point, probe_distance)
        if nearest[0] is None or nearest[1] is None:
            continue
        location, normal, _triangle_index, distance = nearest
        probed += 1
        signed_distance = (point - location).dot(normal.normalized())
        if signed_distance < -severe_depth:
            severe_depths.append(-signed_distance)

    vertex_count = len(armor.vertices)
    allowed = max(
        int(policy["allowedSevereVertexCount"]),
        math.ceil(vertex_count * float(policy["allowedSevereVertexRatio"])),
    )
    maximum = max(severe_depths, default=0.0)
    passed = len(severe_depths) <= allowed and maximum <= hard_depth
    return {
        "slot": armor.slot,
        "mesh": armor.name,
        "vertexCount": vertex_count,
        "probedVertexCount": probed,
        "severeVertexCount": len(severe_depths),
        "severeVertexRatio": len(severe_depths) / max(vertex_count, 1),
        "maxPenetrationMeters": maximum,
        "meanSeverePenetrationMeters": (
            sum(severe_depths) / len(severe_depths) if severe_depths else 0.0
        ),
        "allowedSevereVertices": allowed,
        "thresholds": {
            "severeDepthMeters": severe_depth,
            "hardMaxDepthMeters": hard_depth,
        },
        "passed": passed,
    }


def audit_armor_pair(
    left: WorldMesh,
    right: WorldMesh,
    policy: dict[str, Any],
    intentional_pairs: set[tuple[str, str]],
) -> dict[str, Any]:
    key = pair_key(str(left.slot), str(right.slot))
    intentional = key in intentional_pairs
    thresholds = policy["intentionalLayer" if intentional else "default"]
    overlaps = left.bvh.overlap(right.bvh) or []
    unique_left = len({row[0] for row in overlaps})
    unique_right = len({row[1] for row in overlaps})
    ratio_left = unique_left / max(len(left.triangles), 1)
    ratio_right = unique_right / max(len(right.triangles), 1)
    unique_ratio = max(ratio_left, ratio_right)
    overlap_count = len(overlaps)
    passed = (
        overlap_count <= int(thresholds["hardMaxOverlapPairs"])
        and (
            overlap_count <= int(thresholds["maxOverlapPairs"])
            or unique_ratio <= float(thresholds["maxUniqueTriangleRatio"])
        )
    )
    contact_points = [
        point
        for triangle_index in {row[0] for row in overlaps}
        for point in (left.vertices[index] for index in left.triangles[triangle_index])
    ] + [
        point
        for triangle_index in {row[1] for row in overlaps}
        for point in (right.vertices[index] for index in right.triangles[triangle_index])
    ]
    contact_bounds = None
    if contact_points:
        minimum = [min(point[axis] for point in contact_points) for axis in range(3)]
        maximum = [max(point[axis] for point in contact_points) for axis in range(3)]
        contact_bounds = {
            "minimum": minimum,
            "maximum": maximum,
            "extent": [maximum[axis] - minimum[axis] for axis in range(3)],
        }
    return {
        "slots": list(key),
        "meshes": [left.name, right.name],
        "classification": "intentionalLayer" if intentional else "default",
        "triangleCounts": [len(left.triangles), len(right.triangles)],
        "overlapPairCount": overlap_count,
        "uniqueOverlapTriangles": [unique_left, unique_right],
        "uniqueTriangleRatios": [ratio_left, ratio_right],
        "maxUniqueTriangleRatio": unique_ratio,
        "contactBounds": contact_bounds,
        "thresholds": thresholds,
        "passed": passed,
    }


def audit_pose(
    pose_info: dict[str, Any],
    body_obj: bpy.types.Object,
    armor_objects: list[bpy.types.Object],
    policy: dict[str, Any],
) -> dict[str, Any]:
    body = evaluated_world_mesh(body_obj)
    armors = [evaluated_world_mesh(obj) for obj in armor_objects]
    intentional_pairs = {
        pair_key(str(row[0]), str(row[1]))
        for row in policy["armorIntersection"]["intentionalLayerPairs"]
    }
    body_rows = [
        audit_body_penetration(
            armor,
            body,
            policy["bodyPenetration"],
        )
        for armor in armors
    ]
    pair_rows = [
        audit_armor_pair(
            armors[left_index],
            armors[right_index],
            policy["armorIntersection"],
            intentional_pairs,
        )
        for left_index in range(len(armors))
        for right_index in range(left_index + 1, len(armors))
    ]
    failing_body = [row["slot"] for row in body_rows if not row["passed"]]
    failing_pairs = [row["slots"] for row in pair_rows if not row["passed"]]
    return {
        "pose": pose_info,
        "primaryBodyMesh": {
            "name": body.name,
            "vertexCount": len(body.vertices),
            "triangleCount": len(body.triangles),
            "signedVolume": body.signed_volume,
            "windingWasReversedForAudit": body.signed_volume < 0.0,
        },
        "bodyPenetration": body_rows,
        "armorIntersections": pair_rows,
        "summary": {
            "failingBodySlots": failing_body,
            "failingArmorPairs": failing_pairs,
            "bodyFailureCount": len(failing_body),
            "armorPairFailureCount": len(failing_pairs),
        },
        "passed": not failing_body and not failing_pairs,
    }


def main() -> None:
    args = parse_args()
    model = Path(args.model).resolve()
    report_path = Path(args.report).resolve()
    policy_path = Path(args.policy).resolve()
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    poses = [value.strip() for value in args.poses.split(",") if value.strip()]
    if not poses:
        raise RuntimeError("At least one pose is required")

    clear_scene()
    import_glb(model)
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(rigs) != 1:
        raise RuntimeError(f"Expected one runtime armature; found {len(rigs)}")
    rig = rigs[0]
    armor_objects = sorted(
        (
            obj for obj in bpy.context.scene.objects
            if obj.type == "MESH" and obj.get("assetCategory") == "armor"
        ),
        key=lambda obj: str(obj.get("armorSlot", "")),
    )
    if len(armor_objects) != 9:
        raise RuntimeError(f"Expected nine equipped armor meshes; found {len(armor_objects)}")
    primary_body_candidates = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.get("assetCategory") == "characterBody"
    ]
    if not primary_body_candidates:
        raise RuntimeError("Combined GLB has no characterBody mesh")
    primary_body = max(primary_body_candidates, key=lambda obj: len(obj.data.vertices))

    pose_reports = []
    for pose_name in poses:
        pose_info = set_pose(rig, pose_name)
        pose_reports.append(
            audit_pose(pose_info, primary_body, armor_objects, policy)
        )

    report = {
        "schemaVersion": 1,
        "auditKind": "equipped_character_clearance",
        "model": str(model),
        "modelSha256": sha256(model),
        "policy": {
            "path": str(policy_path),
            "sha256": sha256(policy_path),
            "policyId": policy["policyId"],
            "schemaVersion": policy["schemaVersion"],
        },
        "poses": pose_reports,
        "limitations": [
            "nearest_normal_sign_assumes_consistent_outward_primary_body_normals",
            "vertex_sampling_can_miss_a_crossing_that_occurs_only_inside_large_triangles",
            "bvh_overlap_counts_are_topology_density_dependent",
            "intentional_layer_allowances_do_not_replace_human_visual_review",
        ],
        "passed": all(row["passed"] for row in pose_reports),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("[armor-clearance-audit] " + json.dumps({
        "model": str(model),
        "report": str(report_path),
        "poses": poses,
        "passed": report["passed"],
        "failures": {
            row["pose"]["name"]: row["summary"]
            for row in pose_reports
        },
    }))


if __name__ == "__main__":
    main()
