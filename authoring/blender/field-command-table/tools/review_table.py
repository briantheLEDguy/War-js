"""Review exact runtime GLBs, reimported with delivered PBR and no image editing."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build_table import KEY,audit,sha,save

def render(objects,path,view,lod):
    scene=bpy.context.scene
    for item in list(scene.objects):
        if item.type in('LIGHT','CAMERA'):bpy.data.objects.remove(item,do_unlink=True)
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.world=bpy.data.worlds.new('neutral_original_pbr_review');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.18,.19,.20,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
    target=Vector((0,0,.47));direction=Vector((2.6,-4,2.75));frame=2.65
    if view=='rear':direction=Vector((-2.8,4,2.4))
    if view=='detail':target=Vector((.03,-.01,.883));direction=Vector((.2,-.7,3.8));frame=1.93
    if view=='joinery':target=Vector((-.61,-.02,.31));direction=Vector((-2,-4,1.6));frame=.9
    data=bpy.data.cameras.new('actual_GL B_review'.replace(' ',''));camera=bpy.data.objects.new('review_camera',data);scene.collection.objects.link(camera);scene.camera=camera
    camera.location=target+direction;data.type='ORTHO';data.ortho_scale=frame
    if view=='gameplay':camera.location=Vector((.6,-(4,12,24)[lod],1.72));data.type='PERSP';data.lens=38;scene.render.resolution_x=1280;scene.render.resolution_y=720
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    for name,position,power,size in [('key',(-3,-4,5),650,3),('fill',(4,-2,3),380,3),('rim',(0,4,5),550,2.5)]:
        lamp=bpy.data.lights.new(name,'AREA');lamp.energy=power;lamp.shape='DISK';lamp.size=size
        obj=bpy.data.objects.new(name,lamp);scene.collection.objects.link(obj);obj.location=position;obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.view_transform='AgX';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    return {'cameraZUp':list(camera.location),'targetZUp':list(target),'projection':data.type,'orthoScale':frame if data.type=='ORTHO' else None,'distanceM':(4,12,24)[lod] if view=='gameplay' else None,'lighting':'neutral white area lights, actual exported PBR, no retouching'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--lods',default='0,1,2');parser.add_argument('--views',default='neutral,gameplay');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for lod in map(int,args.lods.split(',')):
        model=ROOT/'runtime'/f'{KEY}_lod{lod}.glb';bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(model));objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];result=audit(objects)
        record={'model':model.name,'sha256':sha(model),'reviewerSha256':sha(Path(__file__)),'audit':result,'views':{}}
        if result['boundary'] or result['multi'] or result['loose']:
            save(ROOT/'review'/f'{KEY}_lod{lod}_reimport-failure.json',record);raise RuntimeError('Actual exported topology failed')
        target=ROOT/'review'/f'{KEY}_lod{lod}_reimport.json'
        if target.exists():
            previous=json.loads(target.read_text())
            if previous['sha256']==record['sha256']:record['views']=previous['views']
        for view in args.views.split(','):
            image=ROOT/'review'/f'{KEY}_lod{lod}_{view}.png';camera=render(objects,image,view,lod)
            record['views'][view]={'image':image.name,'sha256':sha(image),'camera':camera};save(target,record)
        print('COMMAND_TABLE_REIMPORTED',lod,result['triangles'],flush=True)
