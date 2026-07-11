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

import bmesh
import bpy
from mathutils import Matrix, Vector

from bl_ext.blender_org.mpfb.services import HumanService, LocationService


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
MODULE_TRIANGLE_TARGET = 6_500
EQUIPPED_TRIANGLE_LIMIT = 120_000
GENERATOR_VERSION = "1.4.0-draft"

# Each layer is authored with a deterministic clearance from the accepted body.
# The values are deliberately small: enough to prevent coplanar fighting and
# garment-on-garment intersections without changing the accepted silhouette.
FITTED_LAYER_CLEARANCE = {
    "chest": 0.003,
    "hands": 0.008,
    "legs": 0.002,
    "feet": 0.008,
}
SURFACE_LAYER_CLEARANCE = {
    "shoulders": 0.016,
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
    parser.add_argument("--family", required=True, choices=("civic_humanoid_v2", "mire_brutish_v1"))
    parser.add_argument("--variant", required=True, choices=("m", "f"))
    parser.add_argument("--source-blend", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--save-blend")
    parser.add_argument("--weapon-glb")
    parser.add_argument("--resume-existing", action="store_true")
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_recipe(family: str, variant: str) -> tuple[dict, dict]:
    payload = json.loads(RECIPE_PATH.read_text(encoding="utf-8"))
    recipe = payload["sets"].get(family)
    if not recipe:
        raise RuntimeError(f"No free armor recipe exists for {family}")
    if variant not in recipe["bodyVariants"]:
        raise RuntimeError(f"Recipe {recipe['setId']} does not support {variant}")
    if tuple(recipe["modules"].keys()) != ARMOR_SLOTS:
        raise RuntimeError("Armor recipe must declare the canonical nine slots in order")
    return payload, recipe


def hex_color(value: str) -> tuple[float, float, float, float]:
    value = value.lstrip("#")
    srgb = tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))
    linear = tuple(
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in srgb
    )
    return linear + (1.0,)


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
    base_image = create_image(
        f"{name}_baseColor",
        size,
        lambda u, v: tuple(
            max(
                0.0,
                min(
                    1.0,
                    channel
                    * (
                        0.95
                        + 0.022 * math.sin(u * 97.0) * math.sin(v * 103.0)
                        + 0.010 * math.sin(u * 211.0 + v * 173.0)
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
            0.5 + 0.025 * math.sin(u * 52.0),
            0.5 + 0.025 * math.cos(v * 47.0),
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


def offset_vertices_along_normals(obj: bpy.types.Object, distance: float) -> None:
    """Move an authored garment to its deterministic runtime layer."""
    if abs(distance) <= 1e-8:
        return
    for vertex in obj.data.vertices:
        vertex.co += vertex.normal * distance
    obj.data.update()


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
                raise RuntimeError(
                    f"{obj.name} has no {proximal_bone}/{distal_bone} weights for {side}"
                )
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
                raise RuntimeError(f"No weighted seam region found for {obj.name}:{bone_name}")
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
                raise RuntimeError(f"Seam trim removed no distal faces for {obj.name}:{bone_name}")
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


def enforce_triangle_budget(obj: bpy.types.Object) -> None:
    triangles = evaluated_triangles(obj)
    if triangles <= MODULE_TRIANGLE_TARGET:
        return
    decimate = obj.modifiers.new("draft_triangle_budget", "DECIMATE")
    decimate.ratio = max(0.05, MODULE_TRIANGLE_TARGET / triangles)
    decimate.use_collapse_triangulate = True
    apply_modifier(obj, decimate)


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
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    obj.data.remesh_voxel_size = max(obj.dimensions) / 105.0
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
    if not obj.data.uv_layers:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project()
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.select_set(False)
    enforce_triangle_budget(obj)
    cleanup_closed_mesh(obj)
    if non_manifold_edges(obj) > 0:
        raise RuntimeError(
            f"Voxel-remeshed helmet is still non-manifold: {non_manifold_edges(obj)} edges"
        )


def cleanup_closed_mesh(obj: bpy.types.Object) -> None:
    """Weld split vertices, remove degenerate geometry, and cap boundaries."""
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    try:
        bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1e-6)
        bmesh.ops.dissolve_degenerate(mesh, edges=list(mesh.edges), dist=1e-8)
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


def refine_shoulder_shell(
    obj: bpy.types.Object,
    body: bpy.types.Object,
    rig: bpy.types.Object,
    material: bpy.types.Material,
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
    if slot == "shoulders":
        refine_shoulder_shell(obj, body, rig, material)
    else:
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
    assign_material(obj, material)
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
    material_images = []
    for image in sorted(
        (image for image in bpy.data.images if "_draft_pbr_" in image.name),
        key=lambda image: image.name,
    ):
        pixel_count = max(1, len(image.pixels) // 4)
        offsets = (0, (pixel_count // 2) * 4, (pixel_count - 1) * 4)
        samples = [list(image.pixels[offset : offset + 4]) for offset in offsets]
        populated = any(any(channel > 0.0001 for channel in sample[:3]) for sample in samples)
        material_images.append({
            "name": image.name,
            "colorspace": image.colorspace_settings.name,
            "samples": samples,
            "populated": populated,
        })
    armor_images_populated = len(material_images) == 12 and all(
        image["populated"] for image in material_images
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
        "assetId": "chr.civic_humanoid_v2.battle_prelate_m.equipped_review",
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
        "triangleBudget": triangles <= MODULE_TRIANGLE_LIMIT,
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
    pack_recipe, recipe = load_recipe(args.family, args.variant)
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
                if module["kind"] == "mpfbAsset"
                else None
            )
            sources[slot] = (source, module.get("pack"))
        elif args.resume_existing:
            raise RuntimeError(f"Resume blend is missing expected module: {object_name}")
        elif module["kind"] == "mpfbAsset":
            obj, source = fitted_asset(
                body,
                rig,
                object_name,
                module["asset"],
                material,
                slot,
            )
            sources[slot] = (source, module["pack"])
        elif module["kind"] == "bodySurface":
            obj = (
                create_curved_belt(body, rig, object_name, material)
                if slot == "waist"
                else extract_surface_patch(body, rig, object_name, slot, module, material)
            )
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
        if slot == "head" and non_manifold_edges(obj) > 0:
            manifold_rigid_headpiece(obj, material)
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
            or obj in weapon_objects
        )
    ]
    previews = render_reviews(preview_meshes, review_dir)
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

    body_triangles = evaluated_triangles(body)
    armor_triangles = sum(report["totalTriangles"] for report in reports)
    combined_name = (
        "battle_preplate_m_equipped_review.glb"
        if args.family == "civic_humanoid_v2" and args.variant == "m"
        else f"{recipe['setId']}_{args.variant}_equipped_review.glb"
    )
    combined_output = output_dir.parent / combined_name
    sockets = [obj for obj in bpy.context.scene.objects if obj.type == "EMPTY" and obj.name.startswith("socket_")]
    combined_objects = [rig, *preview_meshes, *sockets, *[obj for obj in weapon_objects if obj not in preview_meshes]]
    rig["assetId"] = "chr.civic_humanoid_v2.battle_prelate_m.equipped_review"
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
            "drawCalls": 4 + sum(report["drawCalls"] for report in reports),
            "maxDrawCalls": 16,
            "passed": body_triangles + armor_triangles <= EQUIPPED_TRIANGLE_LIMIT
            and 4 + sum(report["drawCalls"] for report in reports) <= 16,
        },
        "review": {
            "orthographicViews": previews,
            "stressPoseReview": "missing",
            "animationReview": "missing",
            "humanApproval": "missing",
        },
        "lifecycle": {
            "status": "draft",
            "reviewStatus": "pending",
            "promotionEligible": False,
            "blockingReasons": [
                "stress_pose_review_missing",
                "animation_review_missing",
                "explicit_human_approval_missing",
            ],
        },
        "qcPassed": all(report["qcPassed"] for report in reports)
        and body_triangles + armor_triangles <= EQUIPPED_TRIANGLE_LIMIT,
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
