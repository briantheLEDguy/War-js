"""Focused controls for rendered diagnostic comparisons, with no native writes."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from citadel_gameplay_performance import MODES, QUALITY, compare_reports, normalize_native_report, summarize_view, validate_repaired_baseline, validate_shadow_log


def fixture(frame_ms=20):
    samples = [dict(frameMs=frame_ms, gameThreadMs=3, renderThreadMs=4,
                    rhiThreadMs=0, gpuMs=frame_ms - 1, streamingRequests=0)
               for _ in range(int(10000 / frame_ms) + 1)]
    view = dict(id='castle_approach', eye=[100, 0, 200], direction=[1, 0, 0],
                fieldOfView=68, projection='perspective', privateMaterialReadiness=dict(ready=True),
                performanceSamples=samples, performanceSampleSeconds=len(samples) * frame_ms / 1000)
    return dict(passed=True, performanceDiagnostic=True, performanceMode='baseline',
                visualApproved=False, citywideAcceptance=False, releaseAcceptance=False,
                performanceSettings=dict(viewportSize=[2560, 1440], viewRect=[0, 0, 2560, 1440],
                    unscaledViewRect=[0, 0, 2560, 1440],
                    frameLimit=0, vSync=0, dynamicResolution=0, screenPercentage=100,
                    effectiveResolutionFraction=1, secondaryResolutionFraction=1,
                    frameSmoothing=False, fixedFrameRate=False, fixedTimeStep=False, timeDilation=1,
                    quality={key: 3 for key in QUALITY}, rhi='D3D12'), viewPerformance=[view])


class GameplayPerformanceTests(unittest.TestCase):
    def test_rejects_shadow_capacity_overflow_even_when_flags_remain_enabled(self):
        for message in ('LogRenderer: Warning: Virtual Shadow Map Page Pool overflow (597 page allocations were not served)',
                        'LogRenderer: Warning: [VSM] One Pass Projection max lights overflow.', ''):
            with self.subTest(message=message), self.assertRaises(ValueError): validate_shadow_log(message)
        validate_shadow_log('LogRenderer: Virtual shadow maps active\nLogRenderer: [VSM] Non-Nanite Marking Job Queue overflow. Performance may be affected.')

    def test_repaired_baseline_requires_real_tiles_and_retains_practical_shadows(self):
        before, after = fixture(), fixture(10)
        point = dict(component='Decor.PointLight0', **{'class': 'PointLightComponent'}, castShadows=True,
            registered=True, visible=True, affectsWorld=True, actorHidden=False, hiddenInGame=False,
            intensity=1200, intensityUnits=2, color=[1, 1, 1, 1], temperatureK=2850, useTemperature=True,
            attenuationRadiusCm=750, castStaticShadows=True, castDynamicShadows=True)
        nav = dict(available=True, dirty=False, built=True, registeredBounds=1, dataActors=[
            dict(agent=agent, registeredWithNavigation=True, needsRebuild=False, runtimeGeneration=0,
                 agentRadiusCm=radius, agentHeightCm=height, activeTiles=200, tileCapacity=1000,
                 tileCountSource='loaded Recast tile headers; public GetNavMeshTileXY')
            for agent, radius, height in [('Default', 42, 192), ('SiegeConvoy', 320, 330)]],
            characterAnchorPaths=[dict(anchor=i, projected=True, connected=True, searchLimit=False) for i in range(17)],
            convoyPaths=[dict(step=i, connected=True, pathPoints=5) for i in range(1, 4)])
        sun = dict(point, component='City.Sun', **{'class': 'DirectionalLightComponent'}, mobility=2, intensity=12500)
        witness = dict(lightingUnbuiltObjects=0, unbuiltReflectionCaptures=0, forceNoPrecomputedLighting=False,
            consoleVariables={'r.Shadow.UnbuiltPreviewInGame': 1, 'r.Shadow.Virtual.Enable': 1, 'r.ShadowQuality': 5},
            lights=[point, sun], navigation=nav)
        before['viewPerformance'][0]['lightingWitness'] = copy.deepcopy(witness)
        after['viewPerformance'][0]['lightingWitness'] = witness
        before['viewPerformance'][0]['lightingWitness']['navigation']['dataActors'][0]['activeTiles'] = 0
        before['viewPerformance'][0]['lightingWitness']['lightingUnbuiltObjects'] = 6083
        result = validate_repaired_baseline(before, after)
        self.assertTrue(result['rebuildWarningsResolved'])
        self.assertFalse(result['releaseAcceptance'])
        for kind in ('warning', 'false_counter', 'hidden_warning', 'no_baked_lighting', 'classic', 'shadow_quality', 'shadow_removed',
                     'light_power', 'sun_removed', 'sun_power', 'dirty', 'duplicate_bounds', 'empty_tiles', 'tile_pool_only',
                     'unregistered', 'rebuild', 'convoy_missing', 'wrong_agent', 'runtime_generation', 'generator_count',
                     'missing_anchor', 'unprojected', 'disconnected', 'limited_search', 'missing_convoy_leg', 'convoy_partial'):
            bad = copy.deepcopy(after)
            w = bad['viewPerformance'][0]['lightingWitness']
            n = w['navigation']; row = n['dataActors'][0]
            if kind == 'warning': w['lightingUnbuiltObjects'] = 6083
            if kind == 'false_counter': w['lightingUnbuiltObjects'] = False
            if kind == 'hidden_warning': w['consoleVariables']['r.Shadow.UnbuiltPreviewInGame'] = 0
            if kind == 'no_baked_lighting': w['forceNoPrecomputedLighting'] = True
            if kind == 'classic': w['consoleVariables']['r.Shadow.Virtual.Enable'] = 0
            if kind == 'shadow_quality': w['consoleVariables']['r.ShadowQuality'] = 0
            if kind == 'shadow_removed': w['lights'][0]['castShadows'] = False
            if kind == 'light_power': w['lights'][0]['intensity'] = 200
            if kind == 'sun_removed': w['lights'][1]['castShadows'] = False
            if kind == 'sun_power': w['lights'][1]['intensity'] = 10
            if kind == 'dirty': n['dirty'] = True
            if kind == 'duplicate_bounds': n['registeredBounds'] = 2
            if kind == 'empty_tiles': row['activeTiles'] = 0
            if kind == 'tile_pool_only': row.pop('activeTiles')
            if kind == 'unregistered': row['registeredWithNavigation'] = False
            if kind == 'rebuild': row['needsRebuild'] = True
            if kind == 'convoy_missing': n['dataActors'].pop()
            if kind == 'wrong_agent': row['agentRadiusCm'] = 35
            if kind == 'runtime_generation': row['runtimeGeneration'] = 1
            if kind == 'generator_count': row['tileCountSource'] = 'generator count'
            if kind == 'missing_anchor': n['characterAnchorPaths'].pop()
            if kind == 'unprojected': n['characterAnchorPaths'][0]['projected'] = False
            if kind == 'disconnected': n['characterAnchorPaths'][1]['connected'] = False
            if kind == 'limited_search': n['characterAnchorPaths'][1]['searchLimit'] = True
            if kind == 'missing_convoy_leg': n['convoyPaths'].pop()
            if kind == 'convoy_partial': n['convoyPaths'][1]['connected'] = False
            with self.subTest(kind=kind), self.assertRaises(ValueError): validate_repaired_baseline(before, bad)

    def test_uses_raw_wall_intervals_for_fps_and_nearest_rank_p95(self):
        report = fixture()
        metrics = summarize_view(report['viewPerformance'][0])
        self.assertEqual(metrics['fps'], 50)
        self.assertEqual(metrics['p95']['gpuMs'], 19)
        boundary = fixture(100)['viewPerformance'][0]
        boundary['performanceSamples'] = boundary['performanceSamples'][:100]
        for row in boundary['performanceSamples'][-5:]: row['frameMs'] = 200
        boundary['performanceSampleSeconds'] = 10.5
        self.assertEqual(summarize_view(boundary)['p95']['frameMs'], 100)
        before, after = fixture(40), fixture(20)
        original = copy.deepcopy((before, after))
        comparison = compare_reports(before, after)
        self.assertEqual((before, after), original)
        self.assertAlmostEqual(comparison['views'][0]['fpsRatio'], 2)
        self.assertFalse(comparison['populatedPerformanceVerified'])
        self.assertFalse(comparison['releaseAcceptance'])

    def test_rejects_short_inconsistent_unavailable_and_streaming_windows(self):
        for kind in ('short', 'duration', 'gpu', 'wall', 'nan', 'streaming', 'bool'):
            view = fixture()['viewPerformance'][0]
            if kind == 'short': view['performanceSamples'] = view['performanceSamples'][:10]
            if kind == 'duration': view['performanceSampleSeconds'] = 30
            if kind == 'gpu': view['performanceSamples'][0]['gpuMs'] = 0
            if kind == 'wall': view['performanceSamples'][0]['frameMs'] = 0
            if kind == 'nan': view['performanceSamples'][0]['renderThreadMs'] = float('nan')
            if kind == 'streaming': view['performanceSamples'][0]['streamingRequests'] = 1
            if kind == 'bool': view['performanceSamples'][0]['gpuMs'] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError): summarize_view(view)

    def test_rejects_camera_quality_render_resolution_and_scale_substitutions(self):
        for kind in ('camera', 'quality', 'viewport', 'rect', 'scale', 'missing_quality'):
            before, after = fixture(), fixture()
            if kind == 'camera': after['viewPerformance'][0]['eye'][0] += 1
            if kind == 'quality': after['performanceSettings']['quality'][QUALITY[0]] = 2
            if kind == 'viewport': after['performanceSettings']['viewportSize'] = [1920, 1080]
            if kind == 'rect': after['performanceSettings']['viewRect'] = [0, 0, 1280, 720]
            if kind == 'scale': after['performanceSettings']['screenPercentage'] = 50
            if kind == 'missing_quality': after['performanceSettings']['quality'].pop(QUALITY[0])
            with self.subTest(kind=kind), self.assertRaises(ValueError): compare_reports(before, after)

    def test_rejects_capped_or_nonrendered_runs_and_open_acceptance(self):
        for kind in ('cap', 'vsync', 'dynamic', 'fixed', 'smoothing', 'dilation', 'null_rhi', 'approval', 'shaders'):
            before, after = fixture(), fixture()
            if kind == 'cap': after['performanceSettings']['frameLimit'] = 60
            if kind == 'vsync': after['performanceSettings']['vSync'] = 1
            if kind == 'dynamic': after['performanceSettings']['dynamicResolution'] = 1
            if kind == 'fixed': after['performanceSettings']['fixedFrameRate'] = True
            if kind == 'smoothing': after['performanceSettings']['frameSmoothing'] = True
            if kind == 'dilation': after['performanceSettings']['timeDilation'] = .5
            if kind == 'null_rhi': after['performanceSettings']['rhi'] = 'NullRHI'
            if kind == 'approval': after['releaseAcceptance'] = True
            if kind == 'shaders': after['viewPerformance'][0]['privateMaterialReadiness']['ready'] = False
            with self.subTest(kind=kind), self.assertRaises(ValueError): compare_reports(before, after)

    def test_experiments_require_an_explicit_isolation_comparison(self):
        before, after = fixture(), fixture(10)
        for mode in MODES:
            if mode == 'baseline': continue
            after['performanceMode'] = mode
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError): compare_reports(before, after)
                comparison = compare_reports(before, after, diagnostic_comparison=True)
                self.assertTrue(comparison['isolationComparison'])
                self.assertFalse(comparison['releaseAcceptance'])
        after['performanceMode'] = 'unknown'
        with self.assertRaises(ValueError): compare_reports(before, after, diagnostic_comparison=True)

    def test_native_adapter_requires_actual_settings_and_consistent_elapsed_time(self):
        normalized = fixture()
        native = copy.deepcopy(normalized)
        settings = native.pop('performanceSettings')
        native['privatePerformanceMode'] = native.pop('performanceMode')
        native['diagnosticOnly'] = native.pop('performanceDiagnostic')
        view = native['viewPerformance'][0]
        view['requestedSampleSeconds'] = 10
        view['timingSamples'] = view.pop('performanceSamples')
        view.pop('performanceSampleSeconds')
        for i, row in enumerate(view['timingSamples']): row['elapsedSeconds'] = (i + 1) * .02
        view['lightingWitness'] = dict(viewportWidth=2560, viewportHeight=1440,
            frameSmoothing=False, useFixedFrameRate=False, fixedTimeStep=False, worldTimeDilation=1,
            consoleVariables={**settings['quality'], 't.MaxFPS': 0, 'r.VSync': 0,
                              'r.DynamicRes.OperationMode': 0, 'r.ScreenPercentage': 100})
        view['unboundBlendedViewDiagnostic'] = dict(scaledViewRectObserved=True,
            scaledViewRect=[0, 0, 2560, 1440], unscaledViewRect=[0, 0, 2560, 1440], effectiveResolutionFraction=1,
            secondaryResolutionFraction=1, rhi='D3D12')
        original = copy.deepcopy(native)
        adapted = normalize_native_report(native)
        self.assertEqual(native, original)
        self.assertEqual(adapted['performanceSettings'], settings)
        self.assertEqual(compare_reports(adapted, adapted)['views'][0]['fpsRatio'], 1)
        for kind in ('fractions', 'elapsed', 'timer', 'quality'):
            bad = copy.deepcopy(native)
            row = bad['viewPerformance'][0]
            if kind == 'fractions': row['unboundBlendedViewDiagnostic']['scaledViewRectObserved'] = False
            if kind == 'elapsed': row['timingSamples'][0]['elapsedSeconds'] += .5
            if kind == 'timer': row['lightingWitness'].pop('fixedTimeStep')
            if kind == 'quality': row['lightingWitness']['consoleVariables'][QUALITY[0]] = 3.5
            with self.subTest(kind=kind), self.assertRaises(ValueError): normalize_native_report(bad)

    def test_rejects_duplicate_missing_and_invalid_camera_views(self):
        for kind in ('duplicate', 'missing', 'direction', 'nan', 'bool', 'orthographic'):
            before, after = fixture(), fixture()
            view = after['viewPerformance'][0]
            if kind == 'duplicate': after['viewPerformance'].append(copy.deepcopy(view))
            if kind == 'missing': after['viewPerformance'] = []
            if kind == 'direction': view['direction'] = [0, 0, 0]
            if kind == 'nan': view['eye'][0] = float('inf')
            if kind == 'bool': view['eye'][0] = True
            if kind == 'orthographic': view['projection'] = 'orthographic'
            with self.subTest(kind=kind), self.assertRaises(ValueError): compare_reports(before, after)


if __name__ == '__main__': unittest.main()
