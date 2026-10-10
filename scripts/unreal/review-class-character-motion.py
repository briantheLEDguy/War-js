"""Blender: sample supplied choreography on draft bodies without publishing clips.

This source-space review reuses the supplied-set inventory and chain contract.
Native IK retargeting, equipped motion, contacts and role selection remain with
animation-pipeline.py; this script cannot install or approve a character.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from animation_replacement import CLIPS, ROOT, SOURCE, CHAINS

MAPPING = {"Hips": "hips", "Spine": "spine", "Spine1": "chest", "Spine2": "upper_chest", "Neck": "neck", "Head": "head"}
for side, suffix in (("Left", "L"), ("Right", "R")):
    for source, target in (("Shoulder", "shoulder"), ("Arm", "upper_arm"), ("ForeArm", "forearm"), ("Hand", "hand"),
                           ("UpLeg", "thigh"), ("Leg", "shin"), ("Foot", "foot"), ("ToeBase", "toe")):
        MAPPING[side + source] = target + "_" + suffix
    for finger in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
        for segment in range(1, 4):
            MAPPING[f"{side}Hand{finger}{segment}"] = f"{finger.lower()}_{segment:02}_{suffix}"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_samples(run):
    for _, start, end, target_start, target_end in CHAINS:
        if MAPPING[start] != target_start or MAPPING[end] != target_end:
            raise RuntimeError("Diagnostic bone mapping differs from the native anatomical chain contract")
    inventory = json.loads((ROOT / "artifacts/unreal/animation-replacement/sources.json").read_text())["clips"]
    result = {}
    # All bodies are reviewed with the same templates. These are diagnostic
    # choices, never a class's live animation or ability presentation decision.
    for key in ("two.walk", "two.run", "two.slash", "shield.walk", "shield.slash", "spell.bolt"):
        path = SOURCE / CLIPS[key]
        if inventory[key]["sha256"] != sha(path):
            raise RuntimeError("Supplied source changed after its approved inventory: " + key)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
        rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
        names = {bone.name.split(":")[-1]: bone.name for bone in rig.data.bones}
        missing = set(MAPPING) - set(names)
        if missing:
            raise RuntimeError(f"Missing supplied anatomical bones: {missing}")
        world = rig.matrix_world.to_quaternion()
        rest = {target: world @ rig.data.bones[names[name]].matrix_local.to_quaternion() for name, target in MAPPING.items()}
        first, last = rig.animation_data.action.frame_range
        samples = []
        for index in range(17):
            frame = first + (last - first) * index / 16
            bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
            samples.append({target: world @ rig.pose.bones[names[name]].matrix.to_quaternion() for name, target in MAPPING.items()})
        result[key] = dict(rest=rest, samples=samples, sha256=sha(path), file=CLIPS[key])
    return result


def review(directory, templates, optimized=False):
    from class_character_audit import deformation_checks
    import numpy as np

    receipt_file = directory / "receipt.json"
    receipt = json.loads(receipt_file.read_text())
    if not receipt["technicalPassed"]:
        raise RuntimeError("Body technical checks must pass before motion review")
    for file in receipt["files"]:
        if Path(file["path"]).name != file["path"]:
            raise RuntimeError("Unsafe body evidence path")
        if sha(directory / file["path"]) != file["sha256"]:
            raise RuntimeError("Draft evidence changed: " + file["path"])
    candidate = directory / "optimized-v2" if optimized else directory
    atlas_receipt = candidate / "review.json" if optimized else None
    if optimized:
        atlas = json.loads(atlas_receipt.read_text())
        if not atlas["passed"] or atlas["sourceReceiptSha256"] != sha(receipt_file):
            raise RuntimeError("Invalid derived atlas source")
        for file in atlas["files"]:
            if Path(file["path"]).name != file["path"] or sha(candidate / file["path"]) != file["sha256"]:
                raise RuntimeError("Derived atlas evidence changed")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(candidate / "body.glb"))
    rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    body = next(obj for obj in meshes if obj.name.startswith("Body_"))
    world = rig.matrix_world.to_quaternion()
    rest = {bone.name: bone.matrix_local.to_quaternion() for bone in rig.data.bones}
    ordered = list(rig.data.bones)
    edges = np.array([list(edge.vertices) for edge in body.data.edges], dtype=np.int32)

    def coordinates():
        bpy.context.view_layer.update()
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        geometry = evaluated.to_mesh()
        try:
            points = np.empty(len(geometry.vertices) * 3)
            geometry.vertices.foreach_get("co", points)
            return points.reshape((-1, 3))
        finally:
            evaluated.to_mesh_clear()

    neutral = coordinates()
    lengths = np.linalg.norm(neutral[edges[:, 0]] - neutral[edges[:, 1]], axis=1)
    valid = lengths > 1e-5
    height = float(np.ptp(neutral[:, 2]))
    output = candidate / "supplied-motion"
    output.mkdir(exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 640, 800
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new("ClassMotionReviewWorld")
    scene.world.color = (.055, .055, .055)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = -1.1
    camera_data = bpy.data.cameras.new("SuppliedPoseReview")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = height * 1.35
    camera = bpy.data.objects.new("SuppliedPoseReview", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    center = Vector((0, 0, height * .5))
    camera.location = center + Vector((3.2, -5, height * .05))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    for position, energy in (((-3, -4, 4), 600), ((3, -2, 2), 250), ((1, 3, 3), 450)):
        data = bpy.data.lights.new("ReviewArea", "AREA")
        data.energy, data.size = energy, 3
        obj = bpy.data.objects.new("ReviewArea", data)
        scene.collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(output / "imported-rest.png")
    bpy.ops.render.render(write_still=True)
    clips = {}
    for key, template in templates.items():
        aligned = {}
        for name, source_rest in template["rest"].items():
            target_rest = world @ rest[name]
            source_direction = source_rest @ Vector((0, 1, 0))
            target_direction = target_rest @ Vector((0, 1, 0))
            aligned[name] = source_direction.rotation_difference(target_direction).inverted() @ target_rest
        measured = []
        def apply_sample(sample):
            orientations = {}
            for bone in ordered:
                name = bone.name
                parent_rest = rest[bone.parent.name] if bone.parent else Quaternion()
                parent_pose = orientations[bone.parent.name] if bone.parent else Quaternion()
                if name in sample:
                    desired = world.inverted() @ (sample[name] @ template["rest"][name].inverted() @ aligned[name])
                else:
                    desired = parent_pose @ parent_rest.inverted() @ rest[name]
                orientations[name] = desired
                pose = rig.pose.bones[name]
                pose.rotation_mode = "QUATERNION"
                pose.rotation_quaternion = rest[name].inverted() @ parent_rest @ parent_pose.inverted() @ desired
        for index, sample in enumerate(template["samples"]):
            apply_sample(sample)
            points = coordinates()
            current = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
            ratios = np.sort(current[valid] / lengths[valid])
            row = dict(finite=bool(np.isfinite(points).all()), maxEdgeExtensionM=float(np.max(current - lengths)),
                       p01EdgeRatio=float(np.quantile(ratios, .01)), p99EdgeRatio=float(np.quantile(ratios, .99)))
            worst = int(np.argmax(current - lengths))
            row["worstEdgeRestPosition"] = neutral[edges[worst, 0]].tolist()
            row["passed"] = deformation_checks(row, height)
            measured.append(row)
            if index == 8:
                scene.render.filepath = str(output / (key + ".png"))
                bpy.ops.render.render(write_still=True)
        worst_index = max(range(len(measured)), key=lambda index: measured[index]["maxEdgeExtensionM"])
        apply_sample(template["samples"][worst_index])
        scene.render.filepath = str(output / (key + "-worst.png"))
        bpy.ops.render.render(write_still=True)
        clips[key] = dict(file=template["file"], sourceSha256=template["sha256"], samples=measured,
                          worstSample=worst_index, passed=all(row["passed"] for row in measured))
    report = dict(schemaVersion=1, bodyReceiptSha256=sha(receipt_file), modelSha256=sha(candidate / "body.glb"),
        atlasReceiptSha256=sha(atlas_receipt) if optimized else None, modelRelativePath="optimized-v2/body.glb" if optimized else "body.glb",
        sourceToolSha256=sha(__file__), chainContractSha256=sha(TOOLS / "animation_replacement.py"),
        deformationAuditSha256=sha(TOOLS / "class_character_audit.py"),
        method="source_world_rotation_with_rest_direction_alignment_fixed_target_lengths",
        passed=all(clip["passed"] for clip in clips.values()), clips=clips, runtimeEligible=False, nativeAccepted=False,
        limitations=["Unreal IK, foot locking, armor, equipment, contacts and live class motion remain unverified.",
                     "Source-space rotation review holds the pelvis in place; it does not approve capsule motion."])
    report["renders"] = [{"path": file.name, "sha256": sha(file)} for file in sorted(output.glob("*.png"))]
    (output / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    return report["passed"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--character")
    parser.add_argument("--optimized", action="store_true")
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--shard", type=int, default=0)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    run = Path(args.run).resolve()
    run.relative_to(ROOT / "artifacts/unreal/class-characters")
    if not 0 <= args.shard < args.shards <= 4:
        raise RuntimeError("Invalid shard selection")
    templates = source_samples(run)
    rows = {}
    directories = [directory for directory in sorted(run.iterdir()) if (directory / "receipt.json").exists()]
    for index, directory in enumerate(directories):
        if index % args.shards != args.shard or args.character and directory.name != args.character:
            continue
        rows[directory.name] = review(directory, templates, args.optimized)
        report_name = "supplied-motion-report.json" if args.shards == 1 else f"supplied-motion-report-{args.shard}.json"
        (run / report_name).write_text(json.dumps(dict(characters=rows, nativeAccepted=False, runtimeEligible=False), indent=2) + "\n")
        print("WAR_CLASS_SOURCE_POSE", directory.name, rows[directory.name], flush=True)
    if not rows or not all(rows.values()):
        raise RuntimeError("Supplied pose review incomplete or failed; inspect supplied-motion reports")


if __name__ == "__main__":
    main()
