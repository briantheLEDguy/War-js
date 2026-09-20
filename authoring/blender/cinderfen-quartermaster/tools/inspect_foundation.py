"""Read-only measurements of the retained, original Greenskin foundation."""
import bpy, json, hashlib
from pathlib import Path
WORK=Path(__file__).resolve().parents[1]
ROOT=WORK.parents[2]
SOURCE=ROOT/'authoring/blender/frontier-population/foundations/body_mire_brutish_v1_m.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis.identity()
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in [rig,*objects]:o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
report={'source':SOURCE.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'bones':{b.name:{'head':list(b.head_local),'tail':list(b.tail_local)} for b in rig.data.bones},
 'objects':[{'name':o.name,'dimensions':list(o.dimensions),'bounds':[[min(v.co[i] for v in o.data.vertices),max(v.co[i] for v in o.data.vertices)] for i in range(3)],'vertices':len(o.data.vertices),'materials':[m.name for m in o.data.materials]} for o in objects]}
(WORK/'source/foundation-inspection.json').write_text(json.dumps(report,separators=(',',':')))
print(json.dumps(report))
