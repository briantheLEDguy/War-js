"""
Blender headless static asset generator for War-js.

Invocation:
    blender --background --python generate_static_asset.py -- \
        --asset gate \
        --output /absolute/path/to/public/assets/models/gate.glb \
        --spec /absolute/path/to/data/static_asset_spec.json
"""

import argparse
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
from export_utils import normalize_y_up_scene_to_blender_z_up


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    try:
        idx = argv.index("--")
        argv = argv[idx + 1:]
    except ValueError:
        argv = []

    parser = argparse.ArgumentParser(description="War-js static GLB generator")
    parser.add_argument("--asset", required=True, help="Static asset key from static_asset_spec.json")
    parser.add_argument("--output", required=True, help="Absolute path for output .glb")
    parser.add_argument("--spec", required=True, help="Path to static_asset_spec.json")
    parser.add_argument("--asset-id", default=None, help="Neutral manifest assetId for GLTF extras")
    parser.add_argument("--asset-kit", default=None, help="Neutral manifest kit/profile key for GLTF extras")
    parser.add_argument("--asset-category", default=None, help="Neutral manifest category for GLTF extras")
    parser.add_argument("--asset-slot", default=None, help="Optional neutral slot for GLTF extras")
    return parser.parse_args(argv)


def hex_to_linear(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (r ** 2.2, g ** 2.2, b ** 2.2, 1.0)


def make_material(name: str, hex_color: str, roughness=0.7, metallic=0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex_to_linear(hex_color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def add_mesh_obj(
    name: str,
    mesh: bpy.types.Mesh,
    mat: bpy.types.Material | None = None,
    location=(0, 0, 0),
    rotation=(0, 0, 0),
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    if mat:
        obj.data.materials.append(mat)
    return obj


def create_empty(name: str, location=(0, 0, 0)) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.2
    obj.location = location
    return obj


def parent_to(parent: bpy.types.Object, children: list[bpy.types.Object]) -> None:
    for child in children:
        child.parent = parent
        child.matrix_parent_inverse = parent.matrix_world.inverted()


def create_box(
    name: str,
    size: tuple,
    mat: bpy.types.Material,
    location=(0, 0, 0),
    rotation=(0, 0, 0),
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    return add_mesh_obj(name, mesh, mat, location, rotation)


def create_cylinder(
    name: str,
    radius: float,
    depth: float,
    segments: int,
    mat: bpy.types.Material,
    location=(0, 0, 0),
    rotation=(0, 0, 0),
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=depth,
    )
    bm.to_mesh(mesh)
    bm.free()
    obj = add_mesh_obj(name, mesh, mat, location, (rotation[0] - math.pi / 2, rotation[1], rotation[2]))
    return obj


def create_cone(
    name: str,
    radius1: float,
    radius2: float,
    depth: float,
    segments: int,
    mat: bpy.types.Material,
    location=(0, 0, 0),
    rotation=(0, 0, 0),
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius1,
        radius2=radius2,
        depth=depth,
    )
    bm.to_mesh(mesh)
    bm.free()
    return add_mesh_obj(name, mesh, mat, location, (rotation[0] - math.pi / 2, rotation[1], rotation[2]))


def shade_smooth(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        if obj.type != "MESH":
            continue
        for poly in obj.data.polygons:
            poly.use_smooth = True


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes) + list(bpy.data.materials):
        bpy.data.batch_remove([block])


def apply_asset_metadata(args: argparse.Namespace) -> None:
    metadata = {
        "assetId": args.asset_id,
        "assetKit": args.asset_kit,
        "assetCategory": args.asset_category,
        "assetSlot": args.asset_slot,
    }
    for obj in bpy.context.scene.objects:
        if obj.type not in {"MESH", "EMPTY", "ARMATURE"}:
            continue
        for key, value in metadata.items():
            if value:
                obj[key] = value


def build_dummy(spec: dict) -> list[bpy.types.Object]:
    wood = make_material("dummy_wood", spec["wood"], roughness=0.9)
    iron = make_material("dummy_iron", spec["iron"], roughness=0.45, metallic=0.6)
    cloth = make_material("dummy_cloth", spec["cloth"], roughness=0.85)
    paint = make_material("dummy_paint", spec["paint"], roughness=0.75)

    base = create_cylinder("iron_shod_base", 0.55, 0.16, 24, iron, location=(0, 0.08, 0))
    asset_root = create_empty("dummy_export_root")
    root = create_empty("dummy_anim_root")
    objs = [
        base,
        create_cylinder("timber_post", 0.09, 1.75, 14, wood, location=(0, 0.96, 0)),
        create_box("arm_crossbar", (1.05, 0.1, 0.12), wood, location=(0, 1.3, 0)),
        create_box("lower_crossbar", (0.78, 0.08, 0.1), wood, location=(0, 0.55, 0)),
        create_box("padded_target", (0.58, 0.68, 0.2), cloth, location=(0, 0.93, 0.08)),
        create_box("iron_band_top", (0.65, 0.08, 0.24), iron, location=(0, 1.22, 0.1)),
        create_box("iron_band_bottom", (0.65, 0.08, 0.24), iron, location=(0, 0.64, 0.1)),
        create_box("target_slash", (0.68, 0.07, 0.25), paint, location=(0, 0.98, 0.13), rotation=(0, 0, 0.55)),
        create_box("target_cross", (0.07, 0.72, 0.25), paint, location=(0, 0.94, 0.14)),
        create_cone("battered_helm", 0.2, 0.09, 0.22, 14, iron, location=(0, 1.78, 0)),
        create_box("hanging_cloth_L", (0.12, 0.38, 0.045), cloth, location=(-0.36, 0.76, 0.15), rotation=(0, 0, -0.18)),
        create_box("hanging_cloth_R", (0.12, 0.34, 0.045), cloth, location=(0.34, 0.74, 0.15), rotation=(0, 0, 0.16)),
    ]
    parent_to(root, [obj for obj in objs if obj is not base])
    parent_to(asset_root, [base, root])
    animate_dummy(root)
    shade_smooth(objs)
    return objs


def push_action_to_nla(obj: bpy.types.Object, action: bpy.types.Action, name: str, end_frame: int, start_frame: int = 1) -> None:
    obj.animation_data.action = action
    track = obj.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, start_frame, action)
    strip.action_frame_start = 1
    strip.action_frame_end = end_frame
    strip.frame_start = start_frame
    strip.frame_end = start_frame + end_frame - 1
    strip.extrapolation = "NOTHING"
    strip.blend_type = "REPLACE"


def animate_dummy(root: bpy.types.Object) -> None:
    root.animation_data_create()
    root.rotation_mode = "XYZ"

    idle = bpy.data.actions.new("idle")
    idle.use_fake_user = True
    root.animation_data.action = idle
    for frame, rot_z in [(1, -0.015), (30, 0.015), (60, -0.015)]:
        root.rotation_euler = (0, 0, rot_z)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)
    push_action_to_nla(root, idle, "idle", 60)

    hit = bpy.data.actions.new("hit_react")
    hit.use_fake_user = True
    root.animation_data.action = hit
    for frame, rot_x, rot_z in [
        (1, 0, 0),
        (4, -0.22, 0.08),
        (10, 0.12, -0.05),
        (18, -0.06, 0.025),
        (28, 0, 0),
    ]:
        root.rotation_euler = (rot_x, 0, rot_z)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)
    push_action_to_nla(root, hit, "hit_react", 28)
    root.animation_data.action = None


def build_gate(spec: dict) -> list[bpy.types.Object]:
    stone = make_material("gate_stone", spec["stone"], roughness=0.85)
    dark_stone = make_material("gate_dark_stone", spec["darkStone"], roughness=0.9)
    iron = make_material("gate_iron", spec["iron"], roughness=0.45, metallic=0.75)
    wood = make_material("gate_wood", spec["wood"], roughness=0.82)
    trim = make_material("gate_trim", spec["trim"], roughness=0.55, metallic=0.4)

    objs: list[bpy.types.Object] = []
    for x in (-1.45, 1.45):
        objs.extend([
            create_box(f"tower_block_low_{x}", (0.7, 1.6, 0.7), stone, location=(x, 0.8, 0)),
            create_box(f"tower_block_high_{x}", (0.82, 0.35, 0.82), dark_stone, location=(x, 1.78, 0)),
            create_cone(f"tower_roof_{x}", 0.55, 0.18, 0.85, 4, trim, location=(x, 2.38, 0), rotation=(0, 0, math.pi / 4)),
        ])

    objs.extend([
        create_box("arch_left", (0.5, 1.85, 0.42), stone, location=(-0.58, 0.92, 0)),
        create_box("arch_right", (0.5, 1.85, 0.42), stone, location=(0.58, 0.92, 0)),
        create_box("arch_top", (1.7, 0.38, 0.42), stone, location=(0, 1.65, 0)),
        create_box("portcullis_top", (1.05, 0.14, 0.08), iron, location=(0, 1.42, 0.24)),
    ])

    for x in (-0.36, -0.18, 0, 0.18, 0.36):
        objs.append(create_box(f"portcullis_bar_{x}", (0.035, 1.05, 0.035), iron, location=(x, 0.76, 0.25)))

    for x in (-0.25, 0.25):
        objs.append(create_box(f"gate_door_{x}", (0.44, 1.05, 0.08), wood, location=(x, 0.58, 0.18)))
        objs.append(create_box(f"gate_door_trim_{x}", (0.5, 0.07, 0.09), trim, location=(x, 0.86, 0.24)))

    shade_smooth(objs)
    return objs


def build_banner_post(spec: dict) -> list[bpy.types.Object]:
    wood = make_material("banner_wood", spec["wood"], roughness=0.82)
    iron = make_material("banner_iron", spec["iron"], roughness=0.45, metallic=0.65)
    cloth = make_material("banner_cloth", spec["cloth"], roughness=0.9)
    trim = make_material("banner_trim", spec["trim"], roughness=0.5, metallic=0.35)

    objs = [
        create_cylinder("base", 0.18, 0.12, 12, iron, location=(0, 0.06, 0)),
        create_cylinder("pole", 0.035, 1.9, 10, wood, location=(0, 0.98, 0)),
        create_box("crossbar", (0.75, 0.05, 0.05), iron, location=(0.32, 1.65, 0)),
        create_box("banner_cloth", (0.52, 0.85, 0.035), cloth, location=(0.34, 1.16, 0)),
        create_box("banner_trim_top", (0.58, 0.055, 0.04), trim, location=(0.34, 1.57, 0.03)),
        create_box("banner_trim_bottom", (0.48, 0.055, 0.04), trim, location=(0.34, 0.76, 0.03)),
        create_cone("spear_tip", 0.075, 0.0, 0.18, 8, iron, location=(0, 1.99, 0)),
    ]
    shade_smooth(objs)
    return objs


def build_vendor_stall(spec: dict) -> list[bpy.types.Object]:
    wood = make_material("stall_wood", spec["wood"], roughness=0.82)
    dark_wood = make_material("stall_dark_wood", spec["darkWood"], roughness=0.86)
    cloth = make_material("stall_cloth", spec["cloth"], roughness=0.9)
    trim = make_material("stall_trim", spec["trim"], roughness=0.55, metallic=0.3)
    crate = make_material("stall_crate", spec["crate"], roughness=0.9)

    objs = [
        create_box("counter", (1.35, 0.32, 0.55), wood, location=(0, 0.42, 0)),
        create_box("counter_front", (1.45, 0.28, 0.08), dark_wood, location=(0, 0.34, 0.31)),
        create_box("canopy", (1.65, 0.12, 0.85), cloth, location=(0, 1.36, 0)),
        create_box("canopy_trim_front", (1.72, 0.08, 0.08), trim, location=(0, 1.25, 0.46)),
        create_box("canopy_trim_back", (1.72, 0.08, 0.08), trim, location=(0, 1.25, -0.46)),
    ]

    for x in (-0.72, 0.72):
        for z in (-0.36, 0.36):
            objs.append(create_cylinder(f"post_{x}_{z}", 0.035, 1.25, 8, wood, location=(x, 0.74, z)))

    objs.extend([
        create_box("crate_left", (0.35, 0.25, 0.3), crate, location=(-0.56, 0.14, 0.5)),
        create_box("crate_right", (0.28, 0.2, 0.28), crate, location=(0.58, 0.1, 0.48)),
        create_cylinder("barrel", 0.16, 0.34, 12, dark_wood, location=(0.0, 0.17, 0.55), rotation=(math.pi / 2, 0, 0)),
    ])
    shade_smooth(objs)
    return objs


def build_altdorf_castle(spec: dict) -> list[bpy.types.Object]:
    stone = make_material("castle_stone", spec["stone"], roughness=0.88)
    dark_stone = make_material("castle_dark_stone", spec["darkStone"], roughness=0.92)
    roof = make_material("castle_roof", spec["roof"], roughness=0.72)
    iron = make_material("castle_iron", spec["iron"], roughness=0.46, metallic=0.7)
    banner = make_material("castle_banner", spec["banner"], roughness=0.88)
    gold = make_material("castle_gold", spec["gold"], roughness=0.48, metallic=0.5)

    floor_h = 4.0
    outer_w = 150.0
    outer_d = 136.0
    half_w = outer_w / 2
    half_d = outer_d / 2
    wall_t = 5.0
    gate_gap = 20.0
    outer_h = floor_h * 3
    keep_h = floor_h * 5
    top_y = outer_h + 0.75

    objs: list[bpy.types.Object] = []
    root = create_empty("altdorf_castle_export_root")

    def add(obj: bpy.types.Object) -> bpy.types.Object:
        objs.append(obj)
        return obj

    def battlements(prefix: str, start: float, end: float, fixed: float, axis: str, top: float) -> None:
        step = 3.2
        count = int(abs(end - start) / step) + 1
        for i in range(count + 1):
            t = i / max(1, count)
            along = start + (end - start) * t
            if axis == "x":
                loc = (along, top, fixed)
                size = (1.35, 1.45, wall_t * 0.72)
            else:
                loc = (fixed, top, along)
                size = (wall_t * 0.72, 1.45, 1.35)
            add(create_box(f"{prefix}_merlon_{i}", size, dark_stone, location=loc))

    def wall_windows(prefix: str, start: float, end: float, fixed: float, axis: str, levels: int) -> None:
        for floor in range(levels):
            y = 2.1 + floor * floor_h
            count = int(abs(end - start) / 12.0) + 1
            for i in range(count + 1):
                t = i / max(1, count)
                along = start + (end - start) * t
                if abs(along) < gate_gap * 0.6 and fixed > 0:
                    continue
                if axis == "x":
                    add(create_box(f"{prefix}_window_{floor}_{i}", (1.0, 1.7, 0.12), iron, location=(along, y, fixed)))
                else:
                    add(create_box(f"{prefix}_window_{floor}_{i}", (0.12, 1.7, 1.0), iron, location=(fixed, y, along)))

    def floor_band(name: str, size: tuple, loc: tuple) -> None:
        add(create_box(name, size, dark_stone, location=loc))

    add(create_box("castle_foundation", (outer_w + 10, 0.8, outer_d + 12), dark_stone, location=(0, 0.4, 0)))

    add(create_box("castle_front_wall_left", (half_w - gate_gap / 2, outer_h, wall_t), stone, location=(-(half_w + gate_gap / 2) / 2, outer_h / 2 + 0.8, half_d)))
    add(create_box("castle_front_wall_right", (half_w - gate_gap / 2, outer_h, wall_t), stone, location=((half_w + gate_gap / 2) / 2, outer_h / 2 + 0.8, half_d)))
    add(create_box("castle_rear_wall", (outer_w, outer_h, wall_t), stone, location=(0, outer_h / 2 + 0.8, -half_d)))
    add(create_box("castle_left_wall", (wall_t, outer_h, outer_d), stone, location=(-half_w, outer_h / 2 + 0.8, 0)))
    add(create_box("castle_right_wall", (wall_t, outer_h, outer_d), stone, location=(half_w, outer_h / 2 + 0.8, 0)))

    for y in (floor_h + 0.8, floor_h * 2 + 0.8, floor_h * 3 + 0.8):
        floor_band(f"front_left_floor_band_{y}", (half_w - gate_gap / 2, 0.28, 0.34), (-(half_w + gate_gap / 2) / 2, y, half_d + 2.58))
        floor_band(f"front_right_floor_band_{y}", (half_w - gate_gap / 2, 0.28, 0.34), ((half_w + gate_gap / 2) / 2, y, half_d + 2.58))
        floor_band(f"rear_floor_band_{y}", (outer_w, 0.28, 0.34), (0, y, -half_d - 2.58))

    battlements("front_left", -half_w, -gate_gap / 2, half_d, "x", top_y)
    battlements("front_right", gate_gap / 2, half_w, half_d, "x", top_y)
    battlements("rear", -half_w, half_w, -half_d, "x", top_y)
    battlements("left", -half_d, half_d, -half_w, "z", top_y)
    battlements("right", -half_d, half_d, half_w, "z", top_y)
    wall_windows("front", -half_w + 9, half_w - 9, half_d + 2.56, "x", 3)
    wall_windows("rear", -half_w + 9, half_w - 9, -half_d - 2.56, "x", 3)
    wall_windows("left", -half_d + 9, half_d - 9, -half_w - 2.56, "z", 3)
    wall_windows("right", -half_d + 9, half_d - 9, half_w + 2.56, "z", 3)

    for x in (-half_w, half_w):
        for z in (-half_d, half_d):
            add(create_cylinder(f"corner_tower_{x}_{z}", 8.2, outer_h + 4, 32, stone, location=(x, (outer_h + 4) / 2 + 0.8, z)))
            add(create_cylinder(f"corner_tower_cap_{x}_{z}", 8.8, 0.85, 32, dark_stone, location=(x, outer_h + 5.15, z)))
            add(create_cone(f"corner_tower_roof_{x}_{z}", 8.0, 0.3, 6.4, 16, roof, location=(x, outer_h + 8.8, z)))
            for a in range(16):
                angle = (a / 16) * math.pi * 2
                add(create_box(
                    f"corner_tower_merlon_{x}_{z}_{a}",
                    (1.0, 1.35, 1.0),
                    dark_stone,
                    location=(x + math.cos(angle) * 7.7, outer_h + 5.95, z + math.sin(angle) * 7.7),
                    rotation=(0, 0, angle),
                ))

    for x in (-14.0, 14.0):
        add(create_cylinder(f"gatehouse_tower_{x}", 8.2, outer_h + 7.0, 32, stone, location=(x, (outer_h + 7.0) / 2 + 0.8, half_d + 1.8)))
        add(create_cylinder(f"gatehouse_cap_{x}", 8.9, 0.9, 32, dark_stone, location=(x, outer_h + 8.25, half_d + 1.8)))
        add(create_cone(f"gatehouse_roof_{x}", 8.0, 0.28, 7.6, 16, roof, location=(x, outer_h + 12.3, half_d + 1.8)))
    add(create_box("gatehouse_lintel", (30.0, 5.4, 8.0), stone, location=(0, outer_h + 1.8, half_d + 1.8)))
    add(create_box("gatehouse_shadow_arch", (16.0, 9.0, 8.3), dark_stone, location=(0, 5.25, half_d + 2.0)))
    add(create_box("gatehouse_walkway", (34.0, 1.0, 11.0), dark_stone, location=(0, outer_h + 4.7, half_d + 1.8)))
    for x in (-9.0, -5.4, -1.8, 1.8, 5.4, 9.0):
        add(create_box(f"portcullis_track_{x}", (0.22, 9.2, 0.22), iron, location=(x, 5.2, half_d + 6.3)))
    add(create_box("portcullis_top", (20.0, 0.34, 0.34), iron, location=(0, 10.0, half_d + 6.3)))

    def keep_wall(name: str, size: tuple, loc: tuple, mat: bpy.types.Material = stone) -> None:
        add(create_box(name, size, mat, location=loc))

    keep_wall("inner_keep_floor", (58.0, 0.35, 42.0), (0, 0.98, -12.0), dark_stone)
    keep_wall("inner_keep_front_left", (24.0, outer_h, 3.0), (-18.0, outer_h / 2 + 0.8, 10.5))
    keep_wall("inner_keep_front_right", (24.0, outer_h, 3.0), (18.0, outer_h / 2 + 0.8, 10.5))
    keep_wall("grand_entry_left_jamb", (1.6, 7.2, 4.0), (-4.6, 4.45, 10.9))
    keep_wall("grand_entry_right_jamb", (1.6, 7.2, 4.0), (4.6, 4.45, 10.9))
    keep_wall("grand_entry_header", (10.8, 1.2, 4.0), (0, 7.45, 10.9))
    keep_wall("grand_entry_threshold", (11.2, 0.32, 5.2), (0, 1.1, 12.35), dark_stone)
    keep_wall("inner_keep_front_lintel", (14.0, 4.0, 3.0), (0, 10.8, 10.5))
    keep_wall("inner_keep_rear_left", (24.0, outer_h, 3.0), (-18.0, outer_h / 2 + 0.8, -34.5))
    keep_wall("inner_keep_rear_right", (24.0, outer_h, 3.0), (18.0, outer_h / 2 + 0.8, -34.5))
    keep_wall("rear_entry_left_jamb", (1.4, 6.4, 3.6), (-4.3, 4.0, -34.8))
    keep_wall("rear_entry_right_jamb", (1.4, 6.4, 3.6), (4.3, 4.0, -34.8))
    keep_wall("rear_entry_header", (10.0, 1.0, 3.6), (0, 7.0, -34.8))
    keep_wall("inner_keep_rear_lintel", (14.0, 4.0, 3.0), (0, 10.8, -34.5))
    for x in (-30.0, 30.0):
        keep_wall(f"inner_keep_side_front_{x}", (3.0, outer_h, 18.0), (x, outer_h / 2 + 0.8, 1.0))
        keep_wall(f"inner_keep_side_rear_{x}", (3.0, outer_h, 18.0), (x, outer_h / 2 + 0.8, -25.0))
        keep_wall(f"side_entry_jamb_front_{x}", (3.6, 6.2, 1.2), (x, 3.9, -8.6))
        keep_wall(f"side_entry_jamb_rear_{x}", (3.6, 6.2, 1.2), (x, 3.9, -15.4))
        keep_wall(f"side_entry_header_{x}", (3.6, 1.0, 8.0), (x, 6.95, -12.0))
        keep_wall(f"inner_keep_side_lintel_{x}", (3.0, 4.0, 10.0), (x, 10.8, -12.0))

    # Ground-floor rooms: a central hall, side chambers, rear room, and stair bays.
    for x in (-10.0, 10.0):
        keep_wall(f"inner_room_wall_front_{x}", (1.2, 6.2, 17.0), (x, 3.9, 2.0), dark_stone)
        keep_wall(f"inner_room_wall_rear_{x}", (1.2, 6.2, 23.0), (x, 3.9, -23.0), dark_stone)
        keep_wall(f"inner_room_door_header_{x}", (1.2, 1.0, 7.0), (x, 6.5, -8.0), dark_stone)
    keep_wall("inner_cross_wall_left", (24.0, 6.0, 1.4), (-18.0, 3.8, -22.0), dark_stone)
    keep_wall("inner_cross_wall_right", (24.0, 6.0, 1.4), (18.0, 3.8, -22.0), dark_stone)
    keep_wall("inner_cross_wall_header", (12.0, 1.0, 1.4), (0, 6.4, -22.0), dark_stone)
    keep_wall("west_stairwell_back", (18.0, 5.8, 1.2), (-20.0, 3.7, -30.5), dark_stone)
    keep_wall("east_stairwell_back", (18.0, 5.8, 1.2), (20.0, 3.7, -30.5), dark_stone)

    # Floors and railings that the external stair props connect to.
    keep_wall("second_floor_west", (18.5, 0.38, 34.0), (-20.0, floor_h - 0.19, -12.0), dark_stone)
    keep_wall("second_floor_east", (18.5, 0.38, 34.0), (20.0, floor_h - 0.19, -12.0), dark_stone)
    keep_wall("second_floor_rear_bridge", (22.0, 0.38, 13.0), (0, floor_h - 0.19, -28.0), dark_stone)
    keep_wall("second_floor_front_balcony", (18.0, 0.38, 7.0), (0, floor_h - 0.19, 4.5), dark_stone)
    keep_wall("second_floor_west_rail", (1.0, 1.0, 30.0), (-10.2, floor_h + 0.85, -10.0), dark_stone)
    keep_wall("second_floor_east_rail", (1.0, 1.0, 30.0), (10.2, floor_h + 0.85, -10.0), dark_stone)
    keep_wall("second_floor_rear_rail", (18.0, 1.0, 1.0), (0, floor_h + 0.85, -21.0), dark_stone)
    keep_wall("third_floor_center", (32.0, 0.38, 22.0), (0, floor_h * 2 - 0.19, -18.0), dark_stone)
    keep_wall("third_floor_rear_rail", (30.0, 1.0, 1.0), (0, floor_h * 2 + 0.85, -28.5), dark_stone)
    keep_wall("third_floor_left_rail", (1.0, 1.0, 20.0), (-16.0, floor_h * 2 + 0.85, -18.0), dark_stone)
    keep_wall("third_floor_right_rail", (1.0, 1.0, 20.0), (16.0, floor_h * 2 + 0.85, -18.0), dark_stone)

    add(create_box("inner_keep_mid", (48.0, floor_h, 34.0), stone, location=(0, outer_h + floor_h / 2 + 0.8, -12.0)))
    add(create_box("inner_keep_upper", (36.0, floor_h, 24.0), stone, location=(0, outer_h + floor_h * 1.5 + 0.8, -12.0)))
    add(create_cone("inner_keep_roof", 27.0, 0.45, 8.0, 8, roof, location=(0, keep_h + 5.2, -12.0), rotation=(0, 0, math.pi / 4)))
    add(create_cylinder("central_spire_base", 5.0, 9.0, 16, stone, location=(0, keep_h + 8.5, -12.0)))
    add(create_cone("central_spire_roof", 4.5, 0.0, 10.0, 16, roof, location=(0, keep_h + 18.0, -12.0)))
    add(create_cone("central_spire_finial", 0.6, 0.0, 1.7, 16, gold, location=(0, keep_h + 23.9, -12.0)))

    for x in (-31.0, -15.5, 15.5, 31.0):
        add(create_box(f"keep_buttress_front_{x}", (2.1, outer_h, 2.2), dark_stone, location=(x, outer_h / 2 + 0.8, 11.2)))
        add(create_box(f"keep_buttress_back_{x}", (2.1, outer_h, 2.2), dark_stone, location=(x, outer_h / 2 + 0.8, -35.2)))
    for floor in range(5):
        y = 2.2 + floor * floor_h
        width = 54.0 if floor < 3 else 34.0
        for x in (-width / 3, 0, width / 3):
            add(create_box(f"keep_window_front_{floor}_{x}", (1.5, 2.0, 0.14), iron, location=(x, y, 10.35)))
            add(create_box(f"keep_window_rear_{floor}_{x}", (1.5, 2.0, 0.14), iron, location=(x, y, -34.35)))

    for x in (-43.0, 43.0):
        add(create_box(f"city_banner_{x}", (3.4, 8.0, 0.16), banner, location=(x, 7.6, half_d + 2.8)))
        add(create_box(f"city_banner_trim_{x}", (3.8, 0.35, 0.18), gold, location=(x, 11.45, half_d + 2.95)))
        add(create_box(f"city_banner_bar_h_{x}", (2.7, 0.3, 0.18), gold, location=(x, 7.8, half_d + 3.0)))
        add(create_box(f"city_banner_bar_v_{x}", (0.3, 2.6, 0.18), gold, location=(x, 7.8, half_d + 3.05)))

    add(create_box("stone_bridge", (19.0, 0.7, 24.0), dark_stone, location=(0, 0.75, half_d + 16.0)))
    for i in range(8):
        add(create_box(
            f"entry_step_{i}",
            (24.0 - i * 1.0, 0.28, 1.8),
            stone,
            location=(0, 0.95 + i * 0.28, half_d + 7.5 - i * 1.8),
        ))

    parent_to(root, objs)
    return objs


def keyframed_y_rotation(
    obj: bpy.types.Object,
    action_name: str,
    frames: list[tuple[int, float]],
    end_frame: int,
    strip_start: int = 1,
) -> None:
    obj.animation_data_create()
    obj.rotation_mode = "XYZ"
    action = bpy.data.actions.new(action_name)
    action.use_fake_user = True
    obj.animation_data.action = action
    for frame, rot_y in frames:
        obj.rotation_euler = (0, rot_y, 0)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    push_action_to_nla(obj, action, action_name, end_frame, strip_start)
    obj.animation_data.action = None


def build_castle_gate(spec: dict) -> list[bpy.types.Object]:
    wood = make_material("castle_gate_wood", spec["wood"], roughness=0.82)
    dark_wood = make_material("castle_gate_dark_wood", spec["darkWood"], roughness=0.88)
    iron = make_material("castle_gate_iron", spec["iron"], roughness=0.45, metallic=0.75)
    trim = make_material("castle_gate_trim", spec["trim"], roughness=0.55, metallic=0.45)

    root = create_empty("castle_gate_export_root")
    left_hinge = create_empty("castle_gate_left_hinge", location=(-8.0, 0, 0))
    right_hinge = create_empty("castle_gate_right_hinge", location=(8.0, 0, 0))

    objs: list[bpy.types.Object] = [left_hinge, right_hinge]
    left_parts = [
        create_box("left_gate_planks", (8.0, 9.2, 0.55), wood, location=(4.0, 4.7, 0)),
        create_box("left_gate_backing", (7.4, 8.5, 0.18), dark_wood, location=(4.0, 4.55, -0.34)),
    ]
    right_parts = [
        create_box("right_gate_planks", (8.0, 9.2, 0.55), wood, location=(-4.0, 4.7, 0)),
        create_box("right_gate_backing", (7.4, 8.5, 0.18), dark_wood, location=(-4.0, 4.55, -0.34)),
    ]
    for side, parts, base_x in (("left", left_parts, 4.0), ("right", right_parts, -4.0)):
        for y in (1.6, 4.6, 7.4):
            parts.append(create_box(f"{side}_iron_strap_{y}", (7.8, 0.35, 0.68), iron, location=(base_x, y, 0.36)))
        for x_offset in (-2.2, 0, 2.2):
            parts.append(create_box(f"{side}_vertical_rib_{x_offset}", (0.35, 8.7, 0.72), trim, location=(base_x + x_offset, 4.65, 0.42)))
        for y in (2.2, 3.5, 5.0, 6.4, 7.7):
            for x_offset in (-3.0, -1.5, 0, 1.5, 3.0):
                parts.append(create_cylinder(
                    f"{side}_rivet_{x_offset}_{y}",
                    0.12,
                    0.08,
                    12,
                    iron,
                    location=(base_x + x_offset, y, 0.8),
                    rotation=(math.pi / 2, 0, 0),
                ))

    objs.extend(left_parts + right_parts)
    parent_to(left_hinge, left_parts)
    parent_to(right_hinge, right_parts)
    parent_to(root, [left_hinge, right_hinge])

    keyframed_y_rotation(left_hinge, "open", [(1, 0.0), (18, -0.45), (48, -1.35)], 48)
    keyframed_y_rotation(right_hinge, "open", [(1, 0.0), (18, 0.45), (48, 1.35)], 48)
    keyframed_y_rotation(left_hinge, "close", [(1, -1.35), (30, -0.45), (48, 0.0)], 48, 60)
    keyframed_y_rotation(right_hinge, "close", [(1, 1.35), (30, 0.45), (48, 0.0)], 48, 60)
    left_hinge.rotation_euler = (0, 0, 0)
    right_hinge.rotation_euler = (0, 0, 0)
    return objs


def build_castle_door(spec: dict) -> list[bpy.types.Object]:
    wood = make_material("castle_door_wood", spec["wood"], roughness=0.84)
    dark_wood = make_material("castle_door_dark_wood", spec["darkWood"], roughness=0.9)
    iron = make_material("castle_door_iron", spec["iron"], roughness=0.45, metallic=0.75)
    trim = make_material("castle_door_trim", spec["trim"], roughness=0.58, metallic=0.45)

    root = create_empty("castle_door_export_root")
    hinge = create_empty("castle_door_hinge", location=(-2.6, 0, 0))
    parts = [
        create_box("door_panel", (5.2, 6.0, 0.38), wood, location=(2.6, 3.05, 0)),
        create_box("door_backing", (4.75, 5.55, 0.16), dark_wood, location=(2.6, 3.0, -0.28)),
    ]
    for x in (0.85, 2.6, 4.35):
        parts.append(create_box(f"door_vertical_plank_{x}", (0.18, 5.7, 0.46), dark_wood, location=(x, 3.05, 0.12)))
    for y in (1.25, 3.0, 4.75):
        parts.append(create_box(f"door_iron_strap_{y}", (5.0, 0.28, 0.52), iron, location=(2.6, y, 0.28)))
    for y in (1.25, 3.0, 4.75):
        for x in (0.55, 1.6, 2.6, 3.6, 4.65):
            parts.append(create_cylinder(
                f"door_rivet_{x}_{y}",
                0.09,
                0.07,
                12,
                iron,
                location=(x, y, 0.62),
                rotation=(math.pi / 2, 0, 0),
            ))
    parts.append(create_box("door_pull_ring_mount", (0.55, 0.55, 0.08), trim, location=(4.25, 3.05, 0.62)))
    parts.append(create_cylinder("door_pull_ring", 0.26, 0.06, 20, iron, location=(4.25, 2.65, 0.66), rotation=(math.pi / 2, 0, 0)))

    objs: list[bpy.types.Object] = [hinge, *parts]
    parent_to(hinge, parts)
    parent_to(root, [hinge])
    keyframed_y_rotation(hinge, "open", [(1, 0.0), (18, -0.45), (48, -1.35)], 48)
    keyframed_y_rotation(hinge, "close", [(1, -1.35), (30, -0.45), (48, 0.0)], 48, 60)
    hinge.rotation_euler = (0, 0, 0)
    return objs


def build_castle_stairs(spec: dict) -> list[bpy.types.Object]:
    stone = make_material("castle_stairs_stone", spec["stone"], roughness=0.9)
    dark_stone = make_material("castle_stairs_dark_stone", spec["darkStone"], roughness=0.95)
    trim = make_material("castle_stairs_trim", spec["trim"], roughness=0.9)

    root = create_empty("castle_stairs_export_root")
    objs: list[bpy.types.Object] = []
    step_count = 12
    step_h = 4.0 / step_count
    step_d = 1.0
    start_z = -5.5
    for i in range(step_count):
        width = 8.0 - min(i * 0.08, 0.7)
        objs.append(create_box(
            f"stair_tread_{i}",
            (width, step_h, step_d),
            stone,
            location=(0, (i + 0.5) * step_h, start_z + i * step_d),
        ))
        if i % 2 == 0:
            objs.append(create_box(
                f"stair_front_trim_{i}",
                (width + 0.15, 0.07, 0.12),
                dark_stone,
                location=(0, (i + 1) * step_h, start_z + i * step_d - 0.47),
            ))
    objs.append(create_box("stair_top_landing", (7.6, 0.35, 3.2), stone, location=(0, 4.18, 6.8)))
    for x in (-4.4, 4.4):
        objs.append(create_box(f"stair_side_wall_{x}", (0.38, 4.35, 13.8), dark_stone, location=(x, 2.18, 0.15)))
        for i in range(4):
            objs.append(create_box(f"stair_side_merlon_{x}_{i}", (0.54, 0.55, 1.0), trim, location=(x, 4.58, -4.8 + i * 3.1)))
    parent_to(root, objs)
    return objs


def build_preview_twisted_tree(spec: dict) -> list[bpy.types.Object]:
    bark = make_material("preview_twisted_tree_bark", spec["bark"], roughness=0.97)
    split = make_material("preview_twisted_tree_split", spec["split"], roughness=0.95)
    thorn = make_material("preview_twisted_tree_thorn", spec["thorn"], roughness=0.88)
    leaf = make_material("preview_twisted_tree_leaf", spec["leaf"], roughness=0.93)

    root = create_empty("preview_twisted_tree_export_root")
    objs: list[bpy.types.Object] = [
        create_cylinder("curved_trunk_lower", 0.18, 1.25, 10, bark, location=(-0.05, 0.62, 0), rotation=(0, 0, -0.13)),
        create_cylinder("curved_trunk_upper", 0.115, 1.15, 9, bark, location=(0.13, 1.62, 0.02), rotation=(0, 0, 0.28)),
        create_cylinder("split_trunk_core", 0.072, 0.85, 8, split, location=(0.03, 1.25, 0.055), rotation=(0, 0, 0.08)),
    ]
    branches = [
        ("left_hook", -0.52, 1.78, -0.05, 0.92, 0.72),
        ("right_hook", 0.55, 1.55, 0.02, -0.82, 0.82),
        ("crown_splinter", 0.24, 2.15, 0.05, -0.28, 0.7),
        ("rear_bough", -0.12, 1.58, -0.38, 0.25, 0.62),
    ]
    for name, x, y, z, rz, length in branches:
        objs.append(create_cylinder(name, 0.045, length, 7, bark, location=(x, y, z), rotation=(0, 0, rz)))

    for i, (x, y, z, rz) in enumerate([
        (-0.77, 2.0, -0.05, 0.85),
        (0.83, 1.75, 0.04, -0.7),
        (0.36, 2.45, 0.06, -0.18),
        (-0.22, 1.9, -0.42, 0.32),
    ]):
        objs.append(create_cone(f"thorn_cluster_{i}", 0.055, 0.0, 0.32, 6, thorn, location=(x, y, z), rotation=(0, 0, rz)))

    for i, (x, y, z) in enumerate([(-0.6, 1.62, -0.08), (0.6, 1.36, 0.03), (0.2, 1.95, 0.08)]):
        clump = create_box(f"withered_leaf_clump_{i}", (0.42, 0.13, 0.32), leaf, location=(x, y, z), rotation=(0, 0, 0.4 + i * 0.5))
        objs.append(clump)

    parent_to(root, objs)
    shade_smooth(objs)
    return objs


def build_preview_blight_shrub(spec: dict) -> list[bpy.types.Object]:
    stem = make_material("preview_blight_shrub_stem", spec["stem"], roughness=0.97)
    leaf = make_material("preview_blight_shrub_leaf", spec["leaf"], roughness=0.94)
    rot = make_material("preview_blight_shrub_rot", spec["rot"], roughness=0.9)

    root = create_empty("preview_blight_shrub_export_root")
    objs: list[bpy.types.Object] = []
    for i in range(13):
        angle = i * 0.72
        radius = 0.16 + (i % 4) * 0.07
        height = 0.46 + (i % 5) * 0.085
        x = math.cos(angle) * radius
        z = math.sin(angle) * radius * 0.75
        objs.append(create_cylinder(f"crooked_stem_{i}", 0.018, height, 5, stem, location=(x, height / 2, z), rotation=(0, 0, math.sin(angle) * 0.36)))
        objs.append(create_box(
            f"matted_leaf_{i}",
            (0.26 + (i % 3) * 0.04, 0.07, 0.16),
            leaf if i % 4 else rot,
            location=(x + math.cos(angle) * 0.09, height + 0.02, z + math.sin(angle) * 0.06),
            rotation=(0, 0, angle * 0.15),
        ))

    parent_to(root, objs)
    shade_smooth(objs)
    return objs


def build_preview_jagged_stone(spec: dict) -> list[bpy.types.Object]:
    stone = make_material("preview_jagged_stone", spec["stone"], roughness=0.96)
    dark = make_material("preview_jagged_stone_dark", spec["dark"], roughness=0.98)
    stain = make_material("preview_jagged_stone_stain", spec["stain"], roughness=0.9)

    root = create_empty("preview_jagged_stone_export_root")
    objs: list[bpy.types.Object] = []
    for i in range(7):
        height = 0.7 + i * 0.16
        radius = 0.16 + (i % 3) * 0.035
        x = -0.62 + i * 0.2
        z = math.sin(i * 1.1) * 0.16
        mat = stain if i == 3 else dark if i % 2 else stone
        spike = create_cone(
            f"broken_shard_{i}",
            radius,
            0.03,
            height,
            5,
            mat,
            location=(x, height / 2, z),
            rotation=(0, 0, -0.28 + i * 0.08),
        )
        objs.append(spike)
    objs.append(create_box("buried_slab", (1.45, 0.16, 0.62), dark, location=(0, 0.08, 0.02), rotation=(0, 0, 0.08)))

    parent_to(root, objs)
    shade_smooth(objs)
    return objs


def build_preview_dreary_reeds(spec: dict) -> list[bpy.types.Object]:
    reed = make_material("preview_dreary_reed", spec["reed"], roughness=0.98)
    seed = make_material("preview_dreary_seed", spec["seed"], roughness=0.94)
    mud = make_material("preview_dreary_mud", spec["mud"], roughness=0.98)

    root = create_empty("preview_dreary_reeds_export_root")
    objs: list[bpy.types.Object] = [
        create_cylinder("muddy_root_clump", 0.46, 0.08, 18, mud, location=(0, 0.04, 0)),
    ]
    for i in range(18):
        angle = i * 0.63
        radius = 0.14 + (i % 6) * 0.055
        height = 0.56 + (i % 4) * 0.13
        x = math.cos(angle) * radius
        z = math.sin(angle) * radius * 0.72
        lean = math.sin(angle) * 0.24
        objs.append(create_cylinder(f"bent_reed_{i}", 0.01, height, 5, reed, location=(x, height / 2, z), rotation=(0, 0, lean)))
        objs.append(create_cylinder(f"reed_seed_{i}", 0.028, 0.12, 6, seed, location=(x + lean * 0.08, height + 0.04, z), rotation=(0, 0, lean)))

    parent_to(root, objs)
    shade_smooth(objs)
    return objs


BUILDERS = {
    "dummy": build_dummy,
    "gate": build_gate,
    "banner_post": build_banner_post,
    "vendor_stall": build_vendor_stall,
    "altdorf_castle": build_altdorf_castle,
    "castle_gate": build_castle_gate,
    "castle_door": build_castle_door,
    "castle_stairs": build_castle_stairs,
    "preview_twisted_tree": build_preview_twisted_tree,
    "preview_blight_shrub": build_preview_blight_shrub,
    "preview_jagged_stone": build_preview_jagged_stone,
    "preview_dreary_reeds": build_preview_dreary_reeds,
}


def export_glb(output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bpy.context.scene.frame_set(1)
    normalize_y_up_scene_to_blender_z_up()
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        export_animations=True,
        export_skins=False,
        export_extras=True,
        export_apply=True,
        export_yup=True,
        export_draco_mesh_compression_enable=False,
    )


def main() -> None:
    args = parse_args()
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    if args.asset not in BUILDERS:
        print(f"ERROR: unknown static asset '{args.asset}'")
        sys.exit(1)

    if args.asset not in spec:
        print(f"ERROR: no spec entry for '{args.asset}'")
        sys.exit(1)

    print(f"[WAR] Generating static asset {args.asset} -> {args.output}")
    clear_scene()
    BUILDERS[args.asset](spec[args.asset])
    apply_asset_metadata(args)
    export_glb(args.output)
    print(f"[WAR] SUCCESS: {args.output}")


if __name__ == "__main__":
    main()
