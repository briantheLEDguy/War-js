import copy
import importlib.util
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('t1_clearance', Path(__file__).parents[1]/'scripts/unreal/t1_clearance.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ClearanceContract(unittest.TestCase):
    def test_complete_inventory_preserves_inputs(self):
        source = dict(id='zone', paths=[dict(id='road', width=6, points=[dict(x=0, z=0), dict(x=5, z=0)])],
            orvrLayout=dict(caravanRoutes=[dict(id='convoy', width=12, points=[dict(x=5, z=0), dict(x=8, z=3)])]),
            zoneTriggers=[dict(id='portal', arrivalPoint=dict(x=0, z=0))], spawnPoint=dict(x=1, z=0))
        village = dict(zoneId='zone', modules=[dict(id='house', approach=[dict(x=0, z=0), dict(x=0, z=3)])],
            serviceReservations=[dict(id='forge', point=dict(x=2, z=0))])
        before = copy.deepcopy((source, village))
        routes, points = module.clearance_routes(source, village)
        self.assertEqual([p['kind'] for p in routes], ['road', 'supply', 'planned_entry'])
        self.assertEqual([p['kind'] for p in points], ['service', 'portal_arrival', 'spawn'])
        self.assertEqual((source, village), before)
        self.assertFalse(routes[-1]['vehicle'])
        self.assertEqual(routes[0]['width'], 6)
        village['modules'][0]['id'] = 'road'
        with self.assertRaises(ValueError):
            module.clearance_routes(source, village)

    def test_bounded_sweeps_include_endpoints_and_reverse(self):
        a, b = dict(x=0, z=0), dict(x=5, z=3)
        values = module.segment_samples(a, b)
        self.assertEqual(values[0], a)
        self.assertEqual(values[-1], b)
        self.assertTrue(all(math.dist([p['x'], p['z']], [q['x'], q['z']]) <= 2 for p, q in zip(values, values[1:])))
        for p, q in zip(values, reversed(module.segment_samples(b, a))):
            self.assertAlmostEqual(p['x'], q['x'])
            self.assertAlmostEqual(p['z'], q['z'])
        for step in [0, -1, float('nan')]:
            with self.assertRaises(ValueError):
                module.segment_samples(a, b, step)
        with self.assertRaises(ValueError):
            module.segment_samples(a, dict(x=float('inf'), z=0))


if __name__ == '__main__':
    unittest.main()
