import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_pocket_dressing import pocket_dressing
from t1_landscape_ecology import segment_distance

class PocketDressingTest(unittest.TestCase):
    def test_terrain_selects_banks_and_clear_corridors_and_identity_are_preserved(self):
        outline=[dict(x=x,z=z) for x,z in [(-120,-120),(120,-120),(120,120),(-120,120)]]
        corridor=dict(id='approach',radius=12,points=[dict(x=-120,z=0),dict(x=0,z=0)])
        source=dict(id='sunmeadow_march',spatial=dict(playableOutline=outline),orvrLayout=dict(terrain=dict(clearCorridors=[corridor],flattenAreas=[])),npcs=[dict(x=15,z=10)])
        pocket=dict(id='test_pocket',x=0,z=0,radius=9,waterY=0,bedY=-.45,cosmeticWater=True)
        h=lambda x,z:(math.hypot(x,z)-20)*5
        rows=pocket_dressing(source,h,[pocket],[])
        self.assertGreater(len(rows),20);self.assertEqual(rows,pocket_dressing(source,h,[pocket],[]))
        for r in rows:
            radius=math.hypot(r['width'],r['depth'])/2
            self.assertGreaterEqual(segment_distance(r,*corridor['points']),12+radius+2)
            self.assertGreaterEqual(math.hypot(r['x']-15,r['z']-10),radius+12)
            self.assertTrue(-.03<=h(r['x'],r['z'])/100<=2.5)
            self.assertTrue(r['sourceLabel'].startswith('sunmeadow_march_'))
        self.assertEqual(len(set(r['id'] for r in rows)),len(rows))
        self.assertEqual(pocket_dressing(source,lambda x,z:1000,[pocket],[]),[])
        self.assertEqual(pocket_dressing(source,lambda x,z:-100,[pocket],[]),[])

if __name__=='__main__':unittest.main()
