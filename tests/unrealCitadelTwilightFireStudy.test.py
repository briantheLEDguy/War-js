import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/unreal/citadel_twilight_fire_study.py'
spec = importlib.util.spec_from_file_location('twilight_study', path)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def fixture():
    fixtures = [dict(id=i, properties=copy.deepcopy(study.FIXTURE_DELTAS.get(i, {})), identity='retained_'+i)
                for i in sorted(study.FIXTURE_IDS)]
    exposure = next(r for r in fixtures if r['id'] == 'exposure')['properties']
    exposure.update(auto_exposure_method=dict(kind='enum', type='AutoExposureMethod', value='AEM_HISTOGRAM'),
                    auto_exposure_apply_physical_camera_exposure=False,
                    dynamic_global_illumination_method=dict(kind='enum', type='DynamicGlobalIlluminationMethod', value='LUMEN'))
    for field in study.FIXTURE_DELTAS['exposure']: exposure['override_'+field] = True
    lights = [dict(id=i, pointCm=[100, 200, 300], intensityCd=1000, attenuationRadiusCm=1400,
                   sourceRadiusCm=30, temperatureK=2800, mobility='movable', castShadows=True) for i in sorted(study.LIGHT_IDS)]
    return fixtures, lights, {k: 'a'*64 for k in study.SOURCE_KEYS}


class TwilightTests(unittest.TestCase):
    def setUp(self): self.fixtures, self.lights, self.bindings = fixture()
    def plan(self, mode='lumen_hardware', units='native_luminance', extended=False):
        return study.comparison(mode, self.fixtures, self.lights, units, extended, self.bindings)

    def test_explicit_option_only(self):
        for value in ('', '0'): self.assertFalse(study.checked_option(value))
        self.assertTrue(study.checked_option('1'))
        for value in ('true', 'yes', ' 1', '1 ', '2', True, None):
            with self.assertRaises(ValueError): study.checked_option(value)

    def test_inputs_and_unrequested_properties_preserved(self):
        before = copy.deepcopy((self.fixtures, self.lights, self.bindings))
        requests, practicals, spec = self.plan()
        self.assertEqual((self.fixtures, self.lights, self.bindings), before)
        for old, new in zip(self.fixtures, requests):
            self.assertEqual(old['identity'], new['identity'])
            for key, value in old['properties'].items():
                if key not in study.FIXTURE_DELTAS.get(old['id'], {}): self.assertEqual(new['properties'][key], value)
        for old, new in zip(self.lights, practicals): self.assertEqual(old['pointCm'], new['pointCm'])
        for field in ('cloudRecipeChanged', 'materialGraphsChanged', 'newLightsAdded', 'lightShapesOrOriginsChanged',
                      'geometryOrGameplayChanged', 'savedPreferencesChanged', 'nativeReadbacksVerified',
                      'rendererStateVerified', 'visualApproved', 'gameplayApproved', 'releaseAcceptance'):
            self.assertFalse(spec[field])

    def test_backend_and_material_independence(self):
        for mode in ('lumen_software', 'lumen_hardware'): self.assertEqual(self.plan(mode)[2]['backendMode'], mode)
        for mode in ('base', 'storm_dusk', 'material_control', 'alpine_relief', 'unknown'):
            with self.assertRaises(ValueError): self.plan(mode)

    def test_no_ev100_or_unknown_metering(self):
        for units, extended in (('ev100', False), ('native_luminance', True), ('native_luminance', 0)):
            with self.assertRaises(ValueError): self.plan(units=units, extended=extended)
        next(r for r in self.fixtures if r['id'] == 'exposure')['properties']['auto_exposure_method']['value'] = 'AEM_MANUAL'
        with self.assertRaises(ValueError): self.plan()

    def test_missing_or_duplicate_fixtures_and_practicals(self):
        self.fixtures[-1] = copy.deepcopy(self.fixtures[0])
        with self.assertRaises(ValueError): self.plan()
        self.fixtures, self.lights, self.bindings = fixture()
        self.lights.pop()
        with self.assertRaises(ValueError): self.plan()

    def test_source_hashes_required(self):
        self.bindings.pop('blueprint')
        with self.assertRaises(ValueError): self.plan()
        self.fixtures, self.lights, self.bindings = fixture()
        self.bindings['blueprint'] = 'invalid'
        with self.assertRaises(ValueError): self.plan()

    def test_missing_exposure_override_and_nonfinite_source(self):
        exposure = next(r for r in self.fixtures if r['id'] == 'exposure')['properties']
        exposure['override_auto_exposure_bias'] = False
        with self.assertRaises(ValueError): self.plan()
        self.fixtures, self.lights, self.bindings = fixture()
        self.lights[0]['pointCm'][0] = float('nan')
        with self.assertRaises(ValueError): self.plan()

    def test_practical_factors_units_and_no_new_origin(self):
        _, practicals, _ = self.plan()
        for row in practicals:
            factor = 4 if row['id'].startswith(('gate_', 'court_')) else 1.5 if row['id'].startswith('portal_') else 1
            self.assertEqual(row['intensityCd'], 1000 * factor)
            self.assertNotIn('studyPointCm', row)
        self.lights[0]['mobility'] = 'stationary'
        with self.assertRaises(ValueError): self.plan()

    def readbacks(self):
        requests, practicals, spec = self.plan()
        destination = '/Game/WorldRebuild/AegisCitadel_' + 'b'*12
        fixtures = [dict(id=r['id'], actor=destination+'/Layers/Study_0.Study_0:PersistentLevel.'+r['id'],
                         properties=r['properties']) for r in requests]
        rows = [dict(id=r['id'], actor=destination+'/Layers/Study_1.Study_1:PersistentLevel.'+r['id'],
            pointCm=r['pointCm'], originalPointCm=r['pointCm'], intensityCd=r['intensityCd'],
            castShadows=True, temperatureK=2800, attenuationRadiusCm=1400, sourceRadiusCm=30, mobility='movable',
            visibility=dict(actorHidden=False, componentVisible=True, componentHiddenInGame=False)) for r in practicals]
        directions = [dict(actor=next(r for r in fixtures if r['id'] == identity)['actor'],
                           rotationDegrees=rotation)
                      for identity, rotation in study.DIRECTIONAL_ROTATIONS.items()]
        return [spec, fixtures, rows, directions, destination]

    def test_native_object_receipt_never_approves_renderer(self):
        result = study.checked_readbacks(*self.readbacks())
        self.assertTrue(result['nativeReadbacksVerified'])
        self.assertTrue(all(value is False for key, value in result.items() if key != 'nativeReadbacksVerified'))

    def test_missing_foreign_hidden_or_moved_native_light_rejects(self):
        for field, value in (('actor', '/Game/Foreign.Actor'), ('pointCm', [101, 200, 300]),
                             ('castShadows', False), ('intensityCd', 999), ('sourceRadiusCm', 90), ('mobility', 'stationary'),
                             ('visibility', dict(actorHidden=True, componentVisible=True, componentHiddenInGame=False))):
            with self.subTest(field=field):
                args = self.readbacks(); args[2][0][field] = value
                with self.assertRaises(ValueError): study.checked_readbacks(*args)
        args = self.readbacks(); args[2].pop()
        with self.assertRaises(ValueError): study.checked_readbacks(*args)

    def test_wrong_sun_fixture_or_duplicate_direction_rejects(self):
        args = self.readbacks(); args[3][0]['rotationDegrees'] = [-20, 30, 0]
        with self.assertRaises(ValueError): study.checked_readbacks(*args)
        args = self.readbacks(); args[3].append(copy.deepcopy(args[3][0]))
        with self.assertRaises(ValueError): study.checked_readbacks(*args)
        args = self.readbacks(); args[1][0]['properties']['intensity'] = float('inf')
        # ambient_sky sorts first and is one of the explicitly changed fixtures.
        with self.assertRaises(ValueError): study.checked_readbacks(*args)

    def test_fill_rotation_and_power_are_bound_independently_of_the_key(self):
        requests, _, spec = self.plan()
        self.assertEqual(spec['recipeVersion'], 2)
        self.assertEqual(next(r for r in requests if r['id'] == 'soft_sky_fill')['rotationDegrees'], [-65, 0, 0])
        self.assertEqual(next(r for r in requests if r['id'] == 'soft_sky_fill')['properties']['intensity'], 700)
        self.assertEqual(next(r for r in requests if r['id'] == 'ambient_sky')['properties']['intensity'], 1.4)
        for changes in ('missing', 'rotation', 'power'):
            args = self.readbacks()
            if changes == 'missing': args[3].pop()
            elif changes == 'rotation': args[3][1]['rotationDegrees'] = [-50, -140, 0]
            else: next(r for r in args[1] if r['id'] == 'soft_sky_fill')['properties']['intensity'] = 140
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError): study.checked_readbacks(*args)


if __name__ == '__main__': unittest.main()
