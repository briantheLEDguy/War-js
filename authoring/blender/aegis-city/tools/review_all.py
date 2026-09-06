"""Review every optimized runtime GLB in a clean Blender scene."""
import bpy
import json
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
report=json.loads((WORK/'build-report.json').read_text())
for i,asset in enumerate(report):
    bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/asset['lods'][0]['model']))
    objects=list(bpy.context.selected_objects)
    corners=[ob.matrix_world @ Vector(v) for ob in objects if ob.type=='MESH' for v in ob.bound_box]
    lo=Vector(tuple(min(v[a] for v in corners) for a in range(3)));hi=Vector(tuple(max(v[a] for v in corners) for a in range(3)))
    factor=min(1,18/max(hi.x-lo.x,hi.y-lo.y),23/max(1,hi.z-lo.z))
    for ob in objects:
        ob.location=(ob.location-Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z)))*factor
        ob.scale*=factor
        ob.location.x+=(i%8)*20
        ob.location.y+=(i//8)*26
scene=bpy.context.scene
scene.world=bpy.data.worlds.new('neutral_review'); scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.4,.43,.47,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
scene.render.engine='CYCLES';scene.cycles.samples=16
bpy.ops.object.light_add(type='AREA',location=(60,-30,100));bpy.context.object.data.energy=85000;bpy.context.object.data.size=100
bpy.ops.object.camera_add(location=(160,-170,160));cam=bpy.context.object
cam.rotation_euler=(Vector((70,67,8))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=265;scene.camera=cam
scene.render.resolution_x=2400;scene.render.resolution_y=1900;scene.render.resolution_percentage=100
scene.render.filepath=str(WORK/'review'/'all-exports.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'review'/'all-exports.blend'))
