"""Reconcile active development hashes after a separately verified two-map repair."""
import copy
import re
import hashlib
import json
import os
from pathlib import Path


def content_key(package):
    if not isinstance(package, str) or not package.startswith('/Game/') or '..' in package.split('/'):
        raise ValueError('An exact Game package is required')
    return 'unreal/AegisWar/Content/' + package[6:]


def reconciled_manifests(shared, build, partition, repair):
    """Return new manifests without rewriting any original proof or admission."""
    campaign, overlay = repair.get('map'), repair.get('overlay')
    match = re.fullmatch(r'/Game/WorldRebuild/AegisCitadel_([a-f0-9]{12})/CampaignCandidate', campaign or '')
    if not match or overlay != campaign.rsplit('/', 1)[0] + '/CampaignSiegeOverlay':
        raise ValueError('Only the exact private campaign pair may be reconciled')
    if (repair.get('version') != 1 or repair.get('mode') != 'repair'
            or repair.get('completed') is not True or repair.get('coldReloadVerified') is not True
            or repair.get('productionAdmission') is not False
            or type(repair.get('stagePid')) is not int or repair['stagePid'] <= 0
            or type(repair.get('verifyPid')) is not int or repair['verifyPid'] <= 0
            or repair['stagePid'] == repair['verifyPid']):
        raise ValueError('Completed repair and independent cold reload are required with admission closed')
    before, after = repair.get('beforePackageHashes'), repair.get('afterPackageHashes')
    pair = {p: content_key(p) + '.umap' for p in (campaign, overlay)}
    if not isinstance(before, dict) or not isinstance(after, dict) or not before or before.keys() != after.keys():
        raise ValueError('Complete unchanged Content inventories are required')
    if {p for p in before if before[p] != after[p]} != set(pair.values()):
        raise ValueError('Only the campaign and overlay package bytes may change')
    if any(not isinstance(h, str) or not re.fullmatch('[a-f0-9]{64}', h) for h in [*before.values(), *after.values()]):
        raise ValueError('Every Content hash must be a SHA-256 identity')
    rebuilt = repair.get('rebuild', {})
    built, cold = repair.get('builtNav'), repair.get('coldReloadNav')
    if (rebuilt.get('passed') is not True or rebuilt.get('rebuilt') is not True
            or rebuilt.get('productionAdmission') is not False or not isinstance(built, dict)
            or built != cold or len(built.get('actors', [])) != 2
            or {r.get('profile') for r in built['actors']} != {'Default', 'SiegeConvoy'}):
        raise ValueError('Both exact rebuilt tile payloads must survive cold reload')
    for row in built['actors']:
        if (row.get('package') != campaign or row.get('registered') is not True
                or row.get('needsRebuild') is not False or type(row.get('activeTiles')) is not int
                or row['activeTiles'] <= 0 or not isinstance(row.get('tileSnapshot'), str) or not row['tileSnapshot']):
            raise ValueError('Cold navigation needs registered positive tile payloads')
    if (shared.get('campaignMap') != campaign or build.get('map') != campaign or partition.get('mainMap') != campaign
            or build.get('partitionManifest') != 'zone-manifest.json'
            or shared.get('releaseApproved') is not False or partition.get('productionAccepted') is not False
            or any(m.get('developmentOnly') is not True for m in (shared, build, partition))
            or any('developmentRepair' in m for m in (shared, build, partition))
            or build.get('visualApproved') is not False):
        raise ValueError('Only matching active development manifests with closed acceptance may change')
    cities = shared.get('cities', [])
    matches = [r for r in cities if r.get('id') == 'aegis_capital']
    if (len(matches) != 1 or matches[0].get('revision') != repair.get('cityRevision')
            or matches[0].get('definition') != campaign.rsplit('/', 1)[0] + '/City'):
        raise ValueError('The existing exact Aegis city definition must remain bound')

    preexisting_mismatches = []

    def check_hashes(hashes):
        if not isinstance(hashes, dict): raise ValueError('Existing package hashes are required')
        for package, expected in hashes.items():
            stem = content_key(package)
            files = [p for p in (stem + '.umap', stem + '.uasset') if p in before]
            if len(files) != 1 or before[files[0]] != expected:
                if package in pair:
                    raise ValueError('Preserve stale or independently changed active repair bindings')
                mismatch = dict(package=package, recordedSha256=expected,
                    installedBeforeSha256=before[files[0]] if len(files) == 1 else None)
                if mismatch not in preexisting_mismatches: preexisting_mismatches.append(mismatch)

    for hashes in (shared.get('campaignHashes'), partition.get('packageHashes')):
        check_hashes(hashes)
    for city in cities: check_hashes(city.get('packageHashes'))
    if (shared['campaignHashes'].get(campaign) != before[pair[campaign]]
            or matches[0]['packageHashes'].get(overlay) != before[pair[overlay]]
            or build.get('capitalSha256After') != before[pair[campaign]]
            or partition.get('mainSha256') != before[pair[campaign]]
            or any(partition['packageHashes'].get(p) != before[key] for p, key in pair.items())):
        raise ValueError('All active campaign and overlay bindings must still match original bytes')
    results = copy.deepcopy((shared, build, partition))
    new_shared, new_build, new_partition = results
    new_shared['campaignHashes'][campaign] = after[pair[campaign]]
    next(r for r in new_shared['cities'] if r['id'] == 'aegis_capital')['packageHashes'][overlay] = after[pair[overlay]]
    new_build['capitalSha256After'] = after[pair[campaign]]
    new_build['runtimeTraversalVerified'] = False
    new_partition['mainSha256'] = after[pair[campaign]]
    for package, key in pair.items(): new_partition['packageHashes'][package] = after[key]
    provenance = dict(version=1, changedPackages=list(pair), coldReloadVerified=True,
        originalPackageHashes={p: before[key] for p, key in pair.items()},
        packageHashes={p: after[key] for p, key in pair.items()},
        preservedPreexistingManifestMismatches=preexisting_mismatches,
        nativeGameVerified=False, runtimeTraversalVerified=False, visualApproved=False, productionAdmission=False)
    for result in results: result['developmentRepair'] = copy.deepcopy(provenance)
    return results


ACTIVE_FILES = ('artifacts/unreal/shared-cities/current.json', 'artifacts/unreal/world-portals/build.json',
                'artifacts/unreal/world-portals/zone-manifest.json')


def apply_reconciliation(repository, journal_path, receipt_directory):
    """Back up active manifests and journal every atomic replacement; never touch Content."""
    root, journal_path, directory = [Path(p).resolve() for p in (repository, journal_path, receipt_directory)]
    if not journal_path.is_relative_to(root / 'artifacts/unreal') or not directory.is_relative_to(root / 'artifacts/unreal'):
        raise ValueError('Repair evidence and rollback must stay under repository Unreal artifacts')
    if directory == journal_path.parent:
        raise ValueError('Use a separate reconciliation evidence directory')
    paths = [root / name for name in ACTIVE_FILES]
    if any(p.is_symlink() or not p.resolve().is_relative_to(root) for p in paths):
        raise ValueError('Active manifests must remain ordinary repository files')
    digest = lambda data: hashlib.sha256(data).hexdigest()
    receipt_path = directory / 'receipt.json'

    def write(path, data):
        temporary = path.with_name(path.name + '.repair-tmp')
        with temporary.open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)

    def encoded(value): return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')

    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_bytes())
        if receipt.get('completed') is not True:
            raise ValueError('Interrupted reconciliation exists; preserve its rollback and inspect before retrying')
        if (receipt.get('activeFiles') != list(ACTIVE_FILES)
                or not isinstance(receipt.get('afterManifestHashes'), list) or len(receipt['afterManifestHashes']) != len(paths)
                or any(digest(p.read_bytes()) != h for p, h in zip(paths, receipt['afterManifestHashes']))):
            raise ValueError('Preserve independently changed active manifests')
        snapshot = (directory / 'repair-journal.json').read_bytes()
        if digest(snapshot) != receipt['repairJournalSha256']:
            raise ValueError('Preserve changed reconciliation evidence')
        repair = json.loads(snapshot)
        for package in (repair['map'], repair['overlay']):
            key = content_key(package) + '.umap'
            if digest((root / key).read_bytes()) != repair['afterPackageHashes'][key]:
                raise ValueError('Repaired package bytes changed since reconciliation')
        return receipt
    if directory.exists(): raise ValueError('Preserve an existing or incomplete evidence directory')
    original = [p.read_bytes() for p in paths]
    journal_bytes = journal_path.read_bytes(); repair = json.loads(journal_bytes)
    results = reconciled_manifests(*(json.loads(data) for data in original), repair)
    for package in (repair['map'], repair['overlay']):
        key = content_key(package) + '.umap'
        if digest((root / key).read_bytes()) != repair['afterPackageHashes'][key]:
            raise ValueError('Actual repaired package bytes differ from cold verification')
        rollback = repair.get('rollback', {}).get(key, {})
        backup = (root / rollback.get('file', '')).resolve()
        if (not backup.is_relative_to(root / 'artifacts/unreal') or not backup.is_file()
                or digest(backup.read_bytes()) != repair['beforePackageHashes'][key]
                or rollback.get('sha256') != repair['beforePackageHashes'][key]):
            raise ValueError('Exact original map rollback bytes are required')
    replacements = [encoded(value) for value in results]
    directory.mkdir(parents=True)
    for index, data in enumerate(original): (directory / ('manifest-' + str(index) + '.json')).write_bytes(data)
    (directory / 'repair-journal.json').write_bytes(journal_bytes)
    receipt = dict(version=1, activeFiles=list(ACTIVE_FILES), completed=False,
        beforeManifestHashes=[digest(data) for data in original], afterManifestHashes=[digest(data) for data in replacements],
        repairJournalSha256=digest(journal_bytes), nativeGameVerified=False, productionAdmission=False,
        preservedPreexistingManifestMismatches=results[0]['developmentRepair']['preservedPreexistingManifestMismatches'])
    write(receipt_path, encoded(receipt))
    if journal_path.read_bytes() != journal_bytes or any(p.read_bytes() != data for p, data in zip(paths, original)):
        raise ValueError('Repair evidence or manifests changed during preflight; no manifest replaced')
    for path, data in zip(paths, replacements): write(path, data)
    if any(p.read_bytes() != data for p, data in zip(paths, replacements)):
        raise ValueError('Manifest replacement failed; retain rollback before any further changes')
    receipt['completed'] = True
    write(receipt_path, encoded(receipt))
    return receipt


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repair_journal', type=Path)
    parser.add_argument('receipt_directory', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(apply_reconciliation(Path(__file__).resolve().parents[2], args.repair_journal,
                                             args.receipt_directory), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
