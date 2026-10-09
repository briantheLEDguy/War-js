import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_placement_axes import source_scale_to_native
from world_static import read_glb,combine_parts
class PlacementAxesTests(unittest.TestCase):
    def test_width_maps_to_native_y_and_depth_to_native_x_without_mutation(self):
        axes=[4.5,1.1,2.3];before=copy.deepcopy(axes);self.assertEqual(source_scale_to_native(axes),[1.1,4.5,2.3]);self.assertEqual(axes,before)
        self.assertEqual(source_scale_to_native([2,2,2]),[2,2,2])
    def test_actual_reviewed_rock_bounds_match_the_source_reservation(self):
        root=Path(__file__).resolve().parents[1]
        for name,width,depth in [('frontier_sunmeadow_limestone_lod0.glb',7,5),('frontier_cinderfen_basalt_outcrop_lod0.glb',6,5)]:
            data=combine_parts(read_glb(root/'public/assets/models'/name)['parts']);native=source_scale_to_native([4.5,1.1,2.3])
            size=[(max(p[i] for p in data['positions'])-min(p[i] for p in data['positions']))/100*native[i] for i in range(3)]
            self.assertLess(size[1],width*4.5);self.assertGreater(size[1],width*4.5*.75)
            self.assertLess(size[0],depth*1.1);self.assertGreater(size[0],depth*1.1*.75)
    def test_bad_frames_cannot_silently_reach_native_authoring(self):
        for row in ([1,2],[-1,2,3],[1,math.inf,3],[1,math.nan,3],[1,True,3],[1,21,3]):
            with self.assertRaises(ValueError):source_scale_to_native(row)
if __name__=='__main__':unittest.main()
