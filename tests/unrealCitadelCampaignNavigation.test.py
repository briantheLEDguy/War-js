import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from citadel_campaign_navigation import updated_preparation


class CampaignNavigationReceiptTests(unittest.TestCase):
    def fixture(self):
        prefix = '/Game/WorldRebuild/AegisCitadel_4069b99e5f8d'
        main, overlay, route = [prefix + '/' + name for name in ('CampaignCandidate', 'CampaignSiegeOverlay', 'CampaignRoutingCandidate')]
        original = {main: '1' * 64, overlay: '2' * 64, route: '3' * 64}
        observed = {main: '4' * 64, overlay: '5' * 64, route: '3' * 64}
        staged = dict(revision='4069b99e5f8d', published=False, map=main, overlay=overlay,
            packageHashes=original, manifest=dict(mainSha256=original[main], packageHashes={overlay: original[overlay], route: original[route]}),
            build=dict(capitalSha256After=original[main], runtimeTraversalVerified=False),
            sourceHashes={'retained': '6' * 64}, gmDrafts={'preserved': {'id': 1}}, baseBuild={'preserved': True})
        rows = [dict(profile=name, after=main + '.CampaignCandidate:PersistentLevel.' + name,
                     activeTiles=20 + i, tileSnapshot='actual-test-fixture-payload-' + name)
                for i, name in enumerate(('Default', 'SiegeConvoy'))]
        journal = dict(revision=staged['revision'], originalPackageHashes=original, newPackageHashes=observed,
            freshProcessVerified=True, transfer=dict(passed=True, rebuilt=False, actors=rows,
                bounds=dict(before=overlay+'.CampaignSiegeOverlay:PersistentLevel.SiegeBounds', after=main+'.CampaignCandidate:PersistentLevel.SiegeBounds')),
            reloadedActors=[dict(profile=r['profile'], package=main, actor=r['after'], activeTiles=r['activeTiles'], tileSnapshot=r['tileSnapshot']) for r in rows])
        return staged, journal, observed

    def test_only_private_receipt_bindings_change(self):
        staged, journal, observed = self.fixture()
        before = copy.deepcopy(staged)
        result = updated_preparation(staged, journal, observed)
        self.assertEqual(staged, before)
        for field in ('gmDrafts', 'sourceHashes', 'baseBuild'):
            self.assertEqual(result[field], staged[field])
        self.assertEqual(result['manifest']['mainSha256'], observed[staged['map']])
        self.assertFalse(result['campaignNavigationOwnership']['productionAdmission'])
        self.assertFalse(result['campaignNavigationOwnership']['convoyTraversalVerified'])

    def test_unwitnessed_changed_or_conflicting_data_rejects(self):
        for kind in ('published', 'another-map', 'unrelated-package', 'no-reload', 'rebuilt', 'duplicate-profile', 'lost-tiles', 'different-bytes', 'wrong-owner', 'changed-original', 'already-reconciled'):
            staged, journal, observed = self.fixture()
            with self.subTest(kind=kind):
                if kind == 'published': staged['published'] = True
                elif kind == 'another-map': staged['map'] += '_other'
                elif kind == 'unrelated-package': observed[next(p for p in observed if p.endswith('CampaignRoutingCandidate'))] = '7' * 64
                elif kind == 'no-reload': journal['freshProcessVerified'] = False
                elif kind == 'rebuilt': journal['transfer']['rebuilt'] = True
                elif kind == 'duplicate-profile': journal['reloadedActors'][1]['profile'] = 'Default'
                elif kind == 'lost-tiles': journal['reloadedActors'][0]['activeTiles'] = 0
                elif kind == 'different-bytes': journal['reloadedActors'][0]['tileSnapshot'] += 'changed'
                elif kind == 'wrong-owner': journal['reloadedActors'][0]['package'] = staged['overlay']
                elif kind == 'changed-original': journal['originalPackageHashes'] = {}
                elif kind == 'already-reconciled': staged['campaignNavigationOwnership'] = {'verified': True}
                with self.assertRaises(ValueError): updated_preparation(staged, journal, observed)


if __name__ == '__main__': unittest.main()
