import bpy,json
from pathlib import Path
p=Path(__file__).resolve().parents[1]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(p/'runtime/frontier_sunmeadow_empire_farmer_lod0.glb'))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
for t in r.animation_data.nla_tracks:t.mute=True
r.animation_data.action=next(a for a in bpy.data.actions if a.name.endswith('death'))
if r.animation_data.action.slots:r.animation_data.action_slot=r.animation_data.action.slots[0]
bpy.context.scene.frame_set(61);bpy.context.view_layer.update()
for n in ['hips','upper_arm_L','upper_arm_R','hand_L','hand_R','foot_L','foot_R']:
 b=r.pose.bones[n];print(n,list(r.matrix_world@b.head),list(r.matrix_world@b.tail))

b=next(o for o in bpy.context.scene.objects if o.type=='MESH')
e=b.evaluated_get(bpy.context.evaluated_depsgraph_get())
for mi,m in enumerate(b.data.materials):
 ids={i for f in b.data.polygons if f.material_index==mi for i in f.vertices}
 print(m.name,min((b.matrix_world@e.data.vertices[i].co).z for i in ids))
