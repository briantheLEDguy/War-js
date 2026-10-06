"""Native city authoring shared by activation and installed-content migration."""
import hashlib
import json
import sys
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from shared_city_sources import digest, package_file, protected_source_file, REVIEWED_ENGINE_SOURCE
from world_actor_state import snapshot

OWNER = 'shared-city-v1'
assets = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
registry = unreal.AssetRegistryHelpers.get_asset_registry()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def load(package):
    if not levels.load_level(package):
        raise RuntimeError('Cannot load city package: ' + package)
    unreal.GameplayStatics.flush_level_streaming(world())


def own(package):
    return [a for a in actors.get_all_level_actors() if a.get_outer().get_path_name().split('.')[0] == package]


def save(package):
    if not levels.set_current_level_by_name(package.rsplit('/', 1)[1]) or not levels.save_current_level():
        raise RuntimeError('Cannot save city package: ' + package)


def detach(package):
    stream = unreal.GameplayStatics.get_streaming_level(world(), package)
    if stream and not unreal.EditorLevelUtils.remove_level_from_world(stream.get_loaded_level()):
        raise RuntimeError('Cannot detach city layer: ' + package)


def dependencies(packages, protected_sources=None):
    options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
        include_hard_package_references=True, include_searchable_names=False,
        include_soft_management_references=False, include_hard_management_references=False)
    result, todo = {}, list(packages)
    visited = set(packages)
    refreshed = set()
    protected_sources = protected_sources or {}
    while todo:
        package = todo.pop()
        package_file(ROOT, package)
        folder = package.rsplit('/', 1)[0]
        if folder not in refreshed:
            # Newly saved worlds and material instances can retain stale
            # in-memory dependency rows until their on-disk registry is scanned.
            registry.scan_paths_synchronous([folder], True)
            refreshed.add(folder)
        for name in registry.get_dependencies(package, options):
            name = str(name)
            if name in visited:
                continue
            if name == REVIEWED_ENGINE_SOURCE:
                expected = protected_sources.get(name)
                if expected is None:
                    raise RuntimeError('Shared city cloud parent needs its signed protected source hash')
                file = protected_source_file(ROOT, name, expected)
                if digest(file) != expected:
                    raise RuntimeError('Protected Engine source changed during city dependency collection')
                visited.add(name)
                result[name] = expected
                # Only this reviewed read-only parent is in the city contract.
                # Engine packages never enter the owned Game dependency walk.
                continue
            if not name.startswith('/Game/'):
                continue
            visited.add(name)
            file = package_file(ROOT, name)
            if file.suffix == '.umap':
                raise RuntimeError('Shared scenery has a nested world dependency: ' + name)
            result[name] = digest(file)
            todo.append(name)
    return result



def prepare_city(zone, definition_path, backup, record_created, evidence, protected_sources=None):
    zone_id = zone['id']
    scenery, gameplay, changes = [], [], []
    for key, source in list(zone['levels'].items()):
        backup(package_file(ROOT, source))
        load(source)
        source_actors = own(source)
        structural = (unreal.WorldSettings, unreal.LevelScriptActor, unreal.Brush)
        visual = [a for a in source_actors if unreal.WarCityDefinition.is_scenery_actor(a)
                  and not isinstance(a, structural)]
        services = [a for a in source_actors if not unreal.WarCityDefinition.is_scenery_actor(a)]
        if not visual:
            gameplay.append(source)
            continue
        scenery.append(source)
        if not services:
            continue
        # Moving the small gameplay set keeps scenery, collision and GM identities in their original package.
        if any(a.get_attach_parent_actor() and a.get_attach_parent_actor() not in services for a in services):
            raise RuntimeError('Gameplay is attached to scenery; reconcile before splitting: ' + source)
        destination = '/Game/Cities/Shared/' + zone_id + '/Gameplay_' + hashlib.sha256(source.encode()).hexdigest()[:12]
        if assets.does_asset_exist(destination):
            raise RuntimeError('Preserve existing gameplay layer: ' + destination)
        before = {a.get_name(): snapshot(a) for a in source_actors}
        stream = unreal.EditorLevelUtils.create_new_streaming_level(unreal.LevelStreamingDynamic, destination, False)
        if not stream:
            raise RuntimeError('Cannot create gameplay overlay')
        record_created(destination)
        if not unreal.WarImportLibrary.move_city_gameplay_to_level(services, stream):
            raise RuntimeError('Incomplete gameplay move')
        after = {a.get_name(): snapshot(a) for a in own(source) + own(destination)}
        if before != after:
            write(evidence / ('state-diff-' + zone_id + '-' + key + '.json'), dict(before=before, after=after))
            raise RuntimeError('Actor state changed while moving gameplay; see state-diff')
        save(destination)
        detach(destination)
        save(source)
        gameplay.append(destination)
        zone['levels']['gameplay_' + key] = destination
        changes.append(dict(source=source, destination=destination, actors=len(services)))
    if not scenery:
        raise RuntimeError('Capital has no scenery: ' + zone_id)
    visual_hashes = dependencies(scenery, protected_sources)
    hashes = {p: digest(package_file(ROOT, p)) for p in scenery + gameplay}
    revision = hashlib.sha256(json.dumps(dict(scenery={p: hashes[p] for p in scenery},
        dependencies=visual_hashes, origin=zone['origin']), sort_keys=True).encode()).hexdigest()
    definition = assets.load_asset(definition_path) if assets.does_asset_exist(definition_path) else None
    if definition:
        if assets.get_metadata_tag(definition, 'WarCityOwner') != OWNER:
            raise RuntimeError('Preserve unowned city definition')
        backup(package_file(ROOT, definition_path))
    else:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', unreal.WarCityDefinition)
        definition = unreal.AssetToolsHelpers.get_asset_tools().create_asset('City',
            definition_path.rsplit('/', 1)[0], unreal.WarCityDefinition, factory)
        if not definition:
            raise RuntimeError('Cannot create shared city definition')
        assets.set_metadata_tag(definition, 'WarCityOwner', OWNER)
        record_created(definition_path)
    definition.set_editor_property('zone_id', zone_id)
    definition.set_editor_property('origin', unreal.Vector(*zone['origin']))
    definition.set_editor_property('revision', revision)
    definition.set_editor_property('scenery_levels', [assets.load_asset(p) for p in scenery])
    if not assets.save_loaded_asset(definition, only_if_is_dirty=False):
        raise RuntimeError('Cannot save shared city definition')
    hashes[definition_path] = digest(package_file(ROOT, definition_path))
    zone.update(cityDefinition=definition_path, cityRevision=revision)
    return dict(id=zone_id, definition=definition_path, revision=revision, origin=zone['origin'],
        sceneryLevels=scenery, gameplayLevels=gameplay, packageHashes=hashes,
        dependencyHashes=visual_hashes, movedGameplay=changes)
