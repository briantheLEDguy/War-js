import bpy,json,sys
from pathlib import Path
WORK=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(WORK/'runtime/frontier_cinderfen_greenskin_peat_worker_lod0.glb'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=next(a for a in bpy.data.actions if a.name.endswith('death'))
rig.animation_data.action_slot=rig.animation_data.action.slots[0]
bpy.context.scene.frame_set(61);bpy.context.view_layer.update()
print(json.dumps({b.name:{'head':list(rig.matrix_world@b.head),'tail':list(rig.matrix_world@b.tail)} for b in rig.pose.bones if b.name in ['hips','spine','chest','head','forearm_L','upper_arm_L','hand_L','thigh_L','shin_L','foot_L']}))
