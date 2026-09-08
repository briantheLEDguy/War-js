"""Clean GLB imports, measured bounds and fixed neutral PBR review views."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def build_evidence(key):
    file=ROOT/'review'/f'{key}_build.json';build=json.loads(file.read_text())
    if not build.get('source_files') or len(build.get('texture_sources',{}))!=3:
        raise RuntimeError('A build with complete source and texture hashes is required')
    files={**build['source_files'],**build['texture_sources'],build['master']:build['master_sha256'],build['cage']:build['cage_sha256']}
    for name,digest in files.items():
        if sha(ROOT/name)!=digest:raise RuntimeError('Changed authored build dependency: '+name)
    return {'build_sha256':sha(file),'authored_files':files,'lod0_bounds_blender':build['lods'][0]['bounds_blender']}

def setup(objects,output,size_pixels=1200,samples=24):
    scene=bpy.context.scene
    bounds=[obj.matrix_world@vertex.co for obj in objects for vertex in obj.data.vertices]
    low=Vector([min(v[i] for v in bounds) for i in range(3)]); high=Vector([max(v[i] for v in bounds) for i in range(3)])
    center=(low+high)/2; span=high-low; size=max(span.x,span.y,span.z)
    ground=bpy.data.meshes.new('review_surface');ground.from_pydata([(-100,-100,-.001),(100,-100,-.001),(100,100,-.001),(-100,100,-.001)],[],[(0,1,2,3)]);ground.update()
    floor=bpy.data.objects.new('review_surface',ground);scene.collection.objects.link(floor)
    material=bpy.data.materials.new('review_neutral_slate');material.diffuse_color=(.115,.135,.145,1);floor.data.materials.append(material)
    world=bpy.data.worlds.new('neutral_daylight');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.52,.61,.73,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=world
    for index,(position,power) in enumerate([((-size*.65,-size*.8,size*1.8),size*size*85),((size*.8,size*.7,size*1.5),size*size*65)]):
        data=bpy.data.lights.new(f'studio_area_{index}','AREA');data.energy=power;data.shape='DISK';data.size=size*.8
        light=bpy.data.objects.new(data.name,data);scene.collection.objects.link(light);light.location=Vector(position)+center;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('export_review_camera');camera=bpy.data.objects.new('export_review_camera',data);scene.collection.objects.link(camera)
    direction=Vector((1.3,-1.5,.40)).normalized()
    camera.location=center+direction*size*3;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=size*1.3;scene.camera=camera
    scene.render.engine='CYCLES';scene.cycles.samples=samples;scene.cycles.use_denoising=True
    scene.render.resolution_x=size_pixels;scene.render.resolution_y=size_pixels;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(output)
    return {'min':list(low),'max':list(high),'span':list(span)},camera

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default='roe_deer_buck');parser.add_argument('--lods',default='0');parser.add_argument('--states',default='rest');parser.add_argument('--size',type=int,default=1200);parser.add_argument('--samples',type=int,default=24);parser.add_argument('--view',choices=['full','profile','front','rear','head'],default='full');parser.add_argument('--focus');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    records=[]
    for kind in args.assets.split(','):
        key='frontier_sunmeadow_'+kind
        evidence=build_evidence(key)
        receipt=ROOT/'review'/f'{key}_renders.json'
        if receipt.exists():
            for record in json.loads(receipt.read_text()).get('renders',[]):
                model_path=ROOT/'runtime'/record['model'];image_path=ROOT/record['image']
                if model_path.exists() and image_path.exists() and sha(model_path)==record['model_sha256'] and sha(image_path)==record['image_sha256'] and record.get('build_sha256')==evidence['build_sha256'] and record.get('reviewer_source_sha256')==sha(__file__):records.append(record)
        for lod in map(int,args.lods.split(',')):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            model=ROOT/'runtime'/f'{key}_lod{lod}.glb';model_hash=sha(model);bpy.ops.import_scene.gltf(filepath=str(model))
            objects=[ob for ob in bpy.context.scene.objects if ob.type=='MESH' and any(m.type=='ARMATURE' for m in ob.modifiers)];rig=next(ob for ob in bpy.context.scene.objects if ob.type=='ARMATURE')
            rig.animation_data_create();rig.animation_data.action=None
            for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
            bpy.context.view_layer.update()
            output=ROOT/'review'/f'{key}_lod{lod}_reimport.png';bounds,camera=setup(objects,output,args.size,args.samples)
            reference=evidence['lod0_bounds_blender'];center=(Vector(reference['min'])+Vector(reference['max']))/2;span=max(Vector(reference['max'])-Vector(reference['min']));camera.data.ortho_scale=span*1.3
            direction=Vector((1,0,.12) if args.view=='profile' else (0,-1,.12) if args.view=='front' else (0,1,.12) if args.view=='rear' else (1.3,-1.5,.40)).normalized()
            if args.focus:
                values=list(map(float,args.focus.split(',')))
                if len(values)!=4 or values[3]<=0:raise ValueError('--focus requires x,y,z,positive-span')
                center=Vector(values[:3]);span=values[3];camera.data.ortho_scale=span
            camera.location=center+direction*span*3;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
            for state in args.states.split(','):
                clip,_,fraction=state.partition('@');rig.animation_data.action=None
                for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
                if clip!='rest':
                    action=next(a for a in bpy.data.actions if a.name.split('|')[-1]==clip)
                    rig.animation_data.action=action
                    if action.slots:rig.animation_data.action_slot=action.slots[0]
                    first,last=action.frame_range;position=first+(last-first)*float(fraction or 0)
                    bpy.context.scene.frame_set(math.floor(position),subframe=position-math.floor(position))
                bpy.context.view_layer.update();suffix='' if state=='rest' else '_'+state.replace('@','_').replace('.','p')
                view_suffix='' if args.view=='full' else '_'+args.view
                output=ROOT/'review'/f'{key}_lod{lod}{suffix}{view_suffix}_reimport.png';bpy.context.scene.render.filepath=str(output)
                bpy.ops.render.render(write_still=True)
                if lod==0 and state=='rest' and args.view=='full':bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'review'/f'{key}_reimport.blend'),compress=True)
                if sha(model)!=model_hash:raise RuntimeError('Export changed while its review image was rendering: '+model.name)
                if build_evidence(key)!=evidence:raise RuntimeError('Authored source changed while rendering its export')
                evaluated=bpy.context.evaluated_depsgraph_get();points=[obj.matrix_world@v.co for obj in objects for v in obj.evaluated_get(evaluated).data.vertices]
                pose_bounds={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
                records=[r for r in records if not(r['asset']==key and r['level']==lod and r['state']==state and r.get('view','full')==args.view)]
                records.append({'asset':key,'level':lod,'state':state,'view':args.view,'focus':args.focus,'model':model.name,'model_sha256':model_hash,**evidence,'reviewer_source_sha256':sha(__file__),'image':str(output.relative_to(ROOT)),'image_sha256':sha(output),'bounds_blender':bounds,'pose_bounds_blender':pose_bounds,'renderer':f'Cycles {args.samples} samples, {args.size}px, AgX, fixed daylight studio','decision':'pending'})
                (ROOT/'review'/f'{key}_renders.json').write_text(json.dumps({'renders':[r for r in records if r['asset']==key],'visual_approval':False},indent=2)+'\n')
                print('FAUNA_REIMPORT',key,lod,state,flush=True)

if __name__=='__main__':main()
