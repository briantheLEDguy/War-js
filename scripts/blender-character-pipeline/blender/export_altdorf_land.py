"""
Export the supplied Altdorf land blend as a runtime GLB terrain model.

Invocation:
    blender --background blends/altdorf_land.blend --python \
        scripts/blender-character-pipeline/blender/export_altdorf_land.py -- \
        --output public/assets/models/altdorf_land.glb

The source blend is large and uneven. This export pass scales it to the Altdorf
zone footprint and levels a feathered castle pad so the generated castle can be
placed on top without hovering over the hillside.
"""

import argparse
import math
import os
import sys

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    try:
        idx = argv.index("--")
        argv = argv[idx + 1 :]
    except ValueError:
        argv = []

    parser = argparse.ArgumentParser(description="Export Altdorf terrain GLB")
    parser.add_argument("--output", required=True, help="Absolute or repo-relative output .glb path")
    parser.add_argument("--world-size", type=float, default=320.0, help="Target X/Z terrain width in game units")
    parser.add_argument("--castle-x", type=float, default=0.0, help="Castle center X in game units")
    parser.add_argument("--castle-z", type=float, default=-8.0, help="Castle center Z in game units")
    parser.add_argument("--castle-pad-width", type=float, default=184.0, help="Level pad width in game units")
    parser.add_argument("--castle-pad-depth", type=float, default=172.0, help="Level pad depth in game units")
    parser.add_argument("--feather", type=float, default=30.0, help="Blend distance from pad to natural terrain")
    return parser.parse_args(argv)


def ensure_object_mode() -> None:
    try:
        bpy.ops.object.mode_set(mode="OBJECT")
    except RuntimeError:
        pass


def mesh_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mins = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    maxs = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return mins, maxs


def apply_world_transform(obj: bpy.types.Object) -> None:
    obj.data.transform(obj.matrix_world)
    obj.matrix_world.identity()
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)
    obj.scale = (1, 1, 1)


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge0 == edge1:
        return 1.0 if value >= edge1 else 0.0
    t = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def height_at_game_point(obj: bpy.types.Object, x: float, z: float) -> float:
    """Sample the already-scaled Blender mesh at the game-space X/Z point."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mins, maxs = mesh_bounds(obj)
    origin = Vector((x, -z, maxs.z + 100.0))
    hit, location, _normal, _face, _obj, _matrix = bpy.context.scene.ray_cast(
        depsgraph,
        origin,
        Vector((0, 0, -1)),
        distance=(maxs.z - mins.z) + 200.0,
    )
    if not hit:
        return 0.0
    return location.z


def normalize_and_level_terrain(obj: bpy.types.Object, args: argparse.Namespace) -> None:
    apply_world_transform(obj)
    mins, maxs = mesh_bounds(obj)
    center_x = (mins.x + maxs.x) * 0.5
    center_y = (mins.y + maxs.y) * 0.5
    horizontal_size = max(maxs.x - mins.x, maxs.y - mins.y)
    scale = args.world_size / horizontal_size

    for vertex in obj.data.vertices:
        vertex.co.x = (vertex.co.x - center_x) * scale
        vertex.co.y = (vertex.co.y - center_y) * scale
        vertex.co.z = (vertex.co.z - mins.z) * scale

    obj.data.update()
    bpy.context.view_layer.update()

    plateau_height = height_at_game_point(obj, args.castle_x, args.castle_z)
    half_w = args.castle_pad_width * 0.5
    half_d = args.castle_pad_depth * 0.5

    for vertex in obj.data.vertices:
        game_x = vertex.co.x
        game_z = -vertex.co.y
        dx = abs(game_x - args.castle_x)
        dz = abs(game_z - args.castle_z)
        outside_x = max(0.0, dx - half_w)
        outside_z = max(0.0, dz - half_d)
        outside_dist = math.hypot(outside_x, outside_z)

        if dx <= half_w and dz <= half_d:
            blend_to_natural = 0.0
        elif outside_dist <= args.feather:
            blend_to_natural = smoothstep(0.0, args.feather, outside_dist)
        else:
            continue

        vertex.co.z = plateau_height * (1.0 - blend_to_natural) + vertex.co.z * blend_to_natural

    obj.data.update()
    bpy.context.view_layer.update()
    print(
        "[WAR] Altdorf terrain scaled to "
        f"{args.world_size:.1f} game units, castle plateau y={plateau_height:.2f}"
    )


def tune_materials(obj: bpy.types.Object) -> None:
    if not obj.data.materials:
        mat = bpy.data.materials.new("altdorf_land")
        obj.data.materials.append(mat)

    for mat in obj.data.materials:
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if not bsdf:
            continue
        bsdf.inputs["Base Color"].default_value = (0.24, 0.34, 0.16, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.92
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.0


def export_glb(output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        export_animations=False,
        export_skins=False,
        export_apply=True,
        export_yup=True,
        export_draco_mesh_compression_enable=False,
    )


def main() -> None:
    args = parse_args()
    output_path = os.path.abspath(args.output)
    ensure_object_mode()

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        print("ERROR: altdorf_land blend contains no mesh objects")
        sys.exit(1)

    terrain = max(meshes, key=lambda obj: len(obj.data.vertices))
    terrain.name = "altdorf_land_terrain"
    terrain.data.name = "altdorf_land_terrain_mesh"
    normalize_and_level_terrain(terrain, args)
    tune_materials(terrain)
    export_glb(output_path)
    print(f"[WAR] SUCCESS: {output_path}")


if __name__ == "__main__":
    main()
