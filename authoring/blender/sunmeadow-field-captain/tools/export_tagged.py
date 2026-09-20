"""Finish actual authored captain meshes with retained semantic part identity.

The scalar custom attribute identifies geometry for independent attachment
audits after batching and LOD reduction; it adds no runtime behavior.
"""
import bpy,bmesh,json,hashlib,os,shutil,sys,struct
import numpy as np
from pathlib import Path
WORK=Path(__file__).resolve().parents[1];ROOT=WORK.parents[2]
sys.path.insert(0,str(WORK/'tools'))
from export_tangents import repair_export_tangents
from build_inhabitants import build_provenance,CAST
KEY='frontier_sunmeadow_empire_field_captain'
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
master=WORK/'sources'/f'{KEY}.blend'
authored=WORK/'sources'/f'{KEY}.authored.blend'
bpy.ops.wm.open_mainfile(filepath=str(master))
if any(o.type=='MESH' and o.data.attributes.get('_CAPTAIN_PART') for o in bpy.context.scene.objects):
    if not authored.exists():raise RuntimeError('Tagged master lacks its retained authored input')
    bpy.ops.wm.open_mainfile(filepath=str(authored))
else:shutil.copyfile(master,authored)
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
meshes=sorted((o for o in bpy.context.scene.objects if o.type=='MESH' and
               any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)),key=lambda o:o.name)
body=next(o for o in meshes if o.name=='empire_field_captain_exposed_anatomy')
parts={}
for part,obj in enumerate(meshes,1):
    attribute=obj.data.attributes.get('_CAPTAIN_PART') or obj.data.attributes.new('_CAPTAIN_PART','FLOAT','POINT')
    attribute.data.foreach_set('value',[float(part)]*len(obj.data.vertices))
    parts[obj.name]={'id':part,'sourceVertices':len(obj.data.vertices),'materials':[m.name for m in obj.data.materials]}
mapping={'schemaVersion':1,'attribute':'_CAPTAIN_PART','authoringMaster':authored.relative_to(WORK).as_posix(),
         'authoringMasterSha256':digest(authored),'parts':parts}
mapping_path=WORK/'review/semantic-parts.json';mapping_path.write_text(json.dumps(mapping,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(master))
bpy.ops.object.select_all(action='DESELECT')
for obj in meshes:obj.select_set(True)
for obj in meshes:
    bpy.context.view_layer.objects.active=obj
    for modifier in list(obj.modifiers):
        if modifier.type in ('SUBSURF','SOLIDIFY'):
            while list(obj.modifiers).index(modifier)>0:bpy.ops.object.modifier_move_up(modifier=modifier.name)
            bpy.ops.object.modifier_apply(modifier=modifier.name)
    if obj.data.uv_layers:obj.data.uv_layers.active_index=0;obj.data.uv_layers[0].active_render=True
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
world=body.matrix_world.copy();body.parent=None;body.matrix_world=world
base=body.data.copy();lods=[];pending=[];reviewed_boot_source=None
boot_ids={row['id'] for name,row in parts.items() if name.startswith('fitted_boot_')}
if len(boot_ids)!=2:raise RuntimeError('Expected two anatomical fitted boot surfaces')
def keep_boot_parts(obj,keep):
    mesh=bmesh.new();mesh.from_mesh(obj.data);identity=mesh.verts.layers.float.get('_CAPTAIN_PART')
    if identity is None:raise RuntimeError('Boot retention requires exact semantic identity')
    remove=[v for v in mesh.verts if (round(v[identity]) in boot_ids)!=keep]
    bmesh.ops.delete(mesh,geom=remove,context='VERTS');mesh.to_mesh(obj.data);mesh.free();obj.data.update()
for lod,ratio in enumerate([1,.58,.27]):
    body.data=base.copy()
    if ratio<1:
        modifier=body.modifiers.new('Reviewed_LOD_reduction','DECIMATE');modifier.ratio=ratio
        bpy.ops.object.modifier_move_up(modifier=modifier.name);bpy.ops.object.modifier_apply(modifier=modifier.name)
    if lod==2:
        # Thin inner/outer boot shafts cannot be collapsed as aggressively as
        # the body. Keep the actual LOD1 shell before a slit can enter review.
        if reviewed_boot_source is None:raise RuntimeError('Missing measured LOD1 boot input')
        donor=body.copy();donor.data=reviewed_boot_source.copy();bpy.context.collection.objects.link(donor)
        for modifier in list(donor.modifiers):donor.modifiers.remove(modifier)
        keep_boot_parts(donor,True);keep_boot_parts(body,False)
        bpy.ops.object.select_all(action='DESELECT');body.select_set(True);donor.select_set(True)
        bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
    bm=bmesh.new();bm.from_mesh(body.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='FIXED',ngon_method='BEAUTY')
    bmesh.ops.dissolve_degenerate(bm,dist=.000001,edges=list(bm.edges))
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free();body.data.validate();body.data.update()
    identity_attribute=body.data.attributes['_CAPTAIN_PART']
    values=np.array([item.value for item in identity_attribute.data],dtype=np.float32)
    integral=np.rint(values)
    # Subdivision of a constant scalar can introduce one float32 ULP (observed
    # 22 -> 22.000001907 at two LOD0 vertices). Only numerical noise is snapped;
    # any meaningful mixture of two part identities is rejected before export.
    if np.any(np.abs(values-integral)>np.spacing(np.maximum(np.abs(values),1))*4):raise RuntimeError('Geometry operation mixed semantic identities')
    for face in body.data.polygons:
        if len({int(integral[i]) for i in face.vertices})!=1:raise RuntimeError('Triangle crosses authored semantic parts')
    identity_attribute.data.foreach_set('value',integral)
    for vertex in body.data.vertices:
        if lod==2 and int(integral[vertex.index]) in boot_ids:continue
        ranked=sorted([(g.group,g.weight) for g in vertex.groups],key=lambda row:-row[1]);total=sum(w for _,w in ranked[:4])
        for index,weight in ranked[4:]:body.vertex_groups[index].remove([vertex.index])
        for index,weight in ranked[:4]:body.vertex_groups[index].add([vertex.index],weight/total,'REPLACE')
    if lod==1:reviewed_boot_source=body.data.copy()
    bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True)
    final=WORK/'sources'/f'{KEY}_lod{lod}.blend';bpy.ops.wm.save_as_mainfile(filepath=str(final))
    output=WORK/'runtime'/f'{KEY}_lod{lod}.glb';staged=output.with_name(output.stem+'.pending.glb')
    bpy.ops.export_scene.gltf(filepath=str(staged),export_format='GLB',use_selection=True,export_animations=True,
        export_tangents=True,export_attributes=True,export_animation_mode='ACTIONS',export_skins=True,export_morph=False)
    repair=repair_export_tangents(staged)
    raw=staged.read_bytes();length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
    counts={};vertex_count=0
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            accessor=doc['accessors'][primitive['attributes']['_CAPTAIN_PART']]
            positions=doc['accessors'][primitive['attributes']['POSITION']]
            if accessor['count']!=positions['count'] or accessor['componentType']!=5126 or accessor['type']!='SCALAR':raise RuntimeError('Part coverage differs from exported geometry')
            view=doc['bufferViews'][accessor['bufferView']];offset=view.get('byteOffset',0)+accessor.get('byteOffset',0)
            for i in range(accessor['count']):
                value=struct.unpack_from('<f',binary,offset+i*view.get('byteStride',4))[0]
                identity=round(value)
                if abs(value-identity)>1e-6 or identity<1 or identity>len(parts):raise RuntimeError('LOD interpolated semantic part identity')
                counts[str(identity)]=counts.get(str(identity),0)+1;vertex_count+=1
    lods.append({'level':lod,'model':output.name,'master':final.relative_to(WORK).as_posix(),'masterSha256':digest(final),
        'sha256':digest(staged),'bytes':len(raw),'tangentRepair':repair,
        'triangles':sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives']),
        'clips':[a['name'] for a in doc['animations']],'semanticCoverage':{'vertices':vertex_count,'partVertexCounts':counts,'fractionalIds':0}})
    if lod==2:lods[-1]['bootRetention']={'policy':'Exact LOD1 boot topology, winding and skinning retained before lowest-LOD export.',
        'referenceMaster':lods[1]['master'],'referenceMasterSha256':lods[1]['masterSha256'],
        'tool':'tools/export_tagged.py','toolSha256':digest(__file__),'parts':sorted(boot_ids)}
    pending.append((staged,output))
source=WORK/'foundations/body_civic_humanoid_v2_m.glb'
files,images=build_provenance(source,master,CAST['empire_field_captain'],body)
known={row['path'] for row in files}
for path in [Path(__file__).resolve(),authored,mapping_path]:
    relative=path.relative_to(ROOT).as_posix()
    if relative not in known:files.append({'path':relative,'sha256':digest(path),'bytes':path.stat().st_size})
for staged,output in pending:os.replace(staged,output)
record={'key':KEY,'status':'draft','sourceFoundationSha256':digest(source),'masterSha256':digest(master),
        'generatorSha256':digest(WORK/'tools/build_inhabitants.py'),'exporterSha256':digest(__file__),
        'authoringMasterSha256':digest(authored),'sourceFiles':files,'embeddedImages':images,
        'sourceTools':{str(p.relative_to(WORK)):digest(p) for p in sorted((WORK/'tools').glob('*.py'))},'lods':lods}
(WORK/'review'/f'{KEY}_build.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'status':'exported','lods':[{k:v for k,v in row.items() if k not in ('semanticCoverage','tangentRepair')} for row in lods]}))
