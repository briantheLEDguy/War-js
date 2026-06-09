"""Neutral procedural mesh helpers for manifest-backed Blender generators."""

from __future__ import annotations

import math
import bpy
from mathutils import Vector


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _linear(hex_color: str) -> tuple[float, float, float, float]:
    r, g, b = _hex_to_rgb(hex_color)
    return (r ** 2.2, g ** 2.2, b ** 2.2, 1.0)


def _noise(x: float, y: float, seed: float) -> float:
    v = math.sin(x * 12.9898 + y * 78.233 + seed * 37.719) * 43758.5453
    return v - math.floor(v)


def _mix(a: tuple[float, float, float], b: tuple[float, float, float], t: float) -> tuple[float, float, float]:
    return (a[0] * (1 - t) + b[0] * t, a[1] * (1 - t) + b[1] * t, a[2] * (1 - t) + b[2] * t)


def _make_texture(name: str, base_hex: str, kind: str, size: int = 384) -> bpy.types.Image:
    base = _hex_to_rgb(base_hex)
    dark = tuple(c * 0.45 for c in base)
    light = tuple(min(1.0, c * 1.5 + 0.08) for c in base)
    img = bpy.data.images.new(name=name, width=size, height=size, alpha=True)
    pixels: list[float] = []
    seed = sum(ord(ch) for ch in name) * 0.013
    for y in range(size):
        v = y / max(1, size - 1)
        for x in range(size):
            u = x / max(1, size - 1)
            n1 = _noise(u * 11, v * 11, seed)
            n2 = _noise(u * 41, v * 41, seed + 4.5)
            color = base
            if kind == "metal":
                scratch = 1.0 if (
                    n2 > 0.935
                    or (abs(math.sin((u * 8.0 + v * 31.0 + seed) * math.pi)) < 0.035 and n1 > 0.62)
                ) else 0.0
                grime = 0.18 + 0.32 * n1
                color = _mix(light if scratch else base, dark, grime)
            elif kind == "brass":
                tarnish = 0.18 + 0.24 * n1 + (0.20 if n2 > 0.92 else 0.0)
                color = _mix(light, dark, tarnish)
            elif kind == "cloth":
                weave = 0.08 * math.sin(u * math.pi * 72) + 0.08 * math.sin(v * math.pi * 80)
                stain = 0.10 if n2 > 0.90 else 0.0
                color = _mix(base, dark, 0.22 * n1 + stain - weave)
            elif kind == "leather":
                color = _mix(base, dark, 0.28 * n1 + 0.08 * n2)
            elif kind == "skin":
                color = _mix(base, light, 0.08 * n1)
            pixels.extend([max(0, min(1, color[0])), max(0, min(1, color[1])), max(0, min(1, color[2])), 1])
    img.pixels.foreach_set(pixels)
    img.update()
    img.pack()
    return img


def textured_material(name: str, base_hex: str, kind: str, roughness: float, metallic: float = 0.0, size: int = 384) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = _linear(base_hex)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    tex = nodes.new(type="ShaderNodeTexImage")
    tex.image = _make_texture(f"{name}_packed_texture", base_hex, kind, size=size)
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def flat_material(name: str, base_hex: str, roughness: float, metallic: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = _linear(base_hex)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def mesh_obj(name: str, verts: list[tuple[float, float, float]], faces: list[tuple[int, ...]], mat: bpy.types.Material, smooth: bool = True) -> bpy.types.Object:
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


def add_solidify(obj: bpy.types.Object, thickness: float) -> None:
    solid = obj.modifiers.new(name="shell_thickness", type="SOLIDIFY")
    solid.thickness = thickness
    solid.offset = 0.0
    obj.modifiers.new(name="shell_weighted_normals", type="WEIGHTED_NORMAL")


def _section_center(axis: str, sec: dict) -> tuple[float, float, float]:
    coord = sec["coord"]
    if axis == "y":
        return (sec.get("cx", 0.0), coord, sec.get("cz", 0.0))
    if axis == "x":
        return (coord, sec.get("cy", 0.0), sec.get("cz", 0.0))
    return (sec.get("cx", 0.0), sec.get("cy", 0.0), coord)


def loft_axis(name: str, axis: str, sections: list[dict], mat: bpy.types.Material, segments: int = 48, cap: bool = True) -> bpy.types.Object:
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for si, sec in enumerate(sections):
        coord = sec["coord"]
        cx, cy, cz = sec.get("cx", 0.0), sec.get("cy", 0.0), sec.get("cz", 0.0)
        rx, ry, rz = sec.get("rx", sec.get("r", 0.1)), sec.get("ry", sec.get("r", 0.1)), sec.get("rz", sec.get("r", 0.1))
        squash = sec.get("squash", 0.0)
        for i in range(segments):
            a = math.tau * i / segments
            ripple = 1 + squash * math.sin(a * 2 + si)
            if axis == "y":
                verts.append((cx + math.cos(a) * rx * ripple, coord, cz + math.sin(a) * rz * ripple))
            elif axis == "x":
                verts.append((coord, cy + math.cos(a) * ry * ripple, cz + math.sin(a) * rz * ripple))
            else:
                verts.append((cx + math.cos(a) * rx * ripple, cy + math.sin(a) * ry * ripple, coord))
    for si in range(len(sections) - 1):
        row, nxt = si * segments, (si + 1) * segments
        for i in range(segments):
            faces.append((row + i, row + (i + 1) % segments, nxt + (i + 1) % segments, nxt + i))
    if cap:
        start_center, end_center = len(verts), len(verts) + 1
        verts.append(_section_center(axis, sections[0]))
        verts.append(_section_center(axis, sections[-1]))
        last_row = (len(sections) - 1) * segments
        for i in range(segments):
            faces.append((start_center, (i + 1) % segments, i))
            faces.append((end_center, last_row + i, last_row + (i + 1) % segments))
    return mesh_obj(name, verts, faces, mat)


def grid_surface(name: str, u_steps: int, v_steps: int, point_fn, mat: bpy.types.Material, thickness: float = 0.0) -> bpy.types.Object:
    verts, faces = [], []
    for v_i in range(v_steps + 1):
        v = v_i / v_steps
        for u_i in range(u_steps + 1):
            u = (u_i / u_steps) * 2 - 1
            verts.append(point_fn(u, v))
    stride = u_steps + 1
    for v_i in range(v_steps):
        for u_i in range(u_steps):
            a = v_i * stride + u_i
            faces.append((a, a + 1, a + stride + 1, a + stride))
    obj = mesh_obj(name, verts, faces, mat)
    if thickness > 0:
        add_solidify(obj, thickness)
    return obj


def torso_shell(name: str, y0: float, y1: float, angle0: float, angle1: float, rx_fn, rz_fn, mat: bpy.types.Material, u_steps: int = 64, v_steps: int = 24, center_z: float = 0.018, thickness: float = 0.018) -> bpy.types.Object:
    def point(u: float, v: float) -> tuple[float, float, float]:
        angle = angle0 + (angle1 - angle0) * ((u + 1) * 0.5)
        return (math.sin(angle) * rx_fn(v), y0 + (y1 - y0) * v, center_z + math.cos(angle) * rz_fn(v))
    return grid_surface(name, u_steps, v_steps, point, mat, thickness=thickness)


def tube_shell_between(name: str, p0: tuple[float, float, float], p1: tuple[float, float, float], radius_a_fn, radius_b_fn, angle0: float, angle1: float, mat: bpy.types.Material, u_steps: int = 32, v_steps: int = 18, thickness: float = 0.012) -> bpy.types.Object:
    start, end = Vector(p0), Vector(p1)
    axis = end - start
    axis.normalize()
    ref = Vector((0, 1, 0))
    if abs(axis.dot(ref)) > 0.92:
        ref = Vector((1, 0, 0))
    normal_a = ref - axis * axis.dot(ref)
    normal_a.normalize()
    normal_b = axis.cross(normal_a)
    normal_b.normalize()
    def point(u: float, v: float) -> tuple[float, float, float]:
        angle = angle0 + (angle1 - angle0) * ((u + 1) * 0.5)
        center = start.lerp(end, v)
        p = center + normal_a * (math.cos(angle) * radius_a_fn(v)) + normal_b * (math.sin(angle) * radius_b_fn(v))
        return (p.x, p.y, p.z)
    return grid_surface(name, u_steps, v_steps, point, mat, thickness=thickness)


def cloth_panel(name: str, x_center: float, y_top: float, y_bottom: float, z_base: float, top_width: float, bottom_width: float, mat: bpy.types.Material, u_steps: int = 20, v_steps: int = 36, wave: float = 0.012, thickness: float = 0.006, rot_z: float = 0.0) -> bpy.types.Object:
    height = y_top - y_bottom
    cos_r, sin_r = math.cos(rot_z), math.sin(rot_z)
    def point(u: float, v: float) -> tuple[float, float, float]:
        width = top_width * (1 - v) + bottom_width * v
        local_x, local_y = u * width, -height * v
        return (
            x_center + local_x * cos_r - local_y * sin_r,
            y_top + local_x * sin_r + local_y * cos_r,
            z_base + wave * math.sin((u + 1) * math.pi * 2) * math.sin(v * math.pi),
        )
    return grid_surface(name, u_steps, v_steps, point, mat, thickness=thickness)


def superellipse_bar(name: str, axis: str, center: tuple[float, float, float], length: float, half_a: float, half_b: float, mat: bpy.types.Material, segments: int = 24, rings: int = 6, exponent: float = 3.5) -> bpy.types.Object:
    verts, faces = [], []
    cx, cy, cz = center
    for ri in range(rings):
        t = ri / max(1, rings - 1)
        c = -length / 2 + length * t
        bevel = 0.70 + 0.30 * math.sin(math.pi * t)
        for i in range(segments):
            a = math.tau * i / segments
            ca, sa = math.cos(a), math.sin(a)
            x2 = math.copysign(abs(ca) ** (2 / exponent), ca) * half_a * bevel
            y2 = math.copysign(abs(sa) ** (2 / exponent), sa) * half_b * bevel
            verts.append((cx + c, cy + x2, cz + y2) if axis == "x" else (cx + x2, cy + c, cz + y2) if axis == "y" else (cx + x2, cy + y2, cz + c))
    for ri in range(rings - 1):
        row, nxt = ri * segments, (ri + 1) * segments
        for i in range(segments):
            faces.append((row + i, row + (i + 1) % segments, nxt + (i + 1) % segments, nxt + i))
    return mesh_obj(name, verts, faces, mat)


def pauldron_shell(name: str, side: int, mat: bpy.types.Material) -> bpy.types.Object:
    def point(u: float, v: float) -> tuple[float, float, float]:
        theta, phi = u * 1.48, v * math.pi * 0.62
        side_wrap = math.sin(phi)
        return (
            side * 0.325 + side * (0.03 + 0.175 * side_wrap * (0.72 + 0.28 * math.cos(theta))),
            1.390 + 0.150 * math.cos(phi) - 0.050 * v,
            0.026 + 0.205 * math.sin(theta) * side_wrap,
        )
    return grid_surface(name, 64, 32, point, mat, thickness=0.024)


def torus(name: str, major: float, minor: float, mat: bpy.types.Material, location: tuple[float, float, float], rotation=(0, 0, 0), major_segments=64, minor_segments=12) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_segments=major_segments, minor_segments=minor_segments, major_radius=major, minor_radius=minor, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.modifiers.new(name="weighted_normals", type="WEIGHTED_NORMAL")
    return obj


def sphere(name: str, radius: float, mat: bpy.types.Material, location: tuple[float, float, float], segments: int = 16) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(8, segments // 2), radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.modifiers.new(name="weighted_normals", type="WEIGHTED_NORMAL")
    return obj


def box_prism(name: str, center: tuple[float, float, float], size: tuple[float, float, float], mat: bpy.types.Material, rot_z: float = 0.0) -> bpy.types.Object:
    cx, cy, cz = center
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    cos_r, sin_r = math.cos(rot_z), math.sin(rot_z)
    verts = []
    for z in (-sz, sz):
        for y in (-sy, sy):
            for x in (-sx, sx):
                verts.append((cx + x * cos_r - y * sin_r, cy + x * sin_r + y * cos_r, cz + z))
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return mesh_obj(name, verts, faces, mat, smooth=False)
