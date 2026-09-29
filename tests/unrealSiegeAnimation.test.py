"""New class recipes cannot overwrite or admit the established animation set."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def inspect(animation_set):
    environment = dict(os.environ, WAR_ANIMATION_SET=animation_set)
    environment.pop('WAR_ANIMATION_PROFILE', None)
    script = """import sys,json
sys.path.insert(0,'scripts/unreal')
import animation_replacement as a
print(json.dumps(dict(profiles=list(a.PROFILES), output=str(a.OUT),
    selectedOld=a.selected('civic_battle_prelate_m'),
    paths=[a.visual_path(p) for p in a.PROFILES],
    recipes={k:[dict(id=r[0],sources=r[1],contact=r[3]) for r in v] for k,v in a.RECIPES.items()},
    clips=list(a.CLIPS),coverage=a.coverage())))
"""
    return json.loads(subprocess.check_output([sys.executable, '-c', script], cwd=ROOT, env=environment, text=True))


class SiegeAnimationTest(unittest.TestCase):
    def test_pending_classes_use_isolated_outputs_and_staging(self):
        result = inspect('siege-casters')
        self.assertEqual(set(result['profiles']), {'riven_ruin_oracle_m','riven_void_magister_m'})
        self.assertFalse(result['selectedOld'])
        self.assertTrue(all(p.startswith('/Game/Characters/SiegeStaging/') for p in result['paths']))
        self.assertTrue(result['output'].replace('\\','/').endswith('/siege/animation'))
        for recipes in result['recipes'].values():
            self.assertEqual(len({r['id'] for r in recipes}), 10)
            for recipe in recipes:
                self.assertGreater(recipe['contact'], 0)
                self.assertLess(recipe['contact'], 1)
                self.assertTrue(set(recipe['sources']) <= set(result['clips']))

    def test_default_keeps_original_four_profile_contract(self):
        result = inspect('supplied-four')
        self.assertEqual(len(result['profiles']), 4)
        self.assertEqual(sum(map(len,result['recipes'].values())), 40)
        self.assertTrue(all(result['coverage'].values()))
        self.assertTrue(result['selectedOld'])
        self.assertTrue(all(p.startswith('/Game/MigrationProof/') for p in result['paths']))


if __name__ == '__main__': unittest.main()
