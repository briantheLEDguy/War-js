import importlib.util
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_landscape_ecology import cover_layout,pocket_water

class EcologyTests(unittest.TestCase):
    def test_shoreline_clips_beneath_ground_and_keeps_native_clockwise_winding(self):
        p=dict(id='test',x=0,z=0,radius=9,waterY=.45,cosmeticWater=True)
        h=lambda x,z:max(0,math.hypot(x,z)-10)*5
        data=pocket_water(p,h)
        self.assertEqual(len(data['positions']),97)
        for v in data['positions'][1:]:self.assertGreater(h(v[1]/100,v[0]/100),v[2])
        a,b,c=[data['positions'][i] for i in data['indices'][:3]]
        self.assertLess((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]),0)
        with self.assertRaises(ValueError):pocket_water(p,lambda x,z:0)
        with self.assertRaises(ValueError):pocket_water({**p,'cosmeticWater':False},h)

    def test_cover_is_deterministic_and_reserves_clear_road_and_services(self):
        outline=[dict(x=x,z=z) for x,z in [(-120,-120),(120,-120),(120,120),(-120,120)]]
        source=dict(id='sunmeadow_march',spatial=dict(bounds=dict(minX=-120,maxX=120,minZ=-120,maxZ=120),playableOutline=outline),
          paths=[dict(width=12,points=[dict(x=-120,z=0),dict(x=120,z=0)])],orvrLayout=dict(terrain=dict(flattenAreas=[])),npcs=[dict(x=50,z=50)])
        layout=cover_layout(source,lambda x,z:0,[])
        self.assertGreater(len(layout),100);self.assertEqual(layout,cover_layout(source,lambda x,z:0,[]))
        for r in layout:
            z,x,_=r['location'];self.assertGreater(abs(z),800);self.assertGreaterEqual(math.hypot(x/100-50,z/100-50),10)
        self.assertLess(max(r['scale'] for r in layout),.87)

if __name__=='__main__':unittest.main()
