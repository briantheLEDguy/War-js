"""Install exact imported Sunmeadow raiders in its generated level; never replace owner edits."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from world_level_access import WorldLevelAccess
from world_build_assets import ground
from world_actor_state import snapshot

directory = ROOT/'artifacts/unreal/world-portals'
build = json.loads((directory/'build.json').read_text())
plan_file = directory/'plan.json'
if hashlib.sha256(plan_file.read_bytes()).hexdigest() != build['planSha256']:
    raise RuntimeError('World plan changed; reconcile before population')
plan = json.loads(plan_file.read_text())
zone = next(row for row in plan['zones'] if row['id']=='sunmeadow_march')
source = ROOT/'public/assets/maps/sunmeadow_march.json'
source_hash = plan['sourceHashes'][zone['id']]
if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
    raise RuntimeError('Source zone changed')
profile = 'enemy_aegis_campaign_raider_raider'
rows = [row for row in json.loads(source.read_text())['enemies'] if row.get('characterProfileKey')==profile]
if len(rows)!=3 or any(row['archetype']!='raider' or row.get('encounter') for row in rows):
    raise RuntimeError('Reviewed source encounter changed')
spec = importlib.util.spec_from_file_location('enemy_visuals',Path(__file__).with_name('prepare-proof.py'))
visuals = importlib.util.module_from_spec(spec); spec.loader.exec_module(visuals)
imported = visuals.imported(profile)
visuals.DESTINATION = build['layer'].rsplit('/',1)[0]+'/Characters'
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level.load_level(build['map']): raise RuntimeError('Main world unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
existing = {}
for actor in actors.get_all_level_actors():
    if isinstance(actor,unreal.WarEnemy):
        key = (str(actor.get_editor_property('zone_id')),str(actor.get_editor_property('enemy_id')))
        if key in existing: raise RuntimeError('Duplicate enemy identity: '+str(key))
        existing[key] = actor
record_file = directory/'enemy-placement.json'
previous = json.loads(record_file.read_text()) if record_file.exists() else None
access = WorldLevelAccess(ROOT,build)
package = access.package(zone['id'])
if hashlib.sha256(access.file(package).read_bytes()).hexdigest()!=access.manifest['packageHashes'][package]:
    raise RuntimeError('Owner changed Sunmeadow; reconcile before adding enemies')

def state(actor):
    result = snapshot(actor)
    result.update(zone=str(actor.get_editor_property('zone_id')),enemy=str(actor.get_editor_property('enemy_id')),
                  visual=actor.get_editor_property('visual').get_path_name())
    return result

if previous:
    if previous['sourceSha256']!=source_hash or previous['profile']!=profile:
        raise RuntimeError('Enemy placement source changed')
    for row in previous['actors']:
        actor = existing.get((zone['id'],row['id']))
        if actor is None or state(actor)!=row['state']: raise RuntimeError('Enemy actor changed; preserve owner edits: '+row['id'])
    if len(previous['actors'])!=len(rows): raise RuntimeError('Incomplete prior placement receipt')
    unreal.log('WAR_WORLD_ENEMIES_UNCHANGED=3')
else:
    if any((zone['id'],row['id']) in existing for row in rows): raise RuntimeError('Existing enemy lacks owned placement evidence')
    # All source, ownership and import checks precede asset or map mutation.
    access.select(zone['id'])
    visual = visuals.visual(profile,'empire','raider',unreal.WarRealm.AEGIS,'m')
    if not unreal.EditorAssetLibrary.save_loaded_asset(visual,False): raise RuntimeError('Visual save failed')
    placed = []
    for row in rows:
        point = unreal.Vector(zone['origin'][0]+row['z']*100,zone['origin'][1]+row['x']*100,zone['origin'][2])
        floor = ground(world,point,5000)
        actor = actors.spawn_actor_from_class(unreal.WarEnemy,floor+unreal.Vector(0,0,98))
        actor.set_editor_property('zone_id',zone['id'])
        actor.set_editor_property('enemy_id',row['id'])
        actor.set_editor_property('visual',visual)
        actor.set_actor_label('Campaign Raider - '+row['id'])
        actor.tags = ['WarCampaignWorld','WarCampaignEnemy','WarZoneObject_'+zone['id']+'_Enemy_'+row['id']]
        mesh = actor.get_editor_property('mesh')
        mesh.set_skeletal_mesh_asset(visual.skeletal_mesh)
        mesh.set_relative_transform(visual.mesh_transform,False,True)
        mesh.override_animation_data(visual.idle_animation,True,True,0,1)
        unreal.WarImportLibrary.prepare_preview_frame(mesh)
        center,extent,_ = unreal.SystemLibrary.get_component_bounds(mesh)
        if not 100<extent.z*2<240 or abs(center.z-extent.z-floor.z)>10:
            raise RuntimeError('Source raider is not grounded or correctly scaled')
        placed.append({'id':row['id'],'state':state(actor)})
    access.save({zone['id']})
    for row in rows:
        build['gameplay'].append({'id':row['id'],'zone':zone['id'],'kind':'enemy','profile':profile,
            'behavior':'server-melee-raider','acceptance':'pending-live-proof-and-source-special'})
    build['runtimeTraversalVerified'] = False
    (directory/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    record_file.write_text(json.dumps({'schemaVersion':1,'profile':profile,'sourceSha256':source_hash,
        'sourceModelSha256':imported['sourceSha256'],'package':package,'actors':placed,
        'visualApproved':False,'behaviorAccepted':False},indent=2)+'\n')
    unreal.log('WAR_WORLD_ENEMIES_ADDED=3')
