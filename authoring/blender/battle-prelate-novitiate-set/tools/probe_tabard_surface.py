"""Isolated tabard baking/deformation probe using the saved V4 game rig.

Reads the completed game master and staged bundle; writes only a new directory
under review/tabard_surface_probe. No source geometry, staged model/report,
existing review evidence, or master file is saved or replaced.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BAKED_DETAILS = {"relic_tabard_fold_following_cross", "relic_tabard_gilded_pointed_hem"}
TRIM_COLORS = {
    "relic_tabard_gilded_pointed_hem": (1, .015, .45, 1),
    "relic_tabard_explicit_fringe_tassels": (.015, 1, .08, 1),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protected_snapshot(root, master):
    paths = set((root / "runtime").glob("*.glb"))
    paths.update(path for path in (root / "runtime").glob("*.json") if path.is_file())
    paths.update((root / "source").glob("*.json"))
    paths.add(master)
    return {str(path.resolve()): digest(path) for path in sorted(paths)}


def output_directory(root, requested, diagnose):
    boundary = (root / "review/tabard_surface_probe").resolve()
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ("_trim" if diagnose else "_bake")
    path = Path(requested).resolve() if requested else boundary / suffix
    if path == boundary or not path.is_relative_to(boundary):
        raise ValueError("Probe output must be a fresh subdirectory under review/tabard_surface_probe")
    path.mkdir(parents=True, exist_ok=False)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=ROOT / "battle_prelate_game_master.blend")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resolution", type=int, default=1024)
    parser.add_argument("--diagnose-trim", action="store_true", help="Render separate hem/fringe diagnostic colors without baking")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    import bpy
    from mathutils import Matrix
    sys.path.insert(0, str(ROOT / "tools"))
    import rig_character as rig_tools
    import build_proof as proof

    if not bpy.app.background:
        raise ValueError("Run this probe in a disposable background Blender process")
    master = args.master.resolve()
    before = protected_snapshot(ROOT, master)
    output = output_directory(ROOT, args.output, args.diagnose_trim)
    report = {"schema_version": 1, "status": "started", "diagnose_trim": args.diagnose_trim,
              "master": str(master), "master_sha256": before[str(master)], "images": [],
              "source_geometry_modified": False, "staged_outputs_modified": False,
              "camera_policy": "Existing frozen full_front for rest and full_three_quarter for motion; unchanged alignment",
              "animation_policy": "Use the actual saved game-master actions; do not regenerate corrections"}
    try:
        bpy.ops.wm.open_mainfile(filepath=str(master))
        rig = bpy.data.objects.get("humanoid_game_v2")
        if rig is None or rig.type != "ARMATURE":
            raise ValueError("Saved master is missing the canonical game rig")
        rig_tools.verify_contract_rig(rig)
        if rig.get("animation_correction_version") != "authored_hammer_grip_v4_book_clearance":
            raise ValueError("Probe requires the saved V4 book-clearance rig")
        stage = json.loads((ROOT / "runtime/runtime_report.json").read_text())
        report["animation_corrections"] = stage.get("animation_corrections")
        report["runtime_report_sha256"] = digest(ROOT / "runtime/runtime_report.json")
        controls = bpy.data.collections.get(proof.COLLECTION)
        if controls is None:
            raise ValueError("Saved master does not retain authored source controls")
        controls.hide_viewport = controls.hide_render = False
        sources = [obj for obj in controls.all_objects if obj.type == "MESH" and rig_tools.source_slot(obj) == "tabard"]
        for source in sources:
            path = ROOT / source["source_file"]
            if digest(path) != source["source_sha256"]:
                raise ValueError("Saved master tabard source differs from current authored records")
        if not BAKED_DETAILS.issubset({obj["source_part"] for obj in sources}):
            raise ValueError("Saved source is missing one of the modeled cloth appliques")
        rig.animation_data_create()
        rig.animation_data.action = None
        for track in rig.animation_data.nla_tracks:
            track.mute = True
        rig.data.pose_position = "REST"
        for bone in rig.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        for level in (0, 1, 2):
            collection = bpy.data.collections.get(f"RUNTIME_LOD{level}")
            if collection:
                collection.hide_viewport = collection.hide_render = level != 0
                for obj in collection.objects:
                    if obj.get("slot") == "tabard":
                        obj.hide_render = True
        collection = bpy.data.collections.new("ISOLATED_TABARD_PROBE")
        bpy.context.scene.collection.children.link(collection)
        runtime_parts = [rig_tools.evaluate_runtime_part(source, collection, rig, 0) for source in sources
                         if args.diagnose_trim or source["source_part"] not in BAKED_DETAILS]
        report["retained_runtime_parts"] = sorted({obj["source_part"] for obj in runtime_parts})
        report["high_source_parts"] = sorted({obj["source_part"] for obj in sources})
        report["baked_surface_only_parts"] = [] if args.diagnose_trim else sorted(BAKED_DETAILS)
        if args.diagnose_trim:
            for obj in runtime_parts:
                color = TRIM_COLORS.get(obj["source_part"])
                if color:
                    material = bpy.data.materials.new("diagnostic." + obj["source_part"])
                    material.use_nodes = True
                    shader = material.node_tree.nodes.get("Principled BSDF")
                    shader.inputs["Base Color"].default_value = color
                    shader.inputs["Roughness"].default_value = .55
                    obj.data.materials.clear()
                    obj.data.materials.append(material)
                    for polygon in obj.data.polygons:
                        polygon.material_index = 0
            report["trim_color_key"] = {"magenta": "gilded pointed hem", "green": "individual fringe tassels"}
            leg_material = bpy.data.materials.new("diagnostic.runtime_leg_overlap")
            leg_material.use_nodes = True
            leg_material.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (.015, .2, 1, 1)
            for obj in bpy.data.collections["RUNTIME_LOD0"].objects:
                if obj.type == "MESH" and obj.get("slot") == "legs":
                    obj.data.materials.clear()
                    obj.data.materials.append(leg_material)
                    for polygon in obj.data.polygons:
                        polygon.material_index = 0
            report["trim_color_key"]["blue"] = "existing runtime leg module; used to identify overlap"
        else:
            from bake_atlas import bake_module_atlas
            if "transfer_surface_channels" not in inspect.signature(bake_module_atlas).parameters:
                raise ValueError("Wait for the optional high-source surface transfer helper before running the bake probe")
            for obj in bpy.context.view_layer.objects:
                obj.select_set(False)
            target = rig_tools.join_slot(runtime_parts, "tabard", 0)
            bpy.context.view_layer.update()
            for obj in controls.all_objects:
                if obj is not None and obj.type == "MESH":
                    obj.hide_render = True
            report["textures"] = bake_module_atlas(target, "tabard_probe", output / "textures",
                                                   resolution=args.resolution, high_sources=sources,
                                                   transfer_surface_channels=True)
            report["geometry_audit"] = rig_tools.audit_mesh(target, rig)
        controls.hide_viewport = controls.hide_render = True
        scene_data = json.loads((ROOT / "source/scene.json").read_text())
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_percentage = 50
        scene.view_layers[0].material_override = None
        for clip in ("rest", "run", "jump"):
            camera_id = "full_front" if clip == "rest" else "full_three_quarter"
            camera = next(item for item in scene_data["cameras"] if item["id"] == camera_id)
            scene.camera = bpy.data.objects["comparison." + camera_id]
            if max(abs(scene.camera.location[i] - camera["position"][i]) for i in range(3)) > 1e-6:
                raise ValueError("Saved review camera position differs from frozen source")
            if abs(scene.camera.data.ortho_scale - camera["orthographic_scale"]) > 1e-6:
                raise ValueError("Saved review camera scale differs from frozen source")
            scene.render.resolution_x, scene.render.resolution_y = camera["resolution"]
            rig.animation_data.action = None
            for bone in rig.pose.bones:
                bone.matrix_basis = Matrix.Identity(4)
            if clip == "rest":
                rig.data.pose_position = "REST"
                frame = 1.0
            else:
                rig.data.pose_position = "POSE"
                action = bpy.data.actions.get(clip)
                if action is None or not action.slots:
                    raise ValueError(f"Saved corrected action is unavailable: {clip}")
                rig.animation_data.action = action
                rig.animation_data.action_slot = action.slots[0]
                start, end = action.frame_range
                frame = float(start + (end-start) * .5)
            scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame))
            bpy.context.view_layer.update()
            path = output / f"{clip}_50.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            report["images"].append({"clip": clip, "frame": frame, "path": str(path.relative_to(ROOT)),
                                     "sha256": digest(path), "engine": "BLENDER_EEVEE", "resolution_percentage": 50,
                                     "camera": camera})
        report["status"] = "rendered_pending_visual_review"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        after = protected_snapshot(ROOT, master)
        changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
        report["protected_files_unchanged"] = not changed
        report["protected_file_count"] = len(before)
        report["protected_changes"] = changed
        (output / "probe_report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("TABARD_PROBE_REPORT " + str(output / "probe_report.json"), flush=True)
        if changed:
            raise ValueError("Staged/master/source files changed while probe ran; do not treat evidence as frozen")


if __name__ == "__main__":
    main()
