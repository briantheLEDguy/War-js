"""Render deterministic, local-only review evidence for a GLB candidate."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

import bpy
from mathutils import Matrix, Vector


ANIMATION_EVIDENCE_PROFILES = ("midpoint", "locomotion_melee_key_phases")
LOCOMOTION_PHASES = (
    ("left_contact", 0.0),
    ("left_passing", 0.25),
    ("right_contact", 0.5),
    ("right_passing", 0.75),
)
MELEE_PHASES = (
    ("ready", 0.0),
    ("windup", 7 / 30),
    ("impact", 14 / 30),
    ("follow_through", 21 / 30),
    ("recovery", 1.0),
)


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    try:
        argv = argv[argv.index("--") + 1 :]
    except ValueError:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-type", choices=["bare_body", "fully_equipped"], required=True)
    parser.add_argument("--include-animations", action="store_true")
    parser.add_argument(
        "--animation-evidence-profile",
        choices=ANIMATION_EVIDENCE_PROFILES,
        default="midpoint",
    )
    parser.add_argument("--resolution", type=int, default=768)
    return parser.parse_args(argv)


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for data in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(data):
            if block.users == 0:
                data.remove(block)


def model_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not corners:
        raise RuntimeError("The imported GLB has no renderable mesh bounds.")
    minimum = Vector(tuple(min(point[i] for point in corners) for i in range(3)))
    maximum = Vector(tuple(max(point[i] for point in corners) for i in range(3)))
    return minimum, maximum


def visible_review_meshes() -> tuple[list[bpy.types.Object], list[str]]:
    """Exclude hidden rig helpers from review framing.

    GLB import can create hidden custom-bone display meshes. They do not render,
    but including their bounds makes the reviewed character occupy only a small
    part of every animation frame.
    """
    included = []
    excluded = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        if obj.hide_render or obj.hide_get():
            excluded.append(obj.name)
        else:
            included.append(obj)
    return included, sorted(excluded)


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def add_area(name: str, location: tuple[float, float, float], energy: float, size: float, target: Vector) -> None:
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    point_camera(obj, target)


def safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "_", value.lower()).strip("_") or "clip"


def animation_sample_plan(action_name: str, profile: str) -> list[dict[str, object]]:
    """Return a stable review plan without changing the authored animation.

    The focused profile exposes the views and phases that reveal lateral foot
    drift and whether a melee weapon actually follows a windup/impact arc.
    One sample per clip remains marked as primary so legacy promotion evidence
    can continue to use the ``animation_<clip>`` key.
    """
    if profile != "locomotion_melee_key_phases":
        return [{
            "sampleId": "midpoint",
            "normalizedTime": 0.5,
            "view": "isometric",
            "primary": True,
        }]

    if action_name in {"walk", "run"}:
        return [
            {
                "sampleId": sample_id,
                "normalizedTime": normalized_time,
                "view": view,
                "primary": view == "side" and sample_id == "right_contact",
            }
            for view in ("side", "back")
            for sample_id, normalized_time in LOCOMOTION_PHASES
        ]

    if action_name == "attack_melee":
        return [
            {
                "sampleId": sample_id,
                "normalizedTime": normalized_time,
                "view": view,
                "primary": view == "front" and sample_id == "impact",
            }
            for view in ("front", "side")
            for sample_id, normalized_time in MELEE_PHASES
        ]

    return [{
        "sampleId": "midpoint",
        "normalizedTime": 0.5,
        "view": "isometric",
        "primary": True,
    }]


def sample_frame(start: float, end: float, normalized_time: float) -> float:
    return start + ((end - start) * normalized_time)


def reset_armatures_to_bind(armatures: list[bpy.types.Object]) -> None:
    """Match runtime GLTFLoader behavior: load at bind pose without autoplay."""
    for armature in armatures:
        armature.data.pose_position = "POSE"
        if armature.animation_data:
            armature.animation_data.action = None
            for track in armature.animation_data.nla_tracks:
                track.mute = True
        for pose_bone in armature.pose.bones:
            pose_bone.matrix_basis = Matrix.Identity(4)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()


def main() -> None:
    args = parse_args()
    model_path = Path(args.model).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not model_path.is_file() or model_path.suffix.lower() != ".glb":
        raise FileNotFoundError(f"Review model is not a GLB: {model_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    clean_scene()
    bpy.ops.import_scene.gltf(filepath=str(model_path))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    reset_armatures_to_bind(armatures)
    meshes, excluded_bounds_meshes = visible_review_meshes()
    minimum, maximum = model_bounds(meshes)
    center = (minimum + maximum) * 0.5
    extents = maximum - minimum
    span = max(extents.x, extents.y, extents.z, 0.1)
    distance = span * 2.6

    camera_data = bpy.data.cameras.new("review_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(extents.z * 1.18, extents.x * 1.45, extents.y * 1.45, 0.5)
    camera = bpy.data.objects.new("review_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    world = bpy.context.scene.world or bpy.data.worlds.new("review_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.025, 0.028, 0.035, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    # Light power must track the square of subject scale: the original fixed
    # character-studio values underexposed building-sized props almost black.
    lighting_scale = max(1.0, (span / 2.2) ** 2)
    add_area("review_key", tuple(center + Vector((-distance, -distance, distance))), 1200 * lighting_scale, span * 1.5, center)
    add_area("review_fill", tuple(center + Vector((distance, -distance * 0.4, distance * 0.5))), 700 * lighting_scale, span, center)
    add_area("review_rim", tuple(center + Vector((0, distance, distance))), 900 * lighting_scale, span, center)

    scene = bpy.context.scene
    render_engines = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in render_engines else "BLENDER_EEVEE"
    scene.render.resolution_x = max(256, min(args.resolution, 2048))
    scene.render.resolution_y = scene.render.resolution_x
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"

    views = {
        "front": Vector((0, -distance, 0)),
        "side": Vector((distance, 0, 0)),
        "back": Vector((0, distance, 0)),
        "isometric": Vector((distance * 0.72, -distance * 0.72, distance * 0.35)),
    }
    rendered_views: dict[str, str] = {}
    for view, offset in views.items():
        camera.location = center + offset
        point_camera(camera, center)
        filename = f"{args.review_type}_{view}.png"
        scene.render.filepath = str(output_dir / filename)
        bpy.ops.render.render(write_still=True)
        rendered_views[view] = filename

    animation_frames = []
    if args.include_animations and armatures:
        for action in sorted(bpy.data.actions, key=lambda value: value.name):
            armature = armatures[0]
            reset_armatures_to_bind(armatures)
            if armature.animation_data is None:
                armature.animation_data_create()
            armature.animation_data.action = action
            start, end = action.frame_range
            sample_plan = animation_sample_plan(action.name, args.animation_evidence_profile)
            for sample in sample_plan:
                normalized_time = float(sample["normalizedTime"])
                frame = sample_frame(start, end, normalized_time)
                whole_frame = math.floor(frame)
                scene.frame_set(whole_frame, subframe=frame - whole_frame)
                view = str(sample["view"])
                camera.location = center + views[view]
                point_camera(camera, center)
                if args.animation_evidence_profile == "midpoint":
                    filename = f"animation_{safe_name(action.name)}.png"
                else:
                    filename = (
                        f"animation_{safe_name(action.name)}_"
                        f"{safe_name(view)}_{safe_name(str(sample['sampleId']))}.png"
                    )
                scene.render.filepath = str(output_dir / filename)
                bpy.ops.render.render(write_still=True)
                animation_frames.append({
                    "clip": action.name,
                    "sampleId": sample["sampleId"],
                    "view": view,
                    "frame": frame,
                    "frameRange": [float(start), float(end)],
                    "normalizedTime": normalized_time,
                    "primary": bool(sample["primary"]),
                    "image": filename,
                })

    manifest = {
        "schemaVersion": 1,
        "reviewType": args.review_type,
        "model": model_path.name,
        "views": rendered_views,
        "animationEvidenceProfile": args.animation_evidence_profile,
        "animationSamplePlanVersion": 1,
        "animationFrames": animation_frames,
        "bounds": {
            "min": list(minimum),
            "max": list(maximum),
            "meshNames": sorted(obj.name for obj in meshes),
            "excludedHiddenMeshes": excluded_bounds_meshes,
        },
    }
    (output_dir / "review-render.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[model-review] rendered {len(rendered_views)} views and {len(animation_frames)} animation frames")


if __name__ == "__main__":
    main()
