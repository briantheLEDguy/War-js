import bpy,bmesh,json
from pathlib import Path
p=Path('authoring/blender/cinderfen-nature'); rows=[]
for lod in (0,2):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str((p/'runtime'/f'frontier_cinderfen_marsh_alder_lod{lod}.glb').resolve()));o=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('root_flare'));b=bmesh.new();b.from_mesh(o.data);bmesh.ops.remove_doubles(b,verts=list(b.verts),dist=.000001)
 for e in b.edges:
  if len(e.link_faces)!=2:rows.append({'lod':lod,'vertices':[list(v.co) for v in e.verts],'faces':len(e.link_faces),'areas':[f.calc_area() for f in e.link_faces],'face_points':[[list(v.co) for v in f.verts] for f in e.link_faces]})
 b.free()
(p/'review/bad-edges.json').write_text(json.dumps(rows,indent=2))
