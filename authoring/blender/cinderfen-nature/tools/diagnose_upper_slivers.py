"""Inspect the topology of the isolated upper-bole tangent defect."""
import json,sys
from pathlib import Path
import bpy,bmesh
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build_nature import SOURCE,material,joined_bark
from fair_bark_junctions import fair_junctions
bpy.ops.wm.read_factory_settings(use_empty=True)
collection=bpy.data.collections.new('Diagnosis');bpy.context.scene.collection.children.link(collection)
materials={name:material(name) for name in SOURCE['materials']}
source=SOURCE['assets']['frontier_cinderfen_marsh_alder']['lods'][0]['objects'][0]
obj=joined_bark(source,0,materials,collection)
record=fair_junctions(obj,0)
bm=bmesh.new();bm.from_mesh(obj.data)
rows=[]
for edge in bm.edges:
    if edge.calc_length()<.0015 and all(8.2<v.co.z<8.35 for v in edge.verts):
        rows.append({'length':edge.calc_length(),'verts':[list(v.co) for v in edge.verts],'faces':[{'verts':len(f.verts),'lengths':[e.calc_length() for e in f.edges]} for f in edge.link_faces]})
record['candidates']=rows
remaining=set(bm.verts);comps=[]
while remaining:
    seed=remaining.pop();component={seed};queue=[seed]
    while queue:
        for edge in queue.pop().link_edges:
            other=edge.other_vert(next(v for v in edge.verts if v in component))
            if other in remaining:remaining.remove(other);component.add(other);queue.append(other)
    if any(abs(v.co.z-8.275524)<.000001 for v in component) or (min(v.co.z for v in component)<0 and max(v.co.z for v in component)>9):
        comps.append({'count':len(component),'minz':min(v.co.z for v in component),'maxz':max(v.co.z for v in component),'target':any(abs(v.co.z-8.275524)<.000001 for v in component)})
record['components']=comps
(ROOT/'review/upper_sliver_diagnosis.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record['components'],indent=2))
