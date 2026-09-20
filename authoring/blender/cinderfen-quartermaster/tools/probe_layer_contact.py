import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(__file__).resolve().parents[1];K='frontier_cinderfen_greenskin_quartermaster'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(W/'runtime'/f'{K}_lod0.glb'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
points=[v.co.copy() for v in body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
outer=[tuple(f.vertices) for f in body.data.polygons if body.data.materials[f.material_index].name=='quartermaster_supply_waistcoat']
cloth=[f for f in body.data.polygons if any(t in body.data.materials[f.material_index].name for t in ('_woven_linen','_wool','body_mire_brutish_v1_m.body'))]
tree=BVHTree.FromPolygons(points,[tuple(f.vertices) for f in cloth],all_triangles=True)
edges={tuple(sorted((a,b))) for f in outer for a,b in zip(f,f[1:]+f[:1])};hits=[]
for a,b in edges:
 d=points[b]-points[a]
 if d.length<.001:continue
 hit,_,i,_=tree.ray_cast(points[a]+d.normalized()*.00025,d.normalized(),d.length-.0005)
 if hit is not None:hits.append({'position':list(hit),'target':body.data.materials[cloth[i].material_index].name})
report={'count':len(hits),'targets':{n:sum(h['target']==n for h in hits) for n in {h['target'] for h in hits}},'hits':hits}
(W/'review/layer-rest-contact-probe.json').write_text(json.dumps(report,separators=(',',':')))
print(json.dumps({'count':len(hits),'targets':report['targets'],'first':hits[:20]}))
