"""Diagnostic close side comparison of the actual delivered anatomical joints."""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from reimport_review import ROOT,sha,setup,build_evidence

key='frontier_sunmeadow_roe_deer_buck';model=ROOT/'runtime'/f'{key}_lod0.glb';digest=sha(model);evidence=build_evidence(key)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(model))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
rig.animation_data_create();rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();_,camera=setup(objects,ROOT/'review/joints.png',900,16)
center=Vector((0,-.005,.43));camera.location=center+Vector((4,0,.20));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=1.13
records=[]
for state in ['rest','run@0.125','run@0.375','run@0.625','run@0.75']:
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    if state!='rest':
        clip,phase=state.split('@');action=next(a for a in bpy.data.actions if a.name==clip);rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
        first,last=action.frame_range;frame=first+(last-first)*float(phase);bpy.context.scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
    bpy.context.view_layer.update();name=state.replace('@','_').replace('.','p');target=ROOT/'review'/f'{key}_joint_{name}.png';bpy.context.scene.render.filepath=str(target);bpy.ops.render.render(write_still=True)
    if sha(model)!=digest:raise RuntimeError('Diagnostic model changed during render')
    records.append({'state':state,'image':target.relative_to(ROOT).as_posix(),'image_sha256':sha(target),'model_sha256':digest,'build_sha256':evidence['build_sha256'],'status':'diagnostic_not_approval'})
(ROOT/'review'/f'{key}_joint_inspection.json').write_text(json.dumps({'renders':records},indent=2)+'\n')
