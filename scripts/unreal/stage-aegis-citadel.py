"""Build isolated native citadel candidates; never publishes or approves them.

Root serializes this commandlet with all Editor/game writers closed. Existing
outputs are verified, never blindly overwritten. Licensed/shared sources remain
intact. The exact 2,267 castle identities and separately hashed upper enclosure
parts are replaced in copies, with every outside-mask state proved unchanged.
"""
import json
import hashlib
import math
import copy
import sys
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from aegis_citadel_blueprint import (OUT,digest,sha,validate,castle_identity,contains,route_clearance,cloud_material_file,enclosure_edit_bounds)
from aegis_citadel_terrain import native_terrain_carve_document
from aegis_citadel_terrain_readback import checked_committed_carve,native_terrain_policy
from aegis_citadel_terrain_render_readback import checked_rendered_carve
from citadel_route_surface_evidence import checked_surface_bindings
from shared_city_sources import source_plan, package_file
from shared_city_authoring import prepare_city
from world_actor_state import snapshot
from citadel_stage_contract import (REVIEW_START_CM, require_final_city_hashes, canonical_city_payload,
    SOURCE_TRIANGLE_CONVENTION,NATIVE_IMPORT_CONVENTION,NATIVE_MESH_BUILD_SETTINGS,
    OVERLAY_LIGHT_FIXTURES,expected_overlay_light,checked_render_audit,checked_terrain_render_audit,source_array_sha256,
    expected_shared_lighting_fixture,native_lighting_value,lighting_readback,checked_lighting_exposure,
    native_triangle_indices,checked_private_proof_start)

current=json.loads((OUT/'current.json').read_text());RUN=OUT/current['revision']
plan=json.loads((RUN/'blueprint.json').read_text());validate(plan)
if not plan['baseline']:raise RuntimeError('Fresh native baseline is required before staging')
baseline=json.loads((ROOT/plan['baseline']['file']).read_text())
if {k:v for k,v in baseline.items() if k!='actors'}!=plan['baseline']:
    raise RuntimeError('Baseline changed after planning; generate a new revision')
if baseline.get('schemaVersion')!=2 or not baseline.get('gameplayActors') or not baseline.get('terrainProbes'):
    raise RuntimeError('Actual campaign services/connections and upper terrain clearance need a fresh native survey')
if baseline['terrainSurveyRoutesSha256']!=digest(plan['routes']):
    raise RuntimeError('Terrain survey does not cover the current authored routes')
if baseline.get('terrainSurveyPerformanceSha256')!=digest(plan['performanceFormations']):
    raise RuntimeError('Fresh native survey does not cover the 108 signed crowd standing points')
if baseline.get('terrainSurveySurfaceProfilesSha256')!=digest(plan['routeSurfaceProfiles']):
    raise RuntimeError('Fresh native survey does not cover the exact full-width approach surfaces')
surface_height_field=plan['routeSurfaceHeightField']
if sha(ROOT/surface_height_field['file'])!=surface_height_field['sha256']:
    raise RuntimeError('Original graded paving source changed after the fan was authored')
if baseline.get('terrainSurveyCorridorPolicy')!=dict(lanes=[-1,-.5,0,.5,1],maximumSpacingCm=400,
        edgeInsetCm=42,turnBlendSteps=[0,.25,.5,.75,1],nativeTraversalApproved=False,
        surfaceCapsulePoseMethod='signed_piecewise_floor_and_actual_spherical_capsule'):
    raise RuntimeError('Fresh actual survey must include the full reserved route widths and turn elbows')
for spec in plan['terrainCarves']:
    if not spec.get('sourceNativePolicy') or not spec.get('sourcePolicySurvey'):
        raise RuntimeError('Fresh actual original terrain build/collision policy must be signed before staging')
    witness=spec['sourcePolicySurvey'];file=(ROOT/witness['path']).resolve()
    file.relative_to((OUT/'surveys').resolve())
    if sha(file)!=witness['sha256'] or json.loads(file.read_text())!=baseline:
        raise RuntimeError('Immutable actual native terrain policy survey changed after signing')
enclosure_edits=plan['editMask']['upperEnclosureEdits']
for edit in enclosure_edits:enclosure_edit_bounds(plan['editMask'],edit)
if any(e.get('clipRequired') for e in enclosure_edits):
    raise RuntimeError('A compound enclosure needs an outside-preserving source triangle clip before staging')
removed_keys={(r['package'],r['actor']) for r in baseline['castleActors']}
removed_keys.update((r['package'],r['actor']) for r in enclosure_edits if r['mode']=='actor')
removed_components={(r['package'],r['actor'],name) for r in enclosure_edits
                    for name in r.get('removeComponents',[])}
def will_remove(hit):
    blocker=baseline['blockerMetadata'].get(hit['actor'])
    return bool(blocker and ((blocker['package'],blocker['actor']) in removed_keys or
        (blocker['package'],blocker['actor'],str(hit['component']).rsplit('.',1)[-1]) in removed_components))
def will_carve(hit,point):
    blocker=baseline['blockerMetadata'].get(hit['actor'])
    if not blocker:return False
    return any(blocker['package']==row['package'] and blocker['actor']==row['actor']
        and str(hit['component']).rsplit('.',1)[-1]==row['component']
        and digest(blocker['state'])==row['sourceStateHash']
        and any(all(volume['bounds'][0][j]<=point[j]<=volume['bounds'][1][j] for j in range(3))
                for volume in row['worldVolumes']) for row in plan['terrainCarves'])
unresolved=[row for row in baseline['terrainIntrusions'] if
            row['floorIntrusion'] and not (will_remove(row['floorHit']) or will_carve(row['floorHit'],row['point'])) or
            row['capsuleBlocked'] and not (will_remove(row['capsuleHit']) or will_carve(row['capsuleHit'],row['point']))]
if unresolved:raise RuntimeError('Retained terrain/scenery still intrudes into planned floors/capsules: '+str(unresolved[:3]))
city=next(c for c in source_plan(ROOT)['cities'] if c['id']=='aegis_capital')
if city!=baseline['city']:raise RuntimeError('Published city changed; preserve edits and re-survey')
for p,h in baseline['packageHashes'].items():
    if sha(package_file(ROOT,p))!=h:raise RuntimeError('Changed source package: '+p)
source=json.loads((RUN/'assets-source.json').read_text())
if source['blueprintSignature']!=plan['signature']:raise RuntimeError('Geometry was built for a different blueprint')
if source['geometrySignature']!=digest([(r['id'],r['sha256']) for r in source['assets']]):
    raise RuntimeError('Authored geometry manifest changed')
surface_meshes={}
for row in source['assets']:
    file=(RUN/row['meshFile']).resolve();file.relative_to(RUN.resolve())
    if sha(file)!=row['sha256']:raise RuntimeError('Changed source geometry before staging: '+row['id'])
    if row['id'] in {p['meshId'] for p in plan['routeSurfaceProfiles']}:
        surface_meshes[row['id']]=json.loads(file.read_text())
checked_surface_bindings(source,plan,surface_meshes)
for file,expected in source['materialSources'].items():
    if sha(ROOT/file)!=expected:raise RuntimeError('Original PBR source changed before staging: '+file)
master=(RUN/source['sourceMaster']['path']).resolve();master.relative_to(RUN.resolve())
if sha(master)!=source['sourceMaster']['sha256']:raise RuntimeError('Authored Blender master changed; export its new revision first')
for recipe,expected in plan['sourceRecipes'].items():
    if sha(Path(__file__).with_name(recipe))!=expected:raise RuntimeError('Authoring recipe changed; generate and build a new revision')
exposure_extended=checked_lighting_exposure(plan['lightingTreatment'],
    unreal.SystemLibrary.get_console_variable_bool_value('r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange'))
cloud_spec=plan['lightingTreatment']['cloudFixture']
if plan['lightingTreatment']['schemaVersion']!=2 or not cloud_spec:
    raise RuntimeError('Fresh measured seven-fixture lighting and owned cloud recipe are required')
if sha(cloud_material_file())!=cloud_spec['material']['sha256']:
    raise RuntimeError('Reviewed original Engine cloud material changed')
source_hashes={**baseline['packageHashes'],cloud_spec['material']['package']:cloud_spec['material']['sha256']}
DEST='/Game/WorldRebuild/AegisCitadel_'+plan['revision']
assets=unreal.EditorAssetLibrary;levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
wing_ground_witness=plan.get('wingFoundationGroundSurvey')
if plan.get('recipeVersion',0)>=9:
    from citadel_wing_support_evidence import checked_ground_summary
    if not wing_ground_witness:
        raise RuntimeError('Wing foundation repairs require their signed native ground survey')
    wing_ground_file=(ROOT/wing_ground_witness['file']).resolve()
    wing_ground_file.relative_to(OUT.resolve())
    if sha(wing_ground_file)!=wing_ground_witness['sha256']:
        raise RuntimeError('Native wing ground witness changed after signing')
    wing_ground_report=json.loads(wing_ground_file.read_text())
    if checked_ground_summary(wing_ground_report)!=wing_ground_witness['summary']:
        raise RuntimeError('Native wing ground summary differs from its signed witness')
    if any(wing_ground_report['packageHashes'].get(p)!=h for p,h in baseline['packageHashes'].items()):
        raise RuntimeError('Native wing ground witness belongs to changed source packages')
mesh_tools=(unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))


def save(obj):
    if not assets.save_loaded_asset(obj,False):raise RuntimeError('Native save failed: '+obj.get_path_name())


def load(package):
    if not levels.load_level(package):raise RuntimeError('Native level unavailable: '+package)
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.GameplayStatics.flush_level_streaming(world)
    return world


def replay_wing_ground(world,geometry_layer):
    if plan.get('recipeVersion',0)<9:return None
    unreal.WarImportLibrary.prepare_world_preview_frame(world)
    ignored=[a for a in actors.get_all_level_actors()
             if a.get_outer().get_path_name().split('.')[0]==geometry_layer]
    if not ignored:raise RuntimeError('Owned wing geometry must be loaded before ground replay')
    actual=[]
    for sample in wing_ground_report['samples']:
        x,y=sample['xCm'],sample['yCm']
        hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,20000),
            unreal.Vector(x,y,-5000),unreal.TraceTypeQuery.ECC_VISIBILITY,True,ignored,
            unreal.DrawDebugTrace.NONE,True)
        values=hit.to_tuple() if hit else None
        if not values or not values[0]:raise RuntimeError('A wing ground contact disappeared')
        point,normal,actor,component=values[5],values[7],values[9],values[10]
        measured=[point.x,point.y,point.z]
        difference=math.dist(measured,sample['pointCm'])
        if (difference>.01 or not actor or not component
                or actor.get_name()!=sample['actor'].rsplit('.',1)[-1]
                or component.get_name()!=sample['component'].rsplit('.',1)[-1]
                or sum(a*b for a,b in zip((normal.x,normal.y,normal.z),sample['normal']))<.99999):
            raise RuntimeError('A measured wing ground surface or binding changed after import')
        actual.append(dict(pointCm=measured,normal=[normal.x,normal.y,normal.z],
            actor=actor.get_path_name(),component=component.get_path_name(),differenceCm=difference))
    return dict(sourceWitness=wing_ground_witness,samples=actual,passed=True,
        maximumPointDifferenceCm=max(row['differenceCm'] for row in actual),
        foundationApproved=False,physicalTraversalApproved=False)


def own(package):return [a for a in actors.get_all_level_actors() if a.get_outer().get_path_name().split('.')[0]==package]


def world_hashes(packages):return {p:sha(package_file(ROOT,p)) for p in packages}


def select_owned_level(package):
    if not levels.set_current_level_by_name(package.rsplit('/',1)[1]):
        raise RuntimeError('Cannot select intended actor owner: '+package)


def validate_scenery(package):
    # Native exact-class policy is also enforced by ValidateLevel in navigation
    # and runtime. Reject invalid templates before any shared definition is saved.
    for actor in own(package):
        if not unreal.WarCityDefinition.is_scenery_actor(actor):
            raise RuntimeError('Gameplay actor in private scenery: '+actor.get_path_name())
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            if not component.is_visible():continue
            mesh=component.static_mesh
            if not mesh or not mesh.get_path_name().startswith('/Game/'):
                raise RuntimeError('Missing or substitute scenery model')
            if any(not component.get_material(i) for i in range(component.get_num_materials())):
                raise RuntimeError('Missing scenery material')


def place_gameplay_pad(field,pad):
    actor=field.get_editor_property(pad['binding'])[pad['index']]
    if not actor:raise RuntimeError('Missing bound gameplay prop: '+pad['id'])
    before=snapshot(actor)
    if pad.get('preserveTransform'):
        return dict(id=pad['id'],actor=actor.get_path_name(),preserved=True,stateHash=digest(before))
    center,extent=actor.get_actor_bounds(False)
    radius=math.hypot(extent.x,extent.y);height=extent.z*2
    if radius>pad['maximumFootprintRadiusCm'] or height>pad['maximumHeightCm']:
        raise RuntimeError('Actual native gameplay prop exceeds signed clear pad: '+pad['id'])
    point=pad['footprintCentreFloorCm'];location=actor.get_actor_location()
    actor.set_actor_location(unreal.Vector(location.x+point[0]-center.x,location.y+point[1]-center.y,
                                          location.z+point[2]-(center.z-extent.z)),False,True)
    center,extent=actor.get_actor_bounds(False)
    actual=[center.x,center.y,center.z-extent.z]
    if math.dist(actual,point)>.1 or not route_clearance(plan,actual,radius,height):
        raise RuntimeError('Actual native gameplay bounds obstruct a reserved route: '+pad['id'])
    if pad['binding']=='gate_mechanisms':
        capture_radius=float(field.get_editor_property('objective_radius'))
        if capture_radius>pad['captureClearRadiusCm']:
            raise RuntimeError('Native capture radius exceeds the signed mechanism exclusion ring')
        for anchor in plan['objectives'][4:7]+plan['optionalObjectives'][1:2]:
            if math.dist(actual[:2],anchor[:2])<radius+capture_radius+pad['minimumCaptureGapCm']:
                raise RuntimeError('Gate mechanism obstructs a native player capture ring: '+pad['id'])
    return dict(id=pad['id'],actor=actor.get_path_name(),preserved=False,
        footprintCentreFloorCm=actual,footprintRadiusCm=radius,heightCm=height,
        boundsCm=[[center.x-extent.x,center.y-extent.y,center.z-extent.z],
                  [center.x+extent.x,center.y+extent.y,center.z+extent.z]],
        sourceStateHash=digest(before),actualStateHash=digest(snapshot(actor)))


def apply_shared_lighting(package,source_package):
    changes=[]
    for spec in plan['lightingTreatment']['fixtures']:
        if spec['package']!=source_package:continue
        matches=[a for a in own(package) if expected_shared_lighting_fixture(spec,a.get_name(),snapshot(a),source_package)]
        if len(matches)!=1:raise RuntimeError('Shared environment fixture identity changed: '+spec['actor'])
        actor=matches[0];before=snapshot(actor)
        if digest(before)!=spec['sourceStateHash']:raise RuntimeError('Shared fixture changed after survey')
        if spec['component']:
            components=actor.get_components_by_class(getattr(unreal,spec['component']))
            if len(components)!=1:raise RuntimeError('Ambiguous shared lighting component')
            target=components[0]
            if spec['id'] in ('sun','soft_sky_fill','ambient_sky','dutch_street_fill'):
                target.set_mobility(unreal.ComponentMobility.MOVABLE)
        else:target=actor.get_editor_property('settings')
        actual={}
        for key,wanted in spec['properties'].items():
            target.set_editor_property(key,native_lighting_value(wanted))
            actual[key]=lighting_readback(target.get_editor_property(key),wanted)
        if not spec['component']:actor.set_editor_property('settings',target)
        if 'rotationDegrees' in spec:
            pitch,yaw,roll=spec['rotationDegrees']
            actor.set_actor_rotation(unreal.Rotator(pitch=pitch,yaw=yaw,roll=roll),False)
            rotation=actor.get_actor_rotation()
            actual['rotationDegrees']=[rotation.pitch,rotation.yaw,rotation.roll]
            if any(abs(a-b)>.001 for a,b in zip(actual['rotationDegrees'],spec['rotationDegrees'])):
                raise RuntimeError('Shared light orientation changed')
        changes.append(dict(id=spec['id'],sourcePackage=source_package,package=package,actor=actor.get_name(),
            klass=spec['klass'],label=spec['label'],component=spec['component'],requiredTag=spec['requiredTag'],
            actualTags=list(snapshot(actor)['tags']),sourcePackageSha256=spec['sourcePackageSha256'],
            sourceStateHash=digest(before),actualStateHash=digest(snapshot(actor)),
            requestedProperties=spec['properties'],actualPropertyReadback=actual))
    return changes


receipt=RUN/'candidate.json'
if receipt.exists():
    existing=json.loads(receipt.read_text())
    if existing['geometrySignature']!=source['geometrySignature']:raise RuntimeError('Native candidate no longer matches its authored geometry')
    if existing.get('nativeImportConvention')!=NATIVE_IMPORT_CONVENTION:
        raise RuntimeError('Existing candidate needs the bounded native winding repair')
    for p,h in existing['packageHashes'].items():
        if sha(package_file(ROOT,p))!=h:raise RuntimeError('Preserve independently edited candidate: '+p)
    unreal.log('WAR_CITADEL_CANDIDATE_UNCHANGED='+str(receipt))
else:
    pending=RUN/'stage-pending.json'
    if pending.exists():raise RuntimeError('An interrupted candidate needs explicit journal recovery: '+str(pending))
    pending.write_text(json.dumps(dict(revision=plan['revision'],sourceHashes=source_hashes,created=[]),indent=2)+'\n')
    def created(package):
        journal=json.loads(pending.read_text());journal['created'].append(package)
        pending.write_text(json.dumps(journal,indent=2)+'\n')
    def import_texture(file,channel,power_of_two=None):
        texture_path=DEST+'/Textures/T_'+Path(file).stem+'_'+channel
        if not assets.does_asset_exist(texture_path):
            if sha(ROOT/file)!=source['materialSources'][file]:raise RuntimeError('Changed original PBR texture: '+file)
            task=unreal.AssetImportTask();task.filename=str(ROOT/file)
            task.destination_path=DEST+'/Textures';task.destination_name='T_'+Path(file).stem+'_'+channel
            task.automated=True;task.save=True;unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            created(texture_path)
        texture=unreal.load_asset(texture_path)
        if not isinstance(texture,unreal.Texture2D):raise RuntimeError('Original PBR texture import failed: '+file)
        texture.set_editor_property('srgb',channel=='baseColor')
        if channel=='normal':texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
        elif channel=='orm':texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
        elif channel=='height':texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_GRAYSCALE)
        if power_of_two:
            if power_of_two!='stretch_to_2048':raise RuntimeError('Unknown original texture mip policy')
            texture.set_editor_property('power_of_two_mode',unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
            texture.set_editor_property('mip_gen_settings',unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
            texture.set_editor_property('max_texture_size',2048)
        texture.set_editor_property('address_x',unreal.TextureAddress.TA_WRAP)
        texture.set_editor_property('address_y',unreal.TextureAddress.TA_WRAP)
        save(texture);return texture
    materials=[];material_bindings=[]
    for role,spec in source['materialSpecs'].items():
        path=DEST+'/Materials/M_'+role
        if assets.does_asset_exist(path):raise RuntimeError('Unreceipted native material: '+path)
        tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
        material=tools.create_asset('M_'+role,DEST+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
        created(path)
        def connect(a,output,b,pin):
            if not lib.connect_material_expressions(a,output,b,pin):
                raise RuntimeError('Disconnected '+role+' shader input '+pin)
        def property_input(node,output,prop):
            if not lib.connect_material_property(node,output,prop):
                raise RuntimeError('Disconnected '+role+' material property '+str(prop))
            actual=lib.get_material_property_input_node(material,prop)
            if not actual or actual.get_path_name()!=node.get_path_name():
                raise RuntimeError('Incorrect '+role+' material property input '+str(prop))
        tint=lib.create_material_expression(material,unreal.MaterialExpressionConstant3Vector)
        tint.constant=unreal.LinearColor(*spec['tint'],1)
        def sample(channel):
            node=lib.create_material_expression(material,unreal.MaterialExpressionTextureSample)
            node.texture=import_texture(spec[channel],channel,spec.get('texturePowerOfTwo'))
            node.sampler_type=(unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='baseColor' else
                               unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='normal' else
                               unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
            return node
        if 'baseColor' in spec:
            color=sample('baseColor');multiply=lib.create_material_expression(material,unreal.MaterialExpressionMultiply)
            connect(color,'RGB',multiply,'A');connect(tint,'',multiply,'B')
            property_input(multiply,'',unreal.MaterialProperty.MP_BASE_COLOR)
        else:property_input(tint,'',unreal.MaterialProperty.MP_BASE_COLOR)
        packed=sample('orm') if 'orm' in spec else None
        for key,prop in [('roughness',unreal.MaterialProperty.MP_ROUGHNESS),('metallic',unreal.MaterialProperty.MP_METALLIC)]:
            value=lib.create_material_expression(material,unreal.MaterialExpressionConstant);value.r=spec[key]
            if packed:
                multiply=lib.create_material_expression(material,unreal.MaterialExpressionMultiply)
                connect(packed,'G' if key=='roughness' else 'B',multiply,'A')
                connect(value,'',multiply,'B');property_input(multiply,'',prop)
            else:property_input(value,'',prop)
        if 'specular' in spec:
            value=lib.create_material_expression(material,unreal.MaterialExpressionConstant);value.r=spec['specular']
            property_input(value,'',unreal.MaterialProperty.MP_SPECULAR)
        if packed:property_input(packed,'R',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
        if 'normal' in spec:
            normal=sample('normal');strength=lib.create_material_expression(material,unreal.MaterialExpressionConstant3Vector)
            strength.constant=unreal.LinearColor(.45,.45,1,1)
            multiply=lib.create_material_expression(material,unreal.MaterialExpressionMultiply)
            connect(normal,'RGB',multiply,'A');connect(strength,'',multiply,'B')
            normalized=lib.create_material_expression(material,unreal.MaterialExpressionNormalize)
            connect(multiply,'',normalized,'VectorInput')
            property_input(normalized,'',unreal.MaterialProperty.MP_NORMAL)
        if 'height' in spec:
            if any(key in spec for key in ('normal','orm')):raise RuntimeError('Unrelated normal/ORM mixed with original height')
            function=unreal.load_asset('/Engine/Functions/Engine_MaterialFunctions03/Procedurals/NormalFromHeightmap')
            if not function:raise RuntimeError('Native matching height-normal function unavailable')
            height=lib.create_material_expression(material,unreal.MaterialExpressionTextureObject)
            height.texture=import_texture(spec['height'],'height',spec['texturePowerOfTwo'])
            height.sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE
            normal=lib.create_material_expression(material,unreal.MaterialExpressionMaterialFunctionCall)
            normal.set_editor_property('material_function',function)
            # Connect only actual named function pins. Silent failed connections
            # would otherwise leave a compiled but flat/misleading material.
            connect(height,'',normal,'Height Map')
            selector=lib.create_material_expression(material,unreal.MaterialExpressionConstant4Vector)
            selector.constant=unreal.LinearColor(1,0,0,0)
            connect(selector,'',normal,'Height Map Channel Selector')
            strength=lib.create_material_expression(material,unreal.MaterialExpressionConstant)
            strength.r=spec['heightStrength'];connect(strength,'',normal,'Normal Map Intensity')
            offset=lib.create_material_expression(material,unreal.MaterialExpressionConstant)
            offset.r=1/1254;connect(offset,'',normal,'Height Map UV Offset')
            property_input(normal,'',unreal.MaterialProperty.MP_NORMAL)
        if 'emission' in spec:
            emission=lib.create_material_expression(material,unreal.MaterialExpressionConstant3Vector)
            emission.constant=unreal.LinearColor(*spec['emission'],1)
            property_input(emission,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        material.set_editor_property('two_sided',role=='blue');lib.recompile_material(material);save(material)
        materials.append(material)
        if role=='blue':
            if set(spec)!={'tint','roughness','metallic','specular'}:
                raise RuntimeError('Navy cloth must retain its original matte scalar-only policy')
            color_node=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_BASE_COLOR)
            if not isinstance(color_node,unreal.MaterialExpressionConstant3Vector):
                raise RuntimeError('Navy cloth tint is not the actual signed constant input')
            color=color_node.get_editor_property('constant')
            readback=dict(tint=[color.r,color.g,color.b])
            for key,prop in [('roughness',unreal.MaterialProperty.MP_ROUGHNESS),
                    ('metallic',unreal.MaterialProperty.MP_METALLIC),('specular',unreal.MaterialProperty.MP_SPECULAR)]:
                node=lib.get_material_property_input_node(material,prop)
                if not isinstance(node,unreal.MaterialExpressionConstant):
                    raise RuntimeError('Navy cloth scalar graph is not the signed actual constant: '+key)
                readback[key]=node.get_editor_property('r')
                if not math.isfinite(readback[key]) or abs(readback[key]-spec[key])>1e-6:
                    raise RuntimeError('Navy cloth scalar readback differs from source: '+key)
            if any(abs(a-b)>1e-6 for a,b in zip(readback['tint'],spec['tint'])):
                raise RuntimeError('Navy cloth tint readback differs from source')
            for key,prop in [('normalInputConnected',unreal.MaterialProperty.MP_NORMAL),
                    ('ambientOcclusionInputConnected',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)]:
                readback[key]=bool(lib.get_material_property_input_node(material,prop))
                if readback[key]:raise RuntimeError('Navy cloth acquired an unrelated texture input: '+key)
            material_bindings.append(dict(role=role,package=path,sha256=sha(package_file(ROOT,path)),
                sourceSpec=spec,actualConstantReadback=readback))
    bindings=[]
    for row in source['assets']:
        file=(RUN/row['meshFile']).resolve();file.relative_to(RUN.resolve())
        if sha(file)!=row['sha256']:raise RuntimeError('Changed authored source mesh: '+row['id'])
        mesh_json=file.read_text();mesh_data=json.loads(mesh_json);key='SM_'+row['id'];path=DEST+'/Meshes/'+key
        native_indices=native_triangle_indices(mesh_data,SOURCE_TRIANGLE_CONVENTION)
        if assets.does_asset_exist(path):raise RuntimeError('Preserve unreceipted native mesh: '+path)
        mesh=unreal.WarImportLibrary.create_composite_world_surface('AegisCitadel_'+plan['revision'],key,
            [unreal.Vector(*p) for p in mesh_data['positions']],native_indices,
            [unreal.Vector(*p) for p in mesh_data['normals']],[unreal.Vector2D(*p) for p in mesh_data['uvs']],[],
            mesh_data['triangleMaterials'],materials,row['collision'])
        if not mesh:raise RuntimeError('Native authored mesh creation failed: '+key)
        created(path)
        # Reductions are native, platform-scalable LODs; route collision retains LOD0.
        if not unreal.WarImportLibrary.configure_citadel_surface_lods(mesh):
            raise RuntimeError('Owned native surface could not build its signed three-LOD policy: '+key)
        if mesh.get_num_lods()!=3:raise RuntimeError('Native surface did not retain all three signed LODs: '+key)
        for index in range(mesh.get_num_lods()):
            actual=mesh_tools.get_lod_build_settings(mesh,index)
            if any(actual.get_editor_property(k)!=v for k,v in NATIVE_MESH_BUILD_SETTINGS.items()):
                raise RuntimeError('Native build settings changed source normal/UV policy: '+key)
        if (mesh.get_editor_property('light_map_coordinate_index')!=1 or mesh.get_editor_property('light_map_resolution')!=128
                or mesh.get_editor_property('allow_cpu_access') is not True or mesh.get_editor_property('lod_for_collision')!=0):
            raise RuntimeError('Native surface changed its signed render/collision access policy: '+key)
        save(mesh)
        render_payload=unreal.WarImportLibrary.describe_static_mesh_render_data(mesh)
        render_audit=checked_render_audit(json.loads(render_payload),mesh.get_path_name())
        bindings.append(dict(id=row['id'],mesh=path,sha256=sha(package_file(ROOT,path)),gateLeaf=row['gateLeaf'],
                             sourceIndicesSha256=digest(mesh_data['indices']),nativeIndicesSha256=digest(native_indices),
                             sourceArrayHashConvention='sha256_raw_utf8_mesh_json_member_array',
                             sourcePositionsSha256=source_array_sha256(mesh_json,'positions'),
                             sourceNormalsSha256=source_array_sha256(mesh_json,'normals'),sourceUVsSha256=source_array_sha256(mesh_json,'uvs'),
                             renderDataAudit=render_audit,renderDataAuditPayload=render_payload,
                             renderDataAuditSha256=hashlib.sha256(render_payload.encode()).hexdigest(),nativeMeshBuildSettings=NATIVE_MESH_BUILD_SETTINGS,
                             triangles=[mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())]))
    removal_by_identity={r['identity']:r for r in baseline['castleActors']}
    if set(removal_by_identity)!={r['identity'] for r in plan['editMask']['removeActors']}:
        raise RuntimeError('Live castle identities differ from the bounded reference removal set')
    terrain_changes=[];carved_meshes={};terrain_folder=RUN/'terrain-carves';terrain_folder.mkdir(exist_ok=True)
    for spec in plan['terrainCarves']:
        original_file=ROOT/spec['sourceExportFile'];original_bytes=original_file.read_bytes()
        if sha(original_file)!=spec['sourceExportSha256']:raise RuntimeError('Actual committed terrain source changed')
        original_copy=terrain_folder/'mountain-source.json';original_copy.write_bytes(original_bytes)
        document=native_terrain_carve_document(original_bytes.decode('utf-8'),source_provenance=spec)
        if (document['actorTransform']!=spec['actorTransform'] or document['worldVolumes']!=spec['worldVolumes']
                or document['localVolumeBounds']!=spec['localVolumeBounds']):
            raise RuntimeError('Terrain carve left its exact signed occupied volume')
        document_file=terrain_folder/'hall-carve.json';document_file.write_text(json.dumps(document,separators=(',',':'))+'\n')
        path=DEST+'/Meshes/SM_HallCarvedMountain'
        if assets.does_asset_exist(path):raise RuntimeError('Preserve unreceipted private terrain mesh')
        original_mesh=unreal.load_asset(spec['sourceMesh']);original_policy=native_terrain_policy(original_mesh,mesh_tools)
        if original_policy!=spec['sourceNativePolicy']:
            raise RuntimeError('Original native terrain build/collision policy changed after the signed survey')
        original_stored_payload=unreal.WarImportLibrary.describe_static_mesh_stored_corners(original_mesh,0)
        original_rendered_payload=unreal.WarImportLibrary.describe_static_mesh_rendered_faces(original_mesh,0)
        mesh=unreal.WarImportLibrary.create_carved_citadel_terrain(original_mesh,
            DEST.rsplit('/',1)[-1],document_file.read_text())
        if not mesh or mesh.get_path_name()!=path+'.SM_HallCarvedMountain':
            raise RuntimeError('Native full-attribute source-preserving terrain carve failed')
        created(path);save(mesh)
        referenced_payload=unreal.WarImportLibrary.describe_static_mesh_source_data(mesh,0)
        stored_payload=unreal.WarImportLibrary.describe_static_mesh_stored_corners(mesh,0)
        render_payload=unreal.WarImportLibrary.describe_static_mesh_render_data(mesh)
        rendered_payload=unreal.WarImportLibrary.describe_static_mesh_rendered_faces(mesh,0)
        comparison=checked_committed_carve(document,json.loads(referenced_payload),json.loads(stored_payload),
            mesh.get_path_name(),json.loads(original_stored_payload))
        rendered_comparison=checked_rendered_carve(document,json.loads(original_rendered_payload),
            json.loads(rendered_payload),original_policy,mesh.get_path_name())
        checked_terrain_render_audit(json.loads(render_payload),mesh.get_path_name(),
            original_policy['sourceLods'],comparison,rendered_comparison)
        actual_policy=native_terrain_policy(mesh,mesh_tools)
        if actual_policy!=original_policy:raise RuntimeError('Private terrain clone changed original build/material/collision policy')
        def raw_terrain_readback(name,payload):
            file=terrain_folder/name;file.write_text(payload,encoding='utf-8')
            return dict(path=file.relative_to(RUN).as_posix(),sha256=sha(file))
        native_readback=dict(comparison=comparison,
            referencedSource=raw_terrain_readback('hall-carve-committed-source.json',referenced_payload),
            storedCorners=raw_terrain_readback('hall-carve-stored-corners.json',stored_payload),
            renderDataAudit=raw_terrain_readback('hall-carve-render-data.json',render_payload),
            originalStoredCorners=raw_terrain_readback('hall-carve-original-stored-corners.json',original_stored_payload),
            originalRenderedFaces=raw_terrain_readback('hall-carve-original-rendered-faces.json',original_rendered_payload),
            renderedFaces=raw_terrain_readback('hall-carve-rendered-faces.json',rendered_payload),
            renderedComparison=rendered_comparison,
            sourcePolicy=original_policy,actualPolicy=actual_policy,nativePolicyPreserved=True)
        carved_meshes[spec['id']]=(mesh,dict(id=spec['id'],sourcePackage=spec['package'],
            actor=spec['actor'],klass=spec['klass'],label=spec['label'],component=spec['component'],
            requiredTag=spec['requiredTag'],sourceMesh=spec['sourceMesh'],mesh=mesh.get_path_name(),
            sourceMeshSha256=spec['sourceMeshPackageSha256'],meshSha256=sha(package_file(ROOT,path)),
            actorTransform=spec['actorTransform'],worldVolumes=spec['worldVolumes'],localVolumeBounds=spec['localVolumeBounds'],
            sourceExport=dict(path=original_copy.relative_to(RUN).as_posix(),sha256=sha(original_copy)),
            clippedDocument=dict(path=document_file.relative_to(RUN).as_posix(),sha256=sha(document_file)),
            outsidePreservation=document['carveReceipt']['outsidePreservation'],nativeReadback=native_readback,
            nativeSourcePrefixPreserved=comparison['nativeSourcePrefixPreserved']))
    affected=({r['package'] for r in baseline['castleActors']}|{r['package'] for r in enclosure_edits}
        |{r['package'] for r in plan['lightingTreatment']['fixtures']}|{r['package'] for r in plan['terrainCarves']})
    copied_layers={};deleted=[];enclosure_changes=[];preservation=[];lighting_changes=[]
    for layer_index,authored in enumerate(city['sceneryLevels']):
        if authored not in affected:continue
        copied=DEST+'/Layers/RetainedCity_'+str(layer_index);copied_layers[authored]=copied
        if assets.does_asset_exist(copied) or not assets.duplicate_asset(authored,copied):raise RuntimeError('Cannot create fresh retained city copy')
        created(copied);load(copied)
        expected={r['actor']:r['state'] for r in baseline['actors'][authored]}
        before={a.get_name():snapshot(a) for a in own(copied)}
        if before!=expected:raise RuntimeError('Copy changed preserved scenery state')
        enclosure_by_actor={r['actor']:r for r in enclosure_edits if r['package']==authored}
        expected_after=dict(expected)
        for actor in own(copied):
            state=snapshot(actor);identity=castle_identity(state)
            edit=enclosure_by_actor.get(actor.get_name())
            if identity:
                old=removal_by_identity.get(identity)
                if not old or digest(state)!=old['stateHash']:raise RuntimeError('Unreviewed castle actor edit: '+identity)
                deleted.append(dict(package=authored,actor=actor.get_name(),identity=identity))
            elif edit:
                if digest(state)!=edit['stateHash']:raise RuntimeError('Upper enclosure changed after survey')
                if edit['mode']=='components':
                    for component in actor.get_components_by_class(unreal.StaticMeshComponent):
                        if component.get_name() not in edit['removeComponents']:continue
                        center,extent,_=unreal.SystemLibrary.get_component_bounds(component)
                        bounds=[[center.x-extent.x,center.y-extent.y,center.z-extent.z],
                                [center.x+extent.x,center.y+extent.y,center.z+extent.z]]
                        if not contains(plan['editMask']['upperBounds'],bounds):raise RuntimeError('Component extends outside the upper edit mask')
                        component.destroy_component(actor)
                    expected_after[actor.get_name()]={**state,'components':[c for c in state['components'] if c['name'] not in edit['removeComponents']]}
                    enclosure_changes.append(edit);continue
                if not contains(enclosure_edit_bounds(plan['editMask'],edit),edit['bounds']):raise RuntimeError('Actor extends outside its exact enclosure edit volume')
                enclosure_changes.append(edit)
            else:continue
            expected_after.pop(actor.get_name())
            if not actors.destroy_actor(actor):raise RuntimeError('Cannot remove surveyed copied citadel/enclosure actor')
        changes=apply_shared_lighting(copied,authored);lighting_changes.extend(changes)
        for change in changes:
            actor=next(a for a in own(copied) if a.get_name()==change['actor'])
            expected_after[change['actor']]=snapshot(actor)
        layer_carves=[]
        for spec in plan['terrainCarves']:
            if spec['package']!=authored:continue
            matches=[a for a in own(copied) if a.get_name()==spec['actor']]
            if len(matches)!=1:raise RuntimeError('Exact copied mountain actor is unavailable')
            actor=matches[0];before=snapshot(actor)
            if digest(before)!=spec['sourceStateHash']:raise RuntimeError('Retained mountain state changed after actual export')
            components=[c for c in actor.get_components_by_class(unreal.StaticMeshComponent) if c.get_name()==spec['component']]
            if len(components)!=1 or components[0].static_mesh.get_path_name()!=spec['sourceMesh']:
                raise RuntimeError('Exact retained mountain component or original mesh changed')
            mesh,carve_row=carved_meshes[spec['id']];components[0].set_static_mesh(mesh)
            expected_state=copy.deepcopy(before)
            target=next(c for c in expected_state['components'] if c['name']==spec['component'])
            target['mesh']=mesh.get_path_name();after_state=snapshot(actor)
            if after_state!=expected_state:raise RuntimeError('Terrain replacement changed another actor/component property')
            expected_after[spec['actor']]=after_state
            terrain_changes.append(dict(**carve_row,package=copied,actualTags=after_state['tags'],
                sourceActorState=before,actualActorState=after_state,
                sourceActorStateHash=digest(before),actualActorStateHash=digest(after_state)))
            layer_carves.append(spec['id'])
        after={a.get_name():snapshot(a) for a in own(copied)}
        if after!=expected_after:raise RuntimeError('Outside-mask/lower-city actor or component state changed')
        preservation.append(dict(source=authored,candidate=copied,preservedActorCount=len(after),
                                 preservedStateSha256=digest(after),matchesExpected=True,
                                 explicitLightingChanges=[r['id'] for r in changes],explicitTerrainCarves=layer_carves))
        if not levels.save_current_level():raise RuntimeError('Cannot save isolated retained scenery')
    if len(deleted)!=2267:raise RuntimeError('Incomplete exact old-castle replacement')
    if len(enclosure_changes)!=len(enclosure_edits):raise RuntimeError('Incomplete bounded upper enclosure replacement')
    if len(lighting_changes)!=len(plan['lightingTreatment']['fixtures']):
        raise RuntimeError('Incomplete signed private shared-scene lighting treatment')
    if len(terrain_changes)!=len(plan['terrainCarves']):raise RuntimeError('Incomplete bounded private terrain carve')
    geometry=DEST+'/Layers/GothicCitadel'
    if assets.does_asset_exist(geometry) or not levels.new_level(geometry):raise RuntimeError('Cannot create private citadel scenery level')
    created(geometry)
    select_owned_level(geometry)
    for actor in own(geometry):
        if not unreal.WarCityDefinition.is_scenery_actor(actor):
            if actor.get_class().get_name()!='PlayerStart':raise RuntimeError('Unexpected gameplay template in fresh scenery')
            if not actors.destroy_actor(actor):raise RuntimeError('Cannot remove fresh scenery template start')
    for row in bindings:
        if row['gateLeaf']:continue
        actor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector())
        actor.set_actor_label('Bastion reference '+row['id'])
        actor.static_mesh_component.set_static_mesh(unreal.load_asset(row['mesh']))
        actor.static_mesh_component.set_collision_profile_name('BlockAll')
        actor.tags=['WarAegisCitadel','WarCapitalBuilding','WarWorldObject_aegis_reference_'+row['id'],
                    'WarModelSha256_'+row['sha256']]
    cloud=actors.spawn_actor_from_class(unreal.VolumetricCloud,unreal.Vector(*cloud_spec['pointCm']))
    if not cloud or cloud.get_name()!=cloud_spec['actor']:raise RuntimeError('Unknown fresh native cloud fixture identity')
    cloud.set_actor_label(cloud_spec['label']);cloud.tags=[cloud_spec['requiredTag']]
    components=cloud.get_components_by_class(unreal.VolumetricCloudComponent)
    if len(components)!=1:raise RuntimeError('Native cloud component is unavailable')
    component=components[0];parent=unreal.load_asset(cloud_spec['material']['path'])
    if not isinstance(parent,unreal.MaterialInstanceConstant):raise RuntimeError('Reviewed original Engine cloud material is unavailable')
    instance=cloud_spec['materialInstance'];material_path=DEST+'/Materials/'+instance['name']
    if instance['name']!='MI_Cloud' or instance['parent']!=parent.get_path_name() or assets.does_asset_exist(material_path):
        raise RuntimeError('Unknown or independently owned cloud instance')
    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(instance['name'],DEST+'/Materials',
        unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    if not material:raise RuntimeError('Owned cloud material creation failed')
    created(material_path);lib=unreal.MaterialEditingLibrary
    lib.set_material_instance_parent(material,parent)
    if material.get_editor_property('parent').get_path_name()!=instance['parent']:
        raise RuntimeError('Owned cloud material lost its original Engine parent')
    scalar_names=sorted(str(n) for n in lib.get_scalar_parameter_names(material))
    vector_names=sorted(str(n) for n in lib.get_vector_parameter_names(material))
    scalar_readback={};vector_readback={}
    for requested,names in ((instance['scalarParameters'],scalar_names),(instance['vectorParameters'],vector_names)):
        if len(names)>256 or len(names)!=len(set(names)) or not set(requested)<=set(names):
            raise RuntimeError('Cloud recipe contains an unregistered material parameter')
    # These UE5.8 setters return false even after writing the parameter. Exact
    # registered names and typed native readbacks establish success instead.
    for key,wanted in instance['scalarParameters'].items():
        lib.set_material_instance_scalar_parameter_value(material,key,wanted)
        scalar_readback[key]=lighting_readback(lib.get_material_instance_scalar_parameter_value(material,key),wanted)
    for key,wanted in instance['vectorParameters'].items():
        lib.set_material_instance_vector_parameter_value(material,key,
            unreal.LinearColor(r=wanted[0],g=wanted[1],b=wanted[2],a=wanted[3]))
        vector_readback[key]=lighting_readback(lib.get_material_instance_vector_parameter_value(material,key),
                                             dict(kind='linear_color',value=wanted))
    save(material)
    material_instance=dict(package=material_path,path=material.get_path_name(),sha256=sha(package_file(ROOT,material_path)),
        parent=instance['parent'],requestedScalarParameters=instance['scalarParameters'],actualScalarReadback=scalar_readback,
        requestedVectorParameters=instance['vectorParameters'],actualVectorReadback=vector_readback,
        registeredScalarParameters=scalar_names,registeredVectorParameters=vector_names)
    component.set_editor_property('material',material)
    cloud_actual={}
    for key,wanted in cloud_spec['properties'].items():
        component.set_editor_property(key,native_lighting_value(wanted))
        cloud_actual[key]=lighting_readback(component.get_editor_property(key),wanted)
    actual_material=component.get_editor_property('material').get_path_name()
    if actual_material!=material_instance['path']:raise RuntimeError('Native cloud material changed')
    location=cloud.get_actor_location();actual_point=[location.x,location.y,location.z]
    if actual_point!=cloud_spec['pointCm']:raise RuntimeError('Owned native cloud moved')
    cloud_placement=dict(id=cloud_spec['id'],package=geometry,actor=cloud.get_name(),klass=cloud_spec['klass'],
        label=cloud_spec['label'],component=cloud_spec['component'],requiredTag=cloud_spec['requiredTag'],
        actualTags=list(snapshot(cloud)['tags']),pointCm=cloud_spec['pointCm'],actualPointCm=actual_point,
        material=cloud_spec['material'],materialInstance=material_instance,
        actualMaterial=actual_material,requestedProperties=cloud_spec['properties'],
        actualPropertyReadback=cloud_actual,stateHash=digest(snapshot(cloud)))
    # Warm architectural braziers are authored lights, never substitute mesh props.
    practical_lights=[]
    for row in plan['architecturalLights']:
        light=actors.spawn_actor_from_class(unreal.PointLight,unreal.Vector(*row['pointCm']))
        light.set_actor_label('Bastion '+row['id']);light.tags=['WarAegisCitadel','WarCitadelLight_'+row['id']]
        component=light.point_light_component;component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_editor_property('intensity_units',unreal.LightUnits.CANDELAS)
        component.set_editor_property('intensity',row['intensityCd'])
        component.set_editor_property('attenuation_radius',row['attenuationRadiusCm'])
        component.set_editor_property('source_radius',row['sourceRadiusCm'])
        component.set_editor_property('use_temperature',True)
        component.set_editor_property('temperature',row['temperatureK'])
        component.set_editor_property('cast_shadows',row['castShadows'])
        requested=dict(mobility=dict(kind='enum',type='ComponentMobility',value='MOVABLE'),
            intensity_units=dict(kind='enum',type='LightUnits',value='CANDELAS'),
            intensity=row['intensityCd'],attenuation_radius=row['attenuationRadiusCm'],
            source_radius=row['sourceRadiusCm'],use_temperature=True,
            temperature=row['temperatureK'],cast_shadows=row['castShadows'])
        actual={key:lighting_readback(component.get_editor_property(key),wanted)
                for key,wanted in requested.items()}
        location=light.get_actor_location();point=[location.x,location.y,location.z]
        if any(abs(a-b)>.001 for a,b in zip(point,row['pointCm'])):
            raise RuntimeError('Authored practical light moved: '+row['id'])
        practical_lights.append(dict(id=row['id'],package=geometry,actor=light.get_name(),
            klass=light.get_class().get_name(),label=light.get_actor_label(),pointCm=row['pointCm'],
            actualPointCm=point,requestedProperties=requested,actualPropertyReadback=actual,
            stateHash=digest(snapshot(light))))
    validate_scenery(geometry)
    select_owned_level(geometry)
    if not levels.save_current_level():raise RuntimeError('Cannot save authored citadel scenery')
    # Use unchanged published scenery for all lower-city/population layers.
    scenery=[copied_layers.get(p,p) for p in city['sceneryLevels']]+[geometry]
    zone=dict(id='aegis_capital',origin=city['origin'],levels={f'scenery_{i}':p for i,p in enumerate(scenery)})
    def backup(file):
        import shutil
        target=RUN/'native-backup'/file.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copy2(file,target)
    definition=prepare_city(zone,DEST+'/City',backup,created,RUN,protected_sources=source_hashes)
    if definition['dependencyHashes'].get(cloud_spec['material']['package'])!=cloud_spec['material']['sha256']:
        raise RuntimeError('Shared city revision omitted its protected cloud parent')
    definition['revisionPayload']=canonical_city_payload(
        {p:definition['packageHashes'][p] for p in definition['sceneryLevels']},
        definition['dependencyHashes'],definition['origin'])
    preview=DEST+'/ReviewCandidate'
    if not levels.new_level(preview):raise RuntimeError('Cannot create isolated city review world')
    created(preview);world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for p in scenery:
        if not unreal.EditorLevelUtils.add_level_to_world(world,p,unreal.LevelStreamingAlwaysLoaded):raise RuntimeError('Cannot attach candidate scenery')
    # Adding a streaming level can make it current. Gameplay must be spawned and
    # saved only after selecting the persistent review world explicitly.
    select_owned_level(preview)
    start=actors.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(*REVIEW_START_CM))
    if start.get_outer().get_path_name().split('.')[0]!=preview:raise RuntimeError('Review start has incorrect level ownership')
    if not levels.save_current_level():raise RuntimeError('Cannot save review candidate')
    siege=DEST+'/SiegeCandidate'
    if not assets.duplicate_asset(baseline['sourceSiegeMap'],siege):raise RuntimeError('Cannot isolate complete existing siege gameplay')
    created(siege);world=load(siege)
    for level in list(unreal.EditorLevelUtils.get_levels(world)):
        p=level.get_outer().get_path_name().split('.')[0]
        if p!=siege and not unreal.EditorLevelUtils.remove_level_from_world(level):raise RuntimeError('Cannot detach old copied scenery')
    for p in scenery:
        if not unreal.EditorLevelUtils.add_level_to_world(world,p,unreal.LevelStreamingAlwaysLoaded):raise RuntimeError('Cannot attach shared candidate scenery')
    if not levels.set_current_level_by_name('SiegeCandidate'):raise RuntimeError('Cannot select gameplay overlay')
    removed_overlay_lights=[]
    for name in OVERLAY_LIGHT_FIXTURES:
        matches=[a for a in own(siege) if a.get_name()==name]
        if len(matches)!=1 or not expected_overlay_light(name,snapshot(matches[0])):
            raise RuntimeError('Unknown or edited copied overlay light fixture: '+name)
        actor=matches[0];removed_overlay_lights.append(dict(actor=actor.get_path_name(),stateHash=digest(snapshot(actor))))
        if not actors.destroy_actor(actor):raise RuntimeError('Cannot remove duplicate private overlay fixture light')
    field=next(a for a in own(siege) if isinstance(a,unreal.WarSiegeBattlefield))
    field.set_editor_property('definition_version',2)
    field.set_editor_property('city_definition',unreal.load_asset(definition['definition']))
    field.set_editor_property('reviewed_city_revision','')
    for key,value in [('objectives',plan['objectives']),('optional_objectives',plan['optionalObjectives']),('team_spawns',plan['teamSpawns'])]:
        field.set_editor_property(key,[unreal.Vector(*p) for p in value])
    for key in ('traversal_reviewed','lower_city_reviewed','equipped_roster_reviewed'):field.set_editor_property(key,False)
    for actor in list(field.get_editor_property('stage_gates')):
        if actor and not actors.destroy_actor(actor):raise RuntimeError('Cannot retire copied original blockade')
    gates=[]
    by_id={r['id']:r for r in bindings}
    for gate in plan['gates']:
        meshes=[unreal.load_asset(by_id['gate_'+gate['id']+'_'+str(i)]['mesh']) for i in range(len(gate['leaves']))]
        transforms=[unreal.Transform(location=unreal.Vector(*leaf['point'])) for leaf in gate['leaves']]
        actor=unreal.WarSiegeAuthoringLibrary.create_assembly(world,'Bastion '+gate['id']+' compound portcullis',meshes,transforms,True)
        if not actor:raise RuntimeError('Every stage crossing requires an actual authored gate')
        gates.append(actor)
    field.set_editor_property('stage_gates',gates)
    # Pure player captures target empty space. Winches occupy signed side pads;
    # optional props have clear targets and lower-city ammunition stays exact.
    gameplay_pads=[place_gameplay_pad(field,pad) for pad in plan['gameplayPads']]
    lower_ammunition=field.get_editor_property('war_effort_props')[0]
    if digest(snapshot(lower_ammunition))!=next(r['stateHash'] for r in gameplay_pads if r['preserved']):
        raise RuntimeError('Retained lower-city ammunition changed during pad placement')
    standards=list(field.get_editor_property('attacker_standards'))
    for index,p in enumerate(plan['objectives']+plan['optionalObjectives']):
        if index<len(standards) and standards[index]:standards[index].set_actor_location(unreal.Vector(p[0],p[1]+430,p[2]),False,True)
    # Old hall braziers/lighting must move with the redesigned hall, never float in its forecourt.
    hall_props=[a for a in own(siege) if 'WarSiegeHallLight' in [str(t) for t in a.tags]]
    hall_placements=[]
    for klass in (unreal.StaticMeshActor,unreal.PointLight):
        fixtures=sorted((a for a in hall_props if isinstance(a,klass)),key=lambda a:a.get_name())
        if len(fixtures)!=4:raise RuntimeError('Unknown copied hall decoration/light roster')
        for actor,point in zip(fixtures,plan['retainedHallFixturePads']):
            before=snapshot(actor)
            if isinstance(actor,unreal.PointLight):
                actor.set_actor_location(unreal.Vector(point[0],point[1],point[2]+220),False,True)
                actor.point_light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
            else:
                center,extent=actor.get_actor_bounds(False);radius=math.hypot(extent.x,extent.y);height=extent.z*2
                if not route_clearance(plan,point,radius,height):raise RuntimeError('Actual hall fixture overlaps signed route')
                location=actor.get_actor_location()
                actor.set_actor_location(unreal.Vector(location.x+point[0]-center.x,location.y+point[1]-center.y,
                    location.z+point[2]-(center.z-extent.z)),False,True)
            center,extent=actor.get_actor_bounds(False)
            actual_meshes=[component.static_mesh.get_path_name() for component in
                actor.get_components_by_class(unreal.StaticMeshComponent) if component.static_mesh]
            hall_placements.append(dict(actor=actor.get_path_name(),actorClass=actor.get_class().get_name(),
                pointCm=point,meshes=actual_meshes,
                boundsCm=[[center.x-extent.x,center.y-extent.y,center.z-extent.z],
                          [center.x+extent.x,center.y+extent.y,center.z+extent.z]],
                sourceStateHash=digest(before),actualStateHash=digest(snapshot(actor))))
    if not levels.save_current_level():raise RuntimeError('Cannot save isolated siege candidate')
    proof_start=checked_private_proof_start(world,siege,plan,actors,own(siege))
    if not levels.save_current_level():raise RuntimeError('Cannot save checked private proof start')
    # Calculate city identity after all scenery attachments/saves, then return to
    # the persistent overlay. This rejects a late child-level save with old hashes.
    for p in scenery:
        load(p);validate_scenery(p)
    definition=prepare_city(zone,DEST+'/City',backup,created,RUN,protected_sources=source_hashes)
    if definition['dependencyHashes'].get(cloud_spec['material']['package'])!=cloud_spec['material']['sha256']:
        raise RuntimeError('Final saved city revision omitted its protected cloud parent')
    definition['revisionPayload']=canonical_city_payload(
        {p:definition['packageHashes'][p] for p in definition['sceneryLevels']},
        definition['dependencyHashes'],definition['origin'])
    world=load(siege);select_owned_level(siege)
    field=next(a for a in own(siege) if isinstance(a,unreal.WarSiegeBattlefield))
    field.set_editor_property('city_definition',unreal.load_asset(definition['definition']))
    field.set_editor_property('reviewed_city_revision','')
    if not levels.save_current_level():raise RuntimeError('Cannot save final private city binding')
    wing_ground_readback=replay_wing_ground(world,geometry)
    for p,h in baseline['packageHashes'].items():
        if sha(package_file(ROOT,p))!=h:raise RuntimeError('A published source changed during staging')
    if sha(cloud_material_file())!=cloud_spec['material']['sha256']:
        raise RuntimeError('The original Engine cloud material changed during private staging')
    packages=list(dict.fromkeys([*copied_layers.values(),geometry,definition['definition'],preview,siege,
                                *json.loads(pending.read_text())['created']]))
    result=dict(schemaVersion=1,revision=plan['revision'],signature=plan['signature'],geometrySignature=source['geometrySignature'],
        map=preview,siegeMap=siege,city=definition,sceneryLevels=scenery,retainedGameplayLevels=city['gameplayLevels'],
        bindings=bindings,removedActors=deleted,upperEnclosureChanges=enclosure_changes,outsideMaskPreservation=preservation,
        removedOverlayLightFixtures=removed_overlay_lights,retainedHallFixturePlacements=hall_placements,
        sharedLightingChanges=lighting_changes,exposureUsesExtendedEV100=exposure_extended,
        exposureUnits=plan['lightingTreatment']['exposureUnits'],
        architecturalLightPlacements=practical_lights,nativeCloudPlacement=cloud_placement,terrainCarves=terrain_changes,
        wingGroundReadback=wing_ground_readback,
        stageRecipeSha256=sha(Path(__file__)),
        stageDependencySha256={name:sha(Path(__file__).with_name(name)) for name in
            ('citadel_stage_contract.py','aegis_citadel_lighting.py','aegis_citadel_terrain.py','aegis_citadel_terrain_readback.py','aegis_citadel_terrain_render_readback.py','citadel_route_surface_evidence.py','shared_city_authoring.py','shared_city_sources.py','citadel_spawn_surface.py','citadel_wing_support_evidence.py')},
        nativeImportConvention=NATIVE_IMPORT_CONVENTION,proofStart=proof_start,materialBindings=material_bindings,
        gameplayPadPlacements=gameplay_pads,
        resolvedBaselineBlockers=baseline['terrainIntrusions'],sourceHashes=source_hashes,
        packageHashes=world_hashes(packages),nativeImported=True,geometryApproved=False,
        traversalApproved=False,visualApproved=False,published=False)
    require_final_city_hashes(definition,result['packageHashes'],result['sourceHashes'])
    receipt.write_text(json.dumps(result,indent=2)+'\n');pending.unlink()
    unreal.log('WAR_CITADEL_CANDIDATE='+str(receipt))
