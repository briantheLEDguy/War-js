"""Check actual exported knee/apron overlap at literal keys and midpoints."""
import bpy
import hashlib
import json
import math
import struct
import sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WORK=Path(__file__).resolve().parents[1]
key=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--asset=')),'frontier_sunmeadow_dwarf_artisan')
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
source=WORK/'runtime'/f'{key}_lod{lod}.glb';raw=source.read_bytes()
length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE')
body=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH' and any(mod.type=='ARMATURE' and mod.object==rig for mod in obj.modifiers))
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()


def positions():
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    array=np.empty(len(evaluated.data.vertices)*3,dtype=np.float64)
    evaluated.data.vertices.foreach_get('co',array)
    matrix=np.array(body.matrix_world)
    return array.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]


rest=positions();belt=(rig.matrix_world@rig.data.bones['apron_lower'].head_local).z
hinge={vertex.index for vertex in body.data.vertices if any(body.vertex_groups[entry.group].name=='apron_lower' and entry.weight>.0001 for entry in vertex.groups)}
apron=[tuple(face.vertices) for face in body.data.polygons if any(i in hinge for i in face.vertices)]
trousers={i for face in body.data.polygons if '_wool' in body.data.materials[face.material_index].name for i in face.vertices}
probes=np.array(sorted(i for i in trousers if belt-.39<rest[i,2]<belt-.035 and rest[i,1]<-.035 and abs(rest[i,0])<.31),dtype=int)
if not apron or len(probes)<100:raise RuntimeError('Missing authored apron or trouser inspection surface')
records=[]
for clip in doc['animations']:
    if clip['name'] not in ('walk','run','jump'):continue
    action=next(action for action in bpy.data.actions if action.name==clip['name'] or action.name.endswith('_'+clip['name']))
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    times=set()
    for sampler in clip['samplers']:
        accessor=doc['accessors'][sampler['input']];view=doc['bufferViews'][accessor['bufferView']]
        start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        times.update(round(struct.unpack_from('<f',binary,start+i*view.get('byteStride',4))[0],8) for i in range(accessor['count']))
    keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]))
    samples=[]
    for seconds in sorted(times):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update()
        posed=positions();tree=BVHTree.FromPolygons(posed,apron,all_triangles=True)
        gaps=[]
        for i in probes:
            point=posed[i]
            hit=tree.ray_cast(Vector((point[0],-2,point[2])),Vector((0,1,0)),3)[0]
            if hit is not None:gaps.append(float(point[1]-hit.y))
        samples.append({'seconds':seconds,'raysIntersectingApron':len(gaps),'minimumGap':min(gaps) if gaps else None,
                        'penetrationCount':sum(gap<-.002 for gap in gaps)})
    records.append({'clip':clip['name'],'samples':samples,'maximumPenetration':max(0,-min((sample['minimumGap'] for sample in samples if sample['minimumGap'] is not None),default=0))})
report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'probeVertices':len(probes),
        'apronTriangles':len(apron),'status':'inspection_only','clips':records}
(WORK/'review'/f'{key}_lod{lod}_garment_clearance.json').write_text(json.dumps(report,indent=2))
print(json.dumps({clip['clip']:clip['maximumPenetration'] for clip in records}),flush=True)
