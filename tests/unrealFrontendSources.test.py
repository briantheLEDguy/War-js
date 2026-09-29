import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('frontend_sources', Path(__file__).resolve().parents[1] / 'scripts/unreal/frontend_sources.py')
sources = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sources)


class FrontendSourcesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'artifacts/unreal/world-portals'
        self.directory.mkdir(parents=True)
        self.manifest = dict(zones=[dict(id=zone, origin=[0, 0, 0], levels=dict(
            generated=f'/Game/{zone}/Generated', authored=f'/Game/{zone}/Authored',
            population=f'/Game/{zone}/Population', architecture=f'/Game/{zone}/CurrentArchitecture'))
            for zone in ('aegis_capital', 'riftspire_capital')])
        (self.directory / 'build.json').write_text(json.dumps(dict(map='/Game/CurrentCampaign', partitionManifest='active.json')))
        self.write_manifest()
        for file in ('scripts/unreal/frontend_sources.py', 'scripts/unreal/build-frontend-presentation.py',
                     'unreal/AegisWar/Config/DefaultEngine.ini'):
            target = self.root / file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('GameDefaultMap=/Game/CurrentCampaign\n')
        packages = ['/Game/CurrentCampaign', '/Game/UI/Frontend/CapitalPresentation']
        packages += [package for zone in self.manifest['zones'] for package in zone['levels'].values()]
        for package in packages:
            target = self.root / 'unreal/AegisWar/Content' / (package[6:] + '.umap')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(package)
        self.receipt = dict(schemaVersion=2, sourcePlan=sources.source_plan(self.root),
                            outputPackages={'/Game/UI/Frontend/CapitalPresentation': sources.digest(sources.package_file(self.root, '/Game/UI/Frontend/CapitalPresentation'))})
        self.receipt['sourcePackages'] = {p: sources.digest(sources.package_file(self.root, p))
                                         for city in self.receipt['sourcePlan']['cities'] for p in city['maps']}

    def write_manifest(self):
        (self.directory / 'active.json').write_text(json.dumps(self.manifest))

    def test_all_active_layers_and_current_manifest(self):
        plan = sources.source_plan(self.root)
        self.assertEqual(plan['cities'][0]['maps'], ['/Game/CurrentCampaign', *self.manifest['zones'][0]['levels'].values()])
        self.assertEqual(plan['cities'][1]['maps'], list(self.manifest['zones'][1]['levels'].values()))
        self.assertIsNone(sources.stale_reason(self.root, self.receipt))

    def test_changed_placement_requires_refresh(self):
        sources.package_file(self.root, '/Game/riftspire_capital/Authored').write_text('moved building')
        self.assertIn('Changed native package', sources.stale_reason(self.root, self.receipt))

    def test_new_layer_and_origin_require_refresh(self):
        self.manifest['zones'][0]['origin'] = [100, 0, 0]
        self.manifest['zones'][0]['levels']['new_layer'] = '/Game/CurrentCampaign'
        self.write_manifest()
        self.assertIn('routing', sources.stale_reason(self.root, self.receipt))

    def test_legacy_missing_or_overwritten_snapshot_is_stale(self):
        self.assertIsNotNone(sources.stale_reason(self.root, dict(schemaVersion=1)))
        receipt = copy.deepcopy(self.receipt)
        del receipt['sourcePackages']['/Game/aegis_capital/CurrentArchitecture']
        self.assertIn('omits', sources.stale_reason(self.root, receipt))
        output = sources.package_file(self.root, '/Game/UI/Frontend/CapitalPresentation')
        output.write_text('old snapshot saved by another editor')
        self.assertIn('Changed', sources.stale_reason(self.root, self.receipt))
        output.unlink()
        self.assertIn('Missing', sources.stale_reason(self.root, self.receipt))

    def test_startup_routing_mismatch_fails(self):
        (self.root / 'unreal/AegisWar/Config/DefaultEngine.ini').write_text('GameDefaultMap=/Game/Other\n')
        with self.assertRaisesRegex(ValueError, 'startup map'):
            sources.source_plan(self.root)

    def test_missing_layer_and_unsafe_paths_fail(self):
        sources.package_file(self.root, '/Game/aegis_capital/CurrentArchitecture').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing native'):
            sources.source_plan(self.root)
        for package in ('/Engine/BasicShapes/Cube', '/Game/../Outside', '/Game/foo\\bar'):
            with self.assertRaises(ValueError):
                sources.package_file(self.root, package)


if __name__ == '__main__':
    unittest.main()
