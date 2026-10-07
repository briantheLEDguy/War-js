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
from citadel_stage_contract import native_lighting_value, lighting_readback, checked_lighting_exposure, checked_render_audit
from shared_city_sources import package_file,protected_source_file
from shared_city_authoring import prepare_city
from world_actor_state import snapshot, transform
from aegis_citadel_mountain_material import (alpine_material,MOUNTAIN_MATERIAL_SPEC,
    MOUNTAIN_MATERIAL_SOURCE,MOUNTAIN_SHADER,mountain_render_normal_convention)
from aegis_citadel_cloud_material import SPEC as AUTHORED_CLOUD_SPEC, SHADER as AUTHORED_CLOUD_SHADER, create_cloud_material
from aegis_citadel_alpine_relief import SPEC as ALPINE_RELIEF_SPEC, refine_native_highland
from aegis_citadel_stone_material import SPEC as SCULPTURE_SPEC, COLOR_SHADER, HEIGHT_SHADER, NORMAL_SHADER, weather_carved_stone
from aegis_citadel_reference_material import REFERENCE_MATERIAL_MODES, reference_material_comparison, reference_cloud_comparison
from citadel_lumen_study import PRIVATE_LUMEN_MODES, private_lumen_comparison
from citadel_performance_evidence import performance_package_file
from citadel_twilight_fire_study import (checked_option as twilight_fire_option,
    comparison as twilight_fire_comparison, checked_readbacks as checked_twilight_fire_readbacks)
from citadel_private_surface_study import (selected_specs, verify_bindings, create_surfaces,
    create_mountain, actor_binding_readback, verify_role_coverage, graph_readback, sculpture_binding_readbacks)
from aegis_citadel_distant_crags import (checked_option, bind_backdrop, stage_backdrop,
    collision_snapshot, read_component_policy, checked_retained_collision)

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
ALPINE_MODES=('alpine_sunset','alpine_storm','alpine_recess','alpine_clear_foreground','alpine_cloud_scale','alpine_portal_reveal','alpine_engine_mask','alpine_native_clouds','alpine_stratocumulus','alpine_volume_probe','alpine_authored_clouds','alpine_relief')
mode = os.environ.get('WAR_CITADEL_LIGHTING_STUDY_MODE', 'base')
if mode not in ('base', 'cloud_contrast', 'billowing_canopy', 'cumulus_quality', 'grazing_sunset', 'matte_cloth','cinematic_dusk','storm_dusk','balanced_dusk','reference_dusk','slate_dusk',*ALPINE_MODES,*REFERENCE_MATERIAL_MODES,*PRIVATE_LUMEN_MODES):
    raise RuntimeError('Unknown isolated lighting study mode')
backdrop_enabled = checked_option(os.environ.get('WAR_CITADEL_DISTANT_CRAGS', ''))
backdrop_spec, backdrop_mesh, backdrop_readback = None, None, None
retained_scenery_collision = {}
if backdrop_enabled:
    backdrop_spec, backdrop_mesh = bind_backdrop(ROOT, blueprint, revision)
    backdrop_spec['helperSha256'] = sha(Path(__file__).with_name('aegis_citadel_distant_crags.py'))
    backdrop_spec['candidateSha256'] = sha(source_dir / 'candidate.json')
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
if mode in ('alpine_storm','alpine_recess','alpine_clear_foreground','alpine_cloud_scale','alpine_portal_reveal','alpine_engine_mask'):
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
if mode in ('alpine_recess','alpine_clear_foreground','alpine_cloud_scale','alpine_portal_reveal','alpine_engine_mask'):
    # A single-variable comparison against the storm study: retain readable
    # skylight while reducing the shadowless directional wash across recesses.
    by_id['soft_sky_fill']['properties']['intensity']=200
if mode=='alpine_clear_foreground':
    # Volumetric fog has its own start distance in the installed engine. Keep
    # ordinary exponential fog unchanged for this single-variable comparison.
    by_id['distance_haze']['properties']['volumetric_fog_start_distance']=10000
cloud_default_witness = None
if mode in ('alpine_cloud_scale','alpine_native_clouds','alpine_stratocumulus'):
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
    if mode in ('alpine_native_clouds','alpine_stratocumulus'):
        # Isolate the actual installed density/layout recipe before tuning its
        # appearance; render-resource validity alone cannot prove visible clouds.
        native=parent[0]
        cloud_scalars={key:native['scalars'][key] for key in
            ('Layout_CloudGlobalScale','Cloud_GlobalCoverage','Cloud_GlobalDensity','StormClouds')}
        cloud_vectors={key:native['vectors'][key] for key in ('Layout_CloudTypeMask','Cloud_AlbedoColor')}
        cloud_vectors['Storm_LightningColor']=[0,0,0,0]
        cloud_default_witness['requestedScalars']=cloud_scalars
        cloud_default_witness['requestedVectors']=cloud_vectors
if mode=='alpine_stratocumulus':
    # Layout_CloudType controls visibility; TypeMask controls the global mask's
    # influence. Bind real stratocumulus, retain installed shape/noise defaults.
    cloud_scalars.update(Cloud_GlobalCoverage=.65,Cloud_GlobalDensity=.012,StormClouds=.25)
    cloud_vectors.update(Layout_CloudType=[1,.15,.1,.3],Layout_CloudTypeMask=[0,0,0,0],
        Cloud_AlbedoColor=[.55,.61,.70,.65],Storm_AlbedoColor=[.18,.23,.31,.5])
    cloud_properties.update(layer_bottom_altitude=.7,layer_height=3)
    cloud_default_witness.update(parameterSemanticsSource=
        'https://dev.epicgames.com/documentation/unreal-engine/volumetric-cloud-material-in-unreal-engine',
        typeVisibilityParameter='Layout_CloudType',maskInfluenceParameter='Layout_CloudTypeMask')
if mode in ('alpine_portal_reveal','alpine_engine_mask','alpine_native_clouds','alpine_stratocumulus'):
    for request in practical_requests:
        if request['id'] in ('portal_reveal_0', 'portal_reveal_1'):
            request['studyPointCm'] = [25000, *request['pointCm'][1:]]
if mode == 'alpine_engine_mask':
    # Historical comparison of global-mask influence, not cloud-type visibility.
    cloud_vectors['Layout_CloudTypeMask']=[0,0,0,1]
if mode == 'matte_cloth':
    next(r for r in requests if r['id'] == 'sun')['rotationDegrees'] = [-20, 65, 0]
    cloth_spec = dict(baseColor=[.018, .075, .23, 1], roughness=.92, metallic=0, specular=.25, twoSided=True)
volume_probe=dict(extinctionPerCm=.0005,albedo=[.72,.78,.9,1],blendMode='additive',diagnosticOnly=True) if mode=='alpine_volume_probe' else None
authored_cloud = dict(spec=AUTHORED_CLOUD_SPEC,shader=AUTHORED_CLOUD_SHADER,
    helperSha256=sha(Path(__file__).with_name('aegis_citadel_cloud_material.py'))) if mode in ('alpine_authored_clouds','alpine_relief') else None
relief_spec=dict(spec=ALPINE_RELIEF_SPEC,
    helperSha256=sha(Path(__file__).with_name('aegis_citadel_alpine_relief.py')),
    existingCollisionRetained=True,renderOnly=True) if mode=='alpine_relief' else None
sculpture_spec=dict(spec=SCULPTURE_SPEC,colorShader=COLOR_SHADER,heightShader=HEIGHT_SHADER,normalShader=NORMAL_SHADER,
    helperSha256=sha(Path(__file__).with_name('aegis_citadel_stone_material.py'))) if mode=='alpine_relief' else None
if authored_cloud:
    by_id['sun']['rotationDegrees']=[-16,30,0]
    by_id['sun']['properties'].update(intensity=1800,temperature=6500,light_source_angle=4)
    by_id['soft_sky_fill']['properties'].update(intensity=200,cast_shadows=False,cast_dynamic_shadows=False)
    by_id['ambient_sky']['properties'].update(intensity=2.5)
    cloud_properties.update(layer_bottom_altitude=AUTHORED_CLOUD_SPEC['layerBottomKm'],
        layer_height=AUTHORED_CLOUD_SPEC['layerHeightKm'])
    if relief_spec:
        by_id['sun']['properties'].update(cast_cloud_shadows=True,cloud_shadow_strength=.65,
            cloud_shadow_on_surface_strength=.65,cloud_shadow_extent=5,cloud_shadow_map_resolution_scale=2)
        by_id['ambient_sky']['properties'].update(cloud_ambient_occlusion=True,
            cloud_ambient_occlusion_strength=.45,cloud_ambient_occlusion_extent=5)
private_lumen_spec = None
if mode in PRIVATE_LUMEN_MODES:
    requests, private_lumen_cloud, private_lumen_spec = private_lumen_comparison(
        mode, requests, blueprint['lightingTreatment']['cloudFixture'])
    cloud_properties, cloud_scalars, cloud_vectors = private_lumen_cloud
    private_lumen_spec['helperSha256'] = sha(Path(__file__).with_name('citadel_lumen_study.py'))
    private_lumen_spec['cloudRecipeHelperSha256'] = sha(Path(__file__).with_name('aegis_citadel_reference_material.py'))
if mode in REFERENCE_MATERIAL_MODES:
    requests,carved_spec,stone_specs=reference_material_comparison(mode,requests)
    cloud_properties,cloud_scalars,cloud_vectors=reference_cloud_comparison(blueprint['lightingTreatment']['cloudFixture'])
private_twilight_spec = None
if twilight_fire_option(os.environ.get('WAR_CITADEL_TWILIGHT_FIRE_STUDY', '')):
    requests, practical_requests, private_twilight_spec = twilight_fire_comparison(
        mode, requests, blueprint['architecturalLights'], blueprint['lightingTreatment']['exposureUnits'],
        exposure_extended, dict(blueprint=sha(source_dir / 'blueprint.json'),
            candidate=sha(source_dir / 'candidate.json'), stager=sha(Path(__file__)),
            fixtureHelper=sha(Path(__file__).with_name('aegis_citadel_lighting.py')),
            twilightHelper=sha(Path(__file__).with_name('citadel_twilight_fire_study.py'))))
    cloud_properties, cloud_scalars, cloud_vectors = reference_cloud_comparison(blueprint['lightingTreatment']['cloudFixture'])
from citadel_retained_mountain_bridge import inspect_current_mountain
from citadel_private_surface_study import MOUNTAIN_SWITCH,MOUNTAIN_MODE
mountain_inspection = inspect_current_mountain(unreal,ROOT,candidate) if os.environ.get(MOUNTAIN_SWITCH)==MOUNTAIN_MODE else None
private_surface_spec = selected_specs(os.environ, mode, ROOT, source_dir, candidate, mountain_inspection=mountain_inspection)
if private_surface_spec is not None:
    private_surface_spec['helperSha256'] = sha(Path(__file__).with_name('citadel_private_surface_study.py'))
    verify_bindings(ROOT, private_surface_spec)
study_signature_input = dict(sourceRevision=revision, sourceCity=candidate['city']['revision'],
    fixtureRequests=requests, cloud=cloud_properties, glassEmission=[10, 3.1, .4],
    mode=mode, cloudScalars=cloud_scalars, cloudVectors=cloud_vectors,
    practicalShadows=True, practicalRequests=practical_requests,
    cloth=cloth_spec, carvedStone=carved_spec,masonryTints=stone_specs,
    mountainMaterial=MOUNTAIN_MATERIAL_SPEC if mode in ALPINE_MODES else None,
    roofDetail=roof_detail,
    retainedMountainAdapterSha256=sha(Path(__file__).with_name('citadel_retained_mountain_adapter.py')),
    retainedMountainBridgeSha256=sha(Path(__file__).with_name('citadel_retained_mountain_bridge.py')),
    mountainShader=MOUNTAIN_SHADER if mode in ALPINE_MODES else None,helperSha256=sha(Path(__file__)),
    cloudDefaultWitness=cloud_default_witness,volumeProbe=volume_probe,authoredCloud=authored_cloud,alpineRelief=relief_spec,
    sculptureWeathering=sculpture_spec,
    referenceMaterialHelperSha256=sha(Path(__file__).with_name('aegis_citadel_reference_material.py')) if mode in REFERENCE_MATERIAL_MODES else None,
    mountainHelperSha256=sha(Path(__file__).with_name('aegis_citadel_mountain_material.py')))
if private_lumen_spec is not None:
    study_signature_input['privateLumen'] = private_lumen_spec
if backdrop_enabled:
    study_signature_input['distantCragBackdrop'] = backdrop_spec
if private_surface_spec is not None:
    study_signature_input['privateSurfaceStudy'] = private_surface_spec
if private_twilight_spec is not None:
    if private_surface_spec is not None and private_surface_spec['mountainMode']:
        raise RuntimeError('Retained mountain treatment stays disabled for twilight comparisons')
    study_signature_input['privateTwilightFire'] = private_twilight_spec
study_signature = digest(study_signature_input)
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
if private_surface_spec is not None and private_surface_spec['mountainMode']:
    mountain_material, mountain_readback = create_mountain(
        unreal, destination, source_dir, candidate, private_surface_spec, duplicate)
relief_mesh,relief_readback=None,None
dynamic_light_readbacks=[]
if mode in ALPINE_MODES:
    if MOUNTAIN_MATERIAL_SOURCE not in expected:
        raise RuntimeError('Original granite material is outside the signed source package closure')
    normal_convention=mountain_render_normal_convention(source_dir,candidate)
    mountain_material,mountain_readback=alpine_material(unreal,destination,duplicate,normal_convention)
    if relief_spec:
        measured=candidate['terrainCarves'][0]
        rendered_binding=measured['nativeReadback']['renderedFaces']
        rendered_file=source_dir/rendered_binding['path']
        if sha(rendered_file)!=rendered_binding['sha256']:
            raise RuntimeError('Refinement requires the exact saved mountain render buffers')
        relief_data,relief_readback=refine_native_highland(json.loads(rendered_file.read_text()))
        relief_file=output/'alpine-relief.json'
        relief_file.write_text(json.dumps(relief_data,separators=(',',':'))+'\n')
        relief_path=destination+'/Meshes/SM_AlpineRelief'
        if assets.does_asset_exist(relief_path):raise RuntimeError('Preserve an existing alpine refinement')
        # The dedicated visible component has no collision. The original measured
        # actor continues to own all ground/corridor collision in the copied level.
        import math
        native_normals=[[v/math.sqrt(sum(c*c for c in normal)) for v in normal]
            for normal in relief_data['normals']]
        relief_mesh=unreal.WarImportLibrary.create_composite_world_surface('AegisCitadel_'+study_signature[:12],
            'SM_AlpineRelief',[unreal.Vector(*p) for p in relief_data['positions']],relief_data['indices'],
            [unreal.Vector(*n) for n in native_normals],[unreal.Vector2D(*uv) for uv in relief_data['uvs']],[],
            relief_data['triangleMaterials'],[mountain_material],False)
        if not relief_mesh or not unreal.WarImportLibrary.configure_citadel_surface_lods(relief_mesh):
            raise RuntimeError('Cannot build the owned three-LOD alpine render surface')
        record(relief_path)
        render_payload=unreal.WarImportLibrary.describe_static_mesh_render_data(relief_mesh)
        render_audit=json.loads(render_payload)
        checked_render_audit(render_audit,relief_mesh.get_path_name())
        if not assets.save_loaded_asset(relief_mesh,only_if_is_dirty=False):
            raise RuntimeError('Cannot save the owned alpine render surface')
        relief_readback.update(sourceRenderedFaces=rendered_binding,sourceFile=str(relief_file),
            sourceSha256=sha(relief_file),mesh=relief_mesh.get_path_name(),renderAudit=render_audit,
            lodTriangles=[relief_mesh.get_num_triangles(i) for i in range(relief_mesh.get_num_lods())])

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
    if sculpture_spec:
        carved_readbacks['weathering']=weather_carved_stone(unreal,carved,node)
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
private_surface_readbacks = {}
private_surface_actor_readbacks = []
if private_surface_spec is not None and private_surface_spec['surfaceMode']:
    private_materials, private_surface_readbacks = create_surfaces(
        unreal, destination, revision, source_materials, private_surface_spec, duplicate)
    masonry_materials.update(private_materials)
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
authored_cloud_readback = None
if authored_cloud:
    cloud_material,authored_cloud_readback = create_cloud_material(unreal,destination,record)
if volume_probe:
    # A uniform volume isolates renderer/cloud-shell visibility from the stock
    # layout and noise graph. It is a diagnostic, never a proposed final sky.
    material_path=destination+'/Materials/M_CloudVolumeProbe'
    cloud_material=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_CloudVolumeProbe',
        destination+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    if not cloud_material:raise RuntimeError('Cannot create isolated volume probe')
    record(material_path);lib=unreal.MaterialEditingLibrary
    cloud_material.set_editor_property('material_domain',unreal.MaterialDomain.MD_VOLUME)
    cloud_material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE)
    cloud_material.set_editor_property('used_with_volumetric_cloud',True)
    if (cloud_material.get_editor_property('material_domain')!=unreal.MaterialDomain.MD_VOLUME
            or cloud_material.get_editor_property('blend_mode')!=unreal.BlendMode.BLEND_ADDITIVE
            or cloud_material.get_editor_property('used_with_volumetric_cloud') is not True):
        raise RuntimeError('The isolated probe requires an additive volume cloud material')
    for prop,wanted in ((unreal.MaterialProperty.MP_BASE_COLOR,volume_probe['albedo']),
                        (unreal.MaterialProperty.MP_SUBSURFACE_COLOR,[volume_probe['extinctionPerCm']]*3+[1])):
        node=lib.create_material_expression(cloud_material,unreal.MaterialExpressionConstant3Vector)
        node.constant=unreal.LinearColor(*wanted)
        if not lib.connect_material_property(node,'',prop) or lib.get_material_property_input_node(cloud_material,prop)!=node:
            raise RuntimeError('Volume probe has a disconnected material input')
        lighting_readback(node.constant,dict(kind='linear_color',value=wanted))
    errors=lib.recompile_material(cloud_material)
    if errors:raise RuntimeError('Volume probe did not compile: '+str(errors))
    if not assets.save_loaded_asset(cloud_material,only_if_is_dirty=False):raise RuntimeError('Cannot save volume probe')

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
        if backdrop_enabled:
            load(source)
            retained_scenery_collision[source] = collision_snapshot(unreal, own(source))
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
    if relief_spec:
        for actor in rows:
            for component in actor.get_components_by_class(unreal.PointLightComponent):
                original_mobility=component.get_editor_property('mobility')
                component.set_mobility(unreal.ComponentMobility.MOVABLE)
                if component.get_editor_property('mobility')!=unreal.ComponentMobility.MOVABLE:
                    raise RuntimeError('The copied runtime practical retained static-lighting dependence')
                dynamic_light_readbacks.append(dict(actor=actor.get_path_name(),component=component.get_path_name(),
                    sourceMobility=str(original_mobility),actualMobility='movable',intensity=component.get_editor_property('intensity')))
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
            if private_twilight_spec is not None and component.get_editor_property('mobility') != unreal.ComponentMobility.MOVABLE:
                raise RuntimeError('Twilight practical requires the actual movable source component')
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
                intensityCd=lighting_readback(component.get_editor_property('intensity'),request['intensityCd']),
                **(dict(sourceRadiusCm=lighting_readback(component.get_editor_property('source_radius'),source_light['sourceRadiusCm']),
                        mobility='movable') if private_twilight_spec is not None else {})))
        for actor in rows:
            if isinstance(actor, unreal.PointLight):
                actor.point_light_component.set_cast_shadows(True)
            if private_surface_spec is not None and private_surface_spec['surfaceMode']:
                surface_actor_before = snapshot(actor)
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
            if private_surface_spec is not None and private_surface_spec['surfaceMode']:
                replacements = {source: material.get_path_name() for source, material in masonry_materials.items()}
                replacements[glass_source] = glass.get_path_name()
                if cloth:
                    replacements[cloth_source] = cloth.get_path_name()
                if carved:
                    replacements[carved_source] = carved.get_path_name()
                surface_actor_after = snapshot(actor)
                bindings = actor_binding_readback(surface_actor_before, surface_actor_after, replacements)
                bindings = [row for row in bindings if row['actualMaterial'] in
                    {material.get_path_name() for material in private_materials.values()}]
                if bindings:
                    private_surface_actor_readbacks.append(dict(level=target, actorName=actor.get_name(),
                        actor=actor.get_path_name(), before=surface_actor_before, after=surface_actor_after, bindings=bindings))
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
            if relief_mesh:
                collision_before=component.get_collision_enabled()
                component.set_visibility(False,False)
                if component.is_visible() or component.get_collision_enabled()!=collision_before:
                    raise RuntimeError('The measured collision actor must remain enabled beneath the render replacement')
                location=actor.get_actor_location();rotation=actor.get_actor_rotation()
                visual=actors.spawn_actor_from_class(unreal.StaticMeshActor,location,rotation)
                if not visual or visual.get_outer().get_path_name().split('.')[0]!=target:
                    raise RuntimeError('Alpine render actor must belong to the exact owned copied level')
                visual.set_actor_label('Bastion alpine highland render relief')
                visual.tags=[unreal.Name('WarCitadelPrivateAlpineRelief')]
                visible=visual.static_mesh_component;visible.set_static_mesh(relief_mesh)
                visible.set_mobility(unreal.ComponentMobility.STATIC)
                visible.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                visual.set_actor_scale3d(actor.get_actor_scale3d())
                actual_render_transform=transform(visual.get_actor_transform())
                expected_render_transform=transform(actor.get_actor_transform())
                if (visible.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION
                        or not visible.is_visible() or actual_render_transform!=expected_render_transform):
                    raise RuntimeError('Alpine render replacement state differs: '+str(dict(
                        actual=actual_render_transform,expected=expected_render_transform,
                        collision=str(visible.get_collision_enabled()),visible=visible.is_visible())))
                relief_readback.update(collisionActor=actor.get_path_name(),collisionComponent=component.get_path_name(),
                    collisionEnabled=str(collision_before),collisionRetained=True,collisionMesh=component.static_mesh.get_path_name(),
                    originalRenderHidden=True,renderActor=visual.get_path_name(),renderComponent=visible.get_path_name(),
                    renderHasCollision=False,actorTransform=snapshot(visual))
            mountain_actor_readbacks.append(dict(actor=actor.get_path_name(),mesh=component.static_mesh.get_path_name(),
                sourceMaterialBindings=actual_materials,sourcePbrGraph=mountain_readback.get('sourcePbrGraph',MOUNTAIN_MATERIAL_SOURCE),
                studyMaterial=component.get_material(0).get_path_name(),
                before=before_actor,after=after_actor))
    save(target)
    if backdrop_enabled:
        retained_scenery_collision[target] = collision_snapshot(unreal, own(target))
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

if backdrop_enabled:
    backdrop_layer, backdrop_readback = stage_backdrop(unreal, ROOT, destination, study_signature,
        backdrop_spec, backdrop_mesh, record, duplicate, load, own, save)
    scenery.append(backdrop_layer)
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
if backdrop_enabled:
    for package, retained in retained_scenery_collision.items():
        checked_retained_collision(retained, collision_snapshot(unreal, own(package)))
    matches = [a for a in own(backdrop_readback['layer']) if a.get_path_name() == backdrop_readback['actor']]
    if len(matches) != 1:
        raise RuntimeError('Assembled backdrop actor is unavailable or ambiguous')
    loaded_policy = read_component_policy(unreal, matches[0].static_mesh_component)
    if loaded_policy != backdrop_readback['componentReadback']:
        raise RuntimeError('Assembled backdrop lost its saved native flags')
    backdrop_readback['loadedComponentReadback'] = loaded_policy
    backdrop_readback['retainedSceneryCollisionHashes'] = {p: digest(state) for p, state in retained_scenery_collision.items()}
    rebound, _ = bind_backdrop(ROOT, blueprint, revision)
    rebound['helperSha256'] = sha(Path(__file__).with_name('aegis_citadel_distant_crags.py'))
    rebound['candidateSha256'] = sha(source_dir / 'candidate.json')
    if rebound != backdrop_spec:
        raise RuntimeError('Backdrop inputs or protected gameplay records changed during staging')
private_surface_loaded_readbacks = []
if private_surface_spec is not None:
    verify_bindings(ROOT, private_surface_spec)
    for actor_binding in private_surface_actor_readbacks:
        matches = [actor for actor in actors.get_all_level_actors()
            if actor.get_name() == actor_binding['actorName']
            and actor.get_outer().get_path_name().split('.')[0] == actor_binding['level']]
        if len(matches) != 1 or snapshot(matches[0]) != actor_binding['after']:
            raise RuntimeError('Final loaded private surface actor state differs')
        private_surface_loaded_readbacks.append(dict(actor=matches[0].get_path_name(), bindings=actor_binding['bindings']))
    if private_surface_spec['surfaceMode']:
        private_surface_role_coverage = verify_role_coverage(private_surface_loaded_readbacks,
            [material.get_path_name() for material in private_materials.values()])
        private_sculpture_readbacks = sculpture_binding_readbacks(unreal, actors.get_all_level_actors(),
            private_surface_spec, private_materials[carved_source])
    for audit in [*private_surface_readbacks.values(), *([mountain_readback] if private_surface_spec['mountainMode'] else [])]:
        actual = graph_readback(unreal, unreal.load_asset(audit.get('graphMaterial',audit['material'])))
        if actual != audit['afterGraph']:
            raise RuntimeError('Final assembled private material graph differs from its saved readback')
        if 'afterInstance' in audit:
            native_instance=json.loads(unreal.WarImportLibrary.describe_material_instance(unreal.load_asset(audit['material'])))
            if native_instance!=audit['afterInstance']:
                raise RuntimeError('Final assembled retained MI state differs from its native saved readback')
after = {p: sha(source_file(p,h)) for p,h in expected.items()}
if before != after:
    raise RuntimeError('Private study changed retained or historical native bytes')
report = dict(schemaVersion=1, diagnosticOnly=True, signature=study_signature,
    helperSha256=sha(Path(__file__)), cloudDefaultWitness=cloud_default_witness,
    exposureUsesExtendedEV100=exposure_extended,exposureUnits=blueprint['lightingTreatment']['exposureUnits'],
    glassCompileErrors=list(glass_compile_errors),
    mode=mode, cloudParameterReadbacks=cloud_parameter_readbacks, cloudProperties=cloud_properties,volumeProbe=volume_probe,
    authoredCloudReadback=authored_cloud_readback,
    clothSpec=cloth_spec, clothReadbacks=cloth_readbacks,carvedStoneSpec=carved_spec,carvedStoneReadbacks=carved_readbacks,
    masonryTints=stone_specs,masonryReadbacks=masonry_readbacks,
    mountainMaterialReadback=mountain_readback,mountainActorReadbacks=mountain_actor_readbacks,
    roofDetail=roof_detail,alpineReliefReadback=relief_readback,dynamicPracticalReadbacks=dynamic_light_readbacks,
    historicalGeometryRevision=revision, blueprintPath=str(source_dir / 'blueprint.json'),
    blueprintSha256=sha(source_dir / 'blueprint.json'), map=map_path,
    mapSha256=sha(package_file(ROOT, map_path)), cityRevision=city['revision'],
    fixtures=fixture_readbacks,loadedDirectionalLights=loaded_lights,loadedFogState=loaded_fogs,
    practicalReadbacks=practical_readbacks,
    brazierReadbacks=brazier_readbacks,glassEmissionReadback=glass_emission_readback,
    createdPackageHashes={p: sha(package_file(ROOT, p)) for p in created},
    sourceAndCandidateHashesUnchanged=True, visualApproved=False, lightingApproved=False,
    physicalTraversalApproved=False, gameplayApproved=False, releaseAcceptance=False)
if private_surface_spec is not None:
    report['privateSurfaceStudy'] = dict(spec=private_surface_spec,
        materials=private_surface_readbacks, actorBindings=private_surface_actor_readbacks,
        loadedBindings=private_surface_loaded_readbacks,
        roleCoverage=private_surface_role_coverage if private_surface_spec['surfaceMode'] else None,
        sculptures=private_sculpture_readbacks if private_surface_spec['surfaceMode'] else [],
        mountain=mountain_readback if private_surface_spec['mountainMode'] else None,
        editorGraphReadbackMatches=True, coldProcessVerified=False,
        rendererStateVerified=False, visualApproved=False, releaseAcceptance=False)
if private_lumen_spec is not None:
    # Inspect the complete loaded static-mesh closure without rebuilding or
    # saving its shared dependencies. Resource presence is not surface coverage.
    inventory={}
    for actor in actors.get_all_level_actors():
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh=component.static_mesh
            if not mesh:
                continue
            path=mesh.get_path_name()
            if path not in inventory:
                package=path.split('.')[0]
                file=performance_package_file(ROOT,package)
                inventory[path]=dict(mesh=path,packageSha256=sha(file),
                    resources=json.loads(unreal.WarImportLibrary.describe_static_mesh_lumen_resources(mesh)),components=[])
            inventory[path]['components'].append(dict(actor=actor.get_path_name(),component=component.get_path_name(),
                visible=component.is_visible(),hiddenInGame=component.get_editor_property('hidden_in_game'),
                actorHidden=actor.get_editor_property('hidden'),affectDistanceFieldLighting=component.get_editor_property('affect_distance_field_lighting'),
                visibleInRayTracing=component.get_editor_property('visible_in_ray_tracing')))
    report['privateLumen'] = private_lumen_spec
    report['rendererStateVerified'] = False
    report['nativeResourcePresenceReady'] = False
    report['nativeResourceAudit'] = dict(schemaVersion=1,readOnly=True,meshes=list(inventory.values()),
        meshCount=len(inventory),runtimeSceneMembershipVerified=False,surfaceCacheCoverageVerified=False)
    report['blendedViewReadback'] = None
    report['rendererPassWitness'] = None
if private_twilight_spec is not None:
    report['privateTwilightFire'] = dict(spec=private_twilight_spec,
        editorObjectReadback=checked_twilight_fire_readbacks(private_twilight_spec, fixture_readbacks,
            practical_readbacks, loaded_lights, destination))
if backdrop_enabled:
    report['distantCragBackdrop'] = backdrop_readback
(output / 'study.json').write_text(json.dumps(report, indent=2) + '\n')
pending.unlink()
unreal.log('WAR_CITADEL_PRIVATE_LIGHTING_STUDY=' + str(output / 'study.json'))
