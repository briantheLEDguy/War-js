"""Source-only pose-space envelope proof; no publication or approval receipt."""
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_fauna import ROOT,resolve
from reimport_review import setup
from corrective_fields import haunch_envelope

key='frontier_sunmeadow_roe_deer_buck';definition=resolve('roe_deer_buck');scale=definition['scale']
for phase in [.125,.375]:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(ROOT/'runtime'/f'{key}_lod0.glb'))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers));rest=np.array([v.co[:] for v in obj.data.vertices])/scale
    action=next(a for a in bpy.data.actions if a.name=='run');rig.animation_data_create();rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];first,last=action.frame_range;frame=first+(last-first)*phase;bpy.context.scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame));bpy.context.view_layer.update()
    carrier=rig.pose.bones['pelvis'].matrix@rig.data.bones['pelvis'].matrix_local.inverted();inverse=carrier.inverted();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.data.copy();posed=np.array([(inverse@v.co)[:] for v in mesh.vertices])/scale;delta=np.zeros_like(posed)
    for side,label in [(1,'L'),(-1,'R')]:
        hip=np.array((inverse@rig.pose.bones['thigh_'+label].head)[:])/scale;knee=np.array((inverse@rig.pose.bones['thigh_'+label].tail)[:])/scale;delta+=haunch_envelope(rest,posed,definition,side,hip,knee)
    for vertex,point in zip(mesh.vertices,posed+delta):vertex.co=carrier@Vector(point*scale)
    obj.modifiers.clear();obj.data=mesh;mesh.update();obj.hide_set(False)
    target=ROOT/'review/probes'/f'haunch_envelope_{phase}.png';_,camera=setup([obj],target,900,16);center=Vector((0,-.005,.43));camera.location=center+Vector((4,0,.20));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=1.13;bpy.context.scene.render.filepath=str(target);bpy.ops.render.render(write_still=True)
    print('CORRECTIVE_PROBE',phase,float(np.linalg.norm(delta,axis=1).max()),int(np.count_nonzero(np.linalg.norm(delta,axis=1)>1e-5)),flush=True)
