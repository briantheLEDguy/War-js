"""Identify detail reduction that would open a previously closed authored component."""
import json
from pathlib import Path
import sys
import bpy
import bmesh
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_architecture import SOURCE,ROOT,material,prototype
bpy.ops.wm.read_factory_settings(use_empty=True)
materials={name:material(name) for name in SOURCE['materials']}
report=[]
for lod in (0,1,2):
    collection=bpy.data.collections.new('Cage_audit_'+str(lod));bpy.context.scene.collection.children.link(collection)
    for name in SOURCE['parts']:
        obj,data=prototype(name,lod,materials,collection)
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
        boundary=sum(len(e.link_faces)==1 for e in bm.edges);multiple=sum(len(e.link_faces)>2 for e in bm.edges)
        report.append({'part':name,'lod':lod,'triangles':len(bm.faces),'boundary':boundary,'multiple':multiple});bm.free()
(ROOT/'review/cage_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([r for r in report if r['boundary'] or r['multiple']],indent=2))
