"""Generate draft-only, rigid-socket weapon candidates with local Blender.

The hammer prefers the CC0 MakeHuman equipment01 asset when it is installed.
If the pack is unavailable, the script records that fact and builds an original
project fallback. The cleaver is always an original project mesh.
"""

from __future__ import annotations

import argparse
import bmesh
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    try:
        argv = argv[argv.index("--") + 1 :]
    except ValueError:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--asset-root", default=None)
    parser.add_argument("--resolution", type=int, default=640)
    parser.add_argument("--require-preferred-hammer", action="store_true")
    return parser.parse_args(argv)


def sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for blocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(blocks):
            if block.users == 0:
                blocks.remove(block)


def material(name: str, color: tuple[float, float, float, float], metallic: float, roughness: float) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    principled = result.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    return result


def apply_bevel(obj: bpy.types.Object, width: float, segments: int = 2) -> None:
    modifier = obj.modifiers.new("authored_edge_bevel", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def add_cylinder(
    name: str,
    radius: float,
    depth: float,
    location: tuple[float, float, float],
    mat: bpy.types.Material,
    vertices: int = 16,
    rotation: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def add_beveled_box(
    name: str,
    dimensions: tuple[float, float, float],
    location: tuple[float, float, float],
    mat: bpy.types.Material,
    bevel: float,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    apply_bevel(obj, bevel, 3)
    return obj


def add_torus(
    name: str,
    major_radius: float,
    minor_radius: float,
    location: tuple[float, float, float],
    mat: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=20,
        minor_segments=6,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def add_prism(
    name: str,
    points_xz: list[tuple[float, float]],
    thickness: float,
    mat: bpy.types.Material,
    bevel: float = 0.0,
) -> bpy.types.Object:
    count = len(points_xz)
    vertices = [(x, -thickness / 2, z) for x, z in points_xz]
    vertices.extend((x, thickness / 2, z) for x, z in points_xz)
    faces = [list(reversed(range(count))), list(range(count, count * 2))]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append([index, nxt, count + nxt, count + index])
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    if bevel > 0:
        apply_bevel(obj, bevel, 2)
    return obj


def add_uv_sphere(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def authored_hammer(materials: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    parts = []
    parts.append(add_cylinder("maul_ash_shaft", 0.032, 1.08, (0, 0, 0.34), materials["wood"], 20))
    parts.append(add_cylinder("maul_primary_grip", 0.046, 0.42, (0, 0, 0.01), materials["leather"], 20))
    for index, z_value in enumerate((-0.18, -0.08, 0.02, 0.12, 0.22)):
        parts.append(add_torus(f"maul_grip_binding_{index}", 0.047, 0.006, (0, 0, z_value), materials["brass"]))
    parts.append(add_uv_sphere("maul_pommel", (0, 0, -0.225), (0.06, 0.06, 0.075), materials["brass"]))
    parts.append(add_beveled_box("maul_head_core", (0.28, 0.22, 0.23), (0, 0, 0.91), materials["dark_steel"], 0.035))
    parts.append(add_cylinder("maul_left_face", 0.125, 0.16, (-0.21, 0, 0.91), materials["steel"], 12, (0, math.radians(90), 0)))
    parts.append(add_cylinder("maul_right_face", 0.125, 0.16, (0.21, 0, 0.91), materials["steel"], 12, (0, math.radians(90), 0)))
    for side in (-1, 1):
        parts.append(add_torus(
            f"maul_sun_seal_{side}",
            0.074,
            0.012,
            (side * 0.296, 0, 0.91),
            materials["brass"],
        ))
        parts[-1].rotation_euler[1] = math.radians(90)
    parts.append(add_beveled_box("maul_head_collar", (0.1, 0.1, 0.18), (0, 0, 0.75), materials["brass"], 0.018))
    return parts


def authored_cleaver(materials: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    parts = []
    parts.append(add_cylinder("cleaver_tang", 0.03, 0.64, (0.015, 0, 0.08), materials["dark_steel"], 16))
    parts.append(add_cylinder("cleaver_grip", 0.052, 0.46, (0, 0, -0.005), materials["leather"], 20))
    for index, z_value in enumerate((-0.20, -0.10, 0.0, 0.10, 0.20)):
        parts.append(add_torus(f"cleaver_grip_wrap_{index}", 0.052, 0.007, (0, 0, z_value), materials["brass"]))
    parts.append(add_uv_sphere("cleaver_counterweight", (0, 0, -0.255), (0.065, 0.055, 0.075), materials["dark_steel"]))
    guard = add_prism(
        "cleaver_hooked_guard",
        [(-0.18, 0.22), (-0.12, 0.30), (0.14, 0.30), (0.22, 0.23), (0.12, 0.19), (-0.12, 0.19)],
        0.09,
        materials["brass"],
        0.012,
    )
    parts.append(guard)
    blade_points = [
        (-0.075, 0.245),
        (-0.115, 0.88),
        (-0.045, 1.04),
        (0.20, 1.105),
        (0.37, 0.985),
        (0.415, 0.76),
        (0.365, 0.43),
        (0.24, 0.27),
    ]
    parts.append(add_prism("cleaver_broad_blade", blade_points, 0.072, materials["dark_steel"], 0.012))
    edge_points = [
        (0.24, 0.275),
        (0.365, 0.43),
        (0.415, 0.76),
        (0.37, 0.985),
        (0.325, 0.95),
        (0.365, 0.74),
        (0.32, 0.46),
        (0.21, 0.32),
    ]
    parts.append(add_prism("cleaver_honed_edge", edge_points, 0.078, materials["steel"], 0.005))
    fuller_points = [(-0.02, 0.43), (-0.045, 0.86), (0.02, 0.96), (0.22, 0.94), (0.26, 0.86), (0.17, 0.82), (0.03, 0.84)]
    parts.append(add_prism("cleaver_recessed_fuller", fuller_points, 0.079, materials["blackened"], 0.004))
    for index, z_value in enumerate((0.53, 0.69, 0.85)):
        rivet = add_cylinder(
            f"cleaver_blade_rivet_{index}",
            0.025,
            0.088,
            (0.06 + index * 0.045, 0, z_value),
            materials["brass"],
            12,
            (math.radians(90), 0, 0),
        )
        parts.append(rivet)
    return parts


def imported_hammer(asset_root: Path, recipe: dict) -> tuple[list[bpy.types.Object], dict] | tuple[None, dict]:
    preferred = recipe["preferredHammerSource"]
    marker = asset_root / Path(preferred["relativeMarker"])
    preferred_obj = asset_root / Path(preferred["relativeObject"])
    if not marker.is_file():
        return None, {"preferredSourceAvailable": False, "marker": str(marker)}
    object_file = preferred_obj if preferred_obj.is_file() else next(iter(marker.parent.glob("*.obj")), None)
    if not object_file or not object_file.is_file():
        return None, {"preferredSourceAvailable": True, "objectMissing": True, "marker": str(marker)}

    before = set(bpy.context.scene.objects)
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=str(object_file))
    else:
        bpy.ops.import_scene.obj(filepath=str(object_file))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before and obj.type == "MESH"]
    if not imported:
        return None, {"preferredSourceAvailable": True, "importFailed": True, "object": str(object_file)}

    bpy.ops.object.select_all(action="DESELECT")
    for obj in imported:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = imported[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = "culturalibre_cc0_war_hammer"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    dimensions = tuple(obj.dimensions)
    longest_axis = max(range(3), key=lambda index: dimensions[index])
    if longest_axis == 0:
        obj.rotation_euler[1] = math.radians(-90)
    elif longest_axis == 1:
        obj.rotation_euler[0] = math.radians(90)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    scale = 1.24 / max(obj.dimensions)
    obj.scale = (scale, scale, scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    z_values = [vertex.co.z for vertex in obj.data.vertices]
    minimum_z, maximum_z = min(z_values), max(z_values)
    threshold = (maximum_z - minimum_z) * 0.2
    lower = [vertex.co for vertex in obj.data.vertices if vertex.co.z <= minimum_z + threshold]
    upper = [vertex.co for vertex in obj.data.vertices if vertex.co.z >= maximum_z - threshold]
    lower_spread = max((abs(point.x) + abs(point.y) for point in lower), default=0)
    upper_spread = max((abs(point.x) + abs(point.y) for point in upper), default=0)
    if lower_spread > upper_spread:
        obj.rotation_euler[0] = math.radians(180)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    coordinates = [vertex.co for vertex in obj.data.vertices]
    minimum_z = min(point.z for point in coordinates)
    center_x = (min(point.x for point in coordinates) + max(point.x for point in coordinates)) / 2
    center_y = (min(point.y for point in coordinates) + max(point.y for point in coordinates)) / 2
    obj.location = (-center_x, -center_y, -(minimum_z + 0.22))
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return [obj], {
        "preferredSourceAvailable": True,
        "sourceUsed": "makehuman_equipment01_culturalibre_war_hammer",
        "license": preferred["license"],
        "author": preferred["author"],
        "marker": str(marker),
        "object": str(object_file),
        "sourceHashes": {
            "markerSha256": sha256_file(marker),
            "objectSha256": sha256_file(object_file),
        },
    }


def join_parts(parts: list[bpy.types.Object], name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    result = bpy.context.object
    result.name = name
    for polygon in result.data.polygons:
        polygon.use_smooth = False
    return result


def create_semantic_markers(root: bpy.types.Object, weapon: dict) -> dict[str, bpy.types.Object]:
    markers = {}
    handling = weapon["handling"]
    marker_specs = (
        ("secondaryGrip", "ARROWS", 0.10),
        ("strikeHead", "SPHERE", 0.10),
    )
    for role, display_type, display_size in marker_specs:
        spec = handling.get(role)
        if spec is None:
            continue
        marker = bpy.data.objects.new(spec["node"], None)
        bpy.context.collection.objects.link(marker)
        marker.parent = root
        marker.location = Vector(spec["localTranslation"])
        marker.empty_display_type = display_type
        marker.empty_display_size = display_size
        markers[role] = marker
    return markers


def marker_at_local_translation(marker: bpy.types.Object | None, expected: list[float]) -> bool:
    if marker is None:
        return False
    actual = tuple(round(value, 6) for value in marker.location)
    target = tuple(round(float(value), 6) for value in expected)
    return actual == target


def apply_metadata(
    root: bpy.types.Object,
    grip: bpy.types.Object,
    mesh: bpy.types.Object,
    semantic_markers: dict[str, bpy.types.Object],
    weapon: dict,
    recipe: dict,
    source: dict,
) -> None:
    attachment = recipe["attachment"]
    handling = weapon["handling"]
    metadata = {
        "assetId": weapon["assetId"],
        "assetCategory": "weapon",
        "assetSlot": "mainHand",
        "bodyFamily": weapon["bodyFamily"],
        "compatibleBodyVariants": ",".join(weapon["bodyVariants"]),
        "skeletonId": attachment["skeletonId"],
        "bindPoseId": attachment["bindPoseId"],
        "attachmentMode": attachment["mode"],
        "targetSocket": attachment["targetSocket"],
        "socketParentBone": attachment["socketParentBone"],
        "lifecycleStatus": "draft",
        "runtimeReady": False,
        "promotionEligible": False,
        "sourceKind": source.get("sourceUsed", "original_project_mesh"),
        "handedness": handling["handedness"],
        "massClass": handling["massClass"],
    }
    for obj in (root, grip, mesh, *semantic_markers.values()):
        for key, value in metadata.items():
            obj[key] = value
    grip["isAttachmentAnchor"] = True
    grip["gripRole"] = "primary"
    grip["localGripTranslation"] = attachment["localGripTranslation"]
    grip["localGripRotationDegrees"] = attachment["localGripRotationDegrees"]
    secondary_spec = handling.get("secondaryGrip")
    if secondary_spec is not None:
        secondary_grip = semantic_markers["secondaryGrip"]
        secondary_grip["isAttachmentAnchor"] = True
        secondary_grip["gripRole"] = "secondary"
        secondary_grip["targetSocket"] = secondary_spec["targetSocket"]
        secondary_grip["socketParentBone"] = secondary_spec["socketParentBone"]
        secondary_grip["localGripTranslation"] = secondary_spec["localTranslation"]
        root["secondaryGripNode"] = secondary_spec["node"]
    strike_spec = handling.get("strikeHead")
    if strike_spec is not None:
        strike_head = semantic_markers["strikeHead"]
        strike_head["isStrikeHeadMarker"] = True
        strike_head["markerRole"] = "strike_head"
        strike_head["localMarkerTranslation"] = strike_spec["localTranslation"]
        root["strikeHeadNode"] = strike_spec["node"]


def mesh_stats(mesh_obj: bpy.types.Object) -> dict:
    triangles = sum(max(0, len(polygon.vertices) - 2) for polygon in mesh_obj.data.polygons)
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    # glTF round-trip splits vertices at hard-normal/material boundaries. Weld
    # coincident positions in the inspection copy before evaluating topology.
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
    non_manifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.free()
    return {
        "meshCount": 1,
        "drawCalls": max(1, len(mesh_obj.data.materials)),
        "totalTris": triangles,
        "nonManifoldEdges": non_manifold,
    }


def export_weapon(
    root: bpy.types.Object,
    grip: bpy.types.Object,
    semantic_markers: dict[str, bpy.types.Object],
    mesh: bpy.types.Object,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (root, grip, mesh, *semantic_markers.values()):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_animations=False,
        export_skins=False,
        export_extras=True,
        export_apply=True,
        export_yup=True,
        export_draco_mesh_compression_enable=False,
    )
    bpy.ops.object.select_all(action="DESELECT")


def object_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector(tuple(min(point[index] for point in corners) for index in range(3)))
    maximum = Vector(tuple(max(point[index] for point in corners) for index in range(3)))
    return minimum, maximum


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_area_light(name: str, location: Vector, target: Vector, energy: float, size: float) -> None:
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light)
    light.location = location
    point_at(light, target)


def add_axis(name: str, direction: Vector, color: tuple[float, float, float, float]) -> bpy.types.Object:
    axis_material = material(f"{name}_material", color, 0.0, 0.35)
    midpoint = direction * 0.5
    length = direction.length
    axis = add_cylinder(name, 0.008, length, tuple(midpoint), axis_material, 10)
    axis.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return axis


def render_review(mesh_obj: bpy.types.Object, review_dir: Path, resolution: int) -> dict[str, dict]:
    review_dir.mkdir(parents=True, exist_ok=True)
    minimum, maximum = object_bounds(mesh_obj)
    center = (minimum + maximum) * 0.5
    span = max(*(maximum - minimum), 0.2)
    distance = span * 2.4

    camera_data = bpy.data.cameras.new("weapon_review_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span * 1.28
    camera = bpy.data.objects.new("weapon_review_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    world = bpy.context.scene.world or bpy.data.worlds.new("weapon_review_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.018, 0.022, 0.03, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.32
    add_area_light("weapon_key", center + Vector((-distance, -distance, distance)), center, 1100, span)
    add_area_light("weapon_fill", center + Vector((distance, -distance * 0.3, distance * 0.4)), center, 650, span)
    add_area_light("weapon_rim", center + Vector((0, distance, distance * 0.7)), center, 800, span)

    scene = bpy.context.scene
    engines = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    scene.render.resolution_x = max(256, min(resolution, 1536))
    scene.render.resolution_y = scene.render.resolution_x
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"

    views = {
        "front": Vector((0, -distance, 0)),
        "side": Vector((distance, 0, 0)),
        "back": Vector((0, distance, 0)),
        "isometric": Vector((distance * 0.68, -distance * 0.68, distance * 0.32)),
    }
    evidence = {}
    for view_name, offset in views.items():
        camera.location = center + offset
        point_at(camera, center)
        output = review_dir / f"{view_name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        evidence[view_name] = {"path": output.name, "sha256": sha256_file(output)}

    axes = [
        add_axis("qc_socket_axis_x", Vector((0.22, 0, 0)), (0.8, 0.04, 0.03, 1)),
        add_axis("qc_socket_axis_y", Vector((0, 0.22, 0)), (0.03, 0.15, 0.85, 1)),
        add_axis("qc_socket_axis_z", Vector((0, 0, 0.22)), (0.04, 0.8, 0.12, 1)),
    ]
    camera_data.ortho_scale = 0.58
    socket_center = Vector((0, 0, 0))
    camera.location = Vector((0.46, -0.46, 0.30))
    point_at(camera, socket_center)
    output = review_dir / "socket_alignment.png"
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    evidence["socket_alignment"] = {"path": output.name, "sha256": sha256_file(output)}
    for axis in axes:
        bpy.data.objects.remove(axis, do_unlink=True)
    return evidence


def generate_weapon(weapon: dict, recipe: dict, output_root: Path, asset_root: Path | None, resolution: int, require_preferred: bool) -> dict:
    clean_scene()
    materials = {
        "steel": material("forged_steel", (0.29, 0.34, 0.40, 1), 0.88, 0.24),
        "dark_steel": material("blackened_steel", (0.055, 0.065, 0.075, 1), 0.82, 0.31),
        "blackened": material("recessed_black_steel", (0.018, 0.022, 0.027, 1), 0.65, 0.39),
        "brass": material("aged_brass", (0.35, 0.19, 0.045, 1), 0.72, 0.28),
        "wood": material("oiled_ash", (0.18, 0.075, 0.028, 1), 0.03, 0.58),
        "leather": material("wrapped_leather", (0.085, 0.025, 0.014, 1), 0.02, 0.72),
    }
    source = {"sourceUsed": "original_project_mesh", "license": "project-original"}
    parts = None
    if weapon["kind"] == "hammer" and asset_root:
        parts, source = imported_hammer(asset_root, recipe)
    if weapon["kind"] == "hammer" and parts is None:
        if require_preferred:
            raise RuntimeError("The preferred culturalibre_war_hammer CC0 asset is not installed.")
        source = {
            **source,
            "sourceUsed": "original_project_mesh_fallback",
            "license": "project-original",
            "fallbackReason": "preferred CC0 MakeHuman equipment01 hammer was unavailable",
        }
        parts = authored_hammer(materials)
    elif weapon["kind"] == "cleaver":
        parts = authored_cleaver(materials)

    mesh_obj = join_parts(parts, f"{weapon['key']}_mesh")
    root = bpy.data.objects.new(f"{weapon['key']}_root", None)
    bpy.context.collection.objects.link(root)
    grip = bpy.data.objects.new(recipe["attachment"]["gripNode"], None)
    bpy.context.collection.objects.link(grip)
    grip.empty_display_type = "ARROWS"
    grip.empty_display_size = 0.12
    mesh_obj.parent = root
    grip.parent = root
    semantic_markers = create_semantic_markers(root, weapon)
    apply_metadata(root, grip, mesh_obj, semantic_markers, weapon, recipe, source)

    weapon_dir = output_root / weapon["key"]
    weapon_dir.mkdir(parents=True, exist_ok=True)
    output_model = weapon_dir / weapon["outputModel"]
    export_weapon(root, grip, semantic_markers, mesh_obj, output_model)
    model_hash = sha256_file(output_model)

    # Evidence and QC must inspect the serialized GLB, not the authoring scene.
    clean_scene()
    bpy.ops.import_scene.gltf(filepath=str(output_model))
    roundtrip_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    roundtrip_root = bpy.data.objects.get(f"{weapon['key']}_root")
    roundtrip_grip = bpy.data.objects.get(recipe["attachment"]["gripNode"])
    handling = weapon["handling"]
    secondary_spec = handling.get("secondaryGrip")
    strike_spec = handling.get("strikeHead")
    roundtrip_secondary_grip = bpy.data.objects.get(secondary_spec["node"]) if secondary_spec else None
    roundtrip_strike_head = bpy.data.objects.get(strike_spec["node"]) if strike_spec else None
    required_semantic_markers_present = (
        (secondary_spec is None or roundtrip_secondary_grip is not None)
        and (strike_spec is None or roundtrip_strike_head is not None)
    )
    if not roundtrip_meshes or roundtrip_root is None or roundtrip_grip is None or not required_semantic_markers_present:
        raise RuntimeError(f"GLB round-trip lost required nodes for {weapon['assetId']}")
    roundtrip_mesh = max(roundtrip_meshes, key=lambda obj: len(obj.data.vertices))
    review_dir = weapon_dir / "review"
    evidence = render_review(roundtrip_mesh, review_dir, resolution)
    stats = mesh_stats(roundtrip_mesh)
    qc_policy = recipe["qc"]
    checks = {
        "modelWritten": output_model.is_file(),
        "roundTripImported": True,
        "canonicalSocket": roundtrip_root.get("targetSocket") == "socket_hand_R" and roundtrip_grip.get("targetSocket") == "socket_hand_R",
        "gripAtLocalOrigin": tuple(round(value, 6) for value in roundtrip_grip.location) == (0.0, 0.0, 0.0),
        "semanticHandling": (
            roundtrip_root.get("handedness") == handling["handedness"]
            and roundtrip_root.get("massClass") == handling["massClass"]
        ),
        "secondaryGripContract": secondary_spec is None or (
            roundtrip_secondary_grip is not None
            and roundtrip_secondary_grip.parent == roundtrip_root
            and roundtrip_secondary_grip.get("gripRole") == "secondary"
            and roundtrip_secondary_grip.get("targetSocket") == secondary_spec["targetSocket"]
            and roundtrip_secondary_grip.get("socketParentBone") == secondary_spec["socketParentBone"]
            and marker_at_local_translation(roundtrip_secondary_grip, secondary_spec["localTranslation"])
        ),
        "strikeHeadContract": strike_spec is None or (
            roundtrip_strike_head is not None
            and roundtrip_strike_head.parent == roundtrip_root
            and roundtrip_strike_head.get("isStrikeHeadMarker") is True
            and roundtrip_strike_head.get("markerRole") == "strike_head"
            and marker_at_local_translation(roundtrip_strike_head, strike_spec["localTranslation"])
        ),
        "triangleBudget": stats["totalTris"] <= qc_policy["maxTrianglesPerWeapon"],
        "drawCallBudget": stats["drawCalls"] <= qc_policy["maxDrawCallsPerWeapon"],
        "fileSizeBudget": output_model.stat().st_size <= qc_policy["maxFileSizeMb"] * 1024 * 1024,
        "manifoldTopology": stats["nonManifoldEdges"] == 0,
        "reviewEvidenceWritten": set(evidence) == set(qc_policy["requiredReviewViews"]),
        "draftOnly": roundtrip_root.get("runtimeReady") is False and roundtrip_root.get("promotionEligible") is False,
    }
    qc = {
        "schemaVersion": 1,
        "assetId": weapon["assetId"],
        "category": "weapon",
        "model": weapon["outputModel"],
        "modelSha256": model_hash,
        "fileSizeBytes": output_model.stat().st_size,
        **stats,
        "materialChannels": ["baseColor", "roughness", "metallic"],
        "attachmentBinding": {
            "mode": "rigid_socket",
            "skeletonId": "humanoid_game_v2",
            "bindPoseId": "a_pose_v2",
            "targetSocket": "socket_hand_R",
            "socketParentBone": "hand_R",
            "gripNode": recipe["attachment"]["gripNode"],
            "localGripTranslation": [0, 0, 0],
            "verified": checks["canonicalSocket"] and checks["gripAtLocalOrigin"],
            "handedness": handling["handedness"],
            "massClass": handling["massClass"],
            "secondaryGrip": {
                **secondary_spec,
                "verified": checks["secondaryGripContract"],
            } if secondary_spec else None,
            "strikeHead": {
                **strike_spec,
                "verified": checks["strikeHeadContract"],
            } if strike_spec else None,
        },
        "source": source,
        "roundTrip": {
            "reviewedSerializedGlb": True,
            "importedNodeCount": len(bpy.context.scene.objects),
            "rootNode": roundtrip_root.name,
            "gripNode": roundtrip_grip.name,
            "secondaryGripNode": roundtrip_secondary_grip.name if roundtrip_secondary_grip else None,
            "strikeHeadNode": roundtrip_strike_head.name if roundtrip_strike_head else None,
            "serializedModelSha256": model_hash,
        },
        "previewImages": [f"review/{entry['path']}" for entry in evidence.values()],
        "checks": checks,
        "qcPassed": all(checks.values()),
        "lifecycleStatus": "draft",
        "runtimeReady": False,
        "promotionEligible": False,
    }
    qc_path = weapon_dir / weapon["outputModel"].replace(".glb", ".qc.json")
    qc_path.write_text(json.dumps(qc, indent=2) + "\n", encoding="utf-8")
    review = {
        "schemaVersion": 1,
        "assetId": weapon["assetId"],
        "modelSha256": model_hash,
        "reviewStatus": "pending",
        "humanReviewRequired": True,
        "targetSocket": "socket_hand_R",
        "evidenceSource": "serialized_glb_roundtrip_reimport",
        "evidence": evidence,
        "limitations": [
            "Standalone socket alignment is verified; in-hand deformation review awaits generated MPFB pilot bodies.",
            "Draft materials use authored scalar PBR values and have not received final baked normal or occlusion maps.",
        ],
    }
    review_path = weapon_dir / "review.json"
    review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    return {
        "key": weapon["key"],
        "assetId": weapon["assetId"],
        "bodyFamily": weapon["bodyFamily"],
        "model": str(output_model.relative_to(output_root)).replace("\\", "/"),
        "modelSha256": model_hash,
        "qc": str(qc_path.relative_to(output_root)).replace("\\", "/"),
        "review": str(review_path.relative_to(output_root)).replace("\\", "/"),
        "qcPassed": qc["qcPassed"],
        "source": source,
        "lifecycleStatus": "draft",
        "runtimeReady": False,
        "promotionEligible": False,
    }


def validate_handling_contract(weapon: dict) -> None:
    handling = weapon.get("handling")
    if not isinstance(handling, dict):
        raise RuntimeError(f"{weapon['assetId']} is missing its semantic handling contract.")
    if handling.get("handedness") not in {"one_handed", "two_handed"}:
        raise RuntimeError(f"{weapon['assetId']} has an unsupported handedness.")
    if handling.get("massClass") not in {"light", "medium", "heavy"}:
        raise RuntimeError(f"{weapon['assetId']} has an unsupported mass class.")

    secondary = handling.get("secondaryGrip")
    if handling["handedness"] == "two_handed":
        if not isinstance(secondary, dict):
            raise RuntimeError(f"{weapon['assetId']} is two-handed but has no secondary grip marker.")
        if (
            secondary.get("node") != "weapon_grip_socket_hand_L"
            or secondary.get("targetSocket") != "socket_hand_L"
            or secondary.get("socketParentBone") != "hand_L"
            or secondary.get("localTranslation") != [0, 0, 0.3]
        ):
            raise RuntimeError(f"{weapon['assetId']} has an invalid canonical left-hand grip contract.")

    if weapon["kind"] == "hammer":
        strike_head = handling.get("strikeHead")
        if handling["handedness"] != "two_handed" or handling["massClass"] != "heavy":
            raise RuntimeError(f"{weapon['assetId']} must be classified as a two-handed heavy hammer.")
        if not isinstance(strike_head, dict) or strike_head.get("node") != "weapon_strike_head":
            raise RuntimeError(f"{weapon['assetId']} is missing its canonical strike-head marker.")
        if strike_head.get("localTranslation") != [0, 0, 0.91]:
            raise RuntimeError(f"{weapon['assetId']} has an invalid strike-head marker position.")


def main() -> None:
    args = parse_args()
    recipe_path = Path(args.recipe).resolve()
    output_root = Path(args.output_dir).resolve()
    asset_root = Path(args.asset_root).resolve() if args.asset_root else None
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    if recipe["lifecycle"]["promotionEligible"] or recipe["lifecycle"]["runtimeReady"]:
        raise RuntimeError("Weapon pilot recipe must remain draft-only.")
    if recipe["attachment"]["targetSocket"] != "socket_hand_R":
        raise RuntimeError("Weapon pilot must target canonical socket_hand_R.")
    for weapon in recipe["weapons"]:
        validate_handling_contract(weapon)
    output_root.mkdir(parents=True, exist_ok=False)
    results = [
        generate_weapon(weapon, recipe, output_root, asset_root, args.resolution, args.require_preferred_hammer)
        for weapon in recipe["weapons"]
    ]
    run_manifest = {
        "schemaVersion": 1,
        "recipeId": recipe["recipeId"],
        "recipeSha256": sha256_file(recipe_path),
        "generator": "local_blender_weapon_attachment_pilot",
        "blenderVersion": bpy.app.version_string,
        "cost": {"currency": 0, "networkUsed": False, "paidServiceUsed": False},
        "preferredHammerAssetRoot": str(asset_root) if asset_root else None,
        "weapons": results,
        "allQcPassed": all(result["qcPassed"] for result in results),
        "lifecycleStatus": "draft",
        "runtimeReady": False,
        "promotionEligible": False,
    }
    (output_root / "run-manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[weapon-pilot] generated {len(results)} draft weapons at {output_root}")
    if not run_manifest["allQcPassed"]:
        raise RuntimeError("One or more draft weapon QC reports failed.")


if __name__ == "__main__":
    main()
