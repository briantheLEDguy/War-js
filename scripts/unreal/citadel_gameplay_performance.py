"""Compare rendered castle diagnostic windows; never grant release acceptance."""
import copy
import math
import re


MODES = ('baseline', 'preview_shadows_off', 'shadows_off', 'point_shadows_off',
         'shadow_cache_512', 'shadow_cache_1024', 'virtual_shadow_maps', 'ssgi_off', 'reflections_off')
TIMINGS = ('frameMs', 'gameThreadMs', 'renderThreadMs', 'rhiThreadMs', 'gpuMs')
CAMERA_FIELDS = ('eye', 'direction', 'fieldOfView', 'projection')
QUALITY = tuple('sg.' + key + 'Quality' for key in (
    'ViewDistance', 'AntiAliasing', 'Shadow', 'GlobalIllumination', 'Reflection',
    'PostProcess', 'Texture', 'Effects', 'Foliage', 'Shading', 'Landscape'))


def _number(value, minimum=0):
    return type(value) in (int, float) and math.isfinite(value) and value >= minimum


def _point(value):
    return (isinstance(value, list) and len(value) == 3
            and all(type(n) in (int, float) and math.isfinite(n) for n in value))


def summarize_view(view):
    """Use raw wall intervals for FPS, and nearest-rank percentiles for timings."""
    rows = view.get('performanceSamples')
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError('Raw rendered frame samples are required')
    for row in rows:
        if not isinstance(row, dict) or any(not _number(row.get(key)) for key in TIMINGS):
            raise ValueError('Finite nonnegative frame/thread/GPU timings are required')
        if any(row[key] <= 0 for key in ('frameMs', 'gameThreadMs', 'renderThreadMs', 'gpuMs')):
            raise ValueError('Wall, game, render and GPU timers must be available')
        if row.get('streamingRequests') != 0:
            raise ValueError('Measured windows must finish resource streaming')
    seconds = sum(row['frameMs'] for row in rows) / 1000
    declared = view.get('performanceSampleSeconds')
    if not _number(declared, 10) or seconds < 10 or abs(seconds - declared) > max(.1, seconds * .01):
        raise ValueError('At least ten seconds of consistent raw wall timing are required')
    rank = math.ceil(len(rows) * .95) - 1
    return dict(frames=len(rows), seconds=seconds, fps=len(rows) / seconds,
                p95={key: sorted(row[key] for row in rows)[rank] for key in TIMINGS})


def _settings(report):
    settings = report.get('performanceSettings')
    if not isinstance(settings, dict):
        raise ValueError('Actual rendered settings are required')
    resolution, rect = settings.get('viewportSize'), settings.get('viewRect')
    unscaled = settings.get('unscaledViewRect')
    if (not isinstance(resolution, list) or len(resolution) != 2
            or any(type(n) is not int or n <= 0 for n in resolution)
            or not isinstance(rect, list) or len(rect) != 4
            or any(type(n) is not int or n < 0 for n in rect)
            or rect[2] <= rect[0] or rect[3] <= rect[1]
            or not isinstance(unscaled, list) or len(unscaled) != 4
            or any(type(n) is not int or n < 0 for n in unscaled)
            or unscaled[2] <= unscaled[0] or unscaled[3] <= unscaled[1]
            or settings.get('frameLimit') != 0 or settings.get('vSync') != 0
            or settings.get('dynamicResolution') != 0
            or settings.get('frameSmoothing') is not False or settings.get('fixedFrameRate') is not False
            or settings.get('fixedTimeStep') is not False
            or settings.get('timeDilation') != 1
            or not _number(settings.get('effectiveResolutionFraction'), .01)
            or not _number(settings.get('secondaryResolutionFraction'), .01)
            or not _number(settings.get('screenPercentage'))
            or not isinstance(settings.get('quality'), dict)
            or any(type(settings['quality'].get(key)) is not int or not 0 <= settings['quality'][key] <= 4 for key in QUALITY)
            or not isinstance(settings.get('rhi'), str) or not settings['rhi']
            or 'null' in settings['rhi'].lower()):
        raise ValueError('Uncapped actual viewport/render scale/quality/RHI settings are required')
    if abs(settings['effectiveResolutionFraction'] - (rect[2] - rect[0]) / (unscaled[2] - unscaled[0])) > 1e-6:
        raise ValueError('Effective render scale must agree with the actual renderer rectangles')
    return settings


def normalize_native_report(report):
    """Read the native witness directly; preserve original reports and raw samples."""
    result = copy.deepcopy(report)
    result['performanceMode'] = report.get('privatePerformanceMode')
    result['performanceDiagnostic'] = report.get('diagnosticOnly')
    settings = None
    for view in result.get('viewPerformance', []):
        witness = view.get('lightingWitness', {})
        variables = witness.get('consoleVariables', {})
        renderer = view.get('unboundBlendedViewDiagnostic', {})
        if renderer.get('scaledViewRectObserved') is not True:
            raise ValueError('The actual scaled renderer rectangle is required')

        def integer(value):
            if not _number(value) or int(value) != value:
                raise ValueError('Native integer settings must be exact')
            return int(value)

        rect, unscaled = renderer.get('scaledViewRect'), renderer.get('unscaledViewRect')
        if any(not isinstance(value, list) or len(value) != 4 for value in (rect, unscaled)):
            raise ValueError('The actual native view rectangle is required')
        observed = dict(viewportSize=[integer(witness.get('viewportWidth')), integer(witness.get('viewportHeight'))],
                        viewRect=[integer(n) for n in rect], unscaledViewRect=[integer(n) for n in unscaled],
                        frameLimit=variables.get('t.MaxFPS'),
                        vSync=variables.get('r.VSync'), dynamicResolution=variables.get('r.DynamicRes.OperationMode'),
                        screenPercentage=variables.get('r.ScreenPercentage'),
                        effectiveResolutionFraction=renderer.get('effectiveResolutionFraction'),
                        secondaryResolutionFraction=renderer.get('secondaryResolutionFraction'),
                        frameSmoothing=witness.get('frameSmoothing'), fixedFrameRate=witness.get('useFixedFrameRate'),
                        fixedTimeStep=witness.get('fixedTimeStep'), timeDilation=witness.get('worldTimeDilation'),
                        quality={key: integer(variables.get(key)) for key in QUALITY}, rhi=renderer.get('rhi'))
        if settings is not None and settings != observed:
            raise ValueError('Actual graphics settings changed between measured views')
        settings = observed
        samples = view.get('timingSamples')
        if not isinstance(samples, list) or not samples or not _number(view.get('requestedSampleSeconds'), 10):
            raise ValueError('Native raw samples and a ten-second requested window are required')
        elapsed = 0
        for row in samples:
            if not isinstance(row, dict) or not _number(row.get('frameMs')) or not _number(row.get('elapsedSeconds')):
                raise ValueError('Native wall interval and elapsed time are required')
            elapsed += row['frameMs'] / 1000
            if abs(elapsed - row['elapsedSeconds']) > .001:
                raise ValueError('Native elapsed time differs from its raw frame intervals')
        view['performanceSamples'] = samples
        view['performanceSampleSeconds'] = samples[-1]['elapsedSeconds']
    result['performanceSettings'] = settings
    _settings(result)
    _views(result)
    return result


def _views(report):
    if (report.get('passed') is not True or report.get('performanceDiagnostic') is not True
            or any(report.get(key) is not False for key in ('visualApproved', 'citywideAcceptance', 'releaseAcceptance'))
            or report.get('performanceMode') not in MODES):
        raise ValueError('Successful explicit diagnostics with closed acceptance gates are required')
    rows = report.get('viewPerformance')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Rendered views are required')
    result = {}
    for row in rows:
        identity = row.get('id') if isinstance(row, dict) else None
        if not isinstance(identity, str) or not identity or identity in result:
            raise ValueError('Each camera view must have a unique identity')
        if row.get('projection') != 'perspective' or not _number(row.get('fieldOfView'), 10) or row['fieldOfView'] > 120:
            raise ValueError('Gameplay comparisons require a functional perspective camera')
        for key in ('eye', 'direction'):
            if not _point(row.get(key)):
                raise ValueError('Finite camera coordinates are required')
        if abs(sum(n * n for n in row['direction']) - 1) > .001:
            raise ValueError('A unit camera direction is required')
        readiness = row.get('privateMaterialReadiness')
        if not isinstance(readiness, dict) or readiness.get('ready') is not True:
            raise ValueError('Intended shaders must be ready before measurement')
        result[identity] = (row, summarize_view(row))
    return result


def compare_reports(before, after, diagnostic_comparison=False):
    """A shadow-off isolation run cannot be presented as a delivered optimization."""
    if before.get('performanceMode') != 'baseline' or (not diagnostic_comparison and after.get('performanceMode') != 'baseline'):
        raise ValueError('Delivered before/after comparisons require both baseline modes')
    if _settings(before) != _settings(after):
        raise ValueError('Resolution, render scale, quality and timing settings must match')
    old, new = _views(before), _views(after)
    if old.keys() != new.keys():
        raise ValueError('Before and after must measure the same camera views')
    output = []
    for identity, (old_view, old_metrics) in old.items():
        new_view, new_metrics = new[identity]
        if any(old_view.get(key) != new_view.get(key) for key in CAMERA_FIELDS):
            raise ValueError('The camera must remain identical for each comparison')
        output.append(dict(id=identity, before=old_metrics, after=new_metrics,
                           fpsRatio=new_metrics['fps'] / old_metrics['fps'],
                           p95FrameRatio=new_metrics['p95']['frameMs'] / old_metrics['p95']['frameMs']))
    return dict(diagnosticOnly=True, isolationComparison=diagnostic_comparison,
                performanceMode=after['performanceMode'], views=output,
                visualApproved=False, populatedPerformanceVerified=False, releaseAcceptance=False)


def validate_repaired_baseline(before, after):
    """Check actual loaded payloads and retained shadows, not HUD suppression."""
    comparison = compare_reports(before, after)
    old_views, new_views = _views(before), _views(after)

    def shadow_inventory(witness, light_class, mobility=None):
        result = {}
        for light in witness.get('lights', []):
            if (light.get('class') != light_class or light.get('castShadows') is not True
                    or (mobility is not None and light.get('mobility') != mobility)
                    or light.get('registered') is not True or light.get('visible') is not True
                    or light.get('affectsWorld') is not True or light.get('actorHidden') is not False
                    or light.get('hiddenInGame') is not False or not _number(light.get('intensity'), .001)):
                continue
            identity = light.get('component')
            if not isinstance(identity, str) or identity in result:
                raise ValueError('Active shadowed lights require unique native identities')
            result[identity] = {key: light.get(key) for key in (
                'intensity', 'intensityUnits', 'color', 'temperatureK', 'useTemperature',
                'attenuationRadiusCm', 'castStaticShadows', 'castDynamicShadows')}
        if not result:
            raise ValueError('The original shadowed light inventory is required')
        return result

    for identity, (new_view, _) in new_views.items():
        old_witness = old_views[identity][0].get('lightingWitness', {})
        witness = new_view.get('lightingWitness', {})
        variables = witness.get('consoleVariables', {})
        if (type(witness.get('lightingUnbuiltObjects')) is not int or witness['lightingUnbuiltObjects'] != 0
                or type(witness.get('unbuiltReflectionCaptures')) is not int or witness['unbuiltReflectionCaptures'] != 0
                or witness.get('forceNoPrecomputedLighting') is not False
                or variables.get('r.Shadow.UnbuiltPreviewInGame') != 1
                or variables.get('r.Shadow.Virtual.Enable') != 1
                or variables.get('r.ShadowQuality') != old_witness.get('consoleVariables', {}).get('r.ShadowQuality')
                or variables.get('r.ShadowQuality', 0) <= 0):
            raise ValueError('Resolved lighting counts and enabled full-quality shadows are required')
        for light_class, mobility in [('PointLightComponent', None), ('DirectionalLightComponent', 2)]:
            if shadow_inventory(old_witness, light_class, mobility) != shadow_inventory(witness, light_class, mobility):
                raise ValueError('Authored point and movable sun shadows and photometry must remain intact')
        nav = witness.get('navigation', {})
        if (nav.get('available') is not True or nav.get('dirty') is not False
                or nav.get('built') is not True or type(nav.get('registeredBounds')) is not int
                or nav['registeredBounds'] != 1):
            raise ValueError('A clean navigation system with one registered bounds is required')
        rows = [row for row in nav.get('dataActors', []) if 'activeTiles' in row]
        if len(rows) != 2 or {row.get('agent') for row in rows} != {'Default', 'SiegeConvoy'}:
            raise ValueError('Both distinct baked Recast navigation profiles are required')
        for row in rows:
            radius, height = (42, 192) if row['agent'] == 'Default' else (320, 330)
            if (row.get('registeredWithNavigation') is not True or row.get('needsRebuild') is not False
                    or row.get('runtimeGeneration') != 0 or row.get('agentRadiusCm') != radius
                    or row.get('agentHeightCm') != height or type(row.get('activeTiles')) is not int
                    or row.get('tileCountSource') != 'loaded Recast tile headers; public GetNavMeshTileXY'
                    or row['activeTiles'] <= 0 or type(row.get('tileCapacity')) is not int
                    or row['tileCapacity'] < row['activeTiles']):
                raise ValueError('Registered static navigation must contain actual baked tiles for both agents')
        anchors, convoy = nav.get('characterAnchorPaths'), nav.get('convoyPaths')
        if (not isinstance(anchors, list) or len(anchors) != 17
                or any(type(row.get('anchor')) is not int for row in anchors)
                or {row['anchor'] for row in anchors} != set(range(17))
                or any(row.get('projected') is not True or row.get('connected') is not True
                       or row.get('searchLimit') is not False for row in anchors)
                or not isinstance(convoy, list) or len(convoy) != 3
                or any(type(row.get('step')) is not int for row in convoy)
                or {row['step'] for row in convoy} != {1, 2, 3}
                or any(row.get('connected') is not True or not _number(row.get('pathPoints'), 2) for row in convoy)):
            raise ValueError('All seventeen pedestrian anchors and three convoy legs need actual connected native paths')
    comparison['rebuildWarningsResolved'] = True
    comparison['loadedNavigationPayloadVerified'] = True
    comparison['navigationPathQueriesVerified'] = True
    return comparison


def validate_shadow_log(contents):
    """Shadow flags alone do not prove that the renderer served every shadow."""
    if not isinstance(contents, str) or not contents.strip():
        raise ValueError('The native game log is required to check shadow allocation warnings')
    if re.search(r'(?:Virtual Shadow Map Page Pool|One Pass Projection max lights)\s+overflow', contents, re.IGNORECASE):
        raise ValueError('Shadow page/light-capacity overflow remains; rendered shadow quality is incomplete')


if __name__ == '__main__':
    import argparse
    import hashlib
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path, nargs='?')
    parser.add_argument('--isolation', action='store_true', help='Compare an isolation experiment, not a delivered fix')
    parser.add_argument('--require-repair', action='store_true', help='Require actual lighting/navmesh repair with retained point-light shadows')
    args = parser.parse_args()
    try:
        files = [args.before] + ([args.after] if args.after else [])
        reports = [normalize_native_report(json.loads(file.read_text(encoding='utf-8-sig'))) for file in files]
        if args.require_repair and (not args.after or args.isolation):
            raise ValueError('Repair verification requires two ordinary baseline reports')
        if args.after:
            summary = (validate_repaired_baseline(*reports) if args.require_repair
                       else compare_reports(*reports, diagnostic_comparison=args.isolation))
            if args.require_repair:
                log = args.after.parent / 'game.log'
                validate_shadow_log(log.read_text(encoding='utf-8-sig'))
                summary['shadowOverflowLogVerified'] = True
                summary['gameLog'] = dict(path=str(log.resolve()), sha256=hashlib.sha256(log.read_bytes()).hexdigest())
        else:
            if args.isolation: raise ValueError('An isolation comparison requires before and after reports')
            summary = dict(diagnosticOnly=True, performanceMode=reports[0]['performanceMode'],
                           settings=reports[0]['performanceSettings'],
                           views=[dict(id=row['id'], **summarize_view(row)) for row in reports[0]['viewPerformance']],
                           populatedPerformanceVerified=False, releaseAcceptance=False)
        summary['sources'] = [dict(path=str(file.resolve()), sha256=hashlib.sha256(file.read_bytes()).hexdigest()) for file in files]
        print(json.dumps(summary, indent=2))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
