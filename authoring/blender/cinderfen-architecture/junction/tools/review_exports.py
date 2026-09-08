"""Review fresh GLB imports, including full-depth openings and hinge motion."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(objects,path,front=False,gameplay_distance=None,side=False):
    """Neutral physical-light review and honest perspective distance views."""
    for item in list(bpy.data.objects):
        if item.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(item,do_unlink=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16 if gameplay_distance else 24
    scene.render.resolution_x=1280 if gameplay_distance else 1400;scene.render.resolution_y=720 if gameplay_distance else 1050;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.world=bpy.data.worlds.new('neutral_reimport_world');scene.world.color=(.18,.18,.18)
    points=[obj.matrix_world@Vector(corner) for obj in objects for corner in obj.bound_box]
    lower=Vector([min(p[i] for p in points) for i in range(3)]);upper=Vector([max(p[i] for p in points) for i in range(3)]);centre=(lower+upper)/2;extent=max(upper-lower)
    data=bpy.data.cameras.new('actual_export_review');camera=bpy.data.objects.new('actual_export_review',data);scene.collection.objects.link(camera)
    if gameplay_distance:
        camera.location=Vector((centre.x+extent*.35,centre.y-gameplay_distance,5.4));target=Vector((centre.x,centre.y,min(centre.z,4.4)))
        data.type='PERSP';data.lens=38;data.clip_end=1000
    else:
        camera.location=centre+Vector((extent*1.65 if side else extent*.95 if not front else 0,-extent*.30 if side else -extent*1.5,extent*.58 if side else extent*.85 if not front else extent*.05));target=centre;data.type='ORTHO'
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
    if not gameplay_distance:
        inverse=camera.rotation_euler.to_matrix().transposed();projected=[inverse@(point-centre) for point in points]
        width=max(p.x for p in projected)-min(p.x for p in projected);height=max(p.y for p in projected)-min(p.y for p in projected)
        data.ortho_scale=max(width,height*scene.render.resolution_x/scene.render.resolution_y)*1.14
    for name,delta,power,size in [('key',(-4,-6,8),950,5),('fill',(6,-3,5),650,5),('rim',(0,6,8),850,5)]:
        light_data=bpy.data.lights.new(name,'AREA');light_data.energy=power*(extent/7)**2;light_data.shape='DISK';light_data.size=size*extent/7;light_data.color=(1,1,1)
        light=bpy.data.objects.new(name,light_data);scene.collection.objects.link(light);light.location=centre+Vector(delta)*extent/7;light.rotation_euler=(centre-light.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.view_transform='AgX';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    return {'camera_position_z_up':list(camera.location),'target_z_up':list(target),'projection':data.type,'lens_mm':data.lens if gameplay_distance else None,'distance_m':gameplay_distance,'lighting':'neutral white area lights; unmodified exported PBR channels','resolution':[scene.render.resolution_x,scene.render.resolution_y]}


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.scene.frame_set(1)
    return [obj for obj in bpy.context.scene.objects if obj.type=='MESH']


def clearance(objects,half_width,height,depth):
    vertices=[];faces=[]
    for obj in objects:
        offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons)
    tree=BVHTree.FromPolygons(vertices,faces)
    samples=0;hits=[]
    for xi in range(31):
        x=-half_width+.02+xi*(2*half_width-.04)/30
        for zi in range(25):
            z=.25+zi*(height-.27)/24;samples+=1
            point,_,_,distance=tree.ray_cast(Vector((x,-depth/2-.8,z)),Vector((0,1,0)),depth+1.6)
            if point is not None:hits.append({'x':x,'height':z,'hit':list(point)})
    return {'width_m':half_width*2,'minimum_height_m':height,'full_depth_m':depth,'ray_samples':samples,'surface_tolerance_m':.02,'floor_clearance_m':.25,'blocked_rays':hits}


def imported_clip(objects,name,end=False):
    for obj in objects:
        if not obj.animation_data:continue
        obj.animation_data.action=None
        for track in obj.animation_data.nla_tracks:track.mute=track.name!=name
    # glTF importer reconstructs each clip at the same start frame.
    tracks=[track for obj in objects if obj.animation_data for track in obj.animation_data.nla_tracks if track.name==name]
    if not tracks:raise RuntimeError(f'Missing imported clip: {name}')
    frame=max(strip.frame_end for track in tracks for strip in track.strips) if end else min(strip.frame_start for track in tracks for strip in track.strips)
    bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame))
    bpy.context.view_layer.update()
    return {obj.name:{'location':list(obj.location),'quaternion':list(obj.rotation_quaternion),'world_matrix':[list(row) for row in obj.matrix_world]} for obj in objects}


def main(args):
    results=[]
    for path in sorted((ROOT/'runtime').glob('*.glb')):
        if args.assets and not any(path.name.startswith(name+'_lod') for name in args.assets.split(',')):continue
        if int(path.stem[-1]) not in args.lods:continue
        receipt=ROOT/'review'/f'{path.stem}_reimport.json'
        if args.resume and receipt.exists():
            previous=json.loads(receipt.read_text());views=[('preview','preview_sha256')]+[(prefix+'_preview',prefix+'_preview_sha256') for prefix in ('front','open','gameplay','side') if prefix+'_preview' in previous]
            if previous.get('sha256')==sha(path) and previous.get('reviewer_sha256')==sha(__file__) and all((ROOT/'review'/previous[name]).exists() and sha(ROOT/'review'/previous[name])==previous[digest] for name,digest in views):
                print('RETAINED_VALID_REIMPORT '+path.name,flush=True);continue
        objects=load(path)
        animated='gate_leaves' in path.name
        if animated:imported_clip(objects,'gate_open')
        preview=ROOT/'review'/f'{path.stem}_reimport.png'
        neutral=render(objects,preview)
        distance=[40,90,160][int(path.stem[-1])];game=ROOT/'review'/f'{path.stem}_gameplay.png';game_camera=render(objects,game,gameplay_distance=distance)
        record={'model':path.name,'sha256':sha(path),'preview':preview.name,'preview_sha256':sha(preview),'reviewer_sha256':sha(__file__),'neutral_camera':neutral,'gameplay_preview':game.name,'gameplay_preview_sha256':sha(game),'gameplay_camera':game_camera}
        if 'gatehouse' in path.name:
            record['passage']=clearance(objects,3,4.8,12)
            if path.stem.endswith('lod0'):
                front=ROOT/'review'/f'{path.stem}_front.png';render(objects,front,front=True)
                record['front_preview']=front.name;record['front_preview_sha256']=sha(front)
        if animated:
            record['clips']={name:{'start':imported_clip(objects,name),'end':imported_clip(objects,name,True)} for name in ('gate_open','gate_close')}
            imported_clip(objects,'gate_open',True)
            record['opened_passage']=clearance(objects,3,4.8,6.5)
            opened=ROOT/'review'/f'{path.stem}_opened.png';render(objects,opened)
            record['open_preview']=opened.name;record['open_preview_sha256']=sha(opened)
        if 'wall_stair' in path.name and path.stem.endswith('lod0'):
            side=ROOT/'review'/f'{path.stem}_side.png';render(objects,side,side=True);record['side_preview']=side.name;record['side_preview_sha256']=sha(side)
        (ROOT/'review'/f'{path.stem}_reimport.json').write_text(json.dumps(record,indent=2)+'\n')
        results.append(record);print('ARCHITECTURE_REIMPORTED '+path.name,flush=True)
    print(f'Reviewed {len(results)} actual GLB imports.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets');parser.add_argument('--lods',default='0,1,2');parser.add_argument('--resume',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);args.lods=list(map(int,args.lods.split(',')));main(args)
