"""Remove obsolete consumer copies only after native verification and reference checks."""
import json
import shutil
import sys
import time
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from shared_city_sources import source_plan, package_file, digest

plan = source_plan(ROOT)
verification = json.loads((ROOT / 'artifacts/unreal/shared-cities/native-verification.json').read_text())
if not verification.get('passed') or {r['city']: r['revision'] for r in verification['cities']} != {c['id']: c['revision'] for c in plan['cities']}:
    raise RuntimeError('Current native reference verification is required before cleanup')
assets = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
# Unload all consumers before checking and removing the now-unreferenced packages.
if not levels.load_level(plan['cities'][0]['sceneryLevels'][0]):
    raise RuntimeError('Cannot unload old consumer content')
candidates = set()
for folder in ('/Game/Capitals/Siege', '/Game/UI/Frontend/Materials'):
    for path in assets.list_assets(folder, recursive=True, include_folder=False):
        package = path.split('.')[0]
        if (package.startswith('/Game/Capitals/Siege/Scenery_') or package == '/Game/Capitals/Siege/AegisCityGeometry'
                or package.startswith('/Game/UI/Frontend/Materials/')):
            candidates.add(package)
unreal.log('WAR_SHARED_CITY_COPY_CANDIDATES=' + str(len(candidates)))
for package in sorted(candidates):
    references = {str(r).split('.')[0] for r in assets.find_package_referencers_for_asset(package)}
    external = references - candidates - {package}
    if external:
        references = {str(r).split('.')[0] for r in assets.find_package_referencers_for_asset(package, load_assets_to_confirm=True)}
        external = references - candidates - {package}
    if external:
        raise RuntimeError('Preserve referenced consumer copy: ' + package + ' referenced by ' + str(external))
backup = ROOT / 'artifacts/unreal/shared-cities' / ('removed-copies-' + str(time.time_ns()))
records = {}
for package in sorted(candidates):
    file = package_file(ROOT, package)
    target = backup / (package[6:] + file.suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, target)
    records[package] = digest(file)
backup.mkdir(parents=True, exist_ok=True)
(backup / 'packages.json').write_text(json.dumps(records, indent=2) + '\n')
# All saved referencers were checked together above. Batch deletion handles
# internal parent-material chains without repeating the loaded-object scan.
loaded = [assets.load_asset(package) for package in sorted(candidates)]
if any(asset is None for asset in loaded) or (loaded and not assets.delete_loaded_assets(loaded)):
    raise RuntimeError('Could not remove verified redundant copies; inspect the preserved backup')
if any(assets.does_asset_exist(p) for p in candidates):
    raise RuntimeError('Redundant package still present')
(backup / 'cleanup.json').write_text(json.dumps(dict(
    removed=sorted(candidates), backup=str(backup), currentRevisions={c['id']:c['revision'] for c in plan['cities']}), indent=2) + '\n')
if candidates:
    shutil.copy2(backup / 'cleanup.json', ROOT / 'artifacts/unreal/shared-cities/cleanup.json')
unreal.log('WAR_SHARED_CITY_COPIES_REMOVED=' + str(len(candidates)))
