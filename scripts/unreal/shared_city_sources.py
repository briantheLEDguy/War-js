"""Resolve and verify the single published city contract without loading Unreal."""
import hashlib
import json
import re
from pathlib import Path

CITIES = ('aegis_capital', 'riftspire_capital')
RECEIPT = 'artifacts/unreal/shared-cities/current.json'
REVIEWED_ENGINE_SOURCE = '/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst'


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def can_preserve_siege_review(previous_city, city, review, overlay_hash):
    return (previous_city.get('revision') == city['revision']
            and review.get('revision') == city['revision']
            and review.get('mapSha256') == overlay_hash
            and review.get('layers') == city['sceneryLevels'])


def package_file(root, package):
    if not isinstance(package, str) or not package.startswith('/Game/') or any(
            part in ('', '.', '..') for part in package[6:].split('/')) or '\\' in package:
        raise ValueError('Invalid city package: ' + str(package))
    content = (root / 'unreal/AegisWar/Content').resolve()
    base = content / package[6:].split('.')[0]
    base.resolve().relative_to(content)
    for suffix in ('.umap', '.uasset'):
        file = base.with_suffix(suffix)
        if file.is_file():
            return file
    raise ValueError('Missing native package: ' + package)


def protected_source_file(root, package, expected, engine_root=None):
    """The reviewed cloud parent is read-only input, never a city-owned package."""
    if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected):
        raise ValueError('Invalid protected city source hash.')
    if isinstance(package, str) and package.startswith('/Engine/'):
        if package != REVIEWED_ENGINE_SOURCE:
            raise ValueError('Unreviewed Engine city source is forbidden.')
        from citadel_performance_evidence import performance_package_file
        return performance_package_file(root, package, engine_root)
    return package_file(root, package)


def routing(root):
    directory = root / 'artifacts/unreal/world-portals'
    build = json.loads((directory / 'build.json').read_text())
    manifest_file = (directory / build['partitionManifest']).resolve()
    manifest_file.relative_to(directory.resolve())
    manifest = json.loads(manifest_file.read_text())
    config = root / 'unreal/AegisWar/Config/DefaultEngine.ini'
    defaults = [line.split('=', 1)[1].strip().split('.')[0]
                for line in config.read_text().splitlines() if line.startswith('GameDefaultMap=')]
    if defaults != [build['map']]:
        raise ValueError('Active startup map differs from city routing.')
    return build, manifest, manifest_file


def source_plan(root, engine_root=None):
    build, manifest, _ = routing(root)
    receipt = json.loads((root / RECEIPT).read_text())
    if receipt.get('schemaVersion') != 1 or receipt.get('campaignMap') != build['map']:
        raise ValueError('Shared city routing is stale; run unreal:city-sync.')
    cities = receipt.get('cities', [])
    if [row['id'] for row in cities] != list(CITIES):
        raise ValueError('Both shared capital definitions are required.')
    for city in cities:
        zone = next(z for z in manifest['zones'] if z['id'] == city['id'])
        scenery, gameplay = city['sceneryLevels'], city['gameplayLevels']
        if (not scenery or len(set(scenery + gameplay)) != len(scenery + gameplay)
                or zone.get('cityDefinition') != city['definition'] or zone.get('cityRevision') != city['revision']
                or zone['origin'] != city['origin'] or sorted(zone['levels'].values()) != sorted(scenery + gameplay)):
            raise ValueError('Shared city routing is stale or duplicated: ' + city['id'])
        expected = city['packageHashes']
        if any(package not in expected for package in [city['definition'], *scenery, *gameplay]):
            raise ValueError('Shared city package evidence is incomplete.')
        if not city.get('dependencyHashes'):
            raise ValueError('City model dependency evidence is missing.')
        for package, sha in expected.items():
            if digest(package_file(root, package)) != sha:
                raise ValueError('Changed native city package: ' + package)
        for package, sha in city['dependencyHashes'].items():
            if package in expected and expected[package] != sha:
                raise ValueError('Conflicting native city source hash: ' + package)
            if digest(protected_source_file(root, package, sha, engine_root)) != sha:
                raise ValueError('Changed native city source: ' + package)
    if any(p not in receipt.get('campaignHashes', {}) for p in (build['map'], build['layer'])):
        raise ValueError('City routing package evidence is missing.')
    for package, sha in receipt['campaignHashes'].items():
        if digest(package_file(root, package)) != sha:
            raise ValueError('Changed city routing package: ' + package)
    return dict(cities=cities, campaignMap=build['map'])


if __name__ == '__main__':
    import sys
    try:
        source_plan(Path(__file__).resolve().parents[2])
        print('Shared city sources are current.')
    except (ValueError, KeyError, StopIteration, OSError) as error:
        print(str(error))
        sys.exit(1)
