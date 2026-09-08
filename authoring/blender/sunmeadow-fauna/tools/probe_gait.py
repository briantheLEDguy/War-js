"""Discardable source-pose comparisons; never produce approval receipts."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_fauna import ROOT,resolve,sha
from motion import mammal_clips
from reimport_review import setup
from gait_curves import foot_trajectory

parser=argparse.ArgumentParser();parser.add_argument('--cases',default='0.035:0.45:0.09');parser.add_argument('--render',action='store_true');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
key='frontier_sunmeadow_roe_deer_buck';report=json.loads((ROOT/'review'/f'{key}_build.json').read_text());master=ROOT/report['master']
if sha(master)!=report['master_sha256']:raise RuntimeError('Draft master hash changed')
output=ROOT/'review/probes';output.mkdir(exist_ok=True)
records=[]
for case in args.cases.split(','):
    crouch,splay,lift=map(float,case.split(':'));bpy.ops.wm.open_mainfile(filepath=str(master));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(key+'_LOD0')]
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':obj.hide_render=obj not in objects
    definition=resolve('roe_deer_buck');definition['clips']=['run'];definition['gait_controls'].update(run_body_crouch=crouch,run_hind_knee_splay=splay,run_foot_lift=lift)
    for action in list(bpy.data.actions):bpy.data.actions.remove(action,do_unlink=True)
    actions,motion=mammal_clips(rig,'roe_deer_buck',definition);rig.animation_data.action=actions[0];rig.animation_data.action_slot=actions[0].slots[0]
    obj=objects[0];edges=np.array([edge.vertices[:] for edge in obj.data.edges]);rest=np.array([v.co[:] for v in obj.data.vertices]);lengths=np.linalg.norm(rest[edges[:,1]]-rest[edges[:,0]],axis=1);valid=lengths>1e-7;maximum=percentile=plant=0
    contract=motion[0]['locomotion']
    for frame in np.arange(0,36.01,.5):
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame));bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());points=np.array([v.co[:] for v in evaluated.data.vertices]);ratios=np.linalg.norm(points[edges[:,1]]-points[edges[:,0]],axis=1)[valid]/lengths[valid];maximum=max(maximum,float(ratios.max()));percentile=max(percentile,float(np.percentile(ratios,99)))
        for foot,offset in contract['phase_offsets'].items():
            phase=(frame/36+offset)%1
            if phase>contract['stance_fraction']:continue
            name=('hoof_front_' if foot.startswith('front') else 'hoof_hind_')+foot[-1];target=rig.data.bones[name].head_local.copy();dy,dz=foot_trajectory(phase,contract['stance_fraction'],contract['stride_m'],contract['foot_lift_m']);target.y+=dy;target.z+=dz;plant=max(plant,(rig.pose.bones[name].head-target).length)
    if args.render:
        _,camera=setup(objects,output/'unused.png',720,12);center=Vector((0,-.005,.43));camera.location=center+Vector((4,0,.20));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=1.13
        for phase in [.125,.625]:
            frame=phase*36;bpy.context.scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame));target=output/f'crouch_{crouch}_splay_{splay}_lift_{lift}_phase_{phase}.png';bpy.context.scene.render.filepath=str(target);bpy.ops.render.render(write_still=True)
    records.append({'crouch':crouch,'splay':splay,'lift':lift,'maximum_stretch':maximum,'p99_stretch':percentile,'plant_error_m':plant,'motion':motion,'status':'source_diagnostic_only','master_sha256':sha(master)})
    print('GAIT_PROBE',case,maximum,percentile,plant,flush=True)
(output/'gait_probe.json').write_text(json.dumps(records,indent=2)+'\n')
