"""Blender: author a separate anatomy/rig draft, preserving the live MPFB fit mesh."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/blender-character-pipeline/blender"))
sys.path.insert(0, str(Path(__file__).parent))
import generate_mpfb_body as source
from class_character_audit import build_audit, canine_surface, texture_srgb


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fitted_canines(teeth, rig, stature):
    """Fit modest lower canines to the actual dentition, rigidly bound to the jaw."""
    evaluated = teeth.evaluated_get(bpy.context.evaluated_depsgraph_get())
    geometry = evaluated.to_mesh()
    try:
        points = [teeth.matrix_world @ vertex.co for vertex in geometry.vertices]
    finally:
        evaluated.to_mesh_clear()
    low_z, front_y = min(point.z for point in points), min(point.y for point in points)
    result = []
    for side in (-1, 1):
        root = (side * stature * .014, front_y - stature * .003, low_z + stature * .003)
        vertices, faces = canine_surface(side, root, stature * .018)
        geometry = bpy.data.meshes.new("LowerCanineSurface")
        geometry.from_pydata(vertices, [], faces)
        geometry.update()
        canine = bpy.data.objects.new("LowerCanine_" + ("L" if side > 0 else "R"), geometry)
        bpy.context.scene.collection.objects.link(canine)
        for face in geometry.polygons:
            face.use_smooth = True
        canine.parent = rig
        canine.matrix_parent_inverse = rig.matrix_world.inverted()
        canine.vertex_groups.new(name="jaw").add(list(range(len(vertices))), 1, "REPLACE")
        canine.modifiers.new("humanoid_game_v2", "ARMATURE").object = rig
        result.append(canine)
    return result


def balance_legs(body):
    """Correct the measured calf/thigh balance through a smooth, monotonic field.

    Fitting helpers receive the same correction as the surface. MPFB then fits
    the skeleton and wearables to the corrected anatomy instead of scaling bones.
    """
    import math
    import numpy as np
    keys = body.data.shape_keys.key_blocks
    basis = np.array([list(vertex.co) for vertex in keys[0].data])
    mixed = basis.copy()
    for key in list(keys)[1:]:
        mixed += (np.array([list(vertex.co) for vertex in key.data]) - basis) * key.value

    def center(group_name):
        group = body.vertex_groups[group_name]
        indices = [vertex.index for vertex in body.data.vertices if any(item.group == group.index and item.weight > 0 for item in vertex.groups)]
        return float(np.mean(mixed[indices, 2]))

    hip, knee, ankle = [center("joint-l-" + name) for name in ("upper-leg", "knee", "ankle")]
    ratio = (knee - ankle) / (hip - knee)
    if .80 <= ratio <= 1.08:
        return {"calfThighBefore": ratio, "applied": False}
    target = ankle + (hip - ankle) * .95 / 1.95
    amplitude = (target - knee) / math.sin(math.pi * (knee - ankle) / (hip - ankle))
    if abs(amplitude) * math.pi / (hip - ankle) >= .40:
        raise RuntimeError("Leg correction would distort the anatomy; reject this recipe")
    correction = body.shape_key_add(name="AnatomicalLegBalance", from_mix=False)
    for vertex, position in zip(correction.data, mixed):
        if ankle < position[2] < hip:
            vertex.co.z += amplitude * math.sin(math.pi * (position[2] - ankle) / (hip - ankle))
    correction.value = 1
    bpy.context.view_layer.update()
    return {"calfThighBefore": ratio, "applied": True, "amplitudeM": amplitude, "targetCalfThigh": .95}


def smooth_skin_weights(body, rig):
    """Diffuse discontinuities over surface edges without crossing disconnected parts.

    Rigid interiors stay fixed. Local iterations soften the original MPFB
    transitions at elbows, knees, shoulders, hips and knuckles before the final
    four-influence normalization; topology and bone lengths are unchanged.
    """
    import numpy as np
    names = list(rig.data.bones.keys())
    columns = {name: index for index, name in enumerate(names)}
    indices = {group.index: columns[group.name] for group in body.vertex_groups if group.name in columns}
    weights = np.zeros((len(body.data.vertices), len(names)))
    for vertex in body.data.vertices:
        for group in vertex.groups:
            if group.group in indices:
                weights[vertex.index, indices[group.group]] = group.weight
    edges = np.array([list(edge.vertices) for edge in body.data.edges], dtype=np.int32)
    left, right = edges[:, 0], edges[:, 1]
    counts = np.bincount(edges.ravel(), minlength=len(weights))[:, None]
    valid = weights.sum(axis=1) > .5
    original = weights.copy()
    finger_columns = [index for index, name in enumerate(names) if name.startswith(("thumb_", "index_", "middle_", "ring_", "pinky_", "hand_"))]
    hand_vertices = original[:, finger_columns].sum(axis=1) > .7
    keys = body.data.shape_keys.key_blocks
    positions = np.array([list(vertex.co) for vertex in keys[0].data])
    for key in list(keys)[1:]:
        positions += (np.array([list(vertex.co) for vertex in key.data]) - np.array([list(vertex.co) for vertex in keys[0].data])) * key.value
    height = float(np.ptp(positions[:, 2]))
    joint_vertices = np.zeros(len(weights), dtype=bool)
    for name in ("upper_arm_L", "upper_arm_R", "thigh_L", "thigh_R"):
        pivot = np.array(rig.data.bones[name].head_local)
        joint_vertices |= np.linalg.norm(positions - pivot, axis=1) < height * .075
    for iteration in range(64):
        totals = np.zeros_like(weights)
        np.add.at(totals, left, weights[right])
        np.add.at(totals, right, weights[left])
        average = totals / np.maximum(counts, 1)
        mixed = valid & (np.abs(average - weights).max(axis=1) > .0001)
        if iteration >= 6:
            mixed &= ~hand_vertices
        if iteration >= 18:
            mixed &= joint_vertices
        weights[mixed] = weights[mixed] * .5 + average[mixed] * .5
    for vertex, row in zip(body.data.vertices, weights):
        if not valid[vertex.index]:
            continue
        for group_index in indices:
            body.vertex_groups[group_index].remove([vertex.index])
        selected = np.argsort(row)[-4:]
        selected = [index for index in selected if row[index] > 1e-8]
        total = sum(row[index] for index in selected)
        for index in selected:
            group = body.vertex_groups.get(names[index]) or body.vertex_groups.new(name=names[index])
            group.add([vertex.index], float(row[index] / total), "REPLACE")
    return {"bodyIterations": 18, "handIterations": 6, "shoulderHipIterations": 64,
            "changedVertices": int((np.abs(weights - original).max(axis=1) > .0001).sum()),
            "method": "surface_adjacency_diffusion_then_four_influence_normalization"}


def align_eyes(eyes, rig):
    """Place eye pivots in the actual fitted eyeballs and bind each eye rigidly."""
    geometry = eyes.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    positions = [eyes.matrix_world @ vertex.co for vertex in geometry.vertices]
    eyes.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for side, sign in (("L", 1), ("R", -1)):
        points = [position for position in positions if position.x * sign > 0]
        center = sum(points, Vector()) / len(points)
        bone = rig.data.edit_bones["eye_" + side]
        bone.head = rig.matrix_world.inverted() @ center
        bone.tail = bone.head + Vector((0, -.012, 0))
    bpy.ops.object.mode_set(mode="OBJECT")
    eyes.vertex_groups.clear()
    for side, sign in (("L", 1), ("R", -1)):
        indices = [index for index, position in enumerate(positions) if position.x * sign > 0]
        eyes.vertex_groups.new(name="eye_" + side).add(indices, 1, "REPLACE")
    rig.select_set(False)


def prepare_eyes(eyes):
    """Remove the authored corneal shell that uses an atlas shader-data patch.

    The pinned MakeHuman mesh layers a transparent shell over its textured iris.
    Opaque game exports must remove that shell, otherwise the atlas's blue patch
    covers both irises. The original sclera/iris geometry and UVs are retained.
    """
    import bmesh
    uv = eyes.data.uv_layers.active.data
    selected = [face.index for face in eyes.data.polygons if all(uv[index].uv.x > .85 and uv[index].uv.y < .16 for index in face.loop_indices)]
    if len(selected) != 490 or len(eyes.data.polygons) != 1020:
        raise RuntimeError("Pinned eye topology/atlas changed; inspect the cornea adaptation")
    geometry = bmesh.new()
    geometry.from_mesh(eyes.data)
    geometry.faces.ensure_lookup_table()
    bmesh.ops.delete(geometry, geom=[geometry.faces[index] for index in selected], context="FACES")
    geometry.to_mesh(eyes.data)
    geometry.free()
    eyes.data.update()
    return {"removedCornealFaces": len(selected), "retainedIrisScleraFaces": len(eyes.data.polygons)}


def natural_materials(human, meshes, request):
    # Bake the tint into the source image: glTF cannot export MPFB's MixRGB node.
    # Skin pores/colour variation survive; the exported material stays portable.
    import numpy as np
    tint = np.array(texture_srgb(request["skin"]["tint"]))
    for material in human.data.materials:
        shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
        pending = [link.from_node for link in shader.inputs["Base Color"].links]
        visited = set()
        images = []
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            if node.type == "TEX_IMAGE" and node.image:
                images.append(node)
            else:
                pending.extend(link.from_node for socket in node.inputs for link in socket.links)
        if len(images) != 1:
            raise RuntimeError("Skin must have one identifiable source colour image")
        node = images[0]
        original_image = node.image
        pixels = np.empty(len(original_image.pixels), dtype=np.float32)
        original_image.pixels.foreach_get(pixels)
        pixels = pixels.reshape((-1, 4))
        # Use measured median to avoid multiplying an already dark texture twice.
        median = np.median(pixels[:, :3], axis=0)
        target = tint if request["race"] in ("greenskin", "dark_elf", "chaos") else median
        pixels[:, :3] = np.clip(pixels[:, :3] * target / np.maximum(median, .015), 0, 1)
        image = bpy.data.images.new("Skin_" + request["classKey"] + "_" + request["bodyVariant"],
                                    width=original_image.size[0], height=original_image.size[1], alpha=True)
        image.pixels.foreach_set(pixels.ravel())
        image.update()
        image.pack()
        node.image = image
        material.node_tree.links.new(node.outputs["Color"], shader.inputs["Base Color"])
        shader.inputs["Roughness"].default_value = .72
    for mesh in meshes:
        for material in mesh.data.materials:
            if not material or not material.use_nodes:
                continue
            for shader in (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"):
                if mesh.get("bodyAccessory"):
                    shader.inputs["Roughness"].default_value = .78
                    shader.inputs["Metallic"].default_value = 0
                    if mesh.get("groomingCategory") == "hair":
                        upstream = [link.from_node for link in shader.inputs["Base Color"].links]
                        if len(upstream) != 1 or upstream[0].type != "TEX_IMAGE":
                            raise RuntimeError("Expected a portable grooming colour texture")
                        node = upstream[0]
                        original_image = node.image
                        pixels = np.empty(len(original_image.pixels), dtype=np.float32)
                        original_image.pixels.foreach_get(pixels)
                        pixels = pixels.reshape((-1, 4))
                        visible = pixels[:, 3] > .5
                        median = np.median(pixels[visible, :3], axis=0)
                        color = np.array(texture_srgb(request["foundation"]["hairTint"]))
                        pixels[:, :3] = np.clip(pixels[:, :3] * color / np.maximum(median, .015), 0, 1)
                        image = bpy.data.images.new("Hair_" + request["classKey"] + "_" + request["bodyVariant"],
                            width=original_image.size[0], height=original_image.size[1], alpha=True)
                        image.pixels.foreach_set(pixels.ravel())
                        image.update()
                        image.pack()
                        node.image = image
                        material.node_tree.links.new(node.outputs["Alpha"], shader.inputs["Alpha"])
                    if shader.inputs["Alpha"].links:
                        alpha_source = shader.inputs["Alpha"].links[0].from_socket
                        clip = material.node_tree.nodes.new("ShaderNodeMath")
                        clip.operation = "GREATER_THAN"
                        clip.inputs[1].default_value = .45
                        material.node_tree.links.new(alpha_source, clip.inputs[0])
                        material.node_tree.links.new(clip.outputs[0], shader.inputs["Alpha"])
                        material["runtimeAlphaMode"] = "MASK"
                        if hasattr(material, "use_transparent_shadow"):
                            material.use_transparent_shadow = False
        if mesh.get("bodyAccessory"):
            for face in mesh.data.polygons:
                face.use_smooth = True


def studio(meshes, output):
    """Stable lighting shared by colour and neutral-clay anatomy views."""
    low, high = source.render_bounds(meshes)
    center = (low + high) * .5
    height = high.z - low.z
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (.055, .055, .055)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = -1.1
    camera_data = bpy.data.cameras.new("AnatomyReview")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = height * 1.19
    camera = bpy.data.objects.new("AnatomyReview", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for name, position, energy, size in (("Key", (-3, -4, 4), 600, 3), ("Fill", (3, -2, 2), 250, 3), ("Rim", (1, 3, 3), 450, 2)):
        light = bpy.data.lights.new(name, "AREA")
        light.energy = energy
        light.shape = "DISK"
        light.size = size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = position
        source.aim(obj, center)
    views = {"front": (0, -5, 0), "side": (5, 0, 0), "back": (0, 5, 0), "three-quarter": (4, -5, height * .08)}
    def capture(name, offset):
        camera.location = center + Vector(offset)
        source.aim(camera, center)
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    for name, offset in views.items():
        capture(name, offset)
    clay = bpy.data.materials.new("NeutralAnatomyClay")
    clay.diffuse_color = (.28, .30, .32, 1)
    clay.use_nodes = True
    clay.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (.28, .30, .32, 1)
    clay.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = .85
    scene.view_layers[0].material_override = clay
    for name in ("front", "side"):
        camera.location = center + Vector(views[name])
        source.aim(camera, center)
        scene.render.filepath = str(output / f"clay-{name}.png")
        bpy.ops.render.render(write_still=True)
    scene.view_layers[0].material_override = None
    def capture_pose(name):
        scene.view_layers[0].material_override = clay
        capture("pose-" + name, views["three-quarter"])
        scene.view_layers[0].material_override = None
    return capture_pose


def fit_cage(body, rig, request):
    """Editor-only envelope; its offset is a fitting target, not armor approval."""
    cage = body.copy()
    cage.data = body.data.copy()
    cage.name = "ArmorFit_EditorOnly"
    bpy.context.scene.collection.objects.link(cage)
    joint_groups = {group.index for group in cage.vertex_groups if group.name.startswith(("shoulder_", "forearm_", "shin_"))}
    for vertex in cage.data.vertices:
        joint_weight = sum(item.weight for item in vertex.groups if item.group in joint_groups)
        distance = .018 + min(joint_weight, 1) * .007
        vertex.co += vertex.normal * distance
    cage.hide_render = True
    cage.hide_set(True)
    cage.display_type = "WIRE"
    cage["editorOnly"] = True
    cage["clearancePolicy"] = json.dumps(request["foundation"]["armorClearanceM"])
    return cage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    request = json.loads(Path(args.request).read_text())
    output = Path(args.output).resolve()
    output.relative_to(ROOT / "artifacts/unreal/class-characters")
    output.mkdir(parents=True, exist_ok=True)
    source.clear_scene()
    family, variant = source.apply_profile_request(source.load_recipe(request["bodyFamily"]),
        source.load_recipe(request["bodyFamily"])["variants"][request["bodyVariant"]], args.request)
    body = source.create_scaled_human(variant)
    targets = source.load_checked_targets(body, family, variant)
    leg_balance = balance_legs(body)
    skin = source.apply_skin(body, variant)
    rig = source.HumanService.add_builtin_rig(body, "game_engine", import_weights=True)
    parts = source.add_natural_body_parts(body)
    grooming, grooming_provenance = source.add_grooming(body, variant)
    meshes = [body, *parts, *grooming]
    source.canonicalize_rig(rig, meshes)
    eye_preparation = prepare_eyes(parts[0])
    align_eyes(parts[0], rig)
    skin_weight_preparation = smooth_skin_weights(body, rig)
    if request["race"] == "greenskin":
        source.join_tusks_into_teeth(fitted_canines(parts[1], rig, request["expectedHeightM"]), parts[1])
        parts[1]["bodyPartId"] = "curved_lower_canines_v2"
    sockets = source.add_sockets(rig)
    source.set_metadata([rig, *meshes, *sockets], family, variant)
    body.name = f"Body_{request['classKey']}_{request['bodyVariant']}"
    natural_materials(body, meshes, request)
    if len(body.data.vertices) != source.MPFB_AUTHORING_BODY_VERTICES:
        raise RuntimeError("MPFB fitting topology changed")
    # Keep live fitting keys before deleting the hidden authoring helper vertices.
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "fitting-source.blend"))
    stripped = source.bake_targets_and_strip_helpers(body)
    preparation = source.prepare_runtime_materials(meshes)
    for row in preparation:
        if row["alphaMode"] == "BLEND":
            row["alphaMode"] = "MASK"
            bpy.data.materials[row["material"]]["runtimeAlphaMode"] = "MASK"
    for mesh in meshes:
        source.limit_bone_influences(mesh, set(rig.data.bones.keys()), 4)
    capture = studio(meshes, output)
    audit = build_audit(body, meshes, rig, request, capture)
    (output / "anatomy.json").write_text(json.dumps(audit, indent=2) + "\n")
    model = output / "body.glb"
    if bpy.data.actions:
        raise RuntimeError("Character bodies must not contain animation")
    source.export_glb(model, [rig, *meshes, *sockets])
    roundtrip = source.roundtrip_bind_audit(model, meshes, rig)
    (output / "roundtrip.json").write_text(json.dumps(roundtrip, indent=2) + "\n")
    imported_meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj not in meshes]
    for obj in meshes:
        obj.hide_render = True
    scene = bpy.context.scene
    scene.camera.location = (0, -5, request["expectedHeightM"] * .5)
    source.aim(scene.camera, Vector((0, 0, request["expectedHeightM"] * .5)))
    scene.render.filepath = str(output / "export-front.png")
    bpy.ops.render.render(write_still=True)
    target = rig.matrix_world @ rig.data.bones["head"].head_local + Vector((0, -.03, request["expectedHeightM"] * .025))
    scene.camera.location = target + Vector((.15, -2, 0))
    scene.camera.data.ortho_scale = request["expectedHeightM"] * .22
    source.aim(scene.camera, target)
    scene.render.filepath = str(output / "export-head.png")
    bpy.ops.render.render(write_still=True)
    for obj in meshes:
        obj.hide_render = False
    # The round-trip helper leaves its imported objects alive. Remove them before
    # rendering to avoid measuring or displaying two coincident bodies.
    for obj in list(bpy.data.objects):
        if obj not in [rig, *meshes, *sockets]:
            bpy.data.objects.remove(obj, do_unlink=True)
    fit_cage(body, rig, request)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "character.blend"))
    failed = [name for name, passed in audit["checks"].items() if not passed]
    technical = audit["passed"] and roundtrip["passed"]
    receipt = {"schemaVersion": 1, "classKey": request["classKey"], "className": request["className"],
        "race": request["race"], "variant": request["bodyVariant"],
        "requestSha256": hashlib.sha256(json.dumps(request, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
        "technicalPassed": technical, "failedChecks": failed,
        "runtimeEligible": False, "nativeAccepted": False, "reviewStatus": "pending_visual_and_equipped_motion",
        "skinSource": {"path": str(skin), "sha256": digest(skin)}, "targets": targets,
        "groomingSources": grooming_provenance, "legBalance": leg_balance, "skinWeightPreparation": skin_weight_preparation,
        "eyePreparation": eye_preparation,
        "helperStripping": stripped, "materialPreparation": preparation,
        "files": [{"path": file.name, "sha256": digest(file)} for file in sorted(output.iterdir())
                  if file.suffix in (".glb", ".blend", ".png", ".json") and file.name not in ("receipt.json", "request.json")]}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"class": request["classKey"], "variant": request["bodyVariant"], "technicalPassed": technical, "failed": failed}))
    if not technical:
        raise RuntimeError("Character technical checks failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
