"""Read exact private-capital lighting state; never preview, edit or save Content.

Root runs this with Unreal writers serialized and an explicit 12-hex revision.
Editor CVars are observed values, not a claim about a separate game's view flags.
"""
import json
import math
import os
import re
import sys
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT, sha
from shared_city_sources import package_file, protected_source_file
from world_actor_state import value_repr

revision = os.environ.get('WAR_CITADEL_INSPECT_REVISION', '')
if not re.fullmatch('[a-f0-9]{12}', revision):
    raise RuntimeError('An explicit lowercase 12-hex citadel inspection revision is required')
RUN = OUT / revision
candidate_file = RUN / 'candidate.json'
source_file = RUN / 'assets-source.json'
candidate = json.loads(candidate_file.read_text())
source = json.loads(source_file.read_text())
expected = {**candidate['sourceHashes'], **candidate['packageHashes']}
study_id = os.environ.get('WAR_CITADEL_INSPECT_STUDY', '')
study = None
if study_id:
    if not re.fullmatch('[a-f0-9]{12}', study_id):
        raise RuntimeError('An explicit lowercase 12-hex lighting study is required')
    study_file = RUN / ('lighting-study-' + study_id) / 'study.json'
    study = json.loads(study_file.read_text())
    if (study.get('diagnosticOnly') is not True
            or study.get('historicalGeometryRevision') != revision
            or study.get('signature', '')[:12] != study_id
            or study.get('blueprintSha256') != sha(RUN / 'blueprint.json')
            or study.get('sourceAndCandidateHashesUnchanged') is not True):
        raise RuntimeError('Study identity differs from its preserved source candidate')
    for package, expected_hash in study['createdPackageHashes'].items():
        if not package.startswith('/Game/WorldRebuild/AegisCitadel_' + study_id + '/'):
            raise RuntimeError('Study receipt contains an unowned package')
        if package in expected and expected[package] != expected_hash:
            raise RuntimeError('Conflicting candidate/study package hashes')
        expected[package] = expected_hash
map_path = study['map'] if study else candidate['siegeMap']
def inspected_package(package):
    if package in candidate['sourceHashes']:
        return protected_source_file(ROOT, package, expected[package])
    return package_file(ROOT, package)


before = {p: sha(inspected_package(p)) for p in expected}
if before != expected:
    raise RuntimeError('Preserve independently edited candidate/source packages')
unavailable = []


def serial(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else dict(nonfinite=str(value))
    if hasattr(value, 'get_path_name'):
        return value.get_path_name()
    # Named channels avoid the reflected FColor constructor's BGRA ordering.
    for fields in (('r', 'g', 'b', 'a'), ('pitch', 'yaw', 'roll'),
                   ('x', 'y', 'z', 'w'), ('x', 'y', 'z')):
        if all(hasattr(value, key) for key in fields):
            return {key: serial(getattr(value, key)) for key in fields}
    if isinstance(value, (list, tuple, unreal.Array)):
        return [serial(v) for v in value]
    return value_repr(value)[:2048]


def read(obj, names):
    result = {}
    for name in names:
        try:
            result[name] = serial(obj.get_editor_property(name))
        except Exception as error:
            unavailable.append(dict(object=serial(obj), property=name, error=str(error)[:512]))
    return result


def call(obj, name, *args):
    try:
        return getattr(obj, name)(*args)
    except Exception as error:
        unavailable.append(dict(object=serial(obj), method=name, error=str(error)[:512]))
        return None


def component_state(component):
    return dict(path=component.get_path_name(), klass=component.get_class().get_name(),
                values=read(component, ('mobility', 'visible', 'hidden_in_game')),
                isVisible=call(component, 'is_visible'),
                location=serial(call(component, 'get_world_location')),
                rotation=serial(call(component, 'get_world_rotation')),
                forward=serial(call(component, 'get_forward_vector')))


ATMOSPHERE_KEYS = (
    'transform_mode', 'bottom_radius', 'ground_albedo', 'atmosphere_height',
    'multi_scattering_factor', 'trace_sample_count_scale',
    'rayleigh_scattering_scale', 'rayleigh_scattering', 'rayleigh_exponential_distribution',
    'mie_scattering_scale', 'mie_scattering', 'mie_absorption_scale', 'mie_absorption',
    'mie_anisotropy', 'mie_exponential_distribution', 'other_absorption_scale',
    'other_absorption', 'sky_luminance_factor', 'sky_and_aerial_perspective_luminance_factor',
    'aerial_pespective_view_distance_scale', 'height_fog_contribution',
    'transmittance_min_light_elevation_angle', 'aerial_perspective_start_depth',
    'holdout', 'render_in_main_pass')
LIGHT_KEYS = (
    'intensity', 'light_color', 'use_temperature', 'temperature', 'affects_world',
    'cast_shadows', 'cast_dynamic_shadows', 'cast_static_shadows',
    'indirect_lighting_intensity', 'volumetric_scattering_intensity',
    'affect_translucent_lighting', 'lighting_channels')
DIRECTIONAL_KEYS = (
    'atmosphere_sun_light', 'atmosphere_sun_light_index', 'atmosphere_sun_disk_color_scale',
    'per_pixel_atmosphere_transmittance', 'cast_shadows_on_clouds',
    'cast_shadows_on_atmosphere', 'cast_cloud_shadows', 'forward_shading_priority',
    'light_source_angle', 'light_source_soft_angle', 'dynamic_shadow_distance_movable_light',
    'dynamic_shadow_distance_stationary_light', 'dynamic_shadow_cascades',
    'cascade_distribution_exponent', 'cascade_transition_fraction',
    'shadow_distance_fadeout_fraction', 'distance_field_shadow_distance')
PP_KEYS = (
    'auto_exposure_method', 'auto_exposure_bias', 'auto_exposure_apply_physical_camera_exposure',
    'auto_exposure_min_brightness', 'auto_exposure_max_brightness', 'histogram_log_min',
    'histogram_log_max', 'auto_exposure_speed_up', 'auto_exposure_speed_down',
    'auto_exposure_low_percent', 'auto_exposure_high_percent', 'auto_exposure_bias_curve',
    'auto_exposure_meter_mask', 'camera_iso', 'camera_shutter_speed', 'depth_of_field_fstop',
    'color_saturation', 'color_gamma', 'color_gain', 'color_offset', 'color_contrast',
    'color_saturation_shadows', 'color_gamma_shadows', 'color_gain_shadows',
    'color_saturation_midtones', 'color_gamma_midtones', 'color_gain_midtones',
    'color_saturation_highlights', 'color_gamma_highlights', 'color_gain_highlights',
    'white_temp', 'white_tint', 'film_slope', 'film_toe', 'film_shoulder',
    'film_black_clip', 'film_white_clip', 'bloom_intensity', 'lens_flare_intensity',
    'ambient_cubemap', 'ambient_cubemap_intensity', 'ambient_cubemap_tint',
    'indirect_lighting_color', 'indirect_lighting_intensity',
    'dynamic_global_illumination_method', 'reflection_method',
    'lumen_scene_lighting_quality', 'lumen_scene_detail', 'lumen_scene_view_distance',
    'lumen_final_gather_quality', 'lumen_max_trace_distance', 'lumen_skylight_leaking',
    'lumen_full_skylight_leaking_distance', 'ambient_occlusion_intensity',
    'ambient_occlusion_radius', 'local_exposure_highlight_contrast_scale',
    'local_exposure_shadow_contrast_scale', 'local_exposure_detail_strength')
CVARS = (
    'r.DynamicGlobalIlluminationMethod', 'r.ReflectionMethod', 'r.GenerateMeshDistanceFields',
    'r.DistanceFieldAO', 'r.AOQuality', 'r.AllowStaticLighting', 'r.ForwardShading',
    'r.RayTracing', 'r.Lumen.HardwareRayTracing', 'r.Lumen.DiffuseIndirect.Allow',
    'r.Lumen.TraceMeshSDFs.Allow', 'r.Lumen.ScreenProbeGather.ScreenTraces',
    'r.Shadow.Virtual.Enable', 'r.ShadowQuality', 'r.Shadow.DistanceScale',
    'r.Shadow.CSM.MaxCascades', 'r.SupportSkyAtmosphere', 'r.SkyAtmosphere',
    'r.SkyAtmosphere.FastSkyLUT', 'r.SkyAtmosphere.MultiScatteringLUT.HighQuality',
    'r.SkyAtmosphere.AerialPerspectiveLUT.FastApplyOnOpaque',
    'r.SupportSkyAtmosphereAffectsHeightFog', 'r.DefaultFeature.AutoExposure',
    'r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange', 'r.EyeAdaptationQuality',
    'r.UsePreExposure', 'r.TonemapperGamma', 'r.TonemapperFilm',
    'r.Color.Mid', 'r.Color.Min', 'r.Color.Max', 'r.ScreenPercentage',
    'sg.GlobalIlluminationQuality', 'sg.ReflectionQuality', 'sg.ShadowQuality',
    'ShowFlag.Atmosphere', 'ShowFlag.SkyLighting', 'ShowFlag.Lighting',
    'ShowFlag.DynamicShadows', 'ShowFlag.PostProcessing', 'ShowFlag.Tonemapper',
    'ShowFlag.EyeAdaptation', 'ShowFlag.GlobalIllumination',
    'ShowFlag.LumenGlobalIllumination', 'ShowFlag.DistanceFieldAO')

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(map_path):
    raise RuntimeError('Cannot load the exact private siege map')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
directionals = [c for a in actors for c in a.get_components_by_class(unreal.DirectionalLightComponent)]
lighting = []
for actor in actors:
    components = []
    for component in actor.get_components_by_class(unreal.ActorComponent):
        if not isinstance(component, (unreal.LightComponent, unreal.SkyLightComponent,
                                      unreal.SkyAtmosphereComponent, unreal.ExponentialHeightFogComponent,
                                      unreal.PostProcessComponent)):
            continue
        row = component_state(component)
        if isinstance(component, unreal.LightComponent):
            row['light'] = read(component, LIGHT_KEYS)
            row['lightColorLinearBeforeTemperature'] = serial(call(component, 'get_light_color'))
        if isinstance(component, unreal.DirectionalLightComponent):
            row['directional'] = read(component, DIRECTIONAL_KEYS)
            forward = call(component, 'get_forward_vector')
            if forward is not None:
                row['directionTowardSun'] = [float(-getattr(forward, axis)) for axis in ('x', 'y', 'z')]
        if isinstance(component, unreal.PointLightComponent):
            row['point'] = read(component, ('intensity_units', 'attenuation_radius', 'source_radius',
                'soft_source_radius', 'source_length', 'use_inverse_squared_falloff'))
        if isinstance(component, unreal.SkyLightComponent):
            row['sky'] = read(component, ('intensity', 'light_color', 'source_type', 'cubemap',
                'real_time_capture', 'lower_hemisphere_is_black', 'lower_hemisphere_color',
                'cast_shadows', 'cast_static_shadows', 'cast_dynamic_shadows',
                'indirect_lighting_intensity', 'occlusion_max_distance', 'contrast',
                'occlusion_exponent', 'min_occlusion', 'occlusion_tint'))
        if isinstance(component, unreal.ExponentialHeightFogComponent):
            row['fog'] = read(component, ('fog_density', 'fog_height_falloff',
                'fog_inscattering_luminance', 'fog_max_opacity', 'start_distance',
                'enable_volumetric_fog', 'volumetric_fog_scattering_distribution',
                'directional_inscattering_exponent', 'directional_inscattering_start_distance',
                'directional_inscattering_luminance'))
        if isinstance(component, unreal.SkyAtmosphereComponent):
            row['atmosphere'] = read(component, ATMOSPHERE_KEYS)
            tent = component.get_editor_property('other_tent_distribution')
            row['atmosphere']['other_tent_distribution'] = read(tent, ('tip_altitude', 'tip_value', 'width'))
            row['directionOverrides'] = [dict(index=index,
                overridden=call(component, 'is_atmosphere_light_direction_overriden', index),
                direction=serial(call(component, 'get_overriden_atmosphere_light_direction', index)))
                for index in range(2)]
            row['groundTransmittance'] = [dict(directional=light.get_path_name(),
                rgba=serial(call(component, 'get_atmosphere_transmitance_on_ground_at_planet_top', light)))
                for light in directionals]
        if isinstance(component, unreal.PostProcessComponent):
            row['postProcess'] = read(component, ('unbound', 'enabled', 'priority', 'blend_weight', 'blend_radius'))
            row['settings'] = read(component.get_editor_property('settings'),
                (*PP_KEYS, *('override_' + key for key in PP_KEYS)))
        components.append(row)
    if components or isinstance(actor, unreal.PostProcessVolume):
        row = dict(path=actor.get_path_name(), klass=actor.get_class().get_name(), label=actor.get_actor_label(),
                   tags=[str(t) for t in actor.tags], rotation=serial(actor.get_actor_rotation()),
                   location=serial(actor.get_actor_location()), hidden=read(actor, ('hidden',)), components=components)
        if isinstance(actor, unreal.PostProcessVolume):
            row['postProcess'] = read(actor, ('unbound', 'enabled', 'priority', 'blend_weight', 'blend_radius'))
            row['settings'] = read(actor.get_editor_property('settings'),
                (*PP_KEYS, *('override_' + key for key in PP_KEYS)))
        lighting.append(row)

console = {name: dict(available=bool(value), value=value) for name in CVARS
           for value in [unreal.SystemLibrary.get_console_variable_string_value(name)]}
default_atmosphere = unreal.get_default_object(unreal.SkyAtmosphereComponent)
atmosphere_defaults = read(default_atmosphere, ATMOSPHERE_KEYS)
atmosphere_defaults['other_tent_distribution'] = read(
    default_atmosphere.get_editor_property('other_tent_distribution'), ('tip_altitude', 'tip_value', 'width'))

# Inspect the actual function defaults and call-site pins without compiling a graph.
lib = unreal.MaterialEditingLibrary
function_path = '/Engine/Functions/Engine_MaterialFunctions03/Procedurals/NormalFromHeightmap'
function = unreal.load_asset(function_path)
if not function:
    raise RuntimeError('Native NormalFromHeightmap is unavailable')
EXPRESSION_KEYS = {
    'MaterialExpressionConstant': ('r',), 'MaterialExpressionConstant2Vector': ('r', 'g'),
    'MaterialExpressionConstant3Vector': ('constant',), 'MaterialExpressionConstant4Vector': ('constant',),
    'MaterialExpressionScalarParameter': ('parameter_name', 'default_value'),
    'MaterialExpressionFunctionInput': ('input_name', 'input_type', 'preview_value',
        'use_preview_value_as_default', 'sort_priority'),
    'MaterialExpressionFunctionOutput': ('output_name', 'sort_priority'),
    'MaterialExpressionTextureObject': ('texture', 'sampler_type'),
    'MaterialExpressionTextureSample': ('texture', 'sampler_type', 'const_coordinate', 'mip_value_mode'),
    'MaterialExpressionMaterialFunctionCall': ('material_function', 'function_inputs', 'function_outputs'),
    'MaterialExpressionMultiply': ('const_a', 'const_b'), 'MaterialExpressionAdd': ('const_a', 'const_b'),
    'MaterialExpressionDivide': ('const_a', 'const_b'), 'MaterialExpressionSubtract': ('const_a', 'const_b'),
    'MaterialExpressionCustom': ('code', 'output_type', 'description')}


def expressions(owner, is_function):
    result = []
    getter = 'get_material_function_expressions' if is_function else 'get_material_expressions'
    upstream = 'get_inputs_for_material_function_expression' if is_function else 'get_inputs_for_material_expression'
    for node in call(lib, getter, owner) or []:
        klass = node.get_class().get_name()
        result.append(dict(path=node.get_path_name(), klass=klass,
            inputs=serial(call(lib, 'get_material_expression_input_names', node)),
            upstream=serial(call(lib, upstream, owner, node)),
            values=read(node, EXPRESSION_KEYS.get(klass, ()))))
    return result


material_rows = []
for role, spec in source['materialSpecs'].items():
    if 'height' not in spec:
        continue
    material = unreal.load_asset('/Game/WorldRebuild/AegisCitadel_' + revision + '/Materials/M_' + role)
    if not isinstance(material, unreal.Material):
        raise RuntimeError('Missing source-bound height material')
    material_rows.append(dict(role=role, path=material.get_path_name(), source=spec,
        normalInput=serial(call(lib, 'get_material_property_input_node', material, unreal.MaterialProperty.MP_NORMAL)),
        expressions=expressions(material, False)))

# Read the actual saved component overrides and shader inputs in a copied study.
# This diagnoses material application; it does not infer game renderer state.
study_bindings, study_materials = [], []
if study:
    studied_material_paths = set()
    for actor in actors:
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            bindings = [serial(component.get_material(i)) for i in range(component.get_num_materials())]
            owned = [p for p in bindings if p and p.startswith('/Game/WorldRebuild/AegisCitadel_' + study_id + '/')]
            if not owned:
                continue
            study_bindings.append(dict(actor=actor.get_path_name(), label=actor.get_actor_label(),
                component=component.get_path_name(), mesh=serial(component.static_mesh),
                materials=bindings, location=serial(actor.get_actor_location())))
            studied_material_paths.update(owned)
    for path in sorted(studied_material_paths):
        material = unreal.load_asset(path)
        if isinstance(material, unreal.Material):
            study_materials.append(dict(path=path,
                baseColorInput=serial(call(lib, 'get_material_property_input_node', material, unreal.MaterialProperty.MP_BASE_COLOR)),
                normalInput=serial(call(lib, 'get_material_property_input_node', material, unreal.MaterialProperty.MP_NORMAL)),
                expressions=expressions(material, False)))
    for requested in study.get('mountainActorReadbacks', []):
        matches = [row for row in study_bindings if row['actor'] == requested['actor']]
        if len(matches) != 1 or matches[0]['materials'] != [requested['studyMaterial']]:
            raise RuntimeError('Saved study mountain material is not bound to the measured actor')

# These rays identify visible retained terrain inside the hall, without ignoring any actor.
hall_rays = []
for x in (32400, 33000, 33600):
    for y in (-1000, 0, 1000):
        start, end = unreal.Vector(x, y, 8500), unreal.Vector(x, y, 5500)
        hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.ECC_VISIBILITY,
            True, [], unreal.DrawDebugTrace.NONE, True)
        values = hit.to_tuple() if hit else None
        hall_rays.append(dict(start=serial(start), end=serial(end), traceComplex=True,
                             hit=serial(values) if values else None))

after = {p: sha(inspected_package(p)) for p in expected}
unchanged = before == after
report = dict(schemaVersion=1, readOnly=True, diagnosticOnly=True, revision=revision,
    map=map_path, signature=candidate['signature'], geometrySignature=candidate['geometrySignature'],
    studyId=study_id or None, studySignature=study['signature'] if study else None,
    cityRevision=study['cityRevision'] if study else candidate['city']['revision'], candidateSha256=sha(candidate_file), assetsSourceSha256=sha(source_file),
    helperSha256=sha(Path(__file__)), engineVersion=unreal.SystemLibrary.get_engine_version(),
    observationScope='editor_loaded_exact_saved_candidate_no_preview_or_game_tick',
    effectiveGameViewShowFlagsObserved=False, showFlagCVarPolicy='override_only_2_means_per_view_default',
    lighting=lighting, atmosphereClassDefaults=atmosphere_defaults, consoleVariables=console,
    heightNormalFunction=dict(path=function_path, expressions=expressions(function, True)),
    heightMaterials=material_rows, studyMaterialBindings=study_bindings,
    studyMaterials=study_materials, hallTerrainOwnerRays=hall_rays,
    transientEnvironmentActors=[r['path'] for r in lighting if 'WarLocalZoneEnvironment' in r['tags']],
    sourceAndCandidateHashesBefore=before, sourceAndCandidateHashesAfter=after,
    sourceAndCandidateHashesUnchanged=unchanged, unavailable=unavailable,
    visualApproved=False, lightingApproved=False, releaseAcceptance=False)
output = RUN / ('lighting-inspection-' + study_id + '.json' if study else 'lighting-inspection.json')
output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
if not unchanged:
    raise RuntimeError('A source/candidate package changed during read-only lighting inspection; retain report')
unreal.log('WAR_CITADEL_LIGHTING_INSPECTED=' + str(output))
