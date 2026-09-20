"""Measure attachment supports on the literal editable anatomical surface."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
WORK=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(WORK/'sources/frontier_sunmeadow_high_elf_scout.blend'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
records={}
for obj in bpy.context.scene.objects:
    if obj.type!='MESH' or not ('high-poly' in obj.name or 'exposed_anatomy' in obj.name):continue
    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    records[obj.name]={'bounds':{'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]},'materials':[m.name for m in obj.data.materials]}
body=bpy.data.objects['high_elf_scout_exposed_anatomy'];tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
records['headBack']={}
for z in [1.80,1.83,1.85,1.87,1.9,1.92]:
    hit=tree.ray_cast(Vector((0,2,z)),Vector((0,-1,0)))[0]
    records['headBack'][str(z)]=list(hit) if hit else None
(WORK/'review/draft-attachment-supports.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records))
