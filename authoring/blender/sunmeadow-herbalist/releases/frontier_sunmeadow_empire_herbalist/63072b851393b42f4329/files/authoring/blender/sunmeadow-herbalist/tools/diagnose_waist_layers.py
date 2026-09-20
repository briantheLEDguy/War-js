"""Classify visible waist marks from exact imported layered geometry."""
import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
WORK=Path(__file__).resolve().parents[1];model=WORK/'runtime/frontier_sunmeadow_empire_herbalist_lod0.glb'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(model))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=bpy.data.actions['idle']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
bpy.context.scene.frame_set(1);bpy.context.view_layer.update();mesh=body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data;mesh.calc_loop_triangles()
points=[body.matrix_world@v.co for v in mesh.vertices];faces=[tuple(t.vertices) for t in mesh.loop_triangles];names=[mesh.materials[t.material_index].name for t in mesh.loop_triangles]
tree=BVHTree.FromPolygons(points,faces,all_triangles=True)
belt=[f for f,n in zip(faces,names) if n.endswith('_worked_leather') and all(.95<points[i].z<1.10 for i in f)]
belt_tree=BVHTree.FromPolygons(points,belt,all_triangles=True)
records={};crossing=[];openings=[]
for iz in range(201):
 z=.955+iz*.0005
 for ix in range(201):
  x=-.25+ix*.0025;origin=Vector((x,2,z));direction=Vector((0,-1,0))
  hit,n,index,d=tree.ray_cast(origin,direction);bh=belt_tree.ray_cast(origin,direction)[0]
  if hit is None:continue
  name=names[index]
  if not name.endswith(('_woven_linen','_linen_seam')) and name not in ['herbalist_smock_bound_edge','farmer_shirt_sewing_thread']:continue
  record={'triangle':index,'point':list(hit),'material':name,'beltPoint':list(bh) if bh else None,'depthOutsideBelt':hit.y-bh.y if bh else None}
  records.setdefault(name,[]).append(record)
  if bh and hit.y>bh.y+.00005:crossing.append(record)
  else:openings.append(record)
result={'modelSha256':hashlib.sha256(model.read_bytes()).hexdigest(),'visibleCreamCounts':{n:len(r) for n,r in records.items()},'creamBeforeBeltCount':len(crossing),'creamInOpenings':len(openings),'crossingWitnesses':crossing,'openingWitnesses':openings}
(WORK/'review/waist-layer-diagnostic-k.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
for n,r in records.items():print(n,'count',len(r),'x',min(p['point'][0] for p in r),max(p['point'][0] for p in r),'z',min(p['point'][2] for p in r),max(p['point'][2] for p in r),flush=True)
print('BEFORE BELT',len(crossing),'maxDepth',max((r['depthOutsideBelt'] for r in crossing),default=0),flush=True)
print('WITNESS',max(crossing,key=lambda r:r['depthOutsideBelt']) if crossing else None,flush=True)

if crossing:
 witness=max(crossing,key=lambda r:r['depthOutsideBelt']);face=faces[witness['triangle']]
 for index in face:
  v=body.data.vertices[index];print('REST_WITNESS',list(v.co),[(body.vertex_groups[g.group].name,g.weight) for g in v.groups],flush=True)
