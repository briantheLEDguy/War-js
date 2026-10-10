import copy, math, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_woodland_clusters import woodland_layout
from t1_landscape_ecology import segment_distance


def fixture():
    points=[dict(x=-700,z=155),dict(x=-300,z=155)]
    return dict(id='sunmeadow_march', spatial=dict(playableOutline=[dict(x=-740,z=-530),dict(x=740,z=-530),dict(x=740,z=530),dict(x=-740,z=530)]), paths=[dict(points=points,width=12)], orvrLayout=dict(caravanRoutes=[],terrain=dict(clearCorridors=[],flattenAreas=[dict(x=-600,z=250,radius=20)])))


class WoodlandClusterTests(unittest.TestCase):
    def test_deterministic_clusters_preserve_inputs_budget_and_natural_clearings(self):
        source=fixture(); occupied=[dict(x=-565,z=110,radius=12)]; before=copy.deepcopy((source,occupied))
        rows=woodland_layout(source,lambda x,z:10+.1*x,occupied,.38,160)
        self.assertEqual(rows,woodland_layout(source,lambda x,z:10+.1*x,occupied,.38,160)); self.assertEqual((source,occupied),before)
        self.assertEqual(len(rows),160); self.assertEqual(len({p['id'] for p in rows}),160)
        for p in rows:
            self.assertTrue(13<=p['heightMetres']<=22); self.assertAlmostEqual(p['groundMetres'],10+.1*p['x'])
            self.assertGreaterEqual(math.hypot(p['x']+600,p['z']-250),38)
            self.assertGreaterEqual(math.hypot(p['x']+565,p['z']-110),12)
        self.assertEqual({p['group'] for p in rows},{'western_wood','barrow_wood'})
    def test_full_crowns_clear_vehicle_lanes_and_each_other(self):
        source=fixture(); rows=woodland_layout(source,lambda x,z:0,[],.38,160); route=source['paths'][0]
        for i,p in enumerate(rows):
            self.assertGreaterEqual(segment_distance(p,*route['points']),6+p['heightMetres']*.38+3)
            for other in rows[:i]:self.assertGreaterEqual(math.hypot(p['x']-other['x'],p['z']-other['z']),8)
    def test_steep_ground_is_excluded_and_invalid_ground_fails(self):
        self.assertEqual(woodland_layout(fixture(),lambda x,z:x,[],.38),[])
        with self.assertRaises(ValueError):woodland_layout(fixture(),lambda x,z:math.nan,[],.38)
    def test_budgets_regions_and_obstacles_are_bounded(self):
        source=fixture(); source['id']='ashEN_steppe'
        with self.assertRaises(ValueError):woodland_layout(source,lambda x,z:0,[],.38)
        for limit in [True,-1,221,1.5]:
            with self.assertRaises(ValueError):woodland_layout(fixture(),lambda x,z:0,[],.38,limit)
        for ratio in [math.nan,0,2]:
            with self.assertRaises(ValueError):woodland_layout(fixture(),lambda x,z:0,[],ratio)
        with self.assertRaises(ValueError):woodland_layout(fixture(),lambda x,z:0,[dict(x=0,z=0,radius=101)],.38)
        self.assertEqual(woodland_layout(fixture(),lambda x,z:0,[],.38,0),[])

if __name__=='__main__':unittest.main()
