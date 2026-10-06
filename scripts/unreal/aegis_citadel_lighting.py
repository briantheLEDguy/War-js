"""Exact identities for seven copied capital fixtures; no lighting values inferred.

The authored sun and Dutch fill share an actor name. Every edit binds a stable
fixture ID, saved source package, native class/label/tag and complete source state.
The author supplies measured property values after native diagnostics.
"""
import copy
import hashlib
import json
import math


FIXTURES = (
    ('sun', 'DirectionalLight_0', 'DirectionalLight', 'Aegis workbench sun',
     'DirectionalLightComponent', 'authored', 'WarZoneObject_aegis_capital_DirectionalLight_0'),
    ('soft_sky_fill', 'DirectionalLight_1', 'DirectionalLight', 'Crownward soft sky fill',
     'DirectionalLightComponent', 'authored', 'WarZoneObject_aegis_capital_DirectionalLight_1'),
    ('ambient_sky', 'SkyLight_0', 'SkyLight', 'Aegis workbench sky',
     'SkyLightComponent', 'authored', 'WarZoneObject_aegis_capital_SkyLight_0'),
    ('distance_haze', 'ExponentialHeightFog_0', 'ExponentialHeightFog', 'Crownward cold distance haze',
     'ExponentialHeightFogComponent', 'authored', 'WarZoneObject_aegis_capital_ExponentialHeightFog_0'),
    ('exposure', 'PostProcessVolume_0', 'PostProcessVolume', 'Aegis daylight exposure',
     None, 'authored', 'WarZoneObject_aegis_capital_PostProcessVolume_0'),
    ('atmosphere', 'SkyAtmosphere_0', 'SkyAtmosphere', 'Aegis atmosphere',
     'SkyAtmosphereComponent', 'authored', 'WarZoneObject_aegis_capital_SkyAtmosphere_0'),
    ('dutch_street_fill', 'DirectionalLight_0', 'DirectionalLight', 'Bastion overcast street fill',
     'DirectionalLightComponent', 'Bastion_Dutch_Geometry', 'WarWorldObject_dutch_bastion_overcast_fill'))

# This bounds which source fields a later signed recipe can change. The exact
# chosen field set and values also belong to that recipe and its native readback.
PROPERTY_ALLOWANCES = {
    'sun': {'intensity', 'temperature', 'use_temperature', 'cast_shadows', 'cast_dynamic_shadows',
            'atmosphere_sun_light', 'atmosphere_sun_light_index', 'forward_shading_priority', 'light_source_angle'},
    'soft_sky_fill': {'intensity', 'use_temperature', 'cast_shadows', 'cast_dynamic_shadows',
                     'atmosphere_sun_light', 'light_color'},
    'ambient_sky': {'intensity', 'real_time_capture', 'lower_hemisphere_is_black',
                    'lower_hemisphere_color', 'light_color', 'indirect_lighting_intensity'},
    'distance_haze': {'fog_density', 'fog_height_falloff', 'start_distance', 'fog_max_opacity',
                      'enable_volumetric_fog', 'fog_inscattering_luminance'},
    'exposure': {'override_auto_exposure_method', 'auto_exposure_method',
                'override_auto_exposure_apply_physical_camera_exposure', 'auto_exposure_apply_physical_camera_exposure',
                'override_auto_exposure_bias', 'auto_exposure_bias', 'override_auto_exposure_min_brightness',
                'auto_exposure_min_brightness', 'override_auto_exposure_max_brightness', 'auto_exposure_max_brightness',
                'override_histogram_log_min', 'histogram_log_min', 'override_histogram_log_max', 'histogram_log_max',
                'override_auto_exposure_speed_up', 'auto_exposure_speed_up', 'override_auto_exposure_speed_down',
                'auto_exposure_speed_down', 'override_color_saturation', 'color_saturation',
                'override_bloom_intensity', 'bloom_intensity', 'override_lens_flare_intensity', 'lens_flare_intensity'},
    'atmosphere': {'transform_mode', 'bottom_radius', 'ground_albedo', 'atmosphere_height',
                   'multi_scattering_factor', 'trace_sample_count_scale', 'rayleigh_scattering_scale',
                   'rayleigh_scattering', 'rayleigh_exponential_distribution', 'mie_scattering_scale',
                   'mie_scattering', 'mie_absorption_scale', 'mie_absorption', 'mie_anisotropy',
                   'mie_exponential_distribution', 'other_absorption_scale', 'other_absorption',
                   'sky_luminance_factor', 'sky_and_aerial_perspective_luminance_factor',
                   'aerial_pespective_view_distance_scale', 'height_fog_contribution',
                   'transmittance_min_light_elevation_angle', 'aerial_perspective_start_depth'},
    'dutch_street_fill': {'intensity', 'use_temperature', 'cast_shadows', 'cast_dynamic_shadows',
                         'atmosphere_sun_light', 'light_color'}}
PROPERTY_ALLOWANCES['exposure'].update({'override_dynamic_global_illumination_method', 'dynamic_global_illumination_method',
                                       'override_reflection_method', 'reflection_method'})

# These two actual inherited values (.17586599,20) caused measured ground
# transmission RGB(.253436,.041374,.000501). Restore only the primary-engine
# Rayleigh defaults; preserve every other committed atmosphere property.
MEASURED_ATMOSPHERE_REPAIR = dict(rayleigh_scattering_scale=.0331, rayleigh_exponential_distribution=8)
REVIEWED_CLOUD_MATERIAL = '/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst'
CLOUD_IDENTITY = dict(id='citadel_cloud', actor='VolumetricCloud_0', klass='VolumetricCloud',
                      component='VolumetricCloudComponent', label='Bastion mountain cloud canopy',
                      requiredTag='WarWorldObject_aegis_citadel_cloud')
CLOUD_PROPERTIES = dict(layer_bottom_altitude=.5, layer_height=1.2,
                        view_sample_count_scale=2, shadow_view_sample_count_scale=2)


def reference_fixture_requests(existing_five):
    """Measured repair recipe; owned clouds and practical lights bind separately."""
    if not isinstance(existing_five, (tuple, list)) or len(existing_five) != 5:
        raise ValueError('Preserve the five existing signed environment fixtures')
    result = []
    for fixture_id, actor, klass, label, component, _, _ in FIXTURES[:5]:
        matches = [r for r in existing_five if r.get('actor') == actor and r.get('klass') == klass
                   and r.get('label') == label and r.get('component') == component]
        if len(matches) != 1:
            raise ValueError('Existing native lighting recipe identity changed: ' + fixture_id)
        source = matches[0]
        request = dict(id=fixture_id, properties=copy.deepcopy(source['properties']))
        if 'rotationDegrees' in source:
            request['rotationDegrees'] = copy.deepcopy(source['rotationDegrees'])
        if fixture_id == 'sun':
            request['rotationDegrees'] = [-20, 30, 0]
        if fixture_id == 'ambient_sky':
            request['properties']['intensity'] = .35
        if fixture_id == 'soft_sky_fill':
            request['properties'].update(intensity=800, cast_shadows=True, cast_dynamic_shadows=True)
        if fixture_id == 'distance_haze':
            request['properties'].update(fog_density=.006, start_distance=7000, fog_max_opacity=.4)
        if fixture_id == 'exposure':
            request['properties'].update(override_dynamic_global_illumination_method=True,
                dynamic_global_illumination_method=dict(kind='enum', type='DynamicGlobalIlluminationMethod', value='SCREEN_SPACE'),
                override_reflection_method=True,
                reflection_method=dict(kind='enum', type='ReflectionMethod', value='SCREEN_SPACE'))
        result.append(request)
    result.append(dict(id='atmosphere', properties=copy.deepcopy(MEASURED_ATMOSPHERE_REPAIR)))
    result.append(dict(id='dutch_street_fill', properties=dict(intensity=0, use_temperature=False,
        cast_shadows=True, cast_dynamic_shadows=True, atmosphere_sun_light=False,
        light_color=dict(kind='color', value=[173,192,218,255]))))
    return result


def shadowed_practical_requests(existing):
    """Preserve authored placement/power/shape while preventing through-wall fill."""
    result = copy.deepcopy(existing)
    for row in result:
        if not isinstance(row, dict) or row.get('mobility') != 'movable' or 'castShadows' not in row:
            raise ValueError('Unknown original architectural practical light')
        row['castShadows'] = True
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def fixture_catalog(baseline):
    """Resolve all seven identities from actual baseline snapshots, fail on ambiguity."""
    result = []
    for fixture_id, actor, klass, label, component, layer, tag in FIXTURES:
        matches = [(package, row) for package, rows in baseline['actors'].items() for row in rows
                   if package.endswith('/Layers/' + layer) and row['actor'] == actor
                   and row['state']['class'] == klass and row['state']['label'] == label
                   and tag in row['state']['tags']]
        if len(matches) != 1:
            raise ValueError('Unknown or ambiguous copied lighting fixture: ' + fixture_id)
        package, row = matches[0]
        package_hash = baseline['packageHashes'].get(package)
        if not isinstance(package_hash, str) or len(package_hash) != 64 or any(c not in '0123456789abcdef' for c in package_hash):
            raise ValueError('Missing exact saved source package hash: ' + fixture_id)
        result.append(dict(id=fixture_id, actor=actor, klass=klass, label=label, component=component,
                           package=package, requiredTag=tag, sourceStateHash=digest(row['state']),
                           sourcePackageSha256=package_hash))
    return result


def checked_value(value):
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)) and math.isfinite(value):
        return
    if not isinstance(value, dict):
        raise ValueError('Signed lighting property has an unsupported native value')
    if value.get('kind') == 'enum':
        allowed = {'AutoExposureMethod': {'AEM_HISTOGRAM'}, 'DynamicGlobalIlluminationMethod': {'SCREEN_SPACE'},
                   'ReflectionMethod': {'SCREEN_SPACE'}, 'SkyAtmosphereTransformMode': {
            'PLANET_TOP_AT_ABSOLUTE_WORLD_ORIGIN', 'PLANET_TOP_AT_COMPONENT_TRANSFORM', 'PLANET_CENTER_AT_COMPONENT_TRANSFORM'}}
        if set(value) != {'kind', 'type', 'value'} or value.get('value') not in allowed.get(value.get('type'), set()):
            raise ValueError('Unknown signed native lighting enum')
        return
    if (set(value) != {'kind', 'value'} or value.get('kind') not in ('color', 'linear_color', 'vector4')
            or not isinstance(value['value'], list) or len(value['value']) != 4
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value['value'])):
        raise ValueError('Invalid named-channel native lighting value')
    if value['kind'] == 'color' and any(type(v) is not int or not 0 <= v <= 255 for v in value['value']):
        raise ValueError('FColor channels must be exact bytes')


def bind_fixture_edits(baseline, requested):
    """Attach measured, explicit edits to original native state; choose no defaults."""
    if (not isinstance(requested, list) or any(not isinstance(r, dict) for r in requested)
            or {r.get('id') for r in requested} != {row[0] for row in FIXTURES} or len(requested) != 7):
        raise ValueError('Exactly seven distinct copied fixture IDs are required')
    by_id = {r['id']: r for r in requested}
    result = []
    for identity in fixture_catalog(baseline):
        edit = by_id[identity['id']]
        if set(edit) - {'id', 'properties', 'rotationDegrees'}:
            raise ValueError('A fixture edit cannot replace its source identity')
        properties = edit.get('properties')
        if not isinstance(properties, dict) or not properties or set(properties) - PROPERTY_ALLOWANCES[identity['id']]:
            raise ValueError('Unsigned or unbounded lighting property change: ' + identity['id'])
        for value in properties.values():
            checked_value(value)
        rotation = edit.get('rotationDegrees')
        if rotation is not None and (identity['id'] not in ('sun', 'soft_sky_fill', 'dutch_street_fill')
                or not isinstance(rotation, list) or len(rotation) != 3
                or any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in rotation)):
            raise ValueError('Unexpected copied fixture rotation edit')
        result.append(dict(**identity, **copy.deepcopy({k: v for k, v in edit.items() if k != 'id'})))
    return result


def expected_copied_fixture(spec, source_package, actor_name, state):
    """Called on the exact copied layer, never as a global actor-name exception."""
    return (source_package == spec['package'] and actor_name == spec['actor']
            and state['class'] == spec['klass'] and state['label'] == spec['label']
            and spec['requiredTag'] in state['tags'])
