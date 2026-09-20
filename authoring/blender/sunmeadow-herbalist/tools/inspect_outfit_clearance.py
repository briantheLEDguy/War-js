"""Inspect real exported smock layers and carried tools at all keys/midpoints."""
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
expected=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
if triangles!=expected:raise RuntimeError('Inspection must match the actual exported mesh')
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()

def points():
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());data=np.empty(len(evaluated.data.vertices)*3)
    evaluated.data.vertices.foreach_get('co',data);matrix=np.array(body.matrix_world)
    return data.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]

rest=points()
all_faces=[(tuple(t.vertices),body.data.materials[t.material_index].name) for t in body.data.loop_triangles]
face_names=dict(all_faces)
supports=[f for f,n in all_faces if '_woven_linen' in n or '_wool' in n]
smock=[f for f,n in all_faces if n=='herbalist_sage_smock' and not any(.998<rest[i,2]<1.055 for i in f)]
gear=[f for f,n in all_faces if n.startswith('herbalist_tool_')]
obstacles=[f for f,n in all_faces if '_woven_linen' in n or '_wool' in n or n=='herbalist_sage_smock' or '.body' in n]
if not all((supports,smock,gear,obstacles)):raise RuntimeError('Missing outfit surfaces')
sets={'garment_clearance':(smock,supports),'tool_clearance':(gear,obstacles)}
probes={name:sorted({i for f in a for i in f}) for name,(a,b) in sets.items()}
records={name:[] for name in sets}

def measure(posed,subject,reference,indices):
    tree=BVHTree.FromPolygons(posed,reference,all_triangles=True)
    target=BVHTree.FromPolygons(posed,subject,all_triangles=True)
    pairs=target.overlap(tree)
    edges={tuple(sorted((a,b))) for i,_ in pairs for f in [subject[i]] for a,b in zip(f,f[1:]+f[:1])}
    crossings=0;crossing_witness=None
    for a,b in edges:
        start=Vector(posed[a]);delta=Vector(posed[b])-start
        if delta.length<.00003:continue
        direction=delta.normalized()
        hit,normal,triangle,_=tree.ray_cast(start+direction*.00001,direction,delta.length-.00002)
        if hit is not None:
            crossings+=1
            if crossing_witness is None:crossing_witness={'edge':[a,b],'rest':[rest[a].tolist(),rest[b].tolist()],
                                                        'posed':[posed[a].tolist(),posed[b].tolist()],'hit':list(hit),'supportMaterial':face_names[reference[triangle]]}
    minimum=10.;unsigned_minimum=10.;worst=None;edge_sign_checks=0
    closed_tree=None
    ray_directions=[Vector(v).normalized() for v in ((.367,.531,.764),(-.631,.472,.428),(.189,-.593,.803))]
    def inside_closed_cloth(point):
        nonlocal closed_tree
        if closed_tree is None:
            closed_tree=BVHTree.FromPolygons(posed,[f for f in reference if '.body' not in face_names[f]],all_triangles=True)
        votes=[]
        for direction in ray_directions:
            start=point.copy();count=0
            while count<128:
                hit=closed_tree.ray_cast(start,direction,5)[0]
                if hit is None:break
                count+=1;start=hit+direction*.00002
            else:raise RuntimeError('Ambiguous cloth containment ray did not exit')
            votes.append(count%2==1)
        # Three non-axis rays avoid a single edge/vertex graze controlling sign.
        return sum(votes)>=2
    for i in indices:
        p=Vector(posed[i]);hit,n,triangle,distance=tree.find_nearest(p)
        if hit is None:raise RuntimeError('Missing underlying outfit surface')
        gap=distance if (p-hit).dot(n)>=0 else -distance
        unsigned_minimum=min(unsigned_minimum,distance)
        if gap<0 and '.body' not in face_names[reference[triangle]]:
            # Inner cloth faces and closed hem/cuff rims can return a negative
            # nearest normal for a point outside the actual thick garment.
            # Signed contact uses containment, not the arbitrary nearest normal.
            edge_sign_checks+=1
            gap=-distance if inside_closed_cloth(p) else distance
        if gap<minimum:minimum=gap;worst={'vertex':i,'rest':rest[i].tolist(),'point':list(p),'support':list(hit),'supportNormal':list(n),'supportMaterial':face_names[reference[triangle]],'gap':gap}
    return {'candidatePairs':len(pairs),'edgeCrossings':crossings,'crossingWitness':crossing_witness,'minimumSignedGap':minimum,
            'minimumSurfaceDistanceMetres':unsigned_minimum,'closedClothSignChecks':edge_sign_checks,'worstProbe':worst}

selected=next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--clips=')),None)
stride=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--stride=')),'1'))
if stride<1:raise ValueError('Sample stride must be positive')
for clip in doc['animations']:
    if selected is not None and clip['name'] not in selected:continue
    action=next(a for a in bpy.data.actions if a.name==clip['name'] or a.name.endswith('_'+clip['name']))
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    times=set()
    for sampler in clip['samplers']:
        accessor=doc['accessors'][sampler['input']];view=doc['bufferViews'][accessor['bufferView']];start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        times.update(round(struct.unpack_from('<f',binary,start+i*view.get('byteStride',4))[0],8) for i in range(accessor['count']))
    keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]));samples={name:[] for name in sets}
    for seconds in sorted(set(sorted(times)[::stride]+[max(times)])):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update();posed=points()
        for name,(subject,reference) in sets.items():samples[name].append({'seconds':seconds,**measure(posed,subject,reference,probes[name])})
    for name in sets:records[name].append({'clip':clip['name'],'samples':samples[name]})
    print('Outfit clearance: '+clip['name']+' '+json.dumps({name:{'maximumCrossings':max(row['edgeCrossings'] for row in samples[name]),'minimumSignedGap':min(row['minimumSignedGap'] for row in samples[name])} for name in sets}),flush=True)
for name in sets:
    report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'importedTriangles':triangles,'sampleStride':stride,'probeVertices':len(probes[name]),'clips':records[name],
            'scope':'Actual exported surface intersections and signed nearest-surface clearance. Negative cloth-face signs are resolved with three-direction ray parity on actual closed thick clothing; exposed open anatomy retains oriented-face sign. Smock waist tuck/seam band at rest z .998-1.055 m is an intentional overlap and excluded. Tool holders and belt hangers intentionally overlap their contents/support and are excluded; carried canvas, herbs, ceramic vials and stoppers are checked against all worn/exposed body surfaces.','status':'measured'}
    (WORK/'review'/f'{KEY}_lod{lod}_{"probe_" if stride>1 else "selected_" if selected else ""}{name}.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
