"""Measure actual reimported trouser hems inside boots in every key/midpoint."""
import bpy, hashlib, json, math, struct, sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WORK=Path(__file__).resolve().parents[1]
KEY='frontier_sunmeadow_empire_herbalist'
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
source=WORK/'runtime'/f'{KEY}_lod{lod}.glb';raw=source.read_bytes()
length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers))
body.data.calc_loop_triangles();triangles=len(body.data.loop_triangles)
expected=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
if triangles!=expected:raise RuntimeError('Imported triangle count does not match binary')
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()

def positions():
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());array=np.empty(len(evaluated.data.vertices)*3,dtype=np.float64)
    evaluated.data.vertices.foreach_get('co',array);matrix=np.array(body.matrix_world)
    return array.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]

rest=positions();trousers={i for f in body.data.polygons if '_wool' in body.data.materials[f.material_index].name for i in f.vertices}
boots={};probes={};rings={};hem_edges={}
for side,sign in [('L',1),('R',-1)]:
    boots[side]=[tuple(f.vertices) for f in body.data.polygons if '_worked_leather' in body.data.materials[f.material_index].name and all(rest[i,2]<.32 and sign*rest[i,0]>.12 for i in f.vertices)]
    probes[side]=np.array(sorted(i for i in trousers if .205<rest[i,2]<.25 and sign*rest[i,0]>.12),dtype=int)
    if not boots[side] or len(probes[side])<20:raise RuntimeError('Missing actual boot/hem surface: '+side)
    boot_edges=sorted({tuple(sorted((a,b))) for face in boots[side] for a,b in zip(face,face[1:]+face[:1])})
    hem_faces=[tuple(face.vertices) for face in body.data.polygons if '_wool' in body.data.materials[face.material_index].name and all(.205<rest[i,2]<.25 and sign*rest[i,0]>.12 for i in face.vertices)]
    hem_edges[side]=sorted({tuple(sorted((a,b))) for face in hem_faces for a,b in zip(face,face[1:]+face[:1])})
    if not hem_edges[side]:raise RuntimeError('Missing actual tucked hem edges')
    rings[side]={}
    for i in probes[side]:
        # Intersect actual exported edges with the hem-height plane. Decimated
        # boots need not retain a complete vertex row near that height; a band
        # of nearby vertices cannot reliably describe their surface section.
        section={}
        for a,b in boot_edges:
            dz=rest[b,2]-rest[a,2]
            if abs(dz)<1e-9:continue
            t=(rest[i,2]-rest[a,2])/dz
            if not 0<=t<=1:continue
            point=rest[a]*(1-t)+rest[b]*t
            section[tuple(np.round(point,6))]=(a,b,t)
        points=np.array(list(section))
        if len(points)<8 or np.ptp(points[:,0])<.10 or np.ptp(points[:,1])<.08:
            raise RuntimeError(f'Incomplete actual boot section: {side}/{i}/{len(points)}')
        anchors=np.array(list(section.values()))
        rings[side][int(i)]=(anchors[:,0].astype(int),anchors[:,1].astype(int),anchors[:,2:3])
selected=next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--clips=')),None)
records=[]
for clip in doc['animations']:
    if selected is not None and clip['name'] not in selected:continue
    action=next(a for a in bpy.data.actions if a.name==clip['name'] or a.name.endswith('_'+clip['name']))
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    times=set()
    for sampler in clip['samplers']:
        accessor=doc['accessors'][sampler['input']];view=doc['bufferViews'][accessor['bufferView']]
        start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        times.update(round(struct.unpack_from('<f',binary,start+i*view.get('byteStride',4))[0],8) for i in range(accessor['count']))
    keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]));samples=[]
    for seconds in sorted(times):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update();posed=positions();sides={}
        for side in ('L','R'):
            tree=BVHTree.FromPolygons(posed,boots[side],all_triangles=True)
            shin=rig.matrix_world@rig.pose.bones['shin_'+side].matrix;inverse=shin.inverted();gaps=[];worst=None
            for i in probes[side]:
                point=Vector(posed[i])
                # The boot shaft blends ankle and foot deformation. Its actual
                # reimported ring center stays inside the cavity during lift; a
                # rigid shin-axis origin can lie outside and hit an entry wall.
                ring_a,ring_b,ring_t=rings[side][int(i)]
                origin=Vector(np.mean(posed[ring_a]*(1-ring_t)+posed[ring_b]*ring_t,axis=0));delta=point-origin
                if delta.length<.001:continue
                hit=tree.ray_cast(origin,delta.normalized(),.3)[0]
                if hit is not None:
                    gap=(hit-origin).length-delta.length;gaps.append(gap)
                    if worst is None or gap<worst['gap']:worst={'gap':gap,'vertex':int(i),'rest':rest[i].tolist(),'posed':list(point),'origin':list(origin),'hit':list(hit)}
            crossings=0
            for a,b in hem_edges[side]:
                start=Vector(posed[a]);delta=Vector(posed[b])-start
                if delta.length<.00003:continue
                direction=delta.normalized()
                if tree.ray_cast(start+direction*.00001,direction,delta.length-.00002)[0] is not None:crossings+=1
            sides[side]={'intersections':crossings,'rays':len(gaps),'minimumGap':min(gaps) if gaps else None,'penetrations':sum(g<-.002 for g in gaps),'worstProbe':worst}
        samples.append({'seconds':seconds,'sides':sides})
    records.append({'clip':clip['name'],'samples':samples})
    print('Boot clearance: '+clip['name'],flush=True)
report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'importedTriangles':triangles,
        'probeVertices':{side:len(p) for side,p in probes.items()},
        'referenceRingMethod':'Exact rest-height section of exported boot edges, interpolated through actual posed edge endpoints',
        'clips':records,'status':'measured'}
(WORK/'review'/f'{KEY}_lod{lod}_{"selected_" if selected else ""}boot_clearance.json').write_text(json.dumps(report,indent=2))
