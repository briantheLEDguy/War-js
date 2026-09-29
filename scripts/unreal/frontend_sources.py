"""Current capital snapshot inputs and freshness checks, without loading Unreal."""
import hashlib
import json
from pathlib import Path


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def package_file(root, package):
    if not isinstance(package, str) or not package.startswith('/Game/') or any(
            part in ('', '.', '..') for part in package[6:].split('/')) or '\\' in package:
        raise ValueError('Invalid frontend source package: ' + str(package))
    content = (root / 'unreal/AegisWar/Content').resolve()
    base = content / package[6:].split('.')[0]
    base.resolve().relative_to(content)
    for suffix in ('.umap', '.uasset'):
        file = base.with_suffix(suffix)
        if file.is_file():
            return file
    raise ValueError('Missing native package: ' + package)


def source_plan(root):
    directory = root / 'artifacts/unreal/world-portals'
    build = json.loads((directory / 'build.json').read_text())
    manifest_file = (directory / build['partitionManifest']).resolve()
    manifest_file.relative_to(directory.resolve())
    manifest = json.loads(manifest_file.read_text())
    config = root / 'unreal/AegisWar/Config/DefaultEngine.ini'
    default_maps = [line.split('=', 1)[1].strip().split('.')[0]
                    for line in config.read_text().splitlines() if line.startswith('GameDefaultMap=')]
    if default_maps != [build['map']]:
        raise ValueError('Active startup map differs from the world manifest; reconcile routing before refreshing the lobby.')
    cities = []
    for zone_id in ('aegis_capital', 'riftspire_capital'):
        zone = next(zone for zone in manifest['zones'] if zone['id'] == zone_id)
        layers = list(zone['levels'].values())
        if not layers:
            raise ValueError('Capital has no active layers: ' + zone_id)
        # The persistent shell contains legacy Aegis scenery; streamed actors are
        # filtered by their owning package during extraction to avoid duplication.
        maps = list(dict.fromkeys(([build['map']] if zone_id == 'aegis_capital' else []) + layers))
        for package in maps:
            package_file(root, package)
        cities.append(dict(id=zone_id, origin=zone['origin'], maps=maps))
    files = [directory / 'build.json', manifest_file, config,
             root / 'scripts/unreal/build-frontend-presentation.py',
             root / 'scripts/unreal/frontend_sources.py']
    return dict(cities=cities, inputs={file.relative_to(root).as_posix(): digest(file) for file in files})


def stale_reason(root, receipt):
    plan = source_plan(root)
    if receipt.get('schemaVersion') != 2 or receipt.get('sourcePlan') != plan:
        return 'Capital routing or snapshot recipe changed.'
    sources = receipt.get('sourcePackages', {})
    for city in plan['cities']:
        if any(package not in sources for package in city['maps']):
            return 'Snapshot omits an active capital layer.'
    outputs = receipt.get('outputPackages', {})
    if '/Game/UI/Frontend/CapitalPresentation' not in outputs:
        return 'Snapshot output evidence is missing.'
    for package, expected in {**sources, **outputs}.items():
        try:
            if digest(package_file(root, package)) != expected:
                return 'Changed native package: ' + package
        except ValueError:
            return 'Missing native package: ' + package
    return None


if __name__ == '__main__':
    import sys
    root = Path(__file__).resolve().parents[2]
    receipt_file = root / 'artifacts/unreal/frontend/build.json'
    try:
        receipt = json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
        reason = stale_reason(root, receipt)
        print(reason or 'Frontend capital snapshot is current.')
        sys.exit(1 if reason else 0)
    except (ValueError, KeyError, StopIteration, OSError) as error:
        print('Cannot resolve current capital sources: ' + str(error))
        sys.exit(2)
