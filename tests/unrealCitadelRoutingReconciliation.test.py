import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from citadel_routing_reconciliation import reconciled_manifest


class RoutingReconciliationTests(unittest.TestCase):
    def fixture(self):
        staged = dict(published=False, baseBuild=dict(map='/Game/ExistingCampaign'),
            baseManifest=dict(zones=[dict(id='sunmeadow_march', levels=dict(generated='/Game/Sunmeadow')),
                                     dict(id='aegis_capital', levels=dict(scenery='/Game/Capital'))]),
            manifest=dict(packageHashes={'/Game/Sunmeadow': 'a'*64, '/Game/Capital': 'b'*64}),
            gmDrafts=dict(saved='unchanged'))
        network = dict(passed=True, twoClientStreaming=True, productionAccepted=False,
                       map='/Game/ExistingCampaign', packageHashes={'/Game/Sunmeadow': 'c'*64})
        observed = {'/Game/Sunmeadow': 'c'*64, '/Game/Capital': 'b'*64}
        return staged, network, observed

    def test_private_hash_reconciliation_preserves_original_receipt_and_gm(self):
        staged, network, observed = self.fixture()
        before = copy.deepcopy(staged)
        result, changes = reconciled_manifest(staged, network, observed)
        self.assertEqual(staged, before)
        self.assertEqual(result['baseManifest'], before['baseManifest'])
        self.assertEqual(result['gmDrafts'], before['gmDrafts'])
        self.assertEqual(result['manifest']['packageHashes'], observed)
        self.assertEqual(changes, [dict(package='/Game/Sunmeadow', recordedSha256='a'*64, retainedSha256='c'*64)])

    def test_unverified_changes_wrong_maps_and_capital_changes_fail_closed(self):
        for change in ('published', 'failed', 'map', 'production', 'streaming', 'hash', 'capital', 'missing', 'malformed'):
            staged, network, observed = self.fixture()
            if change == 'published': staged['published'] = True
            if change == 'failed': network['passed'] = False
            if change == 'map': network['map'] = '/Game/Other'
            if change == 'production': network['productionAccepted'] = True
            if change == 'streaming': network['twoClientStreaming'] = False
            if change == 'hash': network['packageHashes']['/Game/Sunmeadow'] = 'd'*64
            if change == 'capital': observed['/Game/Capital'] = 'e'*64; network['packageHashes']['/Game/Capital'] = 'e'*64
            if change == 'missing': observed.pop('/Game/Capital')
            if change == 'malformed': observed['/Game/Sunmeadow'] = 'not-a-hash'
            with self.subTest(change=change), self.assertRaises(ValueError):
                reconciled_manifest(staged, network, observed)


if __name__ == '__main__':
    unittest.main()
