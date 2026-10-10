"""Blender: retain draft anatomy while combining detachable parts into two atlases.

Original fitting masters and body receipts are immutable. This derived LOD0
candidate has three draw calls; it does not approve native motion or armor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import struct

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from class_character_audit import build_audit, weight_checks
from class_character_skin import refine_source, transfer, apply_correction


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sample_image(image, size, domain):
    pixels = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape((image.size[1], image.size[0], 4))
    # Bilinear resize in the source channel's existing colour space.
    # glTF's repeat sampler also applies to authored UVs just outside the tile.
    # Sample that extended domain before atlas packing instead of clamping it.
    x = (domain[0][0] + (np.arange(size) + .5) / size * (domain[0][1] - domain[0][0])) * image.size[0] - .5
    y = (domain[1][0] + (np.arange(size) + .5) / size * (domain[1][1] - domain[1][0])) * image.size[1] - .5
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    dx, dy = (x - x0)[None, :, None], (y - y0)[:, None, None]
    x1, y1 = (x0 + 1) % image.size[0], (y0 + 1) % image.size[1]
    x0, y0 = x0 % image.size[0], y0 % image.size[1]
    return ((pixels[y0[:, None], x0] * (1 - dx) + pixels[y0[:, None], x1] * dx) * (1 - dy)
            + (pixels[y1[:, None], x0] * (1 - dx) + pixels[y1[:, None], x1] * dx) * dy)


def upstream_image(socket):
    pending = [link.from_node for link in socket.links]
    visited, images = set(), []
    while pending:
        node = pending.pop()
        if node in visited:
            continue
        visited.add(node)
        if node.type == "TEX_IMAGE" and node.image:
            images.append(node.image)
        else:
            pending.extend(link.from_node for item in node.inputs for link in item.links)
    if len(set(images)) > 1:
        raise RuntimeError("Atlas requires one image per source material channel")
    return images[0] if images else None


def atlas_group(meshes, name, cutout):
    if len(meshes) != 3 or any(len(mesh.data.materials) != 1 for mesh in meshes):
        raise RuntimeError(f"Expected three single-material parts: {[(mesh.name, len(mesh.data.materials)) for mesh in meshes]}")
    tile, gutter = 1024, 8
    color = np.zeros((2048, 2048, 4), dtype=np.float32)
    normal = np.zeros_like(color)
    normal[:] = (.5, .5, 1, 1)
    rough = np.ones_like(color)
    for index, mesh in enumerate(meshes):
        uv = mesh.data.uv_layers.active
        if not uv:
            raise RuntimeError("Body-part UVs missing")
        domain = [(min(0, min(loop.uv[axis] for loop in uv.data)), max(1, max(loop.uv[axis] for loop in uv.data))) for axis in range(2)]
        if any(high - low > 2 for low, high in domain):
            raise RuntimeError("Body-part UV repeat would lose too much atlas resolution")
        material = mesh.data.materials[0]
        shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        rgba = np.ones((tile - 2 * gutter, tile - 2 * gutter, 4), dtype=np.float32)
        image = upstream_image(shader.inputs["Base Color"])
        if image:
            rgba[:] = sample_image(image, len(rgba), domain)
        else:
            linear = np.array(shader.inputs["Base Color"].default_value[:3])
            rgba[:, :, :3] = np.where(linear <= .0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - .055)
        if not cutout:
            rgba[:, :, 3] = 1
        n = np.empty_like(rgba)
        n[:] = (.5, .5, 1, 1)
        normal_image = upstream_image(shader.inputs["Normal"])
        if normal_image:
            n[:] = sample_image(normal_image, len(n), domain)
        r = np.ones_like(rgba)
        r[:, :, :3] = shader.inputs["Roughness"].default_value
        rough_image = upstream_image(shader.inputs["Roughness"])
        if rough_image:
            # Imported glTF roughness lives in the green packed channel.
            r[:, :, :3] = sample_image(rough_image, len(r), domain)[:, :, 1:2]
        x, y = (index % 2) * tile, (index // 2) * tile
        for target, content in ((color, rgba), (normal, n), (rough, r)):
            target[y:y + tile, x:x + tile] = np.pad(content, ((gutter, gutter), (gutter, gutter), (0, 0)), mode="edge")
        for loop in uv.data:
            u = (loop.uv.x - domain[0][0]) / (domain[0][1] - domain[0][0])
            v = (loop.uv.y - domain[1][0]) / (domain[1][1] - domain[1][0])
            loop.uv = ((x + gutter + u * (tile - 2 * gutter)) / 2048,
                       (y + gutter + v * (tile - 2 * gutter)) / 2048)
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    for label, pixels, space in (("Color", color, "sRGB"), ("Normal", normal, "Non-Color"), ("Roughness", rough, "Non-Color")):
        image = bpy.data.images.new(name + label, width=2048, height=2048, alpha=True)
        image.colorspace_settings.name = space
        image.pixels.foreach_set(pixels.ravel())
        image.update()
        image.pack()
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        if label == "Color":
            material.node_tree.links.new(node.outputs["Color"], shader.inputs["Base Color"])
            if cutout:
                clip = material.node_tree.nodes.new("ShaderNodeMath")
                clip.operation = "GREATER_THAN"
                clip.inputs[1].default_value = .45
                material.node_tree.links.new(node.outputs["Alpha"], clip.inputs[0])
                material.node_tree.links.new(clip.outputs[0], shader.inputs["Alpha"])
        elif label == "Normal":
            mapping = material.node_tree.nodes.new("ShaderNodeNormalMap")
            material.node_tree.links.new(node.outputs["Color"], mapping.inputs["Color"])
            material.node_tree.links.new(mapping.outputs["Normal"], shader.inputs["Normal"])
        else:
            material.node_tree.links.new(node.outputs["Color"], shader.inputs["Roughness"])
    shader.inputs["Metallic"].default_value = 0
    bpy.ops.object.select_all(action="DESELECT")
    for mesh in meshes:
        mesh.data.materials.clear()
        mesh.data.materials.append(material)
        for face in mesh.data.polygons:
            face.material_index = 0
        mesh.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    combined = bpy.context.object
    combined.name = name
    return combined


def statistics(meshes, rig):
    positions = [mesh.matrix_world @ vertex.co for mesh in meshes for vertex in mesh.data.vertices]
    return dict(triangles=sum(sum(len(face.vertices) - 2 for face in mesh.data.polygons) for mesh in meshes),
                drawCalls=sum(len(mesh.data.materials) for mesh in meshes), bones=len(rig.data.bones),
                bounds=[[min(point[axis] for point in positions), max(point[axis] for point in positions)] for axis in range(3)])


def skinned_meshes(rig):
    # glTF import may create hidden Icosphere bone widgets. They are editor
    # display objects, never character geometry or export selections.
    return [obj for obj in bpy.data.objects if obj.type == "MESH" and any(
        modifier.type == "ARMATURE" and modifier.object == rig for modifier in obj.modifiers)]


def grooming_clearance(body, meshes):
    """Lift fitted scalp/brow cards out of the skin to remove depth fighting."""
    surface = BVHTree.FromPolygons([body.matrix_world @ vertex.co for vertex in body.data.vertices],
                                  [list(face.vertices) for face in body.data.polygons])
    changed, maximum = 0, 0
    for mesh in meshes:
        clearance = .0012 if "hair_" in mesh.name else .0004
        inverse = mesh.matrix_world.inverted()
        for vertex in mesh.data.vertices:
            position = mesh.matrix_world @ vertex.co
            nearest, normal, _, distance = surface.find_nearest(position)
            signed = (position - nearest).dot(normal)
            if distance < .012 and signed < clearance:
                displacement = clearance - signed
                vertex.co = inverse @ (position + normal * displacement)
                changed += 1
                maximum = max(maximum, displacement)
        mesh.data.update()
    return dict(changedVertices=changed, maximumOffsetM=maximum, scalpClearanceM=.0012)


def render_review(output, height):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 640, 800
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.view_settings.view_transform, scene.view_settings.exposure = "AgX", -1.1
    scene.world = bpy.data.worlds.new("ReviewWorld")
    scene.world.color = (.055, .055, .055)
    center = Vector((0, 0, height * .5))
    camera = bpy.data.objects.new("AtlasReview", bpy.data.cameras.new("AtlasReview"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type, camera.data.ortho_scale = "ORTHO", height * 1.19
    for position, energy in (((-3, -4, 4), 600), ((3, -2, 2), 250), ((1, 3, 3), 450)):
        data = bpy.data.lights.new("ReviewArea", "AREA")
        data.energy, data.size = energy, 3
        obj = bpy.data.objects.new("ReviewArea", data)
        scene.collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()
    for name, target, location, scale in (("front", center, center + Vector((0, -5, 0)), height * 1.19),
        ("head", Vector((0, -.03, height * .925)), Vector((.15, -2, height * .925)), height * .22)):
        camera.location, camera.data.ortho_scale = location, scale
        camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(output / (name + ".png"))
        bpy.ops.render.render(write_still=True)
    clay = bpy.data.materials.new("DeformationClay")
    clay.use_nodes = True
    clay.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (.28, .30, .32, 1)
    def capture_pose(name):
        camera.location, camera.data.ortho_scale = center + Vector((4, -5, height * .08)), height * 1.19
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.view_layers[0].material_override = clay
        scene.render.filepath = str(output / ("pose-" + name + ".png"))
        bpy.ops.render.render(write_still=True)
        scene.view_layers[0].material_override = None
    return capture_pose


def optimize(directory, iterations, shoulder_iterations):
    receipt_file = directory / "receipt.json"
    receipt = json.loads(receipt_file.read_text())
    for item in receipt["files"]:
        if Path(item["path"]).name != item["path"]:
            raise RuntimeError("Unsafe source evidence path")
        if sha(directory / item["path"]) != item["sha256"]:
            raise RuntimeError("Changed source evidence")
    if not receipt["technicalPassed"]:
        raise RuntimeError("Source anatomy must pass first")
    bpy.ops.wm.open_mainfile(filepath=str(directory / "character.blend"))
    source_rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    source_body = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name.startswith("Body_"))
    recipe_file = Path(__file__).with_name("class-character-skin-recipes.json")
    recipes = json.loads(recipe_file.read_text())
    if recipes["schemaVersion"] != 1:
        raise RuntimeError("Unsupported skin refinement recipe")
    settings = {**recipes["defaults"], **recipes["characters"].get(directory.name, {})}
    refinement = refine_source(source_body, source_rig,
                               settings["hipIterations"] if iterations is None else iterations,
                               settings["shoulderIterations"] if shoulder_iterations is None else shoulder_iterations,
                               settings["trunkAnchorWidth"])
    correction_evidence = None
    if settings.get("correction"):
        name = settings["correction"]
        if Path(name).name != name or not name.endswith(".json"):
            raise RuntimeError("Unsafe skin correction path")
        correction_file = Path(__file__).with_name("class-character-skin-corrections") / name
        correction = json.loads(correction_file.read_text())
        if correction["solver"]["toolSha256"] != sha(Path(__file__).with_name("fit-class-character-skin.py")):
            raise RuntimeError("Skin correction solver changed")
        apply_correction(refinement, correction, directory.name, sha(directory / "body.glb"))
        correction_evidence = dict(file=name, sha256=sha(correction_file), solverSha256=correction["solver"]["toolSha256"])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(directory / "body.glb"))
    rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    meshes = skinned_meshes(rig)
    skin_refinement = transfer(next(mesh for mesh in meshes if mesh.name.startswith("Body_")), rig, refinement)
    before = statistics(meshes, rig)
    bone_heads = {bone.name: rig.matrix_world @ bone.head_local for bone in rig.data.bones}
    grooming = [mesh for mesh in meshes if mesh.name.startswith("grooming_")]
    face = [mesh for mesh in meshes if mesh not in grooming and not mesh.name.startswith("Body_")]
    clearance = grooming_clearance(next(mesh for mesh in meshes if mesh.name.startswith("Body_")), grooming)
    atlas_group(grooming, "GroomingAtlas", True)
    atlas_group(face, "FacePartsAtlas", False)
    meshes = skinned_meshes(rig)
    after = statistics(meshes, rig)
    output = directory / "optimized-v2"
    output.mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "character.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [rig, *meshes, *[obj for obj in bpy.data.objects if obj.type == "EMPTY" and obj.name.startswith("socket_")]]:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(output / "body.glb"), export_format="GLB", use_selection=True, export_animations=False, export_yup=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(output / "body.glb"))
    rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    imported = statistics(skinned_meshes(rig), rig)
    checks = dict(trianglesPreserved=before["triangles"] == after["triangles"] == imported["triangles"],
                  threeDrawCalls=after["drawCalls"] == imported["drawCalls"] == 3,
                  canonicalBoneCount=before["bones"] == after["bones"] == imported["bones"] == 56,
                  boundsPreserved=max(abs(a - b) for pair, other in zip(before["bounds"], imported["bounds"]) for a, b in zip(pair, other)) < 1e-5)
    checks["bonePositionsPreserved"] = set(bone_heads) == set(rig.data.bones.keys()) and max(
        (bone_heads[bone.name] - rig.matrix_world @ bone.head_local).length for bone in rig.data.bones) < 1e-5
    checks.update(weight_checks([[item.weight for item in vertex.groups if mesh.vertex_groups[item.group].name in rig.data.bones and item.weight > 1e-8]
                                for mesh in skinned_meshes(rig) for vertex in mesh.data.vertices]))
    data = (output / "body.glb").read_bytes()
    payload = json.loads(data[20:20 + struct.unpack_from("<I", data, 12)[0]])
    checks["noEmbeddedAnimations"] = not payload.get("animations")
    checks["portableAlphaModes"] = sorted(material.get("alphaMode", "OPAQUE") for material in payload["materials"]) == ["MASK", "OPAQUE", "OPAQUE"]
    checks["onlySkinnedGeometry"] = all("skin" in node for node in payload["nodes"] if "mesh" in node)
    checks["textureDimensions"] = all(max(image.size) <= 2048 for image in bpy.data.images if image.type == "IMAGE")
    policy = json.loads((ROOT / "scripts/blender-character-pipeline/data/body-families/pilot-policy.json").read_text())["qc"]["body"]
    checks["bodyBudget"] = imported["triangles"] <= policy["maxTriangles"] and imported["drawCalls"] <= policy["maxDrawCalls"]
    capture = render_review(output, imported["bounds"][2][1])
    request = json.loads((directory / "request.json").read_text())
    anatomy = build_audit(next(mesh for mesh in skinned_meshes(rig) if mesh.name.startswith("Body_")), skinned_meshes(rig), rig, request, capture)
    (output / "anatomy.json").write_text(json.dumps(anatomy, indent=2) + "\n")
    checks["refinedAnatomyAndStaticDeformation"] = anatomy["passed"]
    report = dict(sourceReceiptSha256=sha(receipt_file), sourceModelSha256=sha(directory / "body.glb"), toolSha256=sha(__file__),
                  deformationAuditSha256=sha(Path(__file__).with_name("class_character_audit.py")),
                  skinRefinementToolSha256=sha(Path(__file__).with_name("class_character_skin.py")),
                  skinRecipeSha256=sha(recipe_file),
                  skinCorrection=correction_evidence,
                  policySha256=sha(ROOT / "scripts/blender-character-pipeline/data/body-families/pilot-policy.json"),
                  before=before, after=imported, groomingClearance=clearance, skinRefinement=skin_refinement,
                  checks=checks, passed=all(checks.values()), nativeAccepted=False, runtimeEligible=False,
                  files=[dict(path=file.name, sha256=sha(file)) for file in sorted(output.iterdir()) if file.suffix in (".glb", ".blend", ".png", ".json") and file.name != "review.json"])
    (output / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    print("WAR_CLASS_ATLAS", directory.name, report["passed"], flush=True)
    if not report["passed"]:
        raise RuntimeError("Derived atlas verification failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--character")
    parser.add_argument("--skin-iterations", "--hip-iterations", type=int)
    parser.add_argument("--shoulder-iterations", type=int)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--shard", type=int, default=0)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    run = Path(args.run).resolve()
    run.relative_to(ROOT / "artifacts/unreal/class-characters")
    if not 0 <= args.shard < args.shards <= 4:
        raise RuntimeError("Invalid shard selection")
    directories = [directory for directory in sorted(run.iterdir()) if (directory / "receipt.json").exists()]
    for index, directory in enumerate(directories):
        if index % args.shards == args.shard and (not args.character or directory.name == args.character):
            optimize(directory, args.skin_iterations, args.shoulder_iterations)


if __name__ == "__main__":
    main()
