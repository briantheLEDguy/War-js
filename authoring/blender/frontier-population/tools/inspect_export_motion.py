"""Measure the literal skinned GLB surface at every clip key and midpoint."""
import bpy
import hashlib
import json
import math
import struct
import sys
import numpy as np
from pathlib import Path

WORK=Path(__file__).resolve().parents[1]
key=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--asset=')),'frontier_sunmeadow_dwarf_artisan')
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
source=WORK/'runtime'/f'{key}_lod{lod}.glb'
raw=source.read_bytes();length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers))
actions={a.name:a for a in bpy.data.actions}
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()

def vertices():
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    result=np.empty(len(evaluated.data.vertices)*3,dtype=np.float64)
    evaluated.data.vertices.foreach_get('co',result)
    return result.reshape(-1,3)

rest=vertices();edge_groups={}
sole_indices={}
for side in ('L','R'):
    indices=[vertex.index for vertex in body.data.vertices if rest[vertex.index,2]<.10 and
             any(body.vertex_groups[entry.group].name=='foot_'+side and entry.weight>.9 for entry in vertex.groups)]
    if not indices:raise RuntimeError('Export is missing measurable sole vertices: '+side)
    sole_indices[side]=np.array(indices,dtype=int)
for material,entry in enumerate(body.data.materials):
    edges=set()
    for face in body.data.polygons:
        if face.material_index!=material:continue
        v=tuple(face.vertices);edges.update(tuple(sorted((a,b))) for a,b in zip(v,v[1:]+v[:1]))
    edges=np.array(sorted(edges),dtype=int)
    if not len(edges):continue
    lengths=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1)
    selected=lengths>.001
    edge_groups[entry.name]=(edges[selected],lengths[selected])
records=[]
selected=next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--clips=')),None)
for clip in doc['animations']:
    if selected is not None and clip['name'] not in selected:continue
    action=next(a for name,a in actions.items() if name==clip['name'] or name.endswith('_'+clip['name']))
    times=set()
    for sampler in clip['samplers']:
        accessor=doc['accessors'][sampler['input']];view=doc['bufferViews'][accessor['bufferView']]
        start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        times.update(round(struct.unpack_from('<f',binary,start+i*view.get('byteStride',4))[0],8) for i in range(accessor['count']))
    keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]))
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    samples=[]
    for seconds in sorted(times):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update()
        posed=vertices();groups={}
        for name,(edges,lengths) in edge_groups.items():
            ratios=np.linalg.norm(posed[edges[:,0]]-posed[edges[:,1]],axis=1)/lengths
            groups[name]={'max':float(np.max(ratios)),'p99':float(np.quantile(ratios,.99)),
                          'p999':float(np.quantile(ratios,.999)),'min':float(np.min(ratios)),
                          'maximumEdgeExtensionMetres':float(np.max((ratios-1)*lengths))}
            worst=int(np.argmax(ratios));a,b=edges[worst]
            groups[name]['worstEdge']={'restLength':float(lengths[worst]),
                                      'restCenter':((rest[a]+rest[b])*.5).tolist(),
                                      'posedCenter':((posed[a]+posed[b])*.5).tolist()}
        matrix=np.array(body.matrix_world);world=posed@matrix[:3,:3].T+matrix[:3,3]
        lowest=int(np.argmin(world[:,2]))
        influences=[(body.vertex_groups[g.group].name,g.weight) for g in body.data.vertices[lowest].groups]
        samples.append({'seconds':seconds,'minimumHeight':float(world[lowest,2]),
                        'soleHeights':{side:float(np.min(world[indices,2])) for side,indices in sole_indices.items()},
                        'floorPoint':{'rest':rest[lowest].tolist(),'posed':world[lowest].tolist(),'weights':sorted(influences,key=lambda v:-v[1])[:4]},'materials':groups})
    record={'clip':clip['name'],'samples':samples,'maximumStretch':max(s['max'] for row in samples for s in row['materials'].values()),
            'worstP99':max(s['p99'] for row in samples for s in row['materials'].values()),
            'minimumHeight':min(row['minimumHeight'] for row in samples)}
    records.append(record)
    print(json.dumps({k:v for k,v in record.items() if k!='samples'}),flush=True)
report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'status':'inspection_only','clips':records}
(WORK/'review'/f'{key}_lod{lod}_{"selected_motion" if selected else "motion"}.json').write_text(json.dumps(report,indent=2))
