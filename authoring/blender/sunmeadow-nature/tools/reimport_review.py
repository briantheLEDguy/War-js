"""Clean GLB imports, measured bounds and fixed neutral PBR review views."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def setup(objects,output):
    scene=bpy.context.scene
    bounds=[obj.matrix_world@Vector(corner) for obj in objects for corner in obj.bound_box]
    low=Vector([min(v[i] for v in bounds) for i in range(3)]); high=Vector([max(v[i] for v in bounds) for i in range(3)])
    center=(low+high)/2; span=high-low; size=max(span.x,span.y,span.z)
    ground=bpy.data.meshes.new('review_surface');ground.from_pydata([(-100,-100,-.025),(100,-100,-.025),(100,100,-.025),(-100,100,-.025)],[],[(0,1,2,3)]);ground.update()
    floor=bpy.data.objects.new('review_surface',ground);scene.collection.objects.link(floor)
    material=bpy.data.materials.new('review_neutral_slate');material.diffuse_color=(.115,.135,.145,1);floor.data.materials.append(material)
    world=bpy.data.worlds.new('neutral_daylight');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.52,.61,.73,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=world
    for index,(position,power) in enumerate([((-size*.65,-size*.8,size*1.8),size*size*85),((size*.8,size*.7,size*1.5),size*size*65)]):
        data=bpy.data.lights.new(f'studio_area_{index}','AREA');data.energy=power;data.shape='DISK';data.size=size*.8
        light=bpy.data.objects.new(data.name,data);scene.collection.objects.link(light);light.location=Vector(position)+center;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('export_review_camera');camera=bpy.data.objects.new('export_review_camera',data);scene.collection.objects.link(camera)
    direction=Vector((.74,-1.25,.62 if span.z>2.8 else .95)).normalized()
    camera.location=center+direction*size*3;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=size*1.3;scene.camera=camera
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(output)
    return {'min':list(low),'max':list(high),'span':list(span)},camera

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default='oak_pasture,oak_hedgerow,ash,hawthorn,wheat,meadow,limestone');parser.add_argument('--lods',default='0,1,2');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    records=[]
    for kind in args.assets.split(','):
        key='frontier_sunmeadow_'+kind
        for lod in map(int,args.lods.split(',')):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            model=ROOT/'runtime'/f'{key}_lod{lod}.glb';model_hash=sha(model);bpy.ops.import_scene.gltf(filepath=str(model))
            objects=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
            output=ROOT/'review'/f'{key}_lod{lod}_reimport.png';bounds,camera=setup(objects,output)
            bpy.ops.render.render(write_still=True)
            if lod==0:bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'review'/f'{key}_reimport.blend'),compress=True)
            if sha(model)!=model_hash:raise RuntimeError('Export changed while its review image was rendering: '+model.name)
            records.append({'asset':key,'level':lod,'model':model.name,'model_sha256':model_hash,'image':str(output.relative_to(ROOT)),'image_sha256':sha(output),'bounds_blender':bounds,'renderer':'Cycles 24 samples, AgX, fixed daylight studio','decision':'pending'})
            (ROOT/'review'/f'{key}_renders.json').write_text(json.dumps({'renders':[r for r in records if r['asset']==key],'visual_approval':False},indent=2)+'\n')
            print('NATURE_REIMPORT',key,lod,flush=True)

if __name__=='__main__':main()
