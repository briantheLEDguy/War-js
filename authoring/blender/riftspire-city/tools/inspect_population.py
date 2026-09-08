import bpy
from pathlib import Path
root=Path.cwd()
for file in ['chr_aegis_city_guard_standard.glb','chr_aegis_people_courtier_lod1.glb']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(root/'public/assets/models'/file))
 print('MODEL',file)
 for ob in bpy.context.scene.objects:
  if ob.type=='MESH':print('PART',ob.name,len(ob.data.polygons),list(ob.dimensions),[m.name for m in ob.data.materials])
  if ob.type=='ARMATURE':print('BONES',[(b.name,list(b.head_local),list(b.tail_local)) for b in ob.data.bones if 'head' in b.name.lower() or 'spine' in b.name.lower()])
