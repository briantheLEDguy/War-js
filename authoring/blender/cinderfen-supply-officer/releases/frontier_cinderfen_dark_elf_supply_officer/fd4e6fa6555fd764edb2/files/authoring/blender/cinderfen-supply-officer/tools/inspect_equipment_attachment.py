"""Measure both load-bearing patches of both straps in source and real exports."""
import bpy,hashlib,json,math,struct,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WORK=Path(__file__).resolve().parents[1];KEY='frontier_cinderfen_dark_elf_supply_officer'
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
source=WORK/'runtime'/f'{KEY}_lod{lod}.glb'
master=WORK/'sources'/f'{KEY}.blend'
LABELS={'belt':'officer_belt_attachment_support','case':'officer_ledger_case_shell',
        'belt_contact':'officer_case_suspension_belt_contact',
        'case_contact':'officer_case_suspension_case_contact'}


def geometry(objects):
    points=[];faces={label:[] for label in LABELS}
    for obj in objects:
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
        mesh.calc_loop_triangles();offset=len(points)
        points.extend(obj.matrix_world@vertex.co for vertex in mesh.vertices)
        for triangle in mesh.loop_triangles:
            name=mesh.materials[triangle.material_index].name
            for label,material in LABELS.items():
                if name==material:faces[label].append(tuple(offset+i for i in triangle.vertices))
        evaluated.to_mesh_clear()
    return np.array(points),faces


def patches(points,faces):
    result=[]
    for endpoint in ('belt','case'):
        selected=faces[endpoint+'_contact'];remaining=set(range(len(selected)))
        neighbors={}
        for index,face in enumerate(selected):
            for vertex in face:neighbors.setdefault(vertex,set()).add(index)
        components=[]
        while remaining:
            todo=[remaining.pop()];component=[]
            while todo:
                index=todo.pop();component.append(selected[index])
                adjacent=set().union(*(neighbors[v] for v in selected[index]))&remaining
                remaining-=adjacent;todo.extend(adjacent)
            components.append(component)
        components.sort(key=lambda group:float(np.mean(points[sorted({v for face in group for v in face}),0])))
        if len(components)!=2:raise RuntimeError(f'{endpoint} requires two independent strap contact patches: {len(components)}')
        for strap,group in enumerate(components):
            result.append({'strap':strap,'endpoint':endpoint,'faces':group,'vertices':sorted({v for face in group for v in face})})
    return result


def measure(points,faces,groups):
    trees={name:BVHTree.FromPolygons(points,faces[name],all_triangles=True) for name in ('belt','case')}
    result=[]
    for group in groups:
        tree=trees[group['endpoint']];distances=[];signed=[]
        for vertex in group['vertices']:
            point=Vector(points[vertex]);hit,normal,triangle,distance=tree.find_nearest(point)
            distances.append(float(distance));signed.append(float((point-hit).dot(normal)))
        area=sum(float(np.linalg.norm(np.cross(points[b]-points[a],points[c]-points[a])))/2 for a,b,c in group['faces'])
        result.append({'strap':group['strap'],'endpoint':group['endpoint'],'probeVertices':len(distances),
                       'minimumGap':min(distances),'maximumGap':max(distances),
                       'contactCoverage':sum(d<=.0015 for d in distances)/len(distances),
                       'minimumSignedDistance':min(signed),'contactArea':area})
    return result


def failures(records):
    return [r for r in records if r['probeVertices']<3 or r['maximumGap']>.003 or
            r['minimumGap']>.0015 or r['contactCoverage']<.80 or
            r['minimumSignedDistance']<-.0015 or r['contactArea']<.00009]


bpy.ops.wm.open_mainfile(filepath=str(master))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
points,faces=geometry([bpy.data.objects[name] for name in ('work_belt','officer_closed_ledger_case','officer_case_suspension_0','officer_case_suspension_1')])
source_records=measure(points,faces,patches(points,faces))

raw=source.read_bytes();length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
body.data.calc_loop_triangles();expected=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
if len(body.data.loop_triangles)!=expected:raise RuntimeError('Attachment inspection imported a different mesh')
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()
points,faces=geometry([body]);groups=patches(points,faces);rest=measure(points,faces,groups)
records=[]
for animation in doc['animations']:
    action=next(a for a in bpy.data.actions if a.name==animation['name'] or a.name.endswith('_'+animation['name']))
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    times=set()
    for sampler in animation['samplers']:
        accessor=doc['accessors'][sampler['input']];view=doc['bufferViews'][accessor['bufferView']]
        start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        times.update(round(struct.unpack_from('<f',binary,start+i*view.get('byteStride',4))[0],8) for i in range(accessor['count']))
    keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]));samples=[]
    for seconds in sorted(times):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update()
        evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());coordinates=np.empty(len(body.data.vertices)*3)
        evaluated.data.vertices.foreach_get('co',coordinates)
        points=coordinates.reshape(-1,3)@np.array(body.matrix_world.to_3x3()).T+np.array(body.matrix_world.translation)
        samples.append({'seconds':seconds,'attachments':measure(points,faces,groups)})
    records.append({'clip':animation['name'],'samples':samples})
    print(animation['name'],max(r['maximumGap'] for s in samples for r in s['attachments']),flush=True)
report={'model':source.name,'sha256':hashlib.sha256(raw).hexdigest(),'masterSha256':hashlib.sha256(master.read_bytes()).hexdigest(),
        'importedTriangles':expected,'sourceAttachments':source_records,'restAttachments':rest,'clips':records}
(WORK/'review'/f'{KEY}_lod{lod}_equipment_attachment.json').write_text(json.dumps(report,separators=(',',':')))
bad=failures(source_records+rest+[r for c in records for s in c['samples'] for r in s['attachments']])
if bad:raise RuntimeError('Suspension contact/patch-area gate failed: '+json.dumps(bad[:4]))
