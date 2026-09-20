"""Verify retained packed source and continuous shirt construction."""
import bpy,hashlib,json
from pathlib import Path
WORK=Path(__file__).resolve().parents[1];master=WORK/'sources/frontier_sunmeadow_empire_field_captain.blend'
bpy.ops.wm.open_mainfile(filepath=str(master))
shirt=bpy.data.objects['shirt_continuous_tailored_surface'];edges={};neighbors={v.index:set() for v in shirt.data.vertices}
for face in shirt.data.polygons:
    v=tuple(face.vertices)
    for a,b in zip(v,v[1:]+v[:1]):
        edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1;neighbors[a].add(b);neighbors[b].add(a)
unseen=set(neighbors);components=[]
while unseen:
    queue=[unseen.pop()];count=0
    while queue:
        v=queue.pop();count+=1
        for n in neighbors[v]:
            if n in unseen:unseen.remove(n);queue.append(n)
    components.append(count)
boundary={a:set() for edge,count in edges.items() if count==1 for a in edge}
for (a,b),count in edges.items():
    if count==1:boundary[a].add(b);boundary[b].add(a)
unseen=set(boundary);loops=0
while unseen:
    queue=[unseen.pop()];loops+=1
    while queue:
        for n in boundary[queue.pop()]:
            if n in unseen:unseen.remove(n);queue.append(n)
assert len(components)==1 and loops==4 and all(len(v)==2 for v in boundary.values())
assert 'captain_fitted_brigandine' in bpy.data.objects
assert 'captain_dispatch_case' in bpy.data.objects
assert 'captain_seal_tool_sheath' in bpy.data.objects
assert len([o for o in bpy.data.objects if o.name.startswith('captain_flat_case_hanger')])==4
assert len([o for o in bpy.data.objects if o.name.startswith('captain_articulated_shoulder_lame')])==3
images={n.image for mat in bpy.data.materials if mat.use_nodes for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
assert all(i.packed_file for i in images)
modifiers=[m.type for m in shirt.modifiers];assert modifiers.index('SOLIDIFY')<modifiers.index('ARMATURE')
record={'masterSha256':hashlib.sha256(master.read_bytes()).hexdigest(),'shirtConnectedComponents':components,'shirtBoundaryLoops':loops,'shirtBoundaryValenceValid':True,'fittedBrigandine':True,'caseSuspensionLoops':4,'shoulderLames':3,'packedImages':len(images),'modifiers':modifiers,'status':'passed','scope':'Continuous source shirt torso/axilla/sleeves; fitted brigandine, joined shoulder bridges and three small articulated plates, four physical case hangers; packed editable PBR inputs. Exact exported garment/layer/tool contact measured separately.'}
(WORK/'review/master-continuity.json').write_text(json.dumps(record,indent=2)+'\n')
