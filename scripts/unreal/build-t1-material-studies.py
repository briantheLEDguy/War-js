"""Create fresh private terrain material candidates, preserving frozen geometry and homes."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from t1_materials import terrain_recipe, protected_saved, verify_protected, sha, same_state
from t1_material_assets import regional_material
from t1_material_clone import inventory, clone
from world_build_assets import WorldAssets
DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
CONTENT = ROOT/'unreal/AegisWar/Content'
package_file = lambda package: CONTENT/(package.removeprefix('/Game/')+'.umap')
parent = json.loads((DIRECTORY/'homes-latest.json').read_text())
plan = json.loads((DIRECTORY/'plan.json').read_text())
if sha(DIRECTORY/'plan.json') != parent['inputs']['parentPlanSha256']:
    raise RuntimeError('Material study requires the frozen home terrain plan')
for package, digest in {**parent['inputs']['parentPackages'], **parent['packageHashes']}.items():
    if sha(package_file(package)) != digest: raise RuntimeError('Preserve changed parent candidates')
for package, digest in parent['inputs']['dependencyHashes'].items():
    if sha(CONTENT/(package.removeprefix('/Game/')+'.uasset')) != digest: raise RuntimeError('Preserve changed private source kit')
protected = protected_saved(ROOT)
recipes = {zone['id']: terrain_recipe(ROOT, zone['id']) for zone in parent['zones']}
inputs = dict(parentHomeSignature=parent['signature'], parentPlanSha256=parent['inputs']['parentPlanSha256'],
    parentPackages={**parent['inputs']['parentPackages'], **parent['packageHashes']}, dependencyHashes=parent['inputs']['dependencyHashes'],
    recipes=recipes, protectedHashes=protected,
    tools={file: sha(ROOT/file) for file in ['scripts/unreal/build-t1-material-studies.py', 'scripts/unreal/t1_materials.py',
        'scripts/unreal/t1_material_assets.py', 'scripts/unreal/t1_material_clone.py', 'scripts/unreal/world_build_assets.py']})
signature = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
collection = 'T1Redesign_Materials_'+signature[:12]+'_'+datetime.datetime.now().strftime('%H%M%S_%f')
assets = WorldAssets(ROOT, collection)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
zones, packages = [], []
try:
    for zone in parent['zones']:
        identity = zone['id']
        source_file = DIRECTORY/(identity+'.json')
        if sha(source_file) != plan['candidateHashes'][identity]: raise RuntimeError('Material source coordinates changed')
        source = json.loads(source_file.read_text())
        if not levels.load_level(zone['map']): raise RuntimeError('Parent material candidate unavailable')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world)
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        states = inventory(actors)
        counts = {kind: sum(s['kind'] == kind for s in states.values()) for kind in ('mesh', 'light', 'room')}
        if counts != dict(mesh=zone['placedSourceModels']+2, light=22, room=2):
            raise RuntimeError('Frozen candidate room/light/mesh inventory differs: '+str(counts))
        overrides, materials = {}, {}
        for role, recipe in recipes[identity]['layers'].items():
            label = identity+'_'+role
            if label not in states or len(states[label]['materials']) != 1: raise RuntimeError('Regional surface missing')
            material, expressions = regional_material(assets, label, recipe)
            overrides[label] = material
            materials[role] = dict(asset=material.get_path_name(), expressions=expressions)
        folder = assets.folder+'/'+identity
        if not levels.new_level(folder+'/Review'): raise RuntimeError('Cannot create fresh material study')
        anchor = actors.spawn_actor_from_class(unreal.WarZoneAnchor, unreal.Vector())
        anchor.set_editor_property('zone_id', identity); anchor.set_editor_property('zone_origin', unreal.Vector())
        anchor.set_editor_property('use_spatial_bounds', True)
        bounds = source['spatial']['bounds']
        anchor.set_editor_property('content_min', unreal.Vector2D(bounds['minZ']*100, bounds['minX']*100))
        anchor.set_editor_property('content_max', unreal.Vector2D(bounds['maxZ']*100, bounds['maxX']*100))
        anchor.set_editor_property('playable_outline', [unreal.Vector2D(p['z']*100, p['x']*100) for p in source['spatial']['playableOutline']])
        generated = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, folder+'/Generated', False)
        if not generated: raise RuntimeError('Cannot create material generated layer')
        unreal.EditorLevelUtils.make_level_current(generated)
        clone(actors, states, overrides)
        expected = json.loads(json.dumps(states))
        for label, material in overrides.items(): expected[label]['materials'] = [material.get_path_name()]
        actual = inventory(actors)
        if not same_state(actual, expected):
            differing = [label for label in expected if not same_state(actual.get(label), expected[label])]
            (DIRECTORY/'material-clone-failure.json').write_text(json.dumps({label: dict(expected=expected[label], actual=actual.get(label)) for label in differing}, indent=2))
            raise RuntimeError('Material clone altered preserved actor state: '+str(differing[:8]))
        if not levels.save_current_level(): raise RuntimeError('Cannot save material generated layer')
        authored = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, folder+'/Authored', False)
        if not authored: raise RuntimeError('Cannot reserve material authored layer')
        unreal.EditorLevelUtils.make_level_current(authored)
        if not levels.save_current_level(): raise RuntimeError('Cannot save material authored layer')
        levels.set_current_level_by_name('Review')
        anchor.set_editor_property('content_levels', [folder+'/Generated', folder+'/Authored'])
        if not levels.save_current_level(): raise RuntimeError('Cannot save material review map')
        packages.extend(folder+'/'+name for name in ('Review', 'Generated', 'Authored'))
        zones.append({**zone, 'map': folder+'/Review', 'materials': materials, 'actorInventory': actual,
            'parentMap': zone['map'], 'geometryPreserved': True, 'roomLightingPreserved': True})
finally:
    verify_protected(ROOT, protected)
asset_files = [p for p in (CONTENT/'WorldRebuild'/collection).rglob('*.uasset')]
result = dict(signature=signature, kind='materials', inputs=inputs, zones=zones,
    packageHashes={p: sha(package_file(p)) for p in packages},
    assetHashes={p.relative_to(ROOT).as_posix(): sha(p) for p in asset_files},
    parentCandidatesUnchanged=True, activeCampaignChanged=False, visualApproved=False, walkDriveAccepted=False,
    furnishedHomesAccepted=0, licensedDistributionApproved=False)
target = DIRECTORY/('materials-'+signature[:12]+'.json')
if target.exists(): raise RuntimeError('Preserve existing material receipt')
target.write_text(json.dumps(result, indent=2)+'\n')
(DIRECTORY/'materials-latest.json').write_text(target.read_text())
unreal.log('WAR_T1_MATERIALS_BUILT='+signature[:12])
