"""Ground staged assignments; apply only after exact native review and ownership checks.

Default is a non-saving placement survey. Set WAR_POPULATION_APPLY=1 to publish
reviewed assets and update only the owned population and generated zone levels.
"""
import json
import math
import os
import shutil
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from imported_population import ROOT, OUT, LEDGER, BASE, digest, ledger, models, require_review, verify_sources, check_zone_ownership
from capital_population import official_map, POPULATION_MAP, planned_records, records
from world_level_access import WorldLevelAccess
from world_actor_state import snapshot
from capital_geography import height

def actor_state(actor):
    state = snapshot(actor)
    state['folder'] = str(actor.get_folder_path())
    if isinstance(actor,unreal.WarCityNpc):
        state['identity'] = {key:str(actor.get_editor_property(key)) for key in ('npc_id','display_name','city_role','character_profile')}
        animation = actor.get_component_by_class(unreal.SkeletalMeshComponent).get_editor_property('animation_data')
        state['animation'] = dict(asset=animation.anim_to_play.get_path_name() if animation.anim_to_play else None,
            looping=animation.saved_looping,playing=animation.saved_playing)
    elif isinstance(actor,unreal.WarEnemy):
        state['identity'] = {key:str(actor.get_editor_property(key)) for key in ('enemy_id','zone_id')}
        visual = actor.get_editor_property('visual')
        state['visual'] = visual.get_path_name() if visual else None
    return state

def main():
    apply = os.environ.get('WAR_POPULATION_APPLY') == '1'
    verify_sources()
    data = ledger(); sources = models()
    installed = json.loads((OUT/'installed.json').read_text())
    sets = json.loads((OUT/'presentations.json').read_text())['profiles']
    technical = json.loads((OUT/'technical-verification.json').read_text())
    if installed['ledgerSha256'] != digest(LEDGER): raise RuntimeError('Installed assignments are stale')
    if not technical['structuralChecksPassed']: raise RuntimeError('Native structural checks failed')
    if apply: require_review(json.loads((OUT/'development-review.json').read_text()),digest(OUT/'technical-verification.json'))
    if apply and json.loads((OUT/'development-review.json').read_text()).get('reviewSha256') != digest(OUT/'review.json'):
        raise RuntimeError('Native image review is stale')
    for asset,expected in technical['packages'].items():
        file = ROOT/'unreal/AegisWar/Content'/(asset.split('.')[0].removeprefix('/Game/')+'.uasset')
        if digest(file) != expected: raise RuntimeError('Reviewed package changed: '+asset)
    directory = ROOT/'artifacts/unreal/world-portals'
    build = json.loads((directory/'build.json').read_text())
    access = WorldLevelAccess(ROOT,build)
    target_zones = {r['zone'] for r in data['capitalAdditions'] if r['zone']!='aegis_capital'} | {c['zone'] for c in data['camps']}
    zone_baselines = {access.package(z):digest(access.file(access.package(z))) for z in target_zones}
    reconciled = {p:dict(previous=access.manifest['packageHashes'][p],current=h)
        for p,h in zone_baselines.items() if access.manifest['packageHashes'][p]!=h}
    origins = {z['id']:z['origin'] for z in access.manifest['zones']}
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not levels.load_level(official_map()): raise RuntimeError('Official city is unavailable')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = actors.get_all_level_actors()
    existing = {}
    for actor in all_actors:
        if isinstance(actor,unreal.WarCityNpc):
            identity = str(actor.get_editor_property('npc_id'))
            if identity in existing: raise RuntimeError('Duplicate NPC identity: '+identity)
            existing[identity] = actor
        elif isinstance(actor,unreal.WarEnemy):
            identity = str(actor.get_editor_property('enemy_id'))
            if identity in existing: raise RuntimeError('Duplicate enemy identity: '+identity)
            existing[identity] = actor
    replacement_ids = {r['id'] for r in data['capitalReplacements']}
    rows = [r for r in planned_records() if r['id'] in replacement_ids or 'model' in r]
    rows += [{**r,'profile':sources[r['model']]['profile'],'district':c['id']} for c in data['camps'] for r in c['members']]
    prior_path = OUT/'placement.json'
    prior = json.loads(prior_path.read_text()) if prior_path.exists() else None
    if prior:
        if prior['ledgerSha256'] != digest(LEDGER): raise RuntimeError('Reconcile prior placement before changing assignments')
        for row in prior['actors']:
            if row['id'] not in existing or actor_state(existing[row['id']]) != row['state']:
                raise RuntimeError('Owner changed a placed inhabitant: '+row['id'])
        for package, expected in prior['packages'].items():
            if digest(ROOT/package) != expected: raise RuntimeError('Placed package changed: '+package)
        unreal.log('WAR_IMPORTED_POPULATION_UNCHANGED='+str(len(prior['actors'])))
        return
    if any(r['id'] in existing for r in rows if r['id'] not in replacement_ids):
        raise RuntimeError('An imported identity already exists without an ownership receipt')
    if replacement_ids - existing.keys(): raise RuntimeError('A named capital replacement is missing')

    def package_file(package):
        return ROOT/'unreal/AegisWar/Content'/(package.split('.')[0].removeprefix('/Game/')+'.umap')

    population_file = package_file(POPULATION_MAP)
    population_receipt = ROOT/'artifacts/unreal/population/population-build.json'
    population_baseline = digest(population_file)
    original_profiles = {r['id']:r['profile'] for r in records()}
    for identity in replacement_ids:
        if str(existing[identity].get_editor_property('character_profile')) != original_profiles[identity]:
            raise RuntimeError('Owner changed the appearance of '+identity+'; preserve it before reconciliation')
    main_hash = digest(package_file(official_map()))
    untouched = {a.get_path_name():actor_state(a) for a in all_actors if a not in [existing[i] for i in replacement_ids]}
    candidate, blocked = [], []
    def standing_point(point):
        hit = unreal.SystemLibrary.line_trace_single(world,point+unreal.Vector(0,0,300),point-unreal.Vector(0,0,600),
            unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE)
        if not hit or hit.to_tuple()[7].z < .65: return None
        floor = hit.to_tuple()[5]
        if abs(floor.z-point.z)>250: return None
        center = floor+unreal.Vector(0,0,100)
        if unreal.SystemLibrary.capsule_trace_single(world,center,center+unreal.Vector(0,0,1),42,90,
                unreal.TraceTypeQuery.ECC_VISIBILITY,False,[],unreal.DrawDebugTrace.NONE): return None
        if any(math.hypot(r['position'][0]-floor.x,r['position'][1]-floor.y)<150 for r in candidate): return None
        return floor
    for row in rows:
        profile = row['profile']; entry = sets[profile]
        if row['id'] in replacement_ids:
            actor = existing[row['id']]
            position = actor.get_actor_location()
            # Preserve owner-adjusted identity, role and placement; only its reviewed appearance changes.
            row = {**row,'name':str(actor.get_editor_property('display_name')),
                'role':str(actor.get_editor_property('city_role')),'yaw':actor.get_actor_rotation().yaw+90}
            hit = unreal.SystemLibrary.line_trace_single(world,position+unreal.Vector(0,0,100),position-unreal.Vector(0,0,250),
                unreal.TraceTypeQuery.ECC_VISIBILITY,True,[actor],unreal.DrawDebugTrace.NONE)
            if not hit or hit.to_tuple()[7].z < .65:
                blocked.append(dict(id=row['id'],reason='Existing actor has no walkable ground')); continue
            ground_z = hit.to_tuple()[5].z
        else:
            origin = [0,0,0] if row['zone']=='aegis_capital' else origins[row['zone']]
            if row['id']=='riftspire_import_shrine_attendant':
                source = json.loads((ROOT/'public/assets/maps/riftspire_capital.json').read_text())
                shrine = next(r['entry'] for r in source['craterCity']['interiors'] if r['id']=='shrine')
                row = {**row,**shrine,'x':shrine['x']+2}
            floor = row.get('y',42.1 if row['district']=='crownwatch' else height(row['x'],row['z']) if row['zone']=='aegis_capital' else 0)*100+origin[2]
            position = unreal.Vector(origin[0]+row['z']*100,origin[1]+row['x']*100,floor)
            hit = unreal.SystemLibrary.line_trace_single(world,position+unreal.Vector(0,0,400),position-unreal.Vector(0,0,600),
                unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE)
            if not hit or hit.to_tuple()[7].z < .65:
                blocked.append(dict(id=row['id'],reason='No walkable ground at the assigned location')); continue
            ground_z = hit.to_tuple()[5].z
        clearance_center = unreal.Vector(position.x,position.y,ground_z+100)
        obstruction = unreal.SystemLibrary.capsule_trace_single(world,clearance_center,clearance_center+unreal.Vector(0,0,1),42,90,
            unreal.TraceTypeQuery.ECC_VISIBILITY,False,[],unreal.DrawDebugTrace.NONE)
        if obstruction:
            adjusted = None
            if row['id'] not in replacement_ids and row['zone'] in ('aegis_capital','riftspire_capital'):
                for radius in (200,400,600,800):
                    for angle in range(0,360,45):
                        point = position+unreal.Vector(math.cos(math.radians(angle))*radius,math.sin(math.radians(angle))*radius,0)
                        adjusted = standing_point(point)
                        if adjusted: break
                    if adjusted: break
            if adjusted: position=adjusted; ground_z=adjusted.z
            else:
                blocked.append(dict(id=row['id'],reason='Standing capsule overlaps blocking architecture')); continue
        # Measure the exact equipped idle body instead of assuming all FBXs have the same foot origin.
        probe = actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector())
        component = probe.skeletal_mesh_component
        component.set_skeletal_mesh_asset(unreal.load_asset(entry['mesh']))
        idle = entry['bindings']['idle' if row['role'] in ('guard','marshal','enemy') else 'civilian_idle']
        component.override_animation_data(unreal.load_asset(idle),True,True,0,1)
        unreal.WarImportLibrary.prepare_preview_frame(component)
        center,extent,_ = unreal.SystemLibrary.get_component_bounds(component)
        actors.destroy_actor(probe)
        if not 100 < extent.z*2 < 280:
            blocked.append(dict(id=row['id'],reason='Unexpected native height',height=extent.z*2)); continue
        foot = center.z-extent.z
        position.z = ground_z-foot+(96 if row['role']=='enemy' else 0)
        # Physics triangle intersections vary by sub-micron rounding between loads.
        candidate.append({**row,'position':[round(v,2) for v in (position.x,position.y,position.z)],
            'groundZ':round(ground_z,2),'idle':idle,'footOffset':round(foot,6)})
    navigation = []
    for camp in data['camps']:
        members = [r for r in candidate if r['id'] in {m['id'] for m in camp['members']}]
        if len(members)!=len(camp['members']): continue
        # Verify the short walking links between camp members with the actual runtime capsule.
        for row in members[1:]:
            first=members[0]; start=unreal.Vector(first['position'][0],first['position'][1],first['groundZ']+100)
            end=unreal.Vector(row['position'][0],row['position'][1],row['groundZ']+100)
            obstacle=unreal.SystemLibrary.capsule_trace_single(world,start,end,42,90,
                unreal.TraceTypeQuery.ECC_VISIBILITY,False,[],unreal.DrawDebugTrace.NONE)
            navigation.append(dict(camp=camp['id'],start=first['id'],end=row['id'],clear=not bool(obstacle)))
            if obstacle: blocked.append(dict(id=row['id'],reason='Camp walking link intersects blocking geometry'))
    (OUT/'placement-survey.json').write_text(json.dumps(dict(ledgerSha256=digest(LEDGER),actors=candidate,blocked=blocked,
        populationBaselineSha256=population_baseline,mainBaselineSha256=main_hash,zoneBaselineSha256=zone_baselines,
        preservedOwnerState=untouched,walkingLinks=navigation,saved=False,localNavigationVerified=bool(navigation) and all(r['clear'] for r in navigation)),indent=2,sort_keys=True)+'\n')
    if not apply: return
    if blocked: raise RuntimeError('Placement survey has blocked inhabitants; no world changes were saved')
    reconciled = check_zone_ownership(access.manifest['packageHashes'],zone_baselines,
        {p:digest(access.file(p)) for p in zone_baselines},os.environ.get('WAR_POPULATION_RECONCILE_OWNER') == '1')
    review = json.loads((OUT/'development-review.json').read_text())
    if review.get('placementSurveySha256') != digest(OUT/'placement-survey.json') or review.get('navigation') is not True:
        raise RuntimeError('Exact placement and navigation review is required before saving')

    # Every target and package is checked before the first live mutation.
    zones = {r['zone'] for r in rows if r['zone']!='aegis_capital'}
    for zone in zones:
        package = access.package(zone)
        if digest(access.file(package)) != zone_baselines[package]:
            raise RuntimeError('Owner changed zone during placement: '+zone)
        # Reconcile a historical receipt against the reviewed current actor inventory.
        # No actor is regenerated; all retained state is compared before saving.
        access.manifest['packageHashes'][package] = zone_baselines[package]
    shutil.copy2(population_file,OUT/'population-before.umap')
    equipment = unreal.load_asset('/Game/WorldRebuild/NpcEquipment/CombatLoadouts')
    staged = unreal.load_asset(installed['catalog'])
    old_bindings = list(equipment.get_editor_property('loadouts'))
    new_profiles = {r['profile'] for r in sources.values()}
    if any(str(b.get_editor_property('profile')) in new_profiles for b in old_bindings):
        raise RuntimeError('Unowned imported loadouts already exist')
    registry_file = ROOT/'unreal/AegisWar/Content/Migration/visual-imports.json'
    registry = json.loads(registry_file.read_text())
    if any(r['profileKey'] in new_profiles for r in registry['entries']):
        raise RuntimeError('Imported profiles already have unowned active bindings')
    exported_file = ROOT/'artifacts/unreal/content.json'
    exported = json.loads(exported_file.read_text(encoding='utf-8'))
    revisions = json.loads((ROOT/'migration/content-revisions.json').read_text())
    if exported['source']['contentSha256'] != revisions['currentContentSha256']:
        raise RuntimeError('Export the current camp catalog before placement')
    for camp in data['camps']:
        definition = next(r['definition'] for r in exported['maps'] if r['id']==camp['zone'])
        actual = {r['id']:r for r in definition['enemies' if camp['allegiance']=='hostile' else 'npcs']}
        if any(r['id'] not in actual or actual[r['id']]['characterProfileKey'] != sources[r['model']]['profile'] for r in camp['members']):
            raise RuntimeError('Native catalog lacks the exact camp identities')
    equipment_package = ROOT/'unreal/AegisWar/Content/WorldRebuild/NpcEquipment/CombatLoadouts.uasset'
    shutil.copy2(equipment_package,OUT/'equipment-before.uasset')
    changed_files = [population_file,equipment_package,registry_file,population_receipt,
        ROOT/'unreal/AegisWar/Content/Migration/content.json',directory/'build.json',directory/build['partitionManifest'],
        *[access.file(access.package(zone)) for zone in zones]]
    backups = OUT/'before-placement'; backups.mkdir(exist_ok=True)
    for index,file in enumerate(changed_files): shutil.copy2(file,backups/str(index))
    try:
        equipment.set_editor_property('loadouts',old_bindings+list(staged.get_editor_property('loadouts')))
        if not unreal.EditorAssetLibrary.save_loaded_asset(equipment,False): raise RuntimeError('Equipment publication failed')
        placed = []
        for row in candidate:
            if row['zone']=='aegis_capital':
                if not levels.set_current_level_by_name(POPULATION_MAP.rsplit('/',1)[1]): raise RuntimeError('Population layer unavailable')
            else: access.select(row['zone'])
            actor = existing.get(row['id'])
            if actor is None:
                actor = actors.spawn_actor_from_class(unreal.WarEnemy if row['role']=='enemy' else unreal.WarCityNpc,unreal.Vector(*row['position']))
            actor.set_actor_location_and_rotation(unreal.Vector(*row['position']),unreal.Rotator(yaw=row['yaw']+(0 if row['role']=='enemy' else 180)),False,True)
            visual = unreal.load_asset(installed['profiles'][row['profile']]['visual'])
            if row['role']=='enemy':
                actor.set_editor_properties(dict(zone_id=row['zone'],enemy_id=row['id'],visual=visual))
            else:
                actor.set_editor_properties(dict(npc_id=row['id'],display_name=row['name'],city_role=row['role'],character_profile=row['profile']))
            component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
            component.set_skeletal_mesh_asset(visual.skeletal_mesh)
            if row['role']=='enemy': component.set_relative_transform(visual.mesh_transform,False,True)
            component.override_animation_data(unreal.load_asset(row['idle']),True,True,0,1)
            component.set_collision_profile_name('NoCollision')
            error = unreal.WarNpcEquipmentLibrary.apply(component,row['profile'],row['id'],row['role'])
            if error != '': raise RuntimeError('Equipment rejected '+row['id']+': '+str(error))
            if row['id'] not in replacement_ids:
                actor.set_actor_label(row['name']+' - '+row['role'])
                actor.set_folder_path('ImportedPopulation/'+row['zone']+'/'+row['district'])
            actor.tags = list(actor.tags)+['WarImportedPopulation']
            placed.append(dict(id=row['id'],zone=row['zone'],state=actor_state(actor)))
        for actor in actors.get_all_level_actors():
            if actor.get_path_name() in untouched and actor_state(actor)!=untouched[actor.get_path_name()]:
                raise RuntimeError('Unrelated actor changed: '+actor.get_path_name())
        if digest(package_file(official_map())) != main_hash: raise RuntimeError('Persistent city changed concurrently')
        if not levels.set_current_level_by_name(POPULATION_MAP.rsplit('/',1)[1]) or not levels.save_current_level():
            raise RuntimeError('Population save failed')
        access.save(zones)
        for row in sources.values():
            entry = sets[row['profile']]
            registry['entries'].append(dict(profileKey=row['profile'],sourceModel=row['source'],sourceSha256=row['sha256'],
                skeletalMeshPath=entry['mesh'],animationPaths=sorted(set(entry['bindings'].values())),artApproval=False,developmentOnly=True))
        registry_file.write_text(json.dumps(registry,indent=2)+'\n')
        shutil.copy2(exported_file,ROOT/'unreal/AegisWar/Content/Migration/content.json')
        population = json.loads(population_receipt.read_text())
        by_id = {r['id']:r for r in population['actors']}
        for row in candidate:
            if row['zone']=='aegis_capital':
                by_id[row['id']] = {**row,'mesh':sets[row['profile']]['mesh'],'feetZ':row['groundZ']}
        population.update(actors=list(by_id.values()),newActors=len(by_id),sha256=digest(population_file),
            visualVerified=True,servicesRuntimeVerified=False,importedPopulationLedgerSha256=digest(LEDGER))
        population_receipt.write_text(json.dumps(population,indent=2)+'\n')
        build['runtimeTraversalVerified'] = False
        directory.joinpath('build.json').write_text(json.dumps(build,indent=2)+'\n')
        prior_path.write_text(json.dumps(dict(ledgerSha256=digest(LEDGER),actors=placed,
            packages={file.relative_to(ROOT).as_posix():digest(file) for file in changed_files},
            populationSha256=digest(population_file),reconciledOwnerPackages=reconciled,
            mainUnchanged=True,gameplayVerified=False),indent=2)+'\n')
    except Exception:
        # Commandlet exits without saving its in-memory world; restore every on-disk participant.
        for index,file in enumerate(changed_files): shutil.copy2(backups/str(index),file)
        raise



if __name__ == "__main__": main()
