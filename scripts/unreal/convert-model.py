"""Convert a registry-bound GLB in disposable Blender state; never publish approval.

Run with Blender --background --factory-startup --python this_file -- --profile KEY.
FBX materials, axes, sockets and animations still require an actual Unreal review.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).parent))
from equipped_source import resolve_source

import bpy
import numpy as np
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BAKE_FPS = 120
POSE_SAMPLES = 17
POSITION_TOLERANCE_METERS = 0.001
DEFORMATION_TOLERANCE = 0.001
REST_TOLERANCE_METERS = 0.0001


def digest(file_path):
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def scene_metrics():
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    return {
        "meshes": len(meshes),
        "triangles": sum(sum(len(face.vertices) - 2 for face in obj.data.polygons) for obj in meshes),
        "armatures": len([obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]),
        "joints": sum(len(obj.data.bones) for obj in bpy.context.scene.objects if obj.type == "ARMATURE"),
        "actions": sorted(action.name for action in bpy.data.actions),
        "boundsMeters": {
            "min": [min(p[i] for p in points) for i in range(3)],
            "max": [max(p[i] for p in points) for i in range(3)],
        } if points else None,
    }


def validate_source_geometry(gltf):
    """Match actual imported meshes to the source graph, excluding no names by guesswork."""
    expected = {}
    for node in gltf.get("nodes", []):
        if "mesh" not in node:
            continue
        name = node.get("name")
        if not name or name in expected:
            raise ValueError("Source mesh nodes need unique names for exact geometry verification")
        triangles = 0
        for primitive in gltf["meshes"][node["mesh"]]["primitives"]:
            if primitive.get("mode", 4) != 4:
                raise ValueError("Source geometry verification currently requires triangle primitives")
            accessor = primitive.get("indices", primitive["attributes"]["POSITION"])
            count = gltf["accessors"][accessor]["count"]
            if count % 3:
                raise ValueError("Invalid source triangle count")
            triangles += count // 3
        expected[name] = triangles
    actual = {obj.name: sum(len(face.vertices) - 2 for face in obj.data.polygons)
              for obj in bpy.context.scene.objects if obj.type == "MESH"}
    if actual != expected:
        raise ValueError(f"Imported mesh graph differs from source GLB (generated helpers are forbidden): expected {expected}, got {actual}")
    return {"meshes": len(expected), "triangles": sum(expected.values()), "meshTrianglesByNode": expected}


def rest_transforms():
    return {obj.name: obj.matrix_basis.copy() for obj in bpy.context.scene.objects}


def clear_animation(transforms):
    for obj in bpy.context.scene.objects:
        if obj.animation_data:
            obj.animation_data.action = None
            obj.animation_data.use_nla = False
            for track in obj.animation_data.nla_tracks:
                track.mute = True
        if obj.name in transforms:
            obj.matrix_basis = transforms[obj.name].copy()
        if obj.type == "ARMATURE":
            for bone in obj.pose.bones:
                bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def evaluated_snapshot():
    """World joint/deformation matrices and full evaluated mesh bounds, in Blender meters."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    bounds = {}
    joints = {}
    deformations = {}
    for obj in bpy.context.scene.objects:
        evaluated = obj.evaluated_get(depsgraph)
        if obj.type == "ARMATURE":
            for bone in evaluated.pose.bones:
                key = f"{obj.name}/{bone.name}"
                world = evaluated.matrix_world @ bone.matrix
                joints[key] = list(world.translation)
                # Remove the bind-frame orientation: FBX may legitimately reorient bone axes.
                deform = world @ bone.bone.matrix_local.inverted()
                deformations[key] = [float(deform[row][column]) for row in range(4) for column in range(4)]
        if obj.type == "MESH":
            mesh = evaluated.to_mesh()
            try:
                vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
                mesh.vertices.foreach_get("co", vertices)
                vertices = vertices.reshape((-1, 3))
                if len(vertices):
                    matrix = np.array(evaluated.matrix_world, dtype=np.float64)
                    world = vertices @ matrix[:3, :3].T + matrix[:3, 3]
                    bounds[obj.name] = {"min": world.min(axis=0).tolist(), "max": world.max(axis=0).tolist()}
            finally:
                evaluated.to_mesh_clear()
    return {"joints": joints, "deformations": deformations, "meshBoundsMeters": bounds}


def action_curves(action, slot):
    return [curve for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags if bag.slot_handle == slot.handle for curve in bag.fcurves]


def stabilize_strip_endpoint(strip):
    # Float32 glTF seconds can put an integer endpoint just below the final
    # sample. FBX then drops that frame, losing the end of walk/melee clips.
    end = strip.frame_end
    rounded = round(end)
    if 0 < rounded - end < 0.0001:
        strip.frame_end = float(rounded)


def source_clip_bindings(names):
    bindings = {name: [] for name in names}
    for obj in bpy.context.scene.objects:
        if not obj.animation_data:
            continue
        for track in obj.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.action and strip.action.name in bindings:
                    if strip.action_slot is None:
                        raise ValueError(f"Imported action has no bound slot: {strip.action.name}")
                    bindings[strip.action.name].append((obj, strip.action, strip.action_slot))
    for name, entries in bindings.items():
        if not entries:
            raise ValueError(f"Source clip is missing imported action bindings: {name}")
        # The FBX NLA exporter writes one take per strip. Do not silently split a multi-object clip.
        if len(entries) != 1:
            raise ValueError(f"Clip {name} has {len(entries)} simultaneous object bindings; separate synchronized per-clip export is required")
        if not action_curves(entries[0][1], entries[0][2]):
            raise ValueError(f"Source clip has no animation curves: {name}")
    return bindings


def imported_clip_bindings(names):
    bindings = {name: [] for name in names}
    for obj in bpy.context.scene.objects:
        for name in names:
            action = bpy.data.actions.get(f"{obj.name}|{name}")
            if action:
                if len(action.slots) != 1:
                    raise ValueError(f"Ambiguous FBX action slot for {action.name}")
                bindings[name].append((obj, action, action.slots[0]))
    return bindings


def sample_clips(bindings, transforms, sample_times=None):
    result = {}
    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    for name, entries in bindings.items():
        if not entries:
            raise ValueError(f"FBX roundtrip lost clip: {name}")
        clear_animation(transforms)
        for obj, action, slot in entries:
            obj.animation_data_create()
            obj.animation_data.action = action
            obj.animation_data.action_slot = slot
            obj.animation_data.action_blend_type = "REPLACE"
            obj.animation_data.action_influence = 1.0
        start = min(action.frame_range[0] for _, action, _ in entries)
        end = max(action.frame_range[1] for _, action, _ in entries)
        times = sample_times[name] if sample_times else [(end - start) / fps * index / (POSE_SAMPLES - 1) for index in range(POSE_SAMPLES)]
        snapshots = []
        for seconds in times:
            frame = start + seconds * fps
            bpy.context.scene.frame_set(math.floor(frame), subframe=frame - math.floor(frame))
            snapshots.append(evaluated_snapshot())
        curves = [curve for _, action, slot in entries for curve in action_curves(action, slot)]
        result[name] = {
            "durationSeconds": (end - start) / fps,
            "sampleTimesSeconds": times,
            "boundObjects": [obj.name for obj, _, _ in entries],
            "actions": [action.name for _, action, _ in entries],
            "curveCount": len(curves),
            "keyframeCount": sum(len(curve.keyframe_points) for curve in curves),
            "samples": snapshots,
        }
    clear_animation(transforms)
    return result


def compare_snapshots(before, after):
    maxima = {"jointPositionErrorMeters": 0.0, "deformationMatrixError": 0.0, "meshBoundsErrorMeters": 0.0}
    for key in ("joints", "deformations", "meshBoundsMeters"):
        if set(before[key]) != set(after[key]):
            raise ValueError(f"FBX roundtrip changed {key} identities")
    for name, position in before["joints"].items():
        maxima["jointPositionErrorMeters"] = max(maxima["jointPositionErrorMeters"], (Vector(position) - Vector(after["joints"][name])).length)
    for name, matrix in before["deformations"].items():
        maxima["deformationMatrixError"] = max(maxima["deformationMatrixError"], max(abs(a - b) for a, b in zip(matrix, after["deformations"][name])))
    for name, bounds in before["meshBoundsMeters"].items():
        maxima["meshBoundsErrorMeters"] = max(maxima["meshBoundsErrorMeters"], max(abs(a - b)
            for side in ("min", "max") for a, b in zip(bounds[side], after["meshBoundsMeters"][name][side])))
    return maxima


def validate_animation_samples(before, after):
    reports = []
    if set(before) != set(after):
        raise ValueError("FBX roundtrip changed clip names")
    for name, source in before.items():
        converted = after[name]
        if len(source["samples"]) != len(converted["samples"]) or source["sampleTimesSeconds"] != converted["sampleTimesSeconds"]:
            raise ValueError(f"FBX sample coverage changed for {name}")
        if abs(source["durationSeconds"] - converted["durationSeconds"]) > 1.0 / BAKE_FPS + 1e-6:
            raise ValueError(f"FBX roundtrip changed duration of {name}")
        if not set(source["boundObjects"]).issubset(converted["boundObjects"]):
            raise ValueError(f"FBX roundtrip lost animated objects for {name}")
        if converted["curveCount"] == 0 or converted["keyframeCount"] == 0:
            raise ValueError(f"FBX roundtrip lost animation curves for {name}")
        deltas = [compare_snapshots(a, b) for a, b in zip(source["samples"], converted["samples"])]
        maximum = {key: max(delta[key] for delta in deltas) for key in deltas[0]}
        if (maximum["jointPositionErrorMeters"] > POSITION_TOLERANCE_METERS
                or maximum["meshBoundsErrorMeters"] > POSITION_TOLERANCE_METERS
                or maximum["deformationMatrixError"] > DEFORMATION_TOLERANCE):
            raise ValueError(f"FBX sampled pose mismatch for {name}: {maximum}")
        # This catches a baked static pose even if both sides retain nonempty curve lists.
        movement = [compare_snapshots(source["samples"][0], sample) for sample in source["samples"][1:]]
        reports.append({
            "name": name, "status": "passed", "sampleCount": len(source["samples"]),
            "sampleTimesSeconds": source["sampleTimesSeconds"],
            "sourceDurationSeconds": source["durationSeconds"], "convertedDurationSeconds": converted["durationSeconds"],
            "sourceCurveCount": source["curveCount"], "convertedCurveCount": converted["curveCount"],
            "sourceKeyframeCount": source["keyframeCount"], "convertedKeyframeCount": converted["keyframeCount"],
            "convertedActions": converted["actions"],
            "sourceMaximumJointMotionMeters": max(delta["jointPositionErrorMeters"] for delta in movement),
            **maximum,
        })
    return reports


def fbx_global_settings(file_path):
    from io_scene_fbx import parse_fbx
    root, version = parse_fbx.parse(str(file_path))
    settings = next(element for element in root.elems if element.id == b"GlobalSettings")
    properties = next(element for element in settings.elems if element.id == b"Properties70")
    wanted = {"UnitScaleFactor", "OriginalUnitScaleFactor", "UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign"}
    values = {entry.props[0].decode(): entry.props[-1] for entry in properties.elems if entry.id == b"P" and entry.props[0].decode() in wanted}
    # FBX_SCALE_NONE bakes Blender's meter-to-centimeter factor into exported
    # transforms and declares one centimeter per file unit. Roundtrip world
    # bounds below independently verify that this did not alter physical size.
    if abs(values.get("UnitScaleFactor", 0) - 1.0) > 1e-6 or values.get("UpAxis") != 2 or values.get("UpAxisSign") != 1:
        raise ValueError(f"Unexpected FBX unit or up-axis metadata: {values}")
    return {"fbxVersion": version, **values}


def main():
    global BAKE_FPS
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--verify-existing", action="store_true", help="Validate retained FBX bytes after lossless track removal without re-exporting model data")
    parser.add_argument("--bake-fps", type=int, choices=(120, 240, 480), default=120)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    BAKE_FPS = args.bake_fps
    registry = json.loads((ROOT / "public/assets/models/asset-index.json").read_text(encoding="utf-8"))
    rows = [(kind, registry.get(kind, {}).get(args.profile)) for kind in ("characterProfiles", "staticProps", "equipment")]
    rows = [(kind, row) for kind, row in rows if row is not None]
    if len(rows) != 1:
        raise ValueError("Profile must identify exactly one registered character, prop or equipment asset")
    kind, record = rows[0]
    if record.get("approvalState") != "approved" or not record.get("runtimeReady"):
        raise ValueError("Only an approved repository source may enter the conversion experiment")
    source, qc, source_hash, qc_hash = resolve_source(ROOT, kind, args.profile, record, registry)
    reviews = json.loads((ROOT / "migration/visual-reviews.json").read_text(encoding="utf-8"))
    if reviews.get("schemaVersion") != 1:
        raise ValueError("Unsupported visual review schema")
    if any(review["status"] == "rejected" and review["sourceSha256"] == digest(source) for review in reviews["reviews"]):
        raise ValueError("Source failed the nonprimitive visual review; replacement is required")
    if source.suffix.lower() != ".glb" or digest(source) != source_hash:
        raise ValueError("Source GLB bytes do not match the registered source hash")
    if digest(qc) != qc_hash:
        raise ValueError("Source QC bytes do not match the registered QC hash")
    data = source.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF" or struct.unpack_from("<II", data, 4) != (2, len(data)):
        raise ValueError("Invalid GLB source")
    json_size, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A or 20 + json_size > len(data):
        raise ValueError("Invalid GLB JSON chunk")
    gltf = json.loads(data[20:20 + json_size])
    for reference in gltf.get("images", []) + gltf.get("buffers", []):
        uri = reference.get("uri", "")
        if uri and not uri.startswith("data:"):
            from urllib.parse import unquote, urlparse
            if urlparse(uri).scheme or urlparse(uri).netloc:
                raise ValueError("Remote dependencies are not allowed")
            dependency = (source.parent / unquote(uri)).resolve()
            dependency.relative_to((ROOT / "public/assets").resolve())
            if not dependency.is_file():
                raise ValueError(f"Missing source dependency: {uri}")
    if kind == "characterProfiles" and not gltf.get("skins"):
        raise ValueError("Character conversion requires authored skinned geometry")
    if kind == "characterProfiles" and gltf.get("animations"):
        raise ValueError("Strip character source tracks first; motion is imported separately from supplied FBXs")
    names = [animation.get("name") for animation in gltf.get("animations", [])]
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
        raise ValueError("Source animations require unique nonempty names for auditable FBX take mapping")
    if any(channel["target"]["path"] == "weights" for animation in gltf.get("animations", []) for channel in animation["channels"]):
        raise ValueError("Animated morph-weight conversion needs a separate verified shape-key path")
    output_dir = ROOT / "artifacts/unreal/converted" / args.profile
    # Profile keys become a directory, never an arbitrary output path.
    if not args.profile or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in args.profile):
        raise ValueError("Unsafe profile key")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{args.profile}.fbx"
    receipt_path = output_dir / "conversion.json"
    # An interrupted or failed re-run must not leave an earlier success receipt beside new bytes.
    receipt_path.unlink(missing_ok=True)
    old_import = output_dir / "editor-import.json"
    if args.verify_existing and old_import.exists():
        history = output_dir / "historical-editor-import.json"
        if not history.exists(): history.write_bytes(old_import.read_bytes())
    old_import.unlink(missing_ok=True)
    binding_path = ROOT / "unreal/AegisWar/Content/Migration/visual-imports.json"
    if binding_path.exists() and not args.verify_existing:
        bindings = json.loads(binding_path.read_text(encoding="utf-8"))
        if bindings.get("schemaVersion") != 1 or not isinstance(bindings.get("entries"), list):
            raise ValueError("Cannot invalidate an unsupported visual import registry")
        bindings["entries"] = [entry for entry in bindings["entries"] if entry["profileKey"] != args.profile]
        temporary = binding_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(bindings, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(binding_path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = BAKE_FPS
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0
    # Blender's glTF importer otherwise creates an Icosphere bone-display helper
    # in a hidden collection. That helper is not present in the source GLB and
    # FBX's scene export would include it despite the hidden collection.
    bpy.ops.import_scene.gltf(filepath=str(source), disable_bone_shape=True)
    source_geometry = validate_source_geometry(gltf)
    source_bindings = source_clip_bindings(names)
    source_transforms = rest_transforms()
    clear_animation(source_transforms)
    before = scene_metrics()
    before_rest = evaluated_snapshot()
    if not before["meshes"] or (kind == "characterProfiles" and not before["armatures"]):
        raise ValueError("Imported scene is missing required model geometry or rig")
    before_clips = sample_clips(source_bindings, source_transforms)
    for obj in bpy.context.scene.objects:
        if obj.animation_data:
            obj.animation_data.use_nla = True
            for track in obj.animation_data.nla_tracks:
                # glTF deliberately stashes imported clips in muted NLA tracks. The FBX
                # exporter skips muted tracks, then isolates each unmuted strip itself.
                track.mute = False
                for strip in track.strips:
                    strip.mute = False
                    stabilize_strip_endpoint(strip)
    if not args.verify_existing:
        bpy.ops.export_scene.fbx(
            filepath=str(output), use_selection=False, object_types={"MESH", "ARMATURE", "EMPTY"},
            axis_forward="-Y", axis_up="Z", global_scale=1.0, apply_unit_scale=True,
            apply_scale_options="FBX_SCALE_NONE",
            add_leaf_bones=False, use_armature_deform_only=False, use_triangles=True,
            bake_anim=bool(gltf.get("animations")), bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=False, bake_anim_simplify_factor=0.0, bake_anim_step=1.0,
            path_mode="COPY", embed_textures=True,
        )
    global_settings = fbx_global_settings(output)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(output), anim_offset=0.0, automatic_bone_orientation=False)
    imported_bindings = imported_clip_bindings(names)
    imported_transforms = rest_transforms()
    clear_animation(imported_transforms)
    after = scene_metrics()
    validate_source_geometry(gltf)
    after_rest = evaluated_snapshot()
    if after["meshes"] != before["meshes"] or after["triangles"] != before["triangles"]:
        raise ValueError("FBX roundtrip changed mesh or triangle counts")
    if before["joints"] != after["joints"]:
        raise ValueError("FBX roundtrip changed joint count")
    rest_deltas = compare_snapshots(before_rest, after_rest)
    if rest_deltas["jointPositionErrorMeters"] > REST_TOLERANCE_METERS or rest_deltas["meshBoundsErrorMeters"] > REST_TOLERANCE_METERS:
        raise ValueError(f"FBX roundtrip changed bind-pose placement or meter bounds: {rest_deltas}")
    after_clips = sample_clips(imported_bindings, imported_transforms, {name: entry["sampleTimesSeconds"] for name, entry in before_clips.items()})
    animation_checks = validate_animation_samples(before_clips, after_clips)
    if digest(source) != source_hash or digest(qc) != qc_hash:
        raise ValueError("Registered source or QC bytes changed while conversion was running")
    samples_path = output_dir / "animation-samples.json"
    samples_path.write_text(json.dumps({"restSource": before_rest, "source": before_clips, "converted": after_clips}, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    receipt = {
        "schemaVersion": 1, "profileKey": args.profile, "kind": kind,
        "status": "converted-unverified-in-unreal", "unrealApproved": False,
        "source": source.relative_to(ROOT).as_posix(), "sourceSha256": digest(source),
        "qcSha256": digest(qc), "output": output.relative_to(ROOT).as_posix(),
        "outputSha256": digest(output), "blenderVersion": bpy.app.version_string,
        "sourceAnimationNames": names,
        "sourceGeometry": source_geometry,
        "before": before, "after": after,
        "verification": {
            "status": "blender-roundtrip-passed", "bakeFramesPerSecond": BAKE_FPS,
            "fbxGlobalSettings": global_settings, "restPose": rest_deltas,
            "restSourceMeshBoundsMeters": before_rest["meshBoundsMeters"],
            "restConvertedMeshBoundsMeters": after_rest["meshBoundsMeters"],
            "animations": animation_checks,
            "sampleEvidence": samples_path.relative_to(ROOT).as_posix(), "sampleEvidenceSha256": digest(samples_path),
            "tolerances": {"restMeters": REST_TOLERANCE_METERS, "poseMeters": POSITION_TOLERANCE_METERS, "deformationMatrix": DEFORMATION_TOLERANCE},
        },
        "limitations": [
            "Blender FBX roundtrip is not an Unreal import or visual acceptance test.",
            "Verify centimeter scale, axes, rig bind pose, each animation, PBR reconstruction, LODs, sockets and collision in Unreal.",
            "This conversion does not assign an NPC visual to a playable class or approve a new character variant.",
        ],
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("UNREAL_CONVERSION_RECEIPT=" + str(receipt_path))


if __name__ == "__main__":
    main()
