"""Private Lumen requests and diagnostic gates; never renderer acceptance."""
import copy

PRIVATE_LUMEN_MODES = ('lumen_software', 'lumen_hardware')
FIXTURE_IDS = ('sun', 'soft_sky_fill', 'ambient_sky', 'distance_haze',
               'exposure', 'atmosphere', 'dutch_street_fill')


def runtime_recipe(mode):
    if mode not in PRIVATE_LUMEN_MODES:
        raise ValueError('Unknown private Lumen backend')
    # Override individual gates after graphics initialization, never saved sg.* groups.
    values = {'r.Lumen.DiffuseIndirect.Allow': 1, 'r.Lumen.Reflections.Allow': 1,
              'r.Lumen.FinalGatherMethod': 1,
              'r.Lumen.HardwareRayTracing': int(mode == 'lumen_hardware')}
    if mode == 'lumen_software':
        values.update({'r.Lumen.TraceMeshSDFs': 1, 'r.Lumen.TraceMeshSDFs.Allow': 1,
                       'r.Lumen.ScreenProbeGather.TraceMeshSDFs': 1, 'r.Lumen.Reflections.TraceMeshSDFs': 1})
    else:
        values.update({'r.Lumen.ScreenProbeGather.HardwareRayTracing': 1,
                       'r.Lumen.Reflections.HardwareRayTracing': 1})
    return values


def private_lumen_comparison(mode, fixtures, cloud_fixture):
    """Change only the exposure fixture's GI/reflection method overrides."""
    if mode not in PRIVATE_LUMEN_MODES:
        raise ValueError('Unknown private Lumen backend')
    if (len(fixtures) != len(FIXTURE_IDS)
            or {r.get('id') for r in fixtures} != set(FIXTURE_IDS)):
        raise ValueError('All seven unique signed lighting fixtures are required')
    from aegis_citadel_reference_material import reference_cloud_comparison
    cloud = reference_cloud_comparison(cloud_fixture)
    requests = copy.deepcopy(fixtures)
    exposure = next(r for r in requests if r['id'] == 'exposure')['properties']
    for prop, enum_type in (('dynamic_global_illumination_method', 'DynamicGlobalIlluminationMethod'),
                            ('reflection_method', 'ReflectionMethod')):
        exposure['override_' + prop] = True
        exposure[prop] = dict(kind='enum', type=enum_type, value='LUMEN')
    spec = dict(schemaVersion=1, diagnosticOnly=True, mode=mode,
                requestedBackend='software' if mode == 'lumen_software' else 'hardware',
                runtimeCvars=runtime_recipe(mode), overrideScope='private_process_after_graphics_init',
                screenTracesRetained=True, surfaceCacheLightingRetained=True,
                rendererStateVerified=False, lightingApproved=False,
                nativeResourceAuditRequired=True, blendedViewReadbackRequired=True,
                rendererPassWitnessRequired=True)
    return requests, cloud, spec


def _actual_int(cvars, name):
    row = cvars.get(name)
    if (not isinstance(row, dict) or row.get('available') is not True
            or type(row.get('value')) is not int
            or type(row.get('setByFlags')) is not int):
        raise ValueError('Unavailable native CVar or priority: ' + name)
    return row['value']


def review_resources(mode, meshes, expected_mesh_paths):
    """Built resource presence permits a diagnostic; it does not prove coverage."""
    if mode not in PRIVATE_LUMEN_MODES or not meshes:
        raise ValueError('Backend and complete opaque static-mesh inventory are required')
    paths = [m.get('mesh') for m in meshes]
    if any(not isinstance(p, str) or not p for p in paths) or len(set(paths)) != len(paths):
        raise ValueError('Unique native mesh paths are required')
    if (not expected_mesh_paths or any(not isinstance(p, str) or not p for p in expected_mesh_paths)
            or len(set(expected_mesh_paths)) != len(expected_mesh_paths)
            or set(paths) != set(expected_mesh_paths)):
        raise ValueError('Native mesh audit must match the complete source-bound opaque mesh inventory')
    for mesh in meshes:
        if mesh.get('available') is not True or mesh.get('compiling') is not False:
            raise ValueError('Native mesh data is unavailable or still compiling')
        cards = mesh.get('cards', {})
        if (cards.get('present') is not True or cards.get('finite') is not True
                or type(cards.get('count')) is not int or cards['count'] <= 0):
            raise ValueError('Missing or invalid native Lumen mesh cards: ' + mesh['mesh'])
        if mode == 'lumen_software':
            df = mesh.get('distanceField', {})
            if (df.get('present') is not True or df.get('valid') is not True
                    or df.get('asyncBuilding') is not False
                    or type(df.get('alwaysLoadedBytes')) is not int or df['alwaysLoadedBytes'] <= 0
                    or type(df.get('bricks')) is not int or df['bricks'] <= 0):
                raise ValueError('Missing or unfinished native distance field: ' + mesh['mesh'])
        else:
            rt = mesh.get('rayTracing', {})
            if any(rt.get(k) is not True for k in ('present', 'validInitializer', 'valid', 'rhiPresent')):
                raise ValueError('Missing native ray-tracing geometry: ' + mesh['mesh'])
            if rt.get('requiresBuild') is not False:
                raise ValueError('Native ray-tracing geometry still needs a build: ' + mesh['mesh'])
    return dict(resourcePresenceReady=True, surfaceCacheCoverageVerified=False,
                runtimeSceneMembershipVerified=False, rendererStateVerified=False)


def review_view(mode, view, nonce, image_frame):
    """Check a frame-matched public view readback; actual pass/backend remains unknown."""
    recipe = runtime_recipe(mode)
    if (not isinstance(nonce, str) or not nonce or type(image_frame) is not int or image_frame < 0
            or view.get('available') is not True or view.get('readThread') != 'render'
            or view.get('nonce') != nonce or type(view.get('frameNumber')) is not int
            or view['frameNumber'] != image_frame or type(view.get('viewCount')) is not int
            or view['viewCount'] != 1
            or view.get('captureBindingVerified') is not True):
        raise ValueError('An independently frame-matched single game view is required')
    if view.get('giMethod') != 'Lumen' or view.get('reflectionMethod') != 'Lumen':
        raise ValueError('Final blended view did not select both Lumen methods')
    cvars = view.get('cvars', {})
    for name, wanted in recipe.items():
        if _actual_int(cvars, name) != wanted:
            raise ValueError('Private study CVar did not retain its value: ' + name)
    if _actual_int(cvars, 'r.Lumen.Supported') != 1 or _actual_int(cvars, 'r.ForwardShading') != 0:
        raise ValueError('Project Lumen support or deferred rendering is unavailable')
    if any(view.get(k) is not True for k in ('projectSupportsLumen', 'platformSupportsLumen', 'viewStatePresent')):
        raise ValueError('Native view/platform Lumen prerequisites failed')
    flags = view.get('showFlags', {})
    if any(flags.get(k) is not True for k in ('Lighting', 'GlobalIllumination', 'LumenGlobalIllumination', 'LumenReflections')):
        raise ValueError('View show flags disable Lumen')
    if flags.get('PathTracing') is not False or flags.get('RayTracingDebug') is not False:
        raise ValueError('View is a different renderer path')
    if mode == 'lumen_software':
        if (view.get('projectSupportsDistanceFields') is not True
                or _actual_int(cvars, 'r.GenerateMeshDistanceFields') != 1
                or flags.get('LumenDetailTraces') is not True or flags.get('LumenGlobalTraces') is not True):
            raise ValueError('Native software distance-field tracing prerequisites failed')
    else:
        if (_actual_int(cvars, 'r.RayTracing') != 1
                or _actual_int(cvars, 'r.SkinCache.CompileShaders') < 1
                or view.get('rayTracingEnabledForProject') is not True
                or view.get('rayTracingEnabled') is not True
                or view.get('rayTracingAllowedForView') is not True
                or not (view.get('supportsInlineRayTracing') is True
                        or (view.get('supportsRayTracingShaders') is True
                            and view.get('supportsRayTracingDispatchIndirect') is True))):
            raise ValueError('Hardware backend is unavailable; software fallback is not this comparison')
    # Even perfect public view readback cannot observe private FViewInfo pass selection.
    return dict(resolvedViewPrerequisitesReady=True, captureBindingVerified=True,
                requestedBackend=mode.removeprefix('lumen_'), actualBackend=None,
                rendererStateVerified=False, lightingApproved=False)
