"""Source-only replacement-hoof form proof on the imported buck; not approval."""
import sys
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fauna import ROOT, resolve, Cage, atlas
from hoof_geometry import add_deer_hoof
from quadruped_rig import bind_explicit_weights
from imported_actions import activate_imported_clip
from reimport_review import setup

base = ROOT/'review/candidates/buck_differential'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(base/'frontier_sunmeadow_roe_deer_buck_lod0.glb'))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
body = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers))
activate_imported_clip(rig, [body], 'rest'); bpy.context.view_layer.update()
body.shape_key_clear()
# Separate old horn components by their actual atlas and distal location.
mesh = bmesh.new(); mesh.from_mesh(body.data); uv = mesh.loops.layers.uv.active
faces = [f for f in mesh.faces if max(v.co.z for v in f.verts)<.08 and all(.5<=l[uv].uv.x<.75 and l[uv].uv.y<.5 for l in f.loops)]
if not faces: raise RuntimeError('Could not identify original horn geometry')
bmesh.ops.delete(mesh, geom=faces, context='FACES')
mesh.to_mesh(body.data); mesh.free(); body.data.update()
definition = resolve('roe_deer_buck'); cage = Cage()
for side, label in [(1, 'L'), (-1, 'R')]:
    for limb in ['front', 'hind']:
        add_deer_hoof(cage, definition[limb+'_leg'][-1], side, label, limb, 0, atlas)
material = bpy.data.materials.new('hoof_form_study'); material.use_nodes = True
bsdf = material.node_tree.nodes.get('Principled BSDF'); bsdf.inputs['Base Color'].default_value = (.023, .016, .011, 1); bsdf.inputs['Roughness'].default_value = .68
hoof = cage.object('authored_cloven_horn_form_study', material)
for vertex in hoof.data.vertices: vertex.co *= definition['scale']
bind_explicit_weights(hoof, rig, cage.weights); hoof.parent = None
for full in [False, True]:
    target = ROOT/'review/probes'/('new_hoof_full.png' if full else 'new_hoof_junction.png')
    _, camera = setup([body, hoof], target, 1000, 20)
    center = Vector((0, -.17, .64) if full else (.11, -.33, .07)); camera.location = center+Vector((3, -2.1, .5))
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler(); camera.data.ortho_scale = 1.65 if full else .24
    bpy.ops.render.render(write_still=True)
    print('HOOF_FORM_PROOF', target, flush=True)
