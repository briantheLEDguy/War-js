"""Read source kit geometry or saved capital state without changing packages."""
import hashlib
import json
from pathlib import Path
import sys
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = ROOT / 'artifacts/unreal/capital-expansion'
OUT.mkdir(parents=True, exist_ok=True)
project = Path(unreal.Paths.project_dir()).resolve()


def vector(v):
    return [v.x, v.y, v.z]


def main():
    if project.name == 'CityKitStaging':
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        registry.search_all_assets(True)
        rows = []
        for prefix in ('/Game/Medieval_Environment', '/Game/Medieval_Mod_Town'):
            for data in registry.get_assets_by_path(prefix, recursive=True):
                if str(data.asset_class_path.asset_name) != 'StaticMesh':
                    continue
                package_name = str(data.package_name)
                if '/Hipoly/' in package_name or '/Real_Landscape/' in package_name or '/UV3/' in package_name:
                    continue
                mesh = unreal.load_asset(str(data.package_name))
                bounds = mesh.get_bounds()
                package = project/'Content'/(str(data.package_name).removeprefix('/Game/')+'.uasset')
                rows.append({'path': mesh.get_path_name(), 'name': str(data.asset_name),
                             'origin': vector(bounds.origin), 'extent': vector(bounds.box_extent),
                             'lods': mesh.get_num_lods(),
                             'triangles': [mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())],
                             'materials': [s.material_interface.get_path_name() if s.material_interface else None
                                           for s in mesh.static_materials],
                             'sha256': hashlib.sha256(package.read_bytes()).hexdigest()})
        (OUT/'kit-inventory.json').write_text(json.dumps(rows, indent=2)+'\n')
        unreal.log('WAR_EXPANSION_INVENTORY='+str(len(rows)))
        return
    if project != ROOT/'unreal/AegisWar':
        raise RuntimeError('Unexpected project')
    from world_actor_state import snapshot
    manifest = json.loads((ROOT/'artifacts/unreal/world-portals/zone-manifest.json').read_text())
    build = json.loads((ROOT/'artifacts/unreal/world-portals/build.json').read_text())
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level.load_level(build['map']):
        raise RuntimeError('Cannot load official world')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    result = {}
    for zone in manifest['zones']:
        if zone['id'] not in ('aegis_capital', 'riftspire_capital'):
            continue
        packages = set(zone['levels'].values())
        rows = []
        for actor in actors:
            package = actor.get_outer().get_path_name().split('.')[0]
            if package not in packages:
                continue
            if isinstance(actor, (unreal.WorldSettings, unreal.LevelScriptActor, unreal.Brush)):
                continue
            center, extent = actor.get_actor_bounds(False)
            rows.append({'name': actor.get_name(), 'package': package, 'state': snapshot(actor),
                         'center': vector(center), 'extent': vector(extent)})
        hashes = {p: hashlib.sha256((project/'Content'/(p.removeprefix('/Game/')+'.umap')).read_bytes()).hexdigest()
                  for p in packages}
        result[zone['id']] = {'origin': zone['origin'], 'levels': zone['levels'], 'hashes': hashes, 'actors': rows}
    (OUT/'baseline.json').write_text(json.dumps(result, indent=2)+'\n')
    unreal.log('WAR_EXPANSION_BASELINE='+str({k: len(v['actors']) for k,v in result.items()}))


main()
