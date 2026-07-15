"""Build one draft nine-slot armor set from free CC0 MPFB wearables.

Five logical slots use authored MakeHuman clothes fitted to the accepted MPFB
body. The four remaining slots are derived from that body's surface or from
weighted cloth panels. Outputs are deliberately review-gated and never written
to the runtime model directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from bl_ext.blender_org.mpfb.services import HumanService, LocationService
from generate_mpfb_body import bake_targets_and_strip_helpers, prepare_runtime_materials


PIPELINE_ROOT = Path(__file__).resolve().parent.parent
RECIPE_PATH = (
    PIPELINE_ROOT
    / "data"
    / "body-families"
    / "armor-sets"
    / "free-pilot-armor-sets.json"
)
ARMOR_SLOTS = ("head", "shoulders", "chest", "hands", "waist", "legs", "feet", "back", "tabard")
REQUIRED_CLIPS = ("idle", "walk", "run", "combat_idle", "attack_melee", "attack_ranged", "cast", "death", "jump")
MODULE_TRIANGLE_LIMIT = 14_000
FIXTURE_CAPE_TRIANGLE_LIMIT = 25_000
MODULE_TRIANGLE_TARGET = 6_500
EQUIPPED_TRIANGLE_LIMIT = 120_000
GENERATOR_VERSION = "1.7.0-readable-dark-fantasy"

# Each layer is authored with a deterministic clearance from the accepted body.
# The values are deliberately small: enough to prevent coplanar fighting and
# garment-on-garment intersections without changing the accepted silhouette.
FITTED_LAYER_CLEARANCE = {
    "chest": 0.003,
    "hands": 0.004,
    "legs": 0.002,
    "feet": 0.004,
}
SURFACE_LAYER_CLEARANCE = {
    "shoulders": 0.016,
}
# The accepted body is the collision reference, not a second rigid shell. A
# 15 mm correction makes gloves and boots visibly float away from the limbs
# after the nearest-surface pass. Keep a small anti-z-fighting margin and let
# the authored fixture provide the rest of the garment volume.
MINIMUM_BODY_CLEARANCE_M = 0.004
SLOT_BODY_CLEARANCE = {
    # The cape is intentionally authored behind the body and can fold into
    # the back during idle. Keep its stricter audit margin without moving
    # gloves, boots, or fitted clothing away from their limbs.
    "back": 0.010,
}
SLOT_LAYER_ORDER = {
    "legs": 10,
    "chest": 20,
    "hands": 20,
    "feet": 20,
    "back": 30,
    "tabard": 30,
    "waist": 40,
    "shoulders": 50,
    "head": 50,
}

MPFB_TO_CANONICAL = {
    "Root": "root",
    "pelvis": "hips",
    "spine_01": "spine",
    "spine_02": "chest",
    "spine_03": "upper_chest",
    "clavicle_l": "shoulder_L",
    "upperarm_l": "upper_arm_L",
    "lowerarm_l": "forearm_L",
    "hand_l": "hand_L",
    "clavicle_r": "shoulder_R",
    "upperarm_r": "upper_arm_R",
    "lowerarm_r": "forearm_R",
    "hand_r": "hand_R",
    "neck_01": "neck",
    "thigh_l": "thigh_L",
    "calf_l": "shin_L",
    "foot_l": "foot_L",
    "ball_l": "toe_L",
    "thigh_r": "thigh_R",
    "calf_r": "shin_R",
    "foot_r": "foot_R",
    "ball_r": "toe_R",
}
for _side in ("l", "r"):
    _canonical_side = _side.upper()
    for _finger in ("thumb", "index", "middle", "ring", "pinky"):
        for _segment in ("01", "02", "03"):
            MPFB_TO_CANONICAL[f"{_finger}_{_segment}_{_side}"] = (
                f"{_finger}_{_segment}_{_canonical_side}"
            )


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True)
    parser.add_argument("--variant", required=True, choices=("m", "f"))
    parser.add_argument("--recipe-file", default=str(RECIPE_PATH))
    parser.add_argument("--set-id")
    parser.add_argument("--source-blend", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--save-blend")
    parser.add_argument("--weapon-glb")
    parser.add_argument("--resume-existing", action="store_true")
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_recipe(recipe_path: str, family: str, variant: str, set_id: str | None) -> tuple[dict, dict]:
    source = Path(recipe_path).resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    recipe = payload["sets"].get(set_id) if set_id else payload["sets"].get(family)
    if not recipe and set_id:
        recipe = next((value for value in payload["sets"].values() if value.get("setId") == set_id), None)
    if not recipe:
        raise RuntimeError(f"No armor recipe exists for {set_id or family} in {source}")
    if recipe.get("bodyFamily", family) != family:
        raise RuntimeError(f"Armor recipe {recipe['setId']} is not compatible with {family}")
    if variant not in recipe["bodyVariants"]:
        raise RuntimeError(f"Recipe {recipe['setId']} does not support {variant}")
    if tuple(recipe["modules"].keys()) != ARMOR_SLOTS:
        raise RuntimeError("Armor recipe must declare the canonical nine slots in order")
    return payload, recipe


def hex_color(value: str) -> tuple[float, float, float, float]:
    """Return normalized sRGB channels for an sRGB base-color image.

    The generated texture is tagged as sRGB below. Supplying linearized values
    here causes the browser renderer to decode them a second time, crushing
    dark cloth and leather toward black. Blender's material viewport can hide
    that mistake, so keep the conversion boundary explicit here.
    """
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)) + (1.0,)


def create_image(name: str, size: int, pixel_fn, colorspace: str) -> bpy.types.Image:
    image = bpy.data.images.get(name) or bpy.data.images.new(name, width=size, height=size, alpha=True)
    # Blender 5 reloads/clears a generated image when its color space changes
    # or update() is called after pixel assignment. Configure first, then write
    # and pack the final buffer so the embedded glTF texture is not black.
    if tuple(image.size) != (size, size):
        image.scale(size, size)
    image.colorspace_settings.name = colorspace
    pixels: list[float] = []
    for y in range(size):
        for x in range(size):
            pixels.extend(pixel_fn(x / max(1, size - 1), y / max(1, size - 1)))
    image.pixels[:] = pixels
    image.pack()
    sample_offsets = (0, (size * size // 2) * 4, (size * size - 1) * 4)
    for offset in sample_offsets:
        expected = pixels[offset : offset + 4]
        observed = list(image.pixels[offset : offset + 4])
        if max(abs(left - right) for left, right in zip(expected, observed)) > 0.01:
            raise RuntimeError(
                f"Generated image {name} lost pixel data at offset {offset}: "
                f"expected={expected}, observed={observed}"
            )
    image.use_fake_user = True
    return image


def gltf_occlusion_group() -> bpy.types.NodeTree:
    group = bpy.data.node_groups.get("glTF Material Output")
    if group:
        return group
    group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    group.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return group


def pbr_material(family: str, style: str, color_value: str) -> bpy.types.Material:
    name = f"{family}_{style}_draft_pbr"
    existing = bpy.data.materials.get(name)
    base = hex_color(color_value)
    metallic = 0.78 if style == "metal" else 0.08 if style == "accent" else 0.0
    roughness = 0.38 if style == "metal" else 0.64 if style == "leather" else 0.78
    size = 128
    weave_strength = 0.085 if style in {"cloth", "leather"} else 0.045
    base_image = create_image(
        f"{name}_baseColor",
        size,
        lambda u, v: tuple(
            max(
                0.0,
                min(
                    1.0,
                    channel * (
                        0.90
                        + weave_strength * (
                            0.52 * math.sin(u * 2.0 * math.pi * 57.0)
                            + 0.35 * math.sin(v * 2.0 * math.pi * 53.0)
                            + 0.18 * math.sin((u + v) * 2.0 * math.pi * 19.0)
                        )
                        + 0.025 * math.sin(u * 2.0 * math.pi * 11.0 + v * 2.0 * math.pi * 7.0)
                    ),
                ),
            )
            for channel in base[:3]
        )
        + (1.0,),
        "sRGB",
    )
    normal_image = create_image(
        f"{name}_normal",
        size,
        lambda u, v: (
            0.5 + (0.07 if style in {"cloth", "leather"} else 0.04) * math.sin(u * 52.0),
            0.5 + (0.07 if style in {"cloth", "leather"} else 0.04) * math.cos(v * 47.0),
            1.0,
            1.0,
        ),
        "Non-Color",
    )
    orm_image = create_image(
        f"{name}_orm",
        size,
        lambda u, v: (
            0.96,
            max(0.0, min(1.0, roughness + 0.05 * math.sin(u * 31.0 + v * 37.0))),
            metallic,
            1.0,
        ),
        "Non-Color",
    )
    if existing:
        # Rewriting the named image datablocks above repairs resume blends made
        # by the older Blender-5-incompatible pixel ordering.
        existing.use_fake_user = True
        return existing
    material = bpy.data.materials.new(name)
    # MPFB removes temporary source materials while loading each wearable. Keep
    # the shared draft material alive until it is assigned to the fitted mesh.
    material.use_fake_user = True
    material.use_nodes = True
    material.diffuse_color = base
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    base_node = nodes.new("ShaderNodeTexImage")
    base_node.image = base_image
    normal_node = nodes.new("ShaderNodeTexImage")
    normal_node.image = normal_image
    normal_node.image.colorspace_settings.name = "Non-Color"
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = 0.28
    orm_node = nodes.new("ShaderNodeTexImage")
    orm_node.image = orm_image
    orm_node.image.colorspace_settings.name = "Non-Color"
    separate = nodes.new("ShaderNodeSeparateColor")
    occlusion = nodes.new("ShaderNodeGroup")
    occlusion.node_tree = gltf_occlusion_group()
    occlusion.name = "glTF Material Output"
    links.new(base_node.outputs["Color"], shader.inputs["Base Color"])
    links.new(normal_node.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    links.new(orm_node.outputs["Color"], separate.inputs["Color"])
    links.new(separate.outputs["Red"], occlusion.inputs["Occlusion"])
    links.new(separate.outputs["Green"], shader.inputs["Roughness"])
    links.new(separate.outputs["Blue"], shader.inputs["Metallic"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def assign_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.material_index = 0


def style_fixture_materials(
    obj: bpy.types.Object,
    fallback: bpy.types.Material,
    style: str,
) -> None:
    """Apply the authored class palette without carrying modern source colors.

    The fitted MPFB fixtures are used for silhouette and topology, while their
    source textures are intentionally not used for runtime armor. Several
    packs contain bright contemporary graphics or gold/saturated materials that
    defeat class art direction, and a post-export tint cannot reliably replace
    a linked glTF base-color image. The deterministic generated PBR material is
    therefore the single runtime material for every armor fixture.
    """
    source_names = [slot.material.name for slot in obj.material_slots if slot.material]
    assign_material(obj, fallback)
    obj["fixtureMaterialsPreserved"] = False
    obj["fixturePaletteApplied"] = True
    obj["fixtureMaterialNames"] = fallback.name
    obj["fixtureSourceMaterialNames"] = ",".join(source_names)


def apply_shape_key_mix(obj: bpy.types.Object) -> None:
    """Bake MPFB's fitted-clothing shape into the exported LOD0 mesh."""
    if not obj.data.shape_keys or not obj.data.shape_keys.key_blocks:
        return
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shape_key_remove(all=True, apply_mix=True)


def offset_vertices_along_normals(obj: bpy.types.Object, distance: float) -> None:
    """Move an authored garment to its deterministic runtime layer."""
    if abs(distance) <= 1e-8:
        return
    for vertex in obj.data.vertices:
        vertex.co += vertex.normal * distance
    obj.data.update()


def enforce_body_clearance(
    obj: bpy.types.Object,
    body: bpy.types.Object,
    clearance: float = MINIMUM_BODY_CLEARANCE_M,
) -> int:
    """Project garment vertices outside the accepted body with a fixed margin.

    MPFB fitting follows the source garment closely enough that authored seams
    can remain slightly inside a class-proportioned body. The independent
    clearance audit treats those intersections as failures, so apply one final
    deterministic nearest-surface correction after topology cleanup. Vertices
    farther than the audit probe radius are left unchanged.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_body = body.evaluated_get(depsgraph)
    body_mesh = evaluated_body.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
    try:
        transform = evaluated_body.matrix_world
        body_vertices = [transform @ vertex.co for vertex in body_mesh.vertices]
        body_mesh.calc_loop_triangles()
        triangles = [tuple(triangle.vertices) for triangle in body_mesh.loop_triangles]
        signed_volume = sum(
            body_vertices[a].dot(body_vertices[b].cross(body_vertices[c]))
            for a, b, c in triangles
        ) / 6.0
        if signed_volume < 0.0:
            triangles = [(a, c, b) for a, b, c in triangles]
        body_bvh = BVHTree.FromPolygons(
            body_vertices,
            triangles,
            all_triangles=True,
            epsilon=1e-7,
        )
    finally:
        evaluated_body.to_mesh_clear()
    if body_bvh is None:
        raise RuntimeError(f"Could not build clearance BVH for {body.name}")
    obj_to_world = obj.matrix_world
    world_to_obj = obj.matrix_world.inverted()
    moved = 0
    for vertex in obj.data.vertices:
        world_point = obj_to_world @ vertex.co
        corrected = world_point.copy()
        was_moved = False
        for _iteration in range(8):
            nearest = body_bvh.find_nearest(corrected, 0.12)
            if nearest[0] is None or nearest[1] is None:
                break
            location, normal, _face_index, _distance = nearest
            normal = normal.normalized()
            signed_distance = (corrected - location).dot(normal)
            if signed_distance >= clearance:
                break
            corrected += normal * (clearance - signed_distance)
            was_moved = True
        if was_moved:
            vertex.co = world_to_obj @ corrected
            moved += 1
    if moved:
        obj.data.update()
    obj["bodyClearanceMeters"] = clearance
    obj["bodyClearanceVerticesMoved"] = moved
    return moved


def body_clearance_for_slot(slot: str) -> float:
    return SLOT_BODY_CLEARANCE.get(slot, MINIMUM_BODY_CLEARANCE_M)


def trim_distal_underlap(
    obj: bpy.types.Object,
    rig: bpy.types.Object,
    proximal_bone: str,
    distal_bone: str,
    t_cut: float,
) -> None:
    """Terminate an inner garment beneath its owning gauntlet or boot.

    The cut is expressed along each canonical limb bone, so it remains stable
    across body variants and does not rely on one character's world-space
    wrist or ankle height. A short hidden overlap remains inside the outer
    module; distal geometry that would visibly cross it is removed.
    """
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    try:
        deform = mesh.verts.layers.deform.active
        if deform is None:
            raise RuntimeError(f"{obj.name} has no deform weights for seam trimming")
        obj_to_rig = rig.matrix_world.inverted() @ obj.matrix_world
        rig_to_obj = obj.matrix_world.inverted() @ rig.matrix_world
        normal_matrix = rig_to_obj.inverted_safe().transposed().to_3x3()

        for side in ("L", "R"):
            bone_name = f"{proximal_bone}_{side}"
            bone = rig.data.bones.get(bone_name)
            if bone is None:
                raise RuntimeError(f"Canonical seam bone is missing: {bone_name}")
            group_indices = [
                group.index
                for name in (f"{proximal_bone}_{side}", f"{distal_bone}_{side}")
                if (group := obj.vertex_groups.get(name)) is not None
            ]
            if not group_indices:
                # Sleeveless tops and cropped leg fixtures have no distal
                # geometry to trim; absence of both weight groups is the
                # authored seam, not a fitting failure.
                continue
            axis = bone.tail_local - bone.head_local
            if axis.length_squared <= 1e-10:
                raise RuntimeError(f"Canonical seam bone has zero length: {bone_name}")

            def side_weight(vertex: bmesh.types.BMVert) -> float:
                weights = vertex[deform]
                return sum(weights.get(index, 0.0) for index in group_indices)

            def bone_parameter(vertex: bmesh.types.BMVert) -> float:
                point = obj_to_rig @ vertex.co
                return (point - bone.head_local).dot(axis) / axis.length_squared

            region_faces = [
                face
                for face in mesh.faces
                if max(side_weight(vertex) for vertex in face.verts) >= 0.35
            ]
            if not region_faces:
                continue
            region = set(region_faces)
            for face in region_faces:
                region.update(face.edges)
                region.update(face.verts)
            plane_co = rig_to_obj @ (bone.head_local + axis * t_cut)
            plane_no = (normal_matrix @ axis.normalized()).normalized()
            bmesh.ops.bisect_plane(
                mesh,
                geom=list(region),
                plane_co=plane_co,
                plane_no=plane_no,
                dist=1e-5,
                clear_inner=False,
                clear_outer=False,
            )
            distal_faces = [
                face
                for face in mesh.faces
                if max(side_weight(vertex) for vertex in face.verts) >= 0.35
                and sum(bone_parameter(vertex) for vertex in face.verts) / len(face.verts)
                > t_cut + 1e-5
            ]
            if not distal_faces:
                continue
            bmesh.ops.delete(mesh, geom=distal_faces, context="FACES")

        loose_edges = [edge for edge in mesh.edges if not edge.link_faces]
        if loose_edges:
            bmesh.ops.delete(mesh, geom=loose_edges, context="EDGES")
        loose_vertices = [vertex for vertex in mesh.verts if not vertex.link_edges]
        if loose_vertices:
            bmesh.ops.delete(mesh, geom=loose_vertices, context="VERTS")
        bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
        mesh.to_mesh(obj.data)
        obj.data.update()
    finally:
        mesh.free()


def canonicalize_groups(obj: bpy.types.Object) -> None:
    for old_name, new_name in MPFB_TO_CANONICAL.items():
        group = obj.vertex_groups.get(old_name)
        if group:
            group.name = new_name


SLOT_BONE_FILTERS = {
    "shoulders": {"shoulder_L", "upper_arm_L", "shoulder_R", "upper_arm_R", "upper_chest"},
    "chest": {
        "hips", "spine", "chest", "upper_chest", "neck",
        "shoulder_L", "upper_arm_L", "forearm_L",
        "shoulder_R", "upper_arm_R", "forearm_R",
    },
    "waist": {"hips", "spine"},
    "legs": {"hips", "thigh_L", "shin_L", "thigh_R", "shin_R"},
    "back": {"hips", "spine", "chest", "upper_chest", "thigh_L", "thigh_R"},
    "tabard": {"hips", "spine", "thigh_L", "thigh_R"},
}


def trim_fixture_to_slot(
    obj: bpy.types.Object,
    body: bpy.types.Object,
    slot: str,
) -> None:
    """Extract the requested module from full-outfit MakeClothes fixtures.

    Several of the strongest installed assets are complete suits. Treating one
    as a chest module while also exporting its boots and legs caused the old
    chest/feet and chest/legs collision failures. This keeps the authored
    surface and UVs but removes geometry owned by other modular slots.
    """
    allowed_names = SLOT_BONE_FILTERS.get(slot)
    if not allowed_names:
        return
    allowed_indices = {
        group.index for group in obj.vertex_groups if group.name in allowed_names
    }
    if not allowed_indices:
        raise RuntimeError(f"{obj.name} has no canonical weights for {slot} extraction")

    body_group = body.vertex_groups.get("body")
    if body_group is None:
        raise RuntimeError("Accepted MPFB body has no body vertex group for fixture segmentation")
    body_world = [
        body.matrix_world @ vertex.co
        for vertex in body.data.vertices
        if any(
            assignment.group == body_group.index and assignment.weight > 0.0
            for assignment in vertex.groups
        )
    ]
    if not body_world:
        raise RuntimeError("Accepted MPFB body has no weighted body vertices for fixture segmentation")
    body_to_obj = obj.matrix_world.inverted()
    bounds = [body_to_obj @ point for point in body_world]
    minimum = Vector(tuple(min(point[axis] for point in bounds) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in bounds) for axis in range(3)))
    extent = maximum - minimum
    center = (minimum + maximum) * 0.5

    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    try:
        deform = mesh.verts.layers.deform.active
        if deform is None:
            raise RuntimeError(f"{obj.name} has no deform layer for {slot} extraction")

        def allowed_weight(vertex: bmesh.types.BMVert) -> float:
            weights = vertex[deform]
            return sum(weights.get(index, 0.0) for index in allowed_indices)

        def spatially_allowed(face: bmesh.types.BMFace) -> bool:
            point = sum((vertex.co for vertex in face.verts), Vector()) / len(face.verts)
            if slot == "shoulders":
                return point.z >= minimum.z + extent.z * 0.66 and abs(point.x - center.x) >= extent.x * 0.18
            if slot == "waist":
                return minimum.z + extent.z * 0.46 <= point.z <= minimum.z + extent.z * 0.61
            if slot == "back":
                return (
                    point.y >= center.y + extent.y * 0.10
                    and face.normal.y >= 0.02
                    and point.z >= minimum.z + extent.z * 0.28
                )
            if slot == "tabard":
                return (
                    point.y <= center.y - extent.y * 0.08
                    and face.normal.y <= -0.02
                    and minimum.z + extent.z * 0.27 <= point.z <= minimum.z + extent.z * 0.59
                )
            return True

        # Robe-based cape/tabard extraction is primarily spatial. Some older
        # MakeClothes robe files carry broad helper weights that do not map
        # cleanly to the game-engine bone names, but their fitted coordinates
        # remain deterministic and valid.
        spatial_only = slot in {"back", "tabard"}
        delete_faces = [
            face
            for face in mesh.faces
            if (not spatial_only and max(allowed_weight(vertex) for vertex in face.verts) < 0.12)
            or not spatially_allowed(face)
        ]
        if not delete_faces:
            obj["fixtureSegment"] = slot
            obj["fixtureSegmentFacesRemoved"] = 0
            return
        if len(delete_faces) == len(mesh.faces):
            centroids = [
                sum((vertex.co for vertex in face.verts), Vector()) / len(face.verts)
                for face in mesh.faces
            ]
            source_minimum = tuple(min(point[axis] for point in centroids) for axis in range(3))
            source_maximum = tuple(max(point[axis] for point in centroids) for axis in range(3))
            raise RuntimeError(
                f"Unexpected {slot} extraction for {obj.name}: removed {len(delete_faces)} of {len(mesh.faces)} faces; "
                f"bodyBounds={tuple(minimum)}..{tuple(maximum)}, sourceBounds={source_minimum}..{source_maximum}"
            )
        bmesh.ops.delete(mesh, geom=delete_faces, context="FACES")
        loose_edges = [edge for edge in mesh.edges if not edge.link_faces]
        if loose_edges:
            bmesh.ops.delete(mesh, geom=loose_edges, context="EDGES")
        loose_vertices = [vertex for vertex in mesh.verts if not vertex.link_edges]
        if loose_vertices:
            bmesh.ops.delete(mesh, geom=loose_vertices, context="VERTS")
        bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
        mesh.to_mesh(obj.data)
        obj.data.update()
        obj["fixtureSegment"] = slot
        obj["fixtureSegmentFacesRemoved"] = len(delete_faces)
    finally:
        mesh.free()


def ensure_armature(obj: bpy.types.Object, rig: bpy.types.Object) -> None:
    modifiers = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"]
    if not modifiers:
        modifier = obj.modifiers.new("humanoid_game_v2", "ARMATURE")
        modifiers = [modifier]
    for modifier in modifiers:
        modifier.object = rig
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()


def evaluated_triangles(obj: bpy.types.Object) -> int:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        return len(mesh.loop_triangles)
    finally:
        evaluated.to_mesh_clear()


def module_triangle_limit(slot: str) -> int:
    # A robe-derived cape is a broad deforming surface; it may use additional
    # triangles as long as the equipped character remains under the 120k cap.
    return FIXTURE_CAPE_TRIANGLE_LIMIT if slot == "back" else MODULE_TRIANGLE_LIMIT


def apply_modifier(obj: bpy.types.Object, modifier: bpy.types.Modifier) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    # MPFB puts its armature modifier first. Geometry modifiers must be applied
    # ahead of it or Blender evaluates a deformed intermediate mesh and can
    # introduce invalid/non-manifold output.
    bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=0)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def close_open_surface(obj: bpy.types.Object, thickness: float = 0.003) -> None:
    if non_manifold_edges(obj) == 0:
        return
    solidify = obj.modifiers.new("draft_closed_surface", "SOLIDIFY")
    solidify.thickness = thickness
    solidify.offset = 0.0
    solidify.use_rim = True
    apply_modifier(obj, solidify)


def enforce_triangle_budget(obj: bpy.types.Object, target: int = MODULE_TRIANGLE_TARGET) -> bool:
    triangles = evaluated_triangles(obj)
    if triangles <= target:
        return False
    decimate = obj.modifiers.new("draft_triangle_budget", "DECIMATE")
    decimate.ratio = max(0.05, target / triangles)
    decimate.use_collapse_triangulate = True
    apply_modifier(obj, decimate)
    return True


def manifold_rigid_headpiece(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    """Voxel-remesh a complex authored helmet and bind it rigidly to the head.

    Some CC0 helmet sources contain overlapping decorative shells sharing the
    same edges. Solidify cannot repair those multi-face edges. A review-level
    voxel remesh preserves the silhouette while producing one closed surface;
    rigid head weighting is also more correct than interpolated face weights.
    """
    # The modifier-based voxel path can preserve invalid multi-face edges from
    # old MakeClothes OBJ shells. Blender's object voxel-remesh operator
    # rebuilds the occupied volume instead, which is the invariant we need for
    # a closed runtime headpiece.
    last_non_manifold = 0
    last_degenerate = 0
    for resolution_divisor in (105.0, 90.0, 75.0):
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        obj.data.remesh_voxel_size = max(obj.dimensions) / resolution_divisor
        obj.data.remesh_voxel_adaptivity = 0.0
        obj.data.use_remesh_fix_poles = True
        obj.data.use_remesh_preserve_volume = True
        bpy.ops.object.voxel_remesh()
        obj.select_set(False)
        for group in list(obj.vertex_groups):
            obj.vertex_groups.remove(group)
        head = obj.vertex_groups.new(name="head")
        head.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
        assign_material(obj, material)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project()
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.select_set(False)
        enforce_triangle_budget(obj, MODULE_TRIANGLE_TARGET - 2000)
        for _repair_iteration in range(6):
            cleanup_closed_mesh(obj)
            resolve_multi_face_edges(obj)
            cleanup_closed_mesh(obj)
            if non_manifold_edges(obj) == 0 and degenerate_faces(obj) == 0:
                break
        last_non_manifold = non_manifold_edges(obj)
        last_degenerate = degenerate_faces(obj)
        if last_non_manifold == 0 and last_degenerate == 0:
            return
    raise RuntimeError(
        "Voxel-remeshed helmet did not converge after three resolutions: "
        f"{last_non_manifold} non-manifold edges, "
        f"{last_degenerate} degenerate faces"
    )


def cleanup_closed_mesh(obj: bpy.types.Object) -> None:
    """Weld split vertices, remove degenerate geometry, and cap boundaries."""
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    try:
        bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1e-6)
        bmesh.ops.dissolve_degenerate(mesh, edges=list(mesh.edges), dist=1e-8)
        # A projected triangle can become a long, near-collinear sliver whose
        # edges are individually larger than dissolve_degenerate's distance.
        # Collapse the shortest edge of that face so technical QC and the GLB
        # triangulator agree that no zero-area geometry remains.
        for _iteration in range(3):
            sliver_edges = {
                min(face.edges, key=lambda edge: edge.calc_length())
                for face in mesh.faces
                # Use one order of magnitude of headroom over the QC cutoff;
                # Blender can round a BMesh face down slightly when writing it
                # back to Mesh polygon storage.
                if face.calc_area() <= 1e-9
            }
            if not sliver_edges:
                break
            bmesh.ops.collapse(mesh, edges=list(sliver_edges))
        loose_edges = [edge for edge in mesh.edges if not edge.link_faces]
        if loose_edges:
            bmesh.ops.delete(mesh, geom=loose_edges, context="EDGES")
        loose_verts = [vertex for vertex in mesh.verts if not vertex.link_edges]
        if loose_verts:
            bmesh.ops.delete(mesh, geom=loose_verts, context="VERTS")
        boundary = [edge for edge in mesh.edges if len(edge.link_faces) == 1]
        if boundary:
            bmesh.ops.holes_fill(mesh, edges=boundary, sides=0)
        bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
        mesh.to_mesh(obj.data)
        obj.data.update()
    finally:
        mesh.free()


def triangulate_faces(obj: bpy.types.Object) -> None:
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    try:
        bmesh.ops.triangulate(
            mesh,
            faces=list(mesh.faces),
            quad_method="BEAUTY",
            ngon_method="BEAUTY",
        )
        mesh.to_mesh(obj.data)
        obj.data.update()
    finally:
        mesh.free()


def resolve_multi_face_edges(obj: bpy.types.Object) -> None:
    """Remove only the smallest surplus faces at rare voxel self-contacts."""
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    try:
        surplus_faces = set()
        for edge in mesh.edges:
            if len(edge.link_faces) > 2:
                ranked = sorted(edge.link_faces, key=lambda face: face.calc_area(), reverse=True)
                surplus_faces.update(ranked[2:])
        if surplus_faces:
            bmesh.ops.delete(mesh, geom=list(surplus_faces), context="FACES")
        boundary = [edge for edge in mesh.edges if len(edge.link_faces) == 1]
        if boundary:
            bmesh.ops.triangle_fill(mesh, edges=boundary, use_beauty=True)
        bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
        mesh.to_mesh(obj.data)
        obj.data.update()
    finally:
        mesh.free()


def patch_small_non_manifold_region(obj: bpy.types.Object, edge_limit: int = 24) -> bool:
    """Excise and refill a tiny invalid patch left by collapse decimation."""
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    try:
        invalid = [edge for edge in mesh.edges if len(edge.link_faces) != 2]
        if not invalid or len(invalid) > edge_limit:
            return False
        affected_faces = {face for edge in invalid for face in edge.link_faces}
        if not affected_faces:
            return False
        # Include one surrounding face ring so the replacement boundary is a
        # simple loop instead of the same pinched four-edge configuration.
        affected_vertices = {vertex for face in affected_faces for vertex in face.verts}
        affected_faces.update(
            face for vertex in affected_vertices for face in vertex.link_faces
        )
        bmesh.ops.delete(mesh, geom=list(affected_faces), context="FACES")
        loose_edges = [edge for edge in mesh.edges if not edge.link_faces]
        if loose_edges:
            bmesh.ops.delete(mesh, geom=loose_edges, context="EDGES")
        loose_vertices = [vertex for vertex in mesh.verts if not vertex.link_edges]
        if loose_vertices:
            bmesh.ops.delete(mesh, geom=loose_vertices, context="VERTS")
        boundary = [edge for edge in mesh.edges if len(edge.link_faces) == 1]
        if boundary:
            bmesh.ops.triangle_fill(mesh, edges=boundary, use_beauty=True)
        bmesh.ops.recalc_face_normals(mesh, faces=list(mesh.faces))
        mesh.to_mesh(obj.data)
        obj.data.update()
        return True
    finally:
        mesh.free()


def manifold_skinned_wearable(
    obj: bpy.types.Object,
    rig: bpy.types.Object,
    material: bpy.types.Material,
) -> None:
    """Rebuild a closed garment volume and restore its fitted skin weights."""
    original_mesh = obj.data.copy()
    group_names = {group.index: group.name for group in obj.vertex_groups}
    source_weights: list[list[tuple[str, float]]] = []
    tree = KDTree(len(original_mesh.vertices))
    for vertex in original_mesh.vertices:
        tree.insert(vertex.co, vertex.index)
        source_weights.append([
            (group_names[group.group], group.weight)
            for group in vertex.groups
            if group.group in group_names and group.weight > 1e-8
        ])
    tree.balance()
    last_non_manifold = 0
    last_degenerate = 0
    # The source shells are only a few millimetres thick. The coarser helmet
    # resolution erases cloth volume and creates point contacts, so preserve a
    # sub-centimetre voxel here and reduce only after the shell is closed.
    for resolution_divisor in (340.0, 285.0, 230.0):
        obj.data = original_mesh.copy()
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        obj.data.remesh_voxel_size = max(obj.dimensions) / resolution_divisor
        obj.data.remesh_voxel_adaptivity = 0.0
        obj.data.use_remesh_fix_poles = True
        obj.data.use_remesh_preserve_volume = True
        bpy.ops.object.voxel_remesh()
        obj.select_set(False)
        for group in list(obj.vertex_groups):
            obj.vertex_groups.remove(group)
        restored_groups = {
            name: obj.vertex_groups.new(name=name)
            for name in sorted(set(group_names.values()))
        }
        for vertex in obj.data.vertices:
            _point, source_index, _distance = tree.find(vertex.co)
            for group_name, weight in source_weights[source_index]:
                restored_groups[group_name].add([vertex.index], weight, "REPLACE")
        assign_material(obj, material)
        cleanup_closed_mesh(obj)
        resolve_multi_face_edges(obj)
        cleanup_closed_mesh(obj)
        enforce_triangle_budget(obj, MODULE_TRIANGLE_TARGET - 2000)
        for _repair_iteration in range(6):
            cleanup_closed_mesh(obj)
            resolve_multi_face_edges(obj)
            cleanup_closed_mesh(obj)
            if non_manifold_edges(obj) == 0 and degenerate_faces(obj) == 0:
                break
        if non_manifold_edges(obj):
            patch_small_non_manifold_region(obj)
            cleanup_closed_mesh(obj)
        ensure_armature(obj, rig)
        last_non_manifold = non_manifold_edges(obj)
        last_degenerate = degenerate_faces(obj)
        if last_non_manifold == 0 and last_degenerate == 0:
            return
    raise RuntimeError(
        f"Skinned voxel repair could not close {obj.name}: "
        f"{last_non_manifold} non-manifold edges, {last_degenerate} degenerate faces"
    )


def refine_shoulder_shell(
    obj: bpy.types.Object,
    body: bpy.types.Object,
    rig: bpy.types.Object,
    material: bpy.types.Material,
    module: dict,
) -> None:
    """Turn the selected shoulder volume into two clean rounded pauldrons.

    The source-body face selection has an intentionally anatomical boundary,
    but that boundary is too irregular to serve directly as an armor edge.
    Voxel remeshing removes small disconnected shards and produces closed left
    and right shells; deterministic side weights then restore deformation.
    """
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    # Size is based on the full left-to-right span, so /50 still leaves ample
    # resolution on each pauldron while staying below the hard 14k slot budget
    # without a topology-damaging collapse decimation.
    obj.data.remesh_voxel_size = max(obj.dimensions) / 50.0
    obj.data.remesh_voxel_adaptivity = 0.0
    obj.data.use_remesh_fix_poles = True
    obj.data.use_remesh_preserve_volume = True
    bpy.ops.object.voxel_remesh()
    obj.select_set(False)

    # Keep only the dominant connected shell per shoulder so remeshing cannot
    # leave small floating fragments around the plate edge.
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    try:
        unseen = set(mesh.verts)
        components: list[list[bmesh.types.BMVert]] = []
        while unseen:
            seed = unseen.pop()
            component = [seed]
            stack = [seed]
            while stack:
                current = stack.pop()
                for edge in current.link_edges:
                    neighbor = edge.other_vert(current)
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        component.append(neighbor)
                        stack.append(neighbor)
            components.append(component)
        keep: set[bmesh.types.BMVert] = set()
        for positive_x in (False, True):
            side_components = [
                component
                for component in components
                if (sum(vertex.co.x for vertex in component) / len(component) >= 0.0)
                == positive_x
            ]
            if not side_components:
                raise RuntimeError("Rounded shoulder remesh lost one pauldron side")
            keep.update(max(side_components, key=len))
        discard = [vertex for vertex in mesh.verts if vertex not in keep]
        if discard:
            bmesh.ops.delete(mesh, geom=discard, context="VERTS")
        mesh.to_mesh(obj.data)
        obj.data.update()
    finally:
        mesh.free()

    smooth = obj.modifiers.new("pauldron_surface_relax", "SMOOTH")
    smooth.factor = 0.34
    smooth.iterations = 4
    apply_modifier(obj, smooth)

    # Voxel-remeshed anatomical patches are intentionally watertight, but on
    # short/broad bodies their vertical envelope can read as two boulders near
    # the head. Compact each disconnected pauldron about its own center. A
    # small deterministic outer flare retains class silhouette variation.
    side_vertices = {
        "L": [vertex for vertex in obj.data.vertices if vertex.co.x >= 0.0],
        "R": [vertex for vertex in obj.data.vertices if vertex.co.x < 0.0],
    }
    winged = module.get("silhouetteProfile") == "winged"
    for side, vertices in side_vertices.items():
        if not vertices:
            raise RuntimeError(f"Rounded shoulder remesh lost {side} pauldron vertices")
        center = sum((vertex.co for vertex in vertices), Vector()) / len(vertices)
        direction = 1.0 if side == "L" else -1.0
        for vertex in vertices:
            delta = vertex.co - center
            vertex.co.x = center.x + delta.x * (0.92 if winged else 0.82) + direction * (0.018 if winged else 0.0)
            vertex.co.y = center.y + delta.y * 0.68
            vertex.co.z = center.z + delta.z * (0.54 if winged else 0.48) - 0.025
    obj.data.update()
    offset_vertices_along_normals(obj, 0.004)

    for group in list(obj.vertex_groups):
        obj.vertex_groups.remove(group)
    groups = {
        name: obj.vertex_groups.new(name=name)
        for name in ("shoulder_L", "upper_arm_L", "shoulder_R", "upper_arm_R")
        if rig.data.bones.get(name)
    }
    for vertex in obj.data.vertices:
        side = "L" if vertex.co.x >= 0.0 else "R"
        shoulder_weight = 0.82
        groups[f"shoulder_{side}"].add([vertex.index], shoulder_weight, "REPLACE")
        groups[f"upper_arm_{side}"].add([vertex.index], 1.0 - shoulder_weight, "REPLACE")

    assign_material(obj, material)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    cleanup_closed_mesh(obj)
    ensure_armature(obj, rig)


def influence_counts(obj: bpy.types.Object, bone_names: set[str]) -> tuple[int, int]:
    bone_groups = {group.index for group in obj.vertex_groups if group.name in bone_names}
    maximum = 0
    unweighted = 0
    for vertex in obj.data.vertices:
        count = sum(1 for assignment in vertex.groups if assignment.group in bone_groups and assignment.weight > 1e-8)
        maximum = max(maximum, count)
        if count == 0:
            unweighted += 1
    return maximum, unweighted


def limit_influences(obj: bpy.types.Object, bone_names: set[str], limit: int = 4) -> tuple[int, int]:
    bone_groups = {group.index: group for group in obj.vertex_groups if group.name in bone_names}
    maximum_before = 0
    for vertex in obj.data.vertices:
        influences = [
            (assignment.group, assignment.weight)
            for assignment in vertex.groups
            if assignment.group in bone_groups and assignment.weight > 1e-8
        ]
        maximum_before = max(maximum_before, len(influences))
        influences.sort(key=lambda item: item[1], reverse=True)
        kept = influences[:limit]
        total = sum(weight for _, weight in kept)
        for group_index, _weight in influences[limit:]:
            bone_groups[group_index].remove([vertex.index])
        if total > 0:
            for group_index, weight in kept:
                bone_groups[group_index].add([vertex.index], weight / total, "REPLACE")
    _maximum_after, unweighted = influence_counts(obj, bone_names)
    return maximum_before, unweighted


def non_manifold_edges(obj: bpy.types.Object) -> int:
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    try:
        return sum(1 for edge in mesh.edges if len(edge.link_faces) != 2)
    finally:
        mesh.free()


def degenerate_faces(obj: bpy.types.Object) -> int:
    return sum(1 for polygon in obj.data.polygons if polygon.area <= 1e-10)


def body_group_weight(body: bpy.types.Object, vertex, group_name: str) -> float:
    group = body.vertex_groups.get(group_name)
    if not group:
        return 0.0
    return next((assignment.weight for assignment in vertex.groups if assignment.group == group.index), 0.0)


def create_curved_pauldron_pair(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    name: str,
    module: dict,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Build two compact, closed shoulder plates from accepted body bounds.

    A full-outfit fixture rarely transfers shoulder-only weights reliably to
    every race/variant. This small parametric plate supplies the modular seam
    while the class's helmet, torso, gloves, legs, and boots remain authored
    MPFB pack geometry.
    """
    minimum, maximum = body_bounds(body)
    extent = maximum - minimum
    winged = module.get("silhouetteProfile") == "winged"
    columns = 8
    rows = 5
    thickness = max(float(module["thicknessM"]), extent.z * 0.014)
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []

    for side_index, direction in enumerate((-1.0, 1.0)):
        start = len(vertices)
        side = "L" if direction > 0.0 else "R"
        upper_arm = rig.data.bones.get(f"upper_arm_{side}")
        if upper_arm is None:
            raise RuntimeError(f"Canonical pauldron anchor is missing: upper_arm_{side}")
        half_width = extent.x * (0.105 if winged else 0.080)
        half_depth = extent.y * 0.125
        crown = extent.z * (0.024 if winged else 0.020)
        anchor = upper_arm.head_local
        # The upper-arm head is the actual shoulder seam in the canonical
        # A-pose. The old fixture raised the plate by 6.4% of body height and
        # pushed it outward, which produced the detached wing seen in runtime.
        center_x = anchor.x + direction * half_width * (1.50 if winged else 1.90)
        center_y = anchor.y - extent.y * 0.055
        center_z = anchor.z + extent.z * 0.010
        for layer in (0, 1):
            for row in range(rows + 1):
                v = row / rows * 2.0 - 1.0
                for column in range(columns + 1):
                    u = column / columns * 2.0 - 1.0
                    x = center_x + direction * u * half_width
                    y = center_y + v * half_depth
                    outer = max(0.0, u)
                    flare = extent.z * 0.016 * outer * outer if winged else 0.0
                    arch = crown * max(0.0, 1.0 - 0.72 * u * u - 0.42 * v * v)
                    shoulder_slope = -extent.z * 0.012 * u
                    z = center_z + arch + flare + shoulder_slope - layer * thickness
                    vertices.append((x, y, z))
        stride = columns + 1
        layer_size = (rows + 1) * stride
        for layer in (0, 1):
            base = start + layer * layer_size
            for row in range(rows):
                for column in range(columns):
                    a = base + row * stride + column
                    quad = (a, a + 1, a + stride + 1, a + stride)
                    faces.append(quad if layer == 0 else tuple(reversed(quad)))
        top = start
        bottom = start + layer_size
        boundary = (
            [row * stride for row in range(rows + 1)]
            + [rows * stride + column for column in range(1, columns + 1)]
            + [row * stride + columns for row in range(rows - 1, -1, -1)]
            + [column for column in range(columns - 1, 0, -1)]
        )
        for index, current in enumerate(boundary):
            following = boundary[(index + 1) % len(boundary)]
            faces.append((top + current, top + following, bottom + following, bottom + current))

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for group in list(obj.vertex_groups):
        obj.vertex_groups.remove(group)
    groups = {
        bone: obj.vertex_groups.new(name=bone)
        for bone in ("shoulder_L", "upper_arm_L", "shoulder_R", "upper_arm_R")
        if rig.data.bones.get(bone)
    }
    for vertex in mesh.vertices:
        side = "L" if vertex.co.x >= 0.0 else "R"
        groups[f"shoulder_{side}"].add([vertex.index], 0.86, "REPLACE")
        groups[f"upper_arm_{side}"].add([vertex.index], 0.14, "REPLACE")
    assign_material(obj, material)
    bevel = obj.modifiers.new("pauldron_edge_rounding", "BEVEL")
    bevel.width = min(0.004, thickness * 0.32)
    bevel.segments = 2
    apply_modifier(obj, bevel)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    ensure_armature(obj, rig)
    return obj


def extract_surface_patch(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    name: str,
    slot: str,
    module: dict,
    material: bpy.types.Material,
) -> bpy.types.Object:
    body_min = min(vertex.co.z for vertex in body.data.vertices)
    body_max = max(vertex.co.z for vertex in body.data.vertices)
    height = body_max - body_min
    selected = []
    selected_bones = module["bones"]
    for polygon in body.data.polygons:
        vertices = [body.data.vertices[index] for index in polygon.vertices]
        if min(body_group_weight(body, vertex, "body") for vertex in vertices) < 0.5:
            continue
        center = sum((vertex.co for vertex in vertices), Vector()) / len(vertices)
        normalized_z = (center.z - body_min) / height
        if slot == "shoulders":
            # Shoulder-only weights exclude the connected upper-arm tongue
            # that previously survived voxel remeshing as a jagged metal flap.
            shoulder_score = sum(
                max(
                    body_group_weight(body, vertex, "shoulder_L"),
                    body_group_weight(body, vertex, "shoulder_R"),
                )
                for vertex in vertices
            ) / len(vertices)
            include = (
                shoulder_score >= 0.10
                and 0.725 <= normalized_z <= 0.84
                and 0.15 <= abs(center.x) <= 0.43
            )
        else:
            bone_score = sum(
                max(body_group_weight(body, vertex, bone) for bone in selected_bones)
                for vertex in vertices
            ) / len(vertices)
            include = bone_score >= 0.08 and 0.48 <= normalized_z <= 0.59 and abs(center.x) <= 0.34
        if include:
            selected.append(polygon)
    if not selected:
        raise RuntimeError(f"Surface selection produced no faces for {slot}")

    old_to_new: dict[int, int] = {}
    coordinates = []
    faces = []
    for polygon in selected:
        face = []
        for old_index in polygon.vertices:
            if old_index not in old_to_new:
                old_to_new[old_index] = len(coordinates)
                coordinates.append(tuple(body.data.vertices[old_index].co))
            face.append(old_to_new[old_index])
        faces.append(tuple(face))
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(coordinates, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    source_uv = body.data.uv_layers.active
    if source_uv:
        target_uv = mesh.uv_layers.new(name=source_uv.name)
        for new_polygon, old_polygon in zip(mesh.polygons, selected):
            for new_loop, old_loop in zip(new_polygon.loop_indices, old_polygon.loop_indices):
                target_uv.data[new_loop].uv = source_uv.data[old_loop].uv

    bone_names = {bone.name for bone in rig.data.bones}
    group_lookup = {}
    for old_index, new_index in old_to_new.items():
        source_vertex = body.data.vertices[old_index]
        for assignment in source_vertex.groups:
            source_group = body.vertex_groups[assignment.group]
            if source_group.name not in bone_names:
                continue
            target_group = group_lookup.get(source_group.name)
            if not target_group:
                target_group = obj.vertex_groups.new(name=source_group.name)
                group_lookup[source_group.name] = target_group
            target_group.add([new_index], assignment.weight, "REPLACE")
    layer_clearance = SURFACE_LAYER_CLEARANCE.get(slot, 0.0)
    for vertex in mesh.vertices:
        vertex.co += vertex.normal * (
            float(module["normalOffsetM"]) + layer_clearance
        )
    assign_material(obj, material)
    solidify = obj.modifiers.new("fitted_plate_thickness", "SOLIDIFY")
    solidify.thickness = float(module["thicknessM"])
    # Surface-derived plates already follow the naked-body shell. Build their
    # thickness away from that shell so the inner half cannot fall back into
    # the tunic or body after skinning.
    solidify.offset = 1.0
    solidify.use_rim = True
    apply_modifier(obj, solidify)
    bevel = obj.modifiers.new("fitted_plate_edge", "BEVEL")
    bevel.width = min(0.003, float(module["thicknessM"]) * 0.28)
    bevel.segments = 2
    apply_modifier(obj, bevel)
    # Keep the fitted, solidified MPFB shoulder surface. Voxel-remeshing this
    # narrow anatomical patch rounds it into two detached pods, especially on
    # short bodies; the source topology already provides the desired low,
    # body-following pauldron silhouette.
    ensure_armature(obj, rig)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def body_bounds(body: bpy.types.Object) -> tuple[Vector, Vector]:
    body_vertices = [
        vertex.co
        for vertex in body.data.vertices
        if body_group_weight(body, vertex, "body") >= 0.5
    ]
    return (
        Vector(tuple(min(vertex[index] for vertex in body_vertices) for index in range(3))),
        Vector(tuple(max(vertex[index] for vertex in body_vertices) for index in range(3))),
    )


def torso_depth(body: bpy.types.Object) -> tuple[float, float]:
    minimum, maximum = body_bounds(body)
    height = maximum.z - minimum.z
    torso = [
        vertex.co
        for vertex in body.data.vertices
        if body_group_weight(body, vertex, "body") >= 0.5
        and abs(vertex.co.x) <= 0.28
        and minimum.z + height * 0.40 <= vertex.co.z <= minimum.z + height * 0.78
    ]
    return min(vertex.y for vertex in torso), max(vertex.y for vertex in torso)


def body_surface_y(
    body: bpy.types.Object,
    x: float,
    z: float,
    side: str,
    search_radius: float = 0.050,
) -> float:
    """Sample the front/back body envelope near a panel vertex.

    Weighted panels are intentionally not shrink-wrapped down their full
    length: the sample supplies a collision envelope while the authored drape
    curve remains visible below the attachment area.
    """
    candidates = [
        vertex.co
        for vertex in body.data.vertices
        if body_group_weight(body, vertex, "body") >= 0.5
        and abs(vertex.co.x - x) <= search_radius
        and abs(vertex.co.z - z) <= search_radius
    ]
    if not candidates:
        candidates = [
            vertex.co
            for vertex in body.data.vertices
            if body_group_weight(body, vertex, "body") >= 0.5
            and abs(vertex.co.x - x) <= search_radius * 2.0
            and abs(vertex.co.z - z) <= search_radius * 2.0
        ]
    if not candidates:
        front_y, back_y = torso_depth(body)
        return back_y if side == "back" else front_y
    return max(vertex.y for vertex in candidates) if side == "back" else min(
        vertex.y for vertex in candidates
    )


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def panel_half_width(panel: str, t: float) -> float:
    """Return a torso-scaled, shaped half-width rather than an arm-span width."""
    if panel == "back":
        # Cape: pinned broadly at the shoulders, drawn in at the waist, then
        # opened slightly at the hem so the silhouette hangs instead of boxing.
        if t <= 0.42:
            return 0.240 + (0.225 - 0.240) * smoothstep(t / 0.42)
        return 0.225 + (0.310 - 0.225) * smoothstep((t - 0.42) / 0.58)
    # Tabard: tucked beneath the belt, then opened slightly at the hem so it
    # reads as hanging cloth rather than a narrow rectangular card.
    return 0.170 + (0.200 - 0.170) * smoothstep(t)


def add_panel_weights(
    obj: bpy.types.Object,
    rig: bpy.types.Object,
    rows: int,
    columns: int,
    panel: str,
) -> None:
    groups = {name: obj.vertex_groups.new(name=name) for name in (
        "shoulder_L", "shoulder_R", "upper_chest", "spine", "hips", "thigh_L", "thigh_R"
    ) if rig.data.bones.get(name)}
    for row in range(rows + 1):
        t = row / rows
        for column in range(columns + 1):
            index = row * (columns + 1) + column
            x = column / columns * 2.0 - 1.0
            if panel == "back":
                if t < 0.12:
                    shoulder_blend = (
                        0.65
                        * smoothstep((abs(x) - 0.30) / 0.45)
                        * (1.0 - smoothstep(t / 0.12))
                    )
                    shoulder = "shoulder_L" if x >= 0 else "shoulder_R"
                    weights = {
                        "upper_chest": 1.0 - shoulder_blend,
                        shoulder: shoulder_blend,
                    }
                elif t < 0.48:
                    blend = (t - 0.12) / 0.36
                    weights = {"upper_chest": 1.0 - blend, "spine": blend}
                elif t < 0.58:
                    blend = (t - 0.48) / 0.10
                    weights = {"spine": 1.0 - blend, "hips": blend}
                else:
                    blend = min(1.0, (t - 0.58) / 0.42)
                    thigh = "thigh_L" if x >= 0 else "thigh_R"
                    weights = {
                        "hips": 1.0 - blend * 0.30,
                        "spine": blend * 0.20,
                        thigh: blend * 0.10,
                    }
            else:
                blend = min(1.0, t / 0.74)
                thigh = "thigh_L" if x >= 0 else "thigh_R"
                weights = {"hips": 1.0 - blend * 0.88, thigh: blend * 0.88}
            total = sum(weights.values())
            for name, weight in weights.items():
                groups[name].add([index], weight / total, "REPLACE")


def create_weighted_panel(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    name: str,
    panel: str,
    material: bpy.types.Material,
) -> bpy.types.Object:
    minimum, maximum = body_bounds(body)
    height = maximum.z - minimum.z
    rows = 32 if panel == "back" else 30
    columns = 28 if panel == "back" else 20
    if panel == "back":
        top = minimum.z + height * 0.790
        bottom = minimum.z + height * 0.310
        side = "back"
        clearance = 0.012
    else:
        top = minimum.z + height * 0.552
        bottom = minimum.z + height * 0.300
        side = "front"
        clearance = 0.030

    anchor_y = body_surface_y(body, 0.0, top, side)
    vertices = []
    faces = []
    for row in range(rows + 1):
        t = row / rows
        width = panel_half_width(panel, t)
        for column in range(columns + 1):
            u = column / columns
            across = u * 2.0 - 1.0
            if panel == "back":
                edge_flutter = (
                    0.010
                    * math.sin(
                        2.5 * math.pi * t + (0.0 if across < 0.0 else 0.7)
                    )
                    * abs(across) ** 8
                    * smoothstep(t / 0.25)
                )
                x = (
                    across * width
                    + math.copysign(1.0, across) * edge_flutter
                )
            else:
                x = across * width
            surface_y = body_surface_y(body, x, top + (bottom - top) * t, side)
            if panel == "back":
                # Author the hanging shape below the collar instead of
                # clamping every row to noisy body samples. The outer sweep,
                # center bow, and persistent folds give the cape real depth.
                attachment = smoothstep(t / 0.15)
                belt_window = (
                    smoothstep((t - 0.38) / 0.10)
                    * (1.0 - smoothstep((t - 0.60) / 0.10))
                )
                base_y = (
                    anchor_y
                    + 0.008
                    + 0.112 * smoothstep(t)
                    + 0.040 * belt_window
                )
                bow = 0.025 * (1.0 - across * across) * smoothstep(t * 2.0)
                amplitude = (
                    0.032
                    * smoothstep(t / 0.16)
                    * (0.65 + 0.35 * math.sin(math.pi * t))
                )
                fold = amplitude * math.cos(3.0 * math.pi * across + 0.55 * t)
                y = base_y + bow + fold
                y = max(y, surface_y + clearance * (1.0 - attachment))

                collar_profile = (
                    0.020
                    * math.exp(-((abs(across) - 0.62) / 0.18) ** 2)
                    - 0.040 * (1.0 - abs(across)) ** 2
                    - 0.030 * smoothstep((abs(across) - 0.78) / 0.22)
                ) * (1.0 - smoothstep(t / 0.12))
                hem_envelope = smoothstep((t - 0.80) / 0.20)
                hem = hem_envelope * (
                    0.025 * abs(across) ** 1.8
                    + 0.018
                    * (
                        0.5
                        + 0.5
                        * math.cos(3.0 * math.pi * across + 0.55)
                    )
                )
                z = top + (bottom - top) * t + collar_profile + hem
            else:
                fold_envelope = math.sin(math.pi * smoothstep(t))
                hanging_y = anchor_y - clearance - 0.030 * smoothstep(t)
                collision_y = surface_y - clearance
                # Pleats project away from the wearer only, so a trough cannot
                # undo the tabard's collision clearance at the tunic or belt.
                fold = (
                    0.012
                    * (0.5 + 0.5 * math.cos(across * math.pi * 4.0))
                    * fold_envelope
                )
                y = min(collision_y, hanging_y) - fold
                # A shallow central notch reads as a cloth hem rather than a
                # rectangular card and leaves more room for extreme leg poses.
                notch = 0.035 * (1.0 - abs(across)) ** 1.7 * smoothstep((t - 0.84) / 0.16)
                z = top + (bottom - top) * t + notch
            vertices.append((x, y, z))
    stride = columns + 1
    for row in range(rows):
        for column in range(columns):
            a = row * stride + column
            faces.append((a, a + 1, a + stride + 1, a + stride))
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    uv = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            row, column = divmod(vertex_index, stride)
            uv.data[loop_index].uv = (column / columns, 1.0 - row / rows)
    add_panel_weights(obj, rig, rows, columns, panel)
    assign_material(obj, material)
    solidify = obj.modifiers.new("cloth_thickness", "SOLIDIFY")
    solidify.thickness = 0.002 if panel == "back" else 0.0035
    solidify.offset = 1.0 if panel == "back" else -1.0
    solidify.use_rim = True
    apply_modifier(obj, solidify)
    bevel = obj.modifiers.new("cloth_edge_softening", "BEVEL")
    bevel.width = 0.0005 if panel == "back" else 0.0015
    bevel.segments = 2
    apply_modifier(obj, bevel)
    ensure_armature(obj, rig)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def create_curved_belt(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    name: str,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Create a closed, torso-following belt instead of a flat surface slice."""
    minimum, maximum = body_bounds(body)
    height = maximum.z - minimum.z
    center_z = minimum.z + height * 0.535
    section = [
        vertex.co
        for vertex in body.data.vertices
        if body_group_weight(body, vertex, "body") >= 0.5
        and abs(vertex.co.z - center_z) <= 0.032
        and abs(vertex.co.x) <= 0.32
    ]
    if not section:
        raise RuntimeError("Could not sample the accepted body waist for belt fitting")
    x_radius = max(abs(vertex.x) for vertex in section) + 0.030
    front_y = min(vertex.y for vertex in section)
    back_y = max(vertex.y for vertex in section)
    center_y = (front_y + back_y) * 0.5
    y_radius = (back_y - front_y) * 0.5 + 0.042
    band_height = height * 0.043
    segments = 56
    rows = 4
    vertices = []
    faces = []
    for row in range(rows + 1):
        v = row / rows
        z = center_z + band_height * (0.5 - v)
        # The rounded middle reads like a leather strap while the upper/lower
        # edges remain close enough to cover the chest/tabard seam.
        crown = math.sin(v * math.pi) * 0.004
        for segment in range(segments):
            angle = segment / segments * math.tau
            vertices.append((
                math.sin(angle) * (x_radius + crown),
                center_y + math.cos(angle) * (y_radius + crown),
                z,
            ))
    for row in range(rows):
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            a = row * segments + segment
            b = row * segments + next_segment
            c = (row + 1) * segments + next_segment
            d = (row + 1) * segments + segment
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    uv = mesh.uv_layers.new(name="UVMap")
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            row, segment = divmod(vertex_index, segments)
            uv.data[loop_index].uv = (segment / segments, 1.0 - row / rows)
    hips = obj.vertex_groups.new(name="hips")
    spine = obj.vertex_groups.new(name="spine")
    for vertex in mesh.vertices:
        hips.add([vertex.index], 0.68, "REPLACE")
        spine.add([vertex.index], 0.32, "REPLACE")
    assign_material(obj, material)
    solidify = obj.modifiers.new("belt_thickness", "SOLIDIFY")
    solidify.thickness = 0.009
    solidify.offset = 0.0
    solidify.use_rim = True
    apply_modifier(obj, solidify)
    bevel = obj.modifiers.new("belt_edge_rounding", "BEVEL")
    bevel.width = 0.002
    bevel.segments = 2
    apply_modifier(obj, bevel)
    ensure_armature(obj, rig)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def fitted_asset(
    body: bpy.types.Object,
    rig: bpy.types.Object,
    name: str,
    asset_name: str,
    material: bpy.types.Material,
    slot: str,
    material_style: str,
) -> tuple[bpy.types.Object, Path]:
    source = Path(LocationService.get_user_data("clothes")) / asset_name / f"{asset_name}.mhclo"
    if not source.is_file():
        raise FileNotFoundError(f"Required free MPFB armor asset is missing: {source}")
    obj = HumanService.add_mhclo_asset(
        str(source),
        body,
        asset_type="clothes",
        subdiv_levels=0,
        material_type="GAMEENGINE",
        set_up_rigging=True,
        interpolate_weights=True,
        import_subrig=False,
        import_weights=True,
    )
    obj.name = name
    canonicalize_groups(obj)
    ensure_armature(obj, rig)
    style_fixture_materials(obj, material, material_style)
    apply_shape_key_mix(obj)
    trim_fixture_to_slot(obj, body, slot)
    offset_vertices_along_normals(obj, FITTED_LAYER_CLEARANCE.get(slot, 0.0))
    if slot == "chest":
        # Gauntlets own the forearm seam. Keep roughly 20 mm of hidden tunic
        # underlap, then remove the distal sleeve that previously crossed it.
        trim_distal_underlap(obj, rig, "forearm", "hand", 0.245)
    elif slot == "legs":
        # Boots own the shin seam with the same short hidden underlap.
        trim_distal_underlap(obj, rig, "shin", "foot", 0.380)
    close_open_surface(obj)
    return obj, source


def attach_review_weapon(weapon_path: Path, rig: bpy.types.Object) -> list[bpy.types.Object]:
    if not weapon_path.is_file():
        raise FileNotFoundError(f"Draft review weapon is missing: {weapon_path}")
    existing = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(weapon_path))
    imported = [obj for obj in bpy.context.scene.objects if obj not in existing]
    if not imported:
        raise RuntimeError("Draft review weapon GLB imported without objects")
    root = next((obj for obj in imported if obj.name.startswith("battle_prelate_hammer_root")), None)
    if not root:
        roots = [obj for obj in imported if obj.parent not in imported]
        if len(roots) != 1:
            raise RuntimeError("Draft review weapon must have one attachable root")
        root = roots[0]
    socket = bpy.data.objects.get("socket_hand_R")
    if not socket:
        raise RuntimeError("Accepted body source is missing socket_hand_R")
    root.parent = socket
    root.matrix_parent_inverse = Matrix.Identity(4)
    root.location = (0.0, 0.0, 0.0)
    root.rotation_euler = (0.0, 0.0, 0.0)
    root.scale = (1.0, 1.0, 1.0)
    for obj in imported:
        obj["lifecycleStatus"] = "draft"
        obj["reviewStatus"] = "pending"
        obj["promotionEligible"] = False
        obj["targetSocket"] = "socket_hand_R"
        obj["reviewSourceSha256"] = sha256(weapon_path)
    return imported


def set_metadata(
    obj: bpy.types.Object,
    asset_id: str,
    family: str,
    variant: str,
    slot: str,
    recipe: dict,
) -> None:
    metadata = {
        "assetId": asset_id,
        "assetCategory": "armor",
        "armorSlot": slot,
        "armorSetId": recipe["setId"],
        "bodyFamily": family,
        "bodyVariant": variant,
        "skeletonId": "humanoid_game_v2",
        "bindPoseId": "a_pose_v2",
        "generatorKind": "mpfbFittedModularArmor",
        "generatorVersion": GENERATOR_VERSION,
        "license": "CC0-1.0",
        "lifecycleStatus": "draft",
        "reviewStatus": "pending",
    }
    for key, value in metadata.items():
        obj[key] = value
    obj["layerOrder"] = SLOT_LAYER_ORDER[slot]


def export_module(output: Path, rig: bpy.types.Object, module: bpy.types.Object) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    module.select_set(True)
    bpy.context.view_layer.objects.active = module
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        use_selection=True,
        export_animations=False,
        export_skins=True,
        export_morph=False,
        export_extras=True,
        export_yup=True,
        export_apply=False,
        export_draco_mesh_compression_enable=False,
    )
    bpy.ops.object.select_all(action="DESELECT")


def export_equipped_review(
    output: Path,
    objects: list[bpy.types.Object],
) -> None:
    """Export a single draft-only runtime review GLB with all nine modules."""
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    options = {
        "filepath": str(output),
        "export_format": "GLB",
        "use_selection": True,
        "export_animations": True,
        "export_skins": True,
        "export_morph": True,
        "export_extras": True,
        "export_yup": True,
        "export_apply": False,
        "export_draco_mesh_compression_enable": False,
    }
    available = {prop.identifier for prop in bpy.ops.export_scene.gltf.get_rna_type().properties}
    if "export_animation_mode" in available:
        options["export_animation_mode"] = "ACTIONS"
    if "export_nla_strips" in available:
        options["export_nla_strips"] = False
    if "export_anim_single_armature" in available:
        options["export_anim_single_armature"] = True
    bpy.ops.export_scene.gltf(**options)
    bpy.ops.object.select_all(action="DESELECT")


def embedded_animation_names(output: Path) -> list[str]:
    payload = output.read_bytes()
    if payload[:4] != b"glTF" or int.from_bytes(payload[4:8], "little") != 2:
        raise RuntimeError(f"Not a GLB 2.0 file: {output}")
    offset = 12
    while offset + 8 <= len(payload):
        chunk_length = int.from_bytes(payload[offset : offset + 4], "little")
        chunk_type = payload[offset + 4 : offset + 8]
        chunk = payload[offset + 8 : offset + 8 + chunk_length]
        if chunk_type == b"JSON":
            document = json.loads(chunk.rstrip(b" \t\r\n\x00").decode("utf-8"))
            return sorted(animation.get("name", "") for animation in document.get("animations", []))
        offset += 8 + chunk_length
    return []


def render_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def aim(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_reviews(meshes: list[bpy.types.Object], review_dir: Path) -> list[dict]:
    review_dir.mkdir(parents=True, exist_ok=True)
    for obj in list(bpy.context.scene.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    minimum, maximum = render_bounds(meshes)
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    width = maximum.x - minimum.x
    distance = max(height, width) * 2.2
    camera_data = bpy.data.cameras.new("armor_review_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(height * 1.12, width * 1.18)
    camera = bpy.data.objects.new("armor_review_camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    for name, location, energy, size in (
        ("armor_review_key", (-2.6, -3.4, maximum.z + 1.2), 1050, 2.2),
        ("armor_review_fill", (2.8, -1.5, center.z + 0.4), 700, 2.6),
        ("armor_review_rim", (0.6, 3.2, maximum.z + 0.8), 900, 2.0),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        bpy.context.scene.collection.objects.link(light)
        aim(light, center)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("armor_review_world")
    scene.world.color = (0.025, 0.03, 0.04)
    views = {
        "front": Vector((center.x, minimum.y - distance, center.z)),
        "side": Vector((maximum.x + distance, center.y, center.z)),
        "back": Vector((center.x, maximum.y + distance, center.z)),
        "isometric": Vector((maximum.x + distance * 0.72, minimum.y - distance * 0.72, center.z + height * 0.10)),
    }
    rendered = []
    for name, position in views.items():
        camera.location = position
        aim(camera, center)
        output = review_dir / f"{name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        rendered.append({"view": name, "path": str(output), "sha256": sha256(output)})
    return rendered


def render_stress_reviews(
    rig: bpy.types.Object,
    meshes: list[bpy.types.Object],
    review_dir: Path,
) -> list[dict]:
    """Render shared QA deformation poses without creating animation approval."""
    rotations = {
        "upper_arm_L": (math.radians(-28), math.radians(12), math.radians(-62)),
        "upper_arm_R": (math.radians(22), math.radians(-8), math.radians(58)),
        "forearm_L": (math.radians(-72), 0.0, math.radians(-8)),
        "forearm_R": (math.radians(-54), 0.0, math.radians(10)),
        "thigh_L": (math.radians(38), 0.0, math.radians(-12)),
        "shin_L": (math.radians(-58), 0.0, 0.0),
        "thigh_R": (math.radians(-18), 0.0, math.radians(10)),
        "spine": (math.radians(10), 0.0, math.radians(12)),
    }
    saved = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
    try:
        for bone_name, rotation in rotations.items():
            bone = rig.pose.bones.get(bone_name)
            if not bone:
                raise RuntimeError(f"Canonical stress pose requires missing bone: {bone_name}")
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = rotation
        bpy.context.view_layer.update()
        rendered = render_reviews(meshes, review_dir)
        return [{**row, "pose": "shared_deformation_stress", "animationApprovalEligible": False} for row in rendered]
    finally:
        for bone_name, matrix_basis in saved.items():
            rig.pose.bones[bone_name].matrix_basis = matrix_basis
        bpy.context.view_layer.update()


def render_roundtrip_review(
    combined: Path,
    review_dir: Path,
    expected_clips: list[str],
) -> dict:
    """Re-import the emitted GLB and render that payload, not the source scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(combined))
    imported_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not imported_meshes:
        raise RuntimeError("Equipped review GLB re-imported without any meshes")
    invalid_bounds = [
        obj.name
        for obj in imported_meshes
        if max(obj.dimensions) <= 1e-6 or not all(math.isfinite(value) for value in obj.dimensions)
    ]
    imported_rig = next((obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"), None)
    idle_action = bpy.data.actions.get("idle")
    if imported_rig and idle_action:
        imported_rig.animation_data_create()
        imported_rig.animation_data.action = idle_action
        first, last = idle_action.frame_range
        bpy.context.scene.frame_set(round((first + last) * 0.5))
        bpy.context.view_layer.update()
    previews = render_reviews(imported_meshes, review_dir)
    clips = embedded_animation_names(combined)
    materials = {
        material.name
        for obj in imported_meshes
        for material in obj.data.materials
        if material
    }
    referenced_images = {
        node.image
        for material in bpy.data.materials
        if material.use_nodes and material.node_tree
        for node in material.node_tree.nodes
        if node.type == "TEX_IMAGE" and node.image
    }
    material_images = []
    for image in sorted(referenced_images, key=lambda image: image.name):
        pixel_count = max(1, len(image.pixels) // 4)
        offsets = (0, (pixel_count // 2) * 4, (pixel_count - 1) * 4)
        samples = [list(image.pixels[offset : offset + 4]) for offset in offsets]
        populated = any(any(channel > 0.0001 for channel in sample[:3]) for sample in samples)
        material_images.append({
            "name": image.name,
            "colorspace": image.colorspace_settings.name,
            "samples": samples,
            "populated": populated,
            "sourceKind": "generated_palette" if "_draft_pbr_" in image.name else "authored_fixture",
        })
    authored_fixture_images = [
        image for image in material_images if image["sourceKind"] == "authored_fixture"
    ]
    generated_palette_images = [
        image for image in material_images if image["sourceKind"] == "generated_palette"
    ]
    # Transparent eyebrow cards and intentionally black metal masks can sample
    # to zero at all three probe points. Require every generated PBR channel
    # and at least one visibly populated authored texture instead of rejecting
    # valid sparse/black fixture maps.
    armor_images_populated = (
        len(generated_palette_images) >= 9
        and all(image["populated"] for image in generated_palette_images)
        and any(image["populated"] for image in authored_fixture_images)
    )
    technical_passed = (
        not invalid_bounds
        and len(imported_meshes) >= 13
        and all(Path(row["path"]).is_file() for row in previews)
        and sorted(expected_clips) == clips
        and bool(materials)
        and armor_images_populated
    )
    report = {
        "schemaVersion": 1,
        "assetId": f"chr.review.{combined.stem}",
        "model": combined.name,
        "modelSha256": sha256(combined),
        "fileSizeBytes": combined.stat().st_size,
        "lifecycleStatus": "draft",
        "reviewStatus": "pending_human_visual_review",
        "promotionEligible": False,
        "reimportedMeshCount": len(imported_meshes),
        "reimportedMaterialCount": len(materials),
        "invalidBounds": invalid_bounds,
        "animationClips": clips,
        "requiredAnimationClips": sorted(expected_clips),
        "armorMaterialImages": material_images,
        "armorMaterialImagesPopulated": armor_images_populated,
        "authoredFixtureMaterialImageCount": len(authored_fixture_images),
        "previews": previews,
        "technicalRoundTripPassed": technical_passed,
        "visualApprovalPassed": False,
        "blockingReasons": [
            "human_roundtrip_visual_approval_missing",
            "stress_pose_review_missing",
        ],
    }
    combined.with_suffix(".qc.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return report


def module_report(
    output: Path,
    obj: bpy.types.Object,
    asset_id: str,
    family: str,
    variant: str,
    slot: str,
    previews: list[dict],
    source: Path | None,
    source_pack: str | None,
    pack_recipe: dict,
    max_before: int,
    unweighted: int,
) -> dict:
    triangles = evaluated_triangles(obj)
    manifold = non_manifold_edges(obj)
    degenerate = degenerate_faces(obj)
    checks = {
        "modelExists": output.is_file(),
        "triangleBudget": triangles <= module_triangle_limit(slot),
        "drawCallBudget": len(obj.material_slots) <= 2,
        "fourInfluenceLimitApplied": max_before >= 0,
        "allVerticesWeighted": unweighted == 0,
        "manifold": manifold == 0,
        "noDegenerateFaces": degenerate == 0,
        "reviewViewsPresent": len(previews) == 4,
        "pbrChannelsPresent": True,
    }
    report = {
        "schemaVersion": 1,
        "assetId": asset_id,
        "model": output.name,
        "modelSha256": sha256(output),
        "fileSizeBytes": output.stat().st_size,
        "category": "armor",
        "slot": slot,
        "bodyFamily": family,
        "bodyVariant": variant,
        "skeletonId": "humanoid_game_v2",
        "bindPoseId": "a_pose_v2",
        "lifecycleStatus": "draft",
        "reviewStatus": "pending",
        "promotionEligible": False,
        "totalTriangles": triangles,
        "drawCalls": len(obj.material_slots),
        "maxInfluencesBeforeLimit": max_before,
        "maxInfluencesObserved": influence_counts(obj, {bone.name for bone in bpy.data.objects["humanoid_game_v2"].data.bones})[0],
        "unweightedVertices": unweighted,
        "nonManifoldEdges": manifold,
        "degenerateFaces": degenerate,
        "pbrChannels": ["baseColor", "normal", "roughness", "metallic", "occlusion"],
        "maxTextureDimension": 128,
        "previewImages": [row["path"] for row in previews],
        "previews": previews,
        "provenance": {
            "provider": "local_mpfb",
            "generator": "generate_mpfb_modular_armor.py",
            "license": "CC0-1.0",
            **(
                {
                    "assetSource": str(source),
                    "assetSourceSha256": sha256(source),
                    "sourcePack": source_pack,
                    "sourcePackSha256": pack_recipe["sourcePacks"][source_pack]["sha256"],
                    "sourceUrl": pack_recipe["sourcePacks"][source_pack]["sourceUrl"],
                }
                if source and source_pack
                else {"assetSource": "War-js topology-derived draft"}
            ),
        },
        "checks": checks,
        "qcPassed": all(checks.values()),
    }
    output.with_suffix(".qc.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return report


def main() -> None:
    args = parse_args()
    pack_recipe, recipe = load_recipe(args.recipe_file, args.family, args.variant, args.set_id)
    source_blend = Path(args.source_blend).resolve()
    if not source_blend.is_file():
        raise FileNotFoundError(f"Accepted body source blend is missing: {source_blend}")
    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    body_name = f"body_{args.family}_{args.variant}"
    body = bpy.data.objects.get(body_name)
    rig = bpy.data.objects.get("humanoid_game_v2")
    if not body or body.type != "MESH" or not rig or rig.type != "ARMATURE":
        raise RuntimeError("Source blend does not contain the expected accepted MPFB body and canonical rig")
    if body.get("bodyFamily") != args.family or body.get("bodyVariant") != args.variant:
        raise RuntimeError("Source blend compatibility metadata does not match the requested armor variant")
    output_dir = Path(args.output_dir).resolve()
    review_dir = Path(args.review_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    bone_names = {bone.name for bone in rig.data.bones}
    modules: dict[str, bpy.types.Object] = {}
    sources: dict[str, tuple[Path | None, str | None]] = {}
    for slot in ARMOR_SLOTS:
        module = recipe["modules"][slot]
        if slot == "head" and (
            module.get("faceCoverage") != "open"
            or module.get("faceOcclusionAllowed") is not False
            or module.get("asset") == "culturalibre_skull_helmet"
        ):
            raise RuntimeError(
                f"{recipe['setId']} head fixture is not certified open-face: {module.get('asset')}"
            )
        asset_id = f"arm.{args.family}.{recipe['setId']}.{slot}.{args.variant}"
        object_name = asset_id.replace(".", "_")
        material = pbr_material(args.family, module["materialStyle"], recipe["palette"][module["materialStyle"]])
        existing_module = bpy.data.objects.get(object_name) if args.resume_existing else None
        if existing_module:
            obj = existing_module
            source = (
                Path(LocationService.get_user_data("clothes"))
                / module["asset"]
                / f"{module['asset']}.mhclo"
                if module["kind"] in {"mpfbAsset", "mpfbSegment"}
                else None
            )
            sources[slot] = (source, module.get("pack"))
        elif args.resume_existing:
            raise RuntimeError(f"Resume blend is missing expected module: {object_name}")
        elif module["kind"] in {"mpfbAsset", "mpfbSegment"}:
            obj, source = fitted_asset(
                body,
                rig,
                object_name,
                module["asset"],
                material,
                slot,
                module["materialStyle"],
            )
            sources[slot] = (source, module["pack"])
        elif module["kind"] == "bodySurface":
            if slot == "waist":
                obj = create_curved_belt(body, rig, object_name, material)
            elif slot == "shoulders":
                obj = create_curved_pauldron_pair(body, rig, object_name, module, material)
            else:
                obj = extract_surface_patch(body, rig, object_name, slot, module, material)
            sources[slot] = (None, None)
        elif module["kind"] == "weightedPanel":
            obj = create_weighted_panel(body, rig, object_name, module["panel"], material)
            sources[slot] = (None, None)
        else:
            raise RuntimeError(f"Unsupported armor module kind: {module['kind']}")
        close_open_surface(obj)
        if slot == "shoulders":
            cleanup_closed_mesh(obj)
        if slot == "shoulders":
            shoulder_triangles = evaluated_triangles(obj)
            if shoulder_triangles > MODULE_TRIANGLE_LIMIT:
                raise RuntimeError(
                    f"Rounded shoulder shell has {shoulder_triangles} triangles, "
                    f"above the hard {MODULE_TRIANGLE_LIMIT} module budget; increase "
                    "its voxel size instead of collapse-decimating it"
                )
        else:
            enforce_triangle_budget(obj)
        # Decimation of a complex authored wearable can expose a boundary.
        # Seal that boundary after the budget pass while there is still room
        # under the hard per-slot limit.
        if slot == "shoulders":
            # The voxel shell is already volumetric. Cap the few boundaries a
            # decimation may expose instead of solidifying the whole shell a
            # second time, which would create a nested non-manifold skin.
            cleanup_closed_mesh(obj)
        else:
            close_open_surface(obj)
        if non_manifold_edges(obj) > 0:
            if slot == "head":
                manifold_rigid_headpiece(obj, material)
            else:
                manifold_skinned_wearable(obj, rig, material)
        apply_shape_key_mix(obj)
        if slot != "shoulders":
            enforce_body_clearance(obj, body, body_clearance_for_slot(slot))
        canonicalize_groups(obj)
        ensure_armature(obj, rig)
        max_before, unweighted = limit_influences(obj, bone_names, 4)
        if unweighted:
            raise RuntimeError(f"{slot} has {unweighted} unweighted vertices after MPFB fitting")
        remaining_non_manifold = non_manifold_edges(obj)
        if remaining_non_manifold:
            raise RuntimeError(
                f"{slot} remains non-manifold after repair: {remaining_non_manifold} edges"
            )
        set_metadata(obj, asset_id, args.family, args.variant, slot, recipe)
        modules[slot] = obj
        obj["maxInfluencesBeforeLimit"] = max_before

    # Finalize the body before the review renders and exports, then repeat the
    # surface projection against that exact runtime mesh. MPFB's evaluated
    # authoring body still contains masked helper topology; using it as the
    # final collision surface can leave cuffs inside the stripped hand mesh.
    runtime_body_finalization = bake_targets_and_strip_helpers(body)
    for slot, obj in modules.items():
        if slot != "shoulders":
            enforce_body_clearance(obj, body, body_clearance_for_slot(slot))
        # Nearest-surface projection can collapse a tiny source triangle when
        # two vertices converge on the same cuff or helmet contour. Remove the
        # resulting zero-area face after projection; the 15 mm clearance margin
        # is intentionally much larger than the weld tolerance.
        cleanup_closed_mesh(obj)
        if non_manifold_edges(obj):
            if slot == "head":
                # Rebuild the occupied helmet volume and restore rigid weights.
                manifold_rigid_headpiece(obj, obj.active_material)
            else:
                manifold_skinned_wearable(obj, rig, obj.active_material)
            if slot != "shoulders":
                enforce_body_clearance(obj, body, body_clearance_for_slot(slot))
            cleanup_closed_mesh(obj)
        if non_manifold_edges(obj) or degenerate_faces(obj):
            raise RuntimeError(
                f"{slot} failed final runtime topology repair: "
                f"{non_manifold_edges(obj)} non-manifold edges, "
                f"{degenerate_faces(obj)} degenerate faces"
            )
        triangles_before_final_budget = evaluated_triangles(obj)
        # Final projection can add a large clean cap to fixture-derived capes.
        # Reduce only to the hard per-module ceiling here; forcing every cape
        # down to the 6.5k soft target damages its closed topology.
        slot_limit = module_triangle_limit(slot)
        # Helmet voxel repair can leave a dense but valid shell whose collapse
        # modifier does not hit an exact ratio. Give rigid headpieces generous
        # headroom instead of aiming one thousand triangles below the hard cap;
        # the visible silhouette is already preserved by the voxel pass.
        final_budget_target = (
            min(MODULE_TRIANGLE_TARGET + 1500, slot_limit - 4000)
            if slot == "head"
            else slot_limit - 1000
        )
        final_budget_applied = enforce_triangle_budget(obj, final_budget_target)
        if final_budget_applied:
            cleanup_closed_mesh(obj)
            if non_manifold_edges(obj):
                patch_small_non_manifold_region(obj)
                cleanup_closed_mesh(obj)
        if any(len(polygon.vertices) > 3 for polygon in obj.data.polygons):
            triangulate_faces(obj)
            if non_manifold_edges(obj):
                patch_small_non_manifold_region(obj)
        final_max_before, final_unweighted = limit_influences(obj, bone_names, 4)
        obj["maxInfluencesBeforeLimit"] = max(
            int(obj.get("maxInfluencesBeforeLimit", 0)), final_max_before
        )
        if final_unweighted:
            raise RuntimeError(f"{slot} has {final_unweighted} unweighted vertices after final repair")
        if evaluated_triangles(obj) > slot_limit:
            raise RuntimeError(
                f"{slot} exceeds the final {slot_limit}-triangle module budget"
            )
        if non_manifold_edges(obj) or degenerate_faces(obj):
            raise RuntimeError(
                f"{slot} became invalid during final triangle budgeting: "
                f"{non_manifold_edges(obj)} non-manifold edges, "
                f"{degenerate_faces(obj)} degenerate faces; "
                f"trianglesBefore={triangles_before_final_budget}, "
                f"trianglesAfter={evaluated_triangles(obj)}, "
                f"budgetApplied={final_budget_applied}"
            )

    runtime_body_meshes = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and (obj == body or obj.name.startswith(body_name + ".") or obj.get("bodyAccessory"))
    ]
    runtime_body_materials = prepare_runtime_materials(runtime_body_meshes)
    core_body_materials = [
        row for row in runtime_body_materials if not row["mesh"].startswith("grooming_")
    ]
    if not core_body_materials or any(row["alphaMode"] != "OPAQUE" for row in core_body_materials):
        raise RuntimeError("Equipped export body materials were not normalized to opaque runtime materials")

    weapon_path = Path(args.weapon_glb).resolve() if args.weapon_glb else None
    existing_weapon_objects = [
        obj for obj in bpy.context.scene.objects if obj.get("targetSocket") == "socket_hand_R"
    ] if args.resume_existing else []
    weapon_objects = (
        existing_weapon_objects
        if existing_weapon_objects
        else attach_review_weapon(weapon_path, rig) if weapon_path else []
    )
    preview_meshes = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and (
            obj == body
            or obj in modules.values()
            or obj.name.startswith(body_name + ".")
            or (obj.get("bodyAccessory") and obj.get("groomingCategory") != "hair")
            or obj in weapon_objects
        )
    ]
    previews = render_reviews(preview_meshes, review_dir)
    stress_previews = render_stress_reviews(rig, preview_meshes, review_dir / "stress")
    reports = []
    for slot, obj in modules.items():
        asset_id = obj["assetId"]
        output = output_dir / f"{asset_id.replace('.', '_')}.glb"
        set_metadata(rig, asset_id, args.family, args.variant, slot, recipe)
        export_module(output, rig, obj)
        source, source_pack = sources[slot]
        _max_after, unweighted = influence_counts(obj, bone_names)
        reports.append(module_report(
            output,
            obj,
            asset_id,
            args.family,
            args.variant,
            slot,
            previews,
            source,
            source_pack,
            pack_recipe,
            int(obj["maxInfluencesBeforeLimit"]),
            unweighted,
        ))

    body_triangles = sum(evaluated_triangles(obj) for obj in runtime_body_meshes)
    body_draw_calls = sum(max(1, len(obj.material_slots)) for obj in runtime_body_meshes)
    armor_triangles = sum(report["totalTriangles"] for report in reports)
    combined_name = f"{recipe['setId']}_{args.variant}_equipped_review.glb"
    combined_output = output_dir.parent / combined_name
    sockets = [obj for obj in bpy.context.scene.objects if obj.type == "EMPTY" and obj.name.startswith("socket_")]
    combined_objects = [rig, *preview_meshes, *sockets, *[obj for obj in weapon_objects if obj not in preview_meshes]]
    rig["assetId"] = f"chr.{args.family}.{recipe['setId']}.{args.variant}.equipped_review"
    rig["assetCategory"] = "characterReview"
    rig["lifecycleStatus"] = "draft"
    rig["reviewStatus"] = "pending"
    rig["promotionEligible"] = False
    export_equipped_review(combined_output, combined_objects)
    candidate = {
        "schemaVersion": 1,
        "setId": recipe["setId"],
        "displayName": recipe["displayName"],
        "bodyFamily": args.family,
        "bodyVariant": args.variant,
        "bodySourceBlend": str(source_blend),
        "skeletonId": "humanoid_game_v2",
        "bindPoseId": "a_pose_v2",
        "generatorKind": "mpfbFittedModularArmor",
        "generatorVersion": GENERATOR_VERSION,
        "runtimeBodyFinalization": runtime_body_finalization,
        "equippedFaceIntegrity": {
            "bodyMeshes": [
                obj.name for obj in runtime_body_meshes if not obj.get("bodyAccessory")
            ],
            "groomingMeshes": [
                obj.name for obj in runtime_body_meshes if obj.get("bodyAccessory")
            ],
            "bodyVerticesAfter": runtime_body_finalization["bodyVerticesAfter"],
            "materials": runtime_body_materials,
            "opaqueMaterials": all(row["alphaMode"] == "OPAQUE" for row in core_body_materials),
            "openFaceHeadFixture": recipe["modules"]["head"].get("faceCoverage") == "open",
            "passed": all(row["alphaMode"] == "OPAQUE" for row in core_body_materials)
            and recipe["modules"]["head"].get("faceCoverage") == "open",
        },
        "currencyCost": 0,
        "equippedReviewModel": {
            "path": str(combined_output),
            "sha256": sha256(combined_output),
            "weaponSource": str(weapon_path) if weapon_path else None,
            "weaponSourceSha256": sha256(weapon_path) if weapon_path else None,
        },
        "moduleCount": len(reports),
        "modules": reports,
        "equippedBudget": {
            "bodyTriangles": body_triangles,
            "armorTriangles": armor_triangles,
            "totalTriangles": body_triangles + armor_triangles,
            "maxTriangles": EQUIPPED_TRIANGLE_LIMIT,
            "drawCalls": body_draw_calls + sum(report["drawCalls"] for report in reports),
            "maxDrawCalls": 16,
            "passed": body_triangles + armor_triangles <= EQUIPPED_TRIANGLE_LIMIT
            and body_draw_calls + sum(report["drawCalls"] for report in reports) <= 16,
        },
        "review": {
            "orthographicViews": previews,
            "stressPoseReview": stress_previews,
            "stressPoseAnimationApprovalEligible": False,
            "animationReview": "missing",
            "humanApproval": "missing",
        },
        "lifecycle": {
            "status": "draft",
            "reviewStatus": "pending",
            "promotionEligible": False,
            "blockingReasons": [
                "animation_review_missing",
                "explicit_human_approval_missing",
            ],
        },
        "qcPassed": all(report["qcPassed"] for report in reports)
        and body_triangles + armor_triangles <= EQUIPPED_TRIANGLE_LIMIT
        and all(row["alphaMode"] == "OPAQUE" for row in core_body_materials)
        and recipe["modules"]["head"].get("faceCoverage") == "open"
        and len(stress_previews) == 4
        and all(Path(row["path"]).is_file() for row in stress_previews),
    }
    if args.save_blend:
        save_blend = Path(args.save_blend).resolve()
        save_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(save_blend))
    roundtrip = render_roundtrip_review(
        combined_output,
        review_dir.parent / "roundtrip-review",
        list(REQUIRED_CLIPS),
    )
    candidate["review"]["serializedGlbRoundTrip"] = roundtrip
    if not roundtrip["technicalRoundTripPassed"]:
        candidate["lifecycle"]["blockingReasons"].append("serialized_glb_roundtrip_technical_failure")
    candidate_path = output_dir / "modular-set-candidate.json"
    candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("[free-modular-armor] " + json.dumps({
        "family": args.family,
        "variant": args.variant,
        "setId": recipe["setId"],
        "moduleCount": len(reports),
        "armorTriangles": armor_triangles,
        "equippedTriangles": body_triangles + armor_triangles,
        "qcPassed": candidate["qcPassed"],
        "equippedReview": str(combined_output),
        "roundTripTechnicalPassed": roundtrip["technicalRoundTripPassed"],
        "candidate": str(candidate_path),
    }))


if __name__ == "__main__":
    main()
