"""Reimport exact owned private faces using Unreal's clockwise convention.

Root executes with native writers serialized. Source positions, outward normals,
UVs, materials, paths and gameplay transforms remain unchanged. Hashes/revision
are derived from genuinely saved packages, and all admission stays false.
"""
import copy
import json
import shutil
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT,sha,digest,validate
from citadel_stage_contract import (SOURCE_TRIANGLE_CONVENTION,NATIVE_IMPORT_CONVENTION,
    native_triangle_indices,canonical_city_payload,require_final_city_hashes,checked_private_proof_start)
from shared_city_sources import package_file
from shared_city_authoring import prepare_city
from world_actor_state import snapshot

current=json.loads((OUT/'current.json').read_text());RUN=OUT/current['revision']
plan=json.loads((RUN/'blueprint.json').read_text());validate(plan)
source=json.loads((RUN/'assets-source.json').read_text())
receipt_file=RUN/'candidate.json';receipt=json.loads(receipt_file.read_text())
DEST='/Game/WorldRebuild/AegisCitadel_'+plan['revision']
geometry=DEST+'/Layers/GothicCitadel';preview=DEST+'/ReviewCandidate';siege=DEST+'/SiegeCandidate'
if (receipt['signature']!=plan['signature'] or receipt['published'] or not receipt['nativeImported']
        or receipt['map']!=preview or receipt['siegeMap']!=siege):
    raise RuntimeError('Repair requires the exact unpublished native private candidate')
if source['blueprintSignature']!=plan['signature'] or receipt['geometrySignature']!=source['geometrySignature']:
    raise RuntimeError('Authored source and native candidate identities differ')
if digest([(row['id'],row['sha256']) for row in source['assets']])!=source['geometrySignature']:
    raise RuntimeError('Source geometry manifest changed')
for recipe,expected in plan['sourceRecipes'].items():
    if sha(Path(__file__).with_name(recipe))!=expected:raise RuntimeError('Preserve changed source recipe: '+recipe)
for p in set(receipt['sourceHashes'])&set(receipt['packageHashes']):
    if receipt['sourceHashes'][p]!=receipt['packageHashes'][p]:raise RuntimeError('Conflicting source/owned package hash')
for package,expected in {**receipt['sourceHashes'],**receipt['packageHashes']}.items():
    if sha(package_file(ROOT,package))!=expected:raise RuntimeError('Preserve independently edited package: '+package)
require_final_city_hashes(receipt['city'],receipt['packageHashes'],receipt['sourceHashes'])
if receipt.get('windingRepair'):
    if (receipt.get('nativeImportConvention')!=NATIVE_IMPORT_CONVENTION
            or receipt['stageRecipeSha256']!=sha(Path(__file__).with_name('stage-aegis-citadel.py'))
            or receipt['stageDependencySha256']!={'citadel_stage_contract.py':sha(Path(__file__).with_name('citadel_stage_contract.py'))}):
        raise RuntimeError('Repaired candidate contract changed; preserve existing repair')
    unreal.log('WAR_CITADEL_WINDING_ALREADY_REPAIRED');raise SystemExit(0)
if receipt.get('nativeImportConvention'):
    raise RuntimeError('Only the known original unchanged-index import may be repaired')
master=(RUN/source['sourceMaster']['path']).resolve();master.relative_to(RUN.resolve())
if sha(master)!=source['sourceMaster']['sha256']:raise RuntimeError('Preserve changed source master')
for file,expected in source['materialSources'].items():
    if sha(ROOT/file)!=expected:raise RuntimeError('Preserve changed original PBR source')
for row in source['sourceFurnishings']:
    if sha(ROOT/row['file'])!=row['sha256']:raise RuntimeError('Preserve changed furnishing source')

assets=unreal.EditorAssetLibrary;levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mesh_tools=(unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))
bindings={row['id']:row for row in receipt['bindings']}
if len(bindings)!=38 or set(bindings)!={row['id'] for row in source['assets']}:
    raise RuntimeError('Repair requires the exact 38 source-bound native meshes')
materials=[assets.load_asset(DEST+'/Materials/M_'+role) for role in source['materialSpecs']]
if not all(materials):raise RuntimeError('Preserve candidate with missing native material')
audits=[]
for row in source['assets']:
    binding=bindings[row['id']];package=DEST+'/Meshes/SM_'+row['id']
    if binding['mesh']!=package or binding['sha256']!=receipt['packageHashes'][package]:
        raise RuntimeError('Native mesh binding changed independently')
    mesh=assets.load_asset(package)
    if (not isinstance(mesh,unreal.StaticMesh) or
            assets.get_metadata_tag(mesh,'WarCapitalTerrain')!='AegisCitadel_'+plan['revision']+':SM_'+row['id']):
        raise RuntimeError('Refuse to replace an unowned native mesh: '+package)
    if [mesh.get_material(i) for i in range(len(materials))]!=materials:
        raise RuntimeError('Preserve independently changed native mesh materials')
    file=(RUN/row['meshFile']).resolve();file.relative_to(RUN.resolve())
    if sha(file)!=row['sha256']:raise RuntimeError('Preserve changed source mesh: '+row['id'])
    data=json.loads(file.read_text());indices=native_triangle_indices(data,SOURCE_TRIANGLE_CONVENTION)
    if data['materials']!=list(source['materialSpecs']) or data['collision']!=row['collision']:
        raise RuntimeError('Unknown source material/collision convention')
    audits.append(dict(id=row['id'],sourceSha256=row['sha256'],sourceIndicesSha256=digest(data['indices']),
        nativeIndicesSha256=digest(indices),triangles=len(indices)//3))
    del data,indices

directory=RUN/'winding-repair';journal=directory/'pending.json'
if journal.exists():raise RuntimeError('Interrupted winding repair requires explicit journal recovery')
directory.mkdir(exist_ok=True)
before_file=directory/'candidate-before.json'
if before_file.exists():raise RuntimeError('Preserve existing winding repair evidence')
before_file.write_text(json.dumps(receipt,indent=2)+'\n')
original=copy.deepcopy(receipt)
mutated=[row['mesh'] for row in receipt['bindings']]+[geometry,DEST+'/City',siege]
backups={}
for package in [*mutated,preview]:
    if not package.startswith(DEST+'/'):raise RuntimeError('Repair escaped the private namespace')
    primary=package_file(ROOT,package)
    for file in [primary,*[primary.with_suffix(s) for s in ('.uexp','.ubulk','.uptnl') if primary.with_suffix(s).is_file()]]:
        target=directory/'native-before'/file.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():raise RuntimeError('Preserve an existing private package backup')
        expected=sha(file);shutil.copy2(file,target)
        if sha(target)!=expected:raise RuntimeError('Private native backup verification failed')
        backups[file.relative_to(ROOT).as_posix()]=dict(path=target.relative_to(ROOT).as_posix(),sha256=expected)
journal.write_text(json.dumps(dict(signature=plan['signature'],candidateBeforeSha256=sha(before_file),
    packages={p:receipt['packageHashes'][p] for p in mutated},backups=backups,sourceHashes=receipt['sourceHashes']),indent=2)+'\n')

def load(package):
    if not levels.load_level(package):raise RuntimeError('Cannot load private candidate package')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world);return world

def select(package):
    if not levels.set_current_level_by_name(package.rsplit('/',1)[1]):raise RuntimeError('Cannot select exact private owner')

def own(package):
    return [a for a in actors.get_all_level_actors() if a.get_outer().get_path_name().split('.')[0]==package]

def scenery_valid(package):
    for actor in own(package):
        if not unreal.WarCityDefinition.is_scenery_actor(actor):raise RuntimeError('Gameplay actor in shared private scenery')

load(geometry);before_geometry={a.get_name():snapshot(a) for a in own(geometry)}
if assets.load_asset(receipt['city']['definition']).get_editor_property('revision')!=receipt['city']['revision']:
    raise RuntimeError('Native shared definition no longer matches the receipted revision')
load(siege);before_siege={a.get_name():snapshot(a) for a in own(siege)}
fields=[a for a in own(siege) if isinstance(a,unreal.WarSiegeBattlefield)]
if len(fields)!=1:raise RuntimeError('Private battlefield identity changed')
field=fields[0]
for key,expected in (('objectives',plan['objectives']),('optional_objectives',plan['optionalObjectives']),('team_spawns',plan['teamSpawns'])):
    actual=[[p.x,p.y,p.z] for p in field.get_editor_property(key)]
    if actual!=expected:raise RuntimeError('Preserve changed native gameplay anchors/spawns')
for row,audit in zip(source['assets'],audits):
    file=RUN/row['meshFile'];data=json.loads(file.read_text())
    indices=native_triangle_indices(data,SOURCE_TRIANGLE_CONVENTION)
    mesh=unreal.WarImportLibrary.create_composite_world_surface('AegisCitadel_'+plan['revision'],'SM_'+row['id'],
        [unreal.Vector(*p) for p in data['positions']],indices,[unreal.Vector(*p) for p in data['normals']],
        [unreal.Vector2D(*p) for p in data['uvs']],[],data['triangleMaterials'],materials,row['collision'])
    if not mesh:raise RuntimeError('Native clockwise reimport failed: '+row['id'])
    lod=unreal.EditorScriptingMeshReductionOptions();lod.auto_compute_lod_screen_size=True
    lod.reduction_settings=[unreal.EditorScriptingMeshReductionSettings(percent_triangles=p,screen_size=s)
        for p,s in ((1,1),(.65,.4),(.3,.15))]
    mesh_tools.set_lods(mesh,lod)
    if not assets.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save corrected native mesh')
    binding=bindings[row['id']]
    binding.update(sha256=sha(package_file(ROOT,binding['mesh'])),sourceIndicesSha256=audit['sourceIndicesSha256'],
        nativeIndicesSha256=audit['nativeIndicesSha256'],triangles=[mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())])
    if binding['triangles'][0]!=audit['triangles']:raise RuntimeError('Corrected native LOD0 lost source triangles')
    del data,indices

load(geometry);select(geometry);expected_geometry=copy.deepcopy(before_geometry);tag_updates=[]
for row in receipt['bindings']:
    if row['gateLeaf']:continue
    identity='WarWorldObject_aegis_reference_'+row['id']
    matching=[a for a in own(geometry) if identity in [str(t) for t in a.tags]]
    if len(matching)!=1:raise RuntimeError('Private geometry ownership identity changed')
    actor=matching[0];old_hash=next(b['sha256'] for b in original['bindings'] if b['id']==row['id'])
    old_tag='WarModelSha256_'+old_hash;new_tag='WarModelSha256_'+row['sha256']
    tags=[str(t) for t in actor.tags]
    if tags.count(old_tag)!=1:raise RuntimeError('Preserve independently changed native model binding tag')
    actor.tags=[new_tag if t==old_tag else t for t in tags]
    expected_geometry[actor.get_name()]['tags']=sorted(new_tag if t==old_tag else t for t in expected_geometry[actor.get_name()]['tags'])
    tag_updates.append(dict(actor=actor.get_name(),before=old_tag,after=new_tag))
after_geometry={a.get_name():snapshot(a) for a in own(geometry)}
if after_geometry!=expected_geometry:raise RuntimeError('Winding repair changed unrelated scenery/components')
scenery_valid(geometry)
if not levels.save_current_level():raise RuntimeError('Cannot save refreshed private geometry binding tags')

world=load(siege);select(siege)
if {a.get_name():snapshot(a) for a in own(siege)}!=before_siege:
    raise RuntimeError('Reimport changed gameplay actor/component state')
proof_start=checked_private_proof_start(world,siege,plan,actors,own(siege))
after_siege={a.get_name():snapshot(a) for a in own(siege)}
if any(after_siege.get(k)!=v for k,v in before_siege.items()):raise RuntimeError('Proof start changed existing gameplay state')
new_names=set(after_siege)-set(before_siege)
if len(new_names)>1 or any(after_siege[k]['class']!='PlayerStart' for k in new_names):
    raise RuntimeError('Unexpected actor creation during private proof start repair')
if not levels.save_current_level():raise RuntimeError('Cannot save checked private proof start')

for package in receipt['sceneryLevels']:
    load(package);scenery_valid(package)
zone=dict(id='aegis_capital',origin=receipt['city']['origin'],levels={
    'scenery_'+str(i):p for i,p in enumerate(receipt['sceneryLevels'])})
def backup(file):
    # prepare_city visits unchanged source levels too. They are immutable here;
    # all legitimately mutated owned packages were already verified/backed up.
    if file in [package_file(ROOT,p) for p in mutated]:return
    known={package_file(ROOT,p):h for p,h in {**original['sourceHashes'],**original['packageHashes']}.items()}
    if file not in known or sha(file)!=known[file]:raise RuntimeError('Unexpected package visited during final city preparation')
def created(package):raise RuntimeError('Winding repair must not create new native packages: '+package)
city=prepare_city(zone,DEST+'/City',backup,created,directory)
city['revisionPayload']=canonical_city_payload({p:city['packageHashes'][p] for p in city['sceneryLevels']},
    city['dependencyHashes'],city['origin'])
if assets.load_asset(city['definition']).get_editor_property('revision')!=city['revision']:
    raise RuntimeError('Actual native City revision differs from final canonical payload')
world=load(siege);select(siege)
field=next(a for a in own(siege) if isinstance(a,unreal.WarSiegeBattlefield))
field.set_editor_property('city_definition',assets.load_asset(city['definition']))
field.set_editor_property('reviewed_city_revision','')
for key in ('traversal_reviewed','lower_city_reviewed','equipped_roster_reviewed'):field.set_editor_property(key,False)
if not levels.save_current_level():raise RuntimeError('Cannot save final private siege binding')
if {a.get_name():snapshot(a) for a in own(siege)}!=after_siege:
    raise RuntimeError('Final city binding altered unrelated gameplay/component state')
for package,expected in original['sourceHashes'].items():
    if sha(package_file(ROOT,package))!=expected:raise RuntimeError('Published source changed during private mesh repair')
for package,expected in original['packageHashes'].items():
    if package not in mutated and sha(package_file(ROOT,package))!=expected:
        raise RuntimeError('Unrelated owned asset/map changed during winding repair')
for row in source['assets']:
    if sha(RUN/row['meshFile'])!=row['sha256']:raise RuntimeError('Source mesh changed during native repair')
receipt.update(city=city,nativeImportConvention=NATIVE_IMPORT_CONVENTION,proofStart=proof_start,
    stageRecipeSha256=sha(Path(__file__).with_name('stage-aegis-citadel.py')),
    stageDependencySha256={'citadel_stage_contract.py':sha(Path(__file__).with_name('citadel_stage_contract.py'))},
    packageHashes={p:sha(package_file(ROOT,p)) for p in receipt['packageHashes']})
require_final_city_hashes(city,receipt['packageHashes'],receipt['sourceHashes'])
receipt['windingRepair']=dict(scriptSha256=sha(Path(__file__)),beforeReceiptSha256=sha(before_file),
    originalCityRevision=original['city']['revision'],originalStageRecipeSha256=original['stageRecipeSha256'],
    convention=NATIVE_IMPORT_CONVENTION,sourceTriangleAudits=audits,geometryBindingTagUpdates=tag_updates,
    packagesChanged=mutated,backups=backups,preservedSourcePackages=len(receipt['sourceHashes']),
    preservedGeometryStateSha256=digest(after_geometry),preservedGameplayStateSha256=digest(after_siege))
receipt.pop('navigation',None)
for key in ('geometryApproved','traversalApproved','visualApproved','published'):receipt[key]=False
temporary=receipt_file.with_suffix('.json.tmp');temporary.write_text(json.dumps(receipt,indent=2)+'\n');temporary.replace(receipt_file)
journal.rename(directory/'completed-journal.json')
unreal.log('WAR_CITADEL_WINDING_REPAIRED='+str(receipt_file))
