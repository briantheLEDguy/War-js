"""Small literal test surface; never used as character geometry or an asset."""
from pathlib import Path
import sys
import tempfile

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from bake_atlas import bake_module_atlas
import build_proof

bpy.ops.wm.read_factory_settings(use_empty=True)
actual = build_proof.material("chainmail")
source_node = actual.node_tree.nodes.get("Authored source occlusion")
assert source_node and source_node.image.colorspace_settings.name == "Non-Color"
assert not source_node.outputs["Color"].is_linked


def probe(name, source_ao):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(-.5,-.5,0),(.5,-.5,0),(.5,.5,0),(-.5,.5,0)], [], [(0,1,2,3)])
    uv = mesh.uv_layers.new(name="authored_uv")
    for loop, coordinate in zip(uv.data, [(0,0),(1,0),(1,1),(0,1)]):
        loop.uv = coordinate
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (.4,.3,.2,1)
    shader.inputs["Roughness"].default_value = .6
    if source_ao:
        image = bpy.data.images.new("test.source_ao", width=2, height=2, float_buffer=True)
        image.colorspace_settings.name = "Non-Color"
        image.pixels.foreach_set([.25,.25,.25,1] * 4)
        image.update()
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.name = "Authored source occlusion"
        node.image = image
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def pixels(name):
    image = bpy.data.images[name]
    values = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(values)
    return values.reshape((-1,4))


directory = Path(tempfile.mkdtemp(prefix="prelate-ao-probe-"))
plain, with_ao = probe("probe.plain", False), probe("probe.source_ao", True)
plain_paths = bake_module_atlas(plain, "probe_plain", directory, resolution=32)
ao_paths = bake_module_atlas(with_ao, "probe_ao", directory, resolution=32)
assert set(plain_paths) == set(ao_paths) == {"baseColor", "normal", "roughness", "metallic", "occlusion", "orm"}
plain_base, ao_base = pixels("prelate.probe_plain.baseColor"), pixels("prelate.probe_ao.baseColor")
assert np.max(np.abs(plain_base - ao_base)) < .005, "Source AO changed base color"
plain_ao, combined = pixels("prelate.probe_plain.occlusion"), pixels("prelate.probe_ao.occlusion")
mask = plain_ao[:,0] > .95
assert mask.any(), "Probe produced no covered AO texels"
assert np.max(np.abs(combined[mask,0] - .25)) < .012, "Source/module AO was not multiplied linearly"
orm = pixels("prelate.probe_ao.orm")
assert np.max(np.abs(orm[:,0] - combined[:,0])) < .005, "ORM red does not match final occlusion"
assert not source_node.outputs["Color"].is_linked, "Shared authored material was modified"
print("SOURCE_AO_PROBE_PASSED: six maps; base color unchanged; linear AO product; ORM red matches; source material unchanged")
print("Probe output:", directory)
