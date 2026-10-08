"""Opt-in native atmosphere in fresh first-batch copies; frozen scenery is exact."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from t1_atmosphere import atmosphere_recipe
from t1_atmosphere_assets import weather_material
from t1_materials import protected_saved, verify_protected, sha, same_state
from t1_material_clone import inventory, clone
from world_build_assets import WorldAssets
DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
CONTENT = ROOT/'unreal/AegisWar/Content'
package_file = lambda package: CONTENT/(package.removeprefix('/Game/')+'.umap')
parent = json.loads((DIRECTORY/'materials-latest.json').read_text())
plan = json.loads((DIRECTORY/'plan.json').read_text())
if sha(DIRECTORY/'plan.json') != parent['inputs']['parentPlanSha256']: raise RuntimeError('Atmosphere requires frozen plan')
for package, digest in {**parent['inputs']['parentPackages'], **parent['packageHashes']}.items():
    if sha(package_file(package)) != digest: raise RuntimeError('Preserve changed parent maps')
for package, digest in parent['inputs']['dependencyHashes'].items():
    if sha(CONTENT/(package.removeprefix('/Game/')+'.uasset')) != digest: raise RuntimeError('Preserve changed private kit')
for file, digest in parent['assetHashes'].items():
    if sha(ROOT/file) != digest: raise RuntimeError('Preserve changed regional material')
protected = protected_saved(ROOT)
sources, recipes = {}, {}
for zone in parent['zones']:
    identity = zone['id']; file = DIRECTORY/(identity+'.json')
    if sha(file) != plan['candidateHashes'][identity]: raise RuntimeError('Atmosphere source changed')
    sources[identity] = json.loads(file.read_text())
    recipes[identity] = atmosphere_recipe(sources[identity], json.loads((DIRECTORY/(identity+'_scenes.json')).read_text()))
tools = ['scripts/unreal/build-t1-atmosphere-studies.py', 'scripts/unreal/t1_atmosphere.py', 'scripts/unreal/t1_atmosphere_assets.py',
    'scripts/unreal/t1_material_clone.py', 'scripts/unreal/t1_materials.py', 'scripts/unreal/world_build_assets.py',
    'unreal/AegisWar/Source/AegisWar/Public/WarRegionalAtmosphere.h', 'unreal/AegisWar/Source/AegisWar/Private/WarRegionalAtmosphere.cpp',
    'unreal/AegisWar/Source/AegisWar/Private/WarRegionalAtmosphereRules.cpp', 'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll']
inputs = dict(parentMaterialSignature=parent['signature'], parentPlanSha256=parent['inputs']['parentPlanSha256'],
    parentPackages={**parent['inputs']['parentPackages'], **parent['packageHashes']}, dependencyHashes=parent['inputs']['dependencyHashes'],
    protectedHashes=protected, parentAssetHashes=parent['assetHashes'], recipes=recipes,
    sourceHashes={(DIRECTORY/(z['id']+suffix+'.json')).relative_to(ROOT).as_posix(): sha(DIRECTORY/(z['id']+suffix+'.json'))
                  for z in parent['zones'] for suffix in ('', '_scenes', '_modules')},
    tools={file: sha(ROOT/file) for file in tools})
signature = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
collection = 'T1Redesign_Atmosphere_'+signature[:12]+'_'+datetime.datetime.now().strftime('%H%M%S_%f')
assets = WorldAssets(ROOT, collection)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
zones, packages = [], []
try:
    material = weather_material(assets)
    for zone in parent['zones']:
        identity = zone['id']; source = sources[identity]; recipe = recipes[identity]
        if not levels.load_level(zone['map']): raise RuntimeError('Parent material map unavailable')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world); unreal.WarImportLibrary.prepare_world_preview_frame(world)
        states = inventory(actors)
        if not same_state(states, zone['actorInventory']): raise RuntimeError('Preserve changed parent scenery')
        scenery = [a for a in actors.get_all_level_actors() if 'WarT1PrototypeScenery' in map(str, a.tags)]
        sites = []
        for xyz in recipe['steamSites']:
            p = unreal.Vector(*xyz)
            hit = unreal.SystemLibrary.line_trace_single(world, p+unreal.Vector(0, 0, 20000), p-unreal.Vector(0, 0, 20000),
                unreal.TraceTypeQuery.ECC_VISIBILITY, True, scenery, unreal.DrawDebugTrace.NONE, True)
            if not hit or not hit.to_tuple()[0]: raise RuntimeError('Missing vent ground')
            p = hit.to_tuple()[5]
            # Authored rock centres may bury a ground emitter. Vent from their exposed tops.
            rocks = [a for a in scenery if 'basalt_shelf' in a.get_actor_label() or 'mineral_rise' in a.get_actor_label()]
            for rock in rocks:
                centre, extent = rock.get_actor_bounds(False)
                if abs(p.x-centre.x) <= extent.x and abs(p.y-centre.y) <= extent.y:
                    p.z = max(p.z, centre.z+extent.z+10)
            sites.append([p.x, p.y, p.z])
        folder = assets.folder+'/'+identity
        if not levels.new_level(folder+'/Review'): raise RuntimeError('Cannot create fresh atmosphere map')
        anchor = actors.spawn_actor_from_class(unreal.WarZoneAnchor, unreal.Vector())
        anchor.set_editor_property('zone_id', identity); anchor.set_editor_property('zone_origin', unreal.Vector())
        anchor.set_editor_property('use_spatial_bounds', True)
        bounds = source['spatial']['bounds']
        anchor.set_editor_property('content_min', unreal.Vector2D(bounds['minZ']*100, bounds['minX']*100))
        anchor.set_editor_property('content_max', unreal.Vector2D(bounds['maxZ']*100, bounds['maxX']*100))
        anchor.set_editor_property('playable_outline', [unreal.Vector2D(p['z']*100, p['x']*100) for p in source['spatial']['playableOutline']])
        generated = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, folder+'/Generated', False)
        if not generated: raise RuntimeError('Cannot create atmosphere generated layer')
        unreal.EditorLevelUtils.make_level_current(generated); clone(actors, states, {})
        atmosphere = actors.spawn_actor_from_class(unreal.WarRegionalAtmosphere, unreal.Vector())
        atmosphere.set_actor_label(identity+'_regional_atmosphere')
        atmosphere.set_editor_property('zone_id', identity); atmosphere.set_editor_property('village_centre', unreal.Vector(*recipe['villageCentre']))
        atmosphere.set_editor_property('military_centres', [unreal.Vector(*p) for p in recipe['militaryCentres']])
        atmosphere.set_editor_property('steam_sites', [unreal.Vector(*p) for p in sites])
        atmosphere.set_editor_property('weather_material', material); atmosphere.set_editor_property('audio_gain', recipe['audioGain'])
        if not same_state(inventory(actors), states): raise RuntimeError('Atmosphere clone altered existing scenery')
        if not levels.save_current_level(): raise RuntimeError('Cannot save atmosphere layer')
        authored = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, folder+'/Authored', False)
        if not authored: raise RuntimeError('Cannot reserve atmosphere authored layer')
        unreal.EditorLevelUtils.make_level_current(authored)
        if not levels.save_current_level(): raise RuntimeError('Cannot save atmosphere authored layer')
        levels.set_current_level_by_name('Review'); anchor.set_editor_property('content_levels', [folder+'/Generated', folder+'/Authored'])
        if not levels.save_current_level(): raise RuntimeError('Cannot save atmosphere review map')
        packages.extend(folder+'/'+name for name in ('Review', 'Generated', 'Authored'))
        zones.append({**zone, 'map': folder+'/Review', 'parentMap': zone['map'], 'atmosphere': {**recipe, 'steamSites': sites,
            'material': material.get_path_name()}, 'geometryPreserved': True})
finally:
    verify_protected(ROOT, protected)
result = dict(signature=signature, kind='atmosphere', inputs=inputs, zones=zones,
    packageHashes={p: sha(package_file(p)) for p in packages},
    assetHashes={p.relative_to(ROOT).as_posix(): sha(p) for p in (CONTENT/'WorldRebuild'/collection).rglob('*.uasset')},
    parentCandidatesUnchanged=True, activeCampaignChanged=False, visualApproved=False, audioApproved=False,
    walkDriveAccepted=False, licensedDistributionApproved=False)
target = DIRECTORY/('atmosphere-'+signature[:12]+'.json')
if target.exists(): raise RuntimeError('Preserve existing atmosphere receipt')
target.write_text(json.dumps(result, indent=2)+'\n'); (DIRECTORY/'atmosphere-latest.json').write_text(target.read_text())
unreal.log('WAR_T1_ATMOSPHERE_BUILT='+signature[:12])
