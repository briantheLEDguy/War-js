"""Source-only preview of continuous basalt material on the finished master."""
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from bake_basalt_projection import bake_basalt
from review_nature import render
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'masters/frontier_cinderfen_basalt_outcrop.blend'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
if len(objects)!=1:raise RuntimeError('Expected one authored basalt material batch')
obj=objects[0];bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
for modifier in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=modifier.name)
print('BASALT_SOURCE_PROOF_TRIANGLES',len(obj.data.polygons),flush=True)
bake_basalt(obj,0,preview_only=True)
render(objects,ROOT/'review/diagnostic_basalt_material_source.png',detail=True)
