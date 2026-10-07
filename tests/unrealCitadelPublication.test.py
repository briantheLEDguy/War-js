from fixtures.citadelCapsulePolicy import capsule_collision_policy,capsule_kinematics_policy
"""Portable publication guards; no Editor or actual native Content is accessed."""
import copy
import hashlib
import importlib.util
import json
import math
import struct
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/unreal'))
spec = importlib.util.spec_from_file_location('citadel_publication', ROOT / 'scripts/unreal/publish-aegis-citadel.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def row(key, x=0, source='mesh:hash', template=None):
    result = dict(id=key, hidden=False, sourceIdentity=source, transform=[x, 0, 0, 0, 0, 0, 1, 1, 1, 1])
    if template:
        result['templateId'] = template
    return result


def document(base, current):
    return dict(schemaVersion=2, zoneId='aegis_capital', baseline=json.dumps({'objects': base}), objects=current)


def tangent_basis_fixture(vertices):
    f32=lambda value:struct.unpack('f',struct.pack('f',value))[0]
    return dict(version=1,diagnosticOnly=True,highPrecision=True,
        basisSource='actual_render_buffer_x_z_and_native_reconstructed_y',
        nearZeroComponentTolerance=f32(1e-4),orthogonalityAbsoluteNormalizedDotTolerance=f32(.02),
        invalidVertices=0,orthogonalVertices=vertices,badVertexSamples=[],badVertexSampleLimit=64,
        badVertexSamplesTruncated=False,sampleComponentPolicy='actual_buffer_values_nonfinite_as_null',
        axes={axis:dict(finite=vertices,nonFinite=0,nearZero=0,unit=vertices,nonUnit=0,
            unitSquaredTolerance=f32(.04 if axis=='y' else .02),minimumLength=1.,maximumLength=1.)
            for axis in ('x','y','z')},
        pairs={pair:dict(evaluated=vertices,skipped=0,orthogonal=vertices,nonOrthogonal=0,
            maximumAbsoluteNormalizedDot=0.) for pair in ('xy','xz','yz')})


def width_evidence(routes):
    clear_overlaps=lambda count:dict(queries=count,rawClear=count,separated=0,blocked=0,unresolved=0,
        rawBlockingHits=0,lastDisposition='raw_clear' if count else 'unused',contacts=[])
    setup = dict(version=4, laneFractions=[-1, -.5, 0, .5, 1], maxSpacingCm=100, movementSpacingCm=10,
                 placementOverlapPolicy='fresh_live_static_single_body_unit_zero_margin_full_capsule_planes_v1',gateOverlapAdmissionRemainsRaw=True,
    capsulePolicyCheckedEveryTick=True,capsulePolicyCheckedEveryPlacementQuery=True,capsuleCollisionPolicy=capsule_collision_policy(),capsuleKinematicsPolicy=capsule_kinematics_policy(),
                 edgeInsetCm=0, maxFloorDeviationCm=120, groundClearanceCm=2.4, minFloorDistanceCm=1.9,
                 maxFloorDistanceCm=2.4, capsuleRadiusCm=42, capsuleHalfHeightCm=96, maxStepHeightCm=45,
                 walkableFloorZ=0.7100000381469727, collisionChannel='ECC_Pawn', collisionProfile='Custom',
                 simpleCollision=True, movementMethod='ComputeGroundMovementDelta/ramp-resweep/StepUp-floor-handoff/FindFloor/AdjustFloorHeight')
    rows = []
    for route in routes:
        previous = {}
        for segment,(a,b) in enumerate(zip(route['points'], route['points'][1:])):
            dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy); intervals=math.ceil(length/100)
            for sample in range(intervals+1):
                for lane in setup['laneFractions']:
                    alpha=sample/intervals; offset=lane*(route['clearWidthCm']/2-42)
                    seed=[a[0]+dx*alpha-dy/length*offset,a[1]+dy*alpha+dx/length*offset,a[2]+(b[2]-a[2])*alpha]
                    before=previous.get(lane);previous[lane]=seed
                    movement_steps=math.ceil(math.dist(seed[:2],before[:2])/10) if before else 0
                    rows.append(dict(id=route['id'],segment=segment,sample=sample,lane=lane,alpha=alpha,
                        clearWidthCm=route['clearWidthCm'],lateralOffsetCm=offset,seed=seed,
                        center=[seed[0],seed[1],seed[2]+98.4],floorImpact=seed[:],floorZCm=seed[2],floorNormalZ=1,
                        floorDistanceCm=2.4,floor=True,placementClear=True,transitionClear=True,passed=True,
                        stepAttempted=False,stepSucceeded=False,movementSteps=movement_steps,
                        placementOverlapEvidence=clear_overlaps(2),movementOverlapEvidence=clear_overlaps(2+3*movement_steps if movement_steps else 0)))
    return dict(capsuleRadiusCm=42,capsuleHeightCm=192,routeWidthConfig=setup,routeWidthSamples=rows,
                routeWidthComplete=True,routeWidthPassed=True)


class PublicationTests(unittest.TestCase):
    def test_normal_conversion_is_versioned_and_bound_to_actual_saved_texture(self):
        file='public/assets/textures/aegis_citadel_interiors/citadel_normal.png'
        package='/Game/WorldRebuild/AegisCitadel_0123456789ab/Textures/T_citadel_normal_normal'
        source=dict(materialSpecs=dict(furniture=dict(normal=file,normalConvention='gltf_opengl_positive_y')),
            materialSources={file:'a'*64})
        city=dict(revision='0123456789ab',packageHashes={package:'b'*64},nativeNormalTextureBindings=[dict(
            source=file,sourceSha256='a'*64,sourceConvention='gltf_opengl_positive_y',package=package,sha256='b'*64,
            actualFlipGreenChannel=True,actualSrgb=False,actualCompression='TC_NORMALMAP')])
        publisher.normal_texture_binding_proof(dict(recipeVersion=10),source,{})
        publisher.normal_texture_binding_proof(dict(recipeVersion=11),source,city)
        for key,value in dict(actualFlipGreenChannel=False,actualSrgb=True,actualCompression='TC_DEFAULT',
                sourceConvention='unrecorded',sha256='c'*64,sourceSha256='c'*64,package='/Game/Other/T_normal').items():
            invalid=copy.deepcopy(city);invalid['nativeNormalTextureBindings'][0][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'normal'):
                publisher.normal_texture_binding_proof(dict(recipeVersion=11),source,invalid)
        invalid=copy.deepcopy(city);invalid['nativeNormalTextureBindings']*=2
        with self.assertRaisesRegex(ValueError,'normal'):publisher.normal_texture_binding_proof(dict(recipeVersion=11),source,invalid)

    def test_mesh_recipe_keeps_legacy_counts_and_requires_new_footing_binding(self):
        legacy = [dict(id='asset_'+str(i)) for i in range(38)]
        current = legacy + [dict(id='wing_foundation_repairs')]
        for version in (1, 6, 7, 8):
            self.assertEqual(len(publisher.versioned_mesh_bindings(dict(recipeVersion=version), legacy, legacy)), 38)
            with self.assertRaises(ValueError):
                publisher.versioned_mesh_bindings(dict(recipeVersion=version), current, current)
        self.assertEqual(len(publisher.versioned_mesh_bindings(dict(recipeVersion=9), current, current)), 39)
        dressing=[dict(id='dressing_'+key) for key in ('forehall','throne_hall','west_archive','east_treasury','west_terrace','east_terrace')]
        for version in (10, 11, 12):
            self.assertEqual(len(publisher.versioned_mesh_bindings(dict(recipeVersion=version),current+dressing,current+dressing)),45)
        for missing in dressing:
            wrong=current+[dict(id='wrong_room') if row==missing else row for row in dressing]
            for version in (10, 11, 12):
                with self.assertRaisesRegex(ValueError,'Furnishing groups'):
                    publisher.versioned_mesh_bindings(dict(recipeVersion=version),wrong,wrong)
        for rows, bindings in ((legacy, legacy), (current, legacy),
                (current, current[:-1]+[current[0]]),
                (current, current[:-1]+[dict(id='wrong_mesh')]),
                (legacy+[dict(id='wrong_mesh')], legacy+[dict(id='wrong_mesh')])):
            with self.subTest(rows=rows[-1], bindings=bindings[-1]), self.assertRaises(ValueError):
                publisher.versioned_mesh_bindings(dict(recipeVersion=9), rows, bindings)
        for version in (0, 13, True, '9', None, 9.5):
            with self.subTest(version=version), self.assertRaises(ValueError):
                publisher.versioned_mesh_bindings(dict(recipeVersion=version), current, current)

    def test_gm_rebase_preserves_reflected_runtime_visibility(self):
        from types import SimpleNamespace
        for value in (True, False):
            reads=[]
            actor=SimpleNamespace(get_editor_property=lambda key:(reads.append(key), value)[1])
            self.assertIs(publisher.native_actor_hidden(actor), value)
            self.assertEqual(reads, ['hidden'])
        for value in (0, 1, None, 'false'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                publisher.native_actor_hidden(SimpleNamespace(get_editor_property=lambda key:value))

    def test_frontend_copy_carries_only_verified_exact_source_ownership(self):
        from types import SimpleNamespace
        prefix='/Game/WorldRebuild/AegisCitadel_0123456789ab'
        def asset(path, klass='WarFrontendPresentationDefinition'):
            return SimpleNamespace(get_path_name=lambda:path,
                get_class=lambda:SimpleNamespace(get_name=lambda:klass))
        source=asset(publisher.FRONTEND+'.CapitalPresentation')
        target=asset(prefix+'/CapitalPresentationCandidate.CapitalPresentationCandidate')
        tags={source.get_path_name():'cinematic-frontend-v1',target.get_path_name():''}
        writes=[]
        def set_tag(value,key,owner):
            writes.append((value.get_path_name(),key,owner));tags[value.get_path_name()]=owner
        assets=SimpleNamespace(get_metadata_tag=lambda a,k:tags.get(a.get_path_name(),''),set_metadata_tag=set_tag)
        receipt=publisher.bind_frontend_candidate_owner(assets,source,target,prefix)
        self.assertEqual(receipt['owner'],'cinematic-frontend-v1')
        self.assertEqual(writes,[(target.get_path_name(),'WarFrontendOwner','cinematic-frontend-v1')])
        for which in ('source_owner','source_path','source_class','target_owner','target_path','target_class','prefix'):
            tags[source.get_path_name()]='cinematic-frontend-v1';tags[target.get_path_name()]='';writes.clear()
            bad_source,bad_target,bad_prefix=source,target,prefix
            if which=='source_owner':tags[source.get_path_name()]=''
            if which=='source_path':bad_source=asset('/Game/Other.CapitalPresentation')
            if which=='source_class':bad_source=asset(source.get_path_name(),'OtherDefinition')
            if which=='target_owner':tags[target.get_path_name()]='another-owner'
            if which=='target_path':bad_target=asset('/Game/Other.CapitalPresentationCandidate')
            if which=='target_class':bad_target=asset(target.get_path_name(),'OtherDefinition')
            if which=='prefix':bad_prefix='/Game/WorldRebuild/Other'
            with self.subTest(which=which),self.assertRaises(ValueError):
                publisher.bind_frontend_candidate_owner(assets,bad_source,bad_target,bad_prefix)
            self.assertEqual(writes,[])

    def test_campaign_bounds_use_reflected_properties_and_preserve_xy_zone_rules(self):
        from types import SimpleNamespace

        class ReflectedAnchor:
            def __init__(self, extent=500):
                self.properties = dict(zone_origin=SimpleNamespace(x=1000, y=-2000, z=3000), half_size=extent)

            def get_editor_property(self, name):
                return self.properties[name]

        anchor = ReflectedAnchor()
        self.assertTrue(publisher.native_anchor_contains(anchor, [500, -2500, -9000]))
        self.assertTrue(publisher.native_anchor_contains(anchor, [1500, -1500, 12000]))
        self.assertFalse(publisher.native_anchor_contains(anchor, [1501, -2000, 3000]))
        self.assertFalse(publisher.native_anchor_contains(anchor, [1000, -1499, 3000]))
        for extent in (0, -1, True, float('nan')):
            with self.subTest(extent=extent), self.assertRaises(ValueError):
                publisher.native_anchor_contains(ReflectedAnchor(extent), [1000, -2000, 3000])

    def test_spawn_pad_and_approach_publication_evidence_cannot_be_omitted(self):
        from aegis_citadel_blueprint import plan as blueprint
        plan = blueprint()
        approaches = publisher.spawn_approach_routes(plan)
        self.assertEqual([row['id'] for row in approaches],
                         ['spawn_2_approach', 'spawn_3_approach', 'spawn_4_approach'])
        from citadel_spawn_surface import seed
        config = dict(spawnPads=[dict(index=row['index'], point=row['points'][0], widthCm=row['widthCm'],
                                     groundGradient=row['groundGradient'])
                                for row in plan['spawnApproaches']])
        report = dict(capsuleRadiusCm=42, spawnSamples=[])
        for pad in config['spawnPads']:
            for x in range(-2, 3):
                for y in range(-2, 3):
                    edge = pad['widthCm']/2-42
                    report['spawnSamples'].append(dict(index=pad['index'], x=x, y=y, clear=True,
                        seed=seed(pad['point'],x,y,edge,pad['groundGradient'])))
        publisher.spawn_pad_proof(report, config, plan)
        for mutation in ('missing', 'duplicate', 'blocked', 'moved', 'flattened'):
            bad = copy.deepcopy(report)
            if mutation == 'missing': bad['spawnSamples'].pop()
            if mutation == 'duplicate': bad['spawnSamples'][-1] = copy.deepcopy(bad['spawnSamples'][-2])
            if mutation == 'blocked': bad['spawnSamples'][0]['clear'] = False
            if mutation == 'moved': bad['spawnSamples'][0]['seed'][0] += 1
            if mutation == 'flattened': bad['spawnSamples'][0]['seed'][2] = plan['teamSpawns'][0][2]
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'spawn pad'):
                publisher.spawn_pad_proof(bad, config, plan)
        with self.assertRaisesRegex(ValueError, 'configuration'):
            publisher.spawn_pad_proof(report, {}, plan)
        missing = copy.deepcopy(plan); missing.pop('spawnApproaches')
        with self.assertRaisesRegex(ValueError, 'Every retained spawn'):
            publisher.spawn_approach_routes(missing)
        unconnected = copy.deepcopy(plan); unconnected['spawnApproaches'][2]['points'][-1][1] += 1
        with self.assertRaisesRegex(ValueError, 'declared playable route'):
            publisher.spawn_approach_routes(unconnected)

    def test_gate_publication_uses_the_exact_signed_landing_and_native_clearance(self):
        from aegis_citadel_blueprint import plan as blueprint
        plan = blueprint()
        gate = plan['gates'][0]
        leaf = next(row for row in gate['leaves'] if row.get('approachClearance'))
        config = publisher.gate_config(gate, gate['leaves'].index(leaf), leaf, plan['routes'])
        self.assertEqual(config['sweepHalfSpanCm'], leaf['approachClearance']['localSweepHalfSpanCm'])
        row = dict(actualLeafHalfThicknessCm=20, sweepHalfSpanCm=config['sweepHalfSpanCm'], startClear=True, endClear=True)
        self.assertTrue(publisher.gate_sweep_clearance(row, config, 42))
        for key, value in (('startClear', False), ('endClear', False), ('actualLeafHalfThicknessCm', 500),
                           ('sweepHalfSpanCm', 400), ('sweepHalfSpanCm', float('nan'))):
            bad = {**row, key:value}
            self.assertFalse(publisher.gate_sweep_clearance(bad, config, 42))
        changed = copy.deepcopy(leaf); changed['approachClearance']['incomingFlatLengthCm'] += 1
        with self.assertRaisesRegex(ValueError, 'signed flat landing'):
            publisher.gate_config(gate, 0, changed, plan['routes'])

    def test_engine_cloud_parent_is_protected_source_never_owned_candidate_content(self):
        # Injected package bytes exercise guards, not actual Unreal acceptance.
        from shared_city_sources import REVIEWED_ENGINE_SOURCE, package_file, protected_source_file
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);engine=root/'portable-engine';file=engine/'Engine/Content'/ (REVIEWED_ENGINE_SOURCE[8:]+'.uasset')
            file.parent.mkdir(parents=True);file.write_bytes(b'PORTABLE CLOUD PARENT ONLY')
            sha=hashlib.sha256(file.read_bytes()).hexdigest();hashes={REVIEWED_ENGINE_SOURCE:sha}
            publisher.verify_hashes(root,hashes,protected_sources=True,engine_root=engine)
            self.assertEqual(protected_source_file(root,REVIEWED_ENGINE_SOURCE,sha,engine),file)
            with self.assertRaisesRegex(ValueError,'ownership'):publisher.verify_hashes(root,hashes,engine_root=engine)
            with self.assertRaisesRegex(ValueError,'Invalid city package'):package_file(root,REVIEWED_ENGINE_SOURCE)
            with self.assertRaisesRegex(ValueError,'Unreviewed'):protected_source_file(root,'/Engine/Other',sha,engine)
            with self.assertRaisesRegex(ValueError,'unreviewed'):publisher.verify_hashes(root,{'/Engine/Other':sha},protected_sources=True,engine_root=engine)
            file.write_bytes(b'TAMPERED PORTABLE PARENT')
            with self.assertRaisesRegex(ValueError,'changed'):publisher.verify_hashes(root,hashes,protected_sources=True,engine_root=engine)
            file.with_suffix('.umap').write_bytes(b'AMBIGUOUS PORTABLE PACKAGE')
            with self.assertRaisesRegex(ValueError,'ambiguous'):protected_source_file(root,REVIEWED_ENGINE_SOURCE,sha,engine)

    def test_exact_five_lighting_exceptions_require_source_identity_actual_readbacks_and_preservation(self):
        from aegis_citadel_blueprint import LIGHTING_FIXTURES_V1 as LIGHTING_FIXTURES
        digest=lambda value:hashlib.sha256(value.encode()).hexdigest()
        source='/Game/PortableLightingSource';copied='/Game/WorldRebuild/AegisCitadel_0123456789ab/Layers/RetainedCity_0'
        fixtures=[dict(copy.deepcopy(s),package=source,sourceStateHash=digest('portable source '+s['actor'])) for s in LIGHTING_FIXTURES]
        def actual(value):
            return value['type']+'.'+value['value'] if isinstance(value,dict) and value['kind']=='enum' else value['value'] if isinstance(value,dict) else value
        changes=[dict(actor=s['actor'],sourcePackage=source,package=copied,sourceStateHash=s['sourceStateHash'],
            actualStateHash=digest('portable changed '+s['actor']),requestedProperties=copy.deepcopy(s['properties']),
            actualPropertyReadback={**{k:actual(v) for k,v in s['properties'].items()},
                **({'rotationDegrees':s['rotationDegrees']} if 'rotationDegrees' in s else {})}) for s in fixtures]
        plan=dict(lightingTreatment=dict(schemaVersion=1,fixtures=fixtures,exposureUnits='native_luminance',expectedExtendedEV100=False))
        city=dict(revision='0123456789ab',exposureUsesExtendedEV100=False,exposureUnits='native_luminance',sourceHashes={source:digest('source')},
            packageHashes={copied:digest('copied')},sceneryLevels=[copied],sharedLightingChanges=changes,
            outsideMaskPreservation=[dict(source=source,candidate=copied,matchesExpected=True,preservedActorCount=5,
                preservedStateSha256=digest('portable preservation'),explicitLightingChanges=[s['actor'] for s in fixtures])])
        with self.assertRaises(ValueError):publisher.lighting_proof(plan,city)
        publisher.lighting_proof(plan,city,historical=True)
        for mutate in (lambda c:c['sharedLightingChanges'][0].update(sourceStateHash='f'*64),
                lambda c:c['sharedLightingChanges'][0]['requestedProperties'].update(arbitrary_actor_property=True),
                lambda c:c['sharedLightingChanges'][0]['actualPropertyReadback'].update(intensity=1),
                lambda c:c['sharedLightingChanges'][1]['actualPropertyReadback'].update(light_color=[226,187,158,255]),
                lambda c:c['sharedLightingChanges'][2]['actualPropertyReadback'].update(light_color=[247,228,215,255]),
                lambda c:c['sharedLightingChanges'].append(dict(changes[0],actor='RetainedStreetLight')),
                lambda c:c['outsideMaskPreservation'][0]['explicitLightingChanges'].append('RetainedStreetLight'),
                lambda c:c.update(sceneryLevels=[]),lambda c:c.update(exposureUsesExtendedEV100=True),lambda c:c.update(exposureUnits='EV100')):
            changed=copy.deepcopy(city);mutate(changed)
            with self.assertRaises(ValueError):publisher.lighting_proof(plan,changed,historical=True)

    def test_fresh_seven_package_scoped_fixtures_and_owned_cloud_require_exact_readbacks(self):
        from aegis_citadel_lighting import FIXTURES,CLOUD_IDENTITY,REVIEWED_CLOUD_MATERIAL
        from aegis_citadel_blueprint import LIGHTING_REQUESTS
        digest=lambda value:hashlib.sha256(value.encode()).hexdigest()
        source_prefix='/Game/WorldRebuild/DutchBastion_d105951f4aab/Layers/'
        candidate_prefix='/Game/WorldRebuild/AegisCitadel_0123456789ab/Layers/'
        sources={source_prefix+name:digest('portable source '+name) for name in ('authored','Bastion_Dutch_Geometry')}
        sources[REVIEWED_CLOUD_MATERIAL]=digest('portable cloud material')
        owned={candidate_prefix+name:digest('portable copied '+name) for name in ('RetainedCity_0','RetainedCity_1','GothicCitadel')}
        requests={row['id']:copy.deepcopy(row) for row in LIGHTING_REQUESTS}
        requests['sun']['rotationDegrees']=[-20,30,0]
        requests['ambient_sky']['properties']['intensity']=.35
        fixtures=[];changes=[]
        def actual(value):return value['type']+'.'+value['value'] if isinstance(value,dict) and value['kind']=='enum' else value['value'] if isinstance(value,dict) else value
        for fixture_id,actor,klass,label,component,layer,tag in FIXTURES:
            request=requests[fixture_id]
            spec=dict(id=fixture_id,actor=actor,klass=klass,label=label,component=component,requiredTag=tag,
                package=source_prefix+layer,sourcePackageSha256=sources[source_prefix+layer],
                sourceStateHash=digest('portable source state '+fixture_id),**{k:copy.deepcopy(v) for k,v in request.items() if k!='id'})
            fixtures.append(spec)
            changes.append(dict(id=fixture_id,actor=actor,klass=klass,label=label,component=component,requiredTag=tag,
                sourcePackage=spec['package'],sourcePackageSha256=spec['sourcePackageSha256'],
                package=candidate_prefix+('RetainedCity_1' if fixture_id=='dutch_street_fill' else 'RetainedCity_0'),
                sourceStateHash=spec['sourceStateHash'],actualStateHash=digest('portable actual state '+fixture_id),
                actualTags=[tag]+(['WarCapitalWorkbench'] if fixture_id in ('sun','ambient_sky','exposure','atmosphere') else ['WarDutchBastion'] if fixture_id=='dutch_street_fill' else []),
                requestedProperties=copy.deepcopy(spec['properties']),actualPropertyReadback={**{k:actual(v) for k,v in spec['properties'].items()},
                    **({'rotationDegrees':spec['rotationDegrees']} if 'rotationDegrees' in spec else {})}))
        cloud_properties=dict(layer_bottom_altitude=.5,layer_height=1.2,view_sample_count_scale=2,shadow_view_sample_count_scale=2)
        scalars=dict(Layout_CloudGlobalScale=8,Cloud_GlobalCoverage=.25,Cloud_GlobalDensity=.008,StormClouds=.65)
        vectors=dict(Cloud_AlbedoColor=[.65,.70,.78,.5],Storm_LightningColor=[0,0,0,0],Layout_CloudTypeMask=[0,0,1,0])
        parent=REVIEWED_CLOUD_MATERIAL+'.m_SimpleVolumetricCloud_Inst'
        cloud=dict(**CLOUD_IDENTITY,pointCm=[0,0,0],material=dict(package=REVIEWED_CLOUD_MATERIAL,
            path=parent,sha256=sources[REVIEWED_CLOUD_MATERIAL]),properties=copy.deepcopy(cloud_properties),
            materialInstance=dict(name='MI_Cloud',parent=parent,scalarParameters=copy.deepcopy(scalars),vectorParameters=copy.deepcopy(vectors)))
        instance_package='/Game/WorldRebuild/AegisCitadel_0123456789ab/Materials/MI_Cloud'
        owned[instance_package]=digest('portable owned cloud MIC')
        instance=dict(package=instance_package,path=instance_package+'.MI_Cloud',sha256=owned[instance_package],parent=parent,
            requestedScalarParameters=copy.deepcopy(scalars),actualScalarReadback=copy.deepcopy(scalars),
            requestedVectorParameters=copy.deepcopy(vectors),actualVectorReadback=copy.deepcopy(vectors),
            registeredScalarParameters=list(scalars),registeredVectorParameters=list(vectors))
        placement=dict(**cloud,package=candidate_prefix+'GothicCitadel',actualTags=['WarAegisCitadel',cloud['requiredTag']],
            actualPointCm=[0,0,0],actualMaterial=instance['path'],requestedProperties=copy.deepcopy(cloud_properties),
            actualPropertyReadback=copy.deepcopy(cloud_properties),stateHash=digest('portable cloud state'))
        placement['materialInstance']=instance
        plan=dict(lightingTreatment=dict(schemaVersion=2,fixtures=fixtures,cloudFixture=cloud,exposureUnits='native_luminance',
            expectedExtendedEV100=False,existingAtmospherePreserved=False))
        city=dict(revision='0123456789ab',exposureUsesExtendedEV100=False,exposureUnits='native_luminance',
            sourceHashes=sources,packageHashes=owned,sceneryLevels=[name for name in owned if '/Layers/' in name],sharedLightingChanges=changes,nativeCloudPlacement=placement,
            outsideMaskPreservation=[dict(source=source_prefix+layer,candidate=candidate_prefix+'RetainedCity_'+str(index),
                matchesExpected=True,preservedActorCount=6 if index==0 else 1,preservedStateSha256=digest('portable preserved '+layer),
                explicitLightingChanges=[row['id'] for row in changes if row['sourcePackage']==source_prefix+layer])
                for index,layer in enumerate(('authored','Bastion_Dutch_Geometry'))])
        publisher.lighting_proof(plan,city)
        for mutate in (
            lambda c:c['sharedLightingChanges'][6].update(sourcePackage=source_prefix+'authored'),
            lambda c:c['sharedLightingChanges'][6].update(id='sun'),
            lambda c:c['sharedLightingChanges'][0].update(sourcePackageSha256='f'*64),
            lambda c:c['sharedLightingChanges'][0].update(actualTags=[]),
            lambda c:c['sharedLightingChanges'][6]['actualPropertyReadback'].update(light_color=[218,192,173,255]),
            lambda c:c['sharedLightingChanges'][5]['actualPropertyReadback'].update(rayleigh_scattering_scale=.175866),
            lambda c:c['sharedLightingChanges'][0]['actualPropertyReadback'].update(unlisted_field=True),
            lambda c:c['outsideMaskPreservation'][0]['explicitLightingChanges'].append('DirectionalLight_0'),
            lambda c:c['nativeCloudPlacement'].update(actualMaterial='/Engine/Other.Other'),
            lambda c:c['nativeCloudPlacement'].update(actualMaterial=parent),
            lambda c:c['nativeCloudPlacement']['materialInstance'].update(sha256='f'*64),
            lambda c:c['nativeCloudPlacement']['materialInstance'].update(parent='/Engine/Other.Other'),
            lambda c:c['nativeCloudPlacement']['materialInstance']['actualScalarReadback'].update(Cloud_GlobalDensity=.08),
            lambda c:c['nativeCloudPlacement']['materialInstance']['actualVectorReadback'].update(Cloud_AlbedoColor=[.78,.7,.65,.5]),
            lambda c:c['nativeCloudPlacement']['materialInstance']['actualVectorReadback'].update(Storm_LightningColor=[0,0,0,None]),
            lambda c:c['nativeCloudPlacement']['materialInstance']['registeredScalarParameters'].remove('StormClouds'),
            lambda c:c['nativeCloudPlacement']['materialInstance'].update(setterSucceeded=True),
            lambda c:c['nativeCloudPlacement'].pop('materialInstance'),
            lambda c:c['nativeCloudPlacement'].update(package=candidate_prefix+'RetainedCity_0'),
            lambda c:c['nativeCloudPlacement']['actualPropertyReadback'].update(layer_height=2),
            lambda c:c['nativeCloudPlacement']['actualPropertyReadback'].update(view_sample_count_scale=1),
            lambda c:c['nativeCloudPlacement']['actualPropertyReadback'].pop('shadow_view_sample_count_scale'),
            lambda c:c['nativeCloudPlacement']['materialInstance']['actualVectorReadback'].update(Layout_CloudTypeMask=[0,1,0,0]),
            lambda c:c['nativeCloudPlacement']['actualPropertyReadback'].update(unlisted_field=True),
            lambda c:c['sourceHashes'].update({REVIEWED_CLOUD_MATERIAL:'f'*64}),
            lambda c:c.pop('nativeCloudPlacement'),
        ):
            altered=copy.deepcopy(city);mutate(altered)
            with self.assertRaises(ValueError):publisher.lighting_proof(plan,altered)

    def test_rebase_retains_disjoint_owner_edits_and_additions_while_removing_untouched_castle(self):
        base = [row('lower_house'), row('old_castle')]
        proposed = [row('lower_house'), row('new_citadel', source='new:hash')]
        current = [row('lower_house', 125), row('old_castle'), row('owner_addition', 300, template='lower_house')]
        old = document(base, current)
        original = copy.deepcopy(old)
        result = publisher.rebase_draft(old, proposed)
        self.assertEqual(old, original)
        self.assertEqual([r['id'] for r in result['objects']], ['lower_house', 'new_citadel', 'owner_addition'])
        self.assertEqual(result['objects'][0]['transform'][0], 125)
        self.assertEqual(json.loads(result['baseline'])['objects'], proposed)

    def test_removed_owner_edit_changed_template_and_invalid_transform_fail_closed(self):
        base = [row('lower_house'), row('old_castle')]
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            publisher.rebase_draft(document(base, [row('lower_house'), row('old_castle', 200)]), [row('lower_house')])
        with self.assertRaisesRegex(ValueError, 'template'):
            publisher.rebase_draft(document(base, [*base, row('addition', template='old_castle')]), [row('lower_house')])
        invalid = row('lower_house'); invalid['transform'][0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            publisher.rebase_draft(document(base, [invalid, row('old_castle')]), base)

    def test_manifest_reconciliation_keeps_unrelated_review_changes_and_rejects_competing_routes(self):
        base = dict(map='old', review={'native': False}, portals=['both_connections'])
        proposed = dict(map='new', review={'native': False}, portals=['both_connections'])
        live = dict(map='old', review={'native': True}, portals=['both_connections'])
        self.assertEqual(publisher.merge_manifest(base, proposed, live), dict(map='new', review={'native': True}, portals=['both_connections']))
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            publisher.merge_manifest(base, proposed, {**live, 'map': 'other'})

    def test_native_prop_bounds_preserve_ammunition_and_cannot_obstruct_capture_or_routes(self):
        point = [20100, -3900, 4210]
        plan = dict(gameplayPads=[
            dict(id='lower_ammunition', binding='war_effort_props', index=0, preserveTransform=True),
            dict(id='west_gate_mechanism', binding='gate_mechanisms', index=0,
                 footprintCentreFloorCm=point, maximumFootprintRadiusCm=340, maximumHeightCm=400,
                 captureClearRadiusCm=650, minimumCaptureGapCm=50)],
            routes=[dict(width=600, points=[[0, 0, 4210], [1000, 0, 4210]])],
            objectives=[[20800, -5000, 4210] for _ in range(8)],
            optionalObjectives=[[22000, -4600, 4210] for _ in range(3)])
        city = dict(siegeMap='/Game/Candidate', gameplayPadPlacements=[
            dict(id='lower_ammunition', actor='/Game/Candidate.Candidate:PersistentLevel.Ammo',
                 preserved=True, stateHash='a'*64),
            dict(id='west_gate_mechanism', actor='/Game/Candidate.Candidate:PersistentLevel.Winch',
                 preserved=False, footprintCentreFloorCm=point, footprintRadiusCm=math.hypot(200, 100),
                 heightCm=300, boundsCm=[[19900, -4000, 4210], [20300, -3800, 4510]],
                 sourceStateHash='b'*64, actualStateHash='c'*64)])
        publisher.gameplay_pad_proof(plan, city)
        capture = copy.deepcopy(plan); capture['objectives'][4] = [20300, -3900, 4210]
        with self.assertRaisesRegex(ValueError, 'player objective'):
            publisher.gameplay_pad_proof(capture, city)
        corridor = copy.deepcopy(plan)
        corridor['routes'][0]['points'] = [[19000, -3900, 4210], [22000, -3900, 4210]]
        with self.assertRaisesRegex(ValueError, 'obstruct'):
            publisher.gameplay_pad_proof(corridor, city)
        altered = copy.deepcopy(city); altered['gameplayPadPlacements'][1]['boundsCm'][0][0] -= 400
        with self.assertRaisesRegex(ValueError, 'bounds'):
            publisher.gameplay_pad_proof(plan, altered)
        stale = copy.deepcopy(city); stale['gameplayPadPlacements'][1]['actor'] = '/Game/Old.Old:PersistentLevel.Winch'
        with self.assertRaisesRegex(ValueError, 'another native candidate'):
            publisher.gameplay_pad_proof(plan, stale)
        missing = copy.deepcopy(city); missing['gameplayPadPlacements'].pop()
        with self.assertRaisesRegex(ValueError, 'Complete actual native'):
            publisher.gameplay_pad_proof(plan, missing)
        duplicated = copy.deepcopy(city); duplicated['gameplayPadPlacements'][1]['id'] = 'lower_ammunition'
        with self.assertRaisesRegex(ValueError, 'identity'):
            publisher.gameplay_pad_proof(plan, duplicated)
        retained = copy.deepcopy(city); retained['gameplayPadPlacements'][0]['stateHash'] = None
        with self.assertRaisesRegex(ValueError, 'exact native state hash'):
            publisher.gameplay_pad_proof(plan, retained)

    def test_missing_stale_or_incomplete_native_acceptance_cannot_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); run = root / 'run'; run.mkdir()
            package = '/Game/WorldRebuild/AegisCitadel_0123456789ab/SiegeCandidate'
            file = root / 'unreal/AegisWar/Content/WorldRebuild/AegisCitadel_0123456789ab/SiegeCandidate.umap'
            file.parent.mkdir(parents=True); file.write_bytes(b'fixture package only')
            hashes = {package: publisher.digest(file)}
            plan = dict(revision='0123456789ab', signature='a'*64, reference={'sha256': 'b'*64})
            city = dict(packageHashes=hashes, city={'revision': 'c'*64})
            staged = dict(packageHashes=hashes)
            review = dict(schemaVersion=1, revision=plan['revision'], signature=plan['signature'], cityRevision='c'*64,
                          packageHashes=hashes, unfinished=[], visual={'reviewed': False})
            publisher.write(run / 'publication-review.json', review)
            with self.assertRaisesRegex(ValueError, 'explicit evidence'):
                publisher.publication_review(root, run, plan, city, staged)
            file.write_bytes(b'changed native package')
            with self.assertRaisesRegex(ValueError, 'changed native package'):
                publisher.publication_review(root, run, plan, city, staged)

    def test_scenery_saved_after_city_definition_cannot_use_the_old_nested_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); run = root / 'run'; run.mkdir()
            prefix = '/Game/WorldRebuild/AegisCitadel_0123456789ab'
            hashes = {}
            for package in (prefix+'/City', prefix+'/Layers/GothicCitadel', '/Game/CanonicalSource', '/Game/ModelDependency'):
                file = root / ('unreal/AegisWar/Content/'+package[6:]+'.uasset')
                file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(package.encode())
                hashes[package] = publisher.digest(file)
            stage = root / 'scripts/unreal/stage-aegis-citadel.py'
            stage.parent.mkdir(parents=True); stage.write_text('fixture source recipe')
            dependency = stage.with_name('citadel_stage_contract.py'); dependency.write_text('fixture staging dependency')
            plan = dict(revision='0123456789ab', signature='a'*64, sourceRecipes={})
            source = dict(blueprintSignature=plan['signature'], geometrySignature='b'*64, assets=[])
            packages = {p: hashes[p] for p in (prefix+'/City', prefix+'/Layers/GothicCitadel')}
            city = dict(schemaVersion=1, revision=plan['revision'], signature=plan['signature'],
                        geometrySignature=source['geometrySignature'], nativeImported=True,
                        map=prefix+'/ReviewCandidate', siegeMap=prefix+'/SiegeCandidate',
                        sourceHashes={'/Game/CanonicalSource': hashes['/Game/CanonicalSource']},
                        packageHashes=packages, sceneryLevels=[prefix+'/Layers/GothicCitadel', '/Game/CanonicalSource'], retainedGameplayLevels=[],
                        stageRecipeSha256=publisher.digest(stage),
                        stageDependencySha256={'citadel_stage_contract.py': publisher.digest(dependency)},
                        city=dict(definition=prefix+'/City', origin=[0, 0, 0], sceneryLevels=[prefix+'/Layers/GothicCitadel', '/Game/CanonicalSource'],
                                  packageHashes={**packages, '/Game/CanonicalSource': hashes['/Game/CanonicalSource'], prefix+'/Layers/GothicCitadel': 'c'*64},
                                  dependencyHashes={'/Game/ModelDependency': hashes['/Game/ModelDependency']}))
            publisher.write(run/'blueprint.json', plan); publisher.write(run/'assets-source.json', source)
            publisher.write(run/'candidate.json', city)
            current = dict(id='aegis_capital', gameplayLevels=[], origin=[0, 0, 0])
            with mock.patch('aegis_citadel_blueprint.validate'), mock.patch.object(publisher, 'source_plan', return_value={'cities': [current]}), \
                    mock.patch.object(publisher, 'gameplay_pad_proof'), mock.patch.object(publisher, 'import_binding_proof'), \
                    mock.patch.object(publisher, 'lighting_proof'), mock.patch('citadel_terrain_evidence.require_terrain_carves'):
                with self.assertRaisesRegex(ValueError, 'binding hashes differ|Preserve changed native package'):
                    publisher.candidate(root, run)
                city['city']['packageHashes'] = {**packages, '/Game/CanonicalSource': hashes['/Game/CanonicalSource']}
                payload = dict(scenery={p:city['city']['packageHashes'][p] for p in city['sceneryLevels']},
                               dependencies=city['city']['dependencyHashes'], origin=[0.0, 0.0, 0.0])
                city['city']['revisionPayload'] = json.dumps(payload, sort_keys=True)
                city['city']['revision'] = hashlib.sha256(city['city']['revisionPayload'].encode()).hexdigest()
                publisher.write(run/'candidate.json', city)
                self.assertEqual(publisher.candidate(root, run)[1]['packageHashes'], packages)
                engine='/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst'
                plan['lightingTreatment']=dict(cloudFixture=dict(material=dict(package=engine,sha256='e'*64)))
                city['sourceHashes'][engine]='e'*64
                publisher.write(run/'blueprint.json',plan)
                for bound in (None,'f'*64):
                    if bound is None:city['city']['dependencyHashes'].pop(engine,None)
                    else:city['city']['dependencyHashes'][engine]=bound
                    publisher.write(run/'candidate.json',city)
                    with self.assertRaisesRegex(ValueError,'retain the signed protected cloud parent'):
                        publisher.candidate(root,run)
                plan.pop('lightingTreatment');city['sourceHashes'].pop(engine)
                city['city']['dependencyHashes'].pop(engine,None)
                publisher.write(run/'blueprint.json',plan);publisher.write(run/'candidate.json',city)
                dependency.write_text('independently changed stage dependency')
                with self.assertRaisesRegex(ValueError, 'staging dependency'):
                    publisher.candidate(root, run)
                dependency.write_text('fixture staging dependency')
                payload['scenery'][prefix+'/Layers/GothicCitadel'] = 'c'*64
                city['city']['revisionPayload'] = json.dumps(payload, sort_keys=True)
                city['city']['revision'] = hashlib.sha256(city['city']['revisionPayload'].encode()).hexdigest()
                publisher.write(run/'candidate.json', city)
                with self.assertRaisesRegex(ValueError, 'revision payload'):
                    publisher.candidate(root, run)

    def test_index_only_native_import_and_actual_private_spawn_bind_to_all_signed_sources(self):
        from citadel_stage_contract import NATIVE_IMPORT_CONVENTION,NATIVE_MESH_BUILD_SETTINGS,source_array_sha256
        compact = lambda value: hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            run=Path(directory); (run/'runtime').mkdir(); (run/'sources').mkdir()
            (run/'sources/fixture.blend').write_text('PORTABLE TEST SOURCE ONLY')
            plan=dict(revision='0123456789ab',signature='a'*64,teamSpawns=[[0,0,0] for _ in range(6)])
            source=dict(schemaVersion=1,revision=plan['revision'],blueprintSignature=plan['signature'],assets=[],
                        sourceMaster=dict(path='sources/fixture.blend',sha256=publisher.digest(run/'sources/fixture.blend')))
            prefix='/Game/WorldRebuild/AegisCitadel_'+plan['revision']
            city=dict(geometrySignature='',nativeImportConvention=copy.deepcopy(NATIVE_IMPORT_CONVENTION),bindings=[],packageHashes={},
                siegeMap=prefix+'/SiegeCandidate',proofStart=dict(actor=prefix+'/SiegeCandidate.SiegeCandidate:PersistentLevel.PlayerStart_0',
                    sourceTeamSpawnIndex=1,signedFloorCm=[0,0,0],locationCm=[0,0,99],actualFloorZCm=0,capsuleRadiusCm=42,
                    capsuleHalfHeightCm=96,traceChannel='Visibility',traceComplex=True,capsuleClear=True,otherStartsPreserved=0))
            material_package=prefix+'/Materials/M_blue';material_sha=hashlib.sha256(b'PORTABLE MATTE GRAPH ONLY').hexdigest()
            source['materialSpecs']=dict(blue=copy.deepcopy(publisher.MATTE_NAVY));city['packageHashes'][material_package]=material_sha
            actual=dict(copy.deepcopy(publisher.MATTE_NAVY),normalInputConnected=False,ambientOcclusionInputConnected=False)
            city['materialBindings']=[dict(role='blue',package=material_package,sha256=material_sha,
                sourceSpec=copy.deepcopy(publisher.MATTE_NAVY),actualConstantReadback=actual)]
            mesh=dict(positions=[[0,0,0],[1,0,0],[0,1,0]],normals=[[0,0,1] for _ in range(3)],uvs=[[0,0],[1,0],[0,1]],indices=[0,1,2])
            for i in range(38):
                key='asset_'+str(i);file=run/('runtime/'+key+'.json');publisher.write(file,mesh)
                package=prefix+'/Meshes/SM_'+key;package_sha=hashlib.sha256(key.encode()).hexdigest()
                source['assets'].append(dict(id=key,meshFile=file.relative_to(run).as_posix(),sha256=publisher.digest(file),triangles=1,gateLeaf=False))
                city['packageHashes'][package]=package_sha
                city['bindings'].append(dict(id=key,mesh=package,sha256=package_sha,gateLeaf=False,triangles=[1],
                    sourceIndicesSha256=compact([0,1,2]),nativeIndicesSha256=compact([0,2,1])))
                audit=dict(readOnly=True,available=True,mesh=package+'.SM_'+key,lods=[dict(lod=0,cpuReadable=True,
                    vertices=3,indices=3,uvChannels=2,invalidPositions=0,invalidNormals=0,nonUnitNormals=0,invalidUVs=0,
                    committedSourcePositionMissing=0,committedSourceNormalDifferent=0,committedSourceNormalMatches=3,
                    sourcePositionToleranceCm=.1,sourceNormalDotThreshold=.995,
                    sourceMatchingPolicy='oriented_triangle_corners_material_and_uv0',committedSourceTriangleMatches=1,
                    committedSourceTrianglesMissing=0,committedSourceTrianglesDifferent=0,
                    sourceUvAbsoluteTolerance=.0005,sourceUvRelativeTolerance=.001,tangentBasis=tangent_basis_fixture(3))])
                payload=json.dumps(audit)
                city['bindings'][-1].update(sourceArrayHashConvention='sha256_raw_utf8_mesh_json_member_array',
                    nativeMeshBuildSettings=copy.deepcopy(NATIVE_MESH_BUILD_SETTINGS),renderDataAudit=audit,
                    renderDataAuditPayload=payload,renderDataAuditSha256=hashlib.sha256(payload.encode()).hexdigest(),
                    **{'source'+title+'Sha256':source_array_sha256(file.read_text(),field)
                       for title,field in (('Positions','positions'),('Normals','normals'),('UVs','uvs'))})
            source['geometrySignature']=compact([(r['id'],r['sha256']) for r in source['assets']]);city['geometrySignature']=source['geometrySignature']
            publisher.import_binding_proof(run,plan,source,city)
            for field,value in (('uvChannels',0),('cpuReadable',False),('committedSourceNormalDifferent',1),('nonUnitNormals',1),
                                ('sourcePositionToleranceCm',1),('sourceNormalDotThreshold',.1),
                                ('sourceMatchingPolicy','position_only'),('committedSourceTriangleMatches',0),
                                ('committedSourceTrianglesMissing',1),('committedSourceTrianglesDifferent',1),
                                ('sourceUvAbsoluteTolerance',.1),('sourceUvRelativeTolerance',.1)):
                invalid=copy.deepcopy(city);binding=invalid['bindings'][0];binding['renderDataAudit']['lods'][0][field]=value
                binding['renderDataAuditPayload']=json.dumps(binding['renderDataAudit'])
                binding['renderDataAuditSha256']=hashlib.sha256(binding['renderDataAuditPayload'].encode()).hexdigest()
                with self.assertRaisesRegex(ValueError,'render|normal|source matching|triangle corners'):
                    publisher.import_binding_proof(run,plan,source,invalid)
            wrong=copy.deepcopy(city);wrong['bindings'][0]['nativeIndicesSha256']=compact([0,1,2])
            with self.assertRaisesRegex(ValueError,'index hashes'):
                publisher.import_binding_proof(run,plan,source,wrong)
            unsafe=copy.deepcopy(city);unsafe['proofStart']['capsuleClear']=False
            with self.assertRaisesRegex(ValueError,'proof start'):
                publisher.import_binding_proof(run,plan,source,unsafe)
            reversed_mesh=copy.deepcopy(mesh);reversed_mesh['indices']=[0,2,1]
            file=run/source['assets'][0]['meshFile'];publisher.write(file,reversed_mesh)
            source['assets'][0]['sha256']=publisher.digest(file)
            with self.assertRaisesRegex(ValueError,'outward normals'):
                publisher.import_binding_proof(run,plan,source,city)

    def test_matte_navy_requires_actual_graph_constants_and_disconnected_normal_ao(self):
        plan=dict(revision='0123456789ab');package='/Game/WorldRebuild/AegisCitadel_'+plan['revision']+'/Materials/M_blue'
        source=dict(materialSpecs=dict(blue=copy.deepcopy(publisher.MATTE_NAVY)));sha='a'*64
        row=dict(role='blue',package=package,sha256=sha,sourceSpec=copy.deepcopy(publisher.MATTE_NAVY),
                 actualConstantReadback=dict(copy.deepcopy(publisher.MATTE_NAVY),normalInputConnected=False,ambientOcclusionInputConnected=False))
        city=dict(materialBindings=[row],packageHashes={package:sha});publisher.material_binding_proof(plan,source,city)
        invalids=[]
        for key,value in (('normalInputConnected',True),('ambientOcclusionInputConnected',True),('roughness',.3),
                          ('specular',float('nan')),('tint',[.018,.075,.23])):
            invalid=copy.deepcopy(city);invalid['materialBindings'][0]['actualConstantReadback'][key]=value;invalids.append(invalid)
        invalid=copy.deepcopy(city);invalid['materialBindings'][0]['sourceSpec']['normal']='unrelated texture';invalids.append(invalid)
        invalid=copy.deepcopy(city);invalid['materialBindings'][0]['sourceSpec']['metallic']=False;invalids.append(invalid)
        invalid=copy.deepcopy(city);invalid['materialBindings'][0]['sha256']='b'*64;invalids.append(invalid)
        invalid=copy.deepcopy(city);invalid['materialBindings']=[];invalids.append(invalid)
        for invalid in invalids:
            with self.assertRaisesRegex(ValueError,'matte navy'):
                publisher.material_binding_proof(plan,source,invalid)

    def test_all_route_directions_and_every_physical_gate_cut_are_required(self):
        plan = dict(signature='a'*64, routes=[dict(id='main', width=600, points=[[0, 0, 0], [1000, 0, 0]])],
                    gates=[dict(id='outer', index=0, leaves=[dict(point=[200, 0, 0], width=600, height=1800)]),
                           dict(id='inner', index=1, leaves=[dict(point=[800, 0, 0], width=1800, height=2600)])],
                    objectives=[[index*100, 0, 0] for index in range(8)],
                    optionalObjectives=[[index*100, 500, 0] for index in range(3)])
        city = dict(siegeMap='/Game/Candidate', city={'revision': 'b'*64}, packageHashes={'/Game/Candidate': 'c'*64})
        config = dict(signature='a'*64, map='/Game/Candidate', routes=[dict(id='main:'+direction,
                      points=plan['routes'][0]['points'] if direction == 'forward' else list(reversed(plan['routes'][0]['points'])),
                      clearWidthCm=600) for direction in ('forward', 'reverse')])
        config['anchors'] = [dict(id=kind+':'+str(index), point=point, index=index, optional=kind == 'optional')
                             for kind, points in (('main', plan['objectives']), ('optional', plan['optionalObjectives']))
                             for index, point in enumerate(points)]
        config['gates'] = [dict(id=gate['id']+':'+str(index), index=gate['index'], point=leaf['point'], width=leaf['width'], height=leaf['height'], sweepHalfSpanCm=400)
                           for gate in plan['gates'] for index, leaf in enumerate(gate['leaves'])]
        report = dict(passed=True, signature='a'*64, cityRevision='b'*64, map='/Game/Candidate', mapSha256='c'*64,
                      routeFailures=[], physicalFailures=[], routesWalked=2, completedRoutes=[dict(id='main:'+direction, grounded=True,
                      collisionEnabled=True, waypoints=2, distanceCm=1000) for direction in ('forward', 'reverse')],
                      gateSweeps=[], gateVerticalSweeps=[])
        report.update(width_evidence(config['routes']))
        report['objectiveSamples'] = [dict(id=anchor['id'], spoke=spoke, floor=True, capsuleClear=True, lineOfSight=spoke < 4)
                                      for anchor in config['anchors'] for spoke in range(8)]
        for gate in plan['gates']:
            for phase in range(3):
                closed = phase == 0 or (phase == 1 and gate['index'] == 1)
                for lane in (-1, 0, 1):
                    for direction in (-1, 1):
                        report['gateSweeps'].append(dict(id=gate['id']+':0', phase=phase, lane=lane, direction=direction,
                                                        passed=True, closed=closed, blocked=closed, actualLeafHalfThicknessCm=20,
                                                        sweepHalfSpanCm=400, startClear=True, endClear=True))
                for level in (1, 2, 3):
                    for direction in (-1, 1):
                        report['gateVerticalSweeps'].append(dict(id=gate['id']+':0', phase=phase, level=level, direction=direction,
                                                                heightCm=gate['leaves'][0]['height'], capsuleHalfHeightCm=96,
                                                                centerOffsetCm=99+(gate['leaves'][0]['height']-198)*level/4, passed=True,
                                                                closed=closed, blocked=closed, hitActor='gate' if closed else '',
                                                                actualLeafHalfThicknessCm=20, sweepHalfSpanCm=400,
                                                                startClear=True, endClear=True))
        publisher.route_proof(report, config, plan, city)
        leaking = copy.deepcopy(report); leaking['gateSweeps'][0]['blocked'] = False
        with self.assertRaisesRegex(ValueError, 'leaks'):
            publisher.route_proof(leaking, config, plan, city)
        missing_reverse = copy.deepcopy(report); missing_reverse['completedRoutes'].pop()
        with self.assertRaisesRegex(ValueError, 'Complete physical'):
            publisher.route_proof(missing_reverse, config, plan, city)
        wrong_corridor = copy.deepcopy(config); wrong_corridor['routes'][0]['points'][0][1] += 100
        with self.assertRaisesRegex(ValueError, 'Complete physical'):
            publisher.route_proof(report, wrong_corridor, plan, city)
        duplicate_route = copy.deepcopy(report); duplicate_route['completedRoutes'].append(copy.deepcopy(report['completedRoutes'][0]))
        with self.assertRaisesRegex(ValueError, 'Complete physical'):
            publisher.route_proof(duplicate_route, config, plan, city)
        invalid_distance = copy.deepcopy(report); invalid_distance['completedRoutes'][0]['distanceCm'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'traversal is incomplete'):
            publisher.route_proof(invalid_distance, config, plan, city)
        old_gate_height = copy.deepcopy(report); old_gate_height['gateVerticalSweeps'][18]['heightCm'] = 1100
        with self.assertRaisesRegex(ValueError, 'above floor level'):
            publisher.route_proof(old_gate_height, config, plan, city)
        gallery_drop = copy.deepcopy(report); gallery_drop['gateVerticalSweeps'][18]['blocked'] = False
        with self.assertRaisesRegex(ValueError, 'above floor level'):
            publisher.route_proof(gallery_drop, config, plan, city)
        relabeled_floor = copy.deepcopy(report); relabeled_floor['gateVerticalSweeps'][18]['centerOffsetCm'] = 99
        with self.assertRaisesRegex(ValueError, 'above floor level'):
            publisher.route_proof(relabeled_floor, config, plan, city)
        invalid_capsule = copy.deepcopy(report); invalid_capsule['gateVerticalSweeps'][18]['capsuleHalfHeightCm'] = 0
        with self.assertRaisesRegex(ValueError, 'above floor level'):
            publisher.route_proof(invalid_capsule, config, plan, city)
        no_gate_clearance = copy.deepcopy(report); no_gate_clearance['gateVerticalSweeps'][18]['capsuleHalfHeightCm'] = 1300
        with self.assertRaisesRegex(ValueError, 'above floor level'):
            publisher.route_proof(no_gate_clearance, config, plan, city)
        nonfinite_offset = copy.deepcopy(report); nonfinite_offset['gateVerticalSweeps'][18]['centerOffsetCm'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'above floor level'):
            publisher.route_proof(nonfinite_offset, config, plan, city)
        duplicate_height = copy.deepcopy(report); duplicate_height['gateVerticalSweeps'][1] = duplicate_height['gateVerticalSweeps'][0]
        with self.assertRaisesRegex(ValueError, 'Duplicate physical gate height'):
            publisher.route_proof(duplicate_height, config, plan, city)
        missing_height = copy.deepcopy(report); missing_height['gateVerticalSweeps'].pop()
        with self.assertRaisesRegex(ValueError, 'Complete physical'):
            publisher.route_proof(missing_height, config, plan, city)
        missing_floor = copy.deepcopy(report); missing_floor['objectiveSamples'].pop()
        with self.assertRaisesRegex(ValueError, 'floor and line-of-sight'):
            publisher.route_proof(missing_floor, config, plan, city)
        duplicate_spoke = copy.deepcopy(report); duplicate_spoke['objectiveSamples'][7]['spoke'] = 0
        with self.assertRaisesRegex(ValueError, 'physically playable'):
            publisher.route_proof(duplicate_spoke, config, plan, city)
        blocked_capture = copy.deepcopy(report); blocked_capture['objectiveSamples'][0]['capsuleClear'] = False
        with self.assertRaisesRegex(ValueError, 'physically playable'):
            publisher.route_proof(blocked_capture, config, plan, city)
        stale_anchor = copy.deepcopy(config); stale_anchor['anchors'][0]['point'][0] += 100
        with self.assertRaisesRegex(ValueError, 'match the source plan'):
            publisher.route_proof(report, stale_anchor, plan, city)

    def test_width_edges_need_real_ground_capsule_and_continuous_corner_movement(self):
        routes = [dict(id='corner:forward', clearWidthCm=600, points=[[0,0,0],[1000,0,500],[1000,600,500]])]
        evidence = width_evidence(routes)
        publisher.route_width_proof(evidence, routes)
        failures = []
        missing=copy.deepcopy(evidence);missing['routeWidthSamples'].pop();failures.append(missing)
        duplicate=copy.deepcopy(evidence);duplicate['routeWidthSamples'].append(duplicate['routeWidthSamples'][0]);failures.append(duplicate)
        shrunk=copy.deepcopy(evidence);shrunk['routeWidthConfig']['capsuleRadiusCm']=20;shrunk['capsuleRadiusCm']=20;failures.append(shrunk)
        inset=copy.deepcopy(evidence);inset['routeWidthConfig']['edgeInsetCm']=100;failures.append(inset)
        displaced=copy.deepcopy(evidence);displaced['routeWidthSamples'][0]['seed'][1]+=100;failures.append(displaced)
        floating=copy.deepcopy(evidence);floating['routeWidthSamples'][0]['floorDistanceCm']=100;failures.append(floating)
        unsupported=copy.deepcopy(evidence);unsupported['routeWidthSamples'][0]['center'][2]+=1000;failures.append(unsupported)
        unsafe=copy.deepcopy(evidence);unsafe['routeWidthSamples'][0]['floorNormalZ']=.5;failures.append(unsafe)
        blocked=copy.deepcopy(evidence);blocked['routeWidthSamples'][0]['placementClear']=False;failures.append(blocked)
        unwalked=copy.deepcopy(evidence);unwalked['routeWidthSamples'][5]['movementSteps']=0;failures.append(unwalked)
        for row in failures:
            with self.assertRaisesRegex(ValueError, 'full-width'):
                publisher.route_width_proof(row, routes)
        rounded=copy.deepcopy(evidence)
        rounded['routeWidthSamples'][0]['floorZCm']+=10;rounded['routeWidthSamples'][0]['floorImpact'][2]+=10
        publisher.route_width_proof(rounded, routes)

    def test_native_capsule_policy_cannot_be_omitted_relabelled_or_mutated(self):
        routes = [dict(id='straight:forward',clearWidthCm=600,points=[[0,0,0],[1000,0,0]])]
        for field,value in [('version',3),('capsulePolicyCheckedEveryTick',False),
                            ('capsulePolicyCheckedEveryPlacementQuery',False),('capsuleCollisionPolicy',None),('capsuleKinematicsPolicy',None)]:
            evidence=width_evidence(routes);evidence['routeWidthConfig'][field]=value
            with self.assertRaises(ValueError): publisher.route_width_proof(evidence,routes)
        for field in ('responses','classDefaultResponses'):
            evidence=width_evidence(routes);evidence['routeWidthConfig']['capsuleCollisionPolicy'][field][63]=0
            with self.assertRaisesRegex(ValueError,'capsule collision policy'): publisher.route_width_proof(evidence,routes)

    def test_native_views_require_real_ui_state_and_the_exact_signed_cameras(self):
        plan = dict(signature='a'*64, reviewViews=[dict(id=identity, eyeCm=[0,0,1000],
                    targetCm=[1000,0,1000], focalLengthMm=48,
                    **(dict(orthographicWidthCm=26000) if identity == 'top_down' else {}))
                    for identity in publisher.VIEW_IDS])
        city = dict(city=dict(revision='b'*64), siegeMap='/Game/Private/SiegeCandidate',
                    packageHashes={'/Game/Private/SiegeCandidate':'c'*64})
        identity = dict(signature=plan['signature'], cityRevision=city['city']['revision'],
                        map=city['siegeMap'], mapSha256='c'*64)
        config = dict(**identity, views=[dict(id=v['id'], eye=v['eyeCm'], target=v['targetCm'],
                      fieldOfView=2*math.atan(18/48)*180/math.pi,
                      **(dict(orthographicWidthCm=v['orthographicWidthCm']) if 'orthographicWidthCm' in v else {}))
                      for v in plan['reviewViews']])
        report = dict(**identity, passed=True, views=8, physicalFailures=[], routeFailures=[],
                      visualApproved=False, releaseAcceptance=False, architectureUiSuppressed=True,
                      viewPerformance=[dict(id=v['id'], eye=v['eye'], direction=[1,0,0], fieldOfView=v['fieldOfView'],
                        projection='orthographic' if 'orthographicWidthCm' in v else 'perspective',
                        canvasHudHidden=True, viewportWidgetsCollapsed=True, canvasHudCount=1, viewportWidgetCount=2,
                        **(dict(orthographicWidthCm=v['orthographicWidthCm']) if 'orthographicWidthCm' in v else {}))
                        for v in config['views']])
        publisher.native_view_proof(report, config, plan, city)
        rejected = []
        old=copy.deepcopy(report);old.pop('architectureUiSuppressed');rejected.append(old)
        for key,value in (('canvasHudHidden',False),('viewportWidgetsCollapsed',False),('canvasHudCount',-1),
                          ('viewportWidgetCount',.5),('canvasHudCount',1025),('canvasHudCount',True),('eye',[100,0,1000])):
            changed=copy.deepcopy(report);changed['viewPerformance'][0][key]=value;rejected.append(changed)
        stale=copy.deepcopy(report);stale['mapSha256']='d'*64;rejected.append(stale)
        for changed in rejected:
            with self.assertRaises(ValueError):
                publisher.native_view_proof(changed, config, plan, city)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/'proof';run.mkdir()
            report_file=run/'report.json';config_file=run/'config.json'
            report_file.write_text(json.dumps(report));config_file.write_text(json.dumps(config))
            visual=dict(nativeViews=dict(path='proof/report.json',sha256=publisher.digest(report_file),
                        config=dict(path='proof/config.json',sha256=publisher.digest(config_file))),
                        views=[dict(id=identity,path='proof/'+identity+'.png') for identity in publisher.VIEW_IDS])
            publisher.native_view_evidence(root,visual,plan,city)
            historical=copy.deepcopy(visual);historical['views'][0]['path']='other/hero.png'
            with self.assertRaisesRegex(ValueError,'intended native'):
                publisher.native_view_evidence(root,historical,plan,city)
            changed=copy.deepcopy(visual);changed['nativeViews']['config']['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'evidence changed'):
                publisher.native_view_evidence(root,changed,plan,city)

    def test_evidence_paths_and_interrupted_writes_are_confined_and_recoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); run = root / 'run'; run.mkdir()
            with self.assertRaises(ValueError):
                publisher.confined(root, '../outside.json')
            source = root / 'input.json'; source.write_text('original')
            journal = publisher.Journal(root, run, 'publish')
            journal.backup(source)
            with self.assertRaisesRegex(ValueError, 'interrupted'):
                publisher.Journal(root, run, 'publish')
            self.assertEqual((run / 'publication-backup/input.json').read_text(), 'original')
            journal.complete()
            self.assertFalse((run / 'publish-pending.json').exists())


if __name__ == '__main__':
    unittest.main()
