"""Actual clip checks that the rigid sheathed tool clears moving work clothing."""
import bpy,hashlib,json,math,struct,sys
from collections import Counter
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
WORK=Path(__file__).resolve().parents[1];KEY='frontier_cinderfen_greenskin_quartermaster'
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
source=WORK/'runtime'/f'{KEY}_lod{lod}.glb';raw=source.read_bytes();length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
body.data.calc_loop_triangles();expected=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
if len(body.data.loop_triangles)!=expected:raise RuntimeError('Unexpected imported tool inspection mesh')
rest=np.array([v.co[:] for v in body.data.vertices])
tool=[tuple(f.vertices) for f in body.data.polygons if any(t in body.data.materials[f.material_index].name for t in ('quartermaster_ledger_case_','quartermaster_inventory_metal','quartermaster_case_suspension_'))]
cloth_polygons=[f for f in body.data.polygons if any(t in body.data.materials[f.material_index].name for t in ('_woven_linen','_wool','quartermaster_supply_waistcoat','body_mire_brutish_v1_m.body'))]
cloth=[tuple(f.vertices) for f in cloth_polygons]
collision_targets={body.data.materials[f.material_index].name for f in cloth_polygons}
if not any('body_mire_brutish_v1_m.body' in name for name in collision_targets):raise RuntimeError('Exposed anatomy was omitted from clearance targets')
if not any('_woven_linen' in name for name in collision_targets):raise RuntimeError('Continuous shirt was omitted from clearance targets')
if len(tool)<100 or len(cloth)<100:raise RuntimeError('Clearance surface selection is incomplete')
cloth_materials=[body.data.materials[f.material_index].name for f in cloth_polygons]
if len(tool)<200 or len(cloth)<2000:raise RuntimeError('Missing ledger/tool or full-clothing inspection surface')
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
        p=points[tool_ids];tree=BVHTree.FromPolygons(points[cloth_ids],cloth_faces,all_triangles=True);crossings=[];targets=Counter()
        for a,b in edges:
            start=Vector(p[a]);delta=Vector(p[b])-start
            if delta.length<.001:continue
            direction=delta.normalized();hit,normal,triangle,distance=tree.ray_cast(start+direction*.00025,direction,delta.length-.0005)
            if hit is not None:crossings.append(list(hit));targets[cloth_materials[triangle]]+=1
        samples.append({'seconds':seconds,'crossings':len(crossings),'firstCrossings':crossings[:3],'crossingTargets':dict(targets)})
    records.append({'clip':animation['name'],'samples':samples,'maximumCrossings':max(s['crossings'] for s in samples)})
    print(animation['name'],records[-1]['maximumCrossings'],flush=True)
report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'importedTriangles':expected,'toolTriangles':len(tool),'clothTriangles':len(cloth),'collisionTargets':sorted(collision_targets),'clips':records}
(WORK/'review'/f'{KEY}_lod{lod}_tool_clearance.json').write_text(json.dumps(report,separators=(',',':')))
if any(row['maximumCrossings'] for row in records):raise RuntimeError('Carried ledger/tools cross animated clothing')
