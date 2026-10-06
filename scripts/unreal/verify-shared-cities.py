"""Inspect saved native references and scenery actors; do not grant visual review."""
import json
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from shared_city_sources import source_plan

plan = source_plan(ROOT)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assets = unreal.EditorAssetLibrary
frontend = assets.load_asset('/Game/UI/Frontend/CapitalPresentation')
views = {str(c.get_editor_property('zone_id')): c for c in frontend.get_editor_property('cities')}
rows = []
for city in plan['cities']:
    definition = assets.load_asset(city['definition'])
    if views[city['id']].get_editor_property('city_definition') != definition:
        raise RuntimeError('Frontend uses a different city definition')
    packages = [p.get_path_name().split('.')[0] for p in definition.get_editor_property('scenery_levels')]
    if packages != city['sceneryLevels'] or definition.get_editor_property('revision') != city['revision']:
        raise RuntimeError('Native definition differs from published sources')
    count = 0
    for package in packages:
        if not levels.load_level(package):
            raise RuntimeError('Shared scenery missing')
        for actor in actors.get_all_level_actors():
            if actor.get_outer().get_path_name().split('.')[0] != package:
                raise RuntimeError('Shared scenery contains a nested layer')
            if not unreal.WarCityDefinition.is_scenery_actor(actor):
                raise RuntimeError('Gameplay actor in shared scenery: ' + actor.get_name())
            count += 1
            for component in actor.get_components_by_class(unreal.StaticMeshComponent):
                mesh = component.static_mesh
                if component.is_visible() and (not mesh or not mesh.get_path_name().startswith('/Game/')):
                    raise RuntimeError('Missing or substitute scenery model')
                for index in range(component.get_num_materials()):
                    material = component.get_material(index)
                    if not material or material.get_path_name().startswith('/Game/UI/Frontend/Materials/'):
                        raise RuntimeError('Missing or copied city material')
    rows.append(dict(city=city['id'], definition=city['definition'], sceneryActors=count, revision=city['revision']))

if not levels.load_level(plan['campaignMap']):
    raise RuntimeError('Campaign unavailable')
for city in plan['cities']:
    anchor = next(a for a in actors.get_all_level_actors() if isinstance(a, unreal.WarZoneAnchor)
                  and str(a.get_editor_property('zone_id')) == city['id'])
    if anchor.get_editor_property('city_definition') != assets.load_asset(city['definition']):
        raise RuntimeError('Campaign uses a different city definition')
    if list(map(str, anchor.get_editor_property('content_levels'))) != city['gameplayLevels']:
        raise RuntimeError('Campaign overlay differs from its manifest')

if not levels.load_level('/Game/Capitals/Siege/AegisCapital_Siege'):
    raise RuntimeError('Siege unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
field = next(a for a in actors.get_all_level_actors() if isinstance(a, unreal.WarSiegeBattlefield))
if field.get_editor_property('city_definition') != assets.load_asset(plan['cities'][0]['definition']):
    raise RuntimeError('Siege uses a different city definition')
actual = {level.get_outer().get_path_name().split('.')[0] for level in unreal.EditorLevelUtils.get_levels(world)}
expected = set(plan['cities'][0]['sceneryLevels']) | {'/Game/Capitals/Siege/AegisCapital_Siege'}
if actual != expected:
    raise RuntimeError('Siege has missing or additional scenery: ' + str(actual ^ expected))
out = ROOT / 'artifacts/unreal/shared-cities/native-verification.json'
out.write_text(json.dumps(dict(passed=True, cities=rows, visualApproved=False), indent=2) + '\n')
unreal.log('WAR_SHARED_CITY_REFERENCES_VERIFIED')
