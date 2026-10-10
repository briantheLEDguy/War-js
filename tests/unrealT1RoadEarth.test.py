import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_road_earth import road_earth_recipe,road_earth_weights,road_earth_shaders,validate_recipe

class RoadEarthTest(unittest.TestCase):
    def test_only_sunmeadow_is_adapted_and_recipes_are_independent(self):
        r=road_earth_recipe('sunmeadow_march');r['villageRange'][0]=1
        self.assertEqual(road_earth_recipe('sunmeadow_march')['villageRange'],[75,150])
        for zone in ['cinderfen_outskirts','brightfen_approach','ashen_steppe','aegis_capital']:self.assertIsNone(road_earth_recipe(zone))
    def test_settlement_stone_and_open_earth_stay_bounded(self):
        for patch in [0,.5,1]:
            far=road_earth_weights(500,500,patch,.5)['soil'];village=road_earth_weights(0,500,patch,.5)['soil'];keep=road_earth_weights(500,0,patch,.5)['soil']
            self.assertTrue(.46<=far<=.64);self.assertAlmostEqual(village,far*.2);self.assertAlmostEqual(village,keep)
        self.assertEqual(road_earth_weights(500,500,.5,0)['macro'],.8)
        self.assertEqual(road_earth_weights(500,500,.5,1)['macro'],1.04)
    def test_transitions_have_no_weight_jumps_or_abrupt_endpoint_slope(self):
        for village,edges in [(True,[75,150]),(False,[30,75])]:
            sample=lambda d:road_earth_weights(d if village else 500,500 if village else d,.5,.5)['soil']
            values=[sample(d) for d in range(201)];self.assertEqual(values,sorted(values))
            for edge in edges:
                self.assertLess(abs(sample(edge+.001)-sample(edge-.001)),1e-8)
    def test_invalid_samples_and_duplicate_native_noise_helpers_fail(self):
        for args in [(math.nan,1,.5,.5),(-1,1,.5,.5),(1,1,2,.5),(True,1,.5,.5)]:
            with self.assertRaises(ValueError):road_earth_weights(*args)
        helper='struct SampleHelper { float noise(float2 p) {return .5;} };SampleHelper h; ignored body'
        colour,normal=road_earth_shaders(helper,helper)
        self.assertEqual(colour.count('float noise(float2 p)'),1);self.assertEqual(normal.count('float noise(float2 p)'),1)
        self.assertEqual(colour.split('float3 stone=')[0],normal.split('float3 n=')[0])
        for invalid in ['',helper.replace('float noise','float noise(float2 p); float noise')]:
            with self.assertRaises(ValueError):road_earth_shaders(invalid,helper)
        r=road_earth_recipe('sunmeadow_march');r['farSoil']=2
        with self.assertRaises(ValueError):validate_recipe(r)

if __name__=='__main__':unittest.main()
