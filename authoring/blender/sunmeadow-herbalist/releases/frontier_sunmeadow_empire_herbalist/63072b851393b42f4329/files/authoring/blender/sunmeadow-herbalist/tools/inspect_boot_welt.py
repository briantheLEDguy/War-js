"""Audit exported sole-welt fit, closure and actual contact in every clip."""
import bpy
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree

WORK=Path(__file__).resolve().parents[1]
KEY='frontier_sunmeadow_empire_herbalist'
lod=int(next((arg.split('=',1)[1] for arg in sys.argv if arg.startswith('--lod=')),'0'))
source=WORK/'runtime'/f'{KEY}_lod{lod}.glb';raw=source.read_bytes()
length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE')
body=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH')
body.data.calc_loop_triangles();imported_triangles=len(body.data.loop_triangles)
expected=sum(doc['accessors'][primitive['indices']]['count']//3 for mesh in doc['meshes'] for primitive in mesh['primitives'])
if imported_triangles!=expected:raise RuntimeError('Welt audit imported an unexpected mesh')
rest=np.array([tuple(vertex.co) for vertex in body.data.vertices]);points=[vertex.co.copy() for vertex in body.data.vertices]
welt=set();welt_faces=[];sole=[]
for face in body.data.polygons:
    if max(rest[index,2] for index in face.vertices)>.10:continue
    material=body.data.materials[face.material_index].name
    if '_linen_seam' in material:welt.update(face.vertices);welt_faces.append(tuple(face.vertices))
    elif '_worked_leather' in material:sole.append(tuple(face.vertices))
if not welt or not sole:raise RuntimeError('Missing exported welt or sole surface')
tree=BVHTree.FromPolygons(points,sole,all_triangles=True)
distances=[tree.find_nearest(points[index])[3] for index in welt]
maximum_distance=max(distances)
edges={};neighbors={}
identity={index:tuple(round(float(value),6) for value in rest[index]) for index in welt}
for face in welt_faces:
    for a,b in zip(face,face[1:]+face[:1]):
        a,b=identity[a],identity[b]
        if a==b:continue
        edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
        neighbors.setdefault(a,set()).add(b);neighbors.setdefault(b,set()).add(a)
remaining=set(neighbors);components=0
while remaining:
    todo=[remaining.pop()];components+=1
    while todo:
        for point in neighbors[todo.pop()]:
            if point in remaining:remaining.remove(point);todo.append(point)
boundary=sum(count!=2 for count in edges.values())
supports={};welt_indices={}
for side in ('L','R'):
    faces=[face for face in sole if all((rest[index,0]>0)==(side=='L') for index in face)]
    selected=sorted({index for face in faces for index in face});remap={index:local for local,index in enumerate(selected)}
    supports[side]=(np.array(selected,dtype=int),[tuple(remap[index] for index in face) for face in faces])
    welt_indices[side]=sorted(index for index in welt if (rest[index,0]>0)==(side=='L'))
for track in rig.animation_data.nla_tracks:track.mute=True
actions={action.name:action for action in bpy.data.actions}


def payload(index):
    accessor=doc['accessors'][index];view=doc['bufferViews'][accessor['bufferView']]
    width={'SCALAR':1,'VEC3':3,'VEC4':4}[accessor['type']]*4;stride=view.get('byteStride',width)
    start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
    return b''.join(binary[start+i*stride:start+i*stride+width] for i in range(accessor['count']))


records=[];fingerprints={}
for clip in doc['animations']:
    digest=hashlib.sha256();times=set()
    for channel in clip['channels']:
        sampler=clip['samplers'][channel['sampler']];target=channel['target']
        digest.update((doc['nodes'][target['node']].get('name','')+'|'+target['path']+'|'+sampler.get('interpolation','LINEAR')).encode())
        digest.update(payload(sampler['input']));digest.update(payload(sampler['output']))
    fingerprints[clip['name']]=digest.hexdigest()
    for sampler in clip['samplers']:
        data=payload(sampler['input']);times.update(round(value[0],8) for value in struct.iter_unpack('<f',data))
    keys=sorted(times);times.update((a+b)*.5 for a,b in zip(keys,keys[1:]))
    action=next(action for name,action in actions.items() if name==clip['name'] or name.endswith('_'+clip['name']))
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    samples=[]
    for seconds in sorted(times):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update()
        evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        actual=np.empty(len(body.data.vertices)*3);evaluated.data.vertices.foreach_get('co',actual);actual=actual.reshape(-1,3)
        matrix=np.array(body.matrix_world);posed=actual@matrix[:3,:3].T+matrix[:3,3]
        maximum_pose_distance=0
        for side,(selected,faces) in supports.items():
            # Reduced boot vertices can mix foot/ankle weights. Measure their
            # actual deformed surface instead of assuming the whole patch rigid.
            tree=BVHTree.FromPolygons(posed[selected],faces,all_triangles=True)
            maximum_pose_distance=max(maximum_pose_distance,max(tree.find_nearest(posed[index])[3] for index in welt_indices[side]))
        samples.append({'seconds':seconds,'maximumPoseDistance':maximum_pose_distance})
    records.append({'clip':clip['name'],'samples':samples})
report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'importedTriangles':imported_triangles,
        'weltVertices':len(welt),'components':components,'nonManifoldEdges':boundary,'maximumRestDistance':maximum_distance,
        'animationChannelSha256':fingerprints,'clips':records}
(WORK/'review'/f'{KEY}_lod{lod}_welt.json').write_text(json.dumps(report,indent=2))
print(json.dumps({name:value for name,value in report.items() if name not in ('clips','animationChannelSha256')}),flush=True)
if boundary or components!=2:raise RuntimeError('Each exported boot requires a closed welt')
if maximum_distance>.0035:raise RuntimeError('Exported welt is more than 3.5 mm from the sole')
if max(sample['maximumPoseDistance'] for clip in records for sample in clip['samples'])>.0035:raise RuntimeError('Posed welt is more than 3.5 mm from the sole')

