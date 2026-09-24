"""
Export the runtime guard NPC model from a supplied Blender scene.

The source scene is a normal Blender Z-up character file. This script keeps the
armature/skinned meshes intact, removes embedded motion, scales the visible
character to game size, and exports an animation-free source GLB.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = ROOT / "public" / "assets" / "models" / "guard_male.glb"
DEFAULT_SOURCE_CANDIDATES = (
    ROOT / "blends" / "guard_male.blend",
    ROOT / "blends" / "guard_order.blend",
)
TARGET_HEIGHT = 1.9
IDLE_START = 1
IDLE_END = 97


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Export War-js guard_male.glb")
    parser.add_argument("--source", help="Source .blend. Defaults to blends/guard_male.blend, then guard_order.blend.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output .glb path.")
    parser.add_argument("--target-height", type=float, default=TARGET_HEIGHT, help="Runtime character height in world units.")
    parser.add_argument(
        "--include-extra-skinned-meshes",
        action="store_true",
        help="Keep all visible skinned meshes instead of only the largest runtime guard mesh.",
    )
    return parser.parse_args(argv)


def resolve_path(path_text: str | None, candidates: tuple[Path, ...]) -> Path:
    if path_text:
        path = Path(path_text)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            raise FileNotFoundError(f"Missing source blend: {path}")
        return path

    for candidate in candidates:
        if candidate.exists():
            return candidate
    listed = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"Missing guard source blend. Checked: {listed}")


def armature_for_mesh(mesh: bpy.types.Object) -> bpy.types.Object | None:
    if mesh.parent and mesh.parent.type == "ARMATURE":
        return mesh.parent
    for modifier in mesh.modifiers:
        if modifier.type == "ARMATURE" and modifier.object:
            return modifier.object
    return None


def pick_runtime_objects(include_extra_skinned_meshes: bool = False) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    visible_armatures = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "ARMATURE" and not obj.hide_get() and not obj.hide_render
    ]
    if not visible_armatures:
        raise RuntimeError("Guard blend has no visible armature.")

    visible_meshes = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and not obj.hide_get() and not obj.hide_render
    ]
    if not visible_meshes:
        raise RuntimeError("Guard blend has no visible mesh objects.")

    def skinned_mesh_count(armature: bpy.types.Object) -> int:
        return sum(1 for mesh in visible_meshes if armature_for_mesh(mesh) == armature)

    armature = max(visible_armatures, key=skinned_mesh_count)
    meshes = [mesh for mesh in visible_meshes if armature_for_mesh(mesh) == armature]
    if not meshes:
        raise RuntimeError(f"No visible meshes are bound to armature {armature.name!r}.")

    if not include_extra_skinned_meshes:
        primary = max(meshes, key=lambda mesh: len(mesh.data.vertices))
        skipped = [mesh.name for mesh in meshes if mesh is not primary]
        meshes = [primary]
        if skipped:
            print(f"[WAR] Guard export skipped secondary skinned meshes: {', '.join(skipped)}")

    unskinned = [mesh.name for mesh in meshes if not mesh.vertex_groups]
    if unskinned:
        raise RuntimeError(f"Meshes lack vertex groups for skinning: {', '.join(unskinned)}")

    armature.name = "guard_male_armature"
    armature.data.name = "guard_male_skeleton"
    for index, mesh in enumerate(meshes, start=1):
        mesh.name = f"guard_male_mesh_{index:02d}"
        mesh.data.name = f"guard_male_geometry_{index:02d}"
    return armature, meshes


def mesh_world_bounds(meshes: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    bpy.context.view_layer.update()
    min_v = Vector((math.inf, math.inf, math.inf))
    max_v = Vector((-math.inf, -math.inf, -math.inf))
    for mesh in meshes:
        for corner in mesh.bound_box:
            world = mesh.matrix_world @ Vector(corner)
            min_v.x = min(min_v.x, world.x)
            min_v.y = min(min_v.y, world.y)
            min_v.z = min(min_v.z, world.z)
            max_v.x = max(max_v.x, world.x)
            max_v.y = max(max_v.y, world.y)
            max_v.z = max(max_v.z, world.z)
    return min_v, max_v


def scale_and_ground(armature: bpy.types.Object, meshes: list[bpy.types.Object], target_height: float) -> None:
    min_v, max_v = mesh_world_bounds(meshes)
    height = max_v.z - min_v.z
    if height <= 0:
        raise RuntimeError("Guard mesh height is zero; cannot scale.")

    factor = target_height / height
    armature.scale = (armature.scale.x * factor, armature.scale.y * factor, armature.scale.z * factor)
    bpy.context.view_layer.update()

    min_v, _ = mesh_world_bounds(meshes)
    armature.location.z -= min_v.z
    bpy.context.view_layer.update()


def material_color_for_name(name: str) -> tuple[tuple[float, float, float, float], float, float]:
    lower = name.lower()
    if "metal" in lower or "sord" in lower or "gray" in lower or "material.010" in lower:
        return (0.48, 0.46, 0.40, 1.0), 0.48, 0.58
    if "brown" in lower:
        return (0.25, 0.13, 0.06, 1.0), 0.86, 0.0
    if "black" in lower:
        return (0.025, 0.026, 0.024, 1.0), 0.90, 0.0
    if "material.014" in lower or "material.015" in lower:
        return (0.36, 0.34, 0.30, 1.0), 0.55, 0.45
    return (0.42, 0.38, 0.32, 1.0), 0.68, 0.20


def sanitize_material(mat: bpy.types.Material) -> None:
    color, roughness, metallic = material_color_for_name(mat.name)
    mat.use_nodes = True
    mat.diffuse_color = color
    mat.blend_method = "OPAQUE"
    if hasattr(mat, "use_screen_refraction"):
        mat.use_screen_refraction = False
    if hasattr(mat, "show_transparent_back"):
        mat.show_transparent_back = False

    nodes = mat.node_tree.nodes
    nodes.clear()
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    output = nodes.new(type="ShaderNodeOutputMaterial")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
    mat.node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])


def sanitize_guard_materials(meshes: list[bpy.types.Object]) -> None:
    seen: set[bpy.types.Material] = set()
    for mesh in meshes:
        for mat in mesh.data.materials:
            if mat and mat not in seen:
                seen.add(mat)
                sanitize_material(mat)


def remove_export_constraints(armature: bpy.types.Object) -> None:
    removed = 0
    for pose_bone in armature.pose.bones:
        for constraint in list(pose_bone.constraints):
            pose_bone.constraints.remove(constraint)
            removed += 1
    if removed:
        print(f"[WAR] Guard export removed {removed} pose constraints for GLB export")


def strip_non_runtime_objects(armature: bpy.types.Object, meshes: list[bpy.types.Object]) -> None:
    keep = {armature, *meshes}
    for pose_bone in armature.pose.bones:
        pose_bone.custom_shape = None

    for obj in list(bpy.data.objects):
        if obj not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)




def select_runtime_objects(armature: bpy.types.Object, meshes: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (armature, *meshes):
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature


def export_glb(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_animations=False,
        export_animation_mode="ACTIONS",
        export_skins=True,
        export_yup=True,
        export_apply=True,
        export_force_sampling=True,
        export_cameras=False,
        export_lights=False,
        export_draco_mesh_compression_enable=False,
    )


def main() -> None:
    args = parse_args()
    source = resolve_path(args.source, DEFAULT_SOURCE_CANDIDATES)
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output

    print(f"[WAR] Opening guard source: {source}")
    bpy.ops.wm.open_mainfile(filepath=str(source))

    armature, meshes = pick_runtime_objects(args.include_extra_skinned_meshes)
    strip_non_runtime_objects(armature, meshes)
    sanitize_guard_materials(meshes)
    scale_and_ground(armature, meshes, args.target_height)
    armature.animation_data_clear()
    remove_export_constraints(armature)
    select_runtime_objects(armature, meshes)
    export_glb(output)

    min_v, max_v = mesh_world_bounds(meshes)
    print(
        "[WAR] Guard rig export ok: "
        f"meshes={len(meshes)} animations=0 "
        f"bounds_min=({min_v.x:.3f},{min_v.y:.3f},{min_v.z:.3f}) "
        f"bounds_max=({max_v.x:.3f},{max_v.y:.3f},{max_v.z:.3f}) "
        f"output={output}"
    )


if __name__ == "__main__":
    main()
