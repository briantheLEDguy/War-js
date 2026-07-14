"""Shared Blender primitives for the typed modular-character pipeline.

The functions in this module deliberately keep rigid attachment, skinned
wearables, and loose garments separate. They are small building blocks used by
the review fixture generator and can be reused by MPFB-backed generators.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
SKELETON_PATH = PIPELINE_ROOT / "data" / "body-families" / "humanoid_game_v2.skeleton.json"


def load_skeleton_contract() -> dict:
    return json.loads(SKELETON_PATH.read_text(encoding="utf-8"))


def runtime_to_blender(point: tuple[float, float, float]) -> Vector:
    """Convert the runtime X/Y/Z contract to Blender X/Y/Z-up coordinates."""
    x, y, z = point
    return Vector((x, -z, y))


def canonical_runtime_positions(contract: dict) -> dict[str, tuple[Vector, Vector]]:
    """Return deterministic rest endpoints for every canonical contract bone."""
    p: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
        "root": ((0, 0, 0), (0, 0.08, 0)),
        "hips": ((0, 0.82, 0), (0, 0.98, 0)),
        "spine": ((0, 0.98, 0), (0, 1.20, 0)),
        "chest": ((0, 1.20, 0), (0, 1.43, 0)),
        "upper_chest": ((0, 1.43, 0), (0, 1.60, 0)),
        "neck": ((0, 1.60, 0), (0, 1.73, 0)),
        "head": ((0, 1.73, 0), (0, 1.96, 0)),
        "jaw": ((0, 1.80, -0.04), (0, 1.76, -0.13)),
        "eye_L": ((0.055, 1.84, -0.11), (0.055, 1.84, -0.16)),
        "eye_R": ((-0.055, 1.84, -0.11), (-0.055, 1.84, -0.16)),
        "shoulder_L": ((0.16, 1.51, 0), (0.27, 1.43, 0)),
        "upper_arm_L": ((0.27, 1.43, 0), (0.43, 1.25, 0.015)),
        "forearm_L": ((0.43, 1.25, 0.015), (0.57, 1.09, 0.04)),
        "hand_L": ((0.57, 1.09, 0.04), (0.66, 1.06, 0.07)),
        "shoulder_R": ((-0.16, 1.51, 0), (-0.27, 1.43, 0)),
        "upper_arm_R": ((-0.27, 1.43, 0), (-0.43, 1.25, 0.015)),
        "forearm_R": ((-0.43, 1.25, 0.015), (-0.57, 1.09, 0.04)),
        "hand_R": ((-0.57, 1.09, 0.04), (-0.66, 1.06, 0.07)),
        "thigh_L": ((0.11, 0.84, 0), (0.11, 0.48, 0)),
        "shin_L": ((0.11, 0.48, 0), (0.11, 0.12, 0)),
        "foot_L": ((0.11, 0.12, 0), (0.11, 0.035, 0.12)),
        "toe_L": ((0.11, 0.035, 0.12), (0.11, 0.03, 0.22)),
        "thigh_R": ((-0.11, 0.84, 0), (-0.11, 0.48, 0)),
        "shin_R": ((-0.11, 0.48, 0), (-0.11, 0.12, 0)),
        "foot_R": ((-0.11, 0.12, 0), (-0.11, 0.035, 0.12)),
        "toe_R": ((-0.11, 0.035, 0.12), (-0.11, 0.03, 0.22)),
    }
    for side, sign in (("L", 1.0), ("R", -1.0)):
        hand = p[f"hand_{side}"][1]
        for finger_index, finger in enumerate(("thumb", "index", "middle", "ring", "pinky")):
            start = (hand[0] + sign * (0.015 + finger_index * 0.012), hand[1] + 0.005, hand[2] + 0.025)
            if finger == "thumb":
                direction = (sign * 0.035, -0.01, -0.015)
            else:
                direction = (0.0, -0.005, 0.026)
            for segment in range(1, 4):
                head = tuple(start[index] + direction[index] * (segment - 1) for index in range(3))
                tail = tuple(start[index] + direction[index] * segment for index in range(3))
                p[f"{finger}_{segment:02d}_{side}"] = (head, tail)
    return {name: (runtime_to_blender(head), runtime_to_blender(tail)) for name, (head, tail) in p.items()}


def create_canonical_armature(name: str = "humanoid_game_v2") -> bpy.types.Object:
    contract = load_skeleton_contract()
    positions = canonical_runtime_positions(contract)
    armature_data = bpy.data.armatures.new(name)
    armature = bpy.data.objects.new(name, armature_data)
    bpy.context.scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones: dict[str, bpy.types.EditBone] = {}
    contract_bones = {entry["name"]: entry for entry in contract["bones"]}
    for entry in contract["bones"]:
        bone = armature_data.edit_bones.new(entry["name"])
        head, tail = positions[entry["name"]]
        bone.head = head
        bone.tail = tail
        if (tail - head).length < 0.001:
            bone.tail = head + Vector((0, 0, 0.03))
        parent_name = entry.get("parent")
        if parent_name:
            bone.parent = edit_bones[parent_name]
        bone.use_connect = bool(parent_name and entry.get("name") not in {"jaw", "eye_L", "eye_R"})
        edit_bones[entry["name"]] = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    armature["assetKit"] = "canonical_modular_character_v1"
    armature["skeletonId"] = contract["skeletonId"]
    armature["bindPoseId"] = contract["bindPose"]["bindPoseId"]
    armature["canonicalBoneCount"] = len(contract_bones)
    armature.data.pose_position = "REST"
    armature.select_set(False)
    return armature


def apply_transform_hygiene(objects: list[bpy.types.Object]) -> None:
    """Apply authored rotation/scale before binding, as required by the rig contract."""
    bpy.ops.object.select_all(action="DESELECT")
    selected = [obj for obj in objects if obj and obj.type in {"MESH", "ARMATURE"}]
    for obj in selected:
        obj.select_set(True)
    if selected:
        bpy.context.view_layer.objects.active = selected[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.select_all(action="DESELECT")


def cleanup_mesh(obj: bpy.types.Object) -> dict:
    """Remove loose geometry and near-duplicate vertices before fitting."""
    if obj.type != "MESH":
        return {"removedVertices": 0, "removedEdges": 0}
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    before = len(mesh.verts)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=0.0001)
    loose_verts = [vert for vert in mesh.verts if not vert.link_edges]
    if loose_verts:
        bmesh.ops.delete(mesh, geom=loose_verts, context="VERTS")
    loose_edges = len([edge for edge in mesh.edges if not edge.link_faces])
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    return {"removedVertices": max(0, before - len(obj.data.vertices)), "removedEdges": loose_edges}


def _distance_to_segment(point: Vector, start: Vector, end: Vector) -> float:
    axis = end - start
    if axis.length_squared < 1e-8:
        return (point - start).length
    t = max(0.0, min(1.0, (point - start).dot(axis) / axis.length_squared))
    return (point - (start + axis * t)).length


def assign_nearest_bone_weights(mesh: bpy.types.Object, armature: bpy.types.Object, limit: int = 4) -> dict:
    positions = canonical_runtime_positions(load_skeleton_contract())
    for group in list(mesh.vertex_groups):
        mesh.vertex_groups.remove(group)
    groups = {name: mesh.vertex_groups.new(name=name) for name in positions}
    for vertex in mesh.data.vertices:
        candidates = sorted(
            (_distance_to_segment(vertex.co, head, tail), name)
            for name, (head, tail) in positions.items()
            if name != "root"
        )[:limit]
        weights = [(name, 1.0 / max(distance + 0.025, 0.001) ** 2) for distance, name in candidates]
        total = sum(weight for _, weight in weights) or 1.0
        for name, weight in weights:
            groups[name].add([vertex.index], weight / total, "REPLACE")
    bind_skinned_mesh(mesh, armature)
    return limit_and_normalize_weights(mesh, limit)


def bind_skinned_mesh(mesh: bpy.types.Object, armature: bpy.types.Object) -> None:
    modifier = next((item for item in mesh.modifiers if item.type == "ARMATURE"), None)
    if modifier is None:
        modifier = mesh.modifiers.new("canonical_armature_deform", "ARMATURE")
    modifier.object = armature
    mesh.parent = armature
    mesh.parent_type = "OBJECT"
    mesh.matrix_parent_inverse = armature.matrix_world.inverted()
    mesh["skinned"] = True
    mesh["skeletonId"] = "humanoid_game_v2"


def limit_and_normalize_weights(mesh: bpy.types.Object, limit: int = 4) -> dict:
    maximum = 0
    unweighted = 0
    for vertex in mesh.data.vertices:
        influences = [group for group in vertex.groups if group.weight > 1e-8]
        maximum = max(maximum, len(influences))
        influences.sort(key=lambda group: group.weight, reverse=True)
        if not influences:
            unweighted += 1
            continue
        kept = influences[:limit]
        total = sum(group.weight for group in kept) or 1.0
        keep_indices = {group.group for group in kept}
        for group in list(vertex.groups):
            if group.group not in keep_indices:
                mesh.vertex_groups[group.group].remove([vertex.index])
        for group in kept:
            mesh.vertex_groups[group.group].add([vertex.index], group.weight / total, "REPLACE")
    return {"maxInfluencesObserved": min(maximum, limit), "maxInfluencesBeforeLimit": maximum, "unweightedVertices": unweighted}


def transfer_vertex_groups(source: bpy.types.Object, target: bpy.types.Object) -> str:
    """Transfer weights using face interpolation, with a deterministic fallback."""
    method = "data_transfer_nearest_face_interpolated"
    modifier = target.modifiers.new("transfer_canonical_weights", "DATA_TRANSFER")
    modifier.object = source
    modifier.use_vert_data = True
    modifier.data_types_verts = {"VGROUP_WEIGHTS"}
    try:
        modifier.vert_mapping = "POLYINTERP_NEAREST"
        bpy.context.view_layer.objects.active = target
        target.select_set(True)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    except (RuntimeError, TypeError, AttributeError):
        if modifier in target.modifiers:
            target.modifiers.remove(modifier)
        method = "nearest_bone_reference_fallback"
        assign_nearest_bone_weights(target, next((item for item in source.modifiers if item.type == "ARMATURE")).object)
    return method


def add_surface_deform_fitting(source: bpy.types.Object, target: bpy.types.Object) -> dict:
    """Add Blender's surface-driven fitting path for garments needing stronger conformity."""
    modifier = target.modifiers.new("surface_deform_fit", "SURFACE_DEFORM")
    modifier.target = source
    target["fitMethod"] = "surface_deform"
    target["surfaceDeformBindRequired"] = True
    return {"modifier": modifier.name, "target": source.name, "bindRequired": True}


def add_body_region_mask(body: bpy.types.Object, mask_id: str, lower_z: float = 0.98, upper_z: float = 1.62) -> dict:
    group = body.vertex_groups.get(f"body_mask_{mask_id}") or body.vertex_groups.new(name=f"body_mask_{mask_id}")
    indices = [vertex.index for vertex in body.data.vertices if lower_z <= vertex.co.z <= upper_z]
    if indices:
        group.add(indices, 1.0, "REPLACE")
    modifier = body.modifiers.new(f"mask_{mask_id}", "MASK")
    modifier.vertex_group = group.name
    # Keep the reversible body mask above Armature in the authored stack so
    # Blender's glTF exporter still emits the body mesh with its canonical skin.
    bpy.context.view_layer.objects.active = body
    while body.modifiers.find(modifier.name) > 0:
        bpy.ops.object.modifier_move_up(modifier=modifier.name)
    body[f"bodyMask:{mask_id}"] = group.name
    return {"maskId": mask_id, "vertexGroup": group.name, "vertexCount": len(indices), "modifier": modifier.name}


def add_corrective_smoothing(mesh: bpy.types.Object) -> bool:
    try:
        modifier = mesh.modifiers.new("deformation_cleanup", "CORRECTIVE_SMOOTH")
        modifier.factor = 0.35
        return True
    except (RuntimeError, TypeError):
        return False


def add_loose_garment_stack(mesh: bpy.types.Object, armature: bpy.types.Object, pin_group: str = "garment_pin") -> dict:
    pin = mesh.vertex_groups.get(pin_group) or mesh.vertex_groups.new(name=pin_group)
    top_vertices = [vertex.index for vertex in mesh.data.vertices if vertex.co.z > 1.45]
    if top_vertices:
        pin.add(top_vertices, 1.0, "REPLACE")
    bind_skinned_mesh(mesh, armature)
    cloth = mesh.modifiers.new("pinned_cloth", "CLOTH")
    cloth.settings.vertex_group_mass = pin.name
    mesh["looseGarment"] = True
    mesh["clothModifierBelowArmature"] = mesh.modifiers.find(cloth.name) > mesh.modifiers.find("canonical_armature_deform")
    return {"pinGroup": pin.name, "pinnedVertices": len(top_vertices), "modifier": cloth.name}


def add_socket(armature: bpy.types.Object, name: str, bone_name: str, translation=(0.0, 0.0, 0.0), rotation_degrees=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    socket = bpy.data.objects.new(name, None)
    socket.empty_display_type = "ARROWS"
    socket.empty_display_size = 0.06
    bpy.context.scene.collection.objects.link(socket)
    socket.parent = armature
    socket.parent_type = "BONE"
    socket.parent_bone = bone_name
    socket.location = translation
    socket.rotation_mode = "XYZ"
    socket.rotation_euler = tuple(math.radians(value) for value in rotation_degrees)
    socket["socketId"] = name
    socket["parentBone"] = bone_name
    return socket


def add_canonical_sockets(armature: bpy.types.Object) -> list[bpy.types.Object]:
    contract = load_skeleton_contract()
    sockets = [
        add_socket(armature, item["name"], item["parentBone"], item["translation"], item["rotationDegrees"])
        for item in contract["sockets"]
    ]
    sockets.extend([
        add_socket(armature, "socket_belt_L", "hips", (0.16, 0.0, 0.02)),
        add_socket(armature, "socket_belt_R", "hips", (-0.16, 0.0, 0.02)),
    ])
    return sockets


def attach_rigid_to_socket(item_root: bpy.types.Object, socket: bpy.types.Object, offset_profile: str) -> None:
    item_root.parent = socket
    item_root.matrix_parent_inverse = socket.matrix_world.inverted()
    item_root["attachmentMode"] = "rigid_socket"
    item_root["targetSocket"] = socket.name
    item_root["offsetProfile"] = offset_profile


def evaluated_bvh(obj: bpy.types.Object) -> BVHTree | None:
    if obj.type != "MESH":
        return None
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        triangles = [tuple(triangle.vertices) for triangle in mesh.loop_triangles]
        return BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=1e-6)
    finally:
        evaluated.to_mesh_clear()


def bvh_overlap_count(left: bpy.types.Object, right: bpy.types.Object) -> int:
    left_bvh = evaluated_bvh(left)
    right_bvh = evaluated_bvh(right)
    if not left_bvh or not right_bvh:
        return 0
    return len(left_bvh.overlap(right_bvh) or [])
