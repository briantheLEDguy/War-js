import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
import frontend_sources as sources
import shared_city_sources as shared


class FrontendSourcesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'artifacts/unreal/world-portals'
        self.directory.mkdir(parents=True)
        config = self.root / 'unreal/AegisWar/Config/DefaultEngine.ini'
        config.parent.mkdir(parents=True)
        config.write_text('GameDefaultMap=/Game/Campaign\n')
        self.manifest = dict(zones=[])
        self.contract = dict(schemaVersion=1, campaignMap='/Game/Campaign', cities=[], campaignHashes={})
        for package in ('/Game/Campaign', '/Game/Routing'):
            self.contract['campaignHashes'][package] = self.package(package)
        for zone in shared.CITIES:
            scene, gameplay, definition, model = ['/Game/' + zone + '/' + name for name in ('Scenery', 'Gameplay', 'City', 'Model')]
            row = dict(id=zone, origin=[0, 0, 0], revision='current', definition=definition,
                sceneryLevels=[scene], gameplayLevels=[gameplay],
                packageHashes={p:self.package(p) for p in (scene, gameplay, definition)},
                dependencyHashes={model:self.package(model)})
            self.contract['cities'].append(row)
            self.manifest['zones'].append(dict(id=zone, origin=row['origin'], levels=dict(scenery=scene, gameplay=gameplay),
                cityDefinition=definition, cityRevision='current'))
        self.write()
        output = '/Game/UI/Frontend/CapitalPresentation'
        self.receipt = dict(schemaVersion=3, sourcePlan=sources.source_plan(self.root), outputPackages={output:self.package(output)})

    def package(self, name):
        p = self.root / 'unreal/AegisWar/Content' / (name[6:] + '.umap')
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(name)
        return sources.digest(p)

    def write(self):
        (self.directory / 'build.json').write_text(json.dumps(dict(map='/Game/Campaign', layer='/Game/Routing', partitionManifest='active.json')))
        (self.directory / 'active.json').write_text(json.dumps(self.manifest))
        p = self.root / shared.RECEIPT
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.contract))

    def test_same_canonical_city_for_every_consumer(self):
        self.assertEqual(sources.source_plan(self.root), shared.source_plan(self.root))
        self.assertIsNone(sources.stale_reason(self.root, self.receipt))

    def test_city_revision_changes_invalidate_frontend_until_rebound(self):
        city = self.contract['cities'][0]
        replacement = '/Game/aegis_capital/UpdatedScenery'
        city['sceneryLevels'] = [replacement]
        city['packageHashes'][replacement] = self.package(replacement)
        city['revision'] = 'next'
        self.manifest['zones'][0]['levels']['scenery'] = replacement
        self.manifest['zones'][0]['cityRevision'] = 'next'
        self.write()
        self.assertIsNotNone(sources.stale_reason(self.root, self.receipt))
        self.receipt['sourcePlan'] = sources.source_plan(self.root)
        self.assertIsNone(sources.stale_reason(self.root, self.receipt))
        self.assertEqual(self.receipt['sourcePlan']['cities'][0]['sceneryLevels'], [replacement])

    def test_old_intact_revision_is_rejected(self):
        self.manifest['zones'][0]['cityRevision'] = 'new-city'
        self.write()
        with self.assertRaisesRegex(ValueError, 'stale'):
            sources.source_plan(self.root)

    def test_duplicate_or_gameplay_scenery_is_rejected(self):
        for key in ('sceneryLevels', 'gameplayLevels'):
            previous = copy.deepcopy(self.contract)
            self.contract['cities'][0][key].append(self.contract['cities'][0]['sceneryLevels'][0])
            self.write()
            with self.assertRaisesRegex(ValueError, 'duplicated'):
                sources.source_plan(self.root)
            self.contract = previous

    def test_changed_model_invalidates_siege_and_frontend_sources(self):
        package = next(iter(self.contract['cities'][0]['dependencyHashes']))
        sources.package_file(self.root, package).write_text('changed geometry')
        with self.assertRaisesRegex(ValueError, 'Changed native city source: /Game/aegis_capital/Model'):
            sources.source_plan(self.root)

    def test_missing_model_has_no_fallback(self):
        package = next(iter(self.contract['cities'][0]['dependencyHashes']))
        sources.package_file(self.root, package).unlink()
        with self.assertRaisesRegex(ValueError, 'Missing native package'):
            sources.source_plan(self.root)

    def test_snapshot_receipt_is_not_a_shared_binding(self):
        self.receipt['schemaVersion'] = 2
        self.assertIsNotNone(sources.stale_reason(self.root, self.receipt))

    def test_source_path_cannot_escape_content(self):
        for name in ('/Game/../Outside', '/Game/a/../../Outside', '/Other/Map'):
            with self.assertRaises(ValueError):
                sources.package_file(self.root, name)


if __name__ == '__main__':
    unittest.main()
