"""Verify retained packed source and continuous shirt construction."""
import bpy,hashlib,json
from pathlib import Path
WORK=Path(__file__).resolve().parents[1];master=WORK/'sources/frontier_sunmeadow_high_elf_scout.blend'
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
assert 'scout_fitted_jerkin' in bpy.data.objects
assert 'scout_suspended_quiver' in bpy.data.objects
assert 'scout_carried_recurve_stave' in bpy.data.objects
assert len([o for o in bpy.data.objects if o.name.startswith('scout_quiver_retaining_loop')])==2
images={n.image for mat in bpy.data.materials if mat.use_nodes for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
assert all(i.packed_file for i in images)
modifiers=[m.type for m in shirt.modifiers];assert modifiers.index('SOLIDIFY')<modifiers.index('ARMATURE')
record={'masterSha256':hashlib.sha256(master.read_bytes()).hexdigest(),'shirtConnectedComponents':components,'shirtBoundaryLoops':loops,'shirtBoundaryValenceValid':True,'fittedJerkin':True,'quiverSuspensionLoops':2,'packedImages':len(images),'modifiers':modifiers,'status':'passed','scope':'Continuous source shirt torso/axilla/sleeves; fitted jerkin and independently attached shoulder yokes, suspended bow and quiver; packed editable PBR inputs. Exact exported garment/tool contact measured separately.'}
(WORK/'review/master-continuity.json').write_text(json.dumps(record,indent=2)+'\n')
