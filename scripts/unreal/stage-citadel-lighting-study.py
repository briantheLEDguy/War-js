"""Stage copied historical geometry for actual game-camera lighting diagnostics.

This private study grants no geometry, traversal, gameplay or publication approval.
Only fresh owned packages may be saved; all source and candidate bytes are checked.
"""
import json
import copy
import os
import re
import sys
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT, digest, sha
from aegis_citadel_lighting import FIXTURES, reference_fixture_requests, CLOUD_PROPERTIES, CLOUD_IDENTITY, REVIEWED_CLOUD_MATERIAL
from citadel_stage_contract import native_lighting_value, lighting_readback, checked_lighting_exposure
from shared_city_sources import package_file,protected_source_file
from shared_city_authoring import prepare_city
from world_actor_state import snapshot
from aegis_citadel_mountain_material import (alpine_material,MOUNTAIN_MATERIAL_SPEC,
    MOUNTAIN_MATERIAL_SOURCE,MOUNTAIN_SHADER,mountain_render_normal_convention)

revision = os.environ.get('WAR_CITADEL_INSPECT_REVISION', '')
if not re.fullmatch('[a-f0-9]{12}', revision):
    raise RuntimeError('An explicit historical native revision is required')
source_dir = OUT / revision
candidate = json.loads((source_dir / 'candidate.json').read_text())
blueprint = json.loads((source_dir / 'blueprint.json').read_text())
expected = {**candidate['sourceHashes'], **candidate['packageHashes']}
def source_file(p,h):
    return protected_source_file(ROOT,p,h) if p.startswith('/Engine/') else package_file(ROOT,p)
before = {p: sha(source_file(p,h)) for p,h in expected.items()}
if before != expected:
    raise RuntimeError('Preserve independently changed native packages')
exposure_extended = checked_lighting_exposure(blueprint['lightingTreatment'],
    unreal.SystemLibrary.get_console_variable_bool_value('r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange'))
requests = [dict(id=row['id'],properties=copy.deepcopy(row['properties']),
    **({'rotationDegrees':copy.deepcopy(row['rotationDegrees'])} if 'rotationDegrees' in row else {}))
    for row in blueprint['lightingTreatment']['fixtures']]
if len(requests)!=7 or {row['id'] for row in requests}!={row[0] for row in FIXTURES}:
    raise RuntimeError('Study requires all seven exact signed fixture identities')
ALPINE_MODES=('alpine_sunset','alpine_storm','alpine_recess','alpine_clear_foreground','alpine_cloud_scale','alpine_portal_reveal')
mode = os.environ.get('WAR_CITADEL_LIGHTING_STUDY_MODE', 'base')
if mode not in ('base', 'cloud_contrast', 'billowing_canopy', 'cumulus_quality', 'grazing_sunset', 'matte_cloth','cinematic_dusk','storm_dusk','balanced_dusk','reference_dusk','slate_dusk',*ALPINE_MODES):
    raise RuntimeError('Unknown isolated lighting study mode')
cloud_scalars, cloud_vectors = {}, {}
cloud_properties = dict(CLOUD_PROPERTIES)
if mode in ('cloud_contrast', 'billowing_canopy', 'cumulus_quality', 'grazing_sunset', 'matte_cloth'):
    next(r for r in requests if r['id'] == 'ambient_sky')['properties']['intensity'] = .35
    next(r for r in requests if r['id'] == 'sun')['rotationDegrees'] = [-20, 30, 0]
    cloud_scalars = dict(Layout_CloudGlobalScale=8, Cloud_GlobalCoverage=.25,
                         Cloud_GlobalDensity=.008, StormClouds=.65)
    cloud_vectors = dict(Storm_LightningColor=[0, 0, 0, 0], Cloud_AlbedoColor=[.65, .70, .78, .5])
if mode == 'billowing_canopy':
    cloud_properties.update(layer_bottom_altitude=.35, layer_height=.65)
    cloud_vectors['Layout_CloudTypeMask'] = [0, 1, 0, 0]
if mode in ('cumulus_quality', 'grazing_sunset', 'matte_cloth'):
    cloud_properties.update(layer_bottom_altitude=.5, layer_height=1.2,
                            view_sample_count_scale=2, shadow_view_sample_count_scale=2)
    cloud_vectors['Layout_CloudTypeMask'] = [0, 0, 1, 0]
if mode == 'grazing_sunset':
    next(r for r in requests if r['id'] == 'sun')['rotationDegrees'] = [-20, -65, 0]
cloth_spec = None
carved_spec = None
practical_requests = []
stone_specs = {}
roof_detail=None
if mode in ('cinematic_dusk','storm_dusk','balanced_dusk','reference_dusk','slate_dusk',*ALPINE_MODES):
    by_id={row['id']:row for row in requests}
    by_id['sun']['rotationDegrees']=[-12,-65,0]
    by_id['sun']['properties'].update(intensity=2500,temperature=4300,light_source_angle=3)
    by_id['soft_sky_fill']['properties'].update(intensity=180)
    by_id['ambient_sky']['properties'].update(intensity=.45)
    by_id['distance_haze']['properties'].update(fog_density=.009,start_distance=2500,
        fog_max_opacity=.6,enable_volumetric_fog=True,
        fog_inscattering_luminance=dict(kind='linear_color',value=[.035,.047,.065,1]))
    by_id['exposure']['properties'].update(auto_exposure_min_brightness=16,
        auto_exposure_max_brightness=256,histogram_log_min=-4,histogram_log_max=12,
        auto_exposure_bias=-.4,bloom_intensity=.35)
    cloud_scalars=dict(Layout_CloudGlobalScale=8,Cloud_GlobalCoverage=.42,
        Cloud_GlobalDensity=.012,StormClouds=.8)
    cloud_vectors=dict(Storm_LightningColor=[0,0,0,0],Cloud_AlbedoColor=[.46,.51,.60,.5],
        Layout_CloudTypeMask=[0,0,1,0])
    carved_spec=dict(baseColor=[.085,.095,.11,1])
    if mode in ('storm_dusk','balanced_dusk','reference_dusk','slate_dusk',*ALPINE_MODES):
        by_id['sun']['rotationDegrees']=[-18,30,0]
        by_id['sun']['properties'].update(intensity=1000,temperature=6800,light_source_angle=4)
        by_id['soft_sky_fill']['properties'].update(intensity=450)
        by_id['ambient_sky']['properties'].update(intensity=1.4)
        by_id['distance_haze']['properties'].update(start_distance=1600,
            directional_inscattering_luminance=dict(kind='linear_color',value=[.03,.045,.07,1]))
        by_id['exposure']['properties'].update(auto_exposure_min_brightness=128,
            auto_exposure_max_brightness=512,auto_exposure_bias=-1.1)
        cloud_scalars.update(Cloud_GlobalCoverage=.58,Cloud_GlobalDensity=.018)
    if mode in ('balanced_dusk','reference_dusk','slate_dusk',*ALPINE_MODES):
        by_id['sun']['properties'].update(intensity=1600,temperature=6500)
        by_id['soft_sky_fill']['properties'].update(intensity=900)
        by_id['ambient_sky']['properties'].update(intensity=3)
        by_id['exposure']['properties'].update(auto_exposure_min_brightness=32,
            auto_exposure_max_brightness=128,auto_exposure_bias=-.5)
        cloud_scalars.update(Cloud_GlobalCoverage=.42,Cloud_GlobalDensity=.012)
        for row in blueprint['architecturalLights']:
            factor = 12 if row['id'].startswith(('gate_fire_pool_','court_fire_pool_')) else 6 if row['id'].startswith('portal_reveal_') else 1
            practical_requests.append(dict(id=row['id'],pointCm=row['pointCm'],
                sourceIntensityCd=row['intensityCd'],intensityCd=row['intensityCd']*factor))
    if mode in ('reference_dusk','slate_dusk',*ALPINE_MODES):
        # Preserve this historical metering treatment for matched comparisons.
        # Lowering the legacy-luminance ceiling is not itself a darkening control.
        by_id['exposure']['properties'].update(auto_exposure_min_brightness=64,
            auto_exposure_max_brightness=256,auto_exposure_bias=-.6)
        carved_spec=dict(baseColor=[.045,.052,.063,1])
    if mode in ('slate_dusk',*ALPINE_MODES):
        # Correct the copied masonry palette independently of exposure. Original
        # texture detail and every gameplay/collision surface remain unchanged.
        stone_specs=dict(stone=[.18,.26,.38,1],limestone=[.27,.35,.48,1],
            flagstone=[.40,.47,.58,1],paving_inlay=[.24,.32,.43,1])
    if mode in ALPINE_MODES:
        stone_specs['slate']=[.7,.8,1,1]
        roof_detail=dict(textureRepeat=6,sourcePeriodCm=1100,studyPeriodCm=1100/6,
            originalColorNormalAndOrmPreserved=True,geometryChanged=False)
        by_id['sun']['rotationDegrees']=[-10,-20,0]
        by_id['sun']['properties'].update(intensity=2400,temperature=4500,light_source_angle=5)
        by_id['soft_sky_fill']['properties'].update(intensity=550)
        by_id['ambient_sky']['properties'].update(intensity=2)
        by_id['exposure']['properties'].update(auto_exposure_min_brightness=64,
            auto_exposure_max_brightness=192,auto_exposure_bias=-.5)
if mode in ('alpine_storm','alpine_recess','alpine_clear_foreground','alpine_cloud_scale','alpine_portal_reveal'):
    by_id['sun']['rotationDegrees']=[-16,30,0]
    by_id['sun']['properties'].update(intensity=1800,temperature=5800,light_source_angle=4)
    by_id['soft_sky_fill']['properties'].update(intensity=500,cast_shadows=False,cast_dynamic_shadows=False)
    by_id['ambient_sky']['properties'].update(intensity=2.5)
    by_id['distance_haze']['properties'].update(fog_density=.015,fog_height_falloff=.025,
        start_distance=2600,fog_max_opacity=.65,
        fog_inscattering_luminance=dict(kind='linear_color',value=[.08,.11,.17,1]))
    cloud_scalars.update(Cloud_GlobalCoverage=.58,Cloud_GlobalDensity=.012,StormClouds=.8)
    by_id['exposure']['properties'].update(auto_exposure_min_brightness=64,
        auto_exposure_max_brightness=256,auto_exposure_bias=-.55)
if mode in ('alpine_recess','alpine_clear_foreground','alpine_cloud_scale','alpine_portal_reveal'):
    # A single-variable comparison against the storm study: retain readable
    # skylight while reducing the shadowless directional wash across recesses.
    by_id['soft_sky_fill']['properties']['intensity']=200
if mode=='alpine_clear_foreground':
    # Volumetric fog has its own start distance in the installed engine. Keep
    # ordinary exponential fog unchanged for this single-variable comparison.
    by_id['distance_haze']['properties']['volumetric_fog_start_distance']=10000
cloud_default_witness = None
if mode == 'alpine_cloud_scale':
    surveys = sorted(source_dir.glob('cloud-material-survey-*.json'))
    if not surveys:
        raise RuntimeError('An actual native cloud-default survey is required')
    survey_file = surveys[-1]
    survey = json.loads(survey_file.read_text())
    parent = [row for row in survey.get('nativeMaterials', []) if row.get('package') == REVIEWED_CLOUD_MATERIAL]
    if (survey.get('revision') != revision or survey.get('packagesUnchanged') is not True
            or len(parent) != 1 or parent[0].get('scalars', {}).get('Layout_CloudGlobalScale') != 256.0
            or survey.get('protectedPackageHashes', {}).get(REVIEWED_CLOUD_MATERIAL)
                != candidate['sourceHashes'].get(REVIEWED_CLOUD_MATERIAL)):
        raise RuntimeError('Native cloud-default witness differs from the protected Engine source')
    cloud_default_witness = dict(file=str(survey_file), sha256=sha(survey_file),
        engineSourceSha256=candidate['sourceHashes'][REVIEWED_CLOUD_MATERIAL],
        originalScale=parent[0]['scalars']['Layout_CloudGlobalScale'],
        comparisonScale=8, requestedScale=256)
    cloud_scalars['Layout_CloudGlobalScale'] = 256
if mode == 'alpine_portal_reveal':
    for request in practical_requests:
        if request['id'] in ('portal_reveal_0', 'portal_reveal_1'):
            request['studyPointCm'] = [25000, *request['pointCm'][1:]]
if mode == 'matte_cloth':
    next(r for r in requests if r['id'] == 'sun')['rotationDegrees'] = [-20, 65, 0]
    cloth_spec = dict(baseColor=[.018, .075, .23, 1], roughness=.92, metallic=0, specular=.25, twoSided=True)
study_signature = digest(dict(sourceRevision=revision, sourceCity=candidate['city']['revision'],
    fixtureRequests=requests, cloud=cloud_properties, glassEmission=[10, 3.1, .4],
    mode=mode, cloudScalars=cloud_scalars, cloudVectors=cloud_vectors,
    practicalShadows=True, practicalRequests=practical_requests,
    cloth=cloth_spec, carvedStone=carved_spec,masonryTints=stone_specs,
    mountainMaterial=MOUNTAIN_MATERIAL_SPEC if mode in ALPINE_MODES else None,
    roofDetail=roof_detail,
    mountainShader=MOUNTAIN_SHADER if mode in ALPINE_MODES else None,helperSha256=sha(Path(__file__)),
    cloudDefaultWitness=cloud_default_witness,
    mountainHelperSha256=sha(Path(__file__).with_name('aegis_citadel_mountain_material.py'))))
destination = '/Game/WorldRebuild/AegisCitadel_' + study_signature[:12]
output = source_dir / ('lighting-study-' + study_signature[:12])
output.mkdir(exist_ok=True)
pending = output / 'stage-pending.json'
if pending.exists() or (output / 'study.json').exists():
    raise RuntimeError('Preserve the existing or interrupted private study')
assets = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
created = []
pending.write_text(json.dumps(dict(destination=destination, created=created), indent=2) + '\n')

def record(package):
    if not package.startswith(destination + '/'):
        raise RuntimeError('A study may create only its own packages')
    created.append(package)
    pending.write_text(json.dumps(dict(destination=destination, created=created), indent=2) + '\n')

def duplicate(source, target):
    if assets.does_asset_exist(target) or not assets.duplicate_asset(source, target):
        raise RuntimeError('Cannot create a fresh owned study package: ' + target)
    record(target)

mountain_material,mountain_readback=None,None
mountain_actor_readbacks=[]
if mode in ALPINE_MODES:
    if MOUNTAIN_MATERIAL_SOURCE not in expected:
        raise RuntimeError('Original granite material is outside the signed source package closure')
    normal_convention=mountain_render_normal_convention(source_dir,candidate)
    mountain_material,mountain_readback=alpine_material(unreal,destination,duplicate,normal_convention)

def load(package):
    if not levels.load_level(package):
        raise RuntimeError('Cannot load the private study layer')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    return world

def own(package):
    return [a for a in actors.get_all_level_actors() if a.get_outer().get_path_name().split('.')[0] == package]

def save(package):
    if not package.startswith(destination + '/') or not levels.set_current_level_by_name(package.rsplit('/', 1)[1]):
        raise RuntimeError('Cannot select an owned study layer')
    if not levels.save_current_level():
        raise RuntimeError('Cannot save an owned study layer')

glass_source = '/Game/WorldRebuild/AegisCitadel_' + revision + '/Materials/M_glass'
glass_target = destination + '/Materials/M_glass'
duplicate(glass_source, glass_target)
glass = unreal.load_asset(glass_target)
emission = unreal.MaterialEditingLibrary.get_material_property_input_node(glass, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
if not isinstance(emission, unreal.MaterialExpressionConstant3Vector):
    raise RuntimeError('Unknown historical glass emission graph')
emission.constant = unreal.LinearColor(r=10, g=3.1, b=.4, a=1)
glass_emission_readback = lighting_readback(emission.constant, dict(kind='linear_color', value=[10,3.1,.4,1]))
glass_compile_errors = unreal.MaterialEditingLibrary.recompile_material(glass)
if glass_compile_errors:
    raise RuntimeError('Owned emissive glass compilation failed: ' + str(glass_compile_errors))
if not assets.save_loaded_asset(glass, only_if_is_dirty=False):
    raise RuntimeError('Cannot save owned study glass')
cloth_source = '/Game/WorldRebuild/AegisCitadel_' + revision + '/Materials/M_blue'
cloth = None
cloth_readbacks = {}
if cloth_spec:
    cloth_path = destination + '/Materials/M_blue'
    if assets.does_asset_exist(cloth_path):
        raise RuntimeError('Preserve existing owned study cloth')
    lib = unreal.MaterialEditingLibrary
    cloth = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_blue', destination + '/Materials',
        unreal.Material, unreal.MaterialFactoryNew())
    if not cloth:
        raise RuntimeError('Cannot create owned study cloth')
    record(cloth_path)
    for name, prop in [('baseColor', unreal.MaterialProperty.MP_BASE_COLOR),
                       ('roughness', unreal.MaterialProperty.MP_ROUGHNESS),
                       ('metallic', unreal.MaterialProperty.MP_METALLIC),
                       ('specular', unreal.MaterialProperty.MP_SPECULAR)]:
        wanted = cloth_spec[name]
        node = lib.create_material_expression(cloth, unreal.MaterialExpressionConstant3Vector
            if name == 'baseColor' else unreal.MaterialExpressionConstant)
        if name == 'baseColor':
            node.constant = unreal.LinearColor(r=wanted[0], g=wanted[1], b=wanted[2], a=wanted[3])
        else:
            node.r = wanted
        if not lib.connect_material_property(node, '', prop) or lib.get_material_property_input_node(cloth, prop) != node:
            raise RuntimeError('Incorrect owned cloth material input: ' + name)
        cloth_readbacks[name] = lighting_readback(node.constant, dict(kind='linear_color', value=wanted)) \
            if name == 'baseColor' else lighting_readback(node.r, wanted)
    cloth.set_editor_property('two_sided', True)
    cloth_readbacks['twoSided'] = lighting_readback(cloth.get_editor_property('two_sided'), True)
    lib.recompile_material(cloth)
    if not assets.save_loaded_asset(cloth, only_if_is_dirty=False):
        raise RuntimeError('Cannot save owned study cloth')
carved_source='/Game/WorldRebuild/AegisCitadel_'+revision+'/Materials/M_carved_stone'
carved=None
carved_readbacks={}
if carved_spec:
    carved_target=destination+'/Materials/M_carved_stone'
    duplicate(carved_source,carved_target)
    carved=unreal.load_asset(carved_target)
    node=unreal.MaterialEditingLibrary.get_material_property_input_node(carved,unreal.MaterialProperty.MP_BASE_COLOR)
    if not isinstance(node,unreal.MaterialExpressionConstant3Vector):
        raise RuntimeError('Expected exact untextured carved-stone base color graph')
    wanted=carved_spec['baseColor'];node.constant=unreal.LinearColor(r=wanted[0],g=wanted[1],b=wanted[2],a=1)
    carved_readbacks['baseColor']=lighting_readback(node.constant,dict(kind='linear_color',value=wanted))
    unreal.MaterialEditingLibrary.recompile_material(carved)
    if not assets.save_loaded_asset(carved,only_if_is_dirty=False):
        raise RuntimeError('Cannot save owned study carved stone')
masonry_materials,masonry_readbacks={},{}
source_materials=json.loads((source_dir/'assets-source.json').read_text())['materialSpecs']
for role,wanted in stone_specs.items():
    original='/Game/WorldRebuild/AegisCitadel_'+revision+'/Materials/M_'+role
    target=destination+'/Materials/M_'+role
    duplicate(original,target)
    material=unreal.load_asset(target)
    lib=unreal.MaterialEditingLibrary
    base=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)
    if not isinstance(base,unreal.MaterialExpressionMultiply):
        raise RuntimeError('Unknown original masonry base-color graph: '+role)
    inputs=list(lib.get_inputs_for_material_expression(material,base))
    tints=[node for node in inputs if isinstance(node,unreal.MaterialExpressionConstant3Vector)]
    textures=[node for node in inputs if isinstance(node,unreal.MaterialExpressionTextureSample)]
    if len(tints)!=1 or len(textures)!=1:
        raise RuntimeError('Masonry treatment requires the exact texture-times-tint graph: '+role)
    source_tint=source_materials[role]['tint']+[1]
    lighting_readback(tints[0].constant,dict(kind='linear_color',value=source_tint))
    tints[0].constant=unreal.LinearColor(r=wanted[0],g=wanted[1],b=wanted[2],a=1)
    masonry_readbacks[role]=dict(sourceMaterial=original,
        originalTexture=textures[0].texture.get_path_name(),
        tint=lighting_readback(tints[0].constant,dict(kind='linear_color',value=wanted)))
    if role=='slate' and roof_detail:
        samples=[node for node in lib.get_material_expressions(material) if isinstance(node,unreal.MaterialExpressionTextureSample)]
        expected_textures={'/Game/WorldRebuild/AegisCitadel_'+revision+'/Textures/T_'+Path(source_materials[role][channel]).stem+'_'+channel
            for channel in ('baseColor','normal','orm')}
        if len(samples)!=3 or {node.texture.get_path_name().split('.')[0] for node in samples}!=expected_textures:
            raise RuntimeError('Roof study requires all three exact original PBR texture inputs')
        if any(input_node is not None for node in samples
               for input_node in lib.get_inputs_for_material_expression(material,node)):
            raise RuntimeError('Preserve independently changed roof texture coordinates')
        coordinates=lib.create_material_expression(material,unreal.MaterialExpressionTextureCoordinate)
        coordinates.set_editor_property('u_tiling',roof_detail['textureRepeat'])
        coordinates.set_editor_property('v_tiling',roof_detail['textureRepeat'])
        for node in samples:
            if not lib.connect_material_expressions(coordinates,'',node,'UVs'):
                raise RuntimeError('Cannot bind the matching roof PBR texture scale')
        masonry_readbacks[role]['roofDetail']=dict(roof_detail,
            uTiling=lighting_readback(coordinates.get_editor_property('u_tiling'),roof_detail['textureRepeat']),
            vTiling=lighting_readback(coordinates.get_editor_property('v_tiling'),roof_detail['textureRepeat']))
    errors=lib.recompile_material(material)
    if errors:raise RuntimeError('Owned masonry shader compilation failed: '+str(errors))
    if not assets.save_loaded_asset(material,only_if_is_dirty=False):
        raise RuntimeError('Cannot save owned masonry material: '+role)
    masonry_materials[original]=material
cloud_material = unreal.load_asset(REVIEWED_CLOUD_MATERIAL)
cloud_parameter_readbacks = {}
if cloud_scalars or cloud_vectors:
    material_path = destination + '/Materials/MI_Cloud'
    if assets.does_asset_exist(material_path):
        raise RuntimeError('Preserve existing owned cloud material')
    cloud_material = unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_Cloud',
        destination + '/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    if not cloud_material:
        raise RuntimeError('Cannot create owned cloud instance')
    record(material_path)
    unreal.MaterialEditingLibrary.set_material_instance_parent(cloud_material, unreal.load_asset(REVIEWED_CLOUD_MATERIAL))
    scalar_names = {str(n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(cloud_material)}
    vector_names = {str(n) for n in unreal.MaterialEditingLibrary.get_vector_parameter_names(cloud_material)}
    for key, wanted in cloud_scalars.items():
        if key not in scalar_names:
            raise RuntimeError('Unknown Engine cloud scalar parameter: ' + key)
        # UE5.8's setter leaves its return boolean false even after a successful
        # edit. The registered parameter and actual readback establish success.
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(cloud_material, key, wanted)
        actual = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(cloud_material, key)
        cloud_parameter_readbacks[key] = lighting_readback(actual, wanted)
    for key, wanted in cloud_vectors.items():
        if key not in vector_names:
            raise RuntimeError('Unknown Engine cloud vector parameter: ' + key)
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(cloud_material, key,
            unreal.LinearColor(r=wanted[0], g=wanted[1], b=wanted[2], a=wanted[3]))
        actual = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(cloud_material, key)
        cloud_parameter_readbacks[key] = lighting_readback(actual, dict(kind='linear_color', value=wanted))
    if not assets.save_loaded_asset(cloud_material, only_if_is_dirty=False):
        raise RuntimeError('Cannot save owned cloud instance')

scenery = []
fixture_readbacks = []
practical_readbacks = []
brazier_readbacks = []

def visible_state(actor, component):
    values = dict(actorHidden=actor.get_editor_property('hidden'),
        componentVisible=component.get_editor_property('visible'),
        componentHiddenInGame=component.get_editor_property('hidden_in_game'))
    if any(type(value) is not bool for value in values.values()):
        raise RuntimeError('Native fixture visibility must use exact reflected booleans')
    return values

def portal_shadow_segment(world, actor, origin):
    end = [24000, origin[1], origin[2]]
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(*origin),
        unreal.Vector(*end), unreal.TraceTypeQuery.ECC_VISIBILITY, True, [actor],
        unreal.DrawDebugTrace.NONE, True)
    values = hit.to_tuple() if hit else None
    row = dict(startCm=origin, endCm=end, blocked=bool(values and values[0]),
        traceComplex=True, editorQueryOnly=True, runtimeShadowVerified=False)
    if row['blocked']:
        point = values[5]
        row.update(hitPointCm=[point.x, point.y, point.z],
            actor=values[9].get_path_name() if values[9] else None,
            component=values[10].get_path_name() if values[10] else None)
    return row
for index, source in enumerate(candidate['city']['sceneryLevels']):
    if source.endswith('/Layers/population'):
        scenery.append(source)
        continue
    target = destination + '/Layers/Study_' + str(index)
    duplicate(source, target)
    load(source)
    source_states = {a.get_name(): snapshot(a) for a in own(source)}
    world = load(target)
    if {a.get_name(): snapshot(a) for a in own(target)} != source_states:
        raise RuntimeError('Native duplicate changed retained actor state')
    rows = own(target)
    for request in requests:
        identity = next(row for row in FIXTURES if row[0] == request['id'])
        _, name, klass, label, component_name, _, tag = identity
        matches = [a for a in rows if a.get_name() == name and a.get_class().get_name() == klass
            and a.get_actor_label() == label and tag in [str(t) for t in a.tags]]
        if not matches:
            continue
        if len(matches) != 1:
            raise RuntimeError('Ambiguous private fixture: ' + request['id'])
        actor = matches[0]
        value = actor.get_component_by_class(getattr(unreal, component_name)) if component_name else actor.get_editor_property('settings')
        if component_name:
            value.set_mobility(unreal.ComponentMobility.MOVABLE)
        actual = {}
        for key, wanted in request['properties'].items():
            value.set_editor_property(key, native_lighting_value(wanted))
            actual[key] = lighting_readback(value.get_editor_property(key), wanted)
        if not component_name:
            actor.set_editor_property('settings', value)
        if 'rotationDegrees' in request:
            pitch, yaw, roll = request['rotationDegrees']
            actor.set_actor_rotation(unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll), False)
        fixture_readbacks.append(dict(id=request['id'], package=target, actor=actor.get_path_name(), properties=actual))
    if source.endswith('/Layers/GothicCitadel'):
        for request in practical_requests:
            matches=[actor for actor in rows if isinstance(actor,unreal.PointLight)
                and actor.get_actor_label()=='Bastion '+request['id']
                and 'WarCitadelLight_'+request['id'] in [str(tag) for tag in actor.tags]]
            if len(matches)!=1:raise RuntimeError('Unknown or ambiguous owned practical: '+request['id'])
            actor=matches[0];point=actor.get_actor_location();wanted=request['pointCm']
            if any(abs(v-w)>.01 for v,w in zip((point.x,point.y,point.z),wanted)):
                raise RuntimeError('Private practical moved from its signed position')
            component=actor.point_light_component
            practical_visibility = visible_state(actor,component)
            if practical_visibility != dict(actorHidden=False,componentVisible=True,componentHiddenInGame=False):
                raise RuntimeError('The exact owned practical light is hidden or disabled')
            lighting_readback(component.get_editor_property('intensity'),request['sourceIntensityCd'])
            if component.get_editor_property('intensity_units')!=unreal.LightUnits.CANDELAS:
                raise RuntimeError('Private practical units differ from the native source')
            original_shadow = portal_shadow_segment(world, actor, wanted) if request['id'].startswith('portal_reveal_') else None
            study_point = request.get('studyPointCm', wanted)
            if study_point != wanted:
                if request['id'] not in ('portal_reveal_0', 'portal_reveal_1') or study_point != [25000, *wanted[1:]]:
                    raise RuntimeError('Only the two exact owned portal origins may move in this private study')
                actor.set_actor_location(unreal.Vector(*study_point), False, False)
                actual_point = actor.get_actor_location()
                if any(abs(v-w)>.01 for v,w in zip((actual_point.x,actual_point.y,actual_point.z),study_point)):
                    raise RuntimeError('Private portal origin readback differs from its exact requested position')
            component.set_editor_property('intensity',request['intensityCd'])
            component.set_cast_shadows(True)
            source_light = next(row for row in blueprint['architecturalLights'] if row['id']==request['id'])
            practical_readbacks.append(dict(id=request['id'],actor=actor.get_path_name(),pointCm=study_point,
                originalPointCm=wanted, visibility=practical_visibility,
                sourcePortalSegment=original_shadow,
                studyPortalSegment=portal_shadow_segment(world,actor,study_point) if original_shadow else None,
                castShadows=lighting_readback(component.get_editor_property('cast_shadows'),True),
                attenuationRadiusCm=lighting_readback(component.get_editor_property('attenuation_radius'),source_light['attenuationRadiusCm']),
                temperatureK=lighting_readback(component.get_editor_property('temperature'),source_light['temperatureK']),
                intensityCd=lighting_readback(component.get_editor_property('intensity'),request['intensityCd'])))
        for actor in rows:
            if isinstance(actor, unreal.PointLight):
                actor.point_light_component.set_cast_shadows(True)
            for component in actor.get_components_by_class(unreal.StaticMeshComponent):
                for slot in range(component.get_num_materials()):
                    material = component.get_material(slot)
                    if material and material.get_path_name().split('.')[0] == glass_source:
                        component.set_material(slot, glass)
                    if cloth and material and material.get_path_name().split('.')[0] == cloth_source:
                        component.set_material(slot, cloth)
                    if carved and material and material.get_path_name().split('.')[0] == carved_source:
                        component.set_material(slot,carved)
                    if material and material.get_path_name().split('.')[0] in masonry_materials:
                        component.set_material(slot,masonry_materials[material.get_path_name().split('.')[0]])
                if re.fullmatch('Bastion reference furnishing_brazier_[0-9]+', actor.get_actor_label()):
                    slots = [slot for slot in range(component.get_num_materials()) if component.get_material(slot) == glass]
                    if len(slots) != 1:
                        raise RuntimeError('Each owned brazier requires one actual copied emissive glass slot')
                    brazier_readbacks.append(dict(actor=actor.get_path_name(),label=actor.get_actor_label(),
                        component=component.get_path_name(),mesh=component.static_mesh.get_path_name(),
                        emissiveSlot=slots[0],emissiveMaterial=component.get_material(slots[0]).get_path_name(),
                        visibility=visible_state(actor,component),runtimeVisibilityVerified=False))
        clouds=[a for a in rows if isinstance(a,unreal.VolumetricCloud)
            and a.get_actor_label()==CLOUD_IDENTITY['label']
            and CLOUD_IDENTITY['requiredTag'] in [str(t) for t in a.tags]]
        if len(clouds)!=1:raise RuntimeError('Study requires exactly one existing owned cloud fixture')
        cloud=clouds[0]
        component = cloud.get_component_by_class(unreal.VolumetricCloudComponent)
        component.set_material(cloud_material)
        for key, wanted in cloud_properties.items():
            component.set_editor_property(key, wanted)
            lighting_readback(component.get_editor_property(key), wanted)
    if mountain_material:
        matches=[a for a in rows if a.get_name()=='StaticMeshActor_306'
            and a.get_actor_label()=='Crownward authored mountain massif'
            and 'WarZoneObject_aegis_capital_StaticMeshActor_306' in [str(t) for t in a.tags]]
        for actor in matches:
            component=actor.static_mesh_component
            measured=next(r for r in candidate['terrainCarves'] if r['id']=='occupied_commander_hall')
            if component.get_name()!=measured['component'] or component.static_mesh.get_path_name()!=measured['mesh']:
                raise RuntimeError('Alpine study requires the exact measured carved mountain component')
            measured_component=next(c for c in measured['actualActorState']['components'] if c['name']==measured['component'])
            actual_materials=[component.get_material(i).get_path_name() for i in range(component.get_num_materials())]
            if len(actual_materials)!=1 or actual_materials!=measured_component['materials']:
                raise RuntimeError('Preserve an independently changed mountain material binding')
            if any(material.split('.')[0] not in expected for material in actual_materials):
                raise RuntimeError('Measured mountain override is outside the signed protected source closure')
            before_actor=snapshot(actor)
            if before_actor!=measured['actualActorState']:
                raise RuntimeError('Mountain actor differs from its exact measured native state')
            component.set_material(0,mountain_material);after_actor=snapshot(actor)
            expected_actor=copy.deepcopy(before_actor)
            next(c for c in expected_actor['components'] if c['name']==measured['component'])['materials']=[mountain_material.get_path_name()]
            if after_actor!=expected_actor:
                raise RuntimeError('Mountain study changed geometry, transform, collision or another actor property')
            mountain_actor_readbacks.append(dict(actor=actor.get_path_name(),mesh=component.static_mesh.get_path_name(),
                sourceMaterialBindings=actual_materials,sourcePbrGraph=MOUNTAIN_MATERIAL_SOURCE,
                studyMaterial=component.get_material(0).get_path_name(),
                before=before_actor,after=after_actor))
    save(target)
    scenery.append(target)
if len(fixture_readbacks) != 7 or {r['id'] for r in fixture_readbacks} != {r[0] for r in FIXTURES}:
    raise RuntimeError('All seven exact native fixtures must be treated once')
if {row['id'] for row in practical_readbacks}!={row['id'] for row in practical_requests}:
    raise RuntimeError('Private practical treatment was incomplete')
if (len(brazier_readbacks)!=12 or len({row['label'] for row in brazier_readbacks})!=12
        or any(row['visibility']!=dict(actorHidden=False,componentVisible=True,componentHiddenInGame=False)
            for row in brazier_readbacks)):
    raise RuntimeError('All twelve owned brazier bindings require actual visible native components')
if mountain_material and len(mountain_actor_readbacks)!=1:
    raise RuntimeError('Alpine study must bind exactly one original mountain actor')

def read_only_backup(file):
    # prepare_city calls this for scenery; it may not mutate the source packages.
    if file.exists() and file.suffix not in ('.umap', '.uasset'):
        raise RuntimeError('Unexpected city package')

zone = dict(id='aegis_capital', origin=candidate['city']['origin'], levels={str(i): p for i, p in enumerate(scenery)})
city = prepare_city(zone, destination + '/City', read_only_backup, record, output,expected)
if city['gameplayLevels'] or city['movedGameplay']:
    raise RuntimeError('Diagnostic lighting scenery contains unexpected gameplay')
map_path = destination + '/LightingStudy'
duplicate(candidate['siegeMap'], map_path)
world = load(map_path)
for level in list(unreal.EditorLevelUtils.get_levels(world)):
    if level.get_outer().get_path_name().split('.')[0] != map_path:
        if not unreal.EditorLevelUtils.remove_level_from_world(level):
            raise RuntimeError('Cannot detach copied historical scenery')
for package in scenery:
    if not unreal.EditorLevelUtils.add_level_to_world(world, package, unreal.LevelStreamingAlwaysLoaded):
        raise RuntimeError('Cannot attach study scenery')
field = next(a for a in own(map_path) if isinstance(a, unreal.WarSiegeBattlefield))
field.set_editor_property('city_definition', unreal.load_asset(city['definition']))
field.set_editor_property('reviewed_city_revision', '')
save(map_path)
loaded_lights=[]
loaded_fogs=[]
for actor in actors.get_all_level_actors():
    for component in actor.get_components_by_class(unreal.DirectionalLightComponent):
        rotation=actor.get_actor_rotation()
        loaded_lights.append(dict(actor=actor.get_path_name(),component=component.get_path_name(),
            rotationDegrees=[rotation.pitch,rotation.yaw,rotation.roll],intensity=component.get_editor_property('intensity'),
            temperature=component.get_editor_property('temperature'),
            useTemperature=component.get_editor_property('use_temperature')))
    for component in actor.get_components_by_class(unreal.ExponentialHeightFogComponent):
        loaded_fogs.append(dict(actor=actor.get_path_name(),component=component.get_path_name(),
            actorZCm=actor.get_actor_location().z,
            properties={key:component.get_editor_property(key) for key in
                ('fog_density','fog_height_falloff','start_distance','fog_max_opacity',
                 'enable_volumetric_fog','volumetric_fog_start_distance',
                 'volumetric_fog_near_fade_in_distance','volumetric_fog_distance',
                 'volumetric_fog_extinction_scale','volumetric_fog_scattering_distribution')}))
after = {p: sha(source_file(p,h)) for p,h in expected.items()}
if before != after:
    raise RuntimeError('Private study changed retained or historical native bytes')
report = dict(schemaVersion=1, diagnosticOnly=True, signature=study_signature,
    helperSha256=sha(Path(__file__)), cloudDefaultWitness=cloud_default_witness,
    exposureUsesExtendedEV100=exposure_extended,exposureUnits=blueprint['lightingTreatment']['exposureUnits'],
    glassCompileErrors=list(glass_compile_errors),
    mode=mode, cloudParameterReadbacks=cloud_parameter_readbacks, cloudProperties=cloud_properties,
    clothSpec=cloth_spec, clothReadbacks=cloth_readbacks,carvedStoneSpec=carved_spec,carvedStoneReadbacks=carved_readbacks,
    masonryTints=stone_specs,masonryReadbacks=masonry_readbacks,
    mountainMaterialReadback=mountain_readback,mountainActorReadbacks=mountain_actor_readbacks,
    roofDetail=roof_detail,
    historicalGeometryRevision=revision, blueprintPath=str(source_dir / 'blueprint.json'),
    blueprintSha256=sha(source_dir / 'blueprint.json'), map=map_path,
    mapSha256=sha(package_file(ROOT, map_path)), cityRevision=city['revision'],
    fixtures=fixture_readbacks,loadedDirectionalLights=loaded_lights,loadedFogState=loaded_fogs,
    practicalReadbacks=practical_readbacks,
    brazierReadbacks=brazier_readbacks,glassEmissionReadback=glass_emission_readback,
    createdPackageHashes={p: sha(package_file(ROOT, p)) for p in created},
    sourceAndCandidateHashesUnchanged=True, visualApproved=False, lightingApproved=False,
    physicalTraversalApproved=False, gameplayApproved=False, releaseAcceptance=False)
(output / 'study.json').write_text(json.dumps(report, indent=2) + '\n')
pending.unlink()
unreal.log('WAR_CITADEL_PRIVATE_LIGHTING_STUDY=' + str(output / 'study.json'))
