"""Render the actual delivered planting meshes, including all three LODs."""
import bpy
import json
from pathlib import Path
from mathutils import Vector
WORK=Path(__file__).resolve().parents[1]
report=json.loads((WORK/'build-report.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
for i,asset in enumerate(report):
    for level in range(3):
        bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime'/asset['lods'][level]['model']))
        for ob in bpy.context.selected_objects:
            ob.location.x+=(i-1.5)*7
            ob.location.y+=level*8
        curve=bpy.data.curves.new('caption','FONT');curve.body=asset['kind']+' / LOD'+str(level)
        curve.size=.36;curve.align_x='CENTER'
        ob=bpy.data.objects.new('caption',curve);bpy.context.collection.objects.link(ob)
        ob.location=((i-1.5)*7,level*8-2.6,.03)
scene=bpy.context.scene
world=bpy.data.worlds.new('overcast_studio'); world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.42,.49,.56,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.world=world
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.035))
mat=bpy.data.materials.new('studio_floor');mat.diffuse_color=(.16,.18,.17,1);bpy.context.object.data.materials.append(mat)
for pos,power,size in [((-7,-6,22),3800,12),((12,14,18),3200,10)]:
    bpy.ops.object.light_add(type='AREA',location=pos); ob=bpy.context.object
    ob.data.energy=power;ob.data.size=size
    ob.rotation_euler=(Vector((0,8,2))-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(18,-30,31));cam=bpy.context.object
cam.rotation_euler=(Vector((0,7,3))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=39;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=2200;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
scene.render.filepath=str(WORK/'review/all-exports.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'review/all-exports.blend'))
# Close view checks individual flowers, leaf silhouettes and stone edging.
cam.location=(15,-8,7);cam.rotation_euler=(Vector((7,0,.45))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=13;scene.render.resolution_y=1200
scene.render.filepath=str(WORK/'review/flowerbeds.png');bpy.ops.render.render(write_still=True)
