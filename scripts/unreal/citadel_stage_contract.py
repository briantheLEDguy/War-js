"""Saved-world invariants shared by private citadel staging and bounded repair."""
import hashlib
import json
import math
import struct

REVIEW_START_CM=[15300,0,4310]
SOURCE_TRIANGLE_CONVENTION='counter_clockwise_cross_aligned_with_outward_normals'
NATIVE_IMPORT_CONVENTION=dict(schemaVersion=1,sourceTriangleWinding=SOURCE_TRIANGLE_CONVENTION,
    nativeTriangleWinding='clockwise_cross_opposed_to_outward_normals',normalPolicy='preserve_outward_source_normals')
NATIVE_MESH_BUILD_SETTINGS=dict(recompute_normals=False,recompute_tangents=True,use_mikk_t_space=True,
    compute_weighted_normals=False,generate_lightmap_u_vs=True,src_lightmap_index=0,dst_lightmap_index=1,
    min_lightmap_resolution=64,use_full_precision_u_vs=True,use_high_precision_tangent_basis=True)
OVERLAY_LIGHT_FIXTURES={
    'DirectionalLight_0':dict(klass='DirectionalLight',label='Siege daylight'),
    'SkyLight_0':dict(klass='SkyLight',label='Siege ambient sky')}


def expected_overlay_light(name,state):
    expected=OVERLAY_LIGHT_FIXTURES.get(name)
    return bool(expected and state['class']==expected['klass'] and state['label']==expected['label']
                and 'WarSiegeLighting' in state['tags'])


def expected_shared_lighting_fixture(spec,name,state,source_package=None):
    if spec.get('id'):
        return bool((source_package is None or source_package==spec['package'])
            and name==spec['actor'] and state['class']==spec['klass'] and state['label']==spec['label']
            and spec['requiredTag'] in state['tags'])
    return bool(name==spec['actor'] and state['class']==spec['klass'] and state['label']==spec['label']
        and 'WarZoneObject_aegis_capital_'+name in state['tags'])


def native_lighting_value(spec):
    import unreal
    if not isinstance(spec,dict):return spec
    if spec['kind']=='enum':return getattr(getattr(unreal,spec['type']),spec['value'])
    constructors={'color':unreal.Color,'linear_color':unreal.LinearColor,'vector4':unreal.Vector4}
    # FColor's reflected positional order is BGRA, unlike FLinearColor's RGBA.
    # Named channels preserve the signed order without a color-space conversion.
    names=('x','y','z','w') if spec['kind']=='vector4' else ('r','g','b','a')
    return constructors[spec['kind']](**dict(zip(names,spec['value'])))


def lighting_readback(value,wanted):
    """Require actual reflected values; record primitives without wrapper addresses."""
    if isinstance(wanted,dict):
        if wanted['kind']=='enum':
            token=wanted['type']+'.'+wanted['value']
            if token not in str(value):raise ValueError('Native lighting enum did not match '+token)
            return token
        keys=('x','y','z','w') if wanted['kind']=='vector4' else ('r','g','b','a')
        actual=[getattr(value,k) for k in keys]
        if any(abs(a-b)>1e-5 for a,b in zip(actual,wanted['value'])):
            raise ValueError('Native lighting color/vector did not retain its signed values')
        return actual
    if isinstance(wanted,bool):
        if value is not wanted:raise ValueError('Native lighting boolean changed')
    elif abs(value-wanted)>max(1e-5,abs(wanted)*1e-6):
        raise ValueError('Native lighting numeric property changed')
    return value


def checked_lighting_exposure(treatment,extended_ev100):
    """Luminance settings must agree with the actual project exposure mode."""
    if (treatment.get('exposureUnits')!='native_luminance'
            or treatment.get('expectedExtendedEV100') is not False or extended_ev100 is not False):
        raise ValueError('Signed native-luminance exposure requires the actual legacy luminance mode')
    return extended_ev100


def checked_render_audit(audit,mesh_path):
    """Only actual built buffers establish render UV/normal availability."""
    if not audit.get('readOnly') or not audit.get('available') or audit.get('mesh')!=mesh_path:
        raise ValueError('Native render-buffer audit unavailable or belongs to another mesh')
    lods=audit.get('lods',[])
    if not lods or {row.get('lod') for row in lods}!=set(range(len(lods))):
        raise ValueError('Incomplete native render LOD audit')
    for row in lods:
        if not row.get('cpuReadable') or row.get('vertices',0)<=0 or row.get('uvChannels',0)<=0 or row.get('indices',0)<=0:
            raise ValueError('Native render LOD has unavailable positions, normals or UVs')
        if any(row.get(key)!=0 for key in ('invalidPositions','invalidNormals','nonUnitNormals','invalidUVs')):
            raise ValueError('Native render LOD has invalid position/normal/UV data')
        basis=row.get('tangentBasis',{});vertices=row['vertices']
        if (basis.get('version')!=1 or basis.get('diagnosticOnly') is not True or basis.get('highPrecision') is not True
                or basis.get('basisSource')!='actual_render_buffer_x_z_and_native_reconstructed_y'
                or basis.get('invalidVertices')!=0 or basis.get('orthogonalVertices')!=vertices
                or basis.get('badVertexSamples')!=[] or basis.get('badVertexSampleLimit')!=64
                or basis.get('badVertexSamplesTruncated') is not False
                or basis.get('sampleComponentPolicy')!='actual_buffer_values_nonfinite_as_null'):
            raise ValueError('Native render LOD has unavailable or invalid actual tangent basis')
        def float32(value):return struct.unpack('f',struct.pack('f',value))[0]
        if (basis.get('nearZeroComponentTolerance')!=float32(1e-4)
                or basis.get('orthogonalityAbsoluteNormalizedDotTolerance')!=float32(.02)):
            raise ValueError('Native tangent audit used unknown or weakened thresholds')
        for axis in ('x','y','z'):
            data=basis.get('axes',{}).get(axis,{})
            unit_tolerance=float32(.04 if axis=='y' else .02)
            if (any(data.get(key)!=vertices for key in ('finite','unit'))
                    or any(data.get(key)!=0 for key in ('nonFinite','nearZero','nonUnit'))
                    or data.get('unitSquaredTolerance')!=unit_tolerance):
                raise ValueError('Native render LOD tangent axis is invalid')
            low,high=data.get('minimumLength'),data.get('maximumLength')
            if (not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (low,high))
                    or low>high or low<math.sqrt(1-unit_tolerance)-1e-6
                    or high>math.sqrt(1+unit_tolerance)+1e-6):
                raise ValueError('Native render LOD tangent lengths contradict unit counters')
        for pair in ('xy','xz','yz'):
            data=basis.get('pairs',{}).get(pair,{})
            if (any(data.get(key)!=vertices for key in ('evaluated','orthogonal'))
                    or any(data.get(key)!=0 for key in ('skipped','nonOrthogonal'))):
                raise ValueError('Native render LOD tangent axes are not orthogonal')
            maximum=data.get('maximumAbsoluteNormalizedDot')
            if (not isinstance(maximum,(int,float)) or not math.isfinite(maximum)
                    or not 0<=maximum<=float32(.02)):
                raise ValueError('Native render LOD tangent dot contradicts orthogonality counters')
    base=next(row for row in lods if row['lod']==0)
    if (base.get('committedSourcePositionMissing')!=0 or base.get('committedSourceNormalDifferent')!=0
            or base.get('committedSourceNormalMatches')!=base['vertices']):
        raise ValueError('Actual LOD0 normals differ from committed authored source')
    if (base.get('sourceMatchingPolicy')!='oriented_triangle_corners_material_and_uv0'
            or base['indices']%3 or base.get('committedSourceTriangleMatches')!=base['indices']//3
            or base.get('committedSourceTrianglesMissing')!=0 or base.get('committedSourceTrianglesDifferent')!=0):
        raise ValueError('Actual LOD0 triangle corners, materials or UVs differ from authored source')
    thresholds=dict(sourcePositionToleranceCm=.1,sourceNormalDotThreshold=.995,
        sourceUvAbsoluteTolerance=.0005,sourceUvRelativeTolerance=.001)
    if any(base.get(key)!=value for key,value in thresholds.items()):
        raise ValueError('Native source matching used unknown or weakened thresholds')
    return audit


def source_array_sha256(mesh_json,key):
    """Bind exact array source bytes, avoiding Python/JS float reserialization."""
    marker='"'+key+'":'
    if mesh_json.count(marker)!=1:raise ValueError('Missing or duplicate authored mesh array')
    start=mesh_json.index(marker)+len(marker)
    while mesh_json[start].isspace():start+=1
    value,end=json.JSONDecoder().raw_decode(mesh_json[start:])
    if not isinstance(value,list):raise ValueError('Authored mesh member is not an array')
    return hashlib.sha256(mesh_json[start:start+end].encode()).hexdigest()


def checked_terrain_render_audit(audit,mesh_path,source_lods,comparison,rendered_comparison):
    """Check inherited terrain buffers without assigning the citadel's LOD policy."""
    lods=audit.get('lods',[])
    if (audit.get('readOnly') is not True or audit.get('available') is not True
            or audit.get('mesh')!=mesh_path or len(lods)!=source_lods
            or [row.get('lod') for row in lods]!=list(range(source_lods))):
        raise ValueError('Actual saved terrain render LODs are incomplete')
    for row in lods:
        vertices,indices,basis=row.get('vertices'),row.get('indices'),row.get('tangentBasis',{})
        if (row.get('cpuReadable') is not True or type(vertices) is not int or vertices<=0
                or type(indices) is not int or indices<=0 or indices%3
                or type(row.get('uvChannels')) is not int or row['uvChannels']<comparison['uvChannels']
                or any(row.get(key)!=0 for key in ('invalidPositions','invalidNormals','nonUnitNormals','invalidUVs'))
                or basis.get('invalidVertices')!=0 or basis.get('orthogonalVertices')!=vertices):
            raise ValueError('Actual saved terrain render attributes are invalid or unavailable')
    if (rendered_comparison.get('nativeExteriorRenderPreserved') is not True
            or rendered_comparison.get('nativeExteriorComputedBasisPreserved') is not True
            or rendered_comparison.get('committedTopologyComparisonRequired') is not True
            or rendered_comparison.get('targetMesh')!=mesh_path
            or rendered_comparison.get('cloneTriangles')!=comparison['referencedTriangles']
            or lods[0]['indices']//3!=comparison['referencedTriangles']):
        raise ValueError('Actual original/clone exterior rendered preservation is missing')
    return audit


def native_triangle_indices(mesh,source_convention):
    """Adapt Blender faces at the Unreal boundary; never change source geometry.

    Unreal's native terrain control uses clockwise top faces with +Z normals.
    Recast uses that winding even with double-sided collision. Checking every
    face prevents unknown/mixed sources from silently producing underside nav.
    """
    if source_convention!=SOURCE_TRIANGLE_CONVENTION:
        raise ValueError('Unknown source triangle convention')
    points,normals,indices=mesh['positions'],mesh['normals'],mesh['indices']
    if len(points)!=len(normals) or not indices or len(indices)%3:
        raise ValueError('Invalid source triangle arrays')
    if any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in [*points,*normals]):
        raise ValueError('Invalid source position/normal')
    result=[]
    for offset in range(0,len(indices),3):
        a,b,c=indices[offset:offset+3]
        if any(type(i) is not int or not 0<=i<len(points) for i in (a,b,c)):
            raise ValueError('Invalid source triangle index')
        ab=[points[b][i]-points[a][i] for i in range(3)]
        ac=[points[c][i]-points[a][i] for i in range(3)]
        cross=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        if sum(v*v for v in cross)<1e-12 or any(
                sum(cross[i]*normals[j][i] for i in range(3))<=0 for j in (a,b,c)):
            raise ValueError('Source faces do not consistently match declared outward normals')
        result.extend((a,c,b))
    return result


def proof_start_position(plan):
    floor=plan['teamSpawns'][1]
    return [floor[0],floor[1],floor[2]+96+3]


def checked_private_proof_start(world,package,plan,actor_subsystem,owned_actors):
    """Give direct native review a safe start without moving campaign spawns."""
    import unreal
    floor=plan['teamSpawns'][1];point=proof_start_position(plan)
    starts=[a for a in owned_actors if a.get_class().get_name()=='PlayerStart']
    tagged=[a for a in starts if 'WarDutchProofStart' in [str(t) for t in a.tags]]
    if len(tagged)>1:raise RuntimeError('Ambiguous private proof start')
    if tagged and math.dist([getattr(tagged[0].get_actor_location(),axis) for axis in ('x','y','z')],point)>.1:
        raise RuntimeError('Preserve independently moved private proof start')
    hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(floor[0],floor[1],floor[2]+80),
        unreal.Vector(floor[0],floor[1],floor[2]-150),unreal.TraceTypeQuery.ECC_VISIBILITY,
        True,starts,unreal.DrawDebugTrace.NONE,True)
    values=hit.to_tuple() if hit else None
    if not values or not values[0] or abs(values[5].z-floor[2])>15 or values[7].z<.7:
        raise RuntimeError('Signed private proof start has no valid actual floor')
    center=unreal.Vector(*point)
    hit=unreal.SystemLibrary.capsule_trace_single(world,center,center+unreal.Vector(0,0,1),42,96,
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,starts,unreal.DrawDebugTrace.NONE,True)
    obstruction=hit.to_tuple() if hit else None
    if obstruction and obstruction[0]:raise RuntimeError('Actual private proof start capsule is blocked')
    actor=tagged[0] if tagged else actor_subsystem.spawn_actor_from_class(unreal.PlayerStart,center)
    if not actor or actor.get_outer().get_path_name().split('.')[0]!=package:
        raise RuntimeError('Proof start escaped the private gameplay overlay')
    if not tagged:
        actor.set_actor_label('Bastion private native proof start');actor.tags=['WarDutchProofStart','WarAegisCitadel']
    return dict(actor=actor.get_path_name(),sourceTeamSpawnIndex=1,signedFloorCm=floor,locationCm=point,
        actualFloorZCm=values[5].z,capsuleRadiusCm=42,capsuleHalfHeightCm=96,
        traceChannel='Visibility',traceComplex=True,capsuleClear=True,otherStartsPreserved=len(starts)-len(tagged))


def expected_misowned_review_start(name,state):
    return (name=='PlayerStart_0' and state['class']=='PlayerStart'
            and math.dist(state['transform'][:3],REVIEW_START_CM)<.1)


def canonical_city_payload(scenery_hashes,dependencies,origin):
    # This deliberately uses prepare_city's canonical JSON spacing, not the
    # compact geometry digest. City identity must match the native shared tool.
    return json.dumps(dict(scenery=scenery_hashes,dependencies=dependencies,origin=origin),sort_keys=True)


def canonical_city_revision(scenery_hashes,dependencies,origin):
    return hashlib.sha256(canonical_city_payload(scenery_hashes,dependencies,origin).encode()).hexdigest()


def require_final_city_hashes(city,package_hashes,source_hashes=None):
    source_hashes=source_hashes or {}
    if any(source_hashes[p]!=package_hashes[p] for p in set(source_hashes)&set(package_hashes)):
        raise ValueError('Conflicting source/owned package hash')
    all_hashes={**source_hashes,**package_hashes}
    hashes={p:all_hashes[p] for p in city['sceneryLevels']}
    if any(city['packageHashes'].get(p)!=h for p,h in hashes.items()):
        raise ValueError('A scenery package changed after city revision calculation')
    if city['revision']!=canonical_city_revision(hashes,city['dependencyHashes'],city['origin']):
        raise ValueError('City revision does not describe final saved scenery')
    if city.get('revisionPayload')!=canonical_city_payload(hashes,city['dependencyHashes'],city['origin']):
        raise ValueError('Exact canonical city revision payload is missing or stale')
    if city['packageHashes'].get(city['definition'])!=package_hashes[city['definition']]:
        raise ValueError('Native city definition hash is stale')
