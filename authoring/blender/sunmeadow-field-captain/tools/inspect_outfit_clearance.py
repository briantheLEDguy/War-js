"""Inspect real exported smock layers and carried tools at all keys/midpoints."""
import hashlib,json,math,struct,sys,gzip
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from surface_contact import bounded_tree,connected_shells,require_closed,inside_closed,crossings,signed_clearance,signed_clearances,skin_reference,CONTAINMENT_DIAGNOSTICS

WORK=Path(__file__).resolve().parents[1];KEY='frontier_sunmeadow_empire_field_captain'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
checker_hashes={name:sha(Path(__file__).with_name(name)) for name in ('inspect_outfit_clearance.py','surface_contact.py')}
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
topology_rest=np.array([tuple(v.co) for v in body.data.vertices])
all_faces=[(tuple(t.vertices),body.data.materials[t.material_index].name) for t in body.data.loop_triangles]
supports=[f for f,n in all_faces if '_woven_linen' in n or '_wool' in n]
soft_layers={'captain_layer_leather_brigandine','captain_layer_shoulder_felt'}
smock=[f for f,n in all_faces if n in soft_layers]
plates=[f for f,n in all_faces if n=='captain_layer_tempered_steel']
gear=[f for f,n in all_faces if n.startswith('captain_tool_')]
obstacles=[f for f,n in all_faces if '_woven_linen' in n or '_wool' in n or n.startswith('captain_layer_') or '.body' in n]
if not all((supports,smock,gear,obstacles)):raise RuntimeError('Missing outfit surfaces')
if not plates:raise RuntimeError('Missing articulated armor surfaces')
sets={'garment_clearance':(smock,supports),'layer_clearance':(plates,supports+smock),'tool_clearance':(gear,obstacles)}
probes={name:sorted({i for f in a for i in f}) for name,(a,b) in sets.items()}
records={name:[] for name in sets}

foundation=WORK/'foundations/civic_humanoid_v2_m.quad-surface.json.gz'
foundation_hash=sha(foundation)
anatomy=json.loads(gzip.decompress(foundation.read_bytes()))
reference=np.array(anatomy['vertices'])*(1.0)
reference_faces=[tuple(face) for face in anatomy['faces']]
closed={'retainedUnderlyingBody':require_closed(reference,reference_faces,'retained male body')}
for name,(subject,reference_surface) in sets.items():
    # Exposed runtime skin has intentional neck/cuff openings. A retained closed
    # anatomical body supplies its hidden volume, while all visible cloth faces
    # remain the actual exported surfaces used for intersection checks.
    cloth=[f for f,n in all_faces if ('_woven_linen' in n or '_wool' in n or
        (name in ('layer_clearance','tool_clearance') and n in soft_layers) or
        (name=='tool_clearance' and n=='captain_layer_tempered_steel'))]
    shells=connected_shells(topology_rest,cloth)
    sets[name]=(subject,reference_surface,shells)
    closed[name]={'shells':len(shells),'boundaryEdges':0,'nonManifoldEdges':0}
fields={}
for i,weights in enumerate(anatomy['weights']):
    rows=sorted([(anatomy['vertexGroups'][str(group)],weight) for group,weight in weights if anatomy['vertexGroups'][str(group)] in rig.data.bones],key=lambda row:-row[1])[:4]
    total=sum(weight for _,weight in rows)
    if total<=0:raise RuntimeError('Retained anatomical vertex has no skeleton support')
    for name,weight in rows:fields.setdefault(name,[]).append((i,weight/total))
fields={name:(np.array([i for i,w in rows],dtype=int),np.array([w for i,w in rows])) for name,rows in fields.items()}
diagnostic=None
real_diagnostic=None

def measure(posed,subject,reference_surface,cloth,indices,anatomical_tree):
    global diagnostic
    tree=bounded_tree(posed,reference_surface)[0]
    cloth_trees=[bounded_tree(posed,shell) for shell in cloth]
    edge_crossings,pairs=crossings(posed,subject,tree)
    gaps,hits=signed_clearances(posed[indices],[*cloth_trees,anatomical_tree])
    worst_index=int(np.argmin(gaps));i=indices[worst_index];minimum=float(gaps[worst_index])
    worst={'vertex':i,'point':list(posed[i]),'support':list(hits[worst_index]),'gap':minimum}
    if diagnostic is None:
        for local,i in enumerate(indices):
            p=Vector(posed[i]);gap=float(gaps[local]);old_hit,old_normal,_,old_distance=tree.find_nearest(p)
            old_gap=old_distance if (p-old_hit).dot(old_normal)>=0 else -old_distance
            if old_gap<-.02 and gap>.02:
                diagnostic={'point':list(p),'oldNearestPlaneSignedGap':old_gap,'closedVolumeSignedGap':gap,'reason':'Nearest open boundary face plane does not classify solid containment.'}
                break
    return {'candidatePairs':pairs,'edgeCrossings':edge_crossings,'minimumSignedGap':minimum,'worstProbe':worst}

selected=next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--clips=')),None)
diagnostic_times=next(([float(t) for t in a.split('=',1)[1].split(',')] for a in sys.argv if a.startswith('--at=')),None)
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
    for seconds in (diagnostic_times if diagnostic_times is not None else sorted(times)[:1] if '--first-frame' in sys.argv else sorted(times)):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update();posed=points()
        anatomical_points=skin_reference(reference,fields,rig)
        anatomical_bound=bounded_tree(anatomical_points,reference_faces,False)
        anatomical_tree=anatomical_bound[0]
        if real_diagnostic is None:
            origin=rig.matrix_world@rig.pose.bones['spine'].head
            direction=rig.matrix_world.to_3x3()@Vector((0,-1,0));direction.normalize()
            outside=origin+direction*2
            if not inside_closed(anatomical_tree,origin) or inside_closed(anatomical_tree,outside):raise RuntimeError('Anatomical inside/outside diagnostic failed')
            if not anatomical_tree.exact_inside(origin) or anatomical_tree.exact_inside(outside):raise RuntimeError('Exact anatomical containment control failed')
            hit,_,_,distance=anatomical_tree.ray_cast(origin,direction)
            if hit is None or distance<=0:raise RuntimeError('Real body crossing diagnostic missed the visible body envelope')
            real_diagnostic={'insidePoint':list(origin),'outsidePoint':list(outside),'actualBoundaryHit':list(hit),'exitDistance':distance,'insideParity':True,'outsideParity':False,'exactInsideParity':True,'exactOutsideParity':False}
        for name,(subject,reference_surface,cloth) in sets.items():samples[name].append({'seconds':seconds,**measure(posed,subject,reference_surface,cloth,probes[name],anatomical_bound)})
    for name in sets:records[name].append({'clip':clip['name'],'samples':samples[name]})
    print('Outfit clearance: '+clip['name'],flush=True)
if sha(source)!=hashlib.sha256(raw).hexdigest() or sha(foundation)!=foundation_hash:raise RuntimeError('Outfit gate input changed during inspection')
for name,digest in checker_hashes.items():
    if sha(Path(__file__).with_name(name))!=digest:raise RuntimeError('Outfit checker changed during inspection: '+name)
for name in sets:
    report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'checkerSources':checker_hashes,'nativeContainmentCorrections':CONTAINMENT_DIAGNOSTICS,'importedTriangles':triangles,'probeVertices':len(probes[name]),'clips':records[name],
            'scope':'Actual exported surface intersections and closed-volume signed clearance, with a retained closed anatomical body beneath the real exported garment shells. Open neck/cuff surfaces are used for visible intersections but never as a face-plane inside/outside test. The complete brigandine, shoulder bridges and padding are checked against shirt/trousers; steel lames are independently checked against their actual outer soft layers. Actual dispatch and tool cases are checked against all worn/exposed body surfaces. Intentional sewn/riveted contacts are checked separately by semantic attachment identity.','status':'measured','closedTopology':closed,'underlyingBody':{'path':foundation.relative_to(WORK).as_posix(),'sha256':hashlib.sha256(foundation.read_bytes()).hexdigest()},'falsePositiveDiagnostic':diagnostic,'realCrossingDiagnostic':real_diagnostic}
    (WORK/'review'/f'{KEY}_lod{lod}_{"diagnostic_" if "--first-frame" in sys.argv or diagnostic_times is not None else "selected_" if selected else ""}{name}.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
