import copy
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'unreal'))
from citadel_lumen_study import (FIXTURE_IDS, private_lumen_comparison, runtime_recipe,
                                review_resources, review_view)


class PrivateLumenStudyTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = [dict(id=name, properties=dict(intensity=i, sentinel={'unchanged': [i]}),
                              rotationDegrees=[i, i, i]) for i, name in enumerate(FIXTURE_IDS)]
        self.cloud = dict(properties={'layer_height': 1.2}, materialInstance=dict(
            scalarParameters={'Cloud_GlobalDensity': .012}, vectorParameters={'Layout_CloudType': [1, 0, 0, 0]}))
        self.mesh = dict(mesh='/Game/Private/SM_Hall.SM_Hall', available=True, compiling=False,
                         cards=dict(present=True, finite=True, count=12),
                         distanceField=dict(present=True, valid=True, asyncBuilding=False, alwaysLoadedBytes=128, bricks=20),
                         rayTracing=dict(present=True, valid=True, validInitializer=True, rhiPresent=True, requiresBuild=False))

    def view(self, mode):
        vals = {**runtime_recipe(mode), 'r.Lumen.Supported': 1, 'r.ForwardShading': 0,
                'r.GenerateMeshDistanceFields': 1, 'r.RayTracing': 1, 'r.SkinCache.CompileShaders': 1}
        return dict(available=True, readThread='render', nonce='test_nonce', frameNumber=42,
                    viewCount=1, captureBindingVerified=True, giMethod='Lumen', reflectionMethod='Lumen',
                    cvars={k: dict(available=True, value=v, setByFlags=0x08000000) for k, v in vals.items()},
                    projectSupportsLumen=True, platformSupportsLumen=True, viewStatePresent=True,
                    projectSupportsDistanceFields=True, rayTracingEnabledForProject=True, rayTracingEnabled=True,
                    rayTracingAllowedForView=True, supportsInlineRayTracing=True,
                    showFlags={**{k: True for k in ('Lighting', 'GlobalIllumination', 'LumenGlobalIllumination',
                        'LumenReflections', 'LumenDetailTraces', 'LumenGlobalTraces')}, 'PathTracing': False, 'RayTracingDebug': False})

    def resources(self, mode, meshes):
        return review_resources(mode, meshes, [self.mesh['mesh']])

    def test_only_four_exposure_fields_change(self):
        before = copy.deepcopy(self.fixtures)
        for mode in ('lumen_software', 'lumen_hardware'):
            requests, cloud, spec = private_lumen_comparison(mode, self.fixtures, self.cloud)
            for actual, wanted in zip(requests, before):
                if actual['id'] == 'exposure':
                    for prop in ('override_dynamic_global_illumination_method', 'dynamic_global_illumination_method',
                                 'override_reflection_method', 'reflection_method'):
                        del actual['properties'][prop]
                self.assertEqual(actual, wanted)
            self.assertEqual(cloud, (self.cloud['properties'], self.cloud['materialInstance']['scalarParameters'],
                                     self.cloud['materialInstance']['vectorParameters']))
            self.assertFalse(spec['rendererStateVerified'])
        self.assertEqual(self.fixtures, before)

    def test_cloud_is_copied_and_complete(self):
        _, cloud, _ = private_lumen_comparison('lumen_software', self.fixtures, self.cloud)
        cloud[2]['Layout_CloudType'][0] = 99
        self.assertEqual(self.cloud['materialInstance']['vectorParameters']['Layout_CloudType'][0], 1)
        with self.assertRaises(ValueError):
            private_lumen_comparison('lumen_software', self.fixtures, dict(properties={}))

    def test_fixture_duplicates_and_omissions_rejected(self):
        for bad in (self.fixtures[:-1], self.fixtures[:-1] + [self.fixtures[0]]):
            with self.assertRaises(ValueError):
                private_lumen_comparison('lumen_software', bad, self.cloud)

    def test_modes_are_private_and_exact(self):
        with self.assertRaises(ValueError):
            private_lumen_comparison('base', self.fixtures, self.cloud)
        sw, hw = runtime_recipe('lumen_software'), runtime_recipe('lumen_hardware')
        self.assertEqual(sw['r.Lumen.HardwareRayTracing'], 0)
        self.assertEqual(hw['r.Lumen.HardwareRayTracing'], 1)
        self.assertFalse(any(k.startswith('sg.') for k in sw))

    def test_resource_presence_never_approves_coverage_or_renderer(self):
        for mode in ('lumen_software', 'lumen_hardware'):
            result = self.resources(mode, [self.mesh])
            self.assertTrue(result['resourcePresenceReady'])
            self.assertFalse(result['surfaceCacheCoverageVerified'])
            self.assertFalse(result['rendererStateVerified'])

    def test_missing_and_pending_distance_fields_rejected(self):
        for field, value in (('present', False), ('valid', False), ('asyncBuilding', True),
                             ('alwaysLoadedBytes', 0), ('bricks', 0), ('bricks', True)):
            bad = copy.deepcopy(self.mesh)
            bad['distanceField'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.resources('lumen_software', [bad])

    def test_cards_and_inventory_rejected(self):
        for bad in ([], [self.mesh, self.mesh], [{**self.mesh, 'compiling': True}],
                    [{**self.mesh, 'cards': dict(present=True, finite=False, count=12)}],
                    [{**self.mesh, 'cards': dict(present=True, finite=True, count=0)}]):
            with self.assertRaises(ValueError):
                self.resources('lumen_software', bad)

    def test_hardware_requires_finished_rhi_geometry(self):
        for field, value in (('present', False), ('validInitializer', False), ('valid', False),
                             ('rhiPresent', False), ('requiresBuild', True)):
            bad = copy.deepcopy(self.mesh)
            bad['rayTracing'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.resources('lumen_hardware', [bad])

    def test_complete_source_bound_inventory_required(self):
        for expected in ([], [self.mesh['mesh'], '/Game/Private/SM_Extra.SM_Extra'],
                         [self.mesh['mesh'], self.mesh['mesh']]):
            with self.assertRaises(ValueError):
                review_resources('lumen_software', [self.mesh], expected)

    def test_blended_readback_is_still_not_renderer_acceptance(self):
        for mode in ('lumen_software', 'lumen_hardware'):
            result = review_view(mode, self.view(mode), 'test_nonce', 42)
            self.assertTrue(result['resolvedViewPrerequisitesReady'])
            self.assertIsNone(result['actualBackend'])
            self.assertFalse(result['rendererStateVerified'])
            self.assertFalse(result['lightingApproved'])

    def test_stale_frames_missing_binding_and_wrong_nonce_rejected(self):
        for field, value in (('frameNumber', 41), ('nonce', 'other'), ('captureBindingVerified', False),
                             ('viewCount', 2), ('readThread', 'game'), ('frameNumber', True)):
            bad = self.view('lumen_software')
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                review_view('lumen_software', bad, 'test_nonce', 42)

    def test_actor_enum_and_unavailable_cvar_cannot_pass(self):
        with self.assertRaises(ValueError):
            review_view('lumen_software', dict(giMethod='Lumen', reflectionMethod='Lumen'), 'test_nonce', 42)
        for change in ({'available': False}, {'value': None}, {'value': True}, {'setByFlags': None}, {'value': 0}):
            bad = self.view('lumen_software')
            bad['cvars']['r.Lumen.DiffuseIndirect.Allow'].update(change)
            with self.assertRaises(ValueError):
                review_view('lumen_software', bad, 'test_nonce', 42)

    def test_software_support_and_show_flags_required(self):
        for field in ('projectSupportsDistanceFields', 'projectSupportsLumen', 'platformSupportsLumen', 'viewStatePresent'):
            bad = self.view('lumen_software')
            bad[field] = False
            with self.assertRaises(ValueError):
                review_view('lumen_software', bad, 'test_nonce', 42)
        for field, value in (('LumenDetailTraces', False), ('LumenReflections', False), ('PathTracing', True)):
            bad = self.view('lumen_software')
            bad['showFlags'][field] = value
            with self.assertRaises(ValueError):
                review_view('lumen_software', bad, 'test_nonce', 42)

    def test_hardware_fallback_is_rejected(self):
        for field in ('rayTracingEnabled', 'rayTracingAllowedForView', 'rayTracingEnabledForProject'):
            bad = self.view('lumen_hardware')
            bad[field] = False
            with self.assertRaises(ValueError):
                review_view('lumen_hardware', bad, 'test_nonce', 42)
        bad = self.view('lumen_hardware')
        bad['supportsInlineRayTracing'] = False
        with self.assertRaises(ValueError):
            review_view('lumen_hardware', bad, 'test_nonce', 42)


if __name__ == '__main__':
    unittest.main()
