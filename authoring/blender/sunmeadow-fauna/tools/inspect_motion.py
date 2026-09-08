"""Measure actual reimported skin deformation, floor contact and clip contents."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from glb_sampling import animation_times,inspection_times

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect(kind,lod):
    key='frontier_sunmeadow_'+kind;model=ROOT/'runtime'/f'{key}_lod{lod}.glb';model_sha=sha(model)
    exported_times=animation_times(model.read_bytes())
    build_path=ROOT/'review'/f'{key}_build.json';build_hash=sha(build_path);build=json.loads(build_path.read_text())
    authored_clips={clip['clip']:clip for clip in build['motion']}
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(model))
    rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE');mesh=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH' and any(m.type=='ARMATURE' for m in obj.modifiers))
    rig.animation_data_create();rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    feet={limb+'_'+label:rig.pose.bones['hoof_'+limb+'_'+label].head.copy() for limb in ['front','hind'] for label in ['L','R'] if 'hoof_'+limb+'_'+label in rig.pose.bones}
    def coords():
        evaluated=mesh.evaluated_get(deps);data=np.empty(len(evaluated.data.vertices)*3,dtype=np.float32);evaluated.data.vertices.foreach_get('co',data)
        return data.reshape((-1,3))
    rest=coords();edges=np.array([edge.vertices[:] for edge in mesh.data.edges]);lengths=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1);valid=lengths>.0002
    clips=[]
    for action in bpy.data.actions:
        if not action.slots:continue
        rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];first,last=action.frame_range
        clip_name=action.name.split('|')[-1];key_times=exported_times[clip_name];samples=inspection_times(key_times)
        locomotion=authored_clips[clip_name].get('locomotion');plant_errors={foot:0 for foot in feet};plant_samples=0;worst_plant=None
        minima=np.ones(3)*math.inf;maxima=-minima.copy();stretch=0;p99=0;root_motion=0;start=None;end=None;worst=None
        for seconds in samples:
            frame=first+(last-first)*(seconds-key_times[0])/(key_times[-1]-key_times[0])
            bpy.context.scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame));bpy.context.view_layer.update();points=coords()
            minima=np.minimum(minima,points.min(axis=0));maxima=np.maximum(maxima,points.max(axis=0))
            ratios=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)[valid]/lengths[valid]
            if float(ratios.max())>stretch:
                index=np.flatnonzero(valid)[int(ratios.argmax())];a,b=edges[index]
                worst={'frame':frame,'vertices':[int(a),int(b)],'rest':[rest[a].tolist(),rest[b].tolist()],'posed':[points[a].tolist(),points[b].tolist()],
                    'weights':[{mesh.vertex_groups[g.group].name:g.weight for g in mesh.data.vertices[int(i)].groups} for i in [a,b]]}
            stretch=max(stretch,float(ratios.max()));p99=max(p99,float(np.percentile(ratios,99)))
            root=rig.pose.bones.get('root');root_motion=max(root_motion,float(root.location.length) if root else math.inf)
            if locomotion:
                for foot,rest_head in feet.items():
                    phase=(seconds/key_times[-1]+locomotion['phase_offsets'][foot])%1
                    if phase>=locomotion['stance_fraction']:continue
                    target=rest_head+Vector((0,locomotion['stride_m']*(phase/locomotion['stance_fraction']-.5),0))
                    actual=rig.pose.bones['hoof_'+foot].head;error=float((actual-target).length)
                    if worst_plant is None or error>worst_plant['error_m']:worst_plant={'foot':foot,'seconds':seconds,'frame':frame,'phase':phase,'error_m':error,'expected':list(target),'actual':list(actual)}
                    plant_errors[foot]=max(plant_errors[foot],error);plant_samples+=1
            if start is None:start=points.copy()
            end=points
        clips.append({'name':clip_name,'frames':[float(first),float(last)],'exported_key_count':len(key_times),'inspected_sample_count':len(samples),'sample_times_seconds':samples,'bounds_blender':{'min':minima.tolist(),'max':maxima.tolist()},
            'maximum_edge_stretch':stretch,'p99_edge_stretch':p99,'maximum_root_translation':root_motion,
            'loop_vertex_difference_m':float(np.linalg.norm(end-start,axis=1).max()),'worst_edge':worst,
            'locomotion':{**locomotion,'planted_foot_samples':plant_samples,'plant_error_m':plant_errors,'maximum_plant_error_m':max(plant_errors.values()),'worst_plant':worst_plant} if locomotion else None})
    if sha(model)!=model_sha:raise RuntimeError('Model changed during actual export inspection')
    if sha(build_path)!=build_hash:raise RuntimeError('Build contract changed during actual export inspection')
    report={'asset':key,'lod':lod,'model_sha256':model_sha,'build_sha256':build_hash,'inspector_sha256':sha(Path(__file__)),'sampling_helper_sha256':sha(ROOT/'tools/glb_sampling.py'),'sampling':'exported_keys_and_midpoints','vertices':len(rest),'bones':len(rig.data.bones),'clips':clips,'approval':'pending'}
    target=ROOT/'review'/f'{key}_lod{lod}_motion_inspection.json';target.write_text(json.dumps(report,indent=2)+'\n');print('FAUNA_MOTION',key,lod,[(clip['name'],round(clip['maximum_edge_stretch'],3),round(clip['p99_edge_stretch'],3),clip['locomotion']['maximum_plant_error_m'] if clip['locomotion'] else None) for clip in clips],flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--assets',default='roe_deer_buck');parser.add_argument('--lods',default='0');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for kind in args.assets.split(','):
        for lod in map(int,args.lods.split(',')):inspect(kind,lod)
