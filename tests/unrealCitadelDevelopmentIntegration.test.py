"""Portable guards for a normal Development selection; no native asset writes."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from citadel_development_integration import development_manifests, integration_packages, selected_config


class DevelopmentIntegrationTests(unittest.TestCase):
    def fixture(self):
        packages = integration_packages('62df5e965e66')
        old = dict(id='aegis_capital', definition='/Game/OldCity', revision='old', origin=[0, 0, 0],
                   sceneryLevels=['/Game/OldScenery'], gameplayLevels=['/Game/Services'])
        other = dict(id='riftspire_capital', marker={'nested': 'preserved'})
        build = dict(map='/Game/OldMap', layer='/Game/OldRouting', marker={'camera': 'preserved'})
        manifest = dict(mainMap=build['map'], layer=build['layer'],
            zones=[dict(id=old['id'], cityDefinition=old['definition'], cityRevision=old['revision'],
                        levels=dict(scenery=old['sceneryLevels'][0], services=old['gameplayLevels'][0])),
                   dict(id='other_zone', marker={'portal': 'preserved'})],
            packageHashes={build['layer']: 'a'*64, '/Game/OldScenery': 'b'*64, '/Game/OtherZone': 'c'*64})
        receipt = dict(schemaVersion=1, campaignMap=build['map'], cities=[old, other], releaseApproved=True)
        city = dict(id=old['id'], definition='/Game/NewCity', revision='e'*64, origin=[0, 0, 0],
                    sceneryLevels=['/Game/NewScenery'], dependencyHashes={'/Game/Model': 'f'*64})
        gameplay = ['/Game/Services', '/Game/LiveOverlay', packages['population']]
        hashes = {package: 'd'*64 for package in [packages['map'], packages['routing'], city['definition'],
                                                 *city['sceneryLevels'], *gameplay]}
        return build, manifest, receipt, city, gameplay, packages, hashes

    def test_preserves_unrelated_zones_services_and_inputs(self):
        inputs = self.fixture()
        originals = copy.deepcopy(inputs)
        build, manifest, receipt = development_manifests(*inputs)
        self.assertEqual(inputs, originals)
        self.assertEqual(manifest['zones'][1], originals[1]['zones'][1])
        self.assertEqual(receipt['cities'][1], originals[2]['cities'][1])
        self.assertEqual(build['marker'], originals[0]['marker'])
        self.assertIn('/Game/Services', receipt['cities'][0]['gameplayLevels'])
        self.assertEqual(manifest['packageHashes']['/Game/OtherZone'], 'c'*64)

    def test_development_selection_never_transfers_approval(self):
        build, manifest, receipt = development_manifests(*self.fixture())
        self.assertFalse(build['runtimeTraversalVerified'])
        self.assertFalse(build['visualApproved'])
        self.assertFalse(manifest['productionAccepted'])
        self.assertFalse(receipt['releaseApproved'])
        self.assertTrue(build['developmentOnly'] and manifest['developmentOnly'] and receipt['developmentOnly'])

    def test_rejects_lost_services_duplicate_layers_and_missing_hashes(self):
        for kind in ('lost_service', 'duplicate', 'scenery_overlap', 'missing_hash', 'bad_hash', 'lost_residents'):
            values = list(self.fixture())
            if kind == 'lost_service': values[4].remove('/Game/Services')
            if kind == 'duplicate': values[4].append('/Game/Services')
            if kind == 'scenery_overlap': values[4].append('/Game/NewScenery')
            if kind == 'missing_hash': values[6].pop('/Game/Services')
            if kind == 'bad_hash': values[6]['/Game/Services'] = 'bad'
            if kind == 'lost_residents': values[4].remove(values[5]['population'])
            with self.subTest(kind=kind), self.assertRaises(ValueError): development_manifests(*values)

    def test_rejects_stale_prior_binding_or_changed_capital_origin(self):
        for kind in ('map', 'routing', 'definition', 'revision', 'origin', 'service'):
            values = list(self.fixture())
            if kind == 'map': values[2]['campaignMap'] = '/Game/Changed'
            if kind == 'routing': values[1]['layer'] = '/Game/Changed'
            if kind == 'definition': values[1]['zones'][0]['cityDefinition'] = '/Game/Changed'
            if kind == 'revision': values[1]['zones'][0]['cityRevision'] = 'changed'
            if kind == 'origin': values[3]['origin'] = [1, 0, 0]
            if kind == 'service': values[1]['zones'][0]['levels']['services'] = '/Game/Changed'
            with self.subTest(kind=kind), self.assertRaises(ValueError): development_manifests(*values)

    def test_default_selection_preserves_crlf_and_all_unrelated_bytes(self):
        before = b'[Maps]\r\nGameDefaultMap=/Game/Old\r\nEditorStartupMap=/Game/Old\r\n[Online]\r\nbEnabled=false\r\n'
        after = selected_config(before, '/Game/Old', '/Game/New')
        self.assertEqual(after, before.replace(b'/Game/Old', b'/Game/New'))
        for bad in (before.replace(b'GameDefaultMap=/Game/Old', b'GameDefaultMap=/Game/Changed'),
                    before + b'GameDefaultMap=/Game/Old\r\n', before.replace(b'EditorStartupMap=/Game/Old\r\n', b'')):
            with self.assertRaisesRegex(ValueError, 'Startup'): selected_config(bad, '/Game/Old', '/Game/New')

    def test_requires_confined_exact_revision_and_supported_gm_map(self):
        self.assertTrue(integration_packages('62df5e965e66')['map'].endswith('/CampaignCandidate'))
        for value in ('', '../escape', '62DF5e965e66', '62df5e965e66/Other', 62):
            with self.subTest(value=value), self.assertRaises(ValueError): integration_packages(value)

    def test_commented_and_longer_occurrences_cannot_consume_default_replacement(self):
        earlier = b'; GameDefaultMap=/Game/Old\r\nOther=GameDefaultMap=/Game/OldSuffix\n'
        defaults = b'GameDefaultMap=/Game/Old\r\nEditorStartupMap=/Game/Old\n'
        self.assertEqual(selected_config(earlier + defaults, '/Game/Old', '/Game/New'),
                         earlier + defaults.replace(b'/Game/Old', b'/Game/New'))


if __name__ == '__main__': unittest.main()
