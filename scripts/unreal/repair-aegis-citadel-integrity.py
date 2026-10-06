"""Repair only the receipted private candidate's misplaced review start/bindings.

Root alone executes this with native writers serialized. Imported meshes,
retained actors and every published source are preserved. No admission is granted.
"""
import json
import shutil
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT,sha,digest,validate
from citadel_stage_contract import (REVIEW_START_CM,expected_misowned_review_start,
    canonical_city_payload,require_final_city_hashes)
from shared_city_sources import package_file
from shared_city_authoring import prepare_city
from world_actor_state import snapshot

current=json.loads((OUT/'current.json').read_text());RUN=OUT/current['revision']
plan=json.loads((RUN/'blueprint.json').read_text());validate(plan)
receipt_file=RUN/'candidate.json';receipt=json.loads(receipt_file.read_text())
DEST='/Game/WorldRebuild/AegisCitadel_'+plan['revision']
geometry=DEST+'/Layers/GothicCitadel';preview=DEST+'/ReviewCandidate';siege=DEST+'/SiegeCandidate'
if receipt['signature']!=plan['signature'] or receipt['published'] or receipt['map']!=preview or receipt['siegeMap']!=siege:
    raise RuntimeError('Repair requires the exact unpublished private candidate')
for package,expected in {**receipt['packageHashes'],**receipt['sourceHashes']}.items():
    if sha(package_file(ROOT,package))!=expected:raise RuntimeError('Preserve independently edited package: '+package)
if receipt.get('integrityRepair'):
    require_final_city_hashes(receipt['city'],receipt['packageHashes'],receipt['sourceHashes'])
    unreal.log('WAR_CITADEL_INTEGRITY_ALREADY_REPAIRED');raise SystemExit(0)
directory=RUN/'integrity-repair';journal=directory/'pending.json'
if journal.exists():raise RuntimeError('Interrupted integrity repair requires explicit journal recovery')
directory.mkdir(exist_ok=True)
original_receipt=dict(receipt)
(directory/'candidate-before.json').write_text(json.dumps(receipt,indent=2)+'\n')
mutated=[geometry,preview,siege,DEST+'/City']
for package in mutated:
    if not package.startswith(DEST+'/'):raise RuntimeError('Repair escaped the private namespace')
    source=package_file(ROOT,package);target=directory/'native-before'/source.relative_to(ROOT)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise RuntimeError('Preserve existing repair backup')
    shutil.copy2(source,target)
journal.write_text(json.dumps(dict(signature=plan['signature'],packages={p:receipt['packageHashes'][p] for p in mutated}),indent=2)+'\n')
assets=unreal.EditorAssetLibrary;levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def load(package):
    if not levels.load_level(package):raise RuntimeError('Cannot load private candidate package')
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world);return world

def select(package):
    if not levels.set_current_level_by_name(package.rsplit('/',1)[1]):raise RuntimeError('Cannot select private actor owner')

def own(package):
    return [a for a in actors.get_all_level_actors() if a.get_outer().get_path_name().split('.')[0]==package]

def scenery_valid(package):
    for actor in own(package):
        if not unreal.WarCityDefinition.is_scenery_actor(actor):raise RuntimeError('Gameplay remains in shared scenery: '+actor.get_path_name())
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            if not component.is_visible():continue
            mesh=component.static_mesh
            if not mesh or not mesh.get_path_name().startswith('/Game/') or any(
                    not component.get_material(i) for i in range(component.get_num_materials())):
                raise RuntimeError('Invalid authored scenery model/material')

load(geometry);before={a.get_name():snapshot(a) for a in own(geometry)}
invalid=[a for a in own(geometry) if not unreal.WarCityDefinition.is_scenery_actor(a)]
if len(invalid)!=1 or not expected_misowned_review_start(invalid[0].get_name(),snapshot(invalid[0])):
    raise RuntimeError('Only the exact mistakenly owned review start may be removed')
removed=dict(name=invalid[0].get_name(),state=before[invalid[0].get_name()])
if not actors.destroy_actor(invalid[0]):raise RuntimeError('Cannot remove exact misplaced review start')
expected={k:v for k,v in before.items() if k!=removed['name']}
after={a.get_name():snapshot(a) for a in own(geometry)}
if after!=expected:raise RuntimeError('Repair changed an unrelated private scenery actor/component')
scenery_valid(geometry);select(geometry)
if not levels.save_current_level():raise RuntimeError('Cannot save repaired private scenery')

world=load(preview)
actual=[level.get_outer().get_path_name().split('.')[0] for level in unreal.EditorLevelUtils.get_levels(world)
        if level.get_outer().get_path_name().split('.')[0]!=preview]
if len(actual)!=len(set(actual)) or set(actual)-set(receipt['sceneryLevels']):
    raise RuntimeError('Preserve independently edited review streaming references')
for package in receipt['sceneryLevels']:
    if package not in actual and not unreal.EditorLevelUtils.add_level_to_world(world,package,unreal.LevelStreamingAlwaysLoaded):
        raise RuntimeError('Cannot restore review scenery reference')
select(preview)
starts=[a for a in own(preview) if a.get_class().get_name()=='PlayerStart']
if len(starts)>1:raise RuntimeError('Review contains independent spawn edits')
if starts:
    position=starts[0].get_actor_location()
    if any(abs(v-e)>.1 for v,e in zip((position.x,position.y,position.z),REVIEW_START_CM)):
        raise RuntimeError('Preserve independently moved review start')
else:
    starts=[actors.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(*REVIEW_START_CM))]
if starts[0].get_outer().get_path_name().split('.')[0]!=preview:raise RuntimeError('Review start still has wrong owner')
if not levels.save_current_level():raise RuntimeError('Cannot save restored persistent review references')

for package in receipt['sceneryLevels']:
    load(package);scenery_valid(package)
zone=dict(id='aegis_capital',origin=receipt['city']['origin'],levels={
    'scenery_'+str(i):p for i,p in enumerate(receipt['sceneryLevels'])})
def backup(file):
    target=directory/'native-before'/file.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copy2(file,target)
def created(package):raise RuntimeError('Integrity repair must not create new native packages: '+package)
city=prepare_city(zone,DEST+'/City',backup,created,directory)
city['revisionPayload']=canonical_city_payload({p:city['packageHashes'][p] for p in city['sceneryLevels']},
    city['dependencyHashes'],city['origin'])
if assets.load_asset(city['definition']).get_editor_property('revision')!=city['revision']:
    raise RuntimeError('Actual native City revision differs from final canonical payload')
world=load(siege);select(siege)
fields=[a for a in own(siege) if isinstance(a,unreal.WarSiegeBattlefield)]
if len(fields)!=1:raise RuntimeError('Private candidate battlefield identity changed')
field=fields[0];field.set_editor_property('city_definition',assets.load_asset(city['definition']))
field.set_editor_property('reviewed_city_revision','')
for key in ('traversal_reviewed','lower_city_reviewed','equipped_roster_reviewed'):field.set_editor_property(key,False)
if not levels.save_current_level():raise RuntimeError('Cannot save final private siege binding')
for package,expected_hash in receipt['sourceHashes'].items():
    if sha(package_file(ROOT,package))!=expected_hash:raise RuntimeError('Published source changed during private repair')
unchanged={p:h for p,h in original_receipt['packageHashes'].items() if p not in mutated}
for package,expected_hash in unchanged.items():
    if sha(package_file(ROOT,package))!=expected_hash:raise RuntimeError('Unrelated imported asset/package changed during repair')
receipt['city']=city;receipt['packageHashes']={p:sha(package_file(ROOT,p)) for p in receipt['packageHashes']}
require_final_city_hashes(city,receipt['packageHashes'],receipt['sourceHashes'])
receipt['stageRecipeSha256']=sha(Path(__file__).with_name('stage-aegis-citadel.py'))
receipt['stageDependencySha256']={'citadel_stage_contract.py':sha(Path(__file__).with_name('citadel_stage_contract.py'))}
receipt['integrityRepair']=dict(scriptSha256=sha(Path(__file__)),beforeReceiptSha256=sha(directory/'candidate-before.json'),
    originalStageRecipeSha256=original_receipt['stageRecipeSha256'],removedReviewStart=removed,
    preservedSceneryStateSha256=digest(after),packagesChanged=mutated,sourcePackagesPreserved=len(receipt['sourceHashes']))
receipt.pop('navigation',None)
for key in ('geometryApproved','traversalApproved','visualApproved','published'):receipt[key]=False
receipt_file.write_text(json.dumps(receipt,indent=2)+'\n');journal.unlink()
unreal.log('WAR_CITADEL_INTEGRITY_REPAIRED='+str(receipt_file))
