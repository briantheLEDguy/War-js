"""Diagnostic moving contact witnesses; never substitutes for a full audit."""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
W=Path(__file__).resolve().parents[1];K='frontier_cinderfen_greenskin_quartermaster'
source=W/'runtime'/f'{K}_lod0.glb'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
for track in rig.animation_data.nla_tracks:track.mute=True
clip=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--clip=')),'cast')
seconds=float(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--seconds=')),'.4'))
action=next(a for a in bpy.data.actions if a.name==clip or a.name.endswith('_'+clip))
rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
for bone in rig.pose.bones:bone.matrix_basis.identity()
frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update()
points=[v.co.copy() for v in body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
outer=[tuple(f.vertices) for f in body.data.polygons if body.data.materials[f.material_index].name=='quartermaster_supply_waistcoat']
cloth=[f for f in body.data.polygons if any(t in body.data.materials[f.material_index].name for t in ('_woven_linen','_wool','body_mire_brutish_v1_m.body'))]
tree=BVHTree.FromPolygons(points,[tuple(f.vertices) for f in cloth],all_triangles=True)
edges={tuple(sorted((a,b))) for f in outer for a,b in zip(f,f[1:]+f[:1])};hits=[]
def vertex(i):
    v=body.data.vertices[i]
    return {'index':i,'rest':list(v.co),'pose':list(points[i]),'weights':{body.vertex_groups[g.group].name:g.weight for g in v.groups}}
for a,b in edges:
    d=points[b]-points[a]
    if d.length<.001:continue
    hit,_,i,_=tree.ray_cast(points[a]+d.normalized()*.00025,d.normalized(),d.length-.0005)
    if hit is not None:hits.append({'position':list(hit),'target':body.data.materials[cloth[i].material_index].name,'edge':[vertex(a),vertex(b)],'triangle':[vertex(j) for j in cloth[i].vertices]})
report={'diagnosticOnly':True,'modelSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'clip':clip,'seconds':seconds,'count':len(hits),'targets':{n:sum(h['target']==n for h in hits) for n in {h['target'] for h in hits}},'hits':hits}
(W/'review/layer-motion-contact-probe.json').write_text(json.dumps(report,separators=(',',':')))
print(json.dumps({'count':len(hits),'targets':report['targets'],'first':hits[:3]}))
