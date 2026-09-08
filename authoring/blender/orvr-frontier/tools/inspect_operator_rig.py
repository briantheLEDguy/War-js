"""Read-only inspection of the existing approved equipped character master."""
from pathlib import Path
import json
import bpy
ROOT=Path(__file__).resolve().parents[1]
path=ROOT.parent/'battle-prelate-novitiate-set/battle_prelate_novitiate_game_master.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
print(json.dumps({'rigs':[{'name':obj.name,'bones':list(obj.data.bones.keys())} for obj in bpy.context.scene.objects if obj.type=='ARMATURE'],
  'visible_meshes':[{'name':obj.name,'vertices':len(obj.data.vertices),'parent':obj.parent.name if obj.parent else None,'modifiers':[modifier.type for modifier in obj.modifiers]} for obj in bpy.context.scene.objects if obj.type=='MESH' and not obj.hide_render]},indent=2))
