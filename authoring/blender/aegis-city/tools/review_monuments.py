"""Inspect the large new exports individually at a useful framing scale."""
import bpy
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parents[1]
for kind in ['citadel','citadel_gate','citadel_arcade','citadel_bastion','mountain_massif']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/f'prop_aegis_{kind}.glb'))
    corners=[ob.matrix_world @ Vector(v) for ob in bpy.context.selected_objects if ob.type=='MESH' for v in ob.bound_box]
    lo=Vector(tuple(min(v[a] for v in corners) for a in range(3)));hi=Vector(tuple(max(v[a] for v in corners) for a in range(3)))
    center=(lo+hi)/2;extent=max(hi-lo)
    scene=bpy.context.scene;scene.world=bpy.data.worlds.new('review_daylight');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.45,.48,.52,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
    bpy.ops.object.light_add(type='AREA',location=center+Vector((.2,-.6,1.4))*extent)
    bpy.context.object.data.energy=extent*extent*35;bpy.context.object.data.size=extent
    direction=Vector((.65,1.2,.8)) if kind=='mountain_massif' else Vector((1,-1.7,.9))
    bpy.ops.object.camera_add(location=center+direction*extent);cam=bpy.context.object
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=extent*1.75;cam.data.clip_end=10000;scene.camera=cam
    scene.render.engine='CYCLES';scene.cycles.samples=20
    scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    scene.render.filepath=str(WORK/'review'/f'{kind}.png');bpy.ops.render.render(write_still=True)
