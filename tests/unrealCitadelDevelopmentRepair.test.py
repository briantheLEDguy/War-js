"""Focused controls for reconciling actual repaired development map hashes."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from citadel_development_repair import ACTIVE_FILES, apply_reconciliation, content_key, reconciled_manifests


def fixture():
    root = '/Game/WorldRebuild/AegisCitadel_62df5e965e66/'
    campaign, overlay, router, city = [root + p for p in ('CampaignCandidate', 'CampaignSiegeOverlay', 'CampaignRoutingCandidate', 'City')]
    revision = 'c' * 64
    before = {content_key(p) + '.umap': 'a' * 64 for p in (campaign, overlay, router)}
    before[content_key(city) + '.uasset'] = 'd' * 64
    after = dict(before)
    for p in (campaign, overlay): after[content_key(p) + '.umap'] = 'b' * 64
    nav = dict(actors=[dict(profile=p, package=campaign, registered=True, needsRebuild=False,
                           activeTiles=20, tileSnapshot=p + '|exact-tile-bytes') for p in ('Default', 'SiegeConvoy')])
    repair = dict(version=1, mode='repair', map=campaign, overlay=overlay, cityRevision=revision,
        completed=True, coldReloadVerified=True, productionAdmission=False, stagePid=123, verifyPid=456,
        beforePackageHashes=before, afterPackageHashes=after, builtNav=nav, coldReloadNav=copy.deepcopy(nav),
        rebuild=dict(passed=True, rebuilt=True, productionAdmission=False))
    shared = dict(schemaVersion=1, campaignMap=campaign, releaseApproved=False, developmentOnly=True,
        campaignHashes={campaign: 'a' * 64, router: 'a' * 64}, cities=[dict(id='aegis_capital', definition=city,
        revision=revision, packageHashes={overlay: 'a' * 64, city: 'd' * 64}, sceneryLevels=['retained'])])
    build = dict(map=campaign, capitalSha256After='a' * 64, capitalSha256Before='e' * 64,
        partitionManifest='zone-manifest.json', runtimeTraversalVerified=True, visualApproved=False,
        developmentOnly=True, portals=['retained-route'])
    partition = dict(mainMap=campaign, mainSha256='a' * 64, developmentOnly=True, productionAccepted=False,
        packageHashes={campaign: 'a' * 64, overlay: 'a' * 64, router: 'a' * 64},
        preservedStateSha256='f' * 64, zones=['retained-zone'])
    return shared, build, partition, repair


class DevelopmentRepairTests(unittest.TestCase):
    def test_journaled_application_preserves_raw_backups_and_rejects_changed_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); data = fixture(); shared, build, partition, repair = data
            journal = root / 'artifacts/unreal/repair/native.json'
            journal.parent.mkdir(parents=True)
            digest = lambda value: hashlib.sha256(value).hexdigest()
            for key in list(repair['beforePackageHashes']):
                old = key.encode(); new = old + b' repaired' if 'CampaignCandidate.umap' in key or 'CampaignSiegeOverlay.umap' in key else old
                repair['beforePackageHashes'][key] = digest(old); repair['afterPackageHashes'][key] = digest(new)
                path = root / key; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(new)
                if old != new:
                    backup = journal.parent / path.name; backup.write_bytes(old)
                    repair.setdefault('rollback', {})[key] = dict(file=backup.relative_to(root).as_posix(), sha256=digest(old))
            for hashes in [shared['campaignHashes'], shared['cities'][0]['packageHashes'], partition['packageHashes']]:
                for package in hashes:
                    stem = content_key(package)
                    key = next(key for key in repair['beforePackageHashes'] if key in (stem + '.umap', stem + '.uasset'))
                    hashes[package] = repair['beforePackageHashes'][key]
            build['capitalSha256After'] = partition['mainSha256'] = shared['campaignHashes'][repair['map']]
            originals = []
            for name, value in zip(ACTIVE_FILES, data[:3]):
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
                raw = json.dumps(value).encode(); path.write_bytes(raw); originals.append(raw)
            journal.write_text(json.dumps(repair), encoding='utf-8')
            historical = journal.parent / 'historical-proof.json'; historical.write_bytes(b'original historical proof')
            directory = root / 'artifacts/unreal/reconciliation'
            receipt = apply_reconciliation(root, journal, directory)
            self.assertTrue(receipt['completed'])
            for index, raw in enumerate(originals): self.assertEqual((directory / ('manifest-' + str(index) + '.json')).read_bytes(), raw)
            self.assertEqual(historical.read_bytes(), b'original historical proof')
            self.assertEqual(apply_reconciliation(root, journal, directory), receipt)
            target = root / ACTIVE_FILES[0]; target.write_bytes(target.read_bytes() + b' ')
            with self.assertRaises(ValueError): apply_reconciliation(root, journal, directory)
            self.assertTrue(target.read_bytes().endswith(b' '))

    def test_updates_only_repaired_hashes_without_retroactive_proof_claims(self):
        inputs = fixture(); original = copy.deepcopy(inputs)
        shared, build, partition = reconciled_manifests(*inputs)
        self.assertEqual(inputs, original)
        campaign, overlay = inputs[3]['map'], inputs[3]['overlay']
        self.assertEqual(shared['campaignHashes'][campaign], 'b' * 64)
        self.assertEqual(shared['cities'][0]['packageHashes'][overlay], 'b' * 64)
        self.assertEqual(partition['packageHashes'][overlay], 'b' * 64)
        self.assertEqual(build['capitalSha256After'], partition['mainSha256'])
        self.assertEqual(build['capitalSha256Before'], original[1]['capitalSha256Before'])
        self.assertEqual(partition['preservedStateSha256'], original[2]['preservedStateSha256'])
        self.assertEqual(build['portals'], original[1]['portals'])
        self.assertEqual(partition['zones'], original[2]['zones'])
        self.assertFalse(build['runtimeTraversalVerified'])
        for manifest in (shared, build, partition):
            self.assertFalse(manifest['developmentRepair']['nativeGameVerified'])
            self.assertFalse(manifest['developmentRepair']['productionAdmission'])
        with self.assertRaises(ValueError): reconciled_manifests(shared, build, partition, inputs[3])

    def test_rejects_unverified_incomplete_or_broader_content_mutations(self):
        for kind in ('cold', 'completed', 'pid', 'admission', 'third_package', 'added_package', 'missing_package', 'hash'):
            data = fixture(); r = data[3]
            key = next(k for k in r['afterPackageHashes'] if 'CampaignRoutingCandidate' in k)
            if kind == 'cold': r['coldReloadVerified'] = False
            if kind == 'completed': r['completed'] = False
            if kind == 'pid': r['verifyPid'] = r['stagePid']
            if kind == 'admission': r['productionAdmission'] = True
            if kind == 'third_package': r['afterPackageHashes'][key] = 'f' * 64
            if kind == 'added_package': r['afterPackageHashes'][key + '.extra'] = 'f' * 64
            if kind == 'missing_package': r['afterPackageHashes'].pop(key)
            if kind == 'hash': r['afterPackageHashes'][key] = 'invalid'
            with self.subTest(kind=kind), self.assertRaises(ValueError): reconciled_manifests(*data)

    def test_rejects_empty_unregistered_or_different_cold_tile_payloads(self):
        for kind in ('empty', 'unregistered', 'rebuild', 'changed_tile', 'missing_convoy', 'wrong_owner'):
            data = fixture(); r = data[3]; row = r['builtNav']['actors'][0]
            if kind == 'empty': row['activeTiles'] = 0
            if kind == 'unregistered': row['registered'] = False
            if kind == 'rebuild': row['needsRebuild'] = True
            if kind == 'changed_tile': r['coldReloadNav']['actors'][0]['tileSnapshot'] += '|changed'
            if kind == 'missing_convoy': r['builtNav']['actors'].pop()
            if kind == 'wrong_owner': row['package'] = r['overlay']
            if kind != 'changed_tile': r['coldReloadNav'] = copy.deepcopy(r['builtNav'])
            with self.subTest(kind=kind), self.assertRaises(ValueError): reconciled_manifests(*data)

    def test_preserves_stale_changed_or_wrong_active_manifests(self):
        for kind in ('map', 'overlay', 'city', 'stale', 'portal_hash', 'partition_hash', 'release', 'existing_repair'):
            data = fixture(); shared, build, partition, r = data
            if kind == 'map': build['map'] = '/Game/Capitals/AegisCapital'
            if kind == 'overlay': r['overlay'] = r['overlay'].replace('62df5e965e66', '000000000000')
            if kind == 'city': shared['cities'][0]['revision'] = '0' * 64
            if kind == 'stale': shared['campaignHashes'][r['map']] = 'f' * 64
            if kind == 'portal_hash': build['capitalSha256After'] = 'f' * 64
            if kind == 'partition_hash': partition['packageHashes'][r['overlay']] = 'f' * 64
            if kind == 'release': partition['productionAccepted'] = True
            if kind == 'existing_repair': shared['developmentRepair'] = {}
            with self.subTest(kind=kind), self.assertRaises(ValueError): reconciled_manifests(*data)

    def test_reports_and_preserves_unrelated_preexisting_manifest_mismatches(self):
        data = fixture(); partition, repair = data[2:]
        router = repair['map'].rsplit('/', 1)[0] + '/CampaignRoutingCandidate'
        partition['packageHashes'][router] = 'f' * 64
        result = reconciled_manifests(*data)[2]
        self.assertEqual(result['packageHashes'][router], 'f' * 64)
        self.assertEqual(result['developmentRepair']['preservedPreexistingManifestMismatches'], [
            dict(package=router, recordedSha256='f' * 64, installedBeforeSha256='a' * 64)])


if __name__ == '__main__': unittest.main()
