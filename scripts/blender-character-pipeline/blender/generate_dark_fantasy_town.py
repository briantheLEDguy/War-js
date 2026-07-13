"""Generate the original Aegis dark-fantasy town prop family.

The assets deliberately share materials, dimensions, and construction details so
editor-authored streets read as one believable place.  Geometry is authored in
Blender's Z-up space; the glTF exporter converts it to the runtime's Y-up space.
"""

from __future__ import annotations

import hashlib
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


PALETTE = {
    "stone": ((0.19, 0.18, 0.17, 1), 0.91, 0.06),
    "mortar": ((0.28, 0.27, 0.24, 1), 0.96, 0.03),
    "plaster": ((0.22, 0.23, 0.21, 1), 0.88, 0.05),
    "oak": ((0.105, 0.067, 0.038, 1), 0.84, 0.10),
    "aged_oak": ((0.21, 0.14, 0.075, 1), 0.82, 0.12),
    "slate": ((0.075, 0.072, 0.09, 1), 0.78, 0.10),
    "iron": ((0.055, 0.052, 0.05, 1), 0.49, 0.78),
    "glass": ((0.21, 0.12, 0.055, 1), 0.32, 0.04),
}


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    random.seed(731942)


def texture_pixels(base: tuple[float, float, float, float], seed: int, kind: str, size: int = 64) -> list[float]:
    rng = random.Random(seed)
    pixels: list[float] = []
    for y in range(size):
        for x in range(size):
            grain = math.sin((x * 0.31) + (y * 0.07) + seed) * 0.5
            mottling = math.sin((x * 0.08) - (y * 0.13) + seed * 0.17) * 0.5
            noise = rng.uniform(-0.5, 0.5)
            if kind == "normal":
                nx = 0.5 + (grain + noise) * 0.035
                ny = 0.5 + (mottling + noise) * 0.035
                pixels.extend((nx, ny, 0.985, 1.0))
            elif kind == "roughness":
                value = max(0.0, min(1.0, base[0] + (grain + noise) * 0.07))
                pixels.extend((value, value, value, 1.0))
            else:
                variation = 0.84 + grain * 0.08 + mottling * 0.06 + noise * 0.05
                pixels.extend((base[0] * variation, base[1] * variation, base[2] * variation, base[3]))
    return pixels


def image_node(nodes, name: str, pixels: list[float], size: int = 64):
    image = bpy.data.images.new(name, width=size, height=size, alpha=True)
    image.pixels.foreach_set(pixels)
    # Commit the pixel buffer before packing; otherwise Blender may embed the
    # newly allocated (black) image instead of the generated surface map.
    image.update()
    image.pack()
    node = nodes.new("ShaderNodeTexImage")
    node.image = image
    return node


def build_material(name: str, base, roughness: float, metallic: float) -> bpy.types.Material:
    material = bpy.data.materials.new(f"town_{name}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    seed = int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8], 16)
    color = image_node(nodes, f"{name}_base", texture_pixels(base, seed, "base"))
    rough = image_node(nodes, f"{name}_rough", texture_pixels((roughness,) * 4, seed + 17, "roughness"))
    normal_tex = image_node(nodes, f"{name}_normal", texture_pixels(base, seed + 31, "normal"))
    normal_tex.image.colorspace_settings.name = "Non-Color"
    rough.image.colorspace_settings.name = "Non-Color"
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = 0.42
    links.new(color.outputs["Color"], shader.inputs["Base Color"])
    links.new(rough.outputs["Color"], shader.inputs["Roughness"])
    links.new(normal_tex.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    shader.inputs["Metallic"].default_value = metallic
    if name == "glass":
        shader.inputs["Emission Color"].default_value = (0.32, 0.12, 0.025, 1)
        shader.inputs["Emission Strength"].default_value = 0.65
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def materials() -> dict[str, bpy.types.Material]:
    return {name: build_material(name, *values) for name, values in PALETTE.items()}


def apply_bevel(obj: bpy.types.Object, amount: float, segments: int = 2) -> None:
    modifier = obj.modifiers.new("worn_edges", "BEVEL")
    modifier.width = amount
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def box(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    bevel: float = 0.035,
    rotation: tuple[float, float, float] = (0, 0, 0),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0] / 2, scale[1] / 2, scale[2] / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel:
        apply_bevel(obj, min(bevel, min(scale) * 0.18))
    return obj


def cylinder(name: str, location, radius: float, depth: float, material, vertices: int = 12, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    apply_bevel(obj, min(0.035, radius * 0.15), 2)
    return obj


def beam_between(name: str, start, end, width: float, material) -> bpy.types.Object:
    start_v, end_v = Vector(start), Vector(end)
    delta = end_v - start_v
    midpoint = (start_v + end_v) / 2
    obj = box(name, midpoint, (width, width, delta.length), material, width * 0.12)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(delta.normalized())
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return obj


def wall_panel(name: str, width: float, height: float, material, timber, dark: bool = False):
    parts = [box(f"{name}_infill", (0, 0, height / 2), (width, 0.34, height), material, 0.045)]
    frame = timber["oak" if dark else "aged_oak"]
    parts.extend([
        box(f"{name}_post_l", (-width / 2 + 0.13, -0.2, height / 2), (0.26, 0.28, height + 0.15), frame, 0.025),
        box(f"{name}_post_r", (width / 2 - 0.13, -0.2, height / 2), (0.26, 0.28, height + 0.15), frame, 0.025),
        box(f"{name}_sill", (0, -0.2, 0.15), (width, 0.28, 0.3), frame, 0.025),
        box(f"{name}_rail", (0, -0.2, height - 0.15), (width, 0.28, 0.3), frame, 0.025),
        beam_between(f"{name}_brace", (-width / 2 + 0.2, -0.2, 0.25), (width / 2 - 0.2, -0.2, height - 0.25), 0.18, frame),
    ])
    return parts


def stone_wall(name: str, width: float, height: float, depth: float, mats, courses: int = 5):
    parts = []
    row_h = height / courses
    for row in range(courses):
        count = max(2, round(width / (1.1 if row % 2 else 1.35)))
        stone_w = width / count
        for col in range(count):
            seed = row * 101 + col * 17 + len(name)
            rng = random.Random(seed)
            x = -width / 2 + stone_w * (col + 0.5) + (0.08 if row % 2 else 0)
            z = row_h * (row + 0.5)
            part = box(
                f"{name}_stone_{row}_{col}",
                (x, rng.uniform(-0.04, 0.04), z),
                (stone_w * rng.uniform(0.90, 0.98), depth * rng.uniform(0.9, 1.08), row_h * rng.uniform(0.82, 0.94)),
                mats["stone"],
                0.06,
                (rng.uniform(-0.025, 0.025), rng.uniform(-0.02, 0.02), rng.uniform(-0.025, 0.025)),
            )
            parts.append(part)
    return parts


def door(name: str, width: float, height: float, mats, ornate: bool = False):
    parts = [box(f"{name}_leaf", (0, 0, height / 2), (width, 0.18, height), mats["oak"], 0.055)]
    for x in (-width * 0.34, 0, width * 0.34):
        parts.append(box(f"{name}_plank_{x}", (x, -0.105, height / 2), (0.055, 0.045, height * 0.92), mats["aged_oak"], 0.012))
    for z in (height * 0.26, height * 0.74):
        parts.append(box(f"{name}_strap_{z}", (0, -0.15, z), (width * 0.94, 0.045, 0.085), mats["iron"], 0.018))
    parts.append(cylinder(f"{name}_ring", (width * 0.25, -0.19, height * 0.53), 0.07, 0.035, mats["iron"], 16, (math.pi / 2, 0, 0)))
    if ornate:
        parts.extend([
            beam_between(f"{name}_brace_l", (-width * 0.42, -0.15, 0.15), (0, -0.15, height - 0.18), 0.075, mats["iron"]),
            beam_between(f"{name}_brace_r", (width * 0.42, -0.15, 0.15), (0, -0.15, height - 0.18), 0.075, mats["iron"]),
        ])
    return parts


def window(name: str, width: float, height: float, mats, diamond: bool = False):
    parts = [box(f"{name}_glass", (0, 0, height / 2), (width * 0.78, 0.06, height * 0.78), mats["glass"], 0.01)]
    frame = mats["iron"] if diamond else mats["oak"]
    for x in (-width / 2, width / 2):
        parts.append(box(f"{name}_jamb_{x}", (x, -0.05, height / 2), (0.12, 0.15, height + 0.14), frame, 0.022))
    for z in (0, height):
        parts.append(box(f"{name}_rail_{z}", (0, -0.05, z), (width + 0.12, 0.15, 0.12), frame, 0.022))
    if diamond:
        for offset in (-0.27, 0, 0.27):
            parts.append(beam_between(f"{name}_lead_a_{offset}", (-width * 0.42, -0.1, height * (0.12 + offset)), (width * 0.42, -0.1, height * (0.88 + offset)), 0.025, mats["iron"]))
            parts.append(beam_between(f"{name}_lead_b_{offset}", (-width * 0.42, -0.1, height * (0.88 + offset)), (width * 0.42, -0.1, height * (0.12 + offset)), 0.025, mats["iron"]))
    else:
        parts.extend([
            box(f"{name}_mullion", (0, -0.1, height / 2), (0.065, 0.06, height * 0.8), frame, 0.012),
            box(f"{name}_transom", (0, -0.1, height / 2), (width * 0.8, 0.06, 0.065), frame, 0.012),
        ])
    return parts


def roof_shell(name: str, width: float, depth: float, base_z: float, rise: float, mats):
    """Build a closed triangular-prism roof beneath the decorative slate rows.

    The shell guarantees that roofs remain opaque from every camera angle even
    when glTF backface culling is enabled. The slightly inset eaves leave the
    overlapping slate edges and timber gables readable without exposing gaps.
    """
    half_width = width / 2
    half_depth = depth / 2
    vertices = [
        (-half_width, -half_depth, base_z),
        (half_width, -half_depth, base_z),
        (0, -half_depth, base_z + rise),
        (-half_width, half_depth, base_z),
        (half_width, half_depth, base_z),
        (0, half_depth, base_z + rise),
    ]
    faces = [
        (0, 1, 2),
        (5, 4, 3),
        (0, 2, 5, 3),
        (1, 4, 5, 2),
        (0, 3, 4, 1),
    ]
    mesh = bpy.data.meshes.new(f"{name}_shell_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(mats["slate"])
    shell = bpy.data.objects.new(f"{name}_shell", mesh)
    bpy.context.collection.objects.link(shell)
    apply_bevel(shell, 0.045, 2)
    return shell


def slate_roof(name: str, width: float, depth: float, base_z: float, mats, pitch: float = 0.72):
    half_run = depth / 2
    rise = half_run * pitch
    parts = [roof_shell(name, width * 0.99, depth * 0.99, base_z - 0.025, rise, mats)]
    rows = max(5, round(depth / 0.72))
    cols = max(8, round(width / 0.62))
    # Individual slates overlap both across and down the pitch. They provide
    # silhouette/detail only; the closed shell provides the weather-tight roof.
    tile_w = width / cols * 1.08
    tile_l = half_run / rows * 1.78
    for side in (-1, 1):
        # Positive-Y and negative-Y roof faces slope in opposite directions.
        # The prior sign made the slate boxes cut across the shell like rafters.
        angle = -side * math.atan(pitch)
        for row in range(rows):
            run = half_run * (row + 0.5) / rows
            y = side * (half_run - run)
            z = base_z + run * pitch + 0.055
            for col in range(cols):
                rng = random.Random((side + 2) * 100000 + row * 1000 + col)
                stagger = (width / cols * 0.5) if row % 2 else 0.0
                x = -width / 2 + width * (col + 0.5) / cols + stagger + rng.uniform(-0.025, 0.025)
                if x > width / 2:
                    x -= width
                parts.append(box(
                    f"{name}_slate_{side}_{row}_{col}",
                    (x, y, z),
                    (tile_w, tile_l, 0.085),
                    mats["slate"],
                    0.018,
                    (angle, rng.uniform(-0.018, 0.018), rng.uniform(-0.025, 0.025)),
                ))
    parts.append(cylinder(f"{name}_ridge", (0, 0, base_z + rise + 0.05), 0.14, width + 0.25, mats["slate"], 10, (0, math.pi / 2, 0)))
    return parts


def gable(name: str, width: float, y: float, base_z: float, rise: float, mats):
    depth = 0.22
    vertices = [
        (-width / 2, y - depth / 2, base_z), (width / 2, y - depth / 2, base_z), (0, y - depth / 2, base_z + rise),
        (-width / 2, y + depth / 2, base_z), (width / 2, y + depth / 2, base_z), (0, y + depth / 2, base_z + rise),
    ]
    faces = [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mats["plaster"])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    apply_bevel(obj, 0.035, 2)
    parts = [obj]
    parts += [
        beam_between(f"{name}_barge_l", (-width / 2, y - 0.14, base_z), (0, y - 0.14, base_z + rise), 0.2, mats["oak"]),
        beam_between(f"{name}_barge_r", (width / 2, y - 0.14, base_z), (0, y - 0.14, base_z + rise), 0.2, mats["oak"]),
        box(f"{name}_tie", (0, y - 0.14, base_z + 0.18), (width, 0.2, 0.22), mats["oak"], 0.025),
        box(f"{name}_king_post", (0, y - 0.14, base_z + rise * 0.48), (0.22, 0.2, rise * 0.9), mats["oak"], 0.025),
    ]
    return parts


def place_window_on_side(parts, name: str, x: float, y: float, z: float, mats):
    side_window = window(name, 1.2, 1.65, mats, True)
    for obj in side_window:
        obj.rotation_euler.z += math.pi / 2
        obj.location += Vector((x, y, z))
    parts += side_window


def timber_facade(prefix: str, width: float, depth: float, z0: float, height: float, mats):
    parts = [box(f"{prefix}_upper", (0, 0, z0 + height / 2), (width, depth, height), mats["plaster"], 0.08)]
    for face_y in (-depth / 2 - 0.04, depth / 2 + 0.04):
        for x in (-width / 2 + 0.18, -width / 4, 0, width / 4, width / 2 - 0.18):
            parts.append(box(f"{prefix}_post", (x, face_y, z0 + height / 2), (0.24, 0.2, height + 0.12), mats["oak"], 0.025))
        for z in (z0 + 0.16, z0 + height / 2, z0 + height - 0.16):
            parts.append(box(f"{prefix}_rail", (0, face_y, z), (width + 0.12, 0.2, 0.22), mats["oak"], 0.025))
    return parts


def house_one(mats):
    parts = stone_wall("house1_foundation", 9.4, 1.35, 7.2, mats, 4)
    parts += timber_facade("house1", 9.8, 7.4, 1.28, 4.7, mats)
    parts += gable("house1_front_gable", 9.8, -3.75, 5.9, 3.25, mats)
    parts += gable("house1_back_gable", 9.8, 3.75, 5.9, 3.25, mats)
    parts += slate_roof("house1", 10.6, 8.4, 5.9, mats, 0.78)
    entrance = door("house1_door", 1.55, 2.65, mats, True)
    for obj in entrance:
        obj.location += Vector((0, -3.82, 0.05))
    parts += entrance
    for x in (-2.7, 2.7):
        win = window(f"house1_window_{x}", 1.25, 1.75, mats, True)
        for obj in win:
            obj.location += Vector((x, -3.84, 2.8))
        parts += win
    place_window_on_side(parts, "house1_side_window", 4.96, 0.3, 2.8, mats)
    parts += chimney(mats, (3.0, 1.35, 5.3), 1.0)
    return parts


def house_two(mats):
    parts = stone_wall("house2_foundation", 11.8, 1.55, 8.7, mats, 5)
    parts += timber_facade("house2", 12.2, 9.0, 1.48, 5.9, mats)
    parts += gable("house2_front_gable", 12.2, -4.55, 7.25, 4.3, mats)
    parts += gable("house2_back_gable", 12.2, 4.55, 7.25, 4.3, mats)
    parts += slate_roof("house2", 13.1, 10.0, 7.25, mats, 0.86)
    # Projecting crooked front bay gives the larger house a readable silhouette.
    parts += stone_wall("house2_bay", 3.3, 1.15, 1.65, mats, 3)
    for obj in parts[-12:]:
        obj.location += Vector((-3.3, -5.15, 0))
    bay = box("house2_bay_plaster", (-3.3, -5.05, 3.55), (3.65, 1.7, 4.9), mats["plaster"], 0.07)
    parts.append(bay)
    for z in (1.3, 3.15, 5.6):
        parts.append(box("house2_bay_rail", (-3.3, -5.98, z), (3.85, 0.22, 0.24), mats["oak"], 0.025))
    for x in (-4.85, -3.3, -1.75):
        parts.append(box("house2_bay_post", (x, -5.98, 3.55), (0.24, 0.22, 4.9), mats["oak"], 0.025))
    entrance = door("house2_door", 1.7, 2.9, mats, True)
    for obj in entrance:
        obj.location += Vector((1.8, -4.62, 0.05))
    parts += entrance
    for x, z in ((-3.3, 2.0), (-3.3, 4.1), (4.1, 3.2)):
        win = window(f"house2_window_{x}_{z}", 1.35, 1.8, mats, True)
        for obj in win:
            obj.location += Vector((x, -5.98 if x < 0 else -4.64, z))
        parts += win
    place_window_on_side(parts, "house2_side_window_low", 6.16, 0.6, 2.3, mats)
    place_window_on_side(parts, "house2_side_window_high", 6.16, 0.6, 4.7, mats)
    parts += chimney(mats, (4.25, 1.75, 6.3), 1.15)
    return parts


def chimney(mats, location=(0, 0, 0), scale=1.0):
    x0, y0, z0 = location
    parts = []
    for row in range(7):
        for col in range(4):
            angle = col * math.pi / 2
            radius = 0.38 * scale
            parts.append(box(
                f"chimney_brick_{row}_{col}",
                (x0 + math.cos(angle) * radius, y0 + math.sin(angle) * radius, z0 + row * 0.28 * scale),
                (0.62 * scale, 0.3 * scale, 0.24 * scale), mats["stone"], 0.035,
                (0, 0, angle),
            ))
    parts.append(box("chimney_cap", (x0, y0, z0 + 2.05 * scale), (1.15 * scale, 1.15 * scale, 0.22 * scale), mats["stone"], 0.055))
    return parts


def roof_module(mats):
    return slate_roof("roof_module", 7.2, 6.0, 0.08, mats, 0.74)


def roof_plank(mats, length: float, name: str):
    parts = [box(name, (0, 0, 0.08), (length, 1.2, 0.16), mats["slate"], 0.035)]
    for x in [(-length / 2 + 0.18) + i * 0.42 for i in range(max(1, int(length / 0.42)))]:
        parts.append(box(f"{name}_slate", (x, -0.03, 0.18), (0.38, 1.08, 0.07), mats["slate"], 0.018, (0, 0, random.uniform(-0.025, 0.025))))
    return parts


def rock_wall(mats, width: float, height: float, name: str):
    return stone_wall(name, width, height, 0.7, mats, max(2, round(height / 0.42)))


def spire(mats):
    parts = []
    for level, (radius, height) in enumerate(((0.72, 0.9), (0.52, 0.8), (0.34, 0.72), (0.18, 0.58))):
        z = sum(item[1] for item in ((0.72, 0.9), (0.52, 0.8), (0.34, 0.72), (0.18, 0.58))[:level])
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=radius, radius2=radius * 0.45, depth=height, location=(0, 0, z + height / 2))
        obj = bpy.context.object
        obj.name = f"spire_{level}"
        obj.data.materials.append(mats["slate"])
        apply_bevel(obj, 0.025)
        parts.append(obj)
    parts.append(cylinder("spire_finial", (0, 0, 3.15), 0.055, 0.7, mats["iron"], 10))
    return parts


def plank_arc(mats):
    parts = []
    segments = 11
    radius = 2.15
    for index in range(segments):
        angle = math.pi * index / (segments - 1)
        x = math.cos(angle) * radius
        z = math.sin(angle) * radius
        parts.append(box("arc_segment", (x, 0, z), (0.56, 0.42, 0.28), mats["oak"], 0.045, (0, angle - math.pi / 2, 0)))
    return parts


def town_castle(mats):
    """A grounded, monumental keep designed as the visual heart of a capital."""
    parts = [
        box("castle_keep", (0, 2.5, 8.5), (25.0, 20.0, 17.0), mats["stone"], 0.16),
        box("castle_high_keep", (0, 5.0, 17.0), (14.0, 14.0, 17.0), mats["stone"], 0.14),
        box("castle_gatehouse", (0, -10.0, 6.0), (11.0, 5.0, 12.0), mats["stone"], 0.13),
    ]
    # Four heavy round towers, capped with steep slate roofs.
    for label, x, y in (("sw", -14.0, -8.5), ("se", 14.0, -8.5), ("nw", -14.0, 12.0), ("ne", 14.0, 12.0)):
        parts.append(cylinder(f"castle_tower_{label}", (x, y, 9.0), 4.3, 18.0, mats["stone"], 20))
        parts.append(cylinder(f"castle_tower_band_low_{label}", (x, y, 4.2), 4.42, 0.48, mats["mortar"], 20))
        parts.append(cylinder(f"castle_tower_band_high_{label}", (x, y, 13.0), 4.42, 0.48, mats["mortar"], 20))
        if y < 0:
            parts.append(box(f"castle_arrow_slit_{label}", (x, y - 4.31, 9.0), (0.28, 0.12, 2.1), mats["iron"], 0.035))
        bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=5.1, radius2=0.35, depth=7.0, location=(x, y, 21.5))
        roof = bpy.context.object
        roof.name = f"castle_tower_roof_{label}"
        roof.data.materials.append(mats["slate"])
        apply_bevel(roof, 0.055, 2)
        parts.append(roof)
        parts.append(cylinder(f"castle_finial_{label}", (x, y, 25.4), 0.08, 1.8, mats["iron"], 10))

    # A continuous steep roof avoids distant aliasing while retaining slate PBR detail.
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=10.5, radius2=0.45, depth=9.0, location=(0, 5.0, 30.0), rotation=(0, 0, math.pi / 4))
    high_roof = bpy.context.object
    high_roof.name = "castle_high_roof"
    high_roof.data.materials.append(mats["slate"])
    apply_bevel(high_roof, 0.07, 3)
    parts.append(high_roof)
    for x in (-11.0, -7.0, -3.0, 3.0, 7.0, 11.0):
        parts.append(box("castle_front_merlon", (x, -8.0, 17.9), (1.8, 1.5, 2.2), mats["stone"], 0.08))
        parts.append(box("castle_rear_merlon", (x, 13.0, 17.9), (1.8, 1.5, 2.2), mats["stone"], 0.08))
    for y in (-4.5, 0.0, 4.5, 9.0):
        parts.append(box("castle_west_merlon", (-12.5, y, 17.9), (1.5, 1.8, 2.2), mats["stone"], 0.08))
        parts.append(box("castle_east_merlon", (12.5, y, 17.9), (1.5, 1.8, 2.2), mats["stone"], 0.08))

    # Buttresses and an iron-bound gate give the lower mass believable construction detail.
    for x in (-10.5, -5.3, 5.3, 10.5):
        parts.append(box("castle_front_buttress", (x, -8.7, 5.0), (1.35, 2.2, 10.0), mats["stone"], 0.10))
    front_masonry = stone_wall("castle_front_masonry", 24.0, 15.2, 0.42, mats, 11)
    for obj in front_masonry:
        obj.location += Vector((0, -7.72, 0.4))
    parts += front_masonry
    gate = door("castle_main_gate", 4.5, 6.8, mats, True)
    for obj in gate:
        obj.location += Vector((0, -12.62, 0.08))
    parts += gate
    for x in (-7.2, 7.2):
        for z in (6.0, 11.0):
            win = window(f"castle_window_{x}_{z}", 1.25, 2.4, mats, True)
            for obj in win:
                obj.location += Vector((x, -8.62, z))
            parts += win
    parts += chimney(mats, (5.0, 7.0, 24.0), 1.25)
    return parts


def fortress_wall(mats):
    """A repeatable high curtain wall with a usable-looking crenellated walk."""
    parts = [
        box("fortress_wall_core", (0, 0, 3.2), (12.0, 2.65, 6.4), mats["stone"], 0.12),
        box("fortress_wall_crown", (0, 0, 6.35), (12.35, 2.9, 0.55), mats["mortar"], 0.07),
        box("fortress_wall_walk", (0, 0, 6.72), (11.75, 2.35, 0.20), mats["slate"], 0.04),
    ]
    for side in (-1, 1):
        face = stone_wall("fortress_wall_face", 11.55, 5.95, 0.20, mats, 10)
        for obj in face:
            obj.location += Vector((0, side * 1.38, 0.10))
        parts += face
    for x in (-5.15, -3.1, -1.05, 1.05, 3.1, 5.15):
        parts.append(box("fortress_wall_merlon", (x, 0, 7.45), (1.28, 2.9, 1.75), mats["stone"], 0.07))
    for x in (-4.5, 4.5):
        parts.append(box("fortress_wall_buttress_front", (x, -1.58, 2.65), (1.2, 0.72, 5.3), mats["stone"], 0.08))
        parts.append(box("fortress_wall_buttress_back", (x, 1.58, 2.65), (1.2, 0.72, 5.3), mats["stone"], 0.08))
    for x in (-2.25, 2.25):
        parts.append(box("fortress_wall_arrow_slit", (x, -1.48, 4.0), (0.28, 0.12, 1.7), mats["iron"], 0.02))
    return parts


def fortress_corner_tower(mats):
    """An open-topped, battered tower that connects cleanly to curtain walls."""
    parts = [
        cylinder("fortress_tower_base", (0, 0, 0.65), 5.15, 1.3, mats["mortar"], 20),
        cylinder("fortress_tower_core", (0, 0, 6.7), 4.65, 12.0, mats["stone"], 20),
        cylinder("fortress_tower_lower_band", (0, 0, 2.2), 4.84, 0.48, mats["mortar"], 20),
        cylinder("fortress_tower_upper_band", (0, 0, 10.8), 4.84, 0.48, mats["mortar"], 20),
        cylinder("fortress_tower_walk", (0, 0, 12.55), 5.08, 0.42, mats["slate"], 20),
    ]
    for index in range(10):
        angle = (index / 10) * math.pi * 2
        x = math.cos(angle) * 4.35
        y = math.sin(angle) * 4.35
        parts.append(box(
            "fortress_tower_merlon",
            (x, y, 13.55),
            (1.35, 1.35, 1.9),
            mats["stone"],
            0.07,
            (0, 0, angle),
        ))
    for angle in (0, math.pi / 2, math.pi, math.pi * 1.5):
        x = math.cos(angle) * 4.67
        y = math.sin(angle) * 4.67
        parts.append(box("fortress_tower_arrow_slit", (x, y, 7.1), (0.16, 0.7, 1.9), mats["iron"], 0.02, (0, 0, angle)))
    for x, y in ((-3.8, -3.8), (3.8, -3.8), (-3.8, 3.8), (3.8, 3.8)):
        parts.append(box("fortress_tower_buttress", (x, y, 2.6), (1.05, 1.05, 5.2), mats["stone"], 0.08))
    return parts


def fortress_gatehouse(mats):
    """A gateway shell. The playable portcullis remains a separate animated prop."""
    parts = [
        box("fortress_gatehouse_left_jamb", (-10.0, 0, 4.15), (3.2, 5.4, 8.3), mats["stone"], 0.12),
        box("fortress_gatehouse_right_jamb", (10.0, 0, 4.15), (3.2, 5.4, 8.3), mats["stone"], 0.12),
        box("fortress_gatehouse_lintel", (0, 0, 8.55), (26.0, 5.4, 3.8), mats["stone"], 0.12),
        box("fortress_gatehouse_walk", (0, 0, 10.3), (26.6, 5.8, 0.42), mats["slate"], 0.06),
    ]
    for x in (-10.0, 10.0):
        parts.extend([
            cylinder("fortress_gatehouse_tower", (x, 0, 6.8), 3.45, 13.2, mats["stone"], 18),
            cylinder("fortress_gatehouse_tower_band", (x, 0, 10.7), 3.62, 0.44, mats["mortar"], 18),
        ])
    for x in (-11.5, -8.2, -4.9, -1.6, 1.6, 4.9, 8.2, 11.5):
        parts.append(box("fortress_gatehouse_merlon", (x, 0, 11.4), (1.38, 5.8, 1.85), mats["stone"], 0.07))
    for side in (-1, 1):
        for z in (3.0, 6.1):
            parts.append(box("fortress_gatehouse_iron_slit", (side * 10.0, -2.77, z), (0.32, 0.14, 1.45), mats["iron"], 0.02))
        parts.append(box("fortress_gatehouse_buttress", (side * 11.0, -3.0, 2.55), (1.25, 0.82, 5.1), mats["stone"], 0.08))
    for index in range(9):
        x = -8.0 + index * 2.0
        parts.append(box("fortress_gatehouse_arch", (x, -2.82, 7.15 + 0.65 * math.sin((index / 8) * math.pi)), (1.12, 0.28, 0.72), mats["mortar"], 0.04))
    return parts


def fortress_wall_stairs(mats):
    """A freestanding stair set for connecting a street to the parapet level."""
    parts = []
    step_count = 11
    step_height = 0.58
    for index in range(step_count):
        height = (index + 1) * step_height
        depth = 0.98
        parts.append(box(
            "fortress_stair_tread",
            (0, -5.0 + index * depth, height / 2),
            (6.2 - min(index * 0.07, 0.55), depth + 0.04, height),
            mats["stone"],
            0.05,
        ))
        if index % 2 == 0:
            parts.append(box("fortress_stair_edge", (0, -5.0 + index * depth - 0.48, height), (6.25, 0.12, 0.14), mats["mortar"], 0.02))
    for side in (-1, 1):
        parts.append(box("fortress_stair_sidewall", (side * 3.35, 0, 3.55), (0.52, 11.2, 7.1), mats["stone"], 0.07))
        for index in range(4):
            parts.append(box("fortress_stair_side_merlon", (side * 3.35, -4.1 + index * 3.0, 7.65), (0.72, 1.05, 1.1), mats["stone"], 0.05))
    parts.append(box("fortress_stair_landing", (0, 5.6, 6.55), (7.2, 2.2, 0.44), mats["slate"], 0.05))
    return parts


def fortress_brazier(mats):
    """A low, ember-lit brazier for gate courts and wall approaches."""
    parts = [
        cylinder("fortress_brazier_plinth", (0, 0, 0.3), 1.32, 0.6, mats["stone"], 16),
        cylinder("fortress_brazier_iron_bowl", (0, 0, 1.72), 0.88, 0.48, mats["iron"], 16),
        cylinder("fortress_brazier_coals", (0, 0, 1.88), 0.56, 0.18, mats["glass"], 14),
    ]
    for x, y in ((-0.57, -0.57), (0.57, -0.57), (-0.57, 0.57), (0.57, 0.57)):
        parts.append(box("fortress_brazier_leg", (x, y, 1.0), (0.18, 0.18, 1.25), mats["iron"], 0.03))
    for index, (radius, height) in enumerate(((0.54, 1.32), (0.34, 1.75), (0.16, 1.35))):
        bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=radius, radius2=0.03, depth=height, location=(0.14 * math.sin(index), 0.12 * math.cos(index), 2.15 + height / 2))
        flame = bpy.context.object
        flame.name = f"fortress_brazier_flame_{index}"
        flame.data.materials.append(mats["glass"])
        apply_bevel(flame, 0.025)
        parts.append(flame)
    return parts


def fortress_banner(mats):
    """A neutral torn banner that can be realm-colored by its surrounding scene."""
    parts = [
        cylinder("fortress_banner_stone_base", (0, 0, 0.28), 0.75, 0.56, mats["stone"], 12),
        cylinder("fortress_banner_pole", (0, 0, 4.5), 0.09, 8.5, mats["iron"], 10),
        box("fortress_banner_crossbar", (1.55, 0, 8.2), (3.3, 0.16, 0.16), mats["iron"], 0.025),
        box("fortress_banner_cloth_main", (1.5, 0.05, 6.65), (2.95, 0.12, 3.0), mats["aged_oak"], 0.05),
        box("fortress_banner_cloth_tail_left", (0.74, 0.05, 4.85), (0.68, 0.12, 1.25), mats["aged_oak"], 0.04, (0, 0, 0.18)),
        box("fortress_banner_cloth_tail_right", (2.32, 0.05, 4.65), (0.72, 0.12, 1.62), mats["aged_oak"], 0.04, (0, 0, -0.16)),
    ]
    for z in (5.7, 7.45):
        parts.append(box("fortress_banner_hem", (1.5, -0.05, z), (3.05, 0.18, 0.11), mats["iron"], 0.02))
    return parts


def fortress_barricade(mats):
    """A rough field barricade for staging siege approaches without IP-specific symbols."""
    parts = [
        box("fortress_barricade_rail_low", (0, 0, 0.9), (6.4, 0.30, 0.30), mats["aged_oak"], 0.04, (0, 0.18, 0)),
        box("fortress_barricade_rail_high", (0, 0, 2.0), (6.4, 0.30, 0.30), mats["aged_oak"], 0.04, (0, -0.18, 0)),
    ]
    for index in range(7):
        x = -2.7 + index * 0.9
        bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=0.24, radius2=0.035, depth=3.5, location=(x, 0, 1.75), rotation=(0, 0.28 if index % 2 else -0.28, 0))
        stake = bpy.context.object
        stake.name = "fortress_barricade_stake"
        stake.data.materials.append(mats["oak"])
        apply_bevel(stake, 0.025)
        parts.append(stake)
    for x in (-2.9, 2.9):
        parts.append(box("fortress_barricade_foot", (x, 0, 0.3), (0.65, 2.6, 0.36), mats["stone"], 0.05))
    return parts


def build_variant(variant: str, mats):
    if variant == "house_1": return house_one(mats)
    if variant == "house_2": return house_two(mats)
    if variant == "roof": return roof_module(mats)
    if variant == "chimney": return chimney(mats)
    if variant == "door": return door("door", 1.6, 2.8, mats, False)
    if variant == "door_2": return door("door_ornate", 1.6, 2.8, mats, True)
    if variant == "window": return window("window", 1.6, 1.9, mats, False)
    if variant == "diamond_window": return window("diamond_window", 1.6, 1.9, mats, True)
    if variant == "wooden_wall_dark": return wall_panel("dark_wall", 5.0, 3.2, mats["plaster"], mats, True)
    if variant == "wooden_wall_light": return wall_panel("light_wall", 5.0, 3.2, mats["mortar"], mats, False)
    if variant == "rock_wall_small": return rock_wall(mats, 3.5, 1.7, "small_wall")
    if variant == "rock_wall_large": return rock_wall(mats, 6.2, 2.4, "large_wall")
    if variant == "horizontal_beam": return [box("horizontal_beam", (0, 0, 0.15), (5.0, 0.34, 0.3), mats["oak"], 0.045)]
    if variant == "vertical_beam": return [box("vertical_beam", (0, 0, 1.6), (0.34, 0.34, 3.2), mats["oak"], 0.045)]
    if variant == "roof_plank_small": return roof_plank(mats, 2.5, "small_roof_plank")
    if variant == "roof_plank_medium": return roof_plank(mats, 3.6, "medium_roof_plank")
    if variant == "roof_plank_large": return roof_plank(mats, 4.8, "large_roof_plank")
    if variant == "spire": return spire(mats)
    if variant == "plank_arc": return plank_arc(mats)
    if variant == "castle": return town_castle(mats)
    if variant == "fortress_wall": return fortress_wall(mats)
    if variant == "fortress_corner_tower": return fortress_corner_tower(mats)
    if variant == "fortress_gatehouse": return fortress_gatehouse(mats)
    if variant == "fortress_wall_stairs": return fortress_wall_stairs(mats)
    if variant == "fortress_brazier": return fortress_brazier(mats)
    if variant == "fortress_banner": return fortress_banner(mats)
    if variant == "fortress_barricade": return fortress_barricade(mats)
    raise RuntimeError(f"Unknown dark-fantasy town variant: {variant}")


def join_by_material(parts: list[bpy.types.Object]) -> list[bpy.types.Object]:
    grouped: dict[str, list[bpy.types.Object]] = {}
    for obj in parts:
        if obj.type != "MESH" or not obj.data.materials:
            continue
        grouped.setdefault(obj.data.materials[0].name, []).append(obj)
    joined = []
    for material_name, objects in grouped.items():
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        result = bpy.context.object
        result.name = material_name.removeprefix("town_")
        joined.append(result)
    bpy.ops.object.select_all(action="DESELECT")
    return joined


def generate_dark_fantasy_town(manifest: dict, output_path: Path, artifact_dir: str | None, write_qc_report, apply_metadata, export_selected) -> None:
    reset_scene()
    mats = materials()
    variant = manifest["generator"]["preset"].removeprefix("dark_fantasy_town_")
    objects = join_by_material(build_variant(variant, mats))
    apply_metadata(objects, manifest)
    export_selected(output_path, objects)
    write_qc_report(
        manifest,
        output_path,
        artifact_dir,
        {
            "generator": "original_dark_fantasy_town_v2",
            "variant": variant,
            "materials": sorted(mats),
            "artDirection": "realistic weathered dark-fantasy medieval architecture",
        },
        objects,
    )
