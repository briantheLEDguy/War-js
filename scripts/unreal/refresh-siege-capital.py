"""Refresh private siege scenery from all current Aegis capital layers; preserve its overlay."""
import hashlib
import json
import shutil
import time
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / 'unreal/AegisWar/Content'
OUT = ROOT / 'artifacts/unreal/scenario-queues'
TARGET = '/Game/Capitals/Siege/AegisCapital_Siege'
manifest = json.loads((ROOT / 'artifacts/unreal/world-portals/zone-manifest.json').read_text())
capital = next(zone for zone in manifest['zones'] if zone['id'] == 'aegis_capital')
sources = list(capital['levels'].values())
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
library = unreal.EditorAssetLibrary


def file(package):
    if not package.startswith('/Game/'):
        raise RuntimeError('Only private project packages may be copied')
    result = (CONTENT / (package[6:] + '.umap')).resolve()
    result.relative_to(CONTENT.resolve())
    return result


def sha(package):
    return hashlib.sha256(file(package).read_bytes()).hexdigest()


hashes = {source: sha(source) for source in sources}
revision = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
output = OUT / 'capital' / str(time.time_ns())
output.mkdir(parents=True)
shutil.copy2(file(TARGET), output / 'before-refresh.umap')
gameplay = (unreal.WarEnemy, unreal.WarQuestNpc, unreal.WarCityNpc, unreal.WarResourceNode,
            unreal.WarCraftingStation, unreal.WarZonePortal, unreal.WarZoneAnchor)
copies = []
previous = json.loads((OUT / "capital-scenery.json").read_text()) if (OUT / "capital-scenery.json").exists() else {}
counts = previous.get("counts", {}) if previous.get("revision") == revision else {}
for index, source in enumerate(sources):
    destination = f'/Game/Capitals/Siege/Scenery_{revision[:12]}/Layer_{index}'
    if library.does_asset_exist(destination):
        if previous.get('revision') != revision or destination not in previous.get('layers', []):
            raise RuntimeError('Unowned scenery revision already exists; preserve it.')
        copies.append(destination)
        continue
    if not library.duplicate_asset(source, destination) or not levels.load_level(destination):
        raise RuntimeError('Could not copy source scenery: ' + source)
    retained = removed = 0
    for actor in list(actors.get_all_level_actors()):
        if actor.get_outer().get_path_name().split('.')[0] != destination:
            continue
        if isinstance(actor, gameplay):
            if not actors.destroy_actor(actor):
                raise RuntimeError('Cannot remove copied campaign gameplay')
            removed += 1
        else:
            retained += 1
    if not levels.save_current_level():
        raise RuntimeError('Cannot save copied scenery')
    copies.append(destination)
    counts[source] = dict(retained=retained, removedGameplay=removed)

if not levels.load_level(TARGET):
    raise RuntimeError('Cannot load siege overlay')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
old = {a.get_outer().get_path_name().split('.')[0] for a in actors.get_all_level_actors()} - {TARGET}
for package in old:
    if not package.startswith('/Game/Capitals/Siege/'):
        raise RuntimeError('Unexpected shared layer in siege; preserve and inspect: ' + package)
    streaming = unreal.GameplayStatics.get_streaming_level(world, package)
    if streaming and not unreal.EditorLevelUtils.remove_level_from_world(streaming.get_loaded_level()):
        raise RuntimeError('Cannot detach old scenery')
for package in copies:
    if not unreal.EditorLevelUtils.add_level_to_world(world, package, unreal.LevelStreamingAlwaysLoaded):
        raise RuntimeError('Cannot attach current scenery')
unreal.GameplayStatics.flush_level_streaming(world)
field = next(a for a in actors.get_all_level_actors() if isinstance(a, unreal.WarSiegeBattlefield))
supply = field.get_editor_property('objectives')[0]
field.set_editor_property('equipment_spawns', [supply - unreal.Vector(1300, 0, 0), supply - unreal.Vector(2150, 0, 0)])
if not levels.set_current_level_by_name('AegisCapital_Siege') or not levels.save_current_level():
    raise RuntimeError('Cannot save refreshed siege overlay')
if any(sha(source) != digest for source, digest in hashes.items()):
    raise RuntimeError('Source capital changed during refresh')
receipt = dict(version=1, revision=revision, sourceHashes=hashes, layers=copies, layerHashes={name: sha(name) for name in copies}, counts=counts,
               map=TARGET, mapSha256=sha(TARGET), sourcePackagesUnchanged=True, navigationVerified=False, visualVerified=False)
(OUT / 'capital-scenery.json').write_text(json.dumps(receipt, indent=2) + '\n')
unreal.log('WAR_SCENARIO_SCENERY=' + json.dumps(receipt))
