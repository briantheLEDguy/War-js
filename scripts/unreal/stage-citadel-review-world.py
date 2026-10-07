"""Clone the complete private campaign for review; never remove travel or services.

    WAR_CITADEL_INSPECT_REVISION=<12 hex> WAR_CITADEL_REVIEW_DATE=YYYYMMDD

The wrapper uses a process-local selected-map launch. Canonical maps, config,
existing review worlds and GM drafts remain byte-for-byte preserved. Extra
residents belong to an isolated gameplay layer, never the shared scenery asset.
"""
import copy
import json
import os
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from aegis_citadel_blueprint import sha,digest
from citadel_stage_contract import REVIEW_START_CM
from citadel_review_world import review_packages,checked_residents,routing_bindings
from native_animation_bindings import installed
from shared_city_sources import package_file,protected_source_file
from shared_city_authoring import load,own,save,detach,world
from world_actor_state import snapshot

revision=os.environ.get('WAR_CITADEL_INSPECT_REVISION','')
date=os.environ.get('WAR_CITADEL_REVIEW_DATE','')
review_packages(revision,date)
run=ROOT/'artifacts/unreal/aegis-citadel'/revision
candidate=json.loads((run/'candidate.json').read_text())
staged=json.loads((run/'publication-candidate.json').read_text())
plan=json.loads((run/'blueprint.json').read_text())
source=json.loads((run/'assets-source.json').read_text())
if staged.get('revision')!=revision or staged.get('published') is not False:
    raise RuntimeError('An exact unpublished full campaign candidate is required')
furnishings=[row['boundsCm'] for row in source['dressingLedger']]
furnishings.extend(row['surfaceAdaptation']['boundsCm'] for row in source['assets']
    if 'boundsCm' in row.get('surfaceAdaptation',{}))
population=checked_residents(plan,furnishings)
body_bindings={};resident_package_hashes={}
for profile in sorted({row['profile'] for row in population}):
    binding=installed(profile);mesh=unreal.load_asset(binding['meshes'][0]['path'])
    idle=unreal.load_asset(next(a['path'] for a in binding['animations'] if a['sourceClipName']=='idle'))
    if not isinstance(mesh,unreal.SkeletalMesh) or not isinstance(idle,unreal.AnimSequence):
        raise RuntimeError('Required resident body/animation missing: '+profile)
    body_bindings[profile]=(mesh,idle,binding)
    for asset in (mesh,idle,mesh.skeleton):
        package=asset.get_path_name().split('.')[0]
        resident_package_hashes[package]=sha(package_file(ROOT,package))
signature=digest(dict(sourceRevision=revision,date=date,population=population,
    residentPackageHashes=resident_package_hashes,
    helperSha256=sha(Path(__file__)),policySha256=sha(Path(__file__).with_name('citadel_review_world.py')),
    nativeInspectorSha256=sha(ROOT/'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarImportLibrary.cpp')))
packages=review_packages(signature[:12],date)
out=run/('human-review-'+signature[:12]);out.mkdir(exist_ok=True)
protected={**resident_package_hashes,**candidate['sourceHashes'],**candidate['packageHashes'],**staged['sourceHashes'],
    **staged['manifest']['packageHashes'],**staged['packageHashes']}
def observed():
    return {p:sha(protected_source_file(ROOT,p,h) if p.startswith('/Engine/') else package_file(ROOT,p)) for p,h in protected.items()}
if observed()!=protected:raise RuntimeError('Preserve changed campaign, scenery or service sources')
config=ROOT/'unreal/AegisWar/Config/DefaultEngine.ini';config_hash=sha(config)
assets=unreal.EditorAssetLibrary
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for package in packages.values():
    if assets.does_asset_exist(package):raise RuntimeError('Preserve existing or partial review package: '+package)

# Duplication keeps navigation data, all destination declarations and services.
for original,target in ((staged['map'],packages['map']),(staged['layer'],packages['routing'])):
    if not assets.duplicate_asset(original,target):raise RuntimeError('Cannot clone full campaign package')
load(packages['routing'])
original_states={a.get_name():snapshot(a) for a in own(packages['routing'])}
original_bindings=routing_bindings(own(packages['routing']))
anchors=[a for a in own(packages['routing']) if isinstance(a,unreal.WarZoneAnchor)]
matches=[a for a in anchors if str(a.get_editor_property('zone_id'))=='aegis_capital']
if len(matches)!=1:raise RuntimeError('Review routing has no unique Aegis anchor')
anchor=matches[0]
if sorted(str(a.get_editor_property('zone_id')) for a in anchors)!=sorted(staged['build']['zones']):
    raise RuntimeError('Review routing lost or duplicated campaign zone identities')
actual_city=anchor.get_editor_property('city_definition')
origin=actual_city.get_editor_property('origin') if actual_city else None
if (not isinstance(actual_city,unreal.WarCityDefinition)
        or actual_city.get_path_name().split('.')[0]!=candidate['city']['definition']
        or actual_city.get_editor_property('revision')!=candidate['city']['revision']
        or [origin.x,origin.y,origin.z]!=candidate['city']['origin']
        or [p.get_path_name().split('.')[0] for p in actual_city.get_editor_property('scenery_levels')]!=candidate['city']['sceneryLevels']):
    raise RuntimeError('Actual review Aegis anchor uses another city definition or revision')
portals=[a for a in own(packages['routing']) if isinstance(a,unreal.WarZonePortal)]
if sorted(str(a.get_editor_property('route_id')) for a in portals)!=sorted(staged['build']['portals']):
    raise RuntimeError('Review routing lost or duplicated a directed portal')
anchor.set_actor_location(unreal.Vector(*REVIEW_START_CM),False,True)
before_levels=list(map(str,anchor.get_editor_property('content_levels')))
anchor.set_editor_property('content_levels',[*before_levels,packages['population']])
after_bindings=routing_bindings(own(packages['routing']))
expected_bindings=copy.deepcopy(original_bindings)
next(row for row in expected_bindings if row.get('zone')=='aegis_capital')['levels'].append(packages['population'])
if after_bindings!=expected_bindings:raise RuntimeError('Unrelated route, destination or zone binding changed')
after_states={a.get_name():snapshot(a) for a in own(packages['routing'])}
if any(after_states[k]!=v for k,v in original_states.items() if k!=anchor.get_name()):
    raise RuntimeError('Unrelated routing actor state changed')
save(packages['routing'])

unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
if not unreal.EditorLoadingAndSavingUtils.save_map(world(),packages['population']):raise RuntimeError('Cannot create resident gameplay layer')
for actor in own(packages['population']):
    if not actors.destroy_actor(actor):raise RuntimeError('Cannot remove blank-map template from residents')
save(packages['population'])
load(packages['map'])
streams_before=list(unreal.WarImportLibrary.get_streaming_level_package_names(world()))
detach(staged['layer'])
if not unreal.EditorLevelUtils.add_level_to_world(world(),packages['routing'],unreal.LevelStreamingAlwaysLoaded):
    raise RuntimeError('Cannot attach isolated routing')
population_stream=unreal.EditorLevelUtils.add_level_to_world(world(),packages['population'],unreal.LevelStreamingDynamic)
if not population_stream:raise RuntimeError('Cannot attach resident gameplay')
population_stream.set_editor_property('initially_loaded',False)
population_stream.set_editor_property('initially_visible',False)
streams_after=list(unreal.WarImportLibrary.get_streaming_level_package_names(world()))
expected_streams=sorted([p for p in streams_before if p!=staged['layer']]+[packages['routing'],packages['population']])
if streams_after!=expected_streams:raise RuntimeError('Review world changed another streaming declaration')
loaded_anchors=[a for a in actors.get_all_level_actors() if isinstance(a,unreal.WarZoneAnchor)]
if sorted(str(a.get_editor_property('zone_id')) for a in loaded_anchors)!=sorted(staged['build']['zones']):
    raise RuntimeError('Loaded review layers contain ambiguous zone anchors')
for loaded in loaded_anchors:
    needed=list(map(str,loaded.get_editor_property('content_levels')))
    definition=loaded.get_editor_property('city_definition')
    if definition:needed.extend(p.get_path_name().split('.')[0] for p in definition.get_editor_property('scenery_levels'))
    if not set(needed)<=set(streams_after):raise RuntimeError('Review anchor lacks a required streaming declaration')
world().get_world_settings().set_editor_property('default_game_mode',unreal.WarGameMode)
save(packages['map'])
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).set_current_level_by_name(packages['population'].rsplit('/',1)[1]):
    raise RuntimeError('Cannot select isolated resident owner')
resident_level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).get_current_level()
if not resident_level or resident_level.get_path_name().split('.')[0]!=packages['population']:
    raise RuntimeError('Editor selected another resident owner before placement')

placed=[]
for row in population:
    profile=row['profile']
    x,y,z=row['pointCm']
    hit=unreal.SystemLibrary.line_trace_single(world(),unreal.Vector(x,y,z+300),unreal.Vector(x,y,z-50),
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,ignore_self=False)
    values=hit.to_tuple() if hit else None
    if not values or not values[0] or abs(values[5].z-z)>.5 or values[7].z<.7:
        raise RuntimeError('Resident lacks its actual signed walkable floor: '+row['id'])
    centre=unreal.Vector(x,y,z+row['heightCm']/2+2)
    clearance=unreal.SystemLibrary.capsule_trace_single(world(),centre,centre+unreal.Vector(.1,0,0),
        row['clearanceRadiusCm'],row['heightCm']/2,unreal.TraceTypeQuery.ECC_VISIBILITY,
        True,[],unreal.DrawDebugTrace.NONE,ignore_self=False)
    if clearance and clearance.to_tuple()[0]:raise RuntimeError('Resident intersects native architecture: '+row['id'])
    mesh,idle,binding=body_bindings[profile]
    actor=actors.spawn_actor_from_class(unreal.WarCityNpc,unreal.Vector(x,y,z),unreal.Rotator(yaw=row['yawDegrees']))
    if not actor or actor.get_outer().get_path_name().split('.')[0]!=packages['population']:
        raise RuntimeError('Resident belongs to an unintended level: '+(actor.get_path_name() if actor else 'spawn failed'))
    for key,value in dict(npc_id=row['id'],display_name=row['name'],city_role=row['role'],character_profile=profile).items():
        actor.set_editor_property(key,value)
    actor.set_actor_label(row['name']+' - Citadel resident')
    actor.tags=['WarCityPopulation','WarCitadelReviewResident','WarNpcId_'+row['id']]
    component=actor.skeletal_mesh_component;component.set_skeletal_mesh_asset(mesh)
    component.override_animation_data(idle,True,True,0,1);component.set_collision_profile_name('NoCollision')
    unreal.WarImportLibrary.prepare_preview_frame(component)
    origin,extent,_=unreal.SystemLibrary.get_component_bounds(component)
    if not 100<extent.z*2<row['heightCm'] or max(extent.x,extent.y)>row['clearanceRadiusCm']:
        raise RuntimeError('Resident pose exceeds its signed clearance: '+row['id'])
    actor.set_actor_location(unreal.Vector(x,y,z-(origin.z-extent.z-z)),False,True)
    placed.append(dict(**row,actor=actor.get_path_name(),mesh=mesh.get_path_name(),idle=idle.get_path_name(),
        feetZCm=z,sourceSha256=binding['sourceSha256'],floorActor=values[9].get_path_name(),
        nativeFloorAndCapsuleClear=True))
save(packages['population']);save(packages['map'])
if observed()!=protected or sha(config)!=config_hash:raise RuntimeError('Review staging changed protected sources or startup config')
receipt=dict(schemaVersion=1,signature=signature,sourceRevision=revision,**packages,
    mapSha256=sha(package_file(ROOT,packages['map'])),packageHashes={p:sha(package_file(ROOT,p)) for p in packages.values()},
    sourcePackageHashes=protected,sourcePackagesUnchanged=True,entryPointCm=REVIEW_START_CM,
    directedRoutes=len(portals),zones=len(anchors),routingBindings=after_bindings,streamingDeclarations=streams_after,
    residents=placed,city=candidate['city']['definition'],cityRevision=candidate['city']['revision'],
    launchSelectedMapArgument='-ini:Engine:[/Script/EngineSettings.GameMapsSettings]:GameDefaultMap='+packages['map'],
    requiresDevelopmentGM=True,ordinaryLocalDevelopmentEntry=True,servicesRetained=True,
    residentPopulationPrivateReviewOnly=True,visualApproved=False,gameplayApproved=False,published=False)
(out/'staged.json').write_text(json.dumps(receipt,indent=2)+'\n')
unreal.log('WAR_CITADEL_REVIEW_WORLD='+packages['map'])
