import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'unreal'))
from aegis_citadel_reference_material import reference_material_comparison, reference_cloud_comparison


class ReferenceMaterialComparisonTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = [dict(id=key, rotationDegrees=[-20, 30, 0],
            properties=dict(intensity=12500, temperature=5600, cast_shadows=True,
                auto_exposure_min_brightness=64, auto_exposure_max_brightness=4096))
            for key in ('sun', 'soft_sky_fill', 'ambient_sky', 'distance_haze', 'exposure', 'sky', 'atmosphere')]

    def test_material_control_preserves_every_lighting_request_and_source(self):
        before = copy.deepcopy(self.fixtures)
        requests, carved, masonry = reference_material_comparison('material_control', self.fixtures)
        self.assertEqual(requests, before)
        self.assertEqual(self.fixtures, before)
        self.assertEqual(set(masonry), {'stone', 'limestone', 'flagstone', 'paving_inlay'})
        self.assertEqual(carved['baseColor'], [.06, .072, .09, 1])
        requests[0]['properties']['intensity'] = 1
        masonry['stone'][0] = 1
        self.assertEqual(self.fixtures, before)
        self.assertEqual(reference_material_comparison('material_control', before)[2]['stone'][0], .20)

    def test_lighting_comparison_changes_only_measured_light_balance(self):
        requests, _, _ = reference_material_comparison('material_lighting_control', self.fixtures)
        wanted = copy.deepcopy(self.fixtures)
        wanted[0]['properties'].update(intensity=6500, temperature=5200, light_source_angle=3)
        wanted[1]['properties']['intensity'] = 650
        wanted[2]['properties']['intensity'] = .55
        self.assertEqual(requests, wanted)
        self.assertEqual(self.fixtures[0]['properties']['intensity'], 12500)
        for bad in ('alpine_relief', '', None):
            with self.assertRaises(ValueError): reference_material_comparison(bad, self.fixtures)
        with self.assertRaises(ValueError): reference_material_comparison('material_lighting_control', self.fixtures[1:])

    def test_canopy_preserves_signed_parameters_without_modifying_the_recipe(self):
        cloud = dict(properties=dict(layer_bottom_altitude=.5, layer_height=1.2),
            materialInstance=dict(scalarParameters=dict(Layout_CloudGlobalScale=8),
                vectorParameters=dict(Layout_CloudTypeMask=[0, 0, 1, 0])))
        original = copy.deepcopy(cloud)
        properties, scalars, vectors = reference_cloud_comparison(cloud)
        self.assertEqual((properties, scalars, vectors), (cloud['properties'],
            cloud['materialInstance']['scalarParameters'], cloud['materialInstance']['vectorParameters']))
        scalars['Layout_CloudGlobalScale'] = 256
        vectors['Layout_CloudTypeMask'][2] = 0
        self.assertEqual(cloud, original)
        for bad in (None, {}, dict(properties={}, materialInstance=dict(scalarParameters={}, vectorParameters={}))):
            with self.assertRaises(ValueError): reference_cloud_comparison(bad)


if __name__ == '__main__':
    unittest.main()
