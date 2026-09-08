"""Compare Blender bone-heat binding on the original continuous skin, with measured motion."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
import rig_draft_horse as author
ROOT=author.ROOT
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'masters/frontier_draft_horse_rigged.blend'))
rig=bpy.data.objects['draft_horse_rig'];skin=bpy.data.objects['draft_continuous_skin.weighted']
rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
skin.vertex_groups.clear()
for modifier in list(skin.modifiers):
    if modifier.type=='ARMATURE':skin.modifiers.remove(modifier)
bpy.ops.object.select_all(action='DESELECT');skin.hide_set(False);skin.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
bpy.context.view_layer.objects.active=skin
bpy.ops.object.vertex_group_limit_total(limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
report=author.audit_motion(rig,[skin],[bpy.data.actions[name] for name in ['idle','walk','draft_trot']])
(ROOT/'review/frontier_draft_horse_bone_heat_trial.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'masters/frontier_draft_horse_bone_heat_trial.blend'))
print(json.dumps([{'clip':row['clip'],'worst':row['worst'],'p99':row['maximum_p99_edge_stretch']} for row in report],indent=2))
