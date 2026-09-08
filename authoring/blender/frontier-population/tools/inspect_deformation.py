"""Inspect garment weights and actual bone directions without changing the source."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

work = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(work / 'sources/frontier_sunmeadow_dwarf_artisan.blend'))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
actions = {action.name: action for action in bpy.data.actions}
for track in rig.animation_data.nla_tracks: track.mute = True
records=[]
for clip,frame in [('idle',1),('walk',9),('death',60),('jump',20)]:
    action=actions[clip];rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
    bones={name:{'head':list(rig.pose.bones[name].head),'tail':list(rig.pose.bones[name].tail),
                 'restHead':list(rig.data.bones[name].head_local),'restTail':list(rig.data.bones[name].tail_local)}
           for name in ['hips','thigh_L','shin_L','foot_L','toe_L','thigh_R','shin_R','foot_R','toe_R',
                        'upper_arm_L','forearm_L','hand_L','upper_arm_R','forearm_R','hand_R']}
    meshes={}
    for o in bpy.context.scene.objects:
        if o.type!='MESH' or 'fitted_boot' not in o.name:continue
        weights={g.name:sum(next((entry.weight for entry in v.groups if entry.group==g.index),0) for v in o.data.vertices) for g in o.vertex_groups}
        evaluated=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
        meshes[o.name]={'weights':weights,'bounds':[list(evaluated.matrix_world@Vector(c)) for c in evaluated.bound_box]}
    records.append({'clip':clip,'frame':frame,'bones':bones,'meshes':meshes})
(work/'review/deformation-inspection.json').write_text(json.dumps(records,indent=2))
