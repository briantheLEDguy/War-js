"""Exercise the navigation resolver without loading Unreal or changing assets."""
import ast
import copy
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLOUD = '/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst'


class NavigationSources(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((ROOT / 'scripts/unreal/build-citadel-navigation.py').read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'source_package_file')
        self.cloud_file = Path('installed-engine/Content/EngineSky/VolumetricClouds/cloud.uasset')
        self.game_calls = []

        def game_file(root, package):
            self.game_calls.append(package)
            if not package.startswith('/Game/'):
                raise ValueError('Not a game package')
            return root / 'Content' / (package[6:] + '.uasset')

        self.environment = dict(ROOT=ROOT, REVIEWED_CLOUD_MATERIAL=CLOUD,
            blueprint=dict(lightingTreatment=dict(cloudFixture=dict(
                material=dict(package=CLOUD, sha256='a' * 64)))),
            receipt=dict(sourceHashes={CLOUD: 'a' * 64}),
            cloud_material_file=lambda: self.cloud_file, package_file=game_file)
        exec(compile(ast.Module(body=[copy.deepcopy(function)], type_ignores=[]),
                     'navigation-source-resolver', 'exec'), self.environment)
        self.resolve = self.environment['source_package_file']

    def test_only_signed_bundled_parent_uses_engine_resolver(self):
        self.assertEqual(self.resolve(CLOUD), self.cloud_file)
        self.assertEqual(self.game_calls, [])
        self.assertEqual(self.resolve('/Game/WorldRebuild/Candidate/City'),
                         ROOT / 'Content/WorldRebuild/Candidate/City.uasset')
        with self.assertRaises(ValueError):
            self.resolve('/Engine/EngineSky/Other')
        with self.assertRaises(ValueError):
            self.resolve('/Engine/EngineSky/VolumetricClouds/../Other')

    def test_signed_recipe_and_source_closure_must_agree(self):
        for replacement in (None, 'b' * 64):
            self.environment['receipt']['sourceHashes'][CLOUD] = replacement
            with self.assertRaises(RuntimeError):
                self.resolve(CLOUD)
        self.environment['receipt']['sourceHashes'][CLOUD] = 'a' * 64
        self.environment['blueprint']['lightingTreatment']['cloudFixture']['material']['package'] = '/Engine/Other'
        with self.assertRaises(RuntimeError):
            self.resolve(CLOUD)


if __name__ == '__main__':
    unittest.main()
