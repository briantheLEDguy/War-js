"""Build navigation only in a receipted isolated citadel candidate.

Navigation availability is recorded separately from physical traversal, visual
review and admission. Published worlds and their existing edits are untouched.
"""
import json
import sys
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT, sha, validate, cloud_material_file
from aegis_citadel_lighting import REVIEWED_CLOUD_MATERIAL
from shared_city_sources import package_file
from citadel_stage_contract import require_final_city_hashes


def write(file, value):
    temporary = file.with_suffix(file.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(file)

current = json.loads((OUT / 'current.json').read_text())
directory = OUT / current['revision']
blueprint = json.loads((directory / 'blueprint.json').read_text())
validate(blueprint)
receipt_file = directory / 'candidate.json'
receipt = json.loads(receipt_file.read_text())


def source_package_file(package):
    # The bundled cloud parent is a read-only source dependency, never an owned
    # candidate package. Keep every other Engine path outside this exception.
    if package == REVIEWED_CLOUD_MATERIAL:
        parent = blueprint['lightingTreatment']['cloudFixture']['material']
        if parent['package'] != package or receipt['sourceHashes'].get(package) != parent['sha256']:
            raise RuntimeError('Protected cloud source differs from the signed recipe')
        return cloud_material_file()
    return package_file(ROOT, package)


target = '/Game/WorldRebuild/AegisCitadel_' + blueprint['revision'] + '/SiegeCandidate'
if receipt['signature'] != blueprint['signature'] or receipt['siegeMap'] != target or receipt['published']:
    raise RuntimeError('Only the current isolated candidate may be rebuilt')
require_final_city_hashes(receipt['city'], receipt['packageHashes'], receipt['sourceHashes'])
for name, expected in receipt.get('stageDependencySha256', {}).items():
    file = (ROOT / 'scripts/unreal' / name).resolve()
    file.relative_to((ROOT / 'scripts/unreal').resolve())
    if sha(file) != expected:
        raise RuntimeError('Candidate staging dependency changed before navigation')
if not receipt.get('stageDependencySha256', {}).get('citadel_stage_contract.py'):
    raise RuntimeError('Candidate staging dependency provenance is missing')
for package, expected in receipt['packageHashes'].items():
    if sha(package_file(ROOT, package)) != expected:
        raise RuntimeError('Preserve independently edited candidate: ' + package)
for package, expected in receipt['sourceHashes'].items():
    if sha(source_package_file(package)) != expected:
        raise RuntimeError('Published source changed; re-survey before navigation')

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level(target):
    raise RuntimeError('Native citadel candidate is unavailable')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
if not levels.set_current_level_by_name('SiegeCandidate'):
    raise RuntimeError('Cannot select the owned candidate overlay')
fields = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.WarSiegeBattlefield)]
if len(fields) != 1:
    raise RuntimeError('Expected exactly one isolated battlefield definition')
field = fields[0]
if field.get_editor_property('definition_version') != 2:
    raise RuntimeError('Navigation requires the eight-anchor v2 battlefield')

# Cover the retained lower city and the expanded hall, including high galleries.
if not unreal.WarSiegeAuthoringLibrary.build_navigation(
        world, unreal.Vector(9000, 0, 6500), unreal.Vector(35000, 18000, 12500)):
    raise RuntimeError('Native navigation could not start')
if unreal.WarSiegeAuthoringLibrary.navigation_busy(world):
    raise RuntimeError('Navigation is incomplete; do not save unfinished data')
points = []
for point in blueprint['objectives'] + blueprint['optionalObjectives'] + blueprint['teamSpawns'] + [
        p for route in blueprint['routes'] for p in route['points']] + [
        p for row in blueprint.get('spawnApproaches',[]) for p in row['points']]:
    if point not in points:
        points.append(point)
probe = unreal.WarSiegeAuthoringLibrary.probe_navigation(world, [unreal.Vector(*p) for p in points])
rows = [row for row in probe.splitlines() if row.strip()]
reachable = len(rows) == len(points) and all('projected=1 connected=1' in row for row in rows)
report = dict(schemaVersion=1, map=target, signature=blueprint['signature'], points=points,
              probe=probe, anchorsReachable=reachable, physicalTraversalVerified=False,
              convoyVerified=False, fullSiegeApproved=False, visualApproved=False,
              releaseAcceptance=False, passed=reachable, cityRevision=receipt['city']['revision'])
if not reachable:
    write(directory / 'navigation-diagnostic.json', report)
    raise RuntimeError('A ledger waypoint is unreachable; inspect candidate navigation-diagnostic.json')
if not levels.save_current_level():
    raise RuntimeError('Cannot save completed candidate navigation')
for package, expected in receipt['sourceHashes'].items():
    if sha(source_package_file(package)) != expected:
        raise RuntimeError('Published sources changed during isolated navigation')
for package, expected in receipt['packageHashes'].items():
    if package != target and sha(package_file(ROOT, package)) != expected:
        raise RuntimeError('Non-navigation candidate package changed during Save: ' + package)
for package, expected in receipt['city']['dependencyHashes'].items():
    if sha(source_package_file(package)) != expected:
        raise RuntimeError('Candidate model dependency changed during navigation: ' + package)
receipt['packageHashes'][target] = sha(package_file(ROOT, target))
require_final_city_hashes(receipt['city'], receipt['packageHashes'], receipt['sourceHashes'])
report.update(mapSha256=receipt['packageHashes'][target], packageHashes=dict(receipt['packageHashes']))
prepared = directory / 'publication-candidate.json'
if prepared.exists():
    staged = json.loads(prepared.read_text())
    if staged['revision'] != blueprint['revision'] or staged['published']:
        raise RuntimeError('Prepared routing belongs to another or published candidate')
    for package, expected in staged['sourceHashes'].items():
        if sha(source_package_file(package)) != expected:
            raise RuntimeError('Prepared routing source changed during isolated navigation: ' + package)
    for package, expected in staged['packageHashes'].items():
        if sha(package_file(ROOT, package)) != expected:
            raise RuntimeError('Prepared routing changed during isolated navigation: ' + package)
    report['packageHashes'].update(staged['packageHashes'])
write(directory / 'navigation.json', report)
receipt['navigation'] = {'file': 'navigation.json', 'sha256': sha(directory / 'navigation.json'),
                        'cityRevision': report['cityRevision'], 'mapSha256': report['mapSha256']}
write(receipt_file, receipt)
unreal.log('WAR_CITADEL_NAVIGATION=' + str(directory / 'navigation.json'))
