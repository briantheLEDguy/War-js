"""Track real LOD attachment triangles by retained semantic geometry identity."""
import bpy,hashlib,json,math,struct,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
sys.path.insert(0,str(Path(__file__).resolve().parent))
from surface_contact import bounded_tree
WORK=Path(__file__).resolve().parents[1];KEY='frontier_sunmeadow_empire_field_captain'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
checker_hashes={name:sha(Path(__file__).with_name(name)) for name in ('inspect_equipment_attachment.py','surface_contact.py')}
lod=int(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--lod=')),'0'))
source=WORK/'runtime'/f'{KEY}_lod{lod}.glb';raw=source.read_bytes();length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
mapping_path=WORK/'review/semantic-parts.json';mapping=json.loads(mapping_path.read_text())
anchors_path=WORK/'review/equipment-attachment-source.json';anchors=json.loads(anchors_path.read_text())
input_hashes={source:hashlib.sha256(raw).hexdigest(),mapping_path:sha(mapping_path),anchors_path:sha(anchors_path)}
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers))
body.data.calc_loop_triangles();triangles=len(body.data.loop_triangles)
expected=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives'])
if triangles!=expected:raise RuntimeError('Attachment audit must import exactly the hashed LOD')
attribute=next((a for a in body.data.attributes if a.name.upper()=='_CAPTAIN_PART'),None)
if attribute is None or attribute.domain!='POINT':raise RuntimeError('Actual imported geometry lacks semantic part identity')
values=np.array([item.value for item in attribute.data]);identities=np.rint(values).astype(int)
known={row['id'] for row in mapping['parts'].values()}
if len(values)!=len(body.data.vertices) or np.max(np.abs(values-identities))>1e-6 or any(i not in known for i in identities):raise RuntimeError('Part identity is missing or interpolated')
faces={};referenced=set()
for triangle in body.data.loop_triangles:
    ids=tuple(triangle.vertices);parts={int(identities[i]) for i in ids}
    if len(parts)!=1:raise RuntimeError('LOD triangle crosses semantic part identities')
    faces.setdefault(parts.pop(),[]).append(ids);referenced.update(ids)
if len(referenced)!=len(values):raise RuntimeError('Semantic coverage includes unused phantom geometry')
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update()

def points():
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());data=np.empty(len(evaluated.data.vertices)*3)
    evaluated.data.vertices.foreach_get('co',data);matrix=np.array(body.matrix_world)
    return data.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]

rest=points();links=[]
for link in anchors['links']:
    row={'id':link['id'],'maximumGap':min(.006,link['maximumGap'])}
    for role in ('subject','support'):
        part=link[role];identity=mapping['parts'][part['object']]['id']
        if identity not in faces:raise RuntimeError('LOD discarded required carrying part: '+part['object'])
        selected=faces[identity];tree=bounded_tree(rest,selected)[0]
        hit,normal,triangle,distance=tree.find_nearest(Vector(part['point']))
        if hit is None or distance>.006:raise RuntimeError('LOD displaced attachment anchor: '+link['id']+'/'+role+' '+str(distance))
        indices=selected[triangle];a,b,c=(Vector(rest[i]) for i in indices)
        weights=barycentric_transform(hit,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        if any(w<-.0001 or w>1.0001 for w in weights):raise RuntimeError('Attachment anchor is outside its measured triangle')
        row[role]={'part':part['object'],'partId':identity,'triangle':indices,'barycentricWeights':list(weights),
                   'restPoint':list(hit),'sourceAnchorDistance':distance,'partTriangles':len(selected)}
    links.append(row)
selected_clips=next((a.split('=',1)[1].split(',') for a in sys.argv if a.startswith('--clips=')),None)
records=[]
for clip in doc['animations']:
    if selected_clips and clip['name'] not in selected_clips:continue
    action=next(a for a in bpy.data.actions if a.name==clip['name'] or a.name.endswith('_'+clip['name']))
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    times=set()
    for sampler in clip['samplers']:
        accessor=doc['accessors'][sampler['input']];view=doc['bufferViews'][accessor['bufferView']]
        start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        times.update(round(struct.unpack_from('<f',binary,start+i*view.get('byteStride',4))[0],8) for i in range(accessor['count']))
    keys=sorted(times);times.update((a+b)/2 for a,b in zip(keys,keys[1:]));samples=[]
    for seconds in (sorted(times)[:1] if '--first-frame' in sys.argv else sorted(times)):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update();posed=points()
        needed={link[role]['partId'] for link in links for role in ('subject','support')}
        trees={identity:bounded_tree(posed,faces[identity])[0] for identity in needed}
        measured={}
        for link in links:
            probes={role:sum((Vector(posed[i])*w for i,w in zip(link[role]['triangle'],link[role]['barycentricWeights'])),Vector()) for role in ('subject','support')}
            subject_gap=trees[link['support']['partId']].find_nearest(probes['subject'])[3]
            support_gap=trees[link['subject']['partId']].find_nearest(probes['support'])[3]
            measured[link['id']]={'subjectToSupport':subject_gap,'supportToSubject':support_gap,'anchorSeparation':(probes['subject']-probes['support']).length}
        samples.append({'seconds':seconds,'links':measured})
    records.append({'clip':clip['name'],'samples':samples})
    print('Equipment attachment: '+clip['name'],flush=True)
for path,digest in input_hashes.items():
    if sha(path)!=digest:raise RuntimeError('Attachment gate input changed during inspection: '+str(path))
for name,digest in checker_hashes.items():
    if sha(Path(__file__).with_name(name))!=digest:raise RuntimeError('Attachment checker changed during inspection: '+name)
record={'model':source.name,'sha256':input_hashes[source],'importedTriangles':triangles,'sourceAttachmentSha256':input_hashes[anchors_path],
        'semanticPartsSha256':input_hashes[mapping_path],'checkerSha256':checker_hashes['inspect_equipment_attachment.py'],'checkerSources':checker_hashes,
        'coverage':{'vertices':len(values),'referencedVertices':len(referenced),'fractionalIds':0,'mixedPartTriangles':0,
                    'partVertexCounts':{str(i):int(np.sum(identities==i)) for i in sorted(set(identities))}},
        'links':links,'clips':records,'scope':'Actual exported part IDs and skinned triangle contacts for every semantic carrying link. Anatomical/garment clearance and topology are independent gates.'}
suffix='diagnostic_' if '--first-frame' in sys.argv else 'selected_' if selected_clips else ''
(WORK/'review'/f'{KEY}_lod{lod}_{suffix}equipment_attachment.json').write_text(json.dumps(record,separators=(',',':'))+'\n')
