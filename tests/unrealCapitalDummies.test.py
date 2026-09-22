import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/unreal'))
from capital_training_dummies import targets, export_model, MODELS, rest_scene


class CapitalDummiesTests(unittest.TestCase):
    def test_exact_sources_and_passive_identity(self):
        for zone, (_, model) in MODELS.items():
            source = json.loads((ROOT/'public/assets/maps'/(zone+'.json')).read_text())
            rows, actual = targets(source)
            self.assertEqual(actual,model)
            self.assertEqual([r['maxHealth'] for r in rows],[60,120,90])
            for field, value in [('model','another_species.glb'),('aggroRange',10),('characterProfileKey','raider')]:
                changed = copy.deepcopy(source); changed['enemies'][0][field] = value
                with self.assertRaises(ValueError): targets(changed)
            source['enemies'].append(source['enemies'][0])
            with self.assertRaises(ValueError): targets(source)

    def test_existing_meshes_keep_geometry_materials_and_upright_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            for _, model in MODELS.values():
                exported = export_model(ROOT/'public/assets/models'/model,Path(temporary))
                surface = exported['surface']; points = surface['positions']
                self.assertGreater(len(surface['materials']),0)
                self.assertEqual(len(surface['triangleMaterials']),len(surface['indices'])//3)
                self.assertAlmostEqual(min(p[2] for p in points),0,delta=3)
                self.assertGreater(max(p[2] for p in points),150)
                self.assertLess(max(p[2] for p in points),260)
                self.assertGreater(len(surface['indices']),800)

    def test_skeletal_substitutes_rejected(self):
        with self.assertRaises(ValueError): rest_scene({'skins':[{}]})


if __name__ == '__main__': unittest.main()
