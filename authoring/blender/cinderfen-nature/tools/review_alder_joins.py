"""Neutral actual-GLB close view of the lower bole and limb/root interfaces."""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
file=ROOT/'runtime/frontier_cinderfen_marsh_alder_lod0.glb';bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(file))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('neutral_join_world');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.25,.25,.25,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
target=Vector((0,0,2.42));camera_data=bpy.data.cameras.new('lower_bole_joint_camera');camera=bpy.data.objects.new('lower_bole_joint_camera',camera_data);scene.collection.objects.link(camera);scene.camera=camera
camera.location=Vector((3.5,-7.2,3.4));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=5.5
for name,position,power in [('key',(-4,-6,8),1800),('fill',(6,-3,5),1300),('rim',(0,6,8),1600)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=5
    light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=Vector(position);light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
scene.view_settings.view_transform='AgX';image=ROOT/'review/frontier_cinderfen_marsh_alder_lod0_lower_joins.png';scene.render.filepath=str(image);bpy.ops.render.render(write_still=True)
(ROOT/'review/alder-join-view.json').write_text(json.dumps({'model':file.name,'modelSha256':sha(file),'toolSha256':sha(Path(__file__)),'image':image.name,'imageSha256':sha(image),'camera':{'position_z_up':list(camera.location),'target_z_up':list(target),'projection':'ORTHO','frame_m':5.5},'lighting':'Neutral white lights with unmodified exported PBR'},indent=2)+'\n')
