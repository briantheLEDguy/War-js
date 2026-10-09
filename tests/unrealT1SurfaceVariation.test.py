import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_surface_variation import surface_variation, validate_variation, rotated_uv, validate_substrate, substrate_weight, validate_shorelines, shoreline_weight, channel_weight


class SurfaceVariationTest(unittest.TestCase):
    def test_world_uv_is_continuous_and_rotation_preserves_physical_scale(self):
        row = surface_variation(); validate_variation(row)
        self.assertEqual(rotated_uv([300, 500, 700], 2, 0), [2.5, -1.5])
        a, b = rotated_uv([300, 500, 0], 3.66, .63), rotated_uv([300, 866, 5000], 3.66, .63)
        self.assertAlmostEqual(math.dist(a, b), 1)
        c = rotated_uv([300, 500.0001, 0], 3.66, .63)
        self.assertLess(math.dist(a, c), .000001)

    def test_recipe_rejects_nonfinite_or_out_of_range_controls(self):
        for field, value in [('secondaryScale', 0), ('macroMinimum', math.nan), ('vergeMetres', 50)]:
            with self.assertRaises(ValueError): validate_variation({**surface_variation(), field: value})
        with self.assertRaises(ValueError): rotated_uv([0, 0, 0], 0, 0)

    def test_dark_reviewed_channel_rescales_to_full_smooth_mask(self):
        row=surface_variation()
        self.assertEqual(channel_weight(row,.04),0)
        self.assertEqual(channel_weight(row,.24),1)
        self.assertAlmostEqual(channel_weight(row,.14),.5)
        for i in range(100):
            value=.04+i*.002
            self.assertLess(abs(channel_weight(row,value+.00001)-channel_weight(row,value)),.0001)
        for bounds in ([.2,.1],[0,math.nan],[0,2],[]):
            with self.assertRaises(ValueError):validate_variation({**row,'channelRange':bounds})
        with self.assertRaises(ValueError):channel_weight(row,math.inf)

    def test_substrate_patches_blend_continuously_and_expose_sloped_ground(self):
        row = dict(color=dict(path='public/assets/reviewed-color.png',sha256='a'*64),normal=dict(path='public/assets/reviewed-normal.png',sha256='b'*64),
                   tint=[.8,.87,.77],tileMetres=2.8,patchMetres=43,patchStrength=.52,slopeStrength=.38,maskRange=[.025,.18])
        validate_substrate(row)
        self.assertEqual(substrate_weight(row, 0, 1), 0)
        self.assertEqual(substrate_weight(row, 1, 1), .52)
        self.assertAlmostEqual(substrate_weight(row, 0, .8), .38)
        for n in range(101):
            mask=n/100
            self.assertLess(abs(substrate_weight(row,mask+.00001,.91)-substrate_weight(row,mask,.91)),.001)
            self.assertTrue(0 <= substrate_weight(row,mask,.91) <= 1)
        for bad in [{**row,'maskRange':[.18,.025]},{**row,'tileMetres':float('nan')},{**row,'color':dict(path='x',sha256='wrong')}]:
            with self.assertRaises(ValueError): validate_substrate(bad)
        with self.assertRaises(ValueError): substrate_weight(row,float('nan'),1)

    def test_shore_fade_is_local_continuous_and_never_a_hard_waterline(self):
        row=dict(x=20,z=-30,waterY=10,radius=70)
        self.assertEqual(shoreline_weight(row,20,-30,10),.9)
        self.assertEqual(shoreline_weight(row,200,-30,10),0)
        self.assertEqual(shoreline_weight(row,20,-30,9.55),.9)
        self.assertEqual(shoreline_weight(row,20,-30,11),0)
        for i in range(81):
            y=10+i/100
            self.assertLess(abs(shoreline_weight(row,20,-30,y)-shoreline_weight(row,20,-30,y+.00001)),.0001)
        for bad in [{**row,'radius':1000},{**row,'waterY':math.nan}]:
            with self.assertRaises(ValueError):validate_shorelines([bad])
        with self.assertRaises(ValueError):validate_shorelines([row]*9)
        with self.assertRaises(ValueError):shoreline_weight(row,math.nan,0,10)

if __name__ == '__main__': unittest.main()
