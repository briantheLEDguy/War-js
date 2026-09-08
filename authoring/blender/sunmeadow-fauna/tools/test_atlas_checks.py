import unittest
from atlas_checks import assert_single_atlas_island

class AtlasIslandTests(unittest.TestCase):
    def test_face_remains_inside_pelt_island(self):
        assert_single_atlas_island([(0.01,.01),(.24,.01),(.24,.49),(.01,.49)])
    def test_original_eye_ring_bug_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'unrelated atlas islands'):
            assert_single_atlas_island([(.1,.2),(.12,.2),(.62,.2),(.6,.2)],'eye rim')
    def test_ear_edge_cannot_cross_between_front_and_back_islands(self):
        with self.assertRaisesRegex(ValueError,'unrelated atlas islands'):
            assert_single_atlas_island([(.02,.1),(.02,.2),(.77,.2),(.77,.1)])
    def test_sampling_outside_an_island_cannot_wrap_to_another_feature(self):
        with self.assertRaisesRegex(ValueError,'outside'):
            assert_single_atlas_island([(-.001,.2),(.1,.2),(.1,.3)])
    def test_recess_can_use_one_constant_color_sample(self):
        assert_single_atlas_island([(.62,.2)]*4)

if __name__=='__main__':unittest.main()
