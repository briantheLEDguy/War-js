import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_landscape_ecology import cover_layout
from t1_ecology_clusters import clustered_cover

class ClusterTests(unittest.TestCase):
    def source(self):
        outline=[dict(x=x,z=z) for x,z in [(-120,-120),(120,-120),(120,120),(-120,120)]]
        return dict(id='sunmeadow_march',spatial=dict(bounds=dict(minX=-120,maxX=120,minZ=-120,maxZ=120),playableOutline=outline),
            paths=[dict(width=12,points=[dict(x=-120,z=0),dict(x=120,z=0)])],orvrLayout=dict(terrain=dict(flattenAreas=[])),npcs=[dict(x=50,z=50)])
    def test_colonies_are_deterministic_preserve_seeds_and_clear_roads_services(self):
        source=self.source();base=cover_layout(source,lambda x,z:0,[]);before=copy.deepcopy((source,base))
        result=clustered_cover(source,lambda x,z:0,[],base)
        self.assertEqual((source,base),before);self.assertEqual(result[:len(base)],base)
        self.assertEqual(result,clustered_cover(source,lambda x,z:0,[],base));self.assertGreater(len(result),len(base)*1.6)
        for row in result[len(base):]:
            z,x,y=row['location'];self.assertGreaterEqual(abs(z),725);self.assertGreaterEqual(math.hypot(x/100-50,z/100-50),10)
            self.assertEqual(y,-2);self.assertGreaterEqual(row['scale'],.38);self.assertLess(row['scale'],.72)
    def test_water_steep_slopes_and_reserved_footing_admit_no_extra_colonies(self):
        source=self.source();base=cover_layout(source,lambda x,z:0,[])
        for height,pockets in [(lambda x,z:x*50,[]),(lambda x,z:0,[dict(x=0,z=0,radius=200,waterY=1,cosmeticWater=True,approach=[dict(x=-120,z=0),dict(x=0,z=0)])])]:
            self.assertEqual(clustered_cover(source,height,pockets,base),base)
        source['orvrLayout']['terrain']['flattenAreas']=[dict(id='objective',x=0,z=0,radius=200,preserveFooting=True)]
        self.assertEqual(clustered_cover(source,lambda x,z:0,[],base),base)
    def test_unreviewed_region_bad_seeds_or_nonfinite_ground_fail(self):
        source=self.source();base=cover_layout(source,lambda x,z:0,[])
        with self.assertRaises(ValueError):clustered_cover({**source,'id':'brightfen_approach'},lambda x,z:0,[],base)
        with self.assertRaises(ValueError):clustered_cover(source,lambda x,z:math.nan,[],base)
        bad=copy.deepcopy(base);bad[0]['location'][0]=math.inf
        with self.assertRaises(ValueError):clustered_cover(source,lambda x,z:0,[],bad)

if __name__=='__main__':unittest.main()
