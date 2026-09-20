"""Retain the reviewed LOD1 boot surfaces in LOD2 without changing other parts.

The retained before-master and literal input hashes make this final authoring
operation reproducible. Animation, rig and the other two delivered LODs stay
byte-identical. This is not a runtime replacement or a proxy asset.
"""
import bpy,bmesh,hashlib,json,os,shutil,sys
from pathlib import Path
WORK=Path(__file__).resolve().parents[1];ROOT=WORK.parents[2]
sys.path.insert(0,str(WORK/'tools'))
from export_tangents import repair_export_tangents
KEY='frontier_sunmeadow_high_elf_scout';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record_path=WORK/'review'/f'{KEY}_build.json';record=json.loads(record_path.read_text())
mapping=json.loads((WORK/'review/semantic-parts.json').read_text())
boot_ids={part['id'] for name,part in mapping['parts'].items() if name.startswith('fitted_boot_')}
if len(boot_ids)!=2:raise RuntimeError('Expected two exact authored boot parts')
reference=record['lods'][1];target=record['lods'][2]
reference_master=WORK/reference['master'];target_master=WORK/target['master']
before=target_master.with_name(target_master.stem+'.before-boot-retention.blend')
if 'bootRetention' not in target:
    if sha(target_master)!=target['masterSha256']:raise RuntimeError('LOD2 input master changed')
    shutil.copyfile(target_master,before)
    shutil.copyfile(WORK/'runtime'/target['model'],WORK/'review'/f'{KEY}_lod2_before_boot_retention.glb')
else:
    if sha(before)!=target['bootRetention']['inputMasterSha256']:raise RuntimeError('Retained original LOD2 master changed')
if sha(reference_master)!=reference['masterSha256']:raise RuntimeError('Reviewed boot reference master changed')
unchanged={WORK/'runtime'/lod['model']:sha(WORK/'runtime'/lod['model']) for lod in record['lods'][:2]}
bpy.ops.wm.open_mainfile(filepath=str(before))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.data.attributes.get('_SCOUT_PART'))
retained_actions=set(bpy.data.actions)
with bpy.data.libraries.load(str(reference_master),link=False) as (available,loaded):loaded.objects=[body.name]
donor=loaded.objects[0]
if donor is None:raise RuntimeError('Missing retained LOD1 character object')
bpy.context.collection.objects.link(donor)
if max(abs(a-b) for a,b in zip(sum((list(row) for row in body.matrix_world),[]),sum((list(row) for row in donor.matrix_world),[])))>1e-8:
    raise RuntimeError('LOD master coordinate systems differ')
for modifier in list(donor.modifiers):donor.modifiers.remove(modifier)
donor.parent=None
if len(donor.data.materials)!=len(body.data.materials):raise RuntimeError('LOD material slot contracts differ')
for index,material in enumerate(donor.data.materials):
    original=body.data.materials[index]
    if material.name!=original.name and not material.name.startswith(original.name+'.'):raise RuntimeError('LOD material slot identity differs')
    donor.data.materials[index]=original
for action in list(bpy.data.actions):
    if action not in retained_actions:bpy.data.actions.remove(action,do_unlink=True)
def select_parts(obj,keep_boots):
    mesh=bmesh.new();mesh.from_mesh(obj.data);identity=mesh.verts.layers.float.get('_SCOUT_PART')
    if identity is None:raise RuntimeError('Master lost semantic source identity')
    remove=[v for v in mesh.verts if (round(v[identity]) in boot_ids)!=keep_boots]
    bmesh.ops.delete(mesh,geom=remove,context='VERTS');mesh.to_mesh(obj.data);mesh.free();obj.data.update()
select_parts(donor,True);select_parts(body,False)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);donor.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
body.data.validate();body.data.update()
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(target_master))
output=WORK/'runtime'/target['model'];staged=output.with_name(output.stem+'.pending.glb')
bpy.ops.export_scene.gltf(filepath=str(staged),export_format='GLB',use_selection=True,export_animations=True,
    export_tangents=True,export_attributes=True,export_animation_mode='ACTIONS',export_skins=True,export_morph=False)
repair=repair_export_tangents(staged);raw=staged.read_bytes();doc=json.loads(raw[20:20+int.from_bytes(raw[12:16],'little')])
target.update({'sha256':sha(staged),'bytes':len(raw),'masterSha256':sha(target_master),'tangentRepair':repair,
    'triangles':sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes'] for p in m['primitives']),
    'bootRetention':{'reason':'Retain complete reviewed boot shafts through knee/ankle bending in LOD2.',
        'referenceMaster':reference['master'],'referenceMasterSha256':sha(reference_master),
        'inputMaster':before.relative_to(WORK).as_posix(),'inputMasterSha256':sha(before),
        'tool':'tools/retain_lod2_boots.py','toolSha256':sha(Path(__file__)),'parts':sorted(boot_ids)}})
# The final GLB semantic coverage is verified by the independent attachment
# import; the previous reduction's count is not valid for this finished mesh.
target.pop('semanticCoverage',None)
for path in (before,reference_master,Path(__file__).resolve()):
    relative=path.relative_to(ROOT).as_posix();entry={'path':relative,'sha256':sha(path),'bytes':path.stat().st_size}
    record['sourceFiles']=[r for r in record['sourceFiles'] if r['path']!=relative]+[entry]
for path,digest in unchanged.items():
    if sha(path)!=digest:raise RuntimeError('A previously approved LOD changed')
record['sourceTools']['tools/retain_lod2_boots.py']=sha(Path(__file__))
record.pop('validationSourceFiles',None)
os.replace(staged,output);record_path.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'status':'retained_reviewed_boots','lod':target}))
