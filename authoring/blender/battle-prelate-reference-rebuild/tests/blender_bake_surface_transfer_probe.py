"""Literal cloth and raised gold test patch; no character geometry is generated."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bake_atlas
from smoke_bake_atlas import signature


def surface(name, vertices, faces, uvs, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    layer = mesh.uv_layers.new(name="authored_uv")
    for loop, coordinate in zip(layer.data, uvs):
        loop.uv = coordinate
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def material(name, color, roughness, metallic):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    for input_name, value in (("Roughness", roughness), ("Metallic", metallic)):
        node = result.node_tree.nodes.new("ShaderNodeValue")
        node.outputs[0].default_value = value
        result.node_tree.links.new(node.outputs[0], shader.inputs[input_name])
    return result


def mesh_signature(obj):
    mesh = obj.data
    return {
        "data": mesh.as_pointer(),
        "coordinates": [tuple(vertex.co) for vertex in mesh.vertices],
        "faces": [tuple(face.vertices) for face in mesh.polygons],
        "uv": [(layer.name, [tuple(loop.uv) for loop in layer.data]) for layer in mesh.uv_layers],
        "materials": [item.as_pointer() for item in mesh.materials],
        "matrix": [tuple(row) for row in obj.matrix_world],
    }


def scene_signature(objects):
    return {
        "objects": {obj.name: (obj.hide_render, obj.hide_get(), obj.hide_select, obj.select_get()) for obj in objects},
        "active": bpy.context.view_layer.objects.active,
        "engine": bpy.context.scene.render.engine,
        "samples": bpy.context.scene.cycles.samples,
    }


def pixels(slot, channel):
    image = bpy.data.images[f"prelate.{slot}.{channel}"]
    values = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(values)
    return values.reshape((-1, 4))


def run():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cloth = material("probe.crimson_cloth", (.12, .018, .025, 1), .78, 0)
    gold = material("probe.authored_gold", (.60, .32, .06, 1), .24, .86)
    vertices = [(-.1,-.1,0),(.1,-.1,0),(.1,.1,0),(-.1,.1,0)]
    faces = [(0,1,2,3)]
    uvs = [(0,0),(1,0),(1,1),(0,1)]
    target = surface("probe.runtime_cloth", vertices, faces, uvs, cloth)
    retained_cloth = surface("probe.retained_cloth", vertices, faces, uvs, cloth)
    retained_patch = surface("probe.retained_gold_relief",
        [(-.04,-.04,.001),(.04,-.04,.001),(.04,.04,.001),(-.04,.04,.001),(0,0,.008)],
        [(0,1,4),(1,2,4),(2,3,4),(3,0,4)],
        [(0,0),(1,0),(.5,.5),(1,0),(1,1),(.5,.5),(1,1),(0,1),(.5,.5),(0,1),(0,0),(.5,.5)], gold)
    # A deliberately different active UV map catches accidental sampling from
    # the preview map instead of the retained explicitly named authored UVs.
    preview_uv = retained_patch.data.uv_layers.new(name="preview_other_uv")
    for loop in preview_uv.data:
        loop.uv = (.9, .9)
    preview_uv.active_render = True
    retained_patch.data.uv_layers.active = preview_uv
    paint = bpy.data.images.new("probe.authored_gold_paint", width=2, height=2, float_buffer=True)
    paint.colorspace_settings.name = "Non-Color"
    paint.pixels.foreach_set([.75,.45,.05,1, .50,.27,.04,1,
                             .60,.34,.07,1, .36,.15,.025,1])
    paint.update()
    paint_node = gold.node_tree.nodes.new("ShaderNodeTexImage")
    paint_node.image = paint
    paint_node.interpolation = "Closest"
    gold.node_tree.links.new(paint_node.outputs["Color"], gold.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
    retained_cloth.hide_render = True
    retained_patch.hide_render = True
    retained_patch.hide_set(True)
    retained_patch.hide_select = True
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    objects = [target, retained_cloth, retained_patch]
    original_sources = [mesh_signature(obj) for obj in (retained_cloth, retained_patch)]
    original_materials = [signature(item) for item in (cloth, gold)]
    original_scene = scene_signature(objects)
    original_counts = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials))
    output = ROOT / "tmp/bake_surface_transfer_probe"
    paths = bake_atlas.bake_module_atlas(target, "gold_transfer", output, resolution=64,
        high_sources=[retained_cloth, retained_patch], transfer_surface_channels=True)
    expected = {"baseColor", "normal", "roughness", "metallic", "occlusion", "orm"}
    assert set(paths) == expected
    assert len(target.data.materials) == 1 and len(target.data.uv_layers) == 1
    assert [mesh_signature(obj) for obj in (retained_cloth, retained_patch)] == original_sources
    assert [signature(item) for item in (cloth, gold)] == original_materials
    assert scene_signature(objects) == original_scene
    assert len(bpy.data.objects) == original_counts[0], "Temporary high objects leaked"
    assert len(bpy.data.meshes) == original_counts[1] + 1, "Temporary high mesh data leaked"
    assert len(bpy.data.materials) == original_counts[2] + 1, "Temporary high materials leaked"
    maps = {channel: pixels("gold_transfer", channel) for channel in paths}
    gold_mask = maps["metallic"][:,0] > .7
    cloth_mask = (maps["occlusion"][:,0] > .95) & (maps["metallic"][:,0] < .02)
    assert gold_mask.sum() > 100 and cloth_mask.sum() > 100
    print("TRANSFER_PIXEL_MEDIANS", np.median(maps["baseColor"][gold_mask,:3],axis=0).tolist(),
          np.median(maps["baseColor"][cloth_mask,:3],axis=0).tolist(), flush=True)
    assert np.median(maps["baseColor"][gold_mask,0]) > .5, "Gold color was not transferred"
    assert np.median(maps["baseColor"][gold_mask,1]) > .25, "Gold base color became diffuse-black"
    assert np.median(maps["baseColor"][cloth_mask,0]) < .45, "High cloth coverage was lost"
    assert abs(np.median(maps["roughness"][gold_mask,0]) - .24) < .02
    assert abs(np.median(maps["metallic"][gold_mask,0]) - .86) < .02
    assert abs(np.median(maps["roughness"][cloth_mask,0]) - .78) < .02
    assert np.ptp(maps["normal"][gold_mask,0]) > .10, "Modeled relief did not transfer to normals"
    assert np.ptp(maps["normal"][gold_mask,1]) > .10
    # The lower-left authored paint texel is bright gold; the deliberately wrong
    # active source UV would yield the darker upper-right texel everywhere.
    source_fraction = .38
    weights = [(1-source_fraction)**2, source_fraction*(1-source_fraction),
               source_fraction**2, source_fraction*(1-source_fraction)]
    target_uv = sum(np.array(loop.uv)*weight for loop,weight in zip(target.data.uv_layers[0].data,weights))
    sample = maps["baseColor"].reshape((64,64,4))[int(target_uv[1]*64), int(target_uv[0]*64)]
    assert sample[0] > .85 and sample[1] > .65, "Named authored high-source UVs were not preserved"
    assert np.ptp(maps["baseColor"][gold_mask,0]) > .15, "Authored source paint variation was lost"
    for index, channel in enumerate(("occlusion", "roughness", "metallic")):
        assert np.max(np.abs(maps["orm"][:,index] - maps[channel][:,0])) < .005

    # A failure after the base bake must release source clones and restore target,
    # material graphs, view state and render settings.
    failed = surface("probe.failure_target", vertices, faces, uvs, cloth)
    failed_before = mesh_signature(failed)
    before_failure_objects = list(bpy.data.objects)
    before_failure_scene = scene_signature(before_failure_objects)
    before_failure_counts = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials), len(bpy.data.images))
    original_save = bake_atlas._save
    def injected_failure(image, path):
        raise RuntimeError("Intentional surface-transfer restoration probe")
    bake_atlas._save = injected_failure
    try:
        try:
            bake_atlas.bake_module_atlas(failed, "failure_transfer", output, resolution=32,
                high_sources=[retained_cloth, retained_patch], transfer_surface_channels=True)
        except RuntimeError as error:
            assert "Intentional" in str(error)
        else:
            raise AssertionError("Injected bake failure was not raised")
    finally:
        bake_atlas._save = original_save
    assert mesh_signature(failed) == failed_before
    assert scene_signature(before_failure_objects) == before_failure_scene
    assert [mesh_signature(obj) for obj in (retained_cloth, retained_patch)] == original_sources
    assert [signature(item) for item in (cloth, gold)] == original_materials
    assert (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials), len(bpy.data.images)) == before_failure_counts
    report = {"status":"passed", "gold_texels":int(gold_mask.sum()), "cloth_texels":int(cloth_mask.sum()),
              "gold_base_color_median":np.median(maps["baseColor"][gold_mask,:3],axis=0).tolist(),
              "gold_metallic_median":float(np.median(maps["metallic"][gold_mask,0])),
              "gold_normal_xy_range":np.ptp(maps["normal"][gold_mask,:2],axis=0).tolist(),
              "authored_uv_paint_sample":sample.tolist(), "named_source_uv_preserved":True,
              "six_channels_one_material":True,"retained_sources_unchanged":True,"failure_restoration_verified":True}
    (output / "probe_report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("SURFACE_TRANSFER_PROBE_PASSED", json.dumps(report), flush=True)


if __name__ == "__main__":
    run()
