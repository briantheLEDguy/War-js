"""Evaluate current authored weight fields against retained literal bone motion."""
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import rig_draft_horse as author
import quadruped_rig as shared
ROOT=author.ROOT
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'masters/frontier_draft_horse_rigged.blend'))
rig=bpy.data.objects['draft_horse_rig'];skin=bpy.data.objects['draft_continuous_skin.weighted']
skin.vertex_groups.clear()
for modifier in list(skin.modifiers):
    if modifier.type=='ARMATURE':skin.modifiers.remove(modifier)
shared.bind_explicit_weights(skin,rig,author.skin_weights(skin,author.skeleton()))
report=author.audit_motion(rig,[skin],[bpy.data.actions[name] for name in ['idle','walk','draft_trot']])
(ROOT/'review/frontier_draft_horse_fields_trial.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'masters/frontier_draft_horse_fields_trial.blend'))
print(json.dumps([{'clip':row['clip'],'worst':row['worst'],'p99':row['maximum_p99_edge_stretch']} for row in report],indent=2))
