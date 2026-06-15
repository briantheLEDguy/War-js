"""
Shared Blender export helpers for War-js generators.

The game runtime is Three.js, where Y is up. These scripts author simple
procedural geometry in that same Y-up coordinate system because it matches the
runtime mental model. Blender is Z-up, and its GLB exporter converts Blender Z
to glTF/Three Y when export_yup=True. Before export, rotate root objects from
authored Y-up into Blender Z-up so runtime bounds stay upright.
"""

import math
from pathlib import Path

import bpy
from mathutils import Matrix


Y_UP_TO_BLENDER_Z_UP = Matrix.Rotation(math.radians(90), 4, "X")
REPO_ROOT = Path(__file__).resolve().parents[3]


def normalize_y_up_scene_to_blender_z_up() -> None:
    """Rotate all root objects so authored Y-up assets export upright to Three.js."""
    try:
        bpy.ops.object.mode_set(mode="OBJECT")
    except RuntimeError:
        pass

    roots = [obj for obj in bpy.context.scene.objects if obj.parent is None]
    for obj in roots:
        obj.matrix_world = Y_UP_TO_BLENDER_Z_UP @ obj.matrix_world

    bpy.context.view_layer.update()


def repo_relative_path(value: str | Path | None) -> str | None:
    """Return artifact paths relative to the repository when possible."""
    if value is None:
        return None
    path = Path(value)
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")
