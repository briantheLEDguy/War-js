"""Assemble and render the actual exported GLBs in a fresh background Blender.

No source geometry, weights, bind matrices, camera calibration, or animations are
authored here. Armor rigs are replaced only after exact rest-rig compatibility and
world-space rest-vertex checks. Output is pending visual review, never approval.
Run --compose REPORT with bundled Python/Pillow to make the stress contact sheet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLOTS = ("body", "head", "shoulders", "chest", "hands", "waist", "legs", "feet", "back", "tabard", "weapon")
CLIPS = ("idle", "walk", "run", "combat_idle", "attack_melee", "attack_ranged", "cast", "death", "jump")
SOCKETS = {"socket_hand_R", "socket_hand_L", "socket_back", "socket_root"}
FULL_VIEWS = ("full_front", "full_three_quarter", "full_side", "full_back")
VIEW_LABEL = {"full_front": "front", "full_three_quarter": "isometric", "full_side": "side", "full_back": "back"}
bpy = None
Matrix = None


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def model_name(slot, lod):
    stem = "chr_civic_battle_prelate_t1_m" if slot == "body" else "wep_civic_battle_prelate_dawn_maul" if slot == "weapon" else f"arm_civic_battle_prelate_{slot}_t1_m"
    return stem + (f"_lod{lod}" if lod else "") + ".glb"


def check_files(runtime, validation_path, lods):
    validation = json.loads(validation_path.read_text())
    require(validation.get("status") == "passed" and not validation.get("errors"), "Binary validation must pass before exported-model review")
    require(Path(validation.get("runtime_directory", "")).resolve() == runtime.resolve(), "Validation points to a different runtime directory")
    require(digest(runtime / "runtime_report.json") == validation.get("stage_report_sha256"), "Runtime build changed after binary validation")
    hashes = {}
    for lod in lods:
        record = validation.get("lods", {}).get(str(lod), {})
        require(record.get("complete") is True and set(record.get("modules", {})) == set(SLOTS), f"LOD{lod} is not fully validated")
        for slot in SLOTS:
            module = record["modules"][slot]
            name = model_name(slot, lod)
            require(module.get("model") == name and (runtime / name).is_file(), f"Missing validated {name}")
            require(digest(runtime / name) == module.get("sha256"), f"Export changed after validation: {name}")
            hashes[name] = module["sha256"]
    return validation, hashes


def matrix_delta(left, right):
    return max(abs(left[row][col] - right[row][col]) for row in range(4) for col in range(4))


def bone_display_helpers(objects):
    """Identify importer display objects by bone references, never by mesh name."""
    return {bone.custom_shape for obj in objects if obj.type == "ARMATURE"
            for bone in obj.pose.bones if bone.custom_shape is not None}


def remove_unused_display_helpers(candidates):
    referenced = bone_display_helpers(bpy.data.objects)
    for helper in candidates - referenced:
        mesh = helper.data if helper.type == "MESH" else None
        bpy.data.objects.remove(helper, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = set(bpy.data.objects) - before
    require(imported, f"GLB imported no objects: {path.name}")
    helpers = bone_display_helpers(imported)
    for helper in helpers:
        helper.hide_render = True
        if helper.name in bpy.context.view_layer.objects:
            helper.hide_set(True)
    # Blender may create Icosphere display helpers absent from the binary GLB.
    # They are not authored asset meshes and must never be rebound or rendered.
    return imported - helpers


def bind_audit(source, target):
    source_names = {bone.name for bone in source.data.bones}
    target_names = {bone.name for bone in target.data.bones}
    require(source_names == target_names, "Imported armor and body bone names differ")
    require(matrix_delta(source.matrix_world, target.matrix_world) <= 1e-6, "Imported armor and body armature world matrices differ")
    maximum = 0.0
    for name in source_names:
        left, right = source.data.bones[name], target.data.bones[name]
        require((left.parent.name if left.parent else None) == (right.parent.name if right.parent else None), f"Bone hierarchy mismatch: {name}")
        maximum = max(maximum, matrix_delta(left.matrix_local, right.matrix_local))
    require(maximum <= 1e-5, f"Armor rest matrix mismatch: {maximum}")
    return {"bone_count": len(source_names), "maximum_rest_matrix_delta": maximum, "world_matrix_delta": matrix_delta(source.matrix_world, target.matrix_world)}


def world_vertices(obj):
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def import_body(path):
    before_actions = set(bpy.data.actions)
    objects = import_glb(path)
    rigs = [obj for obj in objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in objects if obj.type == "MESH"]
    require(len(rigs) == 1 and meshes, "Body must import one armature and its mesh")
    rig = rigs[0]
    require(rig.name == "humanoid_game_v2" and len(rig.data.bones) == 56, "Body must expose the canonical named 56-bone rig")
    sockets = {obj.name: obj for obj in objects if obj.type == "EMPTY" and obj.name in SOCKETS}
    require(set(sockets) == SOCKETS, "Body is missing a canonical socket EMPTY")
    actions = {action.name: action for action in set(bpy.data.actions) - before_actions}
    require(set(CLIPS).issubset(actions), "Body reimport is missing the nine named actions")
    # Preserve glTF-imported action-slot bindings, including animated socket roots.
    bindings = {name: [] for name in CLIPS}
    rest_world = {obj: obj.matrix_world.copy() for obj in objects}
    rest_basis = {obj: obj.matrix_basis.copy() for obj in objects}
    for obj in objects:
        data = obj.animation_data
        if not data:
            continue
        for track in data.nla_tracks:
            for strip in track.strips:
                action = strip.action
                if action and action.name in bindings:
                    bindings[action.name].append((obj, action, getattr(strip, "action_slot", None)))
            track.mute = True
        if data.action and data.action.name in bindings:
            bindings[data.action.name].append((obj, data.action, getattr(data, "action_slot", None)))
        data.action = None
    for name in CLIPS:
        if not any(obj == rig for obj, _, _ in bindings[name]):
            action = actions[name]
            slots = list(getattr(action, "slots", []))
            require(len(slots) <= 1, f"Missing authoritative rig action-slot binding for {name}")
            bindings[name].append((rig, action, slots[0] if slots else None))
    rig.data.pose_position = "REST"
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    return {"rig": rig, "meshes": meshes, "sockets": sockets, "objects": objects, "actions": actions,
            "bindings": bindings, "rest_world": rest_world, "rest_basis": rest_basis, "body_sha256": digest(path)}


def rebind_armor(path, rig, slot):
    imported = import_glb(path)
    duplicates = [obj for obj in imported if obj.type == "ARMATURE"]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    require(len(duplicates) == 1 and meshes, f"{slot} must import one rig and a mesh")
    duplicate = duplicates[0]
    helpers = bone_display_helpers(duplicates)
    duplicate.data.pose_position = "REST"
    for bone in duplicate.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    rest = bind_audit(duplicate, rig)
    maximum = 0.0
    for mesh in meshes:
        modifiers = [modifier for modifier in mesh.modifiers if modifier.type == "ARMATURE"]
        require(len(modifiers) == 1 and modifiers[0].object == duplicate, f"{slot} has an unexpected armature modifier")
        before = world_vertices(mesh)
        matrix = mesh.matrix_world.copy()
        modifiers[0].object = rig
        mesh.parent = rig
        mesh.matrix_parent_inverse = rig.matrix_world.inverted()
        mesh.matrix_world = matrix
        after = world_vertices(mesh)
        require(len(before) == len(after), f"{slot} vertex count changed during rebind")
        maximum = max(maximum, max(((a-b).length for a,b in zip(before, after)), default=0))
        mesh["reimport_module"] = slot
        mesh["reimport_source_sha256"] = digest(path)
    require(maximum <= 1e-5, f"{slot} rest vertices moved during rebind: {maximum}")
    for obj in imported - set(meshes):
        bpy.data.objects.remove(obj, do_unlink=True)
    remove_unused_display_helpers(helpers)
    bpy.context.view_layer.update()
    return meshes, {"source": path.name, "sha256": digest(path), "rest_rig": rest, "maximum_rest_vertex_delta_m": maximum}


def attach_weapon(path, socket):
    objects = import_glb(path)
    require(not any(obj.type == "ARMATURE" for obj in objects), "Socketed weapon unexpectedly contains an armature")
    meshes = [obj for obj in objects if obj.type == "MESH"]
    require(meshes, "Weapon has no mesh")
    roots = [obj for obj in objects if obj.parent not in objects]
    require(roots, "Weapon import has no root")
    for obj in roots:
        local = obj.matrix_world.copy()
        obj.parent = socket
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = local
    for obj in meshes:
        obj["reimport_module"] = "weapon"
        obj["reimport_source_sha256"] = digest(path)
    bpy.context.view_layer.update()
    return objects, {"source": path.name, "sha256": digest(path), "socket": socket.name,
                     "policy": "Use exported grip-origin coordinates and imported local transforms; no fitting offset or extra rotation"}


def rest_pose(assembly):
    rig = assembly["rig"]
    for obj in assembly["objects"]:
        if obj.animation_data:
            obj.animation_data.action = None
        obj.matrix_basis = assembly["rest_basis"][obj]
    rig.data.pose_position = "REST"
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    # Restore root transforms only; bone-parented socket transforms remain intact.
    for obj in assembly["objects"]:
        if obj.parent not in assembly["objects"]:
            obj.matrix_world = assembly["rest_world"][obj]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def set_clip(assembly, name, fraction):
    rest_pose(assembly)
    rig = assembly["rig"]
    rig.data.pose_position = "POSE"
    for obj, action, slot in assembly["bindings"][name]:
        obj.animation_data_create()
        obj.animation_data.action = action
        if slot is not None:
            obj.animation_data.action_slot = slot
    action = assembly["actions"][name]
    start, end = action.frame_range
    require(end > start, f"Imported action {name} has no duration")
    frame = float(start + (end-start) * fraction)
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame))
    bpy.context.view_layer.update()
    return frame


def assemble(runtime, lod):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    assembly = import_body(runtime / model_name("body", lod))
    modules = {"body": {"source": model_name("body", lod), "sha256": assembly["body_sha256"], "bone_count": 56}}
    meshes = list(assembly["meshes"])
    for slot in SLOTS:
        if slot in {"body", "weapon"}:
            continue
        imported, report = rebind_armor(runtime / model_name(slot, lod), assembly["rig"], slot)
        meshes.extend(imported)
        modules[slot] = report
    weapon, modules["weapon"] = attach_weapon(runtime / model_name("weapon", lod), assembly["sockets"]["socket_hand_R"])
    meshes.extend(obj for obj in weapon if obj.type == "MESH")
    require(len([obj for obj in bpy.data.objects if obj.type == "ARMATURE"]) == 1, "Duplicate armatures remain after assembly")
    assembly.update(all_meshes=meshes, weapon=weapon, modules=modules)
    rest_pose(assembly)
    return assembly


def render(record, output, engine, samples, percentage=100, neutral=None):
    scene = bpy.context.scene
    scene.camera = bpy.data.objects["comparison." + record["id"]]
    scene.render.engine = engine
    if engine == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = record["resolution"]
    scene.render.resolution_percentage = percentage
    scene.view_layers[0].material_override = neutral
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    scene.view_layers[0].material_override = None
    return {"path": output.relative_to(ROOT).as_posix(), "sha256": digest(output), "engine": engine,
            "samples": samples if engine == "CYCLES" else None, "resolution_percentage": percentage,
            "camera": record, "frame": scene.frame_current + scene.frame_subframe}


def compose(report_path):
    from PIL import Image, ImageDraw, ImageFont
    report_path = Path(report_path).resolve()
    report = json.loads(report_path.read_text())
    frames = report.get("motion_frames", [])
    require(len(frames) == 27, "Contact sheet requires all three recorded samples for each of nine clips")
    width, height = 340, 392
    canvas = Image.new("RGB", (width * 3, height * 9), (25, 27, 31))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    for index, entry in enumerate(frames):
        path = ROOT / entry["path"]
        require(digest(path) == entry["sha256"], "Motion image changed since render")
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((width, height - 30))
            x, y = (index % 3)*width, (index//3)*height
            canvas.paste(image, (x + (width-image.width)//2, y))
            draw.text((x+8, y+height-25), f"{entry['clip']}  {entry['fraction']:.0%}  frame {entry['frame']:.1f}", fill=(230,231,234), font=font)
    output = report_path.parent / "reimport_motion_contact.png"
    canvas.save(output)
    record = {"id": "animation_stress_contact", "scope": "animation_stress", "path": output.relative_to(ROOT).as_posix(), "sha256": digest(output),
              "kind": "Contact sheet of actual GLB action renders; no synthesized frames", "clips": list(CLIPS)}
    report["contact_sheet"] = record
    report["evidence"] = [entry for entry in report["evidence"] if entry.get("id") != record["id"]] + [record]
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print("REIMPORT_CONTACT_COMPLETE " + str(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=ROOT / "runtime")
    parser.add_argument("--validation", type=Path, default=ROOT / "runtime/validation_report.json")
    parser.add_argument("--lods", default="0,1,2")
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
    parser.add_argument("--motion-engine", choices=("CYCLES", "BLENDER_EEVEE"), default="BLENDER_EEVEE")
    parser.add_argument("--motion-percentage", type=int, default=40)
    parser.add_argument("--skip-motion", action="store_true", help="Partial inspection only; cannot provide motion evidence")
    parser.add_argument("--compose", type=Path, metavar="REPORT", help="Run with Python/Pillow after Blender finishes")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else None)
    if args.compose:
        compose(args.compose)
        return
    global bpy, Matrix
    import bpy as blender
    from mathutils import Matrix as BlenderMatrix
    bpy, Matrix = blender, BlenderMatrix
    require(bpy.app.background, "Reimport review runs only in a fresh background Blender process")
    require(1 <= args.samples <= 256 and 1 <= args.motion_percentage <= 100, "Invalid render sampling or resolution percentage")
    lods = tuple(int(value) for value in args.lods.split(","))
    require(lods and len(set(lods)) == len(lods) and all(lod in (0,1,2) for lod in lods), "LODs must be a unique subset of 0,1,2")
    validation, hashes = check_files(args.runtime, args.validation, lods)
    scene_path = ROOT / "source/scene.json"
    scene_data = json.loads(scene_path.read_text())
    cameras = {record["id"]: record for record in scene_data["cameras"]}
    require(all(name in cameras for name in FULL_VIEWS), "Missing frozen full-character cameras")
    sys.path.insert(0, str(ROOT / "tools"))
    import build_proof as proof
    output = ROOT / "review"
    output.mkdir(exist_ok=True)
    report_path = output / "reimport_report.json"
    report = {"schema_version": 1, "status": "rendering_pending_visual_review", "created_utc": datetime.now(timezone.utc).isoformat(),
              "blender_version": bpy.app.version_string, "validation_report_sha256": digest(args.validation),
              "runtime_report_sha256": validation["stage_report_sha256"], "scene_source_sha256": digest(scene_path),
              "model_hashes": hashes, "lods": {}, "evidence": [], "motion_frames": [],
              "camera_policy": "Frozen source camera positions/targets/orthographic scales; only motion output resolution is reduced",
              "pose_policy": "Canonical rest pose for fixed views; actual exported actions for stress frames; no source comparison offsets"}
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    for lod in lods:
        assembly = assemble(args.runtime, lod)
        proof.setup_review(scene_data)
        neutral = proof.make_review_material()
        report["lods"][str(lod)] = {"modules": assembly["modules"], "bone_count": len(assembly["rig"].data.bones),
                                      "sockets": sorted(assembly["sockets"]), "actions": sorted(assembly["actions"])}
        views = FULL_VIEWS if lod == 0 else ("full_front",)
        for view in views:
            path = output / f"reimport_lod{lod}_{view}_material.png"
            record = render(cameras[view], path, args.engine, args.samples)
            report["evidence"].append(dict(record, id=f"lod{lod}_{view}", scope="equipped" if lod == 0 else "lod", view=VIEW_LABEL[view], lod=lod))
        if lod == 0:
            path = output / "reimport_lod0_full_front_neutral.png"
            record = render(cameras["full_front"], path, args.engine, args.samples, neutral=neutral)
            report["evidence"].append(dict(record, id="lod0_front_neutral", scope="neutral", view="front", lod=0))
            if not args.skip_motion:
                for name in CLIPS:
                    for fraction in (.15, .50, .85):
                        frame = set_clip(assembly, name, fraction)
                        path = output / f"reimport_motion_{name}_{int(fraction*100):02d}.png"
                        record = render(cameras["full_three_quarter"], path, args.motion_engine, args.samples, percentage=args.motion_percentage)
                        record.update(clip=name, fraction=fraction, frame=frame)
                        report["motion_frames"].append(record)
            rest_pose(assembly)
            bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "battle_prelate_reimport_review.blend"), compress=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    # Recheck bytes after rendering, so mixed revisions cannot be accepted quietly.
    check_files(args.runtime, args.validation, lods)
    require(digest(scene_path) == report["scene_source_sha256"], "Camera/scene source changed during rendering")
    report["status"] = "rendered_pending_visual_review"
    report["complete_evidence"] = set(lods) == {0,1,2} and len(report["motion_frames"]) == 27
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print("REIMPORT_REVIEW_COMPLETE " + str(report_path))


if __name__ == "__main__":
    main()
