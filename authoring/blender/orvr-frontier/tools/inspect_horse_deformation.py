"""Locate actual skin strain in a retained animated master before changing weights."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import quadruped_rig as shared
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'masters/frontier_draft_horse_rigged.blend'))
rig=bpy.data.objects['draft_horse_rig'];obj=bpy.data.objects['draft_continuous_skin.weighted']
original=np.array([v.co[:] for v in obj.data.vertices]);edges=np.array([e.vertices[:] for e in obj.data.edges])
base=np.linalg.norm(original[edges[:,0]]-original[edges[:,1]],axis=1)
records=[]
for name,frame in [('walk',4),('draft_trot',4)]:
    shared.pin_action(rig,bpy.data.actions[name],frame)
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    current=np.array([v.co[:] for v in mesh.vertices]);ratio=np.linalg.norm(current[edges[:,0]]-current[edges[:,1]],axis=1)/base
    samples=[]
    for index in np.argsort(ratio)[-12:][::-1]:
        vertices=edges[index];samples.append({'ratio':float(ratio[index]),'midpoint':list(original[vertices].mean(axis=0)),
          'vertices':[{'position':list(original[i]),'weights':{obj.vertex_groups[g.group].name:g.weight for g in obj.data.vertices[i].groups}} for i in vertices]})
    records.append({'clip':name,'frame':frame,'samples':samples});evaluated.to_mesh_clear()
(ROOT/'review/frontier_draft_horse_strain_locations.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
