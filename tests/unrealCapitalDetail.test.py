"""Focused geography guarantees for the additive capital detail pass."""
import importlib.util
import math
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('detail',Path(__file__).resolve().parents[1]/'scripts/unreal/capital-detail-layout.py')
detail=importlib.util.module_from_spec(spec)
spec.loader.exec_module(detail)

class CapitalDetailTests(unittest.TestCase):
    def test_deterministic_unique_candidates(self):
        first=detail.layout()
        self.assertEqual(first,detail.layout())
        self.assertGreater(len(first),20)
        self.assertEqual(len(first),len({p['id'] for p in first}))

    def test_clearance_and_stair_exclusion(self):
        rows=detail.layout()
        for i,row in enumerate(rows):
            self.assertLessEqual(row['position'][0],12800)
            self.assertTrue(all(math.isfinite(v) for v in row['position']))
            for other in rows[i+1:]:
                self.assertGreaterEqual(math.dist(row['position'][:2],other['position'][:2]),800)

if __name__=='__main__':
    unittest.main()
