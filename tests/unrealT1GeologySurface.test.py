import math,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_geology_surface import differential_normal,NORMAL_SHADER,bump_height,detail_weight

class GeologyTest(unittest.TestCase):
    def close(self,a,b):
        for x,y in zip(a,b):self.assertAlmostEqual(x,y,places=10)
    def test_zero_height_preserves_surface_and_linear_height_has_expected_gradient(self):
        self.close(differential_normal([0,0,1],[1,0,0],[0,1,0],0,0),[0,0,1])
        length=math.sqrt(1+.2**2+.3**2)
        self.close(differential_normal([0,0,1],[1,0,0],[0,1,0],.2,.3),[-.2/length,-.3/length,1/length])
    def test_screen_orientation_and_pixel_scale_preserve_the_same_surface_normal(self):
        expected=differential_normal([0,0,1],[1,0,0],[0,1,0],.2,.3)
        self.close(expected,differential_normal([0,0,1],[-1,0,0],[0,1,0],-.2,.3))
        self.close(expected,differential_normal([0,0,1],[0,3,0],[-2,0,0],.9,-.4))
    def test_vertical_faces_use_their_own_tangent_plane(self):
        length=math.sqrt(1+.2**2+.3**2)
        self.close(differential_normal([1,0,0],[0,1,0],[0,0,1],.2,.3),[1/length,-.2/length,-.3/length])
    def test_degenerate_view_is_stable_and_nonfinite_samples_are_rejected(self):
        self.close(differential_normal([0,0,2],[1,0,0],[1,0,0],100,100),[0,0,1])
        with self.assertRaises(ValueError):differential_normal([0,0,0],[1,0,0],[0,1,0],0,0)
        with self.assertRaises(ValueError):differential_normal([0,0,1],[math.nan,0,0],[0,1,0],0,0)
        with self.assertRaises(ValueError):differential_normal([0,0,1],[1,0,0],[0,1,0],math.inf,0)
        self.assertIn('TransformWorldVectorToTangent',NORMAL_SHADER)

    def test_height_is_bounded_cosmetic_centimetres_and_rejects_unbounded_inputs(self):
        recipe=dict(bumpHeightCm=[60,8])
        self.assertEqual(bump_height(recipe,.5,.5),0)
        self.assertEqual(bump_height(recipe,0,0),-34)
        self.assertEqual(bump_height(recipe,1,1),34)
        for i in range(101):self.assertLessEqual(abs(bump_height(recipe,i/100,1-i/100)),34)
        for noise in (math.nan,-.01,1.01):
            with self.assertRaises(ValueError):bump_height(recipe,noise,.5)
        for invalid in ([81,0],[-1,8],[math.inf,8],[8]):
            with self.assertRaises(ValueError):bump_height(dict(bumpHeightCm=invalid),.5,.5)

    def test_pixel_footprint_fades_aliasing_continuously_without_changing_contacts(self):
        self.assertEqual(detail_weight(0),1);self.assertEqual(detail_weight(20),1)
        self.assertEqual(detail_weight(70),.5);self.assertEqual(detail_weight(120),0)
        self.assertEqual(detail_weight(1000),0)
        self.close(differential_normal([0,0,1],[120,0,0],[0,120,0],24,36),[0,0,1])
        for i in range(201):
            self.assertGreaterEqual(detail_weight(i),0);self.assertLessEqual(detail_weight(i),1)
            self.assertLessEqual(detail_weight(i+1),detail_weight(i))
        for invalid in (math.nan,math.inf,-1):
            with self.assertRaises(ValueError):detail_weight(invalid)
        self.assertIn('smoothstep(20,120',NORMAL_SHADER)

if __name__=='__main__':unittest.main()
