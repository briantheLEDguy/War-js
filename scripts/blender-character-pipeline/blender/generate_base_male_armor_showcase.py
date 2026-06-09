"""
Build a dark-fantasy armor showcase over blends/male_base.blend.

The provided base mesh is kept as the anatomical baseline. Armor geometry is
created as separate overlay objects in Blender Z-up space, then exported through
glTF with Y-up conversion for the War-js runtime.
"""

from __future__ import annotations

from collections import deque
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[3]
BASE_BLEND = ROOT / "blends" / "male_base.blend"
MODEL_DIR = ROOT / "public" / "assets" / "models"
ARTIFACT_DIR = ROOT / "artifacts" / "blender" / "base_male_armor_showcase"
BASE_BODY_GLB = MODEL_DIR / "body_human_armor_fit_t1_m.glb"
COMBINED_GLB = MODEL_DIR / "body_human_armor_showcase_t1_m.glb"
ARMOR_ONLY_GLB = MODEL_DIR / "arm_human_blackened_plate_full_t1_m.glb"
BLEND_PATH = ARTIFACT_DIR / "base_male_armor_showcase.blend"
RENDER_PATH = ARTIFACT_DIR / "base_male_armor_showcase_iso.png"
REPORT_PATH = ARTIFACT_DIR / "base_male_armor_fit_report.json"

EQUIPMENT_EXPORTS = {
    "arm_human_chest_blackened_plate_t1_m": [
        "armor_fitted_dark_arming_torso",
        "armor_fitted_breastplate_front",
        "armor_fitted_backplate",
        "armor_fitted_gorget",
    ],
    "arm_human_shoulders_blackened_plate_t1_m": [
        "armor_fitted_pauldron",
    ],
    "arm_human_hands_blackened_bracers_t1_m": [
        "armor_fitted_arming_sleeve",
        "armor_fitted_upper_arm_plate",
        "armor_fitted_vambrace",
    ],
    "arm_human_waist_blackened_belt_t1_m": [
        "armor_fitted_belt",
    ],
    "arm_human_legs_blackened_plate_t1_m": [
        "armor_fitted_dark_hose",
        "armor_fitted_cuisse",
        "armor_fitted_greave",
    ],
    "arm_human_feet_blackened_boots_t1_m": [
        "armor_fitted_boot",
    ],
    "arm_human_tabard_oathcloth_t1_m": [
        "armor_front_oath_tabard",
    ],
    "arm_human_back_crimson_cape_t1_m": [
        "armor_back_cape_heavy_fall",
    ],
}


def hex_to_linear(hex_color: str) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (r ** 2.2, g ** 2.2, b ** 2.2, 1.0)


def material(name: str, color: str, roughness: float, metallic: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = hex_to_linear(color)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat


def enhance_base_materials(base: bpy.types.Object) -> None:
    skin = material("base_male_reference_skin", "#9d725f", 0.76, 0.0)
    eye = material("base_male_reference_dark_eye", "#17110d", 0.42, 0.0)
    base.data.materials.clear()
    base.data.materials.append(skin)
    base.data.materials.append(eye)


def mesh_obj(
    name: str,
    verts: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    mat: bpy.types.Material,
    smooth: bool = True,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    if smooth:
        for poly in obj.data.polygons:
            poly.use_smooth = True
    obj.modifiers.new(name="weighted_normals", type="WEIGHTED_NORMAL")
    return obj


def add_solidify(obj: bpy.types.Object, thickness: float) -> bpy.types.Object:
    solid = obj.modifiers.new(name="plate_thickness", type="SOLIDIFY")
    solid.thickness = thickness
    solid.offset = 0.0
    obj.modifiers.new(name="plate_weighted_normals", type="WEIGHTED_NORMAL")
    return obj


def bevel(obj: bpy.types.Object, amount: float, segments: int = 2) -> bpy.types.Object:
    mod = obj.modifiers.new(name="soft_beveled_edges", type="BEVEL")
    mod.width = amount
    mod.segments = segments
    obj.modifiers.new(name="bevel_weighted_normals", type="WEIGHTED_NORMAL")
    return obj


def grid_surface(
    name: str,
    u_steps: int,
    v_steps: int,
    point_fn,
    mat: bpy.types.Material,
    thickness: float = 0.0,
) -> bpy.types.Object:
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for v_i in range(v_steps + 1):
        v = v_i / v_steps
        for u_i in range(u_steps + 1):
            u = (u_i / u_steps) * 2.0 - 1.0
            verts.append(point_fn(u, v))
    stride = u_steps + 1
    for v_i in range(v_steps):
        for u_i in range(u_steps):
            a = v_i * stride + u_i
            faces.append((a, a + 1, a + stride + 1, a + stride))
    obj = mesh_obj(name, verts, faces, mat)
    if thickness:
        add_solidify(obj, thickness)
    return obj


def elliptical_shell(
    name: str,
    z0: float,
    z1: float,
    angle0: float,
    angle1: float,
    rx_fn,
    ry_fn,
    y_center: float,
    mat: bpy.types.Material,
    x_center: float = 0.0,
    u_steps: int = 72,
    v_steps: int = 32,
    thickness: float = 0.012,
) -> bpy.types.Object:
    def point(u: float, v: float) -> tuple[float, float, float]:
        t = (u + 1.0) * 0.5
        angle = angle0 + (angle1 - angle0) * t
        rx = rx_fn(v)
        ry = ry_fn(v)
        x = x_center + math.sin(angle) * rx
        y = y_center - math.cos(angle) * ry
        z = z0 + (z1 - z0) * v
        return (x, y, z)

    return grid_surface(name, u_steps, v_steps, point, mat, thickness=thickness)


def box_prism(
    name: str,
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    mat: bpy.types.Material,
    rot_z: float = 0.0,
    bevel_amount: float = 0.0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center, rotation=(0.0, 0.0, rot_z))
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel_amount:
        bevel(obj, bevel_amount)
    return obj


def ellipsoid(
    name: str,
    center: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    segments: int = 32,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=max(8, segments // 2),
        radius=1.0,
        location=center,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.modifiers.new(name="ellipsoid_weighted_normals", type="WEIGHTED_NORMAL")
    return obj


def cylinder_between(
    name: str,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    radius: float,
    mat: bpy.types.Material,
    segments: int = 20,
) -> bpy.types.Object:
    start = Vector(p0)
    end = Vector(p1)
    mid = (start + end) * 0.5
    axis = end - start
    length = axis.length
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius, depth=length, location=mid)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    obj.rotation_euler = axis.to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    bevel(obj, radius * 0.12, 1)
    return obj


def cloth_panel(
    name: str,
    x_center: float,
    y_base: float,
    z_top: float,
    z_bottom: float,
    width_top: float,
    width_bottom: float,
    mat: bpy.types.Material,
    wave: float = 0.018,
    thickness: float = 0.004,
) -> bpy.types.Object:
    def point(u: float, v: float) -> tuple[float, float, float]:
        width = width_top + (width_bottom - width_top) * v
        x = x_center + u * width
        z = z_top + (z_bottom - z_top) * v
        y = y_base + math.sin((u + 1.0) * math.pi * 1.5) * wave * math.sin(v * math.pi)
        return (x, y, z)

    return grid_surface(name, 22, 26, point, mat, thickness=thickness)


def bounds_for(obj: bpy.types.Object) -> dict[str, float]:
    mins = Vector((math.inf, math.inf, math.inf))
    maxs = Vector((-math.inf, -math.inf, -math.inf))
    for corner in obj.bound_box:
        world = obj.matrix_world @ Vector(corner)
        mins.x = min(mins.x, world.x)
        mins.y = min(mins.y, world.y)
        mins.z = min(mins.z, world.z)
        maxs.x = max(maxs.x, world.x)
        maxs.y = max(maxs.y, world.y)
        maxs.z = max(maxs.z, world.z)
    return {
        "min_x": mins.x,
        "max_x": maxs.x,
        "min_y": mins.y,
        "max_y": maxs.y,
        "min_z": mins.z,
        "max_z": maxs.z,
        "width": maxs.x - mins.x,
        "depth": maxs.y - mins.y,
        "height": maxs.z - mins.z,
    }


def fitted_patch(
    name: str,
    base: bpy.types.Object,
    predicate,
    mat: bpy.types.Material,
    offset: float = 0.014,
    thickness: float = 0.010,
    min_faces: int = 12,
) -> bpy.types.Object | None:
    """Duplicate a body-surface region and offset it along vertex normals."""
    mesh = base.data
    mesh.update()
    normal_matrix = base.matrix_world.to_3x3().inverted().transposed()
    positions = [base.matrix_world @ vert.co for vert in mesh.vertices]
    normals = []
    for vert in mesh.vertices:
        normal = normal_matrix @ vert.normal
        if normal.length < 0.0001:
            normal = Vector((0.0, -1.0, 0.0))
        normal.normalize()
        normals.append(normal)

    selected_faces: list[bpy.types.MeshPolygon] = []
    for poly in mesh.polygons:
        center = sum((positions[i] for i in poly.vertices), Vector()) / len(poly.vertices)
        normal = normal_matrix @ poly.normal
        if normal.length < 0.0001:
            normal = Vector((0.0, -1.0, 0.0))
        normal.normalize()
        if predicate(center, normal):
            selected_faces.append(poly)

    if len(selected_faces) < min_faces:
        print(f"[WAR] SKIP {name}: only {len(selected_faces)} source faces")
        return None

    index_map: dict[int, int] = {}
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for poly in selected_faces:
        face_indices = []
        for source_index in poly.vertices:
            if source_index not in index_map:
                point = positions[source_index] + normals[source_index] * offset
                index_map[source_index] = len(verts)
                verts.append(tuple(point))
            face_indices.append(index_map[source_index])
        faces.append(tuple(face_indices))

    obj = mesh_obj(name, verts, faces, mat)
    if thickness:
        add_solidify(obj, thickness)
    bevel(obj, thickness * 0.35 if thickness else 0.003, 1)
    return obj


def add_if_present(objects: list[bpy.types.Object], obj: bpy.types.Object | None) -> None:
    if obj is not None:
        objects.append(obj)


def build_armor(
    base: bpy.types.Object,
    base_bounds: dict[str, float],
    *,
    include_underlayer_overlays: bool = True,
    include_front_tabard: bool = True,
    use_clean_cuirass: bool = False,
) -> tuple[list[bpy.types.Object], dict]:
    steel = material("base_male_blackened_blued_steel", "#11191e", 0.48, 0.74)
    edge = material("base_male_worn_bright_edges", "#65747a", 0.42, 0.72)
    brass = material("base_male_aged_brass", "#8a672d", 0.50, 0.50)
    leather = material("base_male_dark_leather", "#27160f", 0.86, 0.0)
    arming = material("base_male_black_arming_underlayer", "#12100e", 0.92, 0.0)
    cloth = material("base_male_oath_tabard_cloth", "#b7aa87", 0.94, 0.0)
    red = material("base_male_deep_red_cape_lining", "#2a0c10", 0.95, 0.0)

    z_min = base_bounds["min_z"]
    height = base_bounds["height"]
    z = lambda f: z_min + height * f
    y_center = (base_bounds["min_y"] + base_bounds["max_y"]) * 0.5

    positions = [base.matrix_world @ vert.co for vert in base.data.vertices]

    def region_depth(lo: float, hi: float, max_abs_x: float) -> tuple[float, float]:
        points = [
            point for point in positions
            if abs(point.x) < max_abs_x and z(lo) < point.z < z(hi)
        ]
        if not points:
            return base_bounds["min_y"], base_bounds["max_y"]
        return min(point.y for point in points), max(point.y for point in points)

    torso_front_y, torso_back_y = region_depth(0.405, 0.720, 0.300)
    front_y = torso_front_y - 0.028
    back_y = torso_back_y + 0.032
    objects: list[bpy.types.Object] = []

    # Surface-fitted armor. These pieces are copied from the supplied body mesh,
    # so the source pose and anatomy drive the fit instead of hand-placed tubes.
    if include_underlayer_overlays:
        add_if_present(objects, fitted_patch(
            "armor_fitted_dark_arming_torso",
            base,
            lambda c, _n: abs(c.x) < 0.30 and z(0.405) < c.z < z(0.730),
            arming,
            offset=0.010,
            thickness=0.008,
        ))
    if use_clean_cuirass:
        torso_depth = max(0.080, (torso_back_y - torso_front_y) * 0.5)

        def cuirass_rx(v: float) -> float:
            return 0.225 + math.sin(v * math.pi) * 0.055

        def cuirass_ry(_v: float) -> float:
            return torso_depth + 0.050

        objects.extend([
            elliptical_shell(
                "armor_fitted_breastplate_front",
                z(0.430),
                z(0.790),
                math.radians(-76),
                math.radians(76),
                cuirass_rx,
                cuirass_ry,
                y_center,
                steel,
                u_steps=44,
                v_steps=24,
                thickness=0.020,
            ),
            elliptical_shell(
                "armor_fitted_backplate",
                z(0.430),
                z(0.765),
                math.radians(104),
                math.radians(256),
                cuirass_rx,
                cuirass_ry,
                y_center,
                steel,
                u_steps=44,
                v_steps=22,
                thickness=0.016,
            ),
        ])
    else:
        add_if_present(objects, fitted_patch(
            "armor_fitted_breastplate_front",
            base,
            lambda c, n: abs(c.x) < 0.285 and z(0.450) < c.z < z(0.775) and c.y < y_center + 0.020 and n.y < 0.42,
            steel,
            offset=0.026,
            thickness=0.018,
        ))
        add_if_present(objects, fitted_patch(
            "armor_fitted_backplate",
            base,
            lambda c, n: abs(c.x) < 0.275 and z(0.450) < c.z < z(0.755) and c.y > y_center - 0.020 and n.y > -0.42,
            steel,
            offset=0.024,
            thickness=0.014,
        ))
    add_if_present(objects, fitted_patch(
        "armor_fitted_gorget",
        base,
        lambda c, _n: abs(c.x) < 0.155 and z(0.715) < c.z < z(0.825) and -0.150 < c.y < 0.070,
        steel,
        offset=0.018,
        thickness=0.012,
    ))
    add_if_present(objects, fitted_patch(
        "armor_fitted_belt",
        base,
        lambda c, _n: abs(c.x) < 0.280 and z(0.405) < c.z < z(0.470),
        leather,
        offset=0.018,
        thickness=0.012,
    ))

    if include_front_tabard:
        objects.append(cloth_panel(
            "armor_front_oath_tabard",
            0.0,
            front_y - 0.010,
            z(0.420),
            z(0.055),
            0.120,
            0.165,
            cloth,
            wave=0.014,
            thickness=0.006,
        ))
    objects.append(cloth_panel("armor_back_cape_heavy_fall", 0.0, back_y, z(0.700), z(0.080), 0.280, 0.380, red, wave=0.030, thickness=0.006))

    for side in (-1, 1):
        add_if_present(objects, fitted_patch(
            f"armor_fitted_pauldron_{side}",
            base,
            lambda c, n, side=side: (c.x * side) > 0.155 and (c.x * side) < 0.440 and z(0.655) < c.z < z(0.805) and n.z > -0.30,
            steel,
            offset=0.045,
            thickness=0.018,
        ))
        if include_underlayer_overlays:
            add_if_present(objects, fitted_patch(
                f"armor_fitted_arming_sleeve_{side}",
                base,
                lambda c, _n, side=side: (c.x * side) > 0.225 and (c.x * side) < 0.565 and z(0.495) < c.z < z(0.690),
                arming,
                offset=0.012,
                thickness=0.007,
            ))
        add_if_present(objects, fitted_patch(
            f"armor_fitted_vambrace_{side}",
            base,
            lambda c, _n, side=side: (c.x * side) > 0.170 and (c.x * side) < 0.575 and z(0.390) < c.z < z(0.585) and c.y < 0.080,
            steel,
            offset=0.020,
            thickness=0.012,
        ))
        add_if_present(objects, fitted_patch(
            f"armor_fitted_upper_arm_plate_{side}",
            base,
            lambda c, _n, side=side: (c.x * side) > 0.220 and (c.x * side) < 0.500 and z(0.575) < c.z < z(0.700),
            steel,
            offset=0.020,
            thickness=0.012,
        ))
        if include_underlayer_overlays:
            add_if_present(objects, fitted_patch(
                f"armor_fitted_dark_hose_{side}",
                base,
                lambda c, _n, side=side: (c.x * side) > 0.055 and (c.x * side) < 0.245 and z(0.060) < c.z < z(0.510),
                arming,
                offset=0.010,
                thickness=0.007,
            ))
        add_if_present(objects, fitted_patch(
            f"armor_fitted_cuisse_{side}",
            base,
            lambda c, _n, side=side: (c.x * side) > 0.055 and (c.x * side) < 0.225 and z(0.265) < c.z < z(0.470),
            steel,
            offset=0.018,
            thickness=0.012,
        ))
        add_if_present(objects, fitted_patch(
            f"armor_fitted_greave_{side}",
            base,
            lambda c, _n, side=side: (c.x * side) > 0.090 and (c.x * side) < 0.235 and z(0.090) < c.z < z(0.285),
            steel,
            offset=0.020,
            thickness=0.012,
        ))
        add_if_present(objects, fitted_patch(
            f"armor_fitted_boot_{side}",
            base,
            lambda c, _n, side=side: (c.x * side) > 0.105 and (c.x * side) < 0.260 and z(0.000) <= c.z < z(0.105),
            leather,
            offset=0.016,
            thickness=0.010,
        ))
    report = {
        "baseline_blend": str(BASE_BLEND),
        "combined_glb": str(COMBINED_GLB),
        "armor_overlay_glb": str(ARMOR_ONLY_GLB),
        "armor_piece_count": len(objects),
        "base_bounds_z_up": {key: round(value, 4) for key, value in base_bounds.items()},
        "fit_targets": [
            "armor surfaces are duplicated from the source mesh and offset along normals",
            "breastplate and backplate use source torso faces",
            "gorget, pauldrons, sleeves, bracers, cuisses, greaves, and boots use source body regions",
            "belt, tassets, tabard, and cape share the same base origin",
        ],
        "runtime_contract": {
            "base_model": "body_human_armor_fit_t1_m.glb",
            "equipment_model_pattern": "manifest assetId plus .glb",
            "attachment": "same-origin overlay on the player root in the base mesh neutral pose",
            "animation_requirement": "for animated gameplay, bind the base body and armor modules to the same armature and copy skin weights",
        },
    }
    return objects, report


def apply_modifiers() -> None:
    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        for mod in list(obj.modifiers):
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except RuntimeError:
                pass


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_lighting_and_camera() -> None:
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        bg.inputs["Strength"].default_value = 1.0

    for name, loc, energy, size in [
        ("base_male_armor_key", (-3.2, -4.5, 3.8), 760, 4.2),
        ("base_male_armor_fill", (3.8, -3.0, 2.6), 170, 5.0),
        ("base_male_armor_rim", (0.4, 3.6, 2.8), 260, 2.2),
    ]:
        light_data = bpy.data.lights.new(name, type="AREA")
        light_data.energy = energy
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        light.location = loc
        look_at(light, Vector((0.0, -0.10, 0.90)))
        bpy.context.collection.objects.link(light)

    cam_data = bpy.data.cameras.new("camera_base_male_armor_iso")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 2.18
    cam = bpy.data.objects.new("camera_base_male_armor_iso", cam_data)
    cam.location = (2.85, -4.10, 2.25)
    look_at(cam, Vector((0.0, -0.10, 0.88)))
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam


def setup_render(path: Path) -> None:
    scene = bpy.context.scene
    for engine in ("CYCLES", "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = 128
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 5
    else:
        scene.eevee.taa_render_samples = 96
        if hasattr(scene.eevee, "use_gtao"):
            scene.eevee.use_gtao = True
            scene.eevee.gtao_distance = 3
            scene.eevee.gtao_factor = 1.4
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1600
    scene.render.film_transparent = False
    scene.render.filepath = str(path)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"


def force_white_background(path: Path) -> None:
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    pixels = list(image.pixels[:])
    total = width * height
    visited = bytearray(total)
    queue: deque[int] = deque()

    def is_bg(index: int) -> bool:
        base = index * 4
        r, g, b, a = pixels[base], pixels[base + 1], pixels[base + 2], pixels[base + 3]
        return a > 0.98 and r > 0.86 and g > 0.86 and b > 0.86 and max(r, g, b) - min(r, g, b) < 0.10

    def enqueue(index: int) -> None:
        if not visited[index] and is_bg(index):
            visited[index] = 1
            queue.append(index)

    for x in range(width):
        enqueue(x)
        enqueue((height - 1) * width + x)
    for y in range(height):
        enqueue(y * width)
        enqueue(y * width + width - 1)
    while queue:
        index = queue.popleft()
        x = index % width
        y = index // width
        if x > 0:
            enqueue(index - 1)
        if x < width - 1:
            enqueue(index + 1)
        if y > 0:
            enqueue(index - width)
        if y < height - 1:
            enqueue(index + width)
    for index, mark in enumerate(visited):
        if mark:
            base = index * 4
            pixels[base] = pixels[base + 1] = pixels[base + 2] = pixels[base + 3] = 1.0
    image.pixels.foreach_set(pixels)
    image.save_render(str(path))
    bpy.data.images.remove(image)


def export_selected(path: Path, objects: list[bpy.types.Object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_animations=False,
        export_skins=False,
        export_apply=True,
        export_yup=True,
        export_draco_mesh_compression_enable=False,
    )
    bpy.ops.object.select_all(action="DESELECT")


def export_equipment_modules(armor_objects: list[bpy.types.Object]) -> dict[str, str]:
    exported: dict[str, str] = {}
    for item_key, name_prefixes in EQUIPMENT_EXPORTS.items():
        module_objects = [
            obj
            for obj in armor_objects
            if any(obj.name.startswith(prefix) for prefix in name_prefixes)
        ]
        if not module_objects:
            print(f"[manifest] SKIP {item_key}.glb: no matching objects")
            continue
        path = MODEL_DIR / f"{item_key}.glb"
        export_selected(path, module_objects)
        exported[item_key] = str(path)
    return exported


def main() -> None:
    if not BASE_BLEND.exists():
        raise FileNotFoundError(f"Missing baseline blend: {BASE_BLEND}")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE_BLEND))

    base_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not base_meshes:
        raise RuntimeError(f"No mesh found in {BASE_BLEND}")
    base = max(base_meshes, key=lambda obj: len(obj.data.vertices))
    base.name = "base_male_reference_body"
    base.hide_render = False
    base.hide_viewport = False
    for collection in base.users_collection:
        collection.hide_render = False
        collection.hide_viewport = False
    enhance_base_materials(base)

    base_bounds = bounds_for(base)
    armor_objects, report = build_armor(base, base_bounds)
    report["base_mesh"] = base.name

    apply_modifiers()
    setup_lighting_and_camera()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    export_selected(BASE_BODY_GLB, [base])
    export_selected(COMBINED_GLB, [base, *armor_objects])
    export_selected(ARMOR_ONLY_GLB, armor_objects)
    report["base_body_glb"] = str(BASE_BODY_GLB)
    report["equipment_modules"] = export_equipment_modules(armor_objects)

    setup_render(RENDER_PATH)
    bpy.ops.render.render(write_still=True)
    force_white_background(RENDER_PATH)

    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[WAR] SUCCESS BASE GLB: {BASE_BODY_GLB}")
    print(f"[WAR] SUCCESS COMBINED GLB: {COMBINED_GLB}")
    print(f"[WAR] SUCCESS ARMOR GLB: {ARMOR_ONLY_GLB}")
    print(f"[WAR] SUCCESS BLEND: {BLEND_PATH}")
    print(f"[WAR] SUCCESS RENDER: {RENDER_PATH}")
    print(f"[WAR] SUCCESS REPORT: {REPORT_PATH}")


if __name__ == "__main__":
    main()
