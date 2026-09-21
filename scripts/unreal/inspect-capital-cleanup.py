"""Inspect private capital dependencies without saving or modifying assets."""
import json
from pathlib import Path
import unreal
ROOT = Path(__file__).resolve().parents[2]
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
base = '/Game/Capitals/crownward'
rows = []
options = unreal.AssetRegistryDependencyOptions(True, True, True, True, True)
for asset in registry.get_assets_by_path(base, recursive=True):
    package = str(asset.package_name)
    rows.append({'package':package, 'class':str(asset.asset_class_path.asset_name),
        'dependencies':[str(p) for p in registry.get_dependencies(asset.package_name, options)],
        'referencers':[str(p) for p in registry.get_referencers(asset.package_name, options)]})
(ROOT/'artifacts/unreal/licensed-kits/capital-cleanup-inspection.json').write_text(json.dumps(rows,indent=2))
unreal.log('WAR_CAPITAL_DEPENDENCIES_INSPECTED')
final_map = '/Game/Capitals/crownward/FinalAppearance_20260921_181402_268830/AegisCapital_AppearancePreview'
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(final_map):
    raise RuntimeError('Final city did not load')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
missing = [a.get_actor_label() for a in actors if isinstance(a, unreal.StaticMeshActor) and not a.static_mesh_component.static_mesh]
if missing:
    raise RuntimeError('Final city has missing meshes: '+repr(missing))
(ROOT/'artifacts/unreal/licensed-kits/capital-final-load.json').write_text(json.dumps({'map':final_map,'actors':len(actors),'missingStaticMeshes':missing,'saved':False},indent=2))
unreal.log('WAR_FINAL_CITY_LOADED')
