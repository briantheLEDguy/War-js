"""Attach a verified partition to the main world, retaining the previous packages for rollback."""
import datetime
import hashlib
import json
import shutil
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
directory = ROOT/'artifacts/unreal/world-portals'
receipt = json.loads((directory/'build.json').read_text())
manifest = json.loads((directory/'partition-candidate.json').read_text())


def package_file(package):
    if not package.startswith('/Game/'): raise RuntimeError('Invalid package')
    return ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')


def sha(package): return hashlib.sha256(package_file(package).read_bytes()).hexdigest()


if receipt.get('partitionManifest'):
    if receipt['layer'] != manifest['layer']: raise RuntimeError('A different partition is already attached')
    unreal.log('WAR_WORLD_PARTITION_ALREADY_ATTACHED')
else:
    if receipt['layer'] != manifest['previousLayer'] or receipt['planSha256'] != manifest['planSha256']:
        raise RuntimeError('Source build changed; regenerate the partition')
    if sha(receipt['layer']) != manifest['previousLayerSha256']: raise RuntimeError('Source layer changed after partitioning')
    for package, expected in manifest['packageHashes'].items():
        if sha(package) != expected: raise RuntimeError('Candidate package changed: '+package)
    main = package_file(receipt['map'])
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    shutil.copy2(main, directory/('main-before-partition-'+stamp+'.umap'))
    shutil.copy2(directory/'build.json', directory/('build-before-partition-'+stamp+'.json'))
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level.load_level(receipt['map']): raise RuntimeError('Main world unavailable')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # Root city actors are never moved or rewritten by the partition operation.
    def root_state():
        return {actor.get_path_name():str(actor.get_actor_transform()) for actor in actor_subsystem.get_all_level_actors()
                if actor.get_outer().get_outer().get_path_name() == receipt['map']+'.'+main.stem}
    before = root_state()
    old = unreal.GameplayStatics.get_streaming_level(world, receipt['layer'])
    if not old or not unreal.EditorLevelUtils.remove_level_from_world(old.get_loaded_level()):
        raise RuntimeError('Previous campaign attachment is missing')
    if not unreal.EditorLevelUtils.add_level_to_world(world, manifest['layer'], unreal.LevelStreamingAlwaysLoaded):
        raise RuntimeError('Could not attach routing layer')
    for zone in manifest['zones']:
        for package in zone['levels'].values():
            streaming = unreal.EditorLevelUtils.add_level_to_world(world, package, unreal.LevelStreamingDynamic)
            if not streaming: raise RuntimeError('Could not attach '+package)
            streaming.set_editor_property('initially_loaded', False)
            streaming.set_editor_property('initially_visible', False)
    unreal.GameplayStatics.flush_level_streaming(world)
    actors = actor_subsystem.get_all_level_actors()
    routes = sorted(str(a.get_editor_property('route_id')) for a in actors if isinstance(a, unreal.WarZonePortal))
    zones = sorted(str(a.get_editor_property('zone_id')) for a in actors if isinstance(a, unreal.WarZoneAnchor))
    if routes != sorted(receipt['portals']) or zones != sorted(receipt['zones']): raise RuntimeError('Routing coverage changed')
    if not before or root_state() != before: raise RuntimeError('Authored capital changed')
    if not level.set_current_level_by_name(main.stem) or not level.save_current_level(): raise RuntimeError('Attachment save failed')
    manifest['mainSha256'] = sha(receipt['map'])
    manifest['attached'] = True
    (directory/'zone-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    receipt.update(layer=manifest['layer'], assetLayer=receipt['layer'], partitionManifest='zone-manifest.json',
                   runtimeTraversalVerified=False, capitalSha256After=manifest['mainSha256'])
    (directory/'build.json').write_text(json.dumps(receipt, indent=2)+'\n')
    unreal.log('WAR_WORLD_PARTITION_ATTACHED='+str(len(manifest['zones'])))
