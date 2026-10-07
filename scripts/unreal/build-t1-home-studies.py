"""Clone the isolated candidates and substitute two fingerprinted private home studies."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from t1_native_homes import native_home
DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
CONTENT = ROOT/'unreal/AegisWar/Content'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
package_file = lambda p: CONTENT/(p.split('.')[0].removeprefix('/Game/')+'.umap')
receipt = json.loads((DIRECTORY/'native-latest.json').read_text())
plan = json.loads((DIRECTORY/'plan.json').read_text())
if sha(DIRECTORY/'plan.json') != receipt['planSha256']:
    raise RuntimeError('Home studies require matching saved candidates')
catalog_file = ROOT/'artifacts/unreal/capital-expansion/assets.json'
catalog = json.loads(catalog_file.read_text())['templates']
templates = {key: catalog[key] for key in ['aegis_interior_00_home', 'aegis_interior_01_home', 'riftspire_interior_00_home', 'riftspire_interior_01_home']}
# Fingerprint the full existing dependency closure before referencing the kit.
registry = unreal.AssetRegistryHelpers.get_asset_registry()
options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True,
    include_searchable_names=False, include_soft_management_references=False, include_hard_management_references=False)
dependencies = {}
pending = [t['mesh'].split('.')[0] for t in templates.values()]
while pending:
    package = pending.pop()
    if package in dependencies:
        continue
    if len(dependencies) > 2048:
        raise RuntimeError('Home catalog dependency closure exceeds the bound')
    if not package.startswith('/Game/') or '..' in package:
        raise RuntimeError('Home catalog includes unsupported dependency: '+package)
    file = CONTENT/(package.removeprefix('/Game/')+'.uasset')
    dependencies[package] = sha(file)
    pending.extend(str(p) for p in registry.get_dependencies(package, options) if str(p).startswith('/Game/'))
for template in templates.values():
    if dependencies[template['mesh'].split('.')[0]] != template['sha256']:
        raise RuntimeError('Preserve independently edited home template: '+template['id'])
inputs = dict(parentPlanSha256=receipt['planSha256'], parentPackages=receipt['packageHashes'],
    catalogSha256=sha(catalog_file), dependencyHashes=dependencies,
    tools={p: sha(ROOT/p) for p in ['scripts/unreal/build-t1-home-studies.py', 'scripts/unreal/t1_native_homes.py',
        'unreal/AegisWar/Source/AegisWar/Public/WarPracticalLight.h', 'unreal/AegisWar/Source/AegisWar/Private/WarPracticalLight.cpp',
        'unreal/AegisWar/Source/AegisWar/Public/WarInteriorAtmosphere.h', 'unreal/AegisWar/Source/AegisWar/Private/WarInteriorAtmosphere.cpp',
        'unreal/AegisWar/Source/AegisWar/Private/WarZoneLightingSubsystem.cpp']})
signature = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
target = DIRECTORY/('homes-'+signature[:12]+'.json')

def unchanged():
    for package, digest in receipt['packageHashes'].items():
        if sha(package_file(package)) != digest:
            raise RuntimeError('Parent candidate was edited; preserve it and reconcile')
    for package, digest in dependencies.items():
        if sha(CONTENT/(package.removeprefix('/Game/')+'.uasset')) != digest:
            raise RuntimeError('Home source dependency changed: '+package)

unchanged()
if target.exists():
    saved = json.loads(target.read_text())
    for package, digest in saved['packageHashes'].items():
        if sha(package_file(package)) != digest:
            raise RuntimeError('Preserve owner-edited home study')
    (DIRECTORY/'homes-latest.json').write_text(target.read_text())
    unreal.log('WAR_T1_HOMES_ALREADY_BUILT='+signature[:12])
else:
    collection = '/Game/WorldRebuild/T1Redesign_Homes_'+signature[:12]+'_'+datetime.datetime.now().strftime('%H%M%S_%f')
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    zones, packages = [], []
    for parent in receipt['zones']:
        identity = parent['id']
        if not levels.load_level(parent['map']):
            raise RuntimeError('Parent candidate unavailable')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.GameplayStatics.flush_level_streaming(world)
        unreal.WarImportLibrary.prepare_world_preview_frame(world)
        village = json.loads((DIRECTORY/(identity+'_modules.json')).read_text())
        if sha(DIRECTORY/(identity+'_modules.json')) != plan['moduleHashes'][identity]:
            raise RuntimeError('Village layout differs from parent candidate')
        source_file = DIRECTORY/(identity+'.json')
        if sha(source_file) != plan['candidateHashes'][identity]:
            raise RuntimeError('Terrain source differs from parent candidate')
        source = json.loads(source_file.read_text())
        models = json.loads((DIRECTORY/'models.json').read_text())
        if models['planSha256'] != receipt['planSha256']:
            raise RuntimeError('Ground bindings differ from parent candidate')
        ground = {p['source']['id']: p['source']['groundY'] for p in models['placements'] if p['zone'] == identity}
        modules = [m for m in village['modules'] if m['interiorRequired']]
        if len(modules) != 2:
            raise RuntimeError('Home study requires the two reserved lots')
        realm = 'aegis' if identity == 'sunmeadow_march' else 'riftspire'
        homes = [native_home(m, templates[f'{realm}_interior_{i:02d}_home'], ground[m['id']]) for i, m in enumerate(modules)]
        homes_by_id = {h['id']: h for h in homes}
        states, lights = [], []
        for actor in actors.get_all_level_actors():
            if isinstance(actor, unreal.StaticMeshActor):
                component = actor.static_mesh_component
                if actor.get_actor_label() in homes_by_id:
                    continue
                location = actor.get_actor_location()
                fixture_home = homes_by_id.get(actor.get_actor_label().removesuffix('_lantern'))
                if fixture_home and identity == 'sunmeadow_march':
                    location = unreal.Vector(*fixture_home['wallFixture'])
                states.append(dict(mesh=component.static_mesh, materials=[component.get_material(i) for i in range(component.get_num_materials())],
                    location=location, rotation=actor.get_actor_rotation(), scale=actor.get_actor_scale3d(),
                    collision=str(component.get_collision_profile_name()), label=actor.get_actor_label(), tags=list(actor.tags)))
            elif isinstance(actor, unreal.WarPracticalLight):
                location = actor.get_actor_location()
                fixture_home = homes_by_id.get(actor.get_actor_label().removesuffix('_lantern_light'))
                if fixture_home and identity == 'sunmeadow_march':
                    location = unreal.Vector(*fixture_home['wallFixture'])+unreal.Vector(0, 0, 45)
                lights.append(dict(location=location, zone=actor.get_editor_property('zone_id'), lumens=actor.get_editor_property('night_lumens'), label=actor.get_actor_label()))
        if len(states) != parent['placedSourceModels'] or len(lights) != parent['practicalLights']:
            raise RuntimeError('Parent clone inventory differs')
        folder = collection+'/'+identity
        if not levels.new_level(folder+'/Review'):
            raise RuntimeError('Cannot create home review map')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        anchor = actors.spawn_actor_from_class(unreal.WarZoneAnchor, unreal.Vector())
        anchor.set_editor_property('zone_id', identity)
        anchor.set_editor_property('zone_origin', unreal.Vector())
        anchor.set_editor_property('use_spatial_bounds', True)
        bounds = source['spatial']['bounds']
        anchor.set_editor_property('content_min', unreal.Vector2D(bounds['minZ']*100, bounds['minX']*100))
        anchor.set_editor_property('content_max', unreal.Vector2D(bounds['maxZ']*100, bounds['maxX']*100))
        anchor.set_editor_property('playable_outline', [unreal.Vector2D(p['z']*100, p['x']*100) for p in source['spatial']['playableOutline']])
        generated = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, folder+'/Generated', False)
        if not generated:
            raise RuntimeError('Cannot create generated home-study layer')
        unreal.EditorLevelUtils.make_level_current(generated)
        for state in states:
            actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, state['location'], state['rotation'])
            actor.static_mesh_component.set_static_mesh(state['mesh'])
            for i, material in enumerate(state['materials']):
                actor.static_mesh_component.set_material(i, material)
            actor.set_actor_scale3d(state['scale'])
            actor.static_mesh_component.set_collision_profile_name(state['collision'])
            actor.set_actor_label(state['label'])
            actor.tags = state['tags']
        for home in homes:
            actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*home['location']), unreal.Rotator(yaw=home['yawDegrees']))
            actor.static_mesh_component.set_static_mesh(unreal.load_asset(home['mesh']))
            actor.static_mesh_component.set_collision_profile_name('BlockAll')
            actor.set_actor_label(home['id'])
            actor.tags = ['WarT1PrototypeScenery', 'WarT1FurnishedHomeStudy']
            room = actors.spawn_actor_from_class(unreal.WarInteriorAtmosphere, unreal.Vector(*home['interiorVolume']), unreal.Rotator(yaw=home['yawDegrees']))
            room.set_editor_property('zone_id', identity)
            room.room_bounds.set_box_extent(unreal.Vector(*home['interiorExtent']), False)
            room.set_actor_label(home['id']+'_interior_atmosphere')
            room.tags = ['WarT1InteriorAtmosphereStudy']
            light = actors.spawn_actor_from_class(unreal.WarPracticalLight, unreal.Vector(*home['interiorFixture']))
            light.set_editor_property('zone_id', identity)
            light.set_editor_property('day_lumens', 2500)
            light.set_editor_property('night_lumens', 1400)
            component = light.get_component_by_class(unreal.PointLightComponent)
            component.set_editor_property('attenuation_radius', 650)
            component.set_editor_property('cast_shadows', True)
            light.set_actor_label(home['id']+'_interior_light')
            light.tags = ['WarT1PrototypePractical', 'WarT1InteriorPractical']
        for state in lights:
            light = actors.spawn_actor_from_class(unreal.WarPracticalLight, state['location'])
            light.set_editor_property('zone_id', state['zone'])
            light.set_editor_property('night_lumens', state['lumens'])
            light.set_actor_label(state['label'])
            light.tags = ['WarT1PrototypePractical']
        if not levels.save_current_level():
            raise RuntimeError('Cannot save generated home study')
        authored = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingAlwaysLoaded, folder+'/Authored', False)
        if not authored:
            raise RuntimeError('Cannot create authored home-study layer')
        unreal.EditorLevelUtils.make_level_current(authored)
        if not levels.save_current_level():
            raise RuntimeError('Cannot reserve owner home-study layer')
        levels.set_current_level_by_name('Review')
        anchor.set_editor_property('content_levels', [folder+'/Generated', folder+'/Authored'])
        if not levels.save_current_level():
            raise RuntimeError('Cannot save home-study routing')
        packages.extend([folder+'/'+name for name in ['Review', 'Generated', 'Authored']])
        zones.append(dict(id=identity, map=folder+'/Review', homes=homes, placedSourceModels=parent['placedSourceModels'],
            practicalLights=len(lights)+len(homes), furnishedHomeStudies=2, furnishedHomesAccepted=0))
    unchanged()
    result = dict(signature=signature, inputs=inputs, zones=zones, packageHashes={p: sha(package_file(p)) for p in packages},
        parentCandidatesUnchanged=True, activeCampaignChanged=False, licensedDistributionApproved=False,
        visualApproved=False, walkDriveAccepted=False, furnishedHomesAccepted=0)
    target.write_text(json.dumps(result, indent=2)+'\n')
    (DIRECTORY/'homes-latest.json').write_text(target.read_text())
    unreal.log('WAR_T1_HOMES_BUILT='+signature[:12])
