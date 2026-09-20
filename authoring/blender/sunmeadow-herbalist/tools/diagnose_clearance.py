"""Inspect real exported smock layers and carried tools at all keys/midpoints."""
import hashlib,json,math,struct,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

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
    ray_direction=Vector((.367,.531,.764)).normalized()
    def inside_closed_cloth(point):
        nonlocal closed_tree
        if closed_tree is None:
            closed_tree=BVHTree.FromPolygons(posed,[f for f in reference if '.body' not in face_names[f]],all_triangles=True)
        start=point.copy();count=0
        while count<128:
            hit=closed_tree.ray_cast(start,ray_direction,5)[0]
            if hit is None:return count%2==1
            count+=1;start=hit+ray_direction*.00002
        raise RuntimeError('Ambiguous cloth containment ray did not exit')
    for i in indices:
        p=Vector(posed[i]);hit,n,triangle,distance=tree.find_nearest(p)
        if hit is None:raise RuntimeError('Missing underlying outfit surface')
        gap=distance if (p-hit).dot(n)>=0 else -distance
        unsigned_minimum=min(unsigned_minimum,distance)
        if gap<0 and '.body' not in face_names[reference[triangle]]:
            a,b,c=(Vector(posed[v]) for v in reference[triangle])
            bary=barycentric_transform(hit,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
            # A nearest hem/cuff corner has several opposing face normals.
            # Its arbitrary returned normal is not a signed-distance proof.
            # Use ray parity of the actual closed, thick cloth for edge hits.
            if min(bary)<.0001:
                edge_sign_checks+=1
                gap=-distance if inside_closed_cloth(p) else distance
        if gap<minimum:minimum=gap;worst={'vertex':i,'rest':rest[i].tolist(),'point':list(p),'support':list(hit),'supportNormal':list(n),'supportMaterial':face_names[reference[triangle]],'gap':gap}
    return {'candidatePairs':len(pairs),'edgeCrossings':crossings,'crossingWitness':crossing_witness,'minimumSignedGap':minimum,
            'minimumSurfaceDistanceMetres':unsigned_minimum,'ambiguousEdgeSignChecks':edge_sign_checks,'worstProbe':worst}


sys.path.insert(0,str(WORK/'tools'))
from tailored_locomotion import _solve_chain
rig.animation_data.action=bpy.data.actions['attack_melee']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
for shift in [0,.04,.08]:
 maximum=0;minimum=10.
 for step in range(61):
  for bone in rig.pose.bones:bone.matrix_basis.identity()
  seconds=step/60;frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
  bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update()
  for side,sign in [('L',1),('R',-1)]:
   hand=rig.pose.bones['hand_'+side];target=hand.head.copy();rotation=hand.matrix.to_quaternion();target.x+=sign*shift
   shoulder=rig.pose.bones['upper_arm_'+side].head;delta=target-shoulder;reach=(rig.pose.bones['upper_arm_'+side].length+rig.pose.bones['forearm_'+side].length)*.90
   if delta.length>reach:target=shoulder+delta.normalized()*reach
   _solve_chain(rig,side,target,rotation,('upper_arm','forearm','hand'),Vector((sign*1.6,0,-.25)))
  row=measure(points(),smock,supports,probes['garment_clearance']);maximum=max(maximum,row['edgeCrossings']);minimum=min(minimum,row['minimumSignedGap'])
 print('FULL_MELEE',shift,'maximumCrossings',maximum,'minimumGap',minimum,flush=True)
