"""Opt-in private fixture/practical recipe. Contains no Unreal or filesystem calls."""
import copy
import math
import re

FIXTURE_IDS = {'sun', 'soft_sky_fill', 'ambient_sky', 'distance_haze', 'exposure', 'atmosphere', 'dutch_street_fill'}
LIGHT_IDS = {*(f'hall_sconce_{i}' for i in range(8)), *(f'portal_reveal_{i}' for i in range(2)),
             *(f'gate_fire_pool_{i}' for i in range(4)), *(f'court_fire_pool_{i}' for i in range(4))}
SOURCE_KEYS = {'blueprint', 'candidate', 'stager', 'fixtureHelper', 'twilightHelper'}
FIXTURE_DELTAS = {
    'sun': dict(intensity=1200, temperature=6800, use_temperature=True, light_source_angle=3),
    'soft_sky_fill': dict(intensity=700),
    'ambient_sky': dict(intensity=1.4),
    'distance_haze': dict(fog_density=.0075, start_distance=6500, fog_max_opacity=.45),
    'exposure': dict(auto_exposure_min_brightness=16, auto_exposure_max_brightness=1024,
                     auto_exposure_bias=-.35, bloom_intensity=.22),
}
SUN_ROTATION = [-8, -65, 0]
DIRECTIONAL_ROTATIONS = dict(sun=SUN_ROTATION, soft_sky_fill=[-65, 0, 0])


def checked_option(value):
    if value in ('', '0'): return False
    if value == '1': return True
    raise ValueError('WAR_CITADEL_TWILIGHT_FIRE_STUDY must be absent, 0 or 1')


def _require(value, message):
    if not value: raise ValueError(message)


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def comparison(mode, fixtures, lights, exposure_units, extended_ev100, source_bindings):
    _require(mode in ('lumen_software', 'lumen_hardware'), 'Twilight requires a private Lumen fixture request')
    _require(exposure_units == 'native_luminance' and extended_ev100 is False, 'Require actual legacy luminance exposure')
    _require(set(source_bindings) == SOURCE_KEYS and all(isinstance(v, str) and re.fullmatch('[a-f0-9]{64}', v)
             for v in source_bindings.values()), 'Complete source hash assumptions are required')
    _require(len(fixtures) == 7 and {r['id'] for r in fixtures} == FIXTURE_IDS, 'Require all seven unique fixtures')
    _require(len(lights) == 18 and {r['id'] for r in lights} == LIGHT_IDS, 'Require all eighteen exact existing practicals')
    requests = copy.deepcopy(fixtures)
    by_id = {row['id']: row for row in requests}
    exposure = by_id['exposure']['properties']
    _require(exposure.get('auto_exposure_method') == dict(kind='enum', type='AutoExposureMethod', value='AEM_HISTOGRAM')
             and exposure.get('auto_exposure_apply_physical_camera_exposure') is False, 'Unknown exposure metering mode')
    for field in ('auto_exposure_min_brightness', 'auto_exposure_max_brightness', 'auto_exposure_bias', 'bloom_intensity'):
        _require(exposure.get('override_' + field) is True, 'Exposure override must already be explicit: ' + field)
    for fixture, deltas in FIXTURE_DELTAS.items():
        for field in deltas:
            old = by_id[fixture]['properties'].get(field)
            _require(type(old) is bool if type(deltas[field]) is bool else _finite(old), 'Unknown source fixture property: ' + field)
        by_id[fixture]['properties'].update(copy.deepcopy(deltas))
    for fixture, rotation in DIRECTIONAL_ROTATIONS.items():
        by_id[fixture]['rotationDegrees'] = copy.deepcopy(rotation)
    practicals = []
    for light in lights:
        _require(light.get('mobility') == 'movable' and light.get('castShadows') is True, 'Existing movable shadowed practical required')
        _require(len(light['pointCm']) == 3 and all(_finite(v) for v in light['pointCm']), 'Invalid practical origin')
        for field in ('intensityCd', 'attenuationRadiusCm', 'sourceRadiusCm', 'temperatureK'):
            _require(_finite(light[field]) and light[field] > 0, 'Invalid practical source value: ' + field)
        factor = 4 if light['id'].startswith(('gate_fire_pool_', 'court_fire_pool_')) else 1.5 if light['id'].startswith('portal_reveal_') else 1
        practicals.append(dict(id=light['id'], pointCm=copy.deepcopy(light['pointCm']),
                              sourceIntensityCd=light['intensityCd'], intensityCd=light['intensityCd'] * factor))
    spec = dict(schemaVersion=1, recipeVersion=2, diagnosticOnly=True, profile='cool_twilight_fire_v2', independentOptIn=True,
        backendMode=mode, sourceBindings=copy.deepcopy(source_bindings), fixtureDeltas=copy.deepcopy(FIXTURE_DELTAS),
        sunRotationDegrees=copy.deepcopy(SUN_ROTATION), directionalRotations=copy.deepcopy(DIRECTIONAL_ROTATIONS),
        practicalRequests=copy.deepcopy(practicals),
        sourcePracticals=copy.deepcopy(lights), exposureUnits='native_luminance', expectedExtendedEV100=False,
        cloudRecipeChanged=False, materialGraphsChanged=False, newLightsAdded=False, lightShapesOrOriginsChanged=False,
        geometryOrGameplayChanged=False, savedPreferencesChanged=False, nativeReadbacksVerified=False,
        intendedMaterialReadinessRequired=True, coldPackageReadbacksRequired=True,
        rendererStateVerified=False, visualApproved=False, gameplayApproved=False, releaseAcceptance=False)
    return requests, practicals, spec


def _matches(actual, wanted, tolerance=1e-5):
    if type(wanted) is bool: return actual is wanted
    return _finite(actual) and abs(actual - wanted) <= max(tolerance, abs(wanted) * 1e-6)


def checked_readbacks(spec, fixtures, practicals, directional_lights, destination):
    """Editor object readbacks remain distinct from cold resources and images."""
    _require(re.fullmatch('/Game/WorldRebuild/AegisCitadel_[a-f0-9]{12}', destination), 'Require exact owned study namespace')
    _require(len(fixtures) == 7 and {r['id'] for r in fixtures} == FIXTURE_IDS, 'Incomplete native fixture readbacks')
    _require(len(practicals) == 18 and {r['id'] for r in practicals} == LIGHT_IDS, 'Incomplete native practical readbacks')
    by_id = {r['id']: r for r in fixtures}
    for row in [*fixtures, *practicals]:
        _require(row['actor'].startswith(destination + '/Layers/'), 'Readback escaped owned copied layer')
    for fixture, deltas in spec['fixtureDeltas'].items():
        _require(all(_matches(by_id[fixture]['properties'].get(field), value) for field, value in deltas.items()),
                 'Native fixture did not retain twilight values: ' + fixture)
    for fixture, rotation in spec['directionalRotations'].items():
        matches = [r for r in directional_lights if r['actor'] == by_id[fixture]['actor']]
        _require(len(matches) == 1 and len(matches[0]['rotationDegrees']) == 3
                 and all(_matches(a, b) for a, b in zip(matches[0]['rotationDegrees'], rotation)),
                 'Wrong actual directional rotation: ' + fixture)
    wanted = {r['id']: r for r in spec['practicalRequests']}
    source = {r['id']: r for r in spec['sourcePracticals']}
    for row in practicals:
        request, original = wanted[row['id']], source[row['id']]
        _require(row['castShadows'] is True and row['visibility'] == dict(actorHidden=False, componentVisible=True,
                 componentHiddenInGame=False), 'Hidden or shadowless practical')
        _require(_matches(row['intensityCd'], request['intensityCd']) and _matches(row['temperatureK'], original['temperatureK'])
                 and _matches(row['attenuationRadiusCm'], original['attenuationRadiusCm'])
                 and _matches(row['sourceRadiusCm'], original['sourceRadiusCm']) and row['mobility'] == 'movable',
                 'Changed practical power or shape')
        for key in ('pointCm', 'originalPointCm'):
            _require(len(row[key]) == 3 and all(_matches(a, b, .01) for a, b in zip(row[key], original['pointCm'])), 'Moved practical origin')
    return dict(nativeReadbacksVerified=True, coldProcessVerified=False, rendererStateVerified=False,
                visualApproved=False, gameplayApproved=False, releaseAcceptance=False)
