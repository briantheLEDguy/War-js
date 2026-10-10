"""Derive Greenskin dentition from verified bodies without replacing their sources."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).parent
sys.path.insert(0, str(TOOLS))
from class_character_audit import build_audit, deformation_checks, weight_checks
from class_character_dentition import enamel_point, jaw_weights, split_crowns, surface_signature


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


atlas = module("dentition_atlas", "atlas-class-characters.py")
motion = module("dentition_motion", "review-class-character-motion.py")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_files(directory, receipt):
    if not receipt["passed"] or receipt["nativeAccepted"] is not False or receipt["runtimeEligible"] is not False:
        raise RuntimeError("Expected a verified draft source")
    for item in receipt["files"]:
        if Path(item["path"]).name != item["path"] or sha(directory / item["path"]) != item["sha256"]:
            raise RuntimeError("Changed or unsafe dentition source evidence")


def components(mesh):
    adjacency = [[] for _ in mesh.data.vertices]
    for edge in mesh.data.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    unseen = set(range(len(adjacency)))
    result = []
    while unseen:
        start = unseen.pop()
        island, pending = [start], [start]
        while pending:
            for index in adjacency[pending.pop()]:
                if index in unseen:
                    unseen.remove(index)
                    island.append(index)
                    pending.append(index)
        result.append(island)
    return result


def bind(mesh, rig, indices, weights):
    groups = {group.name: group for group in mesh.vertex_groups if group.name in rig.data.bones}
    for group in groups.values():
        group.remove(indices)
    for name, value in weights.items():
        group = groups.get(name) or mesh.vertex_groups.new(name=name)
        group.add(indices, value, "REPLACE")


def fitted_body_positions(directory):
    bpy.ops.wm.open_mainfile(filepath=str(directory / "fitting-source.blend"))
    body = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("Body_"))
    if len(body.data.vertices) != 19158:
        raise RuntimeError("Live fitting topology changed")
    keys = body.data.shape_keys.key_blocks
    basis = np.array([list(vertex.co) for vertex in keys[0].data])
    mixed = basis.copy()
    for key in list(keys)[1:]:
        mixed += (np.array([list(vertex.co) for vertex in key.data])-basis)*key.value
    # Preview mask modifiers strip helpers and can reorder evaluated indices.
    # Retain the original fitting index contract before matching runtime seams.
    return [body.matrix_world @ Vector(position) for position in mixed[:13380]]


def fit_jaw(body, rig, positions):
    weights_file = TOOLS / "class-character-jaw-weights.json"
    source = json.loads(weights_file.read_text())
    if source["license"] != "CC0" or source["sourceBodyVertices"] != len(positions):
        raise RuntimeError("Unexpected facial weight source")
    values = dict(source["weights"])
    tree = KDTree(len(positions))
    for index, position in enumerate(positions):
        tree.insert(position, index)
    tree.balance()
    count, maximum_distance = 0, 0
    for vertex in body.data.vertices:
        _, index, distance = tree.find(body.matrix_world @ vertex.co)
        if distance > 1e-5:
            raise RuntimeError("Facial source does not match the exported body")
        maximum_distance = max(maximum_distance, distance)
        amount = values.get(index, 0)
        if amount <= 1e-8:
            continue
        original = {body.vertex_groups[item.group].name: item.weight for item in vertex.groups
                    if body.vertex_groups[item.group].name in rig.data.bones and item.weight > 1e-8}
        bind(body, rig, [vertex.index], jaw_weights(original, amount))
        count += 1
    return dict(sourceSha256=sha(weights_file), changedRuntimeVertices=count,
                maximumSourceDistanceM=maximum_distance, method="cc0_default_jaw_descendants_on_welded_fitting_surface")


def fit_teeth(face, body, rig, stature):
    islands = components(face)
    points = [face.matrix_world @ vertex.co for vertex in face.data.vertices]
    tusks = [island for island in islands if len(island) == 193]
    crowns = [island for island in islands if len(island) in (71, 72, 74, 76)]
    if len(tusks) != 2:
        raise RuntimeError("Expected exactly two retained canine surfaces")
    centers = [sum((points[index] for index in island), Vector()) / len(island) for island in crowns]
    vertex_uvs = [[] for _ in face.data.vertices]
    for loop in face.data.loops:
        vertex_uvs[loop.vertex_index].append(face.data.uv_layers.active.data[loop.index].uv)
    bounds = []
    for island in crowns:
        values = [uv for index in island for uv in vertex_uvs[index]]
        bounds.append([min(uv.x for uv in values), max(uv.x for uv in values),
                       min(uv.y for uv in values), max(uv.y for uv in values)])
    contract = json.loads((TOOLS / "class-character-jaw-weights.json").read_text())["dentalCrownUvContract"]
    lower = split_crowns(bounds, contract)
    for island, is_lower in zip(crowns, lower):
        bind(face, rig, island, {"jaw" if is_lower else "head": 1.0})
    lower_gums = [island for island in islands if len(island) in (216, 318)]
    tongues = [island for island in islands if len(island) == 253]
    if len(lower_gums) != 4 or len(tongues) != 1:
        raise RuntimeError("Retained gum/tongue topology changed")
    for island in [*lower_gums, *tongues]:
        bind(face, rig, island, {"jaw": 1.0})
    # Retained gum surfaces share the enamel material. Use the atlas's unused
    # fourth tile for gum colour, preserving the three-draw material contract.
    gums = {index for island in islands if len(island) in (216, 318, 228, 306) for index in island}
    shader = next(node for node in face.data.materials[0].node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    for channel, rgba in (("Base Color", (.23, .28, .245, 1)), ("Normal", (.5, .5, 1, 1)),
                          ("Roughness", (1, .72, 0, 1))):
        image = atlas.upstream_image(shader.inputs[channel])
        pixels = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(pixels)
        pixels = pixels.reshape((image.size[1], image.size[0], 4))
        pixels[1024:, 1024:] = rgba
        image.pixels.foreach_set(pixels.ravel())
        image.update()
        image.pack()
    for polygon in face.data.polygons:
        if all(index in gums for index in polygon.vertices):
            for loop in polygon.loop_indices:
                face.data.uv_layers.active.data[loop].uv = (.75, .75)
    surface = BVHTree.FromPolygons([body.matrix_world @ vertex.co for vertex in body.data.vertices],
                                  [list(polygon.vertices) for polygon in body.data.polygons])
    inverse = face.matrix_world.inverted()
    fitted = []
    for island in tusks:
        old = [points[index] for index in island]
        bottom, top = min(point.z for point in old), max(point.z for point in old)
        old_height = top - bottom
        if abs(old_height - stature * .018) > 1e-5:
            raise RuntimeError("Retained canine profile differs from its source recipe")
        base = [point for point in old if abs(point.z-bottom) < 1e-6]
        if len(base) != 16:
            raise RuntimeError("Retained canine root topology changed")
        old_root = sum(base, Vector()) / len(base)
        side = 1 if old_root.x > 0 else -1
        options = [(island, center) for island, center, is_lower in zip(crowns, centers, lower)
                   if is_lower and center.x * side > 0 and len(island) == 74]
        if len(options) != 1:
            raise RuntimeError("Expected one fitted lower canine crown per side")
        crown, center = options[0]
        root = Vector((center.x, center.y, min(points[index].z for index in crown) - stature * .001))
        height = stature * .019
        lip = surface.ray_cast(Vector((root.x, -1, root.z + stature*.005)), Vector((0, 1, 0)))[0]
        if lip is None or not .006 < root.y-lip.y < .035:
            raise RuntimeError("Canine root is not behind the fitted lower lip")
        front_y = lip.y - stature*.006
        for index in island:
            point = points[index]
            t = min(1.0, max(0.0, (point.z-bottom)/old_height))
            old_center_x = old_root.x + side*old_height*.10*t*t
            old_center_y = old_root.y - old_height*(.32*t-.10*t*t)
            angle = math.atan2((point.y-old_center_y)/.8, point.x-old_center_x)
            face.data.vertices[index].co = inverse @ Vector(enamel_point(side, root, height, front_y, t, angle))
        bind(face, rig, island, {"jaw": 1.0})
        fitted.append(dict(side=side, rootM=list(root), heightM=height, lipPointM=list(lip),
                           rootBehindLipM=root.y-lip.y, frontYM=front_y))
    for polygon in face.data.polygons:
        polygon.use_smooth = True
    face.data.normals_split_custom_set([(0, 0, 0)] * len(face.data.loops))
    face.data.update()
    return dict(canines=fitted, lowerCrowns=sum(lower), lowerGumIslands=len(lower_gums), tongueIslands=len(tongues))


def portraits(output, rig, height, prefix, angles=(0, 12, 24)):
    scene = bpy.context.scene
    camera = scene.camera
    camera.data.ortho_scale = height * .22
    target = Vector((0, -.07, height * .925))
    jaw = rig.data.bones["jaw"]
    axis = (rig.matrix_world.to_3x3() @ jaw.matrix_local.to_3x3()).inverted() @ Vector((1, 0, 0))
    for degrees in angles:
        rig.pose.bones["jaw"].rotation_mode = "QUATERNION"
        rig.pose.bones["jaw"].rotation_quaternion = Quaternion(axis.normalized(), math.radians(degrees))
        for label, offset in (("front", (0, -2, 0)), ("three-quarter", (1.25, -2, 0)), ("profile", (2, 0, 0))):
            camera.location = target + Vector(offset)
            camera.rotation_euler = (target-camera.location).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(output / f"{prefix}-{degrees}-{label}.png")
            bpy.ops.render.render(write_still=True)
    rig.pose.bones["jaw"].matrix_basis = Matrix.Identity(4)


def check_jaw(body, face, rig, teeth_evidence):
    """Check actual exported skinning, root coverage and lower-face deformation."""
    def coordinates(mesh):
        bpy.context.view_layer.update()
        evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        geometry = evaluated.to_mesh()
        try:
            return [mesh.matrix_world @ vertex.co for vertex in geometry.vertices]
        finally:
            evaluated.to_mesh_clear()
    neutral_body, neutral_face = coordinates(body), coordinates(face)
    height = max(point.z for point in neutral_body)-min(point.z for point in neutral_body)
    edges = [list(edge.vertices) for edge in body.data.edges]
    lengths = np.array([(neutral_body[a]-neutral_body[b]).length for a, b in edges])
    jaw_group = face.vertex_groups["jaw"].index
    indices = [vertex.index for vertex in face.data.vertices if sum(
        item.weight for item in vertex.groups if item.group == jaw_group) > 1-1e-6]
    jaw = rig.data.bones["jaw"]
    axis = (rig.matrix_world.to_3x3() @ jaw.matrix_local.to_3x3()).inverted() @ Vector((1, 0, 0))
    rows = []
    for degrees in (0, 12, 24):
        pose = rig.pose.bones["jaw"]
        pose.rotation_mode = "QUATERNION"
        pose.rotation_quaternion = Quaternion(axis.normalized(), math.radians(degrees))
        actual_body, actual_face = coordinates(body), coordinates(face)
        transform = rig.matrix_world @ pose.matrix @ jaw.matrix_local.inverted() @ rig.matrix_world.inverted()
        error = max((actual_face[index]-transform @ neutral_face[index]).length for index in indices)
        surface = BVHTree.FromPolygons(actual_body, [list(polygon.vertices) for polygon in body.data.polygons])
        roots = []
        for canine in teeth_evidence["canines"]:
            root = transform @ Vector(canine["rootM"])
            hit = surface.ray_cast(Vector((root.x, -1, root.z)), Vector((0, 1, 0)))[0]
            roots.append(None if hit is None else root.y-hit.y)
        current = np.array([(actual_body[a]-actual_body[b]).length for a, b in edges])
        ratios = current[lengths > 1e-5]/lengths[lengths > 1e-5]
        row = dict(degrees=degrees, rigidDentalSkinErrorM=error, rootBehindSurfaceM=roots,
                   finite=all(math.isfinite(value) for point in actual_body for value in point),
                   maxEdgeExtensionM=float(np.max(current-lengths)), p01EdgeRatio=float(np.quantile(ratios, .01)),
                   p99EdgeRatio=float(np.quantile(ratios, .99)))
        row["passed"] = (error < 1e-5 and all(value is not None and value > .003 for value in roots)
                         and deformation_checks(row, height))
        rows.append(row)
    rig.pose.bones["jaw"].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    return rows


def evaluate_motion(output, rig, body, templates):
    scene = bpy.context.scene
    camera = scene.camera
    height = max(vertex.co.z for vertex in body.data.vertices)-min(vertex.co.z for vertex in body.data.vertices)
    center = Vector((0, 0, height*.52))
    camera.location, camera.data.ortho_scale = center+Vector((4, -5, .05)), height*1.21
    camera.rotation_euler = (center-camera.location).to_track_quat("-Z", "Y").to_euler()
    world = rig.matrix_world.to_quaternion()
    rest = {bone.name: bone.matrix_local.to_quaternion() for bone in rig.data.bones}
    edges = np.array([list(edge.vertices) for edge in body.data.edges])
    def coordinates():
        bpy.context.view_layer.update()
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        geometry = evaluated.to_mesh()
        try:
            points = np.empty(len(geometry.vertices)*3)
            geometry.vertices.foreach_get("co", points)
            return points.reshape((-1, 3))
        finally:
            evaluated.to_mesh_clear()
    neutral = coordinates()
    lengths = np.linalg.norm(neutral[edges[:, 0]]-neutral[edges[:, 1]], axis=1)
    valid = lengths > 1e-5
    clips = {}
    for key, template in templates.items():
        aligned = {name: (source_rest @ Vector((0, 1, 0))).rotation_difference(
            world @ rest[name] @ Vector((0, 1, 0))).inverted() @ world @ rest[name]
            for name, source_rest in template["rest"].items()}
        def apply(sample):
            orientations = {}
            for bone in rig.data.bones:
                name = bone.name
                parent_rest = rest[bone.parent.name] if bone.parent else Quaternion()
                parent_pose = orientations[bone.parent.name] if bone.parent else Quaternion()
                desired = (world.inverted() @ (sample[name] @ template["rest"][name].inverted() @ aligned[name])
                           if name in sample else parent_pose @ parent_rest.inverted() @ rest[name])
                orientations[name] = desired
                pose = rig.pose.bones[name]
                pose.rotation_mode = "QUATERNION"
                pose.rotation_quaternion = rest[name].inverted() @ parent_rest @ parent_pose.inverted() @ desired
        measured = []
        for index, sample in enumerate(template["samples"]):
            apply(sample)
            points = coordinates()
            current = np.linalg.norm(points[edges[:, 0]]-points[edges[:, 1]], axis=1)
            ratios = current[valid]/lengths[valid]
            row = dict(finite=bool(np.isfinite(points).all()), maxEdgeExtensionM=float(np.max(current-lengths)),
                       p01EdgeRatio=float(np.quantile(ratios, .01)), p99EdgeRatio=float(np.quantile(ratios, .99)))
            row["passed"] = deformation_checks(row, height)
            measured.append(row)
            if index == 8:
                scene.render.filepath = str(output / (key+".png"))
                bpy.ops.render.render(write_still=True)
        worst = max(range(len(measured)), key=lambda index: measured[index]["maxEdgeExtensionM"])
        apply(template["samples"][worst])
        scene.render.filepath = str(output / (key+"-worst.png"))
        bpy.ops.render.render(write_still=True)
        clips[key] = dict(file=template["file"], sourceSha256=template["sha256"], samples=measured,
                          worstSample=worst, passed=all(row["passed"] for row in measured))
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    return clips


def fit(directory, templates):
    request = json.loads((directory / "request.json").read_text())
    if request["race"] != "greenskin":
        raise RuntimeError("Dentition adaptation is specific to Greenskin bodies")
    source = directory / "optimized-v2"
    source_receipt = json.loads((source / "review.json").read_text())
    verify_files(source, source_receipt)
    raw = json.loads((directory / "receipt.json").read_text())
    fitting = next(item for item in raw["files"] if item["path"] == "fitting-source.blend")
    if (raw["technicalPassed"] is not True or raw["nativeAccepted"] is not False
            or raw["runtimeEligible"] is not False
            or source_receipt["sourceReceiptSha256"] != sha(directory / "receipt.json")
            or fitting["sha256"] != sha(directory / fitting["path"])):
        raise RuntimeError("Changed live fitting source or source receipt")
    positions = fitted_body_positions(directory)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source / "body.glb"))
    rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    meshes = atlas.skinned_meshes(rig)
    body = next(obj for obj in meshes if obj.name.startswith("Body_"))
    face = next(obj for obj in meshes if obj.name.startswith("FacePartsAtlas"))
    before = atlas.statistics(meshes, rig)
    bone_heads = {bone.name: rig.matrix_world @ bone.head_local for bone in rig.data.bones}
    original_points = [list(body.matrix_world @ vertex.co) for vertex in body.data.vertices]
    original_body = surface_signature(original_points, [list(polygon.vertices) for polygon in body.data.polygons])
    jaw_evidence = fit_jaw(body, rig, positions)
    teeth_evidence = fit_teeth(face, body, rig, request["expectedHeightM"])
    output = directory / "dentition-v1"
    output.mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "character.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [rig, *meshes, *[obj for obj in bpy.data.objects if obj.type == "EMPTY" and obj.name.startswith("socket_")]]:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(output / "body.glb"), export_format="GLB", use_selection=True, export_animations=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(output / "body.glb"))
    rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    meshes = atlas.skinned_meshes(rig)
    body = next(obj for obj in meshes if obj.name.startswith("Body_"))
    face = next(obj for obj in meshes if obj.name.startswith("FacePartsAtlas"))
    after = atlas.statistics(meshes, rig)
    tree = KDTree(len(original_points))
    for index, point in enumerate(original_points):
        tree.insert(point, index)
    tree.balance()
    matched, maximum_distance = [], 0
    for vertex in body.data.vertices:
        _, index, distance = tree.find(body.matrix_world @ vertex.co)
        matched.append(original_points[index])
        maximum_distance = max(maximum_distance, distance)
    checks = dict(trianglesPreserved=before["triangles"] == after["triangles"], threeDrawCalls=after["drawCalls"] == 3,
                  canonicalBones=after["bones"] == 56,
                  bodyGeometryPreserved=maximum_distance < 1e-5 and original_body == surface_signature(matched,
                      [list(polygon.vertices) for polygon in body.data.polygons]),
                  bonePositionsPreserved=set(bone_heads) == set(rig.data.bones.keys()) and max(
                      (bone_heads[bone.name]-rig.matrix_world @ bone.head_local).length for bone in rig.data.bones) < 1e-5)
    checks.update(weight_checks([[item.weight for item in vertex.groups if mesh.vertex_groups[item.group].name in rig.data.bones and item.weight > 1e-8]
                                for mesh in meshes for vertex in mesh.data.vertices]))
    capture = atlas.render_review(output, before["bounds"][2][1])
    jaw_review = check_jaw(body, face, rig, teeth_evidence)
    checks["jawAttachmentAndDeformation"] = all(row["passed"] for row in jaw_review)
    portraits(output, rig, before["bounds"][2][1], "jaw")
    anatomy = build_audit(body, meshes, rig, request, capture)
    (output / "anatomy.json").write_text(json.dumps(anatomy, indent=2)+'\n')
    checks["anatomyAndStaticBends"] = anatomy["passed"]
    clips = evaluate_motion(output, rig, body, templates) if templates else {}
    checks["suppliedMotion"] = len(clips) == 6 and all(clip["passed"] for clip in clips.values())
    report = dict(schemaVersion=1, identity=directory.name, sourceCandidate="optimized-v2", sourceModelSha256=sha(source / "body.glb"),
                  sourceReceiptSha256=sha(source / "review.json"), bodyReceiptSha256=sha(directory / "receipt.json"),
                  toolSha256=sha(__file__), profileToolSha256=sha(TOOLS / "class_character_dentition.py"),
                  atlasToolSha256=sha(TOOLS / "atlas-class-characters.py"), sourceMotionToolSha256=sha(TOOLS / "review-class-character-motion.py"),
                  chainContractSha256=sha(TOOLS / "animation_replacement.py"), deformationAuditSha256=sha(TOOLS / "class_character_audit.py"),
                  before=before, after=after, maximumBodyRoundTripDistanceM=maximum_distance,
                  jawWeights=jaw_evidence, teethFit=teeth_evidence, jawReview=jaw_review,
                  clips=clips, checks=checks, passed=all(checks.values()), nativeAccepted=False, runtimeEligible=False,
                  limitations=["Diagnostic jaw opening and source-space poses do not approve facial acting, equipment or native locomotion."],
                  files=[dict(path=file.name, sha256=sha(file)) for file in sorted(output.iterdir())
                         if file.suffix in (".glb", ".blend", ".png", ".json") and file.name != "review.json"])
    (output / "review.json").write_text(json.dumps(report, indent=2)+'\n')
    print("WAR_CLASS_DENTITION", directory.name, report["passed"], json.dumps(checks), flush=True)
    if templates and not report["passed"]:
        raise RuntimeError("Dentition export or pose review failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--character")
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    run = args.run.resolve()
    run.relative_to(ROOT / "artifacts/unreal/class-characters")
    templates = None if args.preview_only else motion.source_samples(run)
    processed = 0
    for directory in sorted(run.iterdir()):
        if not (directory / "request.json").exists() or args.character and directory.name != args.character:
            continue
        request = json.loads((directory / "request.json").read_text())
        if request["race"] == "greenskin":
            fit(directory, templates)
            processed += 1
    if not processed:
        raise RuntimeError("No matching Greenskin body")


if __name__ == "__main__":
    main()
