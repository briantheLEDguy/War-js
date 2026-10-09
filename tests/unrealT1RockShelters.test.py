import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_rock_shelters import rock_shelter
from t1_placement_axes import source_scale_to_native

class ShelterTests(unittest.TestCase):
    def fixture(self,identity='sunmeadow_march'):
        s=dict(id=identity,spatial=dict(playableOutline=[dict(x=x,z=z) for x,z in [(-100,-100),(100,-100),(100,100),(-100,100)]]),paths=[],npcs=[])
        p=dict(id=identity+'_pocket_'+('eastern_hollow' if identity=='sunmeadow_march' else 'rust_sedge'),cosmeticWater=False,x=0,z=0,approach=[dict(x=0,z=-20),dict(x=0,z=0)])
        return s,[p],[[-190,-291,-4],[205,299,240]]
    def test_two_open_ends_retain_source_floor_and_clear_width(self):
        for identity in ['sunmeadow_march','cinderfen_outskirts']:
            s,p,b=self.fixture(identity);before=copy.deepcopy([s,p,b]);r=rock_shelter(s,lambda x,z:100+z*10,p,[],b)
            self.assertEqual([s,p,b],before);self.assertEqual(len(r['placements']),3);self.assertEqual(len(r['points']),7)
            self.assertEqual(r['minimumRoofClearanceCm'],570);self.assertFalse(r['terrainCut']);self.assertFalse(r['undergroundBuilt'])
            for q in r['points']:self.assertAlmostEqual(q[2],100+q[0]/10)
            piers=r['placements'][:2];self.assertGreater(13-sum(q['width']/2 for q in piers),6)
    def test_off_centre_source_bounds_map_to_exact_authored_centres_and_bottoms(self):
        s,p,b=self.fixture();r=rock_shelter(s,lambda x,z:0,p,[],b)
        for part in r['placements']:
            scale=source_scale_to_native(part['scaleAxes']);a=math.radians(part['yawDegrees']);centre=[(lo+hi)/2*v for lo,hi,v in zip(*b,scale)]
            x=part['authoredLocationCm'][0]+centre[0]*math.cos(a)-centre[1]*math.sin(a);y=part['authoredLocationCm'][1]+centre[0]*math.sin(a)+centre[1]*math.cos(a)
            self.assertAlmostEqual(x,part['z']*100);self.assertAlmostEqual(y,part['x']*100)
            bottom=part['authoredLocationCm'][2]+b[0][2]*scale[2]
            self.assertAlmostEqual(bottom,570 if part['id'].endswith('fallen_cap') else -20)
    def test_wet_unknown_steep_or_nonfinite_sites_fail(self):
        s,p,b=self.fixture()
        for bad in [[],[{**p[0],'cosmeticWater':True}]]:
            with self.assertRaises(ValueError):rock_shelter(s,lambda x,z:0,bad,[],b)
        with self.assertRaises(ValueError):rock_shelter({**s,'id':'brightfen_approach'},lambda x,z:0,p,[],b)
        for height in [lambda x,z:z*23,lambda x,z:x*23,lambda x,z:math.nan]:
            with self.assertRaises(ValueError):rock_shelter(s,height,p,[],b)
    def test_roads_anchors_and_occupied_scenery_are_preserved(self):
        s,p,b=self.fixture()
        for other in [{**s,'paths':[dict(width=8,points=[dict(x=0,z=-90),dict(x=0,z=90)])]},{**s,'npcs':[dict(x=0,z=10)]}]:
            with self.assertRaises(ValueError):rock_shelter(other,lambda x,z:0,p,[],b)
        with self.assertRaises(ValueError):rock_shelter(s,lambda x,z:0,p,[dict(x=0,z=0,width=20,depth=20)],b)

if __name__=='__main__':unittest.main()
