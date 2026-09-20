"""Measure belt-to-loop-to-payload support on each actual exported LOD pose."""
import hashlib,json,math,struct,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
WORK=Path(__file__).resolve().parents[1];KEY='frontier_sunmeadow_empire_herbalist'
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
source=WORK/'runtime'/f'{KEY}_lod{lod}.glb';raw=source.read_bytes();length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers))
body.data.calc_loop_triangles();triangles=len(body.data.loop_triangles)
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
def points():
 evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());data=np.empty(len(evaluated.data.vertices)*3);evaluated.data.vertices.foreach_get('co',data);matrix=np.array(body.matrix_world)
 return data.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]
rest=points();faces=[(tuple(t.vertices),body.data.materials[t.material_index].name) for t in body.data.loop_triangles]
def components(material):
 selected=[f for f,n in faces if n==material];vertices={i for f in selected for i in f};parents={i:i for i in vertices}
 def root(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 def join(a,b):parents[root(a)]=root(b)
 positions={}
 for i in vertices:
  key=tuple(round(v,5) for v in rest[i])
  if key in positions:join(i,positions[key])
  else:positions[key]=i
 for f in selected:
  for i in f[1:]:join(f[0],i)
 result={}
 for f in selected:result.setdefault(root(f[0]),[]).append(f)
 return list(result.values())
def ids(fs):return sorted({i for f in fs for i in f})
def center(fs):return np.mean(rest[ids(fs)],axis=0)
def upper(fs):return np.max(rest[ids(fs)],axis=0)
def lower(fs):return np.min(rest[ids(fs)],axis=0)
leather=components('herbalist_hanger_leather')
loops=sorted([fs for fs in leather if upper(fs)[2]>1.045],key=lambda fs:center(fs)[0])
if len(loops)!=4:raise RuntimeError(f'Expected four complete suspension loops; got {len(loops)}')
belt=[f for f,n in faces if '_worked_leather' in n and all(.97<rest[i,2]<1.08 for i in f)]
bag=[f for f,n in faces if n=='herbalist_tool_satchel_canvas']
cups=[fs for fs in leather if .89<lower(fs)[2]<.92 and .93<upper(fs)[2]<.95]
vials=components('herbalist_tool_vial_glaze')
if len(cups)!=2 or len(vials)!=2 or not belt or not bag:raise RuntimeError('Missing belt or payload support surfaces')
pairs=[]
for index,loop in enumerate(loops):
 x=center(loop)[0];payload=bag if x<0 else min(cups,key=lambda fs:abs(center(fs)[0]-x))
 pairs.extend([(f'loop_{index}_belt',loop,belt),(f'loop_{index}_payload',loop,payload)])
for index,cup in enumerate(cups):pairs.append((f'vial_{index}_holder',cup,min(vials,key=lambda fs:abs(center(fs)[0]-center(cup)[0]))))
stems=components('herbalist_tool_herb_stem')
if len(stems)!=5:raise RuntimeError('Missing five gathered herb stems')
for index,stem in enumerate(stems):pairs.append((f'herb_{index}_satchel_floor',stem,bag))
all_vertices={i for _,a,b in pairs for i in ids(a)+ids(b)}
assembly_ids=sorted(all_vertices)
rest_hip_world=rig.matrix_world@rig.pose.bones['hips'].matrix
nonmanifold=0
for loop in loops:
 edges={}
 for face in loop:
  keys=[tuple(round(v,5) for v in rest[i]) for i in face]
  for a,b in zip(keys,keys[1:]+keys[:1]):
   edge=tuple(sorted((a,b)))
   if a!=b:edges[edge]=edges.get(edge,0)+1
 nonmanifold+=sum(v!=2 for v in edges.values())
if nonmanifold:raise RuntimeError('A suspension loop is not closed')
hip=body.vertex_groups['hips'].index
min_hips=min(sum(g.weight for g in body.data.vertices[i].groups if g.group==hip) for i in all_vertices)
if min_hips<.9999:raise RuntimeError('Rigid belt assembly has unexpected non-hips skin weights')
def contact(posed,subject,reference):
 tree=BVHTree.FromPolygons(posed,reference,all_triangles=True);target=BVHTree.FromPolygons(posed,subject,all_triangles=True)
 overlaps=target.overlap(tree);edges={tuple(sorted((a,b))) for i,_ in overlaps for f in [subject[i]] for a,b in zip(f,f[1:]+f[:1])};hits=0
 for a,b in edges:
  start=Vector(posed[a]);delta=Vector(posed[b])-start
  if delta.length<.00002:continue
  if tree.ray_cast(start+delta.normalized()*.000005,delta.normalized(),delta.length-.00001)[0] is not None:hits+=1
 distance=min(tree.find_nearest(Vector(posed[i]))[3] for i in ids(subject))
 return {'minimumVertexSurfaceDistanceMetres':distance,'actualEdgeIntersections':hits,'supported':hits>0 or distance<=.0035}
base_contacts={name:contact(rest,a,b) for name,a,b in pairs}
records=[];max_residual=0.
selected=next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--clips=')),None)
for clip in doc['animations']:
 if selected is not None and clip['name'] not in selected:continue
 rig.animation_data.action=next(a for a in bpy.data.actions if a.name==clip['name'] or a.name.endswith('_'+clip['name']))
 if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
 times=set()
 for sampler in clip['samplers']:
  a=doc['accessors'][sampler['input']];v=doc['bufferViews'][a['bufferView']];start=v.get('byteOffset',0)+a.get('byteOffset',0)
  times.update(round(struct.unpack_from('<f',binary,start+i*v.get('byteStride',4))[0],8) for i in range(a['count']))
 keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]));samples=[]
 for seconds in sorted(times):
  for bone in rig.pose.bones:bone.matrix_basis.identity()
  frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base;bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update();posed=points()
  transform=rig.matrix_world@rig.pose.bones['hips'].matrix@rest_hip_world.inverted();matrix=np.array(transform)
  if not np.allclose(matrix[:3,:3].T@matrix[:3,:3],np.eye(3),atol=.000001):raise RuntimeError('Equipment pose changes rigid scale')
  expected=rest[assembly_ids]@matrix[:3,:3].T+matrix[:3,3]
  residual=float(np.max(np.linalg.norm(posed[assembly_ids]-expected,axis=1)));max_residual=max(max_residual,residual)
  if residual>.00001:raise RuntimeError('Imported equipment pose changes measured contacts')
  samples.append({'seconds':seconds,'maximumRigidResidualMetres':residual,'contacts':base_contacts})
 records.append({'clip':clip['name'],'samples':samples});print('Equipment attachment: '+clip['name'],flush=True)
report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'importedTriangles':triangles,'suspensionLoops':len(loops),'contactPairs':len(pairs),'loopNonManifoldEdges':nonmanifold,'maximumPoseRigidResidualMetres':max_residual,'minimumAssemblyHipsWeight':min_hips,'clips':records,'status':'measured',
 'scope':'Actual four connected closed suspension loops against belt and satchel/vial holders, plus both vial/holder contacts and five herb roots against the satchel floor. Actual imported pose vertices are checked at every key and midpoint against the common rigid hips transform; isometry preserves the exact bind-pose contact distances and intersection witnesses. Sewn loop intersections with supports are intentional. Actual edge crossing or <=3.5 mm surface distance proves each contact; shared rigid hips weighting is additionally checked.'}
(WORK/'review'/f'{KEY}_lod{lod}_{"selected_" if selected else ""}equipment_attachment.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
