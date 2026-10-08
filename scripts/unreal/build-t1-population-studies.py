"""Place exact retained NPC/resource actors in fresh, isolated ceiling candidates."""
import copy
import datetime
import hashlib
import json
import math
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from t1_population import population_plan, nearest_route_points, ZONES
from t1_population_native import population_actor, spawn_population, GroundReview
from t1_materials import protected_saved, verify_protected, sha, same_state
from t1_material_clone import inventory, clone

DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
CONTENT = ROOT/'unreal/AegisWar/Content'
read = lambda p: json.loads((ROOT/p).read_text(encoding='utf-8'))
package_file = lambda p: CONTENT/(p.split('.')[0].removeprefix('/Game/')+'.umap')
asset_file = lambda p: CONTENT/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
parent = read('artifacts/unreal/t1-redesign/ceilings-latest.json')
review = read('artifacts/unreal/t1-redesign/ceiling-review.json')
homes = read('artifacts/unreal/t1-redesign/ceiling-home-review.json')
if (parent.get('study') != 'timber-ceilings' or parent['activeCampaignChanged'] or review['signature'] != parent['signature']
    or not review['overheadClosed'] or homes['signature'] != parent['signature'] or not homes['capsuleClear']
    or tuple(z['id'] for z in parent['zones']) != ZONES):
    raise RuntimeError('Population requires the verified first-pair ceiling parent')
for package, digest in {**parent['inputs']['parentPackages'], **parent['packageHashes']}.items():
    if sha(package_file(package)) != digest: raise RuntimeError('Preserve edited parent map')
for file, digest in {**parent['inputs']['sourceHashes'], **parent['inputs']['tools'], **parent['inputs']['parentAssetHashes'], **parent['assetHashes']}.items():
    if sha(ROOT/file) != digest: raise RuntimeError('Parent input, binary or asset changed')
verify_protected(ROOT, parent['inputs']['protectedHashes'])
protected = protected_saved(ROOT)
canonical = {z['definition']['id']: z['definition'] for z in read('unreal/AegisWar/Content/Migration/content.json')['maps']}
imports = read('unreal/AegisWar/Content/Migration/visual-imports.json')
world_catalog = read('unreal/AegisWar/Content/Migration/world-visuals.json')
registry = read('public/assets/models/asset-index.json')['staticProps']
source_catalog = read('migration/world-resource-sources.json')
manifest = read('artifacts/unreal/world-portals/zone-manifest.json')
equipment = read('artifacts/unreal/npc-equipment/import.json')
if sha(asset_file(equipment['catalog'])) != equipment['catalogSha256']: raise RuntimeError('Retained equipment catalog changed')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
plans = {}; source_packages = {}; source_mismatches = []; dependencies = dict(parent['inputs']['dependencyHashes'])
for zone in parent['zones']:
    identity = zone['id']; entry = next(z for z in manifest['zones'] if z['id'] == identity)
    package = entry['levels']['generated']
    if not package.startswith('/Game/WorldRebuild/Zones_') or not package.endswith('/'+identity+'_Generated'):
        raise RuntimeError('Source population is outside its canonical generated layer')
    source_packages[package] = sha(package_file(package))
    recorded = manifest['packageHashes'][package]
    if recorded != source_packages[package]: source_mismatches.append(dict(package=package, recorded=recorded, installed=source_packages[package]))
    if not levels.load_level(package): raise RuntimeError('Retained generated population unavailable')
    survey = dict(zone=identity, actors=[population_actor(a) for a in actors.get_all_level_actors() if isinstance(a, (unreal.WarCityNpc, unreal.WarResourceNode))])
    source = read('artifacts/unreal/t1-redesign/'+identity+'.json')
    plans[identity] = population_plan(source, canonical[identity], survey, world_catalog, imports, registry, source_catalog)
    if len([r for r in plans[identity]['ready'] if r['kind'] == 'npc']) != (4 if identity == ZONES[0] else 2):
        raise RuntimeError('Ready first-pair NPC inventory changed; review the new source explicitly')
    if len([r for r in plans[identity]['ready'] if r['kind'] == 'resource']) != (2 if identity == ZONES[0] else 4):
        raise RuntimeError('Ready first-pair resource inventory changed; review the new source explicitly')
native_registry = unreal.AssetRegistryHelpers.get_asset_registry()
options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True,
    include_searchable_names=False, include_soft_management_references=False, include_hard_management_references=False)
pending = [equipment['catalog'].split('.')[0]]
for plan in plans.values():
    for row in plan['ready']:
        s = row['source']; pending.extend(p.split('.')[0] for p in [s['mesh'], *s['materials']])
        if row['kind'] == 'npc': pending.append(s['animation']['asset'].split('.')[0])
        for weapon in s.get('weapons', []): pending.extend(p.split('.')[0] for p in [weapon['mesh'], *weapon['materials']])
while pending:
    package = pending.pop()
    if package in dependencies: continue
    if not package.startswith('/Game/') or '..' in package or len(dependencies) > 4096:
        raise RuntimeError('Population dependency inventory is invalid or unbounded')
    dependencies[package] = sha(asset_file(package))
    pending.extend(str(p) for p in native_registry.get_dependencies(package, options) if str(p).startswith('/Game/'))
for package, digest in dependencies.items():
    if sha(asset_file(package)) != digest: raise RuntimeError('Frozen native source changed')
source_files = ['unreal/AegisWar/Content/Migration/content.json', 'unreal/AegisWar/Content/Migration/visual-imports.json',
    'unreal/AegisWar/Content/Migration/world-visuals.json', 'migration/world-resource-sources.json',
    'public/assets/models/asset-index.json', 'artifacts/unreal/world-portals/zone-manifest.json', 'artifacts/unreal/npc-equipment/import.json']
for plan in plans.values():
    for row in plan['ready']:
        file = row['visual']['sourceModel'] if row['kind'] == 'npc' else 'public/assets/models/'+row['model']
        digest = row['visual']['sourceSha256'] if row['kind'] == 'npc' else row['sourceSha256']
        if sha(ROOT/file) != digest: raise RuntimeError('Population source model differs from its exact import')
        source_files.append(file)
tools = ['scripts/unreal/build-t1-population-studies.py', 'scripts/unreal/t1_population.py', 'scripts/unreal/t1_population_native.py',
    'scripts/unreal/world_resources.py', 'scripts/unreal/t1_material_clone.py', 'scripts/unreal/t1_materials.py',
    'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll']
inputs = dict(parentCeilingSignature=parent['signature'], parentPlanSha256=parent['inputs']['parentPlanSha256'],
    parentPackages={**parent['inputs']['parentPackages'], **parent['packageHashes'], **source_packages},
    parentAssetHashes={**parent['inputs']['parentAssetHashes'], **parent['assetHashes']}, dependencyHashes=dependencies,
    sourceHashes={**parent['inputs']['sourceHashes'], **{f: sha(ROOT/f) for f in source_files}}, tools={f: sha(ROOT/f) for f in tools},
    protectedHashes=protected, populationPlans=plans, preservedSourceManifestMismatches=source_mismatches)
signature = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
folder = '/Game/WorldRebuild/T1Redesign_Atmosphere_'+signature[:12]+'_'+datetime.datetime.now().strftime('%H%M%S_%f')
zones = []; packages = []
try:
    for zone in parent['zones']:
        identity = zone['id']; source = read('artifacts/unreal/t1-redesign/'+identity+'.json')
        if not levels.load_level(zone['map']): raise RuntimeError('Population parent unavailable')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        states = inventory(actors)
        if not same_state(states, zone['actorInventory']): raise RuntimeError('Parent population surroundings changed')
        destination = folder+'/'+identity
        if not levels.new_level(destination+'/Review'): raise RuntimeError('Cannot create isolated population review')
        anchor = actors.spawn_actor_from_class(unreal.WarZoneAnchor, unreal.Vector())
        anchor.set_editor_property('zone_id', identity); anchor.set_editor_property('zone_origin', unreal.Vector())
        anchor.set_editor_property('use_spatial_bounds', True); b = source['spatial']['bounds']
        anchor.set_editor_property('content_min', unreal.Vector2D(b['minZ']*100, b['minX']*100))
        anchor.set_editor_property('content_max', unreal.Vector2D(b['maxZ']*100, b['maxX']*100))
        anchor.set_editor_property('playable_outline', [unreal.Vector2D(p['z']*100, p['x']*100) for p in source['spatial']['playableOutline']])
        generated = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, destination+'/Generated', False)
        if not generated: raise RuntimeError('Cannot create isolated population layer')
        unreal.EditorLevelUtils.make_level_current(generated); clone(actors, states, {})
        recipe = zone['atmosphere']; effect = actors.spawn_actor_from_class(unreal.WarRegionalAtmosphere, unreal.Vector())
        effect.set_actor_label(identity+'_regional_atmosphere'); effect.set_editor_property('zone_id', identity)
        effect.set_editor_property('village_centre', unreal.Vector(*recipe['villageCentre']))
        for name, key in [('military_centres','militaryCentres'), ('steam_sites','steamSites')]: effect.set_editor_property(name, [unreal.Vector(*p) for p in recipe[key]])
        effect.set_editor_property('weather_material', unreal.load_asset(recipe['material'])); effect.set_editor_property('audio_gain', recipe['audioGain'])
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        ground = GroundReview(world, actors, identity, source['spatial']['playableOutline']); installed = []; access_pending=[]
        for original in plans[identity]['ready']:
            row = copy.deepcopy(original); ideal = row['point']; chosen = None
            ground.failures=[]
            offsets = [(0,0)]+[(math.cos(a*math.pi/4)*r, math.sin(a*math.pi/4)*r) for r in (200,400,800,1200) for a in range(8)]
            for dx, dy in offsets:
                position = ground.ground([ideal[0]+dx, ideal[1]+dy, ideal[2]])
                if position is None or ground.center(position) is None: continue
                for projection in nearest_route_points(position, source['paths'])[:8]:
                    approach = ground.approach(projection['point'], position)
                    if approach:
                        chosen = dict(position=position, approach=approach, road=projection['road'], adjustmentCm=math.hypot(dx,dy)); break
                if chosen: break
            if not chosen:
                failure=dict(kind=row['kind'],id=row['id'],reason='native-terrain-capsule-access-pending',ideal=ideal,
                    witnesses=copy.deepcopy(ground.failures),retainedBindingUnchanged=True)
                access_pending.append(failure)
                unreal.log('WAR_T1_POPULATION_ACCESS_PENDING='+row['id']); continue
            row['point'] = chosen['position']; actor = spawn_population(actors, row)
            component = actor.get_component_by_class(unreal.SkeletalMeshComponent) if row['kind'] == 'npc' else actor.static_mesh_component
            centre, extent, _ = unreal.SystemLibrary.get_component_bounds(component)
            location = actor.get_actor_location(); location.z += chosen['position'][2]+2-(centre.z-extent.z)
            actor.set_actor_location(location, False, True)
            actual = population_actor(actor)
            for field in ('identity', 'mesh', 'materials', 'collision', 'scale', 'visible'):
                if not same_state(actual[field], row['source'][field]): raise RuntimeError('Population changed retained '+field)
            if row['kind'] == 'npc' and (not same_state(actual['animation'], row['source']['animation']) or not same_state(actual['weapons'], row['source']['weapons'])):
                raise RuntimeError('Population changed retained animation or equipment')
            row.update(savedState=actual, ground=chosen['position'], approach=chosen['approach'], connectedRoad=chosen['road'], adjustmentCm=chosen['adjustmentCm'],
                nativePositionOverride=dict(x=actual['location'][1]/100, y=actual['location'][2]/100, z=actual['location'][0]/100),
                sourceRulesUnchanged=True, gameplayAccepted=False)
            installed.append(row); unreal.log('WAR_T1_POPULATION_PLACED='+row['id'])
        actual = inventory(actors); retained = {k:v for k,v in actual.items() if k not in {r['id'] for r in installed}}
        if not same_state(retained, states): raise RuntimeError('Population altered parent terrain, houses or lights')
        if not levels.save_current_level(): raise RuntimeError('Cannot save private population generated layer')
        authored = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, destination+'/Authored', False)
        if not authored: raise RuntimeError('Cannot reserve empty population owner layer')
        unreal.EditorLevelUtils.make_level_current(authored)
        if not levels.save_current_level(): raise RuntimeError('Cannot save empty population owner layer')
        levels.set_current_level_by_name('Review'); anchor.set_editor_property('content_levels', [destination+'/Generated', destination+'/Authored'])
        if not levels.save_current_level(): raise RuntimeError('Cannot save private population review')
        packages.extend(destination+'/'+n for n in ('Review','Generated','Authored'))
        zones.append({**zone, 'map':destination+'/Review', 'parentMap':zone['map'], 'actorInventory':actual,
            'population':installed, 'pendingPopulation':plans[identity]['pending']+access_pending, 'approachCapsuleChecks':ground.samples})
finally:
    verify_protected(ROOT, protected)
    for package, digest in dependencies.items():
        if sha(asset_file(package)) != digest: raise RuntimeError('Population authoring changed native source dependencies')
result = dict(signature=signature, kind='atmosphere', study='retained-population', inputs=inputs, zones=zones,
    packageHashes={p:sha(package_file(p)) for p in packages}, assetHashes={}, parentCandidatesUnchanged=True, activeCampaignChanged=False,
    sourceCatalogsUnchanged=True, nodeGeometrySynchronized=False, nativeResourceTransactionsVerified=False, npcServicesVerified=False,
    visualApproved=False, walkDriveAccepted=False, gameplayAccepted=False, licensedDistributionApproved=False)
target = DIRECTORY/('population-'+signature[:12]+'.json')
if target.exists(): raise RuntimeError('Preserve an existing population receipt')
target.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8'); (DIRECTORY/'population-latest.json').write_text(target.read_text(encoding='utf-8'), encoding='utf-8')
unreal.log('WAR_T1_POPULATION_BUILT='+signature[:12])
