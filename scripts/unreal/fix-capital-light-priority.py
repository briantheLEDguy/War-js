"""Assign the authored capital sun priority over its fill, preserving all other art settings."""
import configparser
import datetime
import hashlib
import json
import shutil
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/unreal/light-priority'
OUT.mkdir(parents=True, exist_ok=True)
config = configparser.ConfigParser(strict=False)
config.read(ROOT / 'unreal/AegisWar/Config/DefaultEngine.ini')
map_path = config['/Script/EngineSettings.GameMapsSettings']['GameDefaultMap']
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(map_path):
    raise RuntimeError('Cannot load the configured capital')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
lights = [actor for actor in actors if isinstance(actor, unreal.DirectionalLight)]
rows = [{'label': a.get_actor_label(), 'path': a.get_path_name(),
         'priority': a.light_component.get_editor_property('forward_shading_priority')}
        for a in lights]
(OUT / 'before.json').write_text(json.dumps(rows, indent=2))
sun = [a for a in lights if a.get_actor_label() == 'Aegis workbench sun']
fill = [a for a in lights if a.get_actor_label() == 'Crownward soft sky fill']
if len(sun) != 1 or len(fill) != 1:
    raise RuntimeError('Expected exactly one authored capital sun and fill; inspect before.json')
targets = [(sun[0], 1), (fill[0], 0)]
changes = [(a, p) for a, p in targets if a.light_component.get_editor_property('forward_shading_priority') != p]
packages = {}
stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
for actor, priority in changes:
    package = actor.get_outer().get_path_name().split('.')[0]
    if not package.startswith(('/Game/Capitals/', '/Game/WorldRebuild/')):
        raise RuntimeError('Unexpected light package: ' + package)
    file = ROOT / 'unreal/AegisWar/Content' / (package.removeprefix('/Game/') + '.umap')
    if package not in packages:
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        backup = OUT / (file.stem + '-' + stamp + '.umap')
        shutil.copy2(file, backup)
        packages[package] = {'file': file, 'beforeSha256': digest, 'backup': str(backup)}
    actor.modify()
    actor.light_component.modify()
    actor.light_component.set_editor_property('forward_shading_priority', priority)
for package, row in packages.items():
    if hashlib.sha256(row['file'].read_bytes()).hexdigest() != row['beforeSha256']:
        raise RuntimeError('Package changed during repair; refusing overwrite: ' + package)
    if not levels.set_current_level_by_name(package.rsplit('/', 1)[1]) or not levels.save_current_level():
        raise RuntimeError('Could not save light package: ' + package)
    row['afterSha256'] = hashlib.sha256(row.pop('file').read_bytes()).hexdigest()
# Keep the managed partition inventory consistent with the deliberately saved package.
build_path = ROOT / 'artifacts/unreal/world-portals/build.json'
if build_path.exists():
    build = json.loads(build_path.read_text())
    if build.get('partitionManifest'):
        manifest_path = build_path.parent / build['partitionManifest']
        manifest = json.loads(manifest_path.read_text())
        for package, row in packages.items():
            if package in manifest.get('packageHashes', {}):
                manifest['packageHashes'][package] = row['afterSha256']
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
for actor, priority in targets:
    assert actor.light_component.get_editor_property('forward_shading_priority') == priority
(OUT / 'result.json').write_text(json.dumps({'saved': True, 'map': map_path,
    'sunPriority': 1, 'fillPriority': 0, 'packages': packages}, indent=2))
