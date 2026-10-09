import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_bedded_outcrops import bedded_outcrops,outcrop_footing
from t1_landscape_ecology import segment_distance

class OutcropTests(unittest.TestCase):
    def source(self):
        ridge=dict(id='scarp',profile='escarpment',points=[dict(x=x,z=0,width=20,height=30) for x in [-160,160]])
        return dict(id='sunmeadow_march',spatial=dict(playableOutline=[dict(x=x,z=z) for x,z in [(-250,-150),(250,-150),(250,150),(-250,150)]]),orvrLayout=dict(terrain=dict(naturalField=dict(ridges=[ridge]),flattenAreas=[],clearCorridors=[])),npcs=[],paths=[])
    def test_bedding_is_deterministic_exposed_and_clears_reserved_routes(self):
        s=self.source();s['orvrLayout']['terrain']['clearCorridors']=[dict(radius=8,points=[dict(x=0,z=-150),dict(x=0,z=150)])]
        before=copy.deepcopy(s);rows=bedded_outcrops(s,lambda x,z:z*35,[])
        self.assertGreater(len(rows),5);self.assertEqual(s,before);self.assertEqual(rows,bedded_outcrops(s,lambda x,z:z*35,[]))
        self.assertEqual(len({r['id'] for r in rows}),len(rows))
        for row in rows:
            self.assertGreaterEqual(row['estimatedCentreExposureMetres'],row['height']*.35)
            self.assertGreaterEqual(abs(row['x']),8+math.hypot(row['width'],row['depth'])/2+3)
            self.assertLess(abs(row['yawDegrees']),8.01)
    def test_flat_or_occupied_ground_and_anchor_footing_are_rejected(self):
        s=self.source();self.assertEqual(bedded_outcrops(s,lambda x,z:0,[]),[])
        s['orvrLayout']['terrain']['flattenAreas']=[dict(id='village',x=0,z=0,radius=300,preserveFooting=True)]
        self.assertEqual(bedded_outcrops(s,lambda x,z:z*35,[]),[])
        s=self.source();self.assertEqual(bedded_outcrops(s,lambda x,z:z*35,[dict(x=0,z=0,width=600,depth=600)]),[])
    def test_painted_walking_counters_are_reserved_without_terrain_grading(self):
        s=self.source();rows=bedded_outcrops(s,lambda x,z:z*35,[]);self.assertGreater(len(rows),5)
        x=rows[len(rows)//2]['x'];s['paths']=[dict(width=4,points=[dict(x=x,z=-150),dict(x=x,z=150)])]
        kept=bedded_outcrops(s,lambda x,z:z*35,[])
        self.assertLess(len(kept),len(rows))
        for row in kept:self.assertGreaterEqual(abs(row['x']-x),2+math.hypot(row['width'],row['depth'])/2+3)

    def test_embedding_samples_the_oriented_rectangle_instead_of_oversized_circle(self):
        p=dict(x=0,z=0,width=10,depth=4,yawDegrees=0);height=lambda x,z:x*50+z*20
        self.assertAlmostEqual(outcrop_footing(height,p),-310)
        self.assertAlmostEqual(outcrop_footing(height,{**p,'yawDegrees':90}),-220)
        with self.assertRaises(ValueError):outcrop_footing(height,{**p,'width':0})
        with self.assertRaises(ValueError):outcrop_footing(lambda x,z:math.nan,p)
    def test_unreviewed_region_and_nonfinite_support_fail(self):
        s=self.source()
        with self.assertRaises(ValueError):bedded_outcrops({**s,'id':'brightfen_approach'},lambda x,z:0,[])
        with self.assertRaises(ValueError):bedded_outcrops(s,lambda x,z:math.nan,[])

if __name__=='__main__':unittest.main()
