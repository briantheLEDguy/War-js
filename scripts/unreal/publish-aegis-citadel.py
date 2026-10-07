"""Journaled private publication of one reviewed citadel scenery revision.

Default execution validates only. Set WAR_CITADEL_PUBLISH_STAGE=prepare to build
isolated routing/live-gameplay candidates, or publish after fresh native evidence.
Run mutation phases only in the root-owned, serialized Editor commandlet. This
never grants final-package scenario, Steam or migration release acceptance.
"""
import copy
import hashlib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from shared_city_sources import RECEIPT, digest, package_file, routing, source_plan
from dutch_city_revision import merge_manifest
from citadel_route_surface_evidence import ABSENT as SURFACE_ABSENT, checked_profiles, checked_surface_bindings, checked_surface_report, width_seed

SIEGE = '/Game/Capitals/Siege/AegisCapital_Siege'
FRONTEND = '/Game/UI/Frontend/CapitalPresentation'
PROOFS = ('navigation', 'routes', 'rules', 'scenario', 'liveCapital', 'evacuation',
          'recovery', 'gm', 'network', 'performance', 'frontend')
VIEW_IDS = ('hero', 'front', 'top_down', 'central_plaza', 'grand_gate',
            'west_balcony', 'east_balcony', 'commander_hall')


def read(file):
    return json.loads(file.read_text(encoding='utf-8-sig'))


def write(file, value):
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_suffix(file.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(file)


def write_bytes(file, value):
    temporary = file.with_suffix(file.suffix + '.citadel.tmp')
    temporary.write_bytes(value)
    temporary.replace(file)


def confined(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or '\\' in relative:
        raise ValueError('A repository-relative evidence path is required.')
    file = (root / relative).resolve()
    file.relative_to(root.resolve())
    return file


def verify_hashes(root, hashes, *, protected_sources=False, engine_root=None):
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError('Complete native package hashes are required.')
    for package, expected in hashes.items():
        from citadel_performance_evidence import performance_package_file
        if (isinstance(package,str) and package.startswith('/Engine/')
                and (not protected_sources or package!='/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst')):
            raise ValueError('Engine candidate ownership or an unreviewed Engine source is forbidden.')
        if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected) or digest(performance_package_file(root, package, engine_root)) != expected:
            raise ValueError('Preserve changed native package: ' + package)


def indexed(rows):
    if not isinstance(rows, list) or any(not isinstance(r, dict) or not isinstance(r.get('id'), str) for r in rows):
        raise ValueError('Invalid GM object document.')
    result = {r['id']: r for r in rows}
    if len(result) != len(rows) or len({key.lower() for key in result}) != len(rows):
        raise ValueError('Duplicate GM object identity.')
    for row in rows:
        pose = row.get('transform', [])
        if (not row['id'] or len(row['id']) > 128 or not isinstance(row.get('sourceIdentity'), str)
                or len(row['sourceIdentity']) > 512 or not isinstance(row.get('hidden'), bool)
                or len(pose) != 10 or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in pose)
                or abs(sum(v*v for v in pose[3:7])-1) > 1e-7 or any(not .05 <= abs(v) <= 20 for v in pose[7:])):
            raise ValueError('Invalid native GM object state.')
    return result


def rebase_draft(document, proposed):
    """Preserve disjoint owner edits; removed edited objects/templates conflict."""
    if document.get('schemaVersion') not in (1, 2) or document.get('zoneId') != 'aegis_capital':
        raise ValueError('Unsupported owner GM document.')
    base = indexed(json.loads(document['baseline'])['objects'])
    current, candidate = indexed(document['objects']), indexed(proposed)
    merged = merge_manifest(base, candidate, current, 'gm/objects')
    if len(merged) > len(candidate) + 1000:
        raise ValueError('Rebased owner additions exceed native GM limits.')
    for key, row in merged.items():
        if key not in candidate and (row.get('templateId') not in candidate
                                     or candidate[row['templateId']]['sourceIdentity'] != row.get('sourceIdentity')):
            raise ValueError('Owner addition uses a removed or changed model template: ' + key)
    result = copy.deepcopy(document)
    result['schemaVersion'] = 2
    result['baseline'] = json.dumps({'objects': sorted(candidate.values(), key=lambda r: r['id'])}, separators=(',', ':'))
    result['objects'] = sorted(merged.values(), key=lambda r: r['id'])
    if len(json.dumps(result)) > 8_000_000:
        raise ValueError('Rebased GM document exceeds native storage limits.')
    return result


def gameplay_pad_proof(plan, city):
    """Bind actual native prop bounds to signed clear pads and preserved ammunition."""
    from aegis_citadel_blueprint import route_clearance
    pads, placements = plan.get('gameplayPads'), city.get('gameplayPadPlacements')
    if (not isinstance(pads, list) or not pads or not isinstance(placements, list)
            or len(placements) != len(pads)
            or any(not isinstance(row, dict) or not isinstance(row.get('id'), str) for row in pads)
            or any(not isinstance(row, dict) or not isinstance(row.get('id'), str)
                   or not isinstance(row.get('actor'), str) for row in placements)):
        raise ValueError('Complete actual native gameplay pad evidence is required.')
    by_id = {row.get('id'): row for row in placements}
    if (len(by_id) != len(placements) or set(by_id) != {pad['id'] for pad in pads}
            or len({row.get('actor') for row in placements}) != len(placements)):
        raise ValueError('Native gameplay pad identity differs from the signed plan.')
    for pad in pads:
        row = by_id[pad['id']]
        if not isinstance(row.get('actor'), str) or not row['actor'].startswith(city['siegeMap']+'.'):
            raise ValueError('Gameplay prop belongs to another native candidate.')
        if pad.get('preserveTransform'):
            if row.get('preserved') is not True or not re.fullmatch('[a-f0-9]{64}', str(row.get('stateHash'))):
                raise ValueError('Retained lower-city ammunition needs its exact native state hash.')
            continue
        point, radius, height, bounds = row.get('footprintCentreFloorCm'), row.get('footprintRadiusCm'), row.get('heightCm'), row.get('boundsCm')
        if (row.get('preserved') is not False or not isinstance(point, list) or len(point) != 3
                or not isinstance(bounds, list) or len(bounds) != 2 or any(not isinstance(b, list) or len(b) != 3 for b in bounds)
                or any(type(n) not in (int, float) or not math.isfinite(n) for n in [*point, radius, height, *bounds[0], *bounds[1]])
                or radius <= 0 or radius > pad['maximumFootprintRadiusCm'] or height <= 0 or height > pad['maximumHeightCm']
                or any(bounds[1][i] <= bounds[0][i] for i in range(3))
                or math.dist(point, pad['footprintCentreFloorCm']) > .1
                or math.dist(point, [(bounds[0][0]+bounds[1][0])/2, (bounds[0][1]+bounds[1][1])/2, bounds[0][2]]) > .1
                or abs(radius-math.hypot((bounds[1][0]-bounds[0][0])/2, (bounds[1][1]-bounds[0][1])/2)) > .1
                or abs(height-(bounds[1][2]-bounds[0][2])) > .1
                or any(not re.fullmatch('[a-f0-9]{64}', str(row.get(key))) for key in ('sourceStateHash', 'actualStateHash'))
                or not route_clearance(plan, point, radius, height)):
            raise ValueError('Actual gameplay prop bounds exceed or obstruct their signed clear pad: '+pad['id'])
        if pad['binding'] == 'gate_mechanisms':
            anchors = plan['objectives'][4:7]+plan['optionalObjectives'][1:2]
            gap = radius+pad['captureClearRadiusCm']+pad['minimumCaptureGapCm']
        else:
            anchors = [plan['optionalObjectives'][pad['optionalIndex']]]
            gap = radius+pad['minimumTargetGapCm']
        if any(math.dist(point[:2], anchor[:2]) < gap for anchor in anchors):
            raise ValueError('Actual gameplay prop obstructs a player objective: '+pad['id'])


MATTE_NAVY = dict(tint=[.0035,.012,.034],roughness=.92,metallic=0,specular=.25)


def material_binding_proof(plan, source, city):
    """Bind only the approved navy scalar graph, including actual disconnected inputs."""
    rows=city.get('materialBindings');package='/Game/WorldRebuild/AegisCitadel_'+plan['revision']+'/Materials/M_blue'
    if not isinstance(rows,list) or len(rows)!=1 or not isinstance(rows[0],dict):
        raise ValueError('Owned matte navy material binding is missing.')
    row=rows[0];spec=source.get('materialSpecs',{}).get('blue');actual=row.get('actualConstantReadback')
    def exact_spec(value):
        return (isinstance(value,dict) and set(value)==set(MATTE_NAVY)
                and isinstance(value.get('tint'),list) and len(value['tint'])==3
                and all(type(v) in (int,float) and v==MATTE_NAVY['tint'][i] for i,v in enumerate(value['tint']))
                and all(type(value.get(k)) in (int,float) and value[k]==MATTE_NAVY[k] for k in ('roughness','metallic','specular')))
    if (set(row)!={'role','package','sha256','sourceSpec','actualConstantReadback'} or row.get('role')!='blue'
            or row.get('package')!=package or not re.fullmatch('[a-f0-9]{64}',str(row.get('sha256')))
            or row['sha256']!=city.get('packageHashes',{}).get(package) or not exact_spec(spec) or not exact_spec(row.get('sourceSpec'))
            or not isinstance(actual,dict) or set(actual)!={'tint','roughness','metallic','specular','normalInputConnected','ambientOcclusionInputConnected'}
            or not isinstance(actual.get('tint'),list) or len(actual['tint'])!=3
            or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v-spec['tint'][i])>1e-6 for i,v in enumerate(actual['tint']))
            or any(type(actual.get(k)) not in (int,float) or not math.isfinite(actual[k]) or abs(actual[k]-spec[k])>1e-6 for k in ('roughness','metallic','specular'))
            or actual.get('normalInputConnected') is not False or actual.get('ambientOcclusionInputConnected') is not False):
        raise ValueError('Owned matte navy constants, graph readbacks or package binding differ from the signed source.')


def normal_texture_binding_proof(plan, source, city):
    if plan.get('recipeVersion',1)<11:return
    sources=set()
    for spec in source.get('materialSpecs',{}).values():
        if 'normal' not in spec:continue
        file=spec['normal']
        if (not isinstance(file,str) or not re.fullmatch(r'public/assets/[a-zA-Z0-9_./-]+\.png',file)
                or '..' in file.split('/') or spec.get('normalConvention')!='gltf_opengl_positive_y'):
            raise ValueError('Original citadel normal source convention is missing.')
        sources.add(file)
    rows=city.get('nativeNormalTextureBindings');seen=set()
    if not isinstance(rows,list) or len(rows)!=len(sources):
        raise ValueError('Original citadel OpenGL normal bindings are missing or duplicated.')
    for row in rows:
        package=f'/Game/WorldRebuild/AegisCitadel_{city["revision"]}/Textures/T_{Path(row.get("source","")).stem}_normal'
        if (set(row)!={'source','sourceSha256','sourceConvention','package','sha256',
                    'actualFlipGreenChannel','actualSrgb','actualCompression'}
                or row['source'] not in sources or row['source'] in seen
                or row['sourceConvention']!='gltf_opengl_positive_y' or row['package']!=package
                or not re.fullmatch('[a-f0-9]{64}',str(row['sha256'])) or row['sha256']!=city.get('packageHashes',{}).get(package)
                or not re.fullmatch('[a-f0-9]{64}',str(row['sourceSha256'])) or row['sourceSha256']!=source.get('materialSources',{}).get(row['source'])
                or row['actualFlipGreenChannel'] is not True or row['actualSrgb'] is not False or row['actualCompression']!='TC_NORMALMAP'):
            raise ValueError('Original citadel OpenGL normal import readbacks or package hashes differ.')
        seen.add(row['source'])


def versioned_mesh_bindings(plan, rows, bindings):
    version = plan.get('recipeVersion', 1)
    if type(version) is not int or not 1 <= version <= 12:
        raise ValueError('Unsupported citadel mesh recipe version.')
    # Recipe twelve changes crown geometry within the signed 45-model manifest.
    count = 45 if version >= 10 else 39 if version == 9 else 38
    if (not isinstance(rows, list) or len(rows) != count
            or not isinstance(bindings, list) or len(bindings) != count
            or any(not isinstance(row, dict) or not isinstance(row.get('id'), str)
                   for row in rows + bindings)):
        raise ValueError('Every versioned native binding must match the signed source manifest.')
    native = {row['id']: row for row in bindings}
    source_ids = {row['id'] for row in rows}
    if len(native) != count or len(source_ids) != count or set(native) != source_ids:
        raise ValueError('Duplicate or mismatched native/source citadel mesh identity.')
    if ('wing_foundation_repairs' in source_ids) != (version >= 9):
        raise ValueError('Wing foundation binding differs from the recorded recipe version.')
    dressing = {'dressing_'+key for key in ('forehall','throne_hall','west_archive','east_treasury','west_terrace','east_terrace')}
    if source_ids.intersection(dressing) != (dressing if version >= 10 else set()):
        raise ValueError('Furnishing groups differ from the recorded recipe version.')
    return native


def import_binding_proof(run, plan, source, city):
    from aegis_citadel_blueprint import digest as value_digest
    from citadel_stage_contract import (NATIVE_IMPORT_CONVENTION, SOURCE_TRIANGLE_CONVENTION, native_triangle_indices,
        NATIVE_MESH_BUILD_SETTINGS, checked_render_audit, source_array_sha256)
    material_binding_proof(plan,source,city)
    normal_texture_binding_proof(plan,source,city)
    if city.get('nativeImportConvention') != NATIVE_IMPORT_CONVENTION:
        raise ValueError('Explicit source CCW to native CW outward-normal import convention is required.')
    rows, bindings = source.get('assets'), city.get('bindings')
    if (source.get('schemaVersion') != 1 or source.get('revision') != plan['revision']
            or source.get('blueprintSignature') != plan['signature'] or source.get('geometrySignature') != city['geometrySignature']):
        raise ValueError('Native bindings must match the signed source manifest.')
    native = versioned_mesh_bindings(plan, rows, bindings)
    meshes = {}
    for row in rows:
        binding = native.get(row['id'], {})
        package = '/Game/WorldRebuild/AegisCitadel_'+plan['revision']+'/Meshes/SM_'+row['id']
        if (not re.fullmatch('[a-z0-9_]+', row['id']) or binding.get('mesh') != package
                or binding.get('sha256') != city['packageHashes'].get(package)
                or type(row.get('gateLeaf')) is not bool or binding.get('gateLeaf') is not row['gateLeaf']
                or not isinstance(binding.get('triangles'), list) or not binding['triangles']
                or binding['triangles'][0] != row['triangles']):
            raise ValueError('Native mesh ownership/source triangle count differs: '+row['id'])
        file = confined(run, row['meshFile'])
        if digest(file) != row['sha256']:
            raise ValueError('Signed citadel mesh source changed: '+row['id'])
        mesh = read(file)
        meshes[row['id']] = mesh
        indices = native_triangle_indices(mesh, SOURCE_TRIANGLE_CONVENTION)
        if (len(indices)//3 != row['triangles'] or binding.get('sourceIndicesSha256') != value_digest(mesh['indices'])
                or binding.get('nativeIndicesSha256') != value_digest(indices)):
            raise ValueError('Native source-to-import index hashes differ: '+row['id'])
        source_text = file.read_text(encoding='utf-8')
        payload = binding.get('renderDataAuditPayload')
        if (binding.get('sourceArrayHashConvention') != 'sha256_raw_utf8_mesh_json_member_array'
                or binding.get('nativeMeshBuildSettings') != NATIVE_MESH_BUILD_SETTINGS
                or any(binding.get('source'+title+'Sha256') != source_array_sha256(source_text,key)
                       for title,key in (('Positions','positions'),('Normals','normals'),('UVs','uvs')))
                or not isinstance(payload,str) or len(payload)>1_000_000
                or hashlib.sha256(payload.encode()).hexdigest()!=binding.get('renderDataAuditSha256')
                or json.loads(payload)!=binding.get('renderDataAudit')):
            raise ValueError('Native render-buffer audit/source normal/UV hashes or build policy differ: '+row['id'])
        audit=checked_render_audit(binding['renderDataAudit'],package+'.'+package.split('/')[-1])
        if len(audit['lods'])!=len(binding['triangles']):
            raise ValueError('Incomplete native render-buffer LOD audit: '+row['id'])
        base=next(lod for lod in audit['lods'] if lod['lod']==0)
        if (base.get('sourcePositionToleranceCm')!=.1 or base.get('sourceNormalDotThreshold')!=.995
                or base.get('sourceMatchingPolicy')!='oriented_triangle_corners_material_and_uv0'
                or type(base.get('indices')) is not int or base['indices']%3
                or base.get('committedSourceTriangleMatches')!=base['indices']//3
                or base.get('committedSourceTrianglesMissing')!=0 or base.get('committedSourceTrianglesDifferent')!=0
                or base.get('sourceUvAbsoluteTolerance')!=.0005 or base.get('sourceUvRelativeTolerance')!=.001):
            raise ValueError('Native render-buffer oriented source triangle matching policy/tolerances changed: '+row['id'])
    checked_surface_bindings(source, plan, meshes)
    if (source['geometrySignature'] != value_digest([(row['id'],row['sha256']) for row in rows])
            or digest(confined(run,source['sourceMaster']['path'])) != source['sourceMaster']['sha256']):
        raise ValueError('Authored geometry manifest or Blender master changed.')
    start = city.get('proofStart', {});floor = plan.get('teamSpawns', [None,None])[1]
    point = lambda value: isinstance(value,list) and len(value)==3 and all(type(v) in (int,float) and math.isfinite(v) for v in value)
    if (not point(floor) or not isinstance(start.get('actor'),str) or not start['actor'].startswith(city['siegeMap']+'.')
            or start.get('sourceTeamSpawnIndex') != 1 or not point(start.get('signedFloorCm')) or not point(start.get('locationCm'))
            or math.dist(start['signedFloorCm'],floor) > .1 or math.dist(start['locationCm'],[floor[0],floor[1],floor[2]+99]) > .1
            or type(start.get('actualFloorZCm')) not in (int,float) or not math.isfinite(start['actualFloorZCm'])
            or abs(start['actualFloorZCm']-floor[2]) > 15 or start.get('capsuleRadiusCm') != 42
            or start.get('capsuleHalfHeightCm') != 96 or start.get('capsuleClear') is not True
            or start.get('traceChannel') != 'Visibility' or start.get('traceComplex') is not True
            or type(start.get('otherStartsPreserved')) is not int or start['otherStartsPreserved'] < 0):
        raise ValueError('Private proof start differs from signed lower-city spawn or actual capsule clearance.')


def historical_lighting_proof(plan, city):
    """Permit only the five signed, copied environment actors with actual readbacks."""
    from aegis_citadel_blueprint import LIGHTING_FIXTURES_V1 as LIGHTING_FIXTURES
    specs=plan.get('lightingTreatment',{}).get('fixtures');changes=city.get('sharedLightingChanges')
    preserved=city.get('outsideMaskPreservation');prefix='/Game/WorldRebuild/AegisCitadel_'+city['revision']+'/Layers/RetainedCity_'
    sha=lambda value:isinstance(value,str) and bool(re.fullmatch('[a-f0-9]{64}',value))
    if (plan.get('lightingTreatment',{}).get('schemaVersion')!=1
            or plan['lightingTreatment'].get('exposureUnits')!='native_luminance' or plan['lightingTreatment'].get('expectedExtendedEV100') is not False
            or city.get('exposureUsesExtendedEV100') is not False or city.get('exposureUnits')!='native_luminance'
            or not isinstance(specs,list) or len(specs)!=5 or not isinstance(changes,list) or len(changes)!=5
            or not isinstance(preserved,list) or not preserved
            or len({s.get('actor') for s in specs})!=5 or len({c.get('actor') for c in changes})!=5):
        raise ValueError('Exactly five signed native lighting changes and preservation witnesses are required.')
    def actual_value(wanted):
        if isinstance(wanted,dict):
            if wanted['kind']=='enum':return wanted['type']+'.'+wanted['value']
            return wanted['value']
        return wanted
    def same_value(wanted,actual):
        if isinstance(wanted,bool) or isinstance(wanted,str):return type(actual) is type(wanted) and actual==wanted
        if isinstance(wanted,list):return isinstance(actual,list) and len(actual)==len(wanted) and all(same_value(w,a) for w,a in zip(wanted,actual))
        return type(wanted) in (int,float) and type(actual) in (int,float) and math.isfinite(wanted) and math.isfinite(actual) and abs(wanted-actual)<=max(1e-5,abs(wanted)*1e-6)
    for expected in LIGHTING_FIXTURES:
        spec=next((s for s in specs if s.get('actor')==expected['actor']),{})
        change=next((c for c in changes if c.get('actor')==expected['actor']),{})
        if (any(spec.get(k)!=v for k,v in expected.items()) or set(spec)!=set(expected)|{'package','sourceStateHash'}
                or not sha(spec.get('sourceStateHash')) or not sha(city.get('sourceHashes',{}).get(spec.get('package')))
                or spec['package'] in city.get('packageHashes',{}) or change.get('sourcePackage')!=spec['package']
                or not re.fullmatch(re.escape(prefix)+r'[0-9]+',str(change.get('package')))
                or not sha(city.get('packageHashes',{}).get(change.get('package')))
                or change.get('package') not in city.get('sceneryLevels',[])
                or change.get('sourceStateHash')!=spec['sourceStateHash'] or not sha(change.get('actualStateHash'))
                or change.get('requestedProperties')!=spec['properties']):
            raise ValueError('Native lighting identity, source state, ownership or property allowance changed.')
        wanted={k:actual_value(v) for k,v in spec['properties'].items()}
        if 'rotationDegrees' in spec:wanted['rotationDegrees']=spec['rotationDegrees']
        actual=change.get('actualPropertyReadback',{})
        if set(actual)!=set(wanted) or any(not same_value(v,actual[k]) for k,v in wanted.items()):
            raise ValueError('Actual lighting readback differs from signed properties.')
        if not any(p.get('source')==spec['package'] and p.get('candidate')==change['package'] for p in preserved):
            raise ValueError('A lighting change lacks its exact copied-layer preservation boundary.')
    if len({p.get('candidate') for p in preserved})!=len(preserved):raise ValueError('Duplicate preserved layer.')
    for row in preserved:
        expected=sorted(c['actor'] for c in changes if c['package']==row.get('candidate') and c['sourcePackage']==row.get('source'))
        if (row.get('matchesExpected') is not True or not sha(city.get('sourceHashes',{}).get(row.get('source')))
                or not sha(city.get('packageHashes',{}).get(row.get('candidate'))) or not sha(row.get('preservedStateSha256'))
                or row.get('candidate') not in city.get('sceneryLevels',[])
                or type(row.get('preservedActorCount')) is not int or row['preservedActorCount']<0
                or not isinstance(row.get('explicitLightingChanges'),list) or sorted(row['explicitLightingChanges'])!=expected):
            raise ValueError('An unrelated preserved actor was allowed through the lighting exception.')


def lighting_proof(plan, city, *, historical=False):
    """Fresh publication uses exact version2 identities; version1 is inspection only."""
    if plan.get('lightingTreatment', {}).get('schemaVersion') == 1 and historical:
        return historical_lighting_proof(plan, city)
    from aegis_citadel_lighting import FIXTURES, CLOUD_IDENTITY, REVIEWED_CLOUD_MATERIAL
    from aegis_citadel_blueprint import LIGHTING_REQUESTS
    treatment=plan.get('lightingTreatment', {});specs=treatment.get('fixtures');changes=city.get('sharedLightingChanges')
    preserved=city.get('outsideMaskPreservation');prefix='/Game/WorldRebuild/AegisCitadel_'+str(city.get('revision'))+'/Layers/'
    sha=lambda value:isinstance(value,str) and bool(re.fullmatch('[a-f0-9]{64}',value))
    point=lambda value:isinstance(value,list) and len(value)==3 and all(type(n) in (int,float) and math.isfinite(n) for n in value)
    if (treatment.get('schemaVersion')!=2 or not re.fullmatch('[a-f0-9]{12}',str(city.get('revision')))
            or treatment.get('exposureUnits')!='native_luminance' or treatment.get('expectedExtendedEV100') is not False
            or treatment.get('existingAtmospherePreserved') is not False
            or city.get('exposureUsesExtendedEV100') is not False or city.get('exposureUnits')!='native_luminance'
            or not isinstance(specs,list) or len(specs)!=7 or not isinstance(changes,list) or len(changes)!=7
            or any(not isinstance(row,dict) for row in specs+changes)
            or len({s.get('id') for s in specs})!=7 or len({c.get('id') for c in changes})!=7
            or not isinstance(preserved,list) or not preserved):
        raise ValueError('Fresh lighting requires version2 with seven package-scoped source identities.')
    requests={row['id']:copy.deepcopy(row) for row in LIGHTING_REQUESTS}
    requests['sun']['rotationDegrees']=[-20,30,0]
    requests['ambient_sky']['properties']['intensity']=.35
    def native_value(value):
        if isinstance(value,dict):return value['type']+'.'+value['value'] if value['kind']=='enum' else value['value']
        return value
    def same_native(wanted,actual):
        if isinstance(wanted,bool) or isinstance(wanted,str):return type(wanted) is type(actual) and wanted==actual
        if isinstance(wanted,list):return isinstance(actual,list) and len(actual)==len(wanted) and all(same_native(w,a) for w,a in zip(wanted,actual))
        return type(wanted) in (int,float) and type(actual) in (int,float) and math.isfinite(wanted) and math.isfinite(actual) and abs(wanted-actual)<=max(1e-5,abs(wanted)*1e-6)
    for fixture_id,actor,klass,label,component,layer,tag in FIXTURES:
        spec=next((row for row in specs if row['id']==fixture_id),{})
        change=next((row for row in changes if row['id']==fixture_id),{})
        source='/Game/WorldRebuild/DutchBastion_d105951f4aab/Layers/'+layer
        wanted_identity=dict(actor=actor,klass=klass,label=label,component=component,requiredTag=tag)
        tags=sorted([tag]+(['WarCapitalWorkbench'] if fixture_id in ('sun','ambient_sky','exposure','atmosphere') else ['WarDutchBastion'] if fixture_id=='dutch_street_fill' else []))
        if (any(spec.get(key)!=value or change.get(key)!=value for key,value in wanted_identity.items())
                or spec.get('package')!=source or change.get('sourcePackage')!=source
                or not sha(spec.get('sourceStateHash')) or change.get('sourceStateHash')!=spec['sourceStateHash']
                or not sha(spec.get('sourcePackageSha256')) or city.get('sourceHashes',{}).get(source)!=spec['sourcePackageSha256']
                or change.get('sourcePackageSha256')!=spec['sourcePackageSha256'] or source in city.get('packageHashes',{})
                or not re.fullmatch(re.escape(prefix)+r'RetainedCity_[0-9]+',str(change.get('package')))
                or not sha(city.get('packageHashes',{}).get(change.get('package')))
                or change.get('package') not in city.get('sceneryLevels',[]) or not sha(change.get('actualStateHash'))
                or not isinstance(change.get('actualTags'),list) or sorted(change['actualTags'])!=tags
                or spec.get('properties')!=requests[fixture_id]['properties']
                or spec.get('rotationDegrees')!=requests[fixture_id].get('rotationDegrees')
                or change.get('requestedProperties')!=spec['properties']):
            raise ValueError('Copied lighting identity, source or exact signed property policy changed: '+fixture_id)
        wanted={key:native_value(value) for key,value in spec['properties'].items()}
        if 'rotationDegrees' in spec:wanted['rotationDegrees']=spec['rotationDegrees']
        actual=change.get('actualPropertyReadback')
        if (not isinstance(actual,dict) or set(actual)!=set(wanted) or any(not same_native(value,actual[key]) for key,value in wanted.items())
                or not any(row.get('source')==source and row.get('candidate')==change['package'] for row in preserved)):
            raise ValueError('Actual native lighting readbacks differ from exact signed fields: '+fixture_id)
    if len({row.get('candidate') for row in preserved})!=len(preserved):raise ValueError('Duplicate copied scenery boundary.')
    for row in preserved:
        expected=sorted(change['id'] for change in changes if change['package']==row.get('candidate') and change['sourcePackage']==row.get('source'))
        if (row.get('matchesExpected') is not True or not sha(city.get('sourceHashes',{}).get(row.get('source')))
                or not sha(city.get('packageHashes',{}).get(row.get('candidate'))) or row.get('candidate') not in city.get('sceneryLevels',[])
                or not sha(row.get('preservedStateSha256')) or type(row.get('preservedActorCount')) is not int or row['preservedActorCount']<0
                or not isinstance(row.get('explicitLightingChanges'),list) or sorted(row['explicitLightingChanges'])!=expected):
            raise ValueError('An unrelated actor was allowed through copied lighting exceptions.')
    cloud=treatment.get('cloudFixture');placed=city.get('nativeCloudPlacement')
    if not isinstance(cloud,dict) or not isinstance(placed,dict):raise ValueError('Owned native cloud witness is missing.')
    material=cloud.get('material',{})
    if (any(cloud.get(key)!=value or placed.get(key)!=value for key,value in CLOUD_IDENTITY.items())
            or cloud.get('pointCm')!=[0,0,0] or placed.get('pointCm')!=cloud['pointCm'] or not point(placed.get('actualPointCm'))
            or any(abs(value)>1e-3 for value in placed['actualPointCm'])
            or placed.get('package')!=prefix+'GothicCitadel' or placed['package'] not in city.get('sceneryLevels',[])
            or not sha(city.get('packageHashes',{}).get(placed['package'])) or not sha(placed.get('stateHash'))
            or not isinstance(placed.get('actualTags'),list) or CLOUD_IDENTITY['requiredTag'] not in placed['actualTags']
            or len(set(placed['actualTags']))!=len(placed['actualTags'])
            or any(not isinstance(tag,str) or not tag or len(tag)>128 for tag in placed['actualTags'])
            or not isinstance(material,dict) or material.get('package')!=REVIEWED_CLOUD_MATERIAL
            or material.get('path')!=REVIEWED_CLOUD_MATERIAL+'.m_SimpleVolumetricCloud_Inst' or not sha(material.get('sha256'))
            or city.get('sourceHashes',{}).get(REVIEWED_CLOUD_MATERIAL)!=material['sha256'] or REVIEWED_CLOUD_MATERIAL in city.get('packageHashes',{})
            or placed.get('material')!=material
            or cloud.get('properties')!=dict(layer_bottom_altitude=.5,layer_height=1.2,
                view_sample_count_scale=2,shadow_view_sample_count_scale=2) or placed.get('requestedProperties')!=cloud['properties']
            or not isinstance(placed.get('actualPropertyReadback'),dict) or set(placed['actualPropertyReadback'])!=set(cloud['properties'])
            or any(not same_native(value,placed['actualPropertyReadback'][key]) for key,value in cloud['properties'].items())):
        raise ValueError('Owned cloud actor/material/layer readbacks differ from the signed native fixture.')
    instance=cloud.get('materialInstance');actual=placed.get('materialInstance')
    owned_package='/Game/WorldRebuild/AegisCitadel_'+city['revision']+'/Materials/MI_Cloud'
    scalars=dict(Layout_CloudGlobalScale=8,Cloud_GlobalCoverage=.25,Cloud_GlobalDensity=.008,StormClouds=.65)
    vectors=dict(Cloud_AlbedoColor=[.65,.70,.78,.5],Storm_LightningColor=[0,0,0,0],Layout_CloudTypeMask=[0,0,1,0])
    if (not isinstance(instance,dict) or set(instance)!= {'name','parent','scalarParameters','vectorParameters'}
            or instance.get('name')!='MI_Cloud' or instance.get('parent')!=material['path']
            or instance.get('scalarParameters')!=scalars or instance.get('vectorParameters')!=vectors
            or not isinstance(actual,dict) or set(actual)!={'package','path','sha256','parent','requestedScalarParameters',
                'actualScalarReadback','requestedVectorParameters','actualVectorReadback','registeredScalarParameters','registeredVectorParameters'}
            or actual.get('package')!=owned_package or actual.get('path')!=owned_package+'.MI_Cloud'
            or actual.get('parent')!=instance['parent'] or not sha(actual.get('sha256'))
            or city.get('packageHashes',{}).get(owned_package)!=actual['sha256'] or owned_package in city.get('sourceHashes',{})
            or placed.get('actualMaterial')!=actual['path']):
        raise ValueError('Cloud MIC must be privately owned and bound to the unchanged Engine parent.')
    for kind,wanted in (('Scalar',scalars),('Vector',vectors)):
        requested=actual.get('requested'+kind+'Parameters');observed=actual.get('actual'+kind+'Readback')
        registered=actual.get('registered'+kind+'Parameters')
        if (requested!=wanted or not isinstance(observed,dict) or set(observed)!=set(wanted)
                or not isinstance(registered,list) or not 0<len(registered)<=256
                or any(not isinstance(name,str) or not name or len(name)>128 for name in registered)
                or len(set(registered))!=len(registered)
                or any(name not in registered or not same_native(value,observed[name]) for name,value in wanted.items())):
            raise ValueError('Cloud MIC needs exact registered names and typed native parameter readbacks: '+kind)


def candidate(root, run):
    from aegis_citadel_blueprint import validate
    plan, source, city = read(run / 'blueprint.json'), read(run / 'assets-source.json'), read(run / 'candidate.json')
    validate(plan)
    for recipe, expected in plan['sourceRecipes'].items():
        if digest(confined(root / 'scripts/unreal', recipe)) != expected:
            raise ValueError('Citadel source recipe changed; generate and prove a new revision.')
    for asset in source['assets']:
        if digest(confined(run, asset['meshFile'])) != asset['sha256']:
            raise ValueError('Authored citadel mesh source changed.')
    for file, expected in source.get('materialSources', {}).items():
        if digest(confined(root, file)) != expected:
            raise ValueError('Original citadel material source changed.')
    destination = '/Game/WorldRebuild/AegisCitadel_' + plan['revision']
    if (city.get('schemaVersion') != 1 or city.get('revision') != plan['revision']
            or city.get('signature') != plan['signature'] or source.get('blueprintSignature') != plan['signature']
            or city.get('geometrySignature') != source.get('geometrySignature') or city.get('nativeImported') is not True
            or city.get('map') != destination + '/ReviewCandidate' or city.get('siegeMap') != destination + '/SiegeCandidate'
            or city.get('city', {}).get('definition') != destination + '/City'):
        raise ValueError('A current, actually staged native citadel candidate is required.')
    cloud=plan.get('lightingTreatment',{}).get('cloudFixture')
    if cloud:
        material=cloud['material']
        if (city['sourceHashes'].get(material['package'])!=material['sha256'] or
                city['city']['dependencyHashes'].get(material['package'])!=material['sha256']):
            raise ValueError('Shared city publication must retain the signed protected cloud parent dependency.')
    verify_hashes(root, city['sourceHashes'], protected_sources=True)
    verify_hashes(root, city['packageHashes'])
    verify_hashes(root, city['city']['dependencyHashes'], protected_sources=True)
    verify_hashes(root, city['city']['packageHashes'])
    if any(p in city['packageHashes'] and city['packageHashes'][p] != h for p,h in city['sourceHashes'].items()):
        raise ValueError('Conflicting owned/source package hashes in the candidate receipt.')
    bound_hashes = {**city['sourceHashes'], **city['packageHashes']}
    for package in [city['city']['definition'], *city['sceneryLevels']]:
        if bound_hashes.get(package) != city['city']['packageHashes'].get(package):
            raise ValueError('Candidate city binding hashes differ from staged packages.')
    payload = city['city'].get('revisionPayload')
    expected = dict(scenery={p: city['city']['packageHashes'][p] for p in city['sceneryLevels']},
                    dependencies=city['city']['dependencyHashes'], origin=city['city']['origin'])
    if (not isinstance(payload, str) or hashlib.sha256(payload.encode()).hexdigest() != city['city'].get('revision')
            or json.loads(payload) != expected):
        raise ValueError('Candidate city revision payload differs from its actual scenery, dependencies or origin.')
    current = next(c for c in source_plan(root)['cities'] if c['id'] == 'aegis_capital')
    if city['retainedGameplayLevels'] != current['gameplayLevels'] or city['city']['origin'] != current['origin']:
        raise ValueError('Campaign services or capital origin changed after the survey.')
    if city['sceneryLevels'] != city['city']['sceneryLevels'] or set(city['sceneryLevels']) & set(current['gameplayLevels']):
        raise ValueError('Scenery/gameplay ownership overlaps.')
    if city.get('stageRecipeSha256') != digest(root / 'scripts/unreal/stage-aegis-citadel.py'):
        raise ValueError('Candidate staging recipe changed; preserve it and prove a new revision.')
    dependencies = city.get('stageDependencySha256')
    if (not isinstance(dependencies, dict) or 'citadel_stage_contract.py' not in dependencies
            or any(not re.fullmatch('[A-Za-z0-9_-]+\\.py', name) or not re.fullmatch('[a-f0-9]{64}', str(expected))
                   or digest(confined(root / 'scripts/unreal', name)) != expected for name,expected in dependencies.items())):
        raise ValueError('Candidate staging dependency changed; preserve it and repeat bounded native preparation.')
    gameplay_pad_proof(plan, city)
    import_binding_proof(run, plan, source, city)
    lighting_proof(plan, city)
    from citadel_terrain_evidence import require_terrain_carves
    require_terrain_carves(root, run, plan, city)
    return plan, city, current


def route_width_proof(report, routes):
    """Every corridor edge uses grounded native capsule placements and movement."""
    if not routes:
        return
    setup = report.get('routeWidthConfig', {})
    finite = lambda value: type(value) in (int, float) and math.isfinite(value)
    point = lambda value: isinstance(value, list) and len(value) == 3 and all(finite(v) for v in value)
    if (report.get('routeWidthComplete') is not True or report.get('routeWidthPassed') is not True
            or setup.get('version') != 4 or setup.get('laneFractions') != [-1, -.5, 0, .5, 1]
            or setup.get('placementOverlapPolicy') != 'fresh_live_static_single_body_unit_zero_margin_full_capsule_planes_v1'
            or setup.get('gateOverlapAdmissionRemainsRaw') is not True
            or setup.get('maxSpacingCm') != 100 or setup.get('movementSpacingCm') != 10
            or setup.get('edgeInsetCm') != 0 or setup.get('maxFloorDeviationCm') != 120
            or setup.get('groundClearanceCm') != 2.4 or setup.get('collisionChannel') != 'ECC_Pawn'
            or setup.get('collisionProfile') != 'Custom' or setup.get('simpleCollision') is not True
            or setup.get('capsulePolicyCheckedEveryTick') is not True or setup.get('capsulePolicyCheckedEveryPlacementQuery') is not True
            or setup.get('movementMethod') != 'ComputeGroundMovementDelta/ramp-resweep/StepUp-floor-handoff/FindFloor/AdjustFloorHeight'
            or not finite(setup.get('capsuleRadiusCm')) or setup['capsuleRadiusCm'] < 42
            or not finite(setup.get('capsuleHalfHeightCm')) or setup['capsuleHalfHeightCm'] < 96
            or setup['capsuleRadiusCm'] != report.get('capsuleRadiusCm')
            or setup['capsuleHalfHeightCm']*2 != report.get('capsuleHeightCm')
            or not finite(setup.get('maxStepHeightCm')) or not 0 < setup['maxStepHeightCm'] <= 45
            or not finite(setup.get('walkableFloorZ')) or not .7 <= setup['walkableFloorZ'] <= 1
            or not finite(setup.get('minFloorDistanceCm')) or abs(setup['minFloorDistanceCm']-1.9) > .01
            or not finite(setup.get('maxFloorDistanceCm')) or abs(setup['maxFloorDistanceCm']-2.4) > .01
            or not isinstance(report.get('routeWidthSamples'), list)):
        raise ValueError('Complete full-width native capsule and floor evidence is required.')
    from citadel_collision_policy import validate_capsule_policy,validate_capsule_kinematics
    validate_capsule_policy(setup.get('capsuleCollisionPolicy'))
    validate_capsule_kinematics(setup.get('capsuleKinematicsPolicy'))
    kinematics=setup['capsuleKinematicsPolicy']
    if any(setup[header]!=kinematics[field] for header,field in (
            ('capsuleRadiusCm','scaledRadiusCm'),('capsuleHalfHeightCm','scaledHalfHeightCm'),
            ('maxStepHeightCm','maxStepHeightCm'),('walkableFloorZ','walkableFloorZ'))):
        raise ValueError('Full-width setup differs from its native capsule geometry and walking receipt.')
    checked_surface_report(setup, routes)
    actual = {}
    for row in report['routeWidthSamples']:
        if (not isinstance(row, dict) or not isinstance(row.get('id'), str)
                or type(row.get('segment')) is not int or type(row.get('sample')) is not int
                or not finite(row.get('lane')) or row['lane'] not in setup['laneFractions']):
            raise ValueError('Invalid full-width native sample identity.')
        key = (row['id'], row['segment'], row['sample'], row['lane'])
        if key in actual:
            raise ValueError('Duplicate full-width native sample.')
        actual[key] = row
    expected = 0
    for route in routes:
        previous = {}
        for segment,(a,b) in enumerate(zip(route['points'], route['points'][1:])):
            dx,dy = b[0]-a[0],b[1]-a[1]; distance = math.hypot(dx,dy)
            if distance < 1 or route['clearWidthCm'] <= 2*setup['capsuleRadiusCm']:
                raise ValueError('Full-width routes need physical walking segments and capsule clearance.')
            intervals = max(1, math.ceil(distance/setup['maxSpacingCm']))
            for sample in range(intervals+1):
                for lane in setup['laneFractions']:
                    expected += 1
                    row = actual.get((route['id'], segment, sample, lane), {})
                    alpha = sample/intervals; offset = lane*(route['clearWidthCm']/2-setup['capsuleRadiusCm'])
                    seed = width_seed(route, segment, alpha, lane, setup['capsuleRadiusCm'])
                    before = previous.get(lane)
                    steps = math.ceil(max(0, math.dist(seed[:2], before[:2])-.01)/setup['movementSpacingCm']) if before else 0
                    if (not finite(row.get('alpha')) or abs(row['alpha']-alpha) > .000001
                            or row.get('clearWidthCm') != route['clearWidthCm']
                            or not finite(row.get('lateralOffsetCm')) or abs(row['lateralOffsetCm']-offset) > .01
                            or not point(row.get('seed')) or any(abs(v-seed[i]) > 1 for i,v in enumerate(row['seed']))
                            or not point(row.get('center')) or math.dist(row['center'][:2],seed[:2]) > 1
                            or not point(row.get('floorImpact')) or not finite(row.get('floorZCm'))
                            or abs(row['floorImpact'][2]-row['floorZCm']) > .01
                            or row['center'][2]-row['floorZCm'] < setup['capsuleHalfHeightCm']-setup['capsuleRadiusCm']-.1
                            or row['center'][2]-row['floorZCm'] > setup['capsuleHalfHeightCm']+setup['maxStepHeightCm']+setup['maxFloorDistanceCm']+.1
                            or abs(row['floorZCm']-seed[2]) > setup['maxFloorDeviationCm']
                            or not finite(row.get('floorNormalZ')) or not setup['walkableFloorZ'] <= row['floorNormalZ'] <= 1.001
                            or not finite(row.get('floorDistanceCm'))
                            or not setup['minFloorDistanceCm']-.1 <= row['floorDistanceCm'] <= setup['maxFloorDistanceCm']+.1
                            or type(row.get('movementSteps')) is not int or row['movementSteps'] < steps
                            or any(row.get(key) is not True for key in ('floor','placementClear','transitionClear','passed'))
                            or type(row.get('stepAttempted')) is not bool or type(row.get('stepSucceeded')) is not bool
                            or row['stepAttempted'] and not row['stepSucceeded']):
                        raise ValueError('Blocked, ungrounded or displaced full-width route sample: '+route['id'])
                    from citadel_placement_evidence import validate_route_placement_overlaps
                    validate_route_placement_overlaps(row.get('placementOverlapEvidence'),None,setup['capsuleRadiusCm'],setup['capsuleHalfHeightCm'])
                    validate_route_placement_overlaps(row.get('movementOverlapEvidence'),row['movementSteps'],setup['capsuleRadiusCm'],setup['capsuleHalfHeightCm'])
                    previous[lane] = row['seed']
    if len(actual) != expected:
        raise ValueError('Unexpected or missing full-width native samples.')


def spawn_approach_routes(plan):
    from citadel_spawn_surface import gradient,validate_retained_surfaces
    approaches = plan.get('spawnApproaches', [])
    if plan.get('recipeVersion', 0) >= 5 or approaches:
        spawns = plan.get('teamSpawns', [])
        if (len(spawns) != 6 or len(approaches) != 6
                or {row.get('index') for row in approaches} != set(range(6))):
            raise ValueError('Every retained spawn needs one signed pad and approach.')
        for row in approaches:
            gradient(row,plan.get('recipeVersion',0))
            index, points, width = row['index'], row.get('points'), row.get('widthCm')
            if (type(index) is not int or not isinstance(points, list) or not points
                    or points[0] != spawns[index] or type(width) not in (int, float)
                    or not math.isfinite(width) or width < 600
                    or any(not isinstance(p, list) or len(p) != 3 or any(
                        type(v) not in (int, float) or not math.isfinite(v) for v in p) for p in points)):
                raise ValueError('Spawn pad differs from its anchor or has invalid clearance.')
            if index < 2:
                if row.get('preserveLowerCity') is not True or len(points) != 1:
                    raise ValueError('Lower-city spawn authoring must preserve the surveyed scene.')
                continue
            route = next((r for r in plan['routes'] if r['id'] == row.get('joinsRoute')), None)
            if not route or width > route['width'] or any(p[2] != points[0][2] for p in points):
                raise ValueError('Upper spawn approach needs a full-width ground route connection.')
            end, connected = points[-1], points[-1] in route['points']
            for a, b in zip(route['points'], route['points'][1:]):
                delta = [b[j]-a[j] for j in range(3)]
                squared = sum(v*v for v in delta)
                if not squared:
                    continue
                t = sum((end[j]-a[j])*delta[j] for j in range(3))/squared
                connected |= 0 <= t <= 1 and math.dist(end, [a[j]+delta[j]*t for j in range(3)]) < .01
            if not connected:
                raise ValueError('Spawn approach does not meet its declared playable route.')
        if plan.get('recipeVersion',0)>=6 and (plan.get('baseline') or {}).get('packageHashes'):
            validate_retained_surfaces(plan['baseline'],approaches,plan.get('spawnRelocations'),plan['recipeVersion'])
    return [dict(id='spawn_' + str(row['index']) + '_approach',
                 points=row['points'], width=row['widthCm'])
            for row in approaches if row['index'] >= 2 and len(row['points']) > 1]


def spawn_pad_proof(report, config, plan):
    from citadel_spawn_surface import gradient,seed as surface_seed
    pads = [dict(index=row['index'], point=row['points'][0], widthCm=row['widthCm'],
                 **({'groundGradient':gradient(row,plan.get('recipeVersion',0))} if 'groundGradient' in row else {}))
            for row in plan.get('spawnApproaches', [])]
    if config.get('spawnPads', []) != pads:
        raise ValueError('Native spawn pad configuration differs from retained anchors.')
    if not pads:
        return
    radius = report.get('capsuleRadiusCm')
    rows = report.get('spawnSamples')
    if (type(radius) not in (int, float) or not math.isfinite(radius) or radius <= 0
            or not isinstance(rows, list) or len(rows) != len(pads) * 25):
        raise ValueError('Native spawn pad clearance evidence is incomplete.')
    for pad in pads:
        selected = [row for row in rows if row.get('index') == pad['index']]
        coordinates = [(row.get('x'), row.get('y')) for row in selected]
        if len(selected) != 25 or len(set(coordinates)) != 25:
            raise ValueError('Native spawn pad samples are missing or duplicated.')
        edge = pad['widthCm'] / 2 - radius
        if edge <= 0:
            raise ValueError('Native capsule cannot fit the signed spawn pad.')
        for row in selected:
            x, y, seed = row.get('x'), row.get('y'), row.get('seed')
            if (type(x) is not int or type(y) is not int or not -2 <= x <= 2 or not -2 <= y <= 2
                    or row.get('clear') is not True or not isinstance(seed, list) or len(seed) != 3
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in seed)):
                raise ValueError('Native retained spawn pad is obstructed or malformed.')
            expected = surface_seed(pad['point'],x,y,edge,gradient(pad,plan.get('recipeVersion',0)))
            if any(abs(a-b) > .01 for a, b in zip(seed, expected)):
                raise ValueError('Native spawn pad sample differs from its signed footprint.')


def gate_config(gate, index, leaf, routes):
    result = dict(id=gate['id'] + ':' + str(index), index=gate['index'],
                  point=leaf['point'], width=leaf['width'], height=leaf['height'], sweepHalfSpanCm=400)
    approach = leaf.get('approachClearance')
    if not approach:
        return result
    fields = ('incomingFlatLengthCm', 'outgoingFlatLengthCm', 'maximumLeafHalfThicknessCm',
              'pedestrianCapsuleRadiusCm', 'requiredCapsuleFloorMarginCm', 'localSweepHalfSpanCm')
    if (any(type(approach.get(key)) not in (int, float) or not math.isfinite(approach[key])
            or approach[key] <= 0 for key in fields)
            or approach['pedestrianCapsuleRadiusCm'] < 42 or approach['requiredCapsuleFloorMarginCm'] < 3
            or approach.get('actualNativeStartClearanceRequired') is not True
            or approach.get('fullWidthRouteTraversalRequired') is not True):
        raise ValueError('Signed gate landing and native clearance checks are required.')
    flat = [0, 0]
    for route in routes:
        for point_index, point in enumerate(route['points']):
            if any(abs(a-b) > .01 for a, b in zip(point, leaf['point'])):
                continue
            for adjacent_index in (point_index-1, point_index+1):
                if not 0 <= adjacent_index < len(route['points']):
                    continue
                adjacent = route['points'][adjacent_index]
                if abs(adjacent[1]-point[1]) > .01 or abs(adjacent[2]-point[2]) > .01:
                    continue
                dx = adjacent[0]-point[0]
                if dx:
                    side = 0 if dx < 0 else 1
                    flat[side] = max(flat[side], abs(dx))
    span = min(400, *(distance-approach['pedestrianCapsuleRadiusCm']
                     -approach['requiredCapsuleFloorMarginCm'] for distance in flat))
    if (abs(flat[0]-approach['incomingFlatLengthCm']) > .01
            or abs(flat[1]-approach['outgoingFlatLengthCm']) > .01
            or abs(span-approach['localSweepHalfSpanCm']) > .01
            or span <= approach['maximumLeafHalfThicknessCm']+approach['pedestrianCapsuleRadiusCm']+3):
        raise ValueError('Gate sweep differs from its signed flat landing.')
    result.update(sweepHalfSpanCm=span, approachClearance=approach)
    return result


def gate_sweep_clearance(row, gate, radius):
    half, span = row.get('actualLeafHalfThicknessCm'), row.get('sweepHalfSpanCm')
    if (type(radius) not in (int, float) or not math.isfinite(radius) or radius < 42
            or type(half) not in (int, float) or not math.isfinite(half) or half <= 0
            or type(span) not in (int, float) or not math.isfinite(span)
            or abs(span-gate['sweepHalfSpanCm']) > .01
            or span <= radius+half+3
            or row.get('startClear') is not True or row.get('endClear') is not True):
        return False
    approach = gate.get('approachClearance')
    return not approach or (half <= approach['maximumLeafHalfThicknessCm']+.01
        and span+radius+approach['requiredCapsuleFloorMarginCm'] <= min(
            approach['incomingFlatLengthCm'], approach['outgoingFlatLengthCm'])+.01)


def route_proof(report, config, plan, city):
    routes = plan['routes'] + spawn_approach_routes(plan)
    profiles = checked_profiles(plan.get('routeSurfaceProfiles', SURFACE_ABSENT), routes)
    expected = {r['id'] + ':' + direction: (r, direction) for r in routes for direction in ('forward', 'reverse')}
    intended_routes = [dict(id=route['id'] + ':' + direction, points=route['points'] if direction == 'forward'
                           else list(reversed(route['points'])), clearWidthCm=route['width'],
                           **({'surfaceProfile':profiles[route['id']]} if route['id'] in profiles else {}))
                       for route in routes for direction in ('forward', 'reverse')]
    actual = {r['id']: r for r in report.get('completedRoutes', [])}
    anchors = [dict(id=kind + ':' + str(index), point=point, index=index, optional=kind == 'optional')
               for kind, points in (('main', plan.get('objectives', [])), ('optional', plan.get('optionalObjectives', [])))
               for index, point in enumerate(points)]
    if (len(plan.get('objectives', [])) != 8 or len(plan.get('optionalObjectives', [])) != 3
            or config.get('anchors') != anchors):
        raise ValueError('All eight main and three optional physical anchors must match the source plan.')
    leaves = [(g, i, leaf) for g in plan['gates'] for i, leaf in enumerate(g['leaves'])]
    intended_gates = [gate_config(gate, index, leaf, plan['routes'])
                      for gate, index, leaf in leaves]
    sweeps = report.get('gateSweeps', [])
    vertical_sweeps = report.get('gateVerticalSweeps', [])
    if (report.get('passed') is not True or report.get('diagnosticOnly') is True or report.get('signature') != plan['signature']
            or report.get('cityRevision') != city['city']['revision'] or report.get('map') != city['siegeMap']
            or report.get('mapSha256') != city['packageHashes'][city['siegeMap']]
            or report.get('routeFailures') != [] or report.get('physicalFailures') != [] or report.get('routesWalked') != len(expected)
            or len(report.get('completedRoutes', [])) != len(expected) or len(actual) != len(expected) or set(actual) != set(expected)
            or len(sweeps) != len(leaves) * 18 or len(vertical_sweeps) != len(leaves) * 18
            or config.get('signature') != plan['signature']
            or config.get('map') != city['siegeMap'] or config.get('routes') != intended_routes
            or config.get('gates') != intended_gates):
        raise ValueError('Complete physical routes and gate cuts need fresh native proof.')
    for key, (route, _) in expected.items():
        row = actual[key]
        distance = sum(math.dist(a[:2], b[:2]) for a, b in zip(route['points'], route['points'][1:]))
        walked = row.get('distanceCm')
        if (row.get('grounded') is not True or row.get('collisionEnabled') is not True
                or row.get('waypoints') != len(route['points']) or type(walked) not in (float, int)
                or not math.isfinite(walked) or walked < distance * .8):
            raise ValueError('Intended route traversal is incomplete: ' + key)
    route_width_proof(report, config['routes'])
    spawn_pad_proof(report, config, plan)
    by_key = {(r['id'], r['phase'], r['lane'], r['direction']): r for r in sweeps}
    gate_by_id = {row['id']: row for row in intended_gates}
    if len(by_key) != len(sweeps):
        raise ValueError('Duplicate physical gate evidence.')
    for gate, index, _ in leaves:
        for phase in range(3):
            closed = phase == 0 or (phase == 1 and gate['index'] == 1)
            for lane in (-1, 0, 1):
                for direction in (-1, 1):
                    row = by_key.get((gate['id'] + ':' + str(index), phase, lane, direction), {})
                    if (row.get('passed') is not True or row.get('closed') is not closed or row.get('blocked') is not closed
                            or not gate_sweep_clearance(row, gate_by_id[gate['id']+':'+str(index)], report.get('capsuleRadiusCm'))):
                        raise ValueError('A physical stage crossing leaks or obstructs traversal.')
    by_height = {(r['id'], r['phase'], r['level'], r['direction']): r for r in vertical_sweeps}
    if len(by_height) != len(vertical_sweeps):
        raise ValueError('Duplicate physical gate height evidence.')
    for gate, index, leaf in leaves:
        for phase in range(3):
            closed = phase == 0 or (phase == 1 and gate['index'] == 1)
            for level in (1, 2, 3):
                for direction in (-1, 1):
                    row = by_height.get((gate['id'] + ':' + str(index), phase, level, direction), {})
                    half, offset = row.get('capsuleHalfHeightCm'), row.get('centerOffsetCm')
                    if (row.get('passed') is not True or row.get('closed') is not closed
                            or row.get('blocked') is not closed or row.get('heightCm') != leaf['height']
                            or not gate_sweep_clearance(row, gate_by_id[gate['id']+':'+str(index)], report.get('capsuleRadiusCm'))
                            or type(half) not in (int, float) or not math.isfinite(half) or half <= 0
                            or leaf['height'] <= 2*half+6 or type(offset) not in (int, float) or not math.isfinite(offset)
                            or abs(offset-(half+3+(leaf['height']-2*half-6)*level/4)) > .01):
                        raise ValueError('A physical stage crossing leaks or obstructs above floor level.')
    samples = report.get('objectiveSamples')
    if not isinstance(samples, list) or len(samples) != len(anchors) * 8:
        raise ValueError('Objective floor and line-of-sight evidence is incomplete.')
    for anchor in anchors:
        positions = [sample for sample in samples if sample.get('id') == anchor['id']]
        spokes = [sample.get('spoke') for sample in positions]
        clear = [sample for sample in positions if sample.get('floor') is True
                 and sample.get('capsuleClear') is True and sample.get('lineOfSight') is True]
        if (len(positions) != 8 or any(type(spoke) is not int or not 0 <= spoke <= 7 for spoke in spokes)
                or len(set(spokes)) != 8 or len(clear) < 4):
            raise ValueError('Insufficient physically playable capture positions: ' + anchor['id'])


def native_view_proof(report, config, plan, city):
    """Bind clean native captures to the signed cameras, rather than PNG names alone."""
    finite = lambda v: type(v) in (int, float) and math.isfinite(v)
    point = lambda v: isinstance(v, list) and len(v) == 3 and all(finite(x) for x in v)
    signed = plan.get('reviewViews', [])
    views, actual = config.get('views', []), report.get('viewPerformance', [])
    if (not isinstance(signed, list) or len(signed) != len(VIEW_IDS)
            or {v.get('id') for v in signed} != set(VIEW_IDS)
            or not isinstance(views, list) or len(views) != len(VIEW_IDS)
            or {v.get('id') for v in views} != set(VIEW_IDS)
            or not isinstance(actual, list) or len(actual) != len(VIEW_IDS)
            or {v.get('id') for v in actual} != set(VIEW_IDS)
            or report.get('passed') is not True or report.get('views') != len(VIEW_IDS)
            or report.get('architectureUiSuppressed') is not True
            or report.get('physicalFailures') != [] or report.get('routeFailures') != []
            or report.get('visualApproved') is not False or report.get('releaseAcceptance') is not False):
        raise ValueError('Fresh native architectural views require verified UI suppression and complete camera receipts.')
    for value in (config, report):
        if (value.get('signature') != plan['signature'] or value.get('cityRevision') != city['city']['revision']
                or value.get('map') != city['siegeMap']
                or value.get('mapSha256') != city['packageHashes'][city['siegeMap']]):
            raise ValueError('Native architectural views are bound to another candidate.')
    for identity in VIEW_IDS:
        source = next(v for v in signed if v['id'] == identity)
        view = next(v for v in views if v['id'] == identity)
        row = next(v for v in actual if v['id'] == identity)
        eye, target, lens = source.get('eyeCm'), source.get('targetCm'), source.get('focalLengthMm')
        if (not point(eye) or not point(target) or not finite(lens) or not 12 <= lens <= 150
                or math.dist(eye, target) < 1):
            raise ValueError('Invalid signed native camera: ' + identity)
        fov = 2*math.atan(18/lens)*180/math.pi
        direction = [target[i]-eye[i] for i in range(3)]
        magnitude = math.sqrt(sum(v*v for v in direction))
        ortho = source.get('orthographicWidthCm')
        if (view.get('eye') != eye or view.get('target') != target
                or not finite(view.get('fieldOfView')) or abs(view['fieldOfView']-fov) > .000001
                or view.get('orthographicWidthCm') != ortho
                or not point(row.get('eye')) or any(abs(v-eye[i]) > 1 for i,v in enumerate(row['eye']))
                or not point(row.get('direction')) or any(abs(v-direction[i]/magnitude) > .001 for i,v in enumerate(row['direction']))
                or not finite(row.get('fieldOfView')) or abs(row['fieldOfView']-fov) > .01
                or row.get('projection') != ('perspective' if ortho is None else 'orthographic')
                or ortho is not None and (not finite(ortho) or not 100 <= ortho <= 100000
                   or not finite(row.get('orthographicWidthCm')) or abs(row['orthographicWidthCm']-ortho) > 1)
                or row.get('canvasHudHidden') is not True or row.get('viewportWidgetsCollapsed') is not True
                or any(type(row.get(key)) is not int or not 0 <= row[key] <= 1024
                       for key in ('canvasHudCount', 'viewportWidgetCount'))):
            raise ValueError('Native view differs from its signed camera or UI suppression is unverified: ' + identity)


def native_view_evidence(root, visual, plan, city):
    binding = visual.get('nativeViews', {})
    file = confined(root, binding.get('path'))
    setup = binding.get('config', {})
    config_file = confined(root, setup.get('path'))
    if digest(file) != binding.get('sha256') or digest(config_file) != setup.get('sha256'):
        raise ValueError('Native architectural view evidence changed.')
    native_view_proof(read(file), read(config_file), plan, city)
    for image in visual['views']:
        if confined(root, image['path']) != file.parent / (image['id'] + '.png'):
            raise ValueError('Reviewed capture must be the intended native proof output: ' + image['id'])


def publication_review(root, run, plan, city, staged):
    review = read(run / 'publication-review.json')
    hashes = {**city['packageHashes'], **staged['packageHashes']}
    if (review.get('schemaVersion') != 1 or review.get('revision') != plan['revision']
            or review.get('signature') != plan['signature'] or review.get('cityRevision') != city['city']['revision']
            or review.get('packageHashes') != hashes or review.get('unfinished') != []):
        raise ValueError('Publication review is missing, stale or unfinished.')
    verify_hashes(root, hashes)
    visual = review.get('visual', {})
    if (visual.get('reviewed') is not True or visual.get('referenceSha256') != plan['reference']['sha256']
            or not visual.get('reviewer') or not visual.get('assessment') or not visual.get('views')):
        raise ValueError('An explicit evidence-based visual assessment against the attached reference is required.')
    required_views = {'hero', 'front', 'top_down', 'central_plaza', 'grand_gate', 'west_balcony', 'east_balcony', 'commander_hall'}
    if ({image.get('id') for image in visual['views']} != required_views or len(visual['views']) != len(required_views)
            or len({image['path'] for image in visual['views']}) != len(required_views)):
        raise ValueError('Every intended native architectural view needs a distinct reviewed capture.')
    for image in visual['views']:
        if digest(confined(root, image['path'])) != image['sha256']:
            raise ValueError('Visual review capture changed.')
    native_view_evidence(root, visual, plan, city)
    reports = {}
    for key in PROOFS:
        if key == 'performance':
            from citadel_performance_evidence import performance_evidence
            reports[key],_ = performance_evidence(root,review.get('evidence',{}).get(key,{}),plan,city,confined,digest,read)
            continue
        binding = review.get('evidence', {}).get(key, {})
        file = confined(root, binding.get('path'))
        if digest(file) != binding.get('sha256'):
            raise ValueError('Native evidence changed: ' + key)
        report = read(file)
        if (report.get('passed') is not True or report.get('cityRevision') != city['city']['revision']
                or report.get('signature') != plan['signature'] or report.get('packageHashes') != hashes):
            raise ValueError('Native evidence is incomplete or bound to other packages: ' + key)
        reports[key] = report
    routes = reports['routes']
    config_binding = review['evidence']['routes']['config']
    config_file = confined(root, config_binding['path'])
    if digest(config_file) != config_binding['sha256']:
        raise ValueError('Route proof setup changed.')
    route_proof(routes, read(config_file), plan, city)
    for key in ('rules', 'scenario', 'liveCapital'):
        report = reports[key]
        if report.get('rulesVersion') != 2 or report.get('capacity') != 18 or report.get('objectiveCount') != 8 or report.get('optionalCount') != 3:
            raise ValueError('Full version-two 18v18 gameplay needs actual native acceptance: ' + key)
    if reports['network'].get('map') != staged['map'] or reports['network'].get('twoClientStreaming') is not True:
        raise ValueError('Revised live campaign needs actual multiplayer streaming acceptance.')
    if reports['evacuation'].get('protectedRecovery') is not True or reports['recovery'].get('characterRestored') is not True:
        raise ValueError('Native evacuation and character recovery are incomplete.')
    from citadel_recovery_evidence import recovery_evidence
    recovery_evidence(root, reports['recovery'].get('normalCharacterProcessRecovery', {}),
                      plan, city, staged, confined, digest, read)
    if reports['gm'].get('draftHashes') != staged.get('gmDraftHashes', {}):
        raise ValueError('Rebased owner drafts need actual native import acceptance.')
    return review, reports


class Journal:
    def __init__(self, root, run, phase):
        self.root, self.run = root, run
        self.pending = run / (phase + '-pending.json')
        if self.pending.exists():
            raise ValueError('An interrupted operation requires journal recovery: ' + str(self.pending))
        self.value = dict(phase=phase, backups={}, created=[], complete=False)
        write(self.pending, self.value)

    def backup(self, file):
        key = file.relative_to(self.root).as_posix()
        if key not in self.value['backups']:
            target = self.run / 'publication-backup' / key
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and digest(target) != digest(file):
                raise ValueError('Preserve changed publication input: ' + key)
            shutil.copy2(file, target)
            self.value['backups'][key] = digest(file)
            write(self.pending, self.value)

    def created(self, package):
        self.value['created'].append(package)
        write(self.pending, self.value)

    def complete(self):
        self.value['complete'] = True
        write(self.run / (self.value['phase'] + '-journal.json'), self.value)
        self.pending.unlink()


def native_actor_hidden(actor):
    """Read runtime visibility through the reflected Actor property API."""
    hidden = actor.get_editor_property('hidden')
    if type(hidden) is not bool:
        raise ValueError('Native actor visibility must be a reflected boolean')
    return hidden


def native_anchor_contains(anchor, point):
    """Read reflected native bounds through the Editor property API."""
    origin = anchor.get_editor_property('zone_origin')
    extent = anchor.get_editor_property('half_size')
    if (type(extent) not in (int, float) or not math.isfinite(extent) or extent <= 0
            or any(not math.isfinite(v) for v in (origin.x, origin.y, origin.z))):
        raise ValueError('Native campaign anchor bounds are invalid')
    return abs(point[0]-origin.x) <= extent and abs(point[1]-origin.y) <= extent


def require_frontend_source_owner(assets, source):
    if (not source or source.get_path_name() != FRONTEND+'.CapitalPresentation'
            or source.get_class().get_name() != 'WarFrontendPresentationDefinition'
            or assets.get_metadata_tag(source, 'WarFrontendOwner') != 'cinematic-frontend-v1'):
        raise ValueError('Exact frontend source ownership differs.')
    return 'cinematic-frontend-v1'


def bind_frontend_candidate_owner(assets, source, target, prefix):
    """DuplicateAsset omits package metadata; carry only verified source ownership."""
    owner = require_frontend_source_owner(assets, source)
    if (not re.fullmatch('/Game/WorldRebuild/AegisCitadel_[a-f0-9]{12}', prefix)
            or not target or target.get_class().get_name() != 'WarFrontendPresentationDefinition'
            or target.get_path_name() != prefix+'/CapitalPresentationCandidate.CapitalPresentationCandidate'
            or assets.get_metadata_tag(target, 'WarFrontendOwner') not in ('', owner)):
        raise ValueError('Preserve an unrelated or differently owned frontend candidate.')
    assets.set_metadata_tag(target, 'WarFrontendOwner', owner)
    if assets.get_metadata_tag(target, 'WarFrontendOwner') != owner:
        raise ValueError('Verified frontend ownership did not survive native readback.')
    return dict(source=source.get_path_name(), candidate=target.get_path_name(), owner=owner)


def prepare(root, run, plan, city, current):
    import unreal
    from shared_city_authoring import load, own, save, detach, world
    from world_actor_state import snapshot
    build, manifest, manifest_file = routing(root)
    receipt = run / 'publication-candidate.json'
    if receipt.exists():
        staged = read(receipt)
        verify_hashes(root, staged['packageHashes'])
        verify_hashes(root, staged['sourceHashes'], protected_sources=True)
        return staged
    assets = unreal.EditorAssetLibrary
    prefix = '/Game/WorldRebuild/AegisCitadel_' + plan['revision']
    packages = dict(map=prefix + '/CampaignCandidate', layer=prefix + '/CampaignRoutingCandidate',
                    overlay=prefix + '/CampaignSiegeOverlay', frontend=prefix + '/CapitalPresentationCandidate')
    require_frontend_source_owner(assets, assets.load_asset(FRONTEND))
    journal = Journal(root, run, 'publication-prepare')
    sources = {p: digest(package_file(root, p)) for p in (build['map'], build['layer'], SIEGE, FRONTEND)}
    for file in (root / 'artifacts/unreal/world-portals/build.json', manifest_file, root / RECEIPT):
        journal.backup(file)
    for source, target in ((build['map'], packages['map']), (build['layer'], packages['layer']),
                           (city['siegeMap'], packages['overlay']), (FRONTEND, packages['frontend'])):
        if assets.does_asset_exist(target):
            raise ValueError('Preserve existing or failed candidate package: ' + target)
        journal.created(target)
        if not assets.duplicate_asset(source, target):
            raise ValueError('Candidate duplication failed: ' + target)
    load(packages['overlay'])
    for level in list(unreal.EditorLevelUtils.get_levels(world())):
        package = level.get_outer().get_path_name().split('.')[0]
        if package != packages['overlay']:
            detach(package)
    fields = [a for a in own(packages['overlay']) if isinstance(a, unreal.WarSiegeBattlefield)]
    if len(fields) != 1 or fields[0].get_editor_property('definition_version') != 2:
        raise ValueError('One complete version-two live gameplay overlay is required.')
    fields[0].set_editor_property('live_capital_overlay', True)
    if any(isinstance(a, (unreal.WarZoneAnchor, unreal.WarZonePortal, unreal.WarCityNpc, unreal.WarQuestNpc))
           for a in own(packages['overlay'])):
        raise ValueError('Live siege overlay duplicates campaign anchors, portals or services.')
    save(packages['overlay'])
    load(packages['layer'])
    before = {a.get_name(): snapshot(a) for a in own(packages['layer'])}
    anchors = [a for a in own(packages['layer']) if isinstance(a, unreal.WarZoneAnchor)]
    matches = [a for a in anchors if str(a.get_editor_property('zone_id')) == 'aegis_capital']
    if len(matches) != 1:
        raise ValueError('A unique retained Aegis routing anchor is required.')
    anchor = matches[0]
    origin = anchor.get_editor_property('zone_origin')
    if [origin.x, origin.y, origin.z] != city['city']['origin']:
        raise ValueError('Candidate city origin differs from live routing.')
    old_definition = anchor.get_editor_property('city_definition')
    if (not old_definition or old_definition.get_path_name().split('.')[0] != current['definition']
            or list(map(str, anchor.get_editor_property('content_levels'))) != current['gameplayLevels']):
        raise ValueError('Retained campaign anchor bindings changed after the survey.')
    extent = anchor.get_editor_property('half_size')
    for point in plan['objectives'] + plan['optionalObjectives'] + plan['teamSpawns'] + [p for r in plan['routes'] for p in r['points']]:
        containing = [a for a in anchors if native_anchor_contains(a, point)]
        if containing != [anchor] or abs(point[0] - origin.x) > extent or abs(point[1] - origin.y) > extent:
            raise ValueError('A citadel gameplay anchor falls outside unique Aegis bounds.')
    anchor.set_editor_property('city_definition', assets.load_asset(city['city']['definition']))
    anchor.set_editor_property('content_levels', [*current['gameplayLevels'], packages['overlay']])
    if before != {a.get_name(): snapshot(a) for a in own(packages['layer'])}:
        raise ValueError('Unrelated authored routing actor state changed.')
    save(packages['layer'])
    load(packages['map'])
    before = {a.get_name(): snapshot(a) for a in own(packages['map'])}
    for package in [build['layer'], *current['sceneryLevels']]:
        if not unreal.GameplayStatics.get_streaming_level(world(), package):
            raise ValueError('Original campaign attachment is missing: ' + package)
        detach(package)
    if not unreal.EditorLevelUtils.add_level_to_world(world(), packages['layer'], unreal.LevelStreamingAlwaysLoaded):
        raise ValueError('Cannot attach retained routing candidate.')
    for package in [*city['sceneryLevels'], packages['overlay']]:
        stream = unreal.EditorLevelUtils.add_level_to_world(world(), package, unreal.LevelStreamingDynamic)
        if not stream:
            raise ValueError('Cannot attach revised city layer: ' + package)
        stream.set_editor_property('initially_loaded', False)
        stream.set_editor_property('initially_visible', False)
    if before != {a.get_name(): snapshot(a) for a in own(packages['map'])}:
        raise ValueError('Persistent campaign actors changed.')
    portals = sorted(str(a.get_editor_property('route_id')) for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                     if isinstance(a, unreal.WarZonePortal))
    zones = sorted(str(a.get_editor_property('zone_id')) for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                   if isinstance(a, unreal.WarZoneAnchor))
    if portals != sorted(build['portals']) or zones != sorted(build['zones']):
        raise ValueError('Campaign portal or zone identities changed.')
    for p in current['gameplayLevels']:
        if not unreal.GameplayStatics.get_streaming_level(world(), p):
            raise ValueError('Retained capital service gameplay attachment is missing: ' + p)
    save(packages['map'])
    # Update only the city reference; existing cameras, palette and studio materials survive.
    frontend = assets.load_asset(packages['frontend'])
    frontend_ownership = bind_frontend_candidate_owner(assets, assets.load_asset(FRONTEND), frontend, prefix)
    cities = list(frontend.get_editor_property('cities'))
    selected = [c for c in cities if str(c.get_editor_property('zone_id')) == 'aegis_capital']
    if len(selected) != 1:
        raise ValueError('A unique frontend Aegis presentation is required.')
    selected[0].set_editor_property('city_definition', assets.load_asset(city['city']['definition']))
    frontend.set_editor_property('cities', cities)
    if not assets.save_loaded_asset(frontend, False):
        raise ValueError('Cannot save frontend candidate.')
    verify_hashes(root, city['sourceHashes'], protected_sources=True)
    updated = copy.deepcopy(manifest)
    capital = next(z for z in updated['zones'] if z['id'] == 'aegis_capital')
    capital.update(cityDefinition=city['city']['definition'], cityRevision=city['city']['revision'],
                   levels={**{f'scenery_{i}': p for i, p in enumerate(city['sceneryLevels'])},
                           **{f'gameplay_{i}': p for i, p in enumerate(current['gameplayLevels'])},
                           'live_siege': packages['overlay']}, citadelRevision=plan['revision'])
    updated.update(layer=packages['layer'], mainMap=packages['map'], mainSha256=digest(package_file(root, packages['map'])))
    for p in [build['layer'], *current['sceneryLevels']]:
        updated['packageHashes'].pop(p, None)
    updated['packageHashes'].update({p: digest(package_file(root, p)) for p in [packages['layer'], *city['sceneryLevels'], packages['overlay']]})
    proposed_build = copy.deepcopy(build)
    proposed_build.update(map=packages['map'], layer=packages['layer'], capitalSha256After=updated['mainSha256'], runtimeTraversalVerified=False)
    staged = dict(schemaVersion=1, revision=plan['revision'], **packages, baseBuild=build, baseManifest=manifest,
                  manifest=updated, build=proposed_build, packageHashes={p: digest(package_file(root, p)) for p in packages.values()},
                  sourceHashes=sources, frontendOwnership=frontend_ownership, gmDraftHashes={}, gmDrafts={}, published=False)
    # Rebase only the active world's documents. Historical Crownward drafts stay untouched.
    directory = root / 'unreal/AegisWar/Saved/WorldEdit'
    active = directory / build['map'].split('/')[-2] if '/WorldRebuild/DutchBastion_' in build['map'] else directory
    documents = list(active.glob('draft.json')) + list(active.glob(build['map'].split('/')[-1] + '-*-live.json'))
    load(city['map'])
    proposed = []
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if not actor.actor_has_tag('WarCapitalBuilding'):
            continue
        ids = [str(t)[15:] for t in actor.tags if str(t).startswith('WarWorldObject_')]
        hashes = [str(t)[15:] for t in actor.tags if str(t).startswith('WarModelSha256_')]
        mesh = actor.static_mesh_component.static_mesh if isinstance(actor, unreal.StaticMeshActor) else None
        if len(ids) != 1 or len(hashes) != 1 or not mesh:
            raise ValueError('Authored GM identity/model provenance is incomplete.')
        pose = actor.get_actor_transform()
        t, q, scale = pose.translation, pose.rotation, pose.scale3d
        proposed.append(dict(id=ids[0], hidden=native_actor_hidden(actor), sourceIdentity=mesh.get_path_name() + ':' + hashes[0],
                             transform=[t.x, t.y, t.z, q.x, q.y, q.z, q.w, scale.x, scale.y, scale.z]))
    for file in documents:
        key = file.relative_to(root).as_posix()
        journal.backup(file)
        target = run / 'gm-rebased' / file.name
        write(target, rebase_draft(read(file), proposed))
        staged['gmDrafts'][key] = dict(sourceSha256=digest(file), file=target.relative_to(root).as_posix())
        staged['gmDraftHashes'][key] = digest(target)
    verify_hashes(root, sources)
    write(receipt, staged)
    journal.complete()
    return staged


def publish(root, run, plan, city, current, staged):
    import unreal
    review, proofs = publication_review(root, run, plan, city, staged)
    build, manifest, manifest_file = routing(root)
    if source_plan(root)['cities'][0] != current:
        raise ValueError('Original shared city changed after candidate preparation.')
    verify_hashes(root, staged['sourceHashes'], protected_sources=True)
    merged_build = merge_manifest(staged['baseBuild'], staged['build'], build, 'build')
    merged_manifest = merge_manifest(staged['baseManifest'], staged['manifest'], manifest)
    assets = unreal.EditorAssetLibrary
    config = root / 'unreal/AegisWar/Config/DefaultEngine.ini'
    frontend_receipt = root / 'artifacts/unreal/frontend/build.json'
    siege_receipt = root / 'artifacts/unreal/scenario-queues/capital-scenery.json'
    approval = root / 'artifacts/unreal/citadel-siege/full-siege-approval.json'
    settings_before = config.read_bytes()
    settings = settings_before
    for key in (b'GameDefaultMap=', b'EditorStartupMap='):
        old = key + build['map'].encode()
        if settings.count(old) != 1:
            raise ValueError('Startup map configuration changed.')
        settings = settings.replace(old, key + staged['map'].encode())
    destinations = proofs['gm'].get('draftDestinations', {})
    gm_outputs = []
    for original, row in staged.get('gmDrafts', {}).items():
        if digest(confined(root, original)) != row['sourceSha256']:
            raise ValueError('Owner draft changed during review; rebase and repeat native GM proof.')
        target = confined(root, destinations.get(original))
        target.relative_to(root / 'unreal/AegisWar/Saved/WorldEdit' / ('AegisCitadel_' + plan['revision']))
        source = confined(root, row['file'])
        if digest(source) != staged['gmDraftHashes'][original] or (target.exists() and digest(target) != digest(source)):
            raise ValueError('Preserve changed rebased or independently edited candidate GM document.')
        gm_outputs.append((source, target))
    new_city = copy.deepcopy(city['city'])
    new_city['gameplayLevels'] = [*current['gameplayLevels'], staged['overlay']]
    new_city['packageHashes'].update({p: current['packageHashes'][p] for p in current['gameplayLevels']})
    new_city['packageHashes'][staged['overlay']] = staged['packageHashes'][staged['overlay']]
    receipt = read(root / RECEIPT)
    receipt.update(campaignMap=staged['map'], campaignHashes={p: staged['packageHashes'][p] for p in (staged['map'], staged['layer'])}, releaseApproved=False)
    receipt['cities'][0] = new_city
    journal = Journal(root, run, 'publication')
    for file in [config, manifest_file, root / 'artifacts/unreal/world-portals/build.json', root / RECEIPT,
                 frontend_receipt, siege_receipt, approval]:
        if file.exists():
            journal.backup(file)
    for package in (SIEGE, FRONTEND):
        file = package_file(root, package)
        journal.backup(file)
        for suffix in ('.uexp', '.ubulk', '.uptnl'):
            sidecar = file.with_suffix(suffix)
            if sidecar.exists():
                journal.backup(sidecar)
    for _, target in gm_outputs:
        if target.exists():
            journal.backup(target)
        else:
            journal.value.setdefault('createdFiles', []).append(target.relative_to(root).as_posix())
            write(journal.pending, journal.value)
    # Asset rename/copy changes serialized package identities: exact final proofs are invalidated below.
    if not assets.delete_asset(SIEGE) or not assets.duplicate_asset(city['siegeMap'], SIEGE):
        raise ValueError('Scenario overlay replacement failed; recover from publication journal.')
    if not assets.delete_asset(FRONTEND) or not assets.duplicate_asset(staged['frontend'], FRONTEND):
        raise ValueError('Frontend binding replacement failed; recover from publication journal.')
    verify_hashes(root, {p: h for p, h in {**city['sourceHashes'], **staged['sourceHashes']}.items()
                        if p not in (SIEGE, FRONTEND)}, protected_sources=True)
    # Native proof supplies actual CRC-derived live-document destinations; Python never guesses them.
    for source, target in gm_outputs:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    if config.read_bytes() != settings_before:
        raise ValueError('Configuration changed during publication; recover journal before retrying.')
    write_bytes(config, settings)
    write(manifest_file, merged_manifest)
    write(root / 'artifacts/unreal/world-portals/build.json', merged_build)
    write(root / RECEIPT, receipt)
    write(siege_receipt, dict(version=2, revision=new_city['revision'], cityDefinition=new_city['definition'], layers=new_city['sceneryLevels'],
                             map=SIEGE, mapSha256=digest(package_file(root, SIEGE)), navigationVerified=False, visualVerified=False))
    write(approval, dict(version=1, rulesVersion=2, revision=new_city['revision'], capacity=18, objectiveCount=8, optionalCount=3,
                         battlefieldDefinitionVersion=2, published=False, admissionApproved=False,
                         reason='Final canonical overlay/frontend packages require fresh native proof after publication.'))
    # The existing frontend receipt cannot certify a different binding. Generate freshness metadata only.
    outputs = read(frontend_receipt)['outputPackages'] if frontend_receipt.exists() else {}
    outputs[FRONTEND] = digest(package_file(root, FRONTEND))
    write(frontend_receipt, dict(schemaVersion=3, asset=FRONTEND + '.CapitalPresentation', sourcePlan=source_plan(root),
                                outputPackages=outputs, sourceMapsModified=False, visualApproved=False, licenseApprovalChanged=False))
    source_plan(root)
    staged.update(published=True, review=review, finalHashes={p: digest(package_file(root, p)) for p in (SIEGE, FRONTEND)},
                  finalPackageAdmissionApproved=False)
    write(run / 'publication-candidate.json', staged)
    journal.complete()
    return staged


def main():
    current = read(ROOT / 'artifacts/unreal/aegis-citadel/current.json')
    if not re.fullmatch('[a-f0-9]{12}', current.get('revision', '')):
        raise ValueError('An exact citadel revision is required.')
    run = ROOT / 'artifacts/unreal/aegis-citadel' / current['revision']
    existing = run / 'publication-candidate.json'
    if existing.exists() and read(existing).get('published') is True:
        staged = read(existing)
        verify_hashes(ROOT, staged['finalHashes'])
        if source_plan(ROOT)['campaignMap'] != staged['map']:
            raise ValueError('The published campaign binding changed.')
        print('WAR_CITADEL_PUBLICATION=' + json.dumps(dict(revision=current['revision'], published=True,
              finalPackageAdmissionApproved=False, alreadyPublished=True)))
        return
    plan, city, previous = candidate(ROOT, run)
    phase = os.environ.get('WAR_CITADEL_PUBLISH_STAGE', 'validate')
    if phase == 'prepare':
        result = prepare(ROOT, run, plan, city, previous)
    elif phase == 'publish':
        result = publish(ROOT, run, plan, city, previous, read(run / 'publication-candidate.json'))
    elif phase == 'validate':
        staged = read(run / 'publication-candidate.json')
        publication_review(ROOT, run, plan, city, staged)
        result = dict(ready=True, published=False, revision=plan['revision'])
    else:
        raise ValueError('WAR_CITADEL_PUBLISH_STAGE must be validate, prepare or publish.')
    print('WAR_CITADEL_PUBLICATION=' + json.dumps(dict(revision=plan['revision'], stage=phase,
          published=result.get('published', False), finalPackageAdmissionApproved=False)))


if __name__ == '__main__':
    main()
