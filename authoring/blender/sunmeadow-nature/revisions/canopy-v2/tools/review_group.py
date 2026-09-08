"""Actual exported trees at 30/90 metres, viewed from a 1.7 metre eye height."""
import hashlib
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
records=[]
for distance,lod in [(30,1),(90,2)]:
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;models=[]
    for index,kind in enumerate(['oak_pasture','oak_hedgerow','ash']):
        model=ROOT/'runtime'/f'frontier_sunmeadow_{kind}_lod{lod}.glb';before=sha(model)
        bpy.ops.import_scene.gltf(filepath=str(model))
        for obj in bpy.context.selected_objects:
            if obj.parent is None:obj.location+=Vector(((index-1)*(12 if distance==30 else 26),distance,0))
        models.append({'model':str(model.relative_to(ROOT)),'sha256':before})
    mesh=bpy.data.meshes.new('review_ground');mesh.from_pydata([(-200,-50,0),(200,-50,0),(200,250,0),(-200,250,0)],[],[(0,1,2,3)]);mesh.update();ground=bpy.data.objects.new('review_ground',mesh);scene.collection.objects.link(ground)
    material=bpy.data.materials.new('neutral_field');material.diffuse_color=(.19,.22,.135,1);mesh.materials.append(material)
    world=bpy.data.worlds.new('daylight');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.52,.62,.75,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
    light=bpy.data.lights.new('summer_sun','SUN');light.energy=2.2;light.angle=.12;sun=bpy.data.objects.new(light.name,light);scene.collection.objects.link(sun);sun.rotation_euler=(math.radians(35),math.radians(-25),math.radians(-35))
    data=bpy.data.cameras.new('gameplay_eye');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera);camera.location=(0,0,1.7);target=Vector((0,distance,5.8));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=28;scene.camera=camera
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    output=ROOT/'review'/f'gameplay_group_{distance}m_lod{lod}.png';scene.render.filepath=str(output);scene.render.image_settings.file_format='PNG';bpy.ops.render.render(write_still=True)
    for record in models:
        if sha(ROOT/record['model'])!=record['sha256']:raise RuntimeError('Tree changed during group review')
    records.append({'distance_metres':distance,'lod':lod,'camera_height':1.7,'lens_mm':28,'models':models,'image':str(output.relative_to(ROOT)),'image_sha256':sha(output)})
    (ROOT/'review/gameplay_group_receipt.json').write_text(json.dumps({'views':records,'approval':'pending'},indent=2)+'\n')
