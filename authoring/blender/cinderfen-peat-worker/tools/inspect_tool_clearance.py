"""Actual clip checks that the rigid sheathed tool clears moving work clothing."""
import bpy,hashlib,json,math,struct,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
WORK=Path(__file__).resolve().parents[1];KEY='frontier_cinderfen_greenskin_peat_worker'
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
source=WORK/'runtime'/f'{KEY}_lod{lod}.glb';raw=source.read_bytes();length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
body.data.calc_loop_triangles();expected=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
if len(body.data.loop_triangles)!=expected:raise RuntimeError('Unexpected imported tool inspection mesh')
rest=np.array([v.co[:] for v in body.data.vertices]);parents={}
def root(key):
    parents.setdefault(key,key)
    if parents[key]!=key:parents[key]=root(parents[key])
    return parents[key]
leather=[tuple(f.vertices) for f in body.data.polygons if '_worked_leather' in body.data.materials[f.material_index].name]
keys={i:tuple(np.round(rest[i],6)) for f in leather for i in f}
for face in leather:
    first=root(keys[face[0]])
    for i in face[1:]:parents[root(keys[i])]=first
components={}
for face in leather:components.setdefault(root(keys[face[0]]),[]).append(face)
sheaths=[]
for faces in components.values():
    points=rest[sorted({i for f in faces for i in f})];low=points.min(axis=0);high=points.max(axis=0)
    if high[0]<-.08 and low[1]>.01 and .6<low[2]<1.05 and high[2]<1.15 and high[2]-low[2]>.15:sheaths.append(faces)
if len(sheaths)!=1:raise RuntimeError('Expected one complete closed peat-knife sheath; found '+str(len(sheaths)))
tool=sheaths[0]+[tuple(f.vertices) for f in body.data.polygons if any(t in body.data.materials[f.material_index].name for t in ('_tool_ash','_forged_iron'))]
cloth=[tuple(f.vertices) for f in body.data.polygons if any(t in body.data.materials[f.material_index].name for t in ('_woven_linen','_wool','_wax_worn_bib'))]
tool_ids=sorted({i for f in tool for i in f});cloth_ids=sorted({i for f in cloth for i in f})
tool_map={i:j for j,i in enumerate(tool_ids)};cloth_map={i:j for j,i in enumerate(cloth_ids)}
tool_faces=[tuple(tool_map[i] for i in f) for f in tool];cloth_faces=[tuple(cloth_map[i] for i in f) for f in cloth]
edges=sorted({tuple(sorted((a,b))) for f in tool_faces for a,b in zip(f,f[1:]+f[:1])})
for track in rig.animation_data.nla_tracks:track.mute=True
records=[]
for animation in doc['animations']:
    action=next(a for a in bpy.data.actions if a.name==animation['name'] or a.name.endswith('_'+animation['name']));rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    times=set()
    for sampler in animation['samplers']:
        accessor=doc['accessors'][sampler['input']];view=doc['bufferViews'][accessor['bufferView']];start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        times.update(round(struct.unpack_from('<f',binary,start+i*view.get('byteStride',4))[0],8) for i in range(accessor['count']))
    keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]));samples=[]
    for seconds in sorted(times):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base;bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update()
        evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());points=np.empty(len(body.data.vertices)*3);evaluated.data.vertices.foreach_get('co',points);points=points.reshape(-1,3)
        p=points[tool_ids];tree=BVHTree.FromPolygons(points[cloth_ids],cloth_faces,all_triangles=True);crossings=[]
        for a,b in edges:
            start=Vector(p[a]);delta=Vector(p[b])-start
            if delta.length<.001:continue
            direction=delta.normalized();hit=tree.ray_cast(start+direction*.00025,direction,delta.length-.0005)[0]
            if hit is not None:crossings.append(list(hit))
        samples.append({'seconds':seconds,'crossings':len(crossings),'firstCrossings':crossings[:3]})
    records.append({'clip':animation['name'],'samples':samples,'maximumCrossings':max(s['crossings'] for s in samples)})
    print(animation['name'],records[-1]['maximumCrossings'],flush=True)
report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'importedTriangles':expected,'toolTriangles':len(tool),'clothTriangles':len(cloth),'clips':records}
(WORK/'review'/f'{KEY}_lod{lod}_tool_clearance.json').write_text(json.dumps(report,indent=2))
if any(row['maximumCrossings'] for row in records):raise RuntimeError('Carried peat knife crosses animated clothing')
