import importlib.util
from pathlib import Path
import unittest
from collections import Counter
spec=importlib.util.spec_from_file_location('population',Path(__file__).resolve().parents[1]/'scripts/unreal/capital_population.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PopulationTests(unittest.TestCase):
    def test_identity_counts_and_districts(self):
        rows=m.records()
        self.assertEqual(len(rows),18)
        self.assertEqual(len({r['id'] for r in rows}),18)
        self.assertEqual(sum(r['profile']=='existing' for r in rows),1)
        self.assertEqual(Counter(r['district'] for r in rows),dict(gateward=5,cinderbank=4,lantern_quays=3,bellfound=3,crownwatch=3))
    def test_only_explicit_human_imports(self):
        self.assertEqual({r['profile'] for r in m.records()},{'existing',m.FARMER,m.HERBALIST,m.OFFICER})
if __name__=='__main__': unittest.main()
