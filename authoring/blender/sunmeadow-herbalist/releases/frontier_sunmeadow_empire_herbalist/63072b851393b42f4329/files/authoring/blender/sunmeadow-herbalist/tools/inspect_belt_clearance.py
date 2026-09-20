"""Audit the actual belt against all tucked cloth and bindings in every clip."""
import bpy,json,hashlib,struct,sys,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
WORK=Path(__file__).resolve().parents[1];KEY='frontier_sunmeadow_empire_herbalist'
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
selected=next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--clips=')),None)
source=WORK/'runtime'/f'{KEY}_lod{lod}.glb';raw=source.read_bytes();length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update();body.data.calc_loop_triangles()
def points():
 mesh=body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data;data=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',data);m=np.array(body.matrix_world)
 return data.reshape(-1,3)@m[:3,:3].T+m[:3,3]
assert len(body.data.loop_triangles)==sum(doc['accessors'][p['indices']]['count']//3 for mesh in doc['meshes'] for p in mesh['primitives'])
rest=points();faces=[(tuple(t.vertices),body.data.materials[t.material_index].name) for t in body.data.loop_triangles]
belt=[f for f,n in faces if n.endswith('_worked_leather') and all(.97<rest[i,2]<1.08 for i in f)]
cloth=[f for f,n in faces if (n.endswith(('_woven_linen','_wool','_linen_seam')) or n in ['herbalist_sage_smock','herbalist_smock_bound_edge','farmer_shirt_sewing_thread']) and min(rest[i,2] for i in f)<1.12 and max(rest[i,2] for i in f)>.92 and all(abs(rest[i,0])<.35 for i in f)]
assert belt and cloth
ids=sorted({i for f in cloth for i in f});belt_ids=sorted({i for f in belt for i in f});belt_tree=BVHTree.FromPolygons(rest,belt,all_triangles=True)
lower=float(rest[belt_ids,2].min());upper=float(rest[belt_ids,2].max());rest_hip_world=rig.matrix_world@rig.pose.bones['hips'].matrix
records=[]
for clip in doc['animations']:
 if selected and clip['name'] not in selected:continue
 action=next(a for a in bpy.data.actions if a.name==clip['name'] or a.name.endswith('_'+clip['name']));rig.animation_data.action=action
 if action.slots:rig.animation_data.action_slot=action.slots[0]
 times=set()
 for sampler in clip['samplers']:
  a=doc['accessors'][sampler['input']];v=doc['bufferViews'][a['bufferView']];start=v.get('byteOffset',0)+a.get('byteOffset',0)
  times.update(round(struct.unpack_from('<f',binary,start+i*v.get('byteStride',4))[0],8) for i in range(a['count']))
 keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]));samples=[]
 for seconds in sorted(times):
  for bone in rig.pose.bones:bone.matrix_basis.identity()
  frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base;bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update();posed=points()
  transform=rig.matrix_world@rig.pose.bones['hips'].matrix@rest_hip_world.inverted();inverse=np.array(transform.inverted());local=posed@inverse[:3,:3].T+inverse[:3,3]
  target=BVHTree.FromPolygons(local,cloth,all_triangles=True);pairs=target.overlap(belt_tree);crossings=0
  for fs,indices,tree in [(cloth,{a for a,b in pairs},belt_tree),(belt,{b for a,b in pairs},target)]:
   edges={tuple(sorted((a,b))) for index in indices for face in [fs[index]] for a,b in zip(face,face[1:]+face[:1])}
   for a,b in edges:
    start=Vector(local[a]);delta=Vector(local[b])-start
    if delta.length<.00003:continue
    direction=delta.normalized()
    if tree.ray_cast(start+direction*.00001,direction,delta.length-.00002)[0] is not None:crossings+=1
  minimum=10.;probes=0;worst=None
  for index in ids:
   p=Vector(local[index])
   if not lower+.0001<p.z<upper-.0001:continue
   direction=Vector((p.x,p.y,0));radius=direction.length
   if radius<.001:continue
   direction.normalize();hit=belt_tree.ray_cast(Vector((0,0,p.z)),direction)[0]
   if hit is None:raise RuntimeError('Actual belt section is not closed')
   gap=Vector((hit.x,hit.y,0)).length-radius;probes+=1
   if gap<minimum:minimum=gap;worst={'vertex':index,'pointInWaistFrame':list(p),'beltInnerPoint':list(hit)}
  assert probes>100
  samples.append({'seconds':seconds,'edgeCrossings':crossings,'minimumInnerClearanceMetres':minimum,'probeVertices':probes,'worstProbe':worst})
 records.append({'clip':clip['name'],'samples':samples});print('Belt layers',clip['name'],'crossings',max(r['edgeCrossings'] for r in samples),'minimum gap',min(r['minimumInnerClearanceMetres'] for r in samples),flush=True)
report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'importedTriangles':len(body.data.loop_triangles),'clips':records,'status':'measured','scope':'Actual imported closed belt against woven shirt, trousers, sage panels, bound edges and sewing thread. Both triangle-edge directions checked for crossings; all cloth vertices within the belt-height slab must remain inside its inner surface in the exact rigid hips frame. No waist-band exclusion.'}
(WORK/'review'/f'{KEY}_lod{lod}_{"selected_" if selected else ""}belt_clearance.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
