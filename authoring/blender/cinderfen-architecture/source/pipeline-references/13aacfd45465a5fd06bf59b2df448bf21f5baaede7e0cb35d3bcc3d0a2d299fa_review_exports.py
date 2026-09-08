"""Review fresh GLB imports, including full-depth openings and hinge motion."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_architecture import render
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
        objects=load(path)
        animated='gate_leaves' in path.name
        if animated:imported_clip(objects,'gate_open')
        preview=ROOT/'review'/f'{path.stem}_reimport.png'
        render(objects,preview)
        record={'model':path.name,'sha256':sha(path),'preview':preview.name,'preview_sha256':sha(preview),'reviewer_sha256':sha(__file__)}
        if 'gatehouse' in path.name:
            record['passage']=clearance(objects,3,4.8,12)
            if path.stem.endswith('lod0'):
                front=ROOT/'review'/f'{path.stem}_front.png';render(objects,front,front=True)
                record['front_preview']=front.name;record['front_preview_sha256']=sha(front)
        if animated:
            record['clips']={name:{'start':imported_clip(objects,name),'end':imported_clip(objects,name,True)} for name in ('gate_open','gate_close')}
            imported_clip(objects,'gate_open',True)
            opened=ROOT/'review'/f'{path.stem}_opened.png';render(objects,opened)
            record['open_preview']=opened.name;record['open_preview_sha256']=sha(opened)
        (ROOT/'review'/f'{path.stem}_reimport.json').write_text(json.dumps(record,indent=2)+'\n')
        results.append(record);print('ARCHITECTURE_REIMPORTED '+path.name,flush=True)
    print(f'Reviewed {len(results)} actual GLB imports.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets')
    main(parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []))
