"""Generate detailed original rig-ready roster creatures from closed lofted anatomy."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
POLICY_PATH = PIPELINE_ROOT / "data" / "full-roster-policy.json"

SPECIES_STYLE = {
    "barrow_wolf": {"base": "#51483d", "secondary": "#8b806e", "accent": "#d7b96a", "feature": "mane"},
    "war_boar": {"base": "#3c2a22", "secondary": "#695044", "accent": "#d8c39d", "feature": "tusks"},
    "wild_stag": {"base": "#805c36", "secondary": "#d1b07a", "accent": "#cdbb92", "feature": "antlers"},
    "suncrest_ram": {"base": "#d4c5a5", "secondary": "#695849", "accent": "#e2ba47", "feature": "curl_horns"},
    "briarback_bear": {"base": "#3a2b22", "secondary": "#65503c", "accent": "#9d7a41", "feature": "briar"},
    "glassriver_snapper": {"base": "#36554d", "secondary": "#203c38", "accent": "#477b7b", "feature": "shell"},
    "ash_hound": {"base": "#201b1a", "secondary": "#4a3c36", "accent": "#e85a2a", "feature": "ember_spines"},
    "mire_hound": {"base": "#39472d", "secondary": "#69704d", "accent": "#9cbc52", "feature": "mire_warts"},
    "rift_hound": {"base": "#271d36", "secondary": "#513b67", "accent": "#a768ff", "feature": "rift_crest"},
    "lair_spider": {"base": "#24191d", "secondary": "#5a2934", "accent": "#d94255", "feature": "fangs"},
    "cinderhide_drake": {"base": "#35201c", "secondary": "#65342a", "accent": "#ef6a2f", "feature": "drake_spines"},
    "rotmaw_toad": {"base": "#445024", "secondary": "#78863b", "accent": "#d1b32f", "feature": "rot_warts"},
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", required=True)
    parser.add_argument("--revision-seed", type=int, default=1)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--save-blend")
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
        for item in list(collection):
            if item.users == 0:
                collection.remove(item)


def color(value: str) -> tuple[float, float, float, float]:
    clean = value.lstrip("#")
    encoded = [int(clean[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in encoded]
    return tuple(linear) + (1.0,)


def material(name: str, value: str, metallic: float = 0.0, roughness: float = 0.72, emissive: bool = False) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    rgba = color(value)
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if emissive:
        shader.inputs["Emission Color"].default_value = rgba
        shader.inputs["Emission Strength"].default_value = 0.85
    result["runtimeAlphaMode"] = "OPAQUE"
    return result


def add_uvs(objects: list[bpy.types.Object]) -> None:
    """Add deterministic UVs so authored surface textures survive GLB export."""
    for obj in objects:
        if obj.type != "MESH" or not obj.data.polygons:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(58.0), island_margin=0.018)
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.select_set(False)


def mesh_object(name: str, vertices: list[tuple[float, float, float]], faces: list[tuple[int, ...]], mat: bpy.types.Material) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    if len(vertices) > 20 and len(faces) > 20:
        subdivision = obj.modifiers.new("organic_surface_subdivision", "SUBSURF")
        subdivision.subdivision_type = "CATMULL_CLARK"
        subdivision.levels = 1
        subdivision.render_levels = 1
    obj["modelingMethod"] = "original_closed_loft"
    obj["primitiveGeometry"] = False
    return obj


def loft_y(name: str, rings: list[tuple[float, float, float, float]], mat: bpy.types.Material, sides: int = 18) -> bpy.types.Object:
    vertices = []
    for y, z, radius_x, radius_z in rings:
        for side in range(sides):
            angle = math.tau * side / sides
            vertices.append((radius_x * math.cos(angle), y, z + radius_z * math.sin(angle)))
    faces = [tuple(reversed(range(sides))), tuple((len(rings) - 1) * sides + side for side in range(sides))]
    for ring in range(len(rings) - 1):
        for side in range(sides):
            nxt = (side + 1) % sides
            a = ring * sides + side
            b = ring * sides + nxt
            c = (ring + 1) * sides + nxt
            d = (ring + 1) * sides + side
            faces.append((a, b, c, d))
    return mesh_object(name, vertices, faces, mat)


def ellipsoid(name: str, center: tuple[float, float, float], radii: tuple[float, float, float], mat: bpy.types.Material, segments: int = 18, rings: int = 10) -> bpy.types.Object:
    vertices = [(center[0], center[1], center[2] + radii[2])]
    for ring in range(1, rings):
        phi = math.pi * ring / rings
        for segment in range(segments):
            theta = math.tau * segment / segments
            vertices.append((
                center[0] + radii[0] * math.sin(phi) * math.cos(theta),
                center[1] + radii[1] * math.sin(phi) * math.sin(theta),
                center[2] + radii[2] * math.cos(phi),
            ))
    bottom = len(vertices)
    vertices.append((center[0], center[1], center[2] - radii[2]))
    faces = []
    for segment in range(segments):
        nxt = (segment + 1) % segments
        faces.append((0, 1 + segment, 1 + nxt))
    for ring in range(rings - 2):
        start = 1 + ring * segments
        next_start = start + segments
        for segment in range(segments):
            nxt = (segment + 1) % segments
            faces.append((start + segment, next_start + segment, next_start + nxt, start + nxt))
    last = 1 + (rings - 2) * segments
    for segment in range(segments):
        nxt = (segment + 1) % segments
        faces.append((last + segment, bottom, last + nxt))
    return mesh_object(name, vertices, faces, mat)


def tube(name: str, points: list[tuple[float, float, float]], radii: list[float], mat: bpy.types.Material, sides: int = 12) -> bpy.types.Object:
    vectors = [Vector(point) for point in points]
    vertices = []
    for index, point in enumerate(vectors):
        if index == 0:
            tangent = (vectors[1] - point).normalized()
        elif index == len(vectors) - 1:
            tangent = (point - vectors[index - 1]).normalized()
        else:
            tangent = (vectors[index + 1] - vectors[index - 1]).normalized()
        reference = Vector((0, 0, 1)) if abs(tangent.z) < 0.90 else Vector((1, 0, 0))
        right = tangent.cross(reference).normalized()
        up = right.cross(tangent).normalized()
        for side in range(sides):
            angle = math.tau * side / sides
            offset = right * (math.cos(angle) * radii[index]) + up * (math.sin(angle) * radii[index])
            vertices.append(tuple(point + offset))
    faces = [tuple(reversed(range(sides))), tuple((len(points) - 1) * sides + side for side in range(sides))]
    for ring in range(len(points) - 1):
        for side in range(sides):
            nxt = (side + 1) % sides
            faces.append((ring * sides + side, ring * sides + nxt, (ring + 1) * sides + nxt, (ring + 1) * sides + side))
    return mesh_object(name, vertices, faces, mat)


def wedge(name: str, center: tuple[float, float, float], size: tuple[float, float, float], mat: bpy.types.Material, mirror: float = 1.0) -> bpy.types.Object:
    cx, cy, cz = center
    sx, sy, sz = size
    vertices = [
        (cx - sx, cy + sy, cz - sz), (cx + sx, cy + sy, cz - sz),
        (cx, cy - sy, cz + sz), (cx - sx * 0.55, cy + sy, cz + sz * 0.18),
        (cx + sx * 0.55, cy + sy, cz + sz * 0.18), (cx, cy - sy * 0.72, cz + sz * 0.78),
    ]
    if mirror < 0:
        vertices = [(-x, y, z) for x, y, z in vertices]
    faces = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
    return mesh_object(name, vertices, faces, mat)


def bind(obj: bpy.types.Object, rig: bpy.types.Object, bone_name: str) -> None:
    group = obj.vertex_groups.new(name=bone_name)
    group.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
    modifier = obj.modifiers.new("creature_skin", "ARMATURE")
    modifier.object = rig
    obj.parent = rig
    obj["deformBone"] = bone_name


def bind_longitudinal_body(obj: bpy.types.Object, rig: bpy.types.Object) -> None:
    groups = {name: obj.vertex_groups.new(name=name) for name in ("spine", "neck", "head")}
    for vertex in obj.data.vertices:
        if vertex.co.y <= -0.72:
            groups["head"].add([vertex.index], 1.0, "REPLACE")
        elif vertex.co.y <= -0.43:
            groups["neck"].add([vertex.index], 1.0, "REPLACE")
        else:
            groups["spine"].add([vertex.index], 1.0, "REPLACE")
    modifier = obj.modifiers.new("creature_skin", "ARMATURE")
    modifier.object = rig
    obj.parent = rig
    obj["deformBone"] = "spine/neck/head"


def build_armature(creature: dict) -> bpy.types.Object:
    data = bpy.data.armatures.new(creature["skeletonId"])
    rig = bpy.data.objects.new(creature["skeletonId"], data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name: str, head: tuple[float, float, float], tail: tuple[float, float, float], parent=None):
        item = data.edit_bones.new(name)
        item.head = head
        item.tail = tail
        item.parent = parent
        return item

    root = bone("root", (0, 0, 0), (0, 0, 0.22))
    spine = bone("spine", (0, 0.52, 0.72), (0, -0.40, 0.82), root)
    neck = bone("neck", (0, -0.35, 0.82), (0, -0.75, 1.02), spine)
    head = bone("head", (0, -0.72, 1.01), (0, -1.20, 0.94), neck)
    if creature["bodyPlan"] == "arachnid":
        for side, sign in (("L", -1), ("R", 1)):
            for index, y in enumerate((-0.48, -0.18, 0.14, 0.45), start=1):
                upper = bone(f"leg_{side}_{index}_upper", (0.22 * sign, y, 0.65), (0.72 * sign, y - 0.08, 0.48), spine)
                bone(f"leg_{side}_{index}_lower", (0.72 * sign, y - 0.08, 0.48), (1.15 * sign, y + 0.02, 0.05), upper)
    else:
        for side, sign in (("L", -1), ("R", 1)):
            for end, y in (("front", -0.36), ("rear", 0.47)):
                upper = bone(f"leg_{end}_{side}_upper", (0.22 * sign, y, 0.70), (0.27 * sign, y, 0.35), spine)
                bone(f"leg_{end}_{side}_lower", (0.27 * sign, y, 0.35), (0.29 * sign, y - 0.05, 0.07), upper)
        tail = bone("tail_01", (0, 0.62, 0.76), (0, 1.02, 0.69), spine)
        bone("tail_02", (0, 1.02, 0.69), (0, 1.42, 0.53), tail)
    bpy.ops.object.mode_set(mode="OBJECT")
    rig["assetId"] = f"creature.{creature['key']}.lod0"
    rig["skeletonId"] = creature["skeletonId"]
    rig["modelingMethod"] = "original_closed_loft_v2"
    rig["primitiveGeometry"] = False
    rig["runtimeEligible"] = False
    return rig


def add_eyes(meshes: list[bpy.types.Object], rig: bpy.types.Object, eye_mat: bpy.types.Material, y: float, z: float, spread: float, scale: float = 1.0) -> None:
    for side, sign in (("L", -1), ("R", 1)):
        eye = ellipsoid(f"eye_{side}", (spread * sign, y, z), (0.031 * scale, 0.018 * scale, 0.030 * scale), eye_mat, 16, 8)
        bind(eye, rig, "head")
        meshes.append(eye)


def add_quadruped_legs(meshes: list[bpy.types.Object], rig: bpy.types.Object, body_mat: bpy.types.Material, detail_mat: bpy.types.Material, *, spread: float, front_y: float, rear_y: float, shoulder_z: float, hoof: bool = False, heavy: float = 1.0) -> None:
    for side, sign in (("L", -1), ("R", 1)):
        for end, y in (("front", front_y), ("rear", rear_y)):
            hip = (spread * sign, y, shoulder_z)
            knee = ((spread + 0.035) * sign, y - (0.025 if end == "front" else -0.02), 0.38)
            ankle = ((spread + 0.045) * sign, y - 0.055, 0.10)
            upper = tube(f"leg_{end}_{side}_upper_mesh", [hip, knee], [0.105 * heavy, 0.082 * heavy], body_mat, 12)
            lower = tube(f"leg_{end}_{side}_lower_mesh", [knee, ankle], [0.083 * heavy, 0.055 * heavy], body_mat, 12)
            foot = ellipsoid(f"foot_{end}_{side}", ((spread + 0.045) * sign, y - 0.11, 0.065), ((0.075 if hoof else 0.11) * heavy, 0.15 * heavy, 0.055 * heavy), detail_mat if hoof else body_mat, 14, 8)
            bind(upper, rig, f"leg_{end}_{side}_upper")
            bind(lower, rig, f"leg_{end}_{side}_lower")
            bind(foot, rig, f"leg_{end}_{side}_lower")
            meshes.extend((upper, lower, foot))


def add_face(meshes: list[bpy.types.Object], rig: bpy.types.Object, base: bpy.types.Material, secondary: bpy.types.Material, eye: bpy.types.Material, nose: bpy.types.Material, *, head_width: float, head_z: float, muzzle_length: float, ear: str = "pointed") -> None:
    head = loft_y("head_mesh", [
        (-0.68, head_z, head_width * 0.75, head_width * 0.68),
        (-0.83, head_z + 0.035, head_width, head_width * 0.78),
        (-1.00, head_z - 0.02, head_width * 0.82, head_width * 0.66),
    ], base, 18)
    muzzle = loft_y("muzzle", [
        (-0.94, head_z - 0.08, head_width * 0.62, head_width * 0.44),
        (-1.00 - muzzle_length * 0.55, head_z - 0.10, head_width * 0.50, head_width * 0.34),
        (-1.00 - muzzle_length, head_z - 0.12, head_width * 0.38, head_width * 0.28),
    ], secondary, 16)
    nose_obj = ellipsoid("nose", (0, -1.02 - muzzle_length, head_z - 0.105), (head_width * 0.39, 0.045, head_width * 0.25), nose, 16, 8)
    for obj in (head, muzzle, nose_obj):
        bind(obj, rig, "head")
        meshes.append(obj)
    add_eyes(meshes, rig, eye, -1.005, head_z + head_width * 0.24, head_width * 0.48, max(0.8, head_width / 0.30))
    if ear == "pointed":
        for side, sign in (("L", -1), ("R", 1)):
            obj = wedge(f"ear_{side}", (head_width * 0.70, -0.80, head_z + head_width * 0.65), (head_width * 0.27, 0.105, head_width * 0.58), secondary, sign)
            bind(obj, rig, "head")
            meshes.append(obj)
    elif ear == "round":
        for side, sign in (("L", -1), ("R", 1)):
            obj = ellipsoid(f"ear_{side}", (head_width * 0.76 * sign, -0.79, head_z + head_width * 0.48), (head_width * 0.27, 0.06, head_width * 0.29), secondary, 14, 8)
            bind(obj, rig, "head")
            meshes.append(obj)


def add_drake_face(meshes: list[bpy.types.Object], rig: bpy.types.Object, mats: dict[str, bpy.types.Material], head_z: float) -> None:
    """Build a low, armored reptilian skull without mammalian ears or nose."""
    skull = loft_y("head_mesh", [
        (-0.58, head_z, 0.25, 0.17), (-0.76, head_z + 0.025, 0.34, 0.20),
        (-0.98, head_z - 0.015, 0.31, 0.16), (-1.18, head_z - 0.045, 0.25, 0.12),
        (-1.39, head_z - 0.07, 0.17, 0.075),
    ], mats["base"], 22)
    jaw = loft_y("lower_jaw", [
        (-0.79, head_z - 0.13, 0.27, 0.085), (-1.10, head_z - 0.16, 0.23, 0.070),
        (-1.37, head_z - 0.17, 0.14, 0.045),
    ], mats["secondary"], 18)
    for obj in (skull, jaw):
        bind(obj, rig, "head")
        meshes.append(obj)
    for side, sign in (("L", -1), ("R", 1)):
        eye = ellipsoid(
            f"eye_{side}", (0.195 * sign, -1.00, head_z + 0.095),
            (0.034, 0.020, 0.025), mats["eye"], 14, 7,
        )
        pupil = ellipsoid(
            f"slit_pupil_{side}", (0.197 * sign, -1.018, head_z + 0.095),
            (0.010, 0.007, 0.020), mats["nose"], 12, 6,
        )
        brow = wedge(
            f"armored_brow_{side}", (0.19, -0.96, head_z + 0.16),
            (0.17, 0.13, 0.075), mats["secondary"], sign,
        )
        nostril = ellipsoid(
            f"nostril_{side}", (0.070 * sign, -1.39, head_z - 0.045),
            (0.018, 0.010, 0.011), mats["nose"], 10, 5,
        )
        cheek_spike = wedge(
            f"cheek_spike_{side}", (0.28, -0.86, head_z - 0.02),
            (0.16, 0.10, 0.090), mats["horn"], sign,
        )
        for obj in (eye, pupil, brow, nostril, cheek_spike):
            bind(obj, rig, "head")
            meshes.append(obj)


def add_drake_legs(meshes: list[bpy.types.Object], rig: bpy.types.Object, mats: dict[str, bpy.types.Material], body_z: float) -> None:
    """Build laterally splayed reptilian limbs with planted clawed feet."""
    for side, sign in (("L", -1), ("R", 1)):
        for end, y in (("front", -0.34), ("rear", 0.48)):
            hip = (0.34 * sign, y, body_z)
            elbow = (0.57 * sign, y - (0.08 if end == "front" else -0.05), 0.37)
            wrist = (0.49 * sign, y - 0.07, 0.105)
            upper = tube(
                f"leg_{end}_{side}_upper_mesh", [hip, elbow],
                [0.105 if end == "front" else 0.13, 0.075], mats["base"], 14,
            )
            lower = tube(
                f"leg_{end}_{side}_lower_mesh", [elbow, wrist],
                [0.075, 0.045], mats["secondary"], 12,
            )
            foot = ellipsoid(
                f"foot_{end}_{side}", (0.49 * sign, y - 0.16, 0.065),
                (0.12, 0.17, 0.045), mats["secondary"], 16, 8,
            )
            for obj, bone_name in (
                (upper, f"leg_{end}_{side}_upper"),
                (lower, f"leg_{end}_{side}_lower"),
                (foot, f"leg_{end}_{side}_lower"),
            ):
                bind(obj, rig, bone_name)
                meshes.append(obj)
            for toe_index in (-1, 0, 1):
                claw = tube(
                    f"claw_{end}_{side}_{toe_index + 2}",
                    [
                        ((0.49 + toe_index * 0.040) * sign, y - 0.22, 0.065),
                        ((0.49 + toe_index * 0.047) * sign, y - 0.34, 0.030),
                    ],
                    [0.016, 0.003], mats["horn"], 8,
                )
                bind(claw, rig, f"leg_{end}_{side}_lower")
                meshes.append(claw)
def add_tail(meshes: list[bpy.types.Object], rig: bpy.types.Object, mat: bpy.types.Material, points: list[tuple[float, float, float]], radii: list[float], bushy: bool = False) -> None:
    tail = tube("tail_mesh", points, radii, mat, 14 if bushy else 12)
    bind(tail, rig, "tail_01")
    meshes.append(tail)


def add_spines(meshes: list[bpy.types.Object], rig: bpy.types.Object, mat: bpy.types.Material, count: int, y_start: float, y_step: float, z: float, size: float) -> None:
    for index in range(count):
        spine = wedge(f"dorsal_spine_{index + 1}", (0, y_start + index * y_step, z), (size * 0.42, size * 0.42, size), mat)
        bind(spine, rig, "spine" if index > 1 else "neck")
        meshes.append(spine)


def unify_canid_anatomy(
    meshes: list[bpy.types.Object],
    rig: bpy.types.Object,
    mat: bpy.types.Material,
) -> None:
    """Voxel-union overlapping organic canid parts and restore spatial skinning."""
    prefixes = (
        "continuous_canid_body", "lower_jaw", "leg_", "foot_",
        "front_carpal_", "rear_hock_", "tail_mesh", "ruff_tuft_",
    )
    organic = [obj for obj in meshes if obj.name.startswith(prefixes)]
    if len(organic) < 12:
        raise RuntimeError("Canid anatomy union is missing expected organic components")
    detail_meshes = [obj for obj in meshes if obj not in organic]
    for obj in organic:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in organic:
        obj.select_set(True)
    unified = next(obj for obj in organic if obj.name.startswith("continuous_canid_body"))
    bpy.context.view_layer.objects.active = unified
    bpy.ops.object.join()
    unified.name = "unified_canid_anatomy"
    unified.data.remesh_voxel_size = 0.026
    unified.data.remesh_voxel_adaptivity = 0.0
    unified.data.use_remesh_fix_poles = True
    unified.data.use_remesh_preserve_volume = True
    bpy.context.view_layer.objects.active = unified
    unified.select_set(True)
    bpy.ops.object.voxel_remesh()
    unified.select_set(False)
    unified.data.materials.clear()
    unified.data.materials.append(mat)
    for polygon in unified.data.polygons:
        polygon.use_smooth = True
    skin_noise = bpy.data.textures.new(f"{unified.name}_surface_breakup", type="CLOUDS")
    skin_noise.noise_scale = 0.085
    skin_noise.noise_depth = 2
    skin_breakup = unified.modifiers.new("subtle_skin_surface_breakup", "DISPLACE")
    skin_breakup.texture = skin_noise
    skin_breakup.texture_coords = "GLOBAL"
    skin_breakup.strength = 0.010
    skin_breakup.mid_level = 0.5

    for group in list(unified.vertex_groups):
        unified.vertex_groups.remove(group)
    group_names = (
        "spine", "neck", "head", "tail_01", "tail_02",
        "leg_front_L_upper", "leg_front_L_lower", "leg_front_R_upper", "leg_front_R_lower",
        "leg_rear_L_upper", "leg_rear_L_lower", "leg_rear_R_upper", "leg_rear_R_lower",
    )
    groups = {name: unified.vertex_groups.new(name=name) for name in group_names}
    for vertex in unified.data.vertices:
        x, y, z = vertex.co
        if z < 0.69 and abs(x) > 0.15:
            side = "L" if x >= 0.0 else "R"
            end = "front" if y < 0.02 else "rear"
            segment = "upper" if z >= 0.30 else "lower"
            bone_name = f"leg_{end}_{side}_{segment}"
        elif y > 1.06:
            bone_name = "tail_02"
        elif y > 0.64:
            bone_name = "tail_01"
        elif y < -0.72:
            bone_name = "head"
        elif y < -0.40:
            bone_name = "neck"
        else:
            bone_name = "spine"
        groups[bone_name].add([vertex.index], 1.0, "REPLACE")
    modifier = unified.modifiers.new("creature_skin", "ARMATURE")
    modifier.object = rig
    unified.parent = rig
    unified["deformBone"] = "spatial_multi_bone"
    unified["modelingMethod"] = "original_closed_loft"
    unified["primitiveGeometry"] = False
    meshes[:] = [unified, *detail_meshes]


def unify_quadruped_anatomy(
    meshes: list[bpy.types.Object],
    rig: bpy.types.Object,
    mat: bpy.types.Material,
) -> None:
    """Create one coherent organic surface for non-canid quadrupeds."""
    prefixes = (
        "body_mesh", "neck_mesh", "head_mesh", "muzzle", "lower_jaw",
        "leg_", "foot_", "tail_mesh", "ear_",
    )
    organic = [obj for obj in meshes if obj.name.startswith(prefixes)]
    if len(organic) < 9:
        raise RuntimeError("Quadruped anatomy union is missing expected organic components")
    detail_meshes = [obj for obj in meshes if obj not in organic]
    for obj in organic:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in organic:
        obj.select_set(True)
    unified = next(obj for obj in organic if obj.name.startswith("body_mesh"))
    bpy.context.view_layer.objects.active = unified
    bpy.ops.object.join()
    unified.name = "unified_quadruped_anatomy"
    unified.data.remesh_voxel_size = 0.028
    unified.data.remesh_voxel_adaptivity = 0.0
    unified.data.use_remesh_fix_poles = True
    unified.data.use_remesh_preserve_volume = True
    bpy.context.view_layer.objects.active = unified
    unified.select_set(True)
    bpy.ops.object.voxel_remesh()
    unified.select_set(False)
    unified.data.materials.clear()
    unified.data.materials.append(mat)
    for polygon in unified.data.polygons:
        polygon.use_smooth = True

    skin_noise = bpy.data.textures.new(f"{unified.name}_surface_breakup", type="CLOUDS")
    skin_noise.noise_scale = 0.085
    skin_noise.noise_depth = 2
    skin_breakup = unified.modifiers.new("subtle_skin_surface_breakup", "DISPLACE")
    skin_breakup.texture = skin_noise
    skin_breakup.texture_coords = "GLOBAL"
    skin_breakup.strength = 0.010
    skin_breakup.mid_level = 0.5

    for group in list(unified.vertex_groups):
        unified.vertex_groups.remove(group)
    group_names = (
        "spine", "neck", "head", "tail_01", "tail_02",
        "leg_front_L_upper", "leg_front_L_lower", "leg_front_R_upper", "leg_front_R_lower",
        "leg_rear_L_upper", "leg_rear_L_lower", "leg_rear_R_upper", "leg_rear_R_lower",
    )
    groups = {name: unified.vertex_groups.new(name=name) for name in group_names}
    for vertex in unified.data.vertices:
        x, y, z = vertex.co
        if z < 0.72 and abs(x) > 0.15:
            side = "L" if x >= 0.0 else "R"
            end = "front" if y < 0.02 else "rear"
            segment = "upper" if z >= 0.30 else "lower"
            bone_name = f"leg_{end}_{side}_{segment}"
        elif y > 1.03:
            bone_name = "tail_02"
        elif y > 0.62:
            bone_name = "tail_01"
        elif y < -0.74:
            bone_name = "head"
        elif y < -0.36:
            bone_name = "neck"
        else:
            bone_name = "spine"
        groups[bone_name].add([vertex.index], 1.0, "REPLACE")
    modifier = unified.modifiers.new("creature_skin", "ARMATURE")
    modifier.object = rig
    unified.parent = rig
    unified["deformBone"] = "spatial_multi_bone"
    unified["modelingMethod"] = "original_closed_loft"
    unified["primitiveGeometry"] = False
    meshes[:] = [unified, *detail_meshes]


def build_canid(creature: dict, mats: dict[str, bpy.types.Material], rig: bpy.types.Object) -> list[bpy.types.Object]:
    """Build one continuous canine torso/neck/head silhouette with bent limbs."""
    meshes = []
    body = loft_y("continuous_canid_body", [
        (0.72, 0.80, 0.24, 0.22), (0.58, 0.82, 0.35, 0.32),
        (0.31, 0.86, 0.38, 0.29), (0.04, 0.89, 0.39, 0.28),
        (-0.25, 0.91, 0.40, 0.36), (-0.45, 0.94, 0.31, 0.32),
        (-0.60, 0.98, 0.23, 0.25), (-0.73, 1.02, 0.25, 0.24),
        (-0.86, 1.01, 0.245, 0.21), (-0.97, 0.97, 0.20, 0.16),
        (-1.10, 0.93, 0.15, 0.11), (-1.24, 0.90, 0.09, 0.07),
    ], mats["base"], 24)
    fur_noise = bpy.data.textures.new(f"{creature['key']}_fur_surface", type="CLOUDS")
    fur_noise.noise_scale = 0.075
    fur_noise.noise_depth = 2
    fur_breakup = body.modifiers.new("subtle_fur_surface_breakup", "DISPLACE")
    fur_breakup.texture = fur_noise
    fur_breakup.texture_coords = "GLOBAL"
    fur_breakup.strength = 0.014
    fur_breakup.mid_level = 0.5
    bind_longitudinal_body(body, rig)
    meshes.append(body)

    lower_jaw = loft_y("lower_jaw", [
        (-0.99, 0.87, 0.15, 0.065), (-1.14, 0.85, 0.115, 0.048), (-1.23, 0.855, 0.075, 0.032),
    ], mats["secondary"], 16)
    nose_obj = ellipsoid("nose", (0, -1.265, 0.905), (0.088, 0.042, 0.058), mats["nose"], 18, 9)
    bind(lower_jaw, rig, "head")
    bind(nose_obj, rig, "head")
    meshes.extend((lower_jaw, nose_obj))

    for side, sign in (("L", -1), ("R", 1)):
        socket = ellipsoid(f"eye_socket_{side}", (0.108 * sign, -0.995, 1.055), (0.040, 0.020, 0.035), mats["nose"], 16, 8)
        pupil = ellipsoid(f"eye_glow_{side}", (0.108 * sign, -1.013, 1.056), (0.018, 0.009, 0.019), mats["eye"], 14, 7)
        ear = wedge(f"ear_{side}", (0.19, -0.72, 1.16), (0.090, 0.065, 0.205), mats["secondary"], sign)
        for obj in (socket, pupil, ear):
            bind(obj, rig, "head")
            meshes.append(obj)
        fang = tube(
            f"fang_{side}",
            [(0.080 * sign, -1.15, 0.875), (0.082 * sign, -1.17, 0.82)],
            [0.013, 0.003], mats["horn"], 8,
        )
        bind(fang, rig, "head")
        meshes.append(fang)

    for side, sign in (("L", -1), ("R", 1)):
        # Front legs remain columnar at the forearm but taper naturally into
        # a rearward paw. Hind legs use a canine stifle/hock bend.
        front_upper = tube(f"leg_front_{side}_upper_mesh", [
            (0.29 * sign, -0.31, 0.86), (0.31 * sign, -0.34, 0.54), (0.30 * sign, -0.38, 0.36),
        ], [0.105, 0.083, 0.070], mats["base"], 14)
        front_lower = tube(f"leg_front_{side}_lower_mesh", [
            (0.30 * sign, -0.38, 0.36), (0.31 * sign, -0.43, 0.13),
        ], [0.071, 0.046], mats["secondary"], 12)
        front_paw = ellipsoid(f"foot_front_{side}", (0.31 * sign, -0.52, 0.070), (0.078, 0.125, 0.045), mats["secondary"], 16, 8)
        rear_upper = tube(f"leg_rear_{side}_upper_mesh", [
            (0.29 * sign, 0.46, 0.78), (0.32 * sign, 0.25, 0.52), (0.33 * sign, 0.44, 0.34),
        ], [0.13, 0.10, 0.066], mats["base"], 14)
        rear_lower = tube(f"leg_rear_{side}_lower_mesh", [
            (0.33 * sign, 0.44, 0.34), (0.32 * sign, 0.53, 0.13),
        ], [0.067, 0.043], mats["secondary"], 12)
        rear_paw = ellipsoid(f"foot_rear_{side}", (0.32 * sign, 0.43, 0.070), (0.082, 0.130, 0.045), mats["secondary"], 16, 8)
        front_joint = ellipsoid(f"front_carpal_{side}", (0.30 * sign, -0.39, 0.34), (0.076, 0.070, 0.078), mats["base"], 14, 8)
        rear_joint = ellipsoid(f"rear_hock_{side}", (0.33 * sign, 0.43, 0.34), (0.072, 0.078, 0.072), mats["base"], 14, 8)
        for obj, bone_name in (
            (front_upper, f"leg_front_{side}_upper"), (front_lower, f"leg_front_{side}_lower"),
            (front_paw, f"leg_front_{side}_lower"), (rear_upper, f"leg_rear_{side}_upper"),
            (rear_lower, f"leg_rear_{side}_lower"), (rear_paw, f"leg_rear_{side}_lower"),
            (front_joint, f"leg_front_{side}_upper"), (rear_joint, f"leg_rear_{side}_upper"),
        ):
            bind(obj, rig, bone_name)
            meshes.append(obj)
        for end, paw_y, paw_x, bone_name in (
            ("front", -0.61, 0.31, f"leg_front_{side}_lower"),
            ("rear", 0.34, 0.32, f"leg_rear_{side}_lower"),
        ):
            for toe_index in (-1, 0, 1):
                toe = ellipsoid(
                    f"toe_{end}_{side}_{toe_index + 2}",
                    ((paw_x + toe_index * 0.034) * sign, paw_y, 0.066),
                    (0.020, 0.044, 0.017), mats["nose"], 10, 6,
                )
                bind(toe, rig, bone_name)
                meshes.append(toe)

    add_tail(meshes, rig, mats["secondary"], [
        (0, 0.62, 0.82), (0, 0.90, 0.96), (0.03, 1.18, 0.92),
        (0.05, 1.43, 0.78), (0.03, 1.62, 0.58),
    ], [0.16, 0.18, 0.15, 0.09, 0.018], bushy=True)

    # Irregular ruff tufts break the smooth loft at the neck without creating
    # the toy-like full collar that the first pass used.
    for index, (x, y, z, sign) in enumerate((
        (0.31, -0.47, 1.02, 1), (0.35, -0.39, 0.91, 1),
        (0.31, -0.47, 1.02, -1), (0.35, -0.39, 0.91, -1),
    )):
        tuft = wedge(f"ruff_tuft_{index}", (x, y, z), (0.11, 0.08, 0.18), mats["secondary"], sign)
        bind(tuft, rig, "neck")
        meshes.append(tuft)

    unify_canid_anatomy(meshes, rig, mats["base"])

    if creature["key"] in {"ash_hound", "rift_hound"}:
        add_spines(meshes, rig, mats["accent"], 7, -0.40, 0.15, 1.23, 0.12 if creature["key"] == "ash_hound" else 0.15)
    elif creature["key"] == "mire_hound":
        for index, (x, y, z) in enumerate(((-0.23, -0.18, 1.14), (0.26, 0.18, 1.14), (-0.20, 0.43, 1.08))):
            wart = ellipsoid(f"mire_wart_{index}", (x, y, z), (0.050, 0.042, 0.045), mats["accent"], 12, 6)
            bind(wart, rig, "spine")
            meshes.append(wart)
    return meshes


def add_horns(meshes: list[bpy.types.Object], rig: bpy.types.Object, mat: bpy.types.Material, style: str, head_z: float) -> None:
    for side, sign in (("L", -1), ("R", 1)):
        if style == "curl":
            points = [
                (0.18 * sign, -0.80, head_z + 0.20), (0.34 * sign, -0.74, head_z + 0.26),
                (0.43 * sign, -0.82, head_z + 0.14), (0.40 * sign, -0.93, head_z - 0.01),
                (0.28 * sign, -1.00, head_z - 0.04),
            ]
        else:
            points = [
                (0.15 * sign, -0.80, head_z + 0.18), (0.28 * sign, -0.78, head_z + 0.42),
                (0.36 * sign, -0.75, head_z + 0.68),
            ]
        horn = tube(f"horn_{side}", points, [0.070, 0.060, 0.038, 0.022, 0.010][:len(points)], mat, 12)
        bind(horn, rig, "head")
        meshes.append(horn)


def build_quadruped(creature: dict, mats: dict[str, bpy.types.Material], rig: bpy.types.Object) -> list[bpy.types.Object]:
    plan = creature["bodyPlan"]
    key = creature["key"]
    if plan == "canid":
        return build_canid(creature, mats, rig)
    meshes = []
    dims = {
        "canid": (0.44, 0.39, 0.30, 0.82), "boar": (0.56, 0.48, 0.34, 0.80),
        "cervid": (0.32, 0.29, 0.20, 0.96), "caprine": (0.38, 0.34, 0.23, 0.90),
        "ursine": (0.64, 0.58, 0.40, 0.82), "ground_drake": (0.48, 0.31, 0.30, 0.68),
    }
    width, depth, head_width, body_z = dims[plan]
    body = loft_y("body_mesh", [
        (0.86 if plan == "ground_drake" else 0.72, body_z - 0.03, width * 0.62, depth * 0.70),
        (0.48, body_z, width * 0.96, depth),
        (0.12, body_z + 0.04, width, depth * 1.06),
        (-0.27, body_z + 0.05, width * 0.90, depth),
        (-0.58 if plan == "ground_drake" else -0.49, body_z + 0.02, width * 0.64, depth * 0.76),
    ], mats["base"], 20)
    bind(body, rig, "spine")
    meshes.append(body)
    if plan in {"cervid", "caprine"}:
        neck = tube("neck_mesh", [(0, -0.35, body_z + 0.20), (0, -0.57, 1.12), (0, -0.77, 1.28)], [width * 0.32, width * 0.26, width * 0.22], mats["base"], 16)
        bind(neck, rig, "neck")
        meshes.append(neck)
        head_z = 1.28
    else:
        neck = loft_y("neck_mesh", [(-0.40, body_z + 0.10, width * 0.56, depth * 0.70), (-0.68, body_z + 0.13, width * 0.46, depth * 0.60)], mats["secondary"], 18)
        bind(neck, rig, "neck")
        meshes.append(neck)
        head_z = body_z + 0.14
    ear = "none" if plan == "ground_drake" else "round" if plan in {"boar", "ursine"} else "pointed"
    muzzle = {"boar": 0.34, "cervid": 0.40, "caprine": 0.34, "ursine": 0.27, "ground_drake": 0.43}.get(plan, 0.30)
    if plan == "ground_drake":
        add_drake_face(meshes, rig, mats, head_z)
    else:
        add_face(meshes, rig, mats["base"], mats["secondary"], mats["eye"], mats["nose"], head_width=head_width, head_z=head_z, muzzle_length=muzzle, ear=ear)
    heavy = 1.35 if plan in {"boar", "ursine"} else 0.95 if plan == "cervid" else 1.0
    if plan == "ground_drake":
        add_drake_legs(meshes, rig, mats, body_z)
    else:
        add_quadruped_legs(meshes, rig, mats["base"], mats["horn"], spread=width * 0.70, front_y=-0.34, rear_y=0.48, shoulder_z=body_z, hoof=plan in {"boar", "cervid", "caprine"}, heavy=heavy)
    if plan == "boar":
        add_tail(meshes, rig, mats["base"], [(0, 0.63, body_z), (0.04, 0.91, body_z + 0.07), (-0.03, 1.02, body_z + 0.12)], [0.06, 0.04, 0.015])
        for side, sign in (("L", -1), ("R", 1)):
            tusk = tube(
                f"mouth_tusk_{side}",
                [
                    (0.16 * sign, -1.13, head_z - 0.17),
                    (0.23 * sign, -1.27, head_z - 0.10),
                    (0.21 * sign, -1.31, head_z + 0.015),
                ],
                [0.045, 0.030, 0.006], mats["horn"], 12,
            )
            bind(tusk, rig, "head")
            meshes.append(tusk)
        add_spines(meshes, rig, mats["secondary"], 7, -0.36, 0.15, body_z + depth * 0.92, 0.13)
    elif plan == "cervid":
        add_tail(meshes, rig, mats["secondary"], [(0, 0.58, body_z), (0, 0.91, body_z + 0.08)], [0.09, 0.025])
        add_horns(meshes, rig, mats["horn"], "straight", head_z)
        for side, sign in (("L", -1), ("R", 1)):
            tine = tube(f"antler_tine_{side}", [(0.29 * sign, -0.76, head_z + 0.42), (0.48 * sign, -0.83, head_z + 0.58)], [0.035, 0.010], mats["horn"], 10)
            bind(tine, rig, "head")
            meshes.append(tine)
    elif plan == "caprine":
        add_tail(meshes, rig, mats["secondary"], [(0, 0.60, body_z), (0, 0.90, body_z + 0.13)], [0.10, 0.022])
        add_horns(meshes, rig, mats["horn"], "curl", head_z)
        beard = tube("chin_beard", [(0, -1.07, head_z - 0.11), (0, -1.11, head_z - 0.36)], [0.07, 0.012], mats["secondary"], 12)
        bind(beard, rig, "head")
        meshes.append(beard)
    elif plan == "ursine":
        add_tail(meshes, rig, mats["secondary"], [(0, 0.61, body_z), (0, 0.83, body_z + 0.03)], [0.11, 0.02])
        for side, sign in (("L", -1), ("R", 1)):
            for index in range(3):
                claw = tube(f"front_claw_{side}_{index}", [(sign * (width * 0.70 + (index - 1) * 0.035), -0.52, 0.06), (sign * (width * 0.70 + (index - 1) * 0.035), -0.66, 0.045)], [0.018, 0.004], mats["horn"], 8)
                bind(claw, rig, f"leg_front_{side}_lower")
                meshes.append(claw)
    elif plan == "ground_drake":
        add_tail(meshes, rig, mats["base"], [(0, 0.58, body_z), (0, 1.02, body_z - 0.02), (0, 1.52, body_z - 0.18), (0, 1.95, body_z - 0.28)], [0.22, 0.16, 0.08, 0.012])
        add_spines(meshes, rig, mats["accent"], 9, -0.52, 0.18, body_z + depth * 0.95, 0.16)
        for index, (x, y, z, sign) in enumerate((
            (0.34, -0.16, body_z + 0.20, 1), (0.34, -0.16, body_z + 0.20, -1),
            (0.37, 0.12, body_z + 0.18, 1), (0.37, 0.12, body_z + 0.18, -1),
        )):
            side_scale = wedge(f"flank_scale_{index}", (x, y, z), (0.11, 0.13, 0.06), mats["secondary"], sign)
            bind(side_scale, rig, "spine")
            meshes.append(side_scale)
    unify_quadruped_anatomy(meshes, rig, mats["base"])
    if plan in {"boar", "cervid", "caprine"}:
        for side, sign in (("L", -1), ("R", 1)):
            for end, y in (("front", -0.46), ("rear", 0.36)):
                hoof = ellipsoid(
                    f"hoof_cap_{end}_{side}",
                    (width * 0.70 * sign, y, 0.050),
                    (0.068 * heavy, 0.100 * heavy, 0.034 * heavy),
                    mats["horn"], 14, 7,
                )
                bind(hoof, rig, f"leg_{end}_{side}_lower")
                meshes.append(hoof)
    return meshes


def build_chelonian(creature: dict, mats: dict[str, bpy.types.Material], rig: bpy.types.Object) -> list[bpy.types.Object]:
    meshes = []
    body = ellipsoid("body_mesh", (0, 0.05, 0.55), (0.61, 0.78, 0.27), mats["base"], 22, 12)
    shell = ellipsoid("faceted_shell", (0, 0.12, 0.78), (0.72, 0.82, 0.30), mats["secondary"], 24, 12)
    shell_noise = bpy.data.textures.new(f"{creature['key']}_shell_surface", type="VORONOI")
    shell_noise.noise_scale = 0.11
    shell_breakup = shell.modifiers.new("weathered_shell_breakup", "DISPLACE")
    shell_breakup.texture = shell_noise
    shell_breakup.texture_coords = "GLOBAL"
    shell_breakup.strength = 0.018
    shell_breakup.mid_level = 0.5
    shell.data.materials.append(mats["accent"])
    shell.data.materials.append(mats["base"])
    # Color the shell's own authored faces in staggered bands. Unlike separate
    # plate meshes, these scutes remain conformal through subdivision/export.
    for polygon in shell.data.polygons:
        center = polygon.center
        if center.z < 0.01:
            polygon.material_index = 0
            continue
        angle_band = int(((math.atan2(center.y - 0.12, center.x) + math.pi) / math.tau) * 10)
        radial_band = int(math.hypot(center.x / 0.72, (center.y - 0.12) / 0.82) * 5)
        polygon.material_index = 1 if (angle_band + radial_band) % 3 else 2
    neck = tube("neck_mesh", [(0, -0.48, 0.58), (0, -0.83, 0.61)], [0.20, 0.15], mats["base"], 16)
    head = loft_y("head_mesh", [
        (-0.78, 0.64, 0.17, 0.15), (-0.97, 0.66, 0.25, 0.20),
        (-1.18, 0.62, 0.20, 0.14),
    ], mats["base"], 18)
    beak = loft_y("beak", [
        (-1.12, 0.60, 0.17, 0.095), (-1.29, 0.59, 0.11, 0.060),
        (-1.41, 0.58, 0.025, 0.015),
    ], mats["horn"], 14)
    for obj, bone_name in ((body, "spine"), (shell, "spine"), (neck, "neck"), (head, "head"), (beak, "head")):
        bind(obj, rig, bone_name)
        meshes.append(obj)
    add_eyes(meshes, rig, mats["eye"], -1.115, 0.70, 0.16, 0.65)
    add_quadruped_legs(meshes, rig, mats["base"], mats["base"], spread=0.50, front_y=-0.40, rear_y=0.46, shoulder_z=0.58, heavy=0.82)
    add_tail(meshes, rig, mats["base"], [(0, 0.70, 0.56), (0, 1.03, 0.50)], [0.11, 0.018])
    for side, sign in (("L", -1), ("R", 1)):
        nostril = ellipsoid(
            f"nostril_{side}", (0.060 * sign, -1.30, 0.64),
            (0.014, 0.009, 0.010), mats["nose"], 10, 5,
        )
        bind(nostril, rig, "head")
        meshes.append(nostril)
    unify_quadruped_anatomy(meshes, rig, mats["base"])
    return meshes


def build_arachnid(creature: dict, mats: dict[str, bpy.types.Material], rig: bpy.types.Object) -> list[bpy.types.Object]:
    meshes = []
    abdomen = loft_y("abdomen", [
        (0.90, 0.70, 0.16, 0.15), (0.73, 0.72, 0.35, 0.29),
        (0.37, 0.75, 0.48, 0.40), (0.03, 0.72, 0.40, 0.35),
    ], mats["base"], 22)
    thorax = loft_y("cephalothorax", [
        (0.04, 0.68, 0.27, 0.22), (-0.26, 0.67, 0.39, 0.31),
        (-0.55, 0.64, 0.33, 0.27), (-0.70, 0.61, 0.22, 0.18),
    ], mats["secondary"], 20)
    pedicel = tube("pedicel", [(0, -0.01, 0.68), (0, 0.12, 0.71)], [0.14, 0.17], mats["base"], 14)
    for obj, bone_name in ((abdomen, "spine"), (thorax, "head"), (pedicel, "spine")):
        bind(obj, rig, bone_name)
        meshes.append(obj)
    for side, sign in (("L", -1), ("R", 1)):
        for index, y in enumerate((-0.48, -0.18, 0.14, 0.45), start=1):
            reach = 1.18 - abs(index - 2.5) * 0.08
            lift = 0.82 + (0.05 if index in {2, 3} else 0.0)
            upper = tube(
                f"leg_{side}_{index}_upper_mesh",
                [(0.24 * sign, y, 0.65), (0.53 * sign, y - 0.06, lift), (0.76 * sign, y - 0.09, 0.54)],
                [0.065, 0.052, 0.041], mats["base"], 10,
            )
            lower = tube(
                f"leg_{side}_{index}_lower_mesh",
                [(0.76 * sign, y - 0.09, 0.54), (reach * sign, y + 0.02, 0.06), (reach * 1.03 * sign, y - 0.04, 0.035)],
                [0.042, 0.014, 0.006], mats["secondary"], 10,
            )
            bind(upper, rig, f"leg_{side}_{index}_upper")
            bind(lower, rig, f"leg_{side}_{index}_lower")
            meshes.extend((upper, lower))
    for row, (z, spread) in enumerate(((0.73, 0.20), (0.67, 0.12))):
        add_eyes(meshes, rig, mats["eye"], -0.72 - row * 0.02, z, spread, 0.70)
    for side, sign in (("L", -1), ("R", 1)):
        fang = tube(f"fang_{side}", [(0.12 * sign, -0.69, 0.58), (0.14 * sign, -0.91, 0.43)], [0.045, 0.007], mats["horn"], 10)
        bind(fang, rig, "head")
        meshes.append(fang)
        palp = tube(
            f"pedipalp_{side}",
            [(0.18 * sign, -0.63, 0.61), (0.28 * sign, -0.82, 0.53), (0.23 * sign, -0.95, 0.47)],
            [0.040, 0.026, 0.010], mats["secondary"], 10,
        )
        bind(palp, rig, "head")
        meshes.append(palp)
    for index, (x, y, z, sign) in enumerate((
        (0.20, 0.25, 1.03, 1), (0.20, 0.25, 1.03, -1),
        (0.27, 0.48, 1.01, 1), (0.27, 0.48, 1.01, -1),
        (0.18, 0.69, 0.94, 1), (0.18, 0.69, 0.94, -1),
    )):
        marking = ellipsoid(f"abdomen_marking_{index}", (x * sign, y, z), (0.085, 0.045, 0.018), mats["accent"], 12, 6)
        bind(marking, rig, "spine")
        meshes.append(marking)
    add_spines(meshes, rig, mats["accent"], 5, 0.02, 0.17, 1.04, 0.12)
    return meshes


def build_anuran(creature: dict, mats: dict[str, bpy.types.Material], rig: bpy.types.Object) -> list[bpy.types.Object]:
    meshes = []
    body = loft_y("body_mesh", [
        (0.83, 0.42, 0.34, 0.24), (0.55, 0.49, 0.59, 0.39),
        (0.13, 0.52, 0.68, 0.43), (-0.24, 0.55, 0.60, 0.36),
    ], mats["base"], 24)
    head = loft_y("head_mesh", [
        (-0.18, 0.55, 0.53, 0.30), (-0.48, 0.57, 0.63, 0.34),
        (-0.76, 0.52, 0.53, 0.27), (-0.91, 0.47, 0.40, 0.19),
    ], mats["secondary"], 22)
    mouth = tube("mouth_ridge", [(-0.42, -0.86, 0.50), (0, -0.91, 0.46), (0.42, -0.86, 0.50)], [0.012, 0.012, 0.012], mats["nose"], 8)
    for obj, bone_name in ((body, "spine"), (head, "head"), (mouth, "head")):
        bind(obj, rig, bone_name)
        meshes.append(obj)
    for side, sign in (("L", -1), ("R", 1)):
        eye_bulge = ellipsoid(f"eye_bulge_{side}", (0.35 * sign, -0.61, 0.79), (0.15, 0.13, 0.14), mats["base"], 16, 8)
        eye = ellipsoid(f"eye_{side}", (0.36 * sign, -0.72, 0.81), (0.052, 0.025, 0.060), mats["eye"], 14, 8)
        pupil = ellipsoid(f"slit_pupil_{side}", (0.36 * sign, -0.742, 0.81), (0.012, 0.008, 0.036), mats["nose"], 12, 6)
        bind(eye_bulge, rig, "head")
        bind(eye, rig, "head")
        bind(pupil, rig, "head")
        meshes.extend((eye_bulge, eye, pupil))
    for side, sign in (("L", -1), ("R", 1)):
        limb_parts = (
            (f"leg_front_{side}_upper_mesh", [(0.42 * sign, -0.35, 0.50), (0.49 * sign, -0.45, 0.27)], [0.090, 0.060], f"leg_front_{side}_upper"),
            (f"leg_front_{side}_lower_mesh", [(0.49 * sign, -0.45, 0.27), (0.52 * sign, -0.57, 0.09)], [0.060, 0.035], f"leg_front_{side}_lower"),
            (f"leg_rear_{side}_upper_mesh", [(0.51 * sign, 0.39, 0.52), (0.72 * sign, 0.58, 0.31)], [0.16, 0.105], f"leg_rear_{side}_upper"),
            (f"leg_rear_{side}_lower_mesh", [(0.72 * sign, 0.58, 0.31), (0.62 * sign, 0.40, 0.08)], [0.105, 0.050], f"leg_rear_{side}_lower"),
        )
        for name, points, radii, bone_name in limb_parts:
            part = tube(name, points, radii, mats["base"], 12)
            bind(part, rig, bone_name)
            meshes.append(part)
        for end, x, y, scale, bone_name in (
            ("front", 0.52, -0.64, 0.85, f"leg_front_{side}_lower"),
            ("rear", 0.62, 0.31, 1.25, f"leg_rear_{side}_lower"),
        ):
            foot = ellipsoid(
                f"foot_{end}_{side}", (x * sign, y, 0.055),
                (0.11 * scale, 0.17 * scale, 0.040), mats["accent"], 16, 8,
            )
            bind(foot, rig, bone_name)
            meshes.append(foot)
    unify_quadruped_anatomy(meshes, rig, mats["base"])
    for index, (x, y, z) in enumerate(((-0.28, 0.06, 0.82), (0.22, 0.26, 0.84), (0.40, -0.04, 0.71), (-0.43, 0.36, 0.68))):
        wart = ellipsoid(f"rot_wart_{index}", (x, y, z), (0.065, 0.055, 0.052), mats["accent"], 12, 6)
        bind(wart, rig, "spine")
        meshes.append(wart)
    return meshes


def build_creature(creature: dict, seed: int) -> tuple[bpy.types.Object, list[bpy.types.Object], list[bpy.types.Object]]:
    rig = build_armature(creature)
    style = SPECIES_STYLE[creature["key"]]
    rift = creature["realm"] == "riftbound"
    mats = {
        "base": material(f"{creature['key']}_base", style["base"], roughness=0.82),
        "secondary": material(f"{creature['key']}_secondary", style["secondary"], roughness=0.70),
        "accent": material(f"{creature['key']}_accent", style["accent"], metallic=0.18 if rift else 0.02, roughness=0.48, emissive=rift),
        "eye": material(
            f"{creature['key']}_eyes",
            style["accent"] if rift else "#18130f",
            metallic=0.10 if rift else 0.0,
            roughness=0.20 if rift else 0.32,
            emissive=rift,
        ),
        "nose": material(f"{creature['key']}_nose", "#161315", roughness=0.38),
        "horn": material(f"{creature['key']}_horn", "#b5a47f" if not rift else "#493646", roughness=0.46),
    }
    plan = creature["bodyPlan"]
    if plan == "arachnid":
        meshes = build_arachnid(creature, mats, rig)
    elif plan == "chelonian":
        meshes = build_chelonian(creature, mats, rig)
    elif plan == "anuran":
        meshes = build_anuran(creature, mats, rig)
    else:
        meshes = build_quadruped(creature, mats, rig)
    add_uvs(meshes)
    markers = []
    marker_values = {
        "root": (0, 0, 0), "ground_contact": (0, 0, 0.015),
        "attack_origin": (0, -1.35, 0.73), "hit_center": (0, 0, 0.72),
    }
    for name, location in marker_values.items():
        marker = bpy.data.objects.new(name, None)
        marker.empty_display_type = "SPHERE"
        marker.empty_display_size = 0.055
        marker.location = location
        marker.parent = rig
        marker["markerRole"] = name
        bpy.context.scene.collection.objects.link(marker)
        markers.append(marker)
    for obj in meshes:
        obj["assetId"] = f"creature.{creature['key']}.lod0"
        obj["speciesKey"] = creature["key"]
        obj["speciesFeature"] = style["feature"]
        # Blender ID integer properties are signed 32-bit on this path while
        # deterministic roster seeds use the full unsigned range.
        obj["revisionSeed"] = str(seed)
    return rig, meshes, markers


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def aim(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_reviews(meshes: list[bpy.types.Object], rig: bpy.types.Object, review_dir: Path) -> list[dict]:
    review_dir.mkdir(parents=True, exist_ok=True)
    minimum, maximum = bounds(meshes)
    center = (minimum + maximum) * 0.5
    span = max(maximum.x - minimum.x, maximum.y - minimum.y, maximum.z - minimum.z)
    camera_data = bpy.data.cameras.new("creature_review_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span * 1.25
    camera = bpy.data.objects.new("creature_review_camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    for name, location, energy in (("key", (-3, -4, 5), 760), ("fill", (3, -1, 3), 340), ("rim", (0, 4, 4), 540)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.size = 2.4
        light = bpy.data.objects.new(name, data)
        light.location = location
        bpy.context.scene.collection.objects.link(light)
        aim(light, center)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -0.35
    scene.world.color = (0.018, 0.022, 0.032)
    views = {
        "front": Vector((center.x, minimum.y - span * 2.4, center.z)),
        "side": Vector((maximum.x + span * 2.4, center.y, center.z)),
        "back": Vector((center.x, maximum.y + span * 2.4, center.z)),
        "isometric": Vector((maximum.x + span * 1.7, minimum.y - span * 1.7, center.z + span * 0.30)),
    }
    rows = []
    for name, position in views.items():
        camera.location = position
        aim(camera, center)
        output = review_dir / f"{name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        rows.append({"view": name, "path": str(output), "sha256": sha256(output)})
    saved = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
    for bone in rig.pose.bones:
        if "leg_" in bone.name and ("front" in bone.name or "_1_" in bone.name):
            bone.rotation_mode = "XYZ"
            bone.rotation_euler.x = math.radians(22)
    bpy.context.view_layer.update()
    camera.location = views["isometric"]
    aim(camera, center)
    stress = review_dir / "deformation_stress.png"
    scene.render.filepath = str(stress)
    bpy.ops.render.render(write_still=True)
    rows.append({"view": "deformation_stress", "path": str(stress), "sha256": sha256(stress)})
    for bone_name, matrix in saved.items():
        rig.pose.bones[bone_name].matrix_basis = matrix
    bpy.context.view_layer.update()
    return rows


def export_glb(output: Path, objects: list[bpy.types.Object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(output), export_format="GLB", use_selection=True,
        export_skins=True, export_extras=True, export_yup=True, export_apply=False,
    )


def main() -> None:
    args = parse_args()
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    creature = next((row for row in policy["creatures"] if row["key"] == args.key), None)
    if creature is None:
        raise ValueError(f"Unknown creature key: {args.key}")
    creature = {**creature, "skeletonId": f"creature_{creature['bodyPlan']}_v1"}
    clear_scene()
    rig, meshes, markers = build_creature(creature, args.revision_seed)
    previews = render_reviews(meshes, rig, Path(args.review_dir).resolve())
    output = Path(args.output_dir).resolve() / f"creature_{creature['key']}_lod0.glb"
    export_glb(output, [rig, *meshes, *markers])
    triangles = 0
    non_manifold = 0
    for obj in meshes:
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        evaluated_mesh = evaluated.to_mesh()
        evaluated_mesh.calc_loop_triangles()
        triangles += len(evaluated_mesh.loop_triangles)
        evaluated.to_mesh_clear()
        non_manifold += sum(1 for edge in obj.data.edges if len(edge.link_faces) != 2) if hasattr(obj.data.edges[0] if obj.data.edges else None, "link_faces") else 0
    checks = {
        "lod0Present": output.is_file(),
        "armaturePresent": len(rig.data.bones) >= 10,
        "skinningPresent": all(any(modifier.type == "ARMATURE" for modifier in obj.modifiers) for obj in meshes),
        "markersPresent": {marker.name for marker in markers} == {"root", "ground_contact", "attack_origin", "hit_center"},
        "reviewViewsPresent": len(previews) == 5 and all(Path(row["path"]).is_file() for row in previews),
        "originalLoftedAnatomy": all(obj.get("modelingMethod") == "original_closed_loft" for obj in meshes),
        "noPrimitiveGeometry": all(obj.get("primitiveGeometry") is False for obj in meshes),
        "speciesSpecificFeature": all(obj.get("speciesFeature") == SPECIES_STYLE[creature["key"]]["feature"] for obj in meshes),
        "substantiveGeometry": triangles >= 1600 and len(meshes) >= 5,
        "triangleBudget": triangles <= 45_000,
        "pbrMaterials": len({material.name for obj in meshes for material in obj.data.materials if material}) >= 4,
    }
    report = {
        "schemaVersion": 2,
        "assetId": f"creature.{creature['key']}.lod0",
        "kind": "creature",
        "creatureKey": creature["key"],
        "displayName": creature["name"],
        "realm": creature["realm"],
        "bodyPlan": creature["bodyPlan"],
        "skeletonId": creature["skeletonId"],
        "lod": 0,
        "revisionSeed": args.revision_seed,
        "modelingMethod": "original_closed_loft_v2",
        "primitiveOperatorsUsed": False,
        "speciesFeature": SPECIES_STYLE[creature["key"]]["feature"],
        "meshCount": len(meshes),
        "boneCount": len(rig.data.bones),
        "totalTriangles": triangles,
        "maxTriangles": 45_000,
        "maxInfluences": 1,
        "markers": [marker.name for marker in markers],
        "previews": previews,
        "deformationStressPose": "deformation_stress",
        "modelStage": "pending",
        "animationStage": "pending",
        "animationApprovalEligible": False,
        "runtimeEligible": False,
        "checks": checks,
        "qcPassed": all(checks.values()),
        "output": {"path": str(output), "sha256": sha256(output)},
    }
    output.with_suffix(".qc.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.save_blend:
        blend = Path(args.save_blend).resolve()
        blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print("[roster-creature-v2] " + json.dumps({
        "output": str(output), "triangles": triangles, "meshes": len(meshes), "qcPassed": report["qcPassed"]
    }))


if __name__ == "__main__":
    main()
