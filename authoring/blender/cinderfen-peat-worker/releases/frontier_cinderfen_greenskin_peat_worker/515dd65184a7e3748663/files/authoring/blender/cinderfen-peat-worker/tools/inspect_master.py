"""Verify editable clothing continuity and finished closed source surfaces."""
import bpy,bmesh,hashlib,json,sys
from pathlib import Path
WORK=Path(__file__).resolve().parents[1]
source=WORK/'sources/frontier_cinderfen_greenskin_peat_worker.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
required=['shirt_continuous_tailored_surface','trousers_continuous_tailored_surface','fitted_boot_-1','fitted_boot_1','greenskin_peat_worker_folded_work_apron','work_belt','peat_knife_closed_wet_leather_sheath','peat_worker_curved_lower_tusk_-1','peat_worker_curved_lower_tusk_1']
records=[]
for name in required:
    obj=bpy.data.objects[name];evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    bm=bmesh.new();bm.from_mesh(mesh)
    nonmanifold=sum(not edge.is_manifold for edge in bm.edges)
    pending=set(bm.verts);components=[]
    while pending:
        todo=[pending.pop()];count=0
        while todo:
            v=todo.pop();count+=1
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other in pending:pending.remove(other);todo.append(other)
        components.append(count)
    records.append({'object':name,'vertices':len(mesh.vertices),'faces':len(mesh.polygons),'components':components,'nonManifoldEdges':nonmanifold,'uvLayers':len(mesh.uv_layers),'unweightedVertices':sum(not any(g.weight>0 for g in v.groups) for v in mesh.vertices)})
    bm.free();evaluated.to_mesh_clear()
report={'masterSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'skeletonId':rig['skeletonId'],'bindPoseId':rig['bindPoseId'],'objects':records}
(WORK/'review/master-continuity.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
for row in records:
    if row['nonManifoldEdges'] or len(row['components'])!=1 or row['unweightedVertices'] or not row['uvLayers']:raise RuntimeError('Source construction gate failed: '+row['object'])
if any(o.name=='Icosphere' for o in bpy.context.scene.objects):raise RuntimeError('Imported rig helper leaked into editable asset master')
