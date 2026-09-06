"""Small Blender smoke test using two literal authored quads; no primitive ops."""
import hashlib
import json
import struct
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from bake_atlas import bake_module_atlas


def pixels(image):
    values = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(values)
    return values.reshape((-1, 4))


def signature(material):
    return [(n.name, n.bl_idname, [(s.name, str(s.default_value)) for s in n.inputs if hasattr(s, "default_value")])
            for n in material.node_tree.nodes], [(l.from_node.name, l.from_socket.name, l.to_node.name, l.to_socket.name)
                                                for l in material.node_tree.links]


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("explicit_smoke_surface")
    mesh.from_pydata([(-.5, 0, 0), (.5, 0, 0), (.5, .5, 0), (-.5, .5, 0),
                     (-.5, .5, .5), (.5, .5, .5)], [], [(0, 1, 2, 3), (3, 2, 5, 4)])
    mesh.update()
    uv = mesh.uv_layers.new(name="authored_uv")
    for loop, co in zip(uv.data, [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (1, 0), (1, 1), (0, 1)]):
        loop.uv = co
    target = bpy.data.objects.new("atlas_smoke_target", mesh)
    bpy.context.scene.collection.objects.link(target)
    original_materials = []
    for name, color, roughness, metallic in [
        ("authored_red_metal", (.7, .05, .015, 1), .23, 1.0),
        ("authored_green", (.025, .6, .06, 1), .74, .25),
    ]:
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        shader = material.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = color
        rough_value = material.node_tree.nodes.new("ShaderNodeValue")
        rough_value.outputs[0].default_value = roughness
        material.node_tree.links.new(rough_value.outputs[0], shader.inputs["Roughness"])
        metal_value = material.node_tree.nodes.new("ShaderNodeValue")
        metal_value.outputs[0].default_value = metallic
        material.node_tree.links.new(metal_value.outputs[0], shader.inputs["Metallic"])
        mesh.materials.append(material)
        original_materials.append(material)
    mesh.polygons[1].material_index = 1
    paint = bpy.data.images.new("literal_paint_pixels", width=2, height=2, alpha=True)
    paint.colorspace_settings.name = "Non-Color"
    paint.pixels = [.80, .02, .01, 1, .35, .03, .01, 1,
                    .65, .15, .02, 1, .50, .04, .01, 1]
    paint_node = original_materials[0].node_tree.nodes.new("ShaderNodeTexImage")
    paint_node.image = paint
    paint_node.interpolation = "Closest"
    original_materials[0].node_tree.links.new(paint_node.outputs["Color"], original_materials[0].node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
    witness = bpy.data.objects.new("shared_source_witness", mesh)
    witness.hide_render = True
    bpy.context.scene.collection.objects.link(witness)
    signatures = [signature(m) for m in original_materials]
    authored_uvs = [tuple(loop.uv) for loop in mesh.uv_layers[0].data]
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    output = ROOT / "tmp/bake_atlas_smoke"
    paths = bake_module_atlas(target, "smoke", output, resolution=64)
    assert set(paths) == {"baseColor", "normal", "roughness", "metallic", "occlusion", "orm"}
    assert len(target.data.materials) == 1 and len(target.data.uv_layers) == 1
    assert target.data.uv_layers[0].name == "runtime_atlas"
    assert witness.data is mesh and len(mesh.materials) == 2
    assert [signature(m) for m in original_materials] == signatures
    assert [tuple(loop.uv) for loop in mesh.uv_layers[0].data] == authored_uvs
    assert witness.hide_render is True
    image_data = {channel: pixels(bpy.data.images.get(f"prelate.smoke.{channel}")) for channel in paths}
    mask = image_data["occlusion"][:, 0] > .05
    assert np.any(mask)
    rough = image_data["roughness"][:, 0]
    metal = image_data["metallic"][:, 0]
    assert np.any(np.abs(rough - .23) < .02) and np.any(np.abs(rough - .74) < .02)
    assert np.any(np.abs(metal - 1) < .02) and np.any(np.abs(metal - .25) < .02)
    assert np.median(image_data["normal"][mask, 2]) > .8
    assert np.any(image_data["baseColor"][:, 0] > .5), "Metal's base color baked black"
    assert np.any(image_data["baseColor"][:, 1] > .5), "Second material assignment lost"
    for index, channel in enumerate(("occlusion", "roughness", "metallic")):
        assert np.max(np.abs(image_data["orm"][:, index] - image_data[channel][:, 0])) <= 1 / 255 + 1e-5
    # The original painted UV quarter must still map to its red texel after unwrap.
    weights = [.5625, .1875, .0625, .1875]
    final_uv = sum((np.array(target.data.uv_layers[0].data[i].uv) * w for i, w in enumerate(weights)))
    sample = image_data["baseColor"].reshape((64, 64, 4))[int(final_uv[1] * 64), int(final_uv[0] * 64)]
    assert sample[0] > .7 and sample[1] < .25, "Original image UV mapping was not preserved"
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    glb_path = output / "atlas_smoke.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", use_selection=True,
                              export_animations=False, export_texcoords=True, export_normals=True)
    payload = glb_path.read_bytes()
    length, kind = struct.unpack_from("<II", payload, 12)
    assert kind == 0x4E4F534A
    gltf = json.loads(payload[20:20 + length])
    material = gltf["materials"][0]
    assert "occlusionTexture" in material and "normalTexture" in material
    assert "baseColorTexture" in material["pbrMetallicRoughness"]
    assert "metallicRoughnessTexture" in material["pbrMetallicRoughness"]
    assert len(gltf["materials"]) == 1
    assert material["occlusionTexture"]["index"] == material["pbrMetallicRoughness"]["metallicRoughnessTexture"]["index"]
    low_mesh = bpy.data.meshes.new("explicit_transfer_target")
    low_mesh.from_pydata([(-.5, 0, 0), (.5, 0, 0), (.5, .5, 0), (-.5, .5, 0)], [], [(0, 1, 2, 3)])
    low_mesh.update()
    low_uv = low_mesh.uv_layers.new(name="authored_uv")
    for loop, co in zip(low_uv.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop.uv = co
    low_mesh.materials.append(original_materials[1])
    low = bpy.data.objects.new("explicit_normal_transfer_target", low_mesh)
    bpy.context.scene.collection.objects.link(low)
    high_mesh = bpy.data.meshes.new("explicit_relief_source")
    high_mesh.from_pydata([(-.5, 0, 0), (.5, 0, 0), (.5, .5, 0), (-.5, .5, 0), (0, .25, .008)], [],
                         [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)])
    high_mesh.update()
    high_mesh.materials.append(original_materials[1])
    high = bpy.data.objects.new("explicit_normal_transfer_source", high_mesh)
    bpy.context.scene.collection.objects.link(high)
    high.hide_render = True
    transfer_paths = bake_module_atlas(low, "high_transfer", output, resolution=64, high_sources=[high])
    transfer_normal = pixels(bpy.data.images.get("prelate.high_transfer.normal"))
    transfer_ao = pixels(bpy.data.images.get("prelate.high_transfer.occlusion"))
    transfer_mask = transfer_ao[:, 0] > .5
    assert np.ptp(transfer_normal[transfer_mask, 1]) > .012, "Selected high-detail normals were not transferred"
    assert high.hide_render is True and high.data is high_mesh
    assert [signature(m) for m in original_materials] == signatures
    report = {"status": "passed", "shared_sources_preserved": True,
              "paint_uv_mapping_preserved": True, "metal_base_color_preserved": True,
              "orm_packing_verified": True, "glb_material_channels_verified": True,
              "selected_high_normal_transfer_verified": True,
              "packed_orm_shared_in_glb": True,
              "texture_dimensions": [64, 64], "paint_sample": sample.tolist(),
              "files": {channel: {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                        for channel, path in paths.items()}}
    (output / "smoke_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("ATLAS_SMOKE_PASSED " + json.dumps(report), flush=True)


if __name__ == "__main__":
    run()
