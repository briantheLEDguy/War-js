"""CPU-only private render geometry proposal; original collision and source assets stay authoritative."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from aegis_citadel_alpine_relief import _noise,_cross,_unit

SPEC=dict(recipeVersion=1,option='ridged_highland_and_closed_backdrop_v1',minimumHeightCm=16000,
    fullHeightCm=22000,protectedPaddingCm=2400,targetSourceEdgeCm=250,maximumRefinementPasses=7,
    maximumOutputTriangles=320000,maximumRiseCm=620,maximumCutCm=280,
    gullyPeriodCm=1800,beddingPeriodCm=1500,smallFracturePeriodCm=700,
    originalCollisionRequired=True,collisionChanged=False,navigationChanged=False,
    lightingChanged=False,sourceAssetsChanged=False,nativeVerified=False,visualApproved=False,releaseAcceptance=False)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def smooth(value):
    t=max(0.,min(1.,value));return t*t*(3.-2.*t)


def eligibility(world,protected_bounds):
    height=smooth((world[2]-SPEC['minimumHeightCm'])/(SPEC['fullHeightCm']-SPEC['minimumHeightCm']))
    # The entire signed upper edit volume is excluded in XY, even above its roof.
    low,high=protected_bounds
    distance=math.hypot(max(low[0]-world[0],0.,world[0]-high[0]),max(low[1]-world[1],0.,world[1]-high[1]))
    return height*smooth(distance/SPEC['protectedPaddingCm'])


def relief_offset(world,protected_bounds):
    x,y,z=world;weight=eligibility(world,protected_bounds)
    if weight==0:return 0.
    warp=(_noise(x/7200.,y/6500.)-.5)*1.4
    gully=(.5+.5*math.cos((y+.16*x)/SPEC['gullyPeriodCm']+warp))**8
    bedding=(.5+.5*math.sin((z+.22*x-.11*y)/SPEC['beddingPeriodCm']))**6
    fracture=(1.-abs(2.*_noise((x-.19*y)/SPEC['smallFracturePeriodCm'],y/1100.)-1.))**4
    rise=SPEC['maximumRiseCm']*(.69*bedding+.31*fracture)*(1.-gully)
    return weight*(rise-SPEC['maximumCutCm']*gully)


def _position_key(point):return tuple(round(v,5) for v in point)


def _edge(a,b):return tuple(sorted((_position_key(a['p']),_position_key(b['p']))))


def _mid(a,b):
    return dict(p=[(x+y)/2 for x,y in zip(a['p'],b['p'])],
        n=_unit([(x+y)/2 for x,y in zip(a['n'],b['n'])]),
        uv=[[(x+y)/2 for x,y in zip(left,right)] for left,right in zip(a['uv'],b['uv'])])


def _split(corners,marked):
    flags=[_edge(corners[i],corners[(i+1)%3]) in marked for i in range(3)]
    count=sum(flags)
    if count==0:return [corners]
    mid=[_mid(corners[i],corners[(i+1)%3]) if flags[i] else None for i in range(3)]
    if count==1:
        i=flags.index(True);a,b,c=[corners[(i+j)%3] for j in range(3)];m=mid[i]
        return [[a,m,c],[m,b,c]]
    if count==2:
        common=next(i for i in range(3) if flags[i] and flags[(i-1)%3])
        left,v,right=corners[(common-1)%3],corners[common],corners[(common+1)%3]
        ml,mr=mid[(common-1)%3],mid[common]
        return [[v,mr,ml],[left,ml,right],[ml,mr,right]]
    a,b,c=corners;ab,bc,ca=mid
    return [[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]


def _retain_displaced_normal_side(mesh,source_positions,offsets):
    """Split only displaced normal seams when averaging crosses a native face plane."""
    repaired=0
    for offset in range(0,len(mesh['indices']),3):
        ids=mesh['indices'][offset:offset+3]
        if not any(offsets[i]!=0 for i in ids):continue
        a,b,c=[mesh['positions'][i] for i in ids]
        cross=_cross([b[i]-a[i] for i in range(3)],[c[i]-a[i] for i in range(3)])
        outward=_unit([-v for v in cross])
        average=[sum(mesh['normals'][i][j] for i in ids) for j in range(3)]
        if sum(a*b for a,b in zip(outward,average))>0:continue
        repaired+=1
        for corner,index in enumerate(ids):
            if offsets[index]==0:continue
            replacement=len(mesh['positions'])
            mesh['positions'].append(mesh['positions'][index][:]);mesh['normals'].append(outward[:])
            source_positions.append(source_positions[index][:]);offsets.append(offsets[index])
            for channel in mesh['uvChannels']:channel.append(channel[index][:])
            mesh['indices'][offset+corner]=replacement
        ids=mesh['indices'][offset:offset+3]
        average=[sum(mesh['normals'][i][j] for i in ids) for j in range(3)]
        if sum(a*b for a,b in zip(outward,average))<=0:
            raise ValueError('Displaced face normals cannot retain their side without changing protected corners')
    return repaired


def refine_saved_highland(document,actor_transform,protected_bounds):
    """Refine shared source edges consistently; all zero-weight faces remain verbatim."""
    before=digest(document)
    if (document.get('schemaVersion')!=1 or any(document.get(k) is not True for k in ('readOnly','available','valid'))
        or document.get('policy')!='actual_render_index_order_oriented_triangle_corners'
        or document.get('lod')!=0 or type(document.get('invalidValues')) is not int or document['invalidValues']!=0
        or not isinstance(document.get('triangles'),list) or not 1<=len(document['triangles'])<=100000):
        raise ValueError('Exact bounded valid saved native LOD0 triangles required')
    if actor_transform!=dict(translationCm=[25000,0,0],rotationQuaternion=[0,0,0,1],scale=[1,1,1]):
        raise ValueError('Measured native mountain transform required')
    if (not isinstance(protected_bounds,list) or len(protected_bounds)!=2
        or any(not isinstance(p,list) or len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in protected_bounds)
        or any(protected_bounds[0][i]>=protected_bounds[1][i] for i in range(3))):
        raise ValueError('Signed upper edit bounds required')
    translation=actor_transform['translationCm'];triangles=[];protected=[];identities=set();channel_count=None
    def world(p):return [p[i]+translation[i] for i in range(3)]
    for row in document['triangles']:
        if type(row.get('index')) is not int or row['index'] in identities or type(row.get('materialIndex')) is not int or row['materialIndex']!=0:
            raise ValueError('Unique actual triangle identities and retained slot zero required')
        identities.add(row['index']);positions=row.get('positions');normals=row.get('normals');channels=row.get('uvChannels')
        if (not isinstance(positions,list) or len(positions)!=3 or not isinstance(normals,list) or len(normals)!=3
            or any(not isinstance(v,list) or len(v)!=3 or any(type(c) not in (int,float) or not math.isfinite(c) for c in v) for v in positions+normals)
            or any(sum(v*v for v in n)<.25 for n in normals) or not isinstance(channels,list) or not 1<=len(channels)<=8
            or any(not isinstance(uv,list) or len(uv)!=3 or any(not isinstance(v,list) or len(v)!=2
                or any(type(c) not in (int,float) or not math.isfinite(c) for c in v) for v in uv) for uv in channels)):
            raise ValueError('Finite saved positions/normals and every UV channel required')
        if channel_count is None:channel_count=len(channels)
        if channel_count!=len(channels):raise ValueError('Saved native UV channel count changed')
        corners=[dict(p=p[:],n=n[:],uv=[uv[i][:] for uv in channels]) for i,(p,n) in enumerate(zip(positions,normals))]
        triangles.append(corners)
        if all(eligibility(world(c['p']),protected_bounds)==0 for c in corners):protected.append(copy.deepcopy(corners))
    passes=[]
    for iteration in range(SPEC['maximumRefinementPasses']+1):
        marked=set()
        for corners in triangles:
            for a,b in zip(corners,corners[1:]+corners[:1]):
                if (eligibility(world(a['p']),protected_bounds)>0 or eligibility(world(b['p']),protected_bounds)>0):
                    if math.dist(a['p'],b['p'])>SPEC['targetSourceEdgeCm']:marked.add(_edge(a,b))
        if not marked:break
        if iteration==SPEC['maximumRefinementPasses']:raise ValueError('Refinement pass budget exceeded; do not silently coarsen')
        expected=sum(1+sum(_edge(c[i],c[(i+1)%3]) in marked for i in range(3)) for c in triangles)
        if expected>SPEC['maximumOutputTriangles']:raise ValueError('Render triangle budget exceeded; native review required')
        triangles=[child for c in triangles for child in _split(c,marked)]
        passes.append(dict(markedEdges=len(marked),triangles=len(triangles)))
    mesh=dict(positions=[],normals=[],uvs=[],lightmapUvs=[],indices=[],triangleMaterials=[],uvChannels=[[] for unused in range(channel_count)])
    lookup={};source_positions=[];offsets=[];normal_sums={};unchanged_faces=0
    for corners in triangles:
        indices=[]
        if all(eligibility(world(c['p']),protected_bounds)==0 for c in corners):unchanged_faces+=1
        for c in corners:
            key=(tuple(c['p']),tuple(c['n']),tuple(tuple(v) for v in c['uv']))
            if key not in lookup:
                index=len(mesh['positions']);lookup[key]=index;offset=relief_offset(world(c['p']),protected_bounds)
                p=c['p'][:]
                if offset!=0:p[2]+=offset
                mesh['positions'].append(p);mesh['normals'].append(c['n'][:])
                source_positions.append(c['p'][:]);offsets.append(offset)
                for channel,uv in zip(mesh['uvChannels'],c['uv']):channel.append(uv[:])
            indices.append(lookup[key])
        mesh['indices'].extend(indices);mesh['triangleMaterials'].append(0)
        a,b,c=[mesh['positions'][i] for i in indices]
        normal=_cross([b[i]-a[i] for i in range(3)],[c[i]-a[i] for i in range(3)])
        if any(offsets[i]!=0 for i in indices):
            if sum(v*v for v in normal)<1e-12:raise ValueError('Displaced native face became degenerate')
            # Saved render normals oppose index winding on all measured highland faces.
            normal=[-v for v in normal]
            for i in indices:
                key=_position_key(source_positions[i]);total=normal_sums.setdefault(key,[0.,0.,0.])
                for j in range(3):total[j]+=normal[j]
    for i,p in enumerate(source_positions):
        if offsets[i]!=0:mesh['normals'][i]=_unit(normal_sums[_position_key(p)])
    normal_seams=_retain_displaced_normal_side(mesh,source_positions,offsets)
    mesh['uvs']=mesh['uvChannels'][0]
    mesh['lightmapUvs']=mesh['uvChannels'][1] if channel_count>1 else []
    assert digest(document)==before,'Input mutated'
    # Protected source triangles are still present with exact positions, normals and all UV values.
    preserved=set()
    for offset in range(0,len(mesh['indices']),3):
        ids=mesh['indices'][offset:offset+3]
        if all(eligibility(world(source_positions[i]),protected_bounds)==0 for i in ids):
            preserved.add(tuple((tuple(mesh['positions'][i]),tuple(mesh['normals'][i]),
                tuple(tuple(channel[i]) for channel in mesh['uvChannels'])) for i in ids))
    if any(tuple((tuple(v['p']),tuple(v['n']),tuple(tuple(uv) for uv in v['uv'])) for v in c) not in preserved for c in protected):
        raise ValueError('Protected source triangle was split or changed')
    audit=dict(spec=copy.deepcopy(SPEC),sourceMesh=document['mesh'],sourceDocumentSha256=before,sourceTriangles=len(document['triangles']),
        outputTriangles=len(mesh['triangleMaterials']),refinementPasses=passes,untouchedSourceTriangles=len(protected),
        untouchedSourceTrianglesPreserved=True,allNativeUvChannelsPreserved=channel_count,protectedUpperEditBounds=copy.deepcopy(protected_bounds),
        protectedBoundsSha256=digest(protected_bounds),minimumActualOffsetCm=min(offsets),maximumActualOffsetCm=max(offsets),
        measuredInputNormalSign=-1,repairedDisplacedFaceNormalSeams=normal_seams,
        nativeSavedOutputNormalSignVerified=False,originalCollisionActorRequired=True,
        collisionChanged=False,navigationChanged=False,lightingChanged=False,walkingRecordsChanged=False,
        nativeVerified=False,performanceVerified=False,visualApproved=False,releaseAcceptance=False)
    return mesh,audit


def closure_controls(existing):
    if len(existing)!=8 or any(len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in existing):
        raise ValueError('Eight frozen original distant-ridge controls required')
    west=[[p[0]+7000,-p[1],p[2]*.93] for p in reversed(existing)]
    seam=[[87000,-56000,12500],[97000,-40000,21000],[108000,-18000,34000],
        [111000,10000,43000],[101000,35000,23000],[85000,52000,12500]]
    return west+seam+copy.deepcopy(existing)


def build_backdrop_closure(root):
    """Reuse the owned connected crag loft; extend it across both retained terrain ends."""
    from aegis_citadel_distant_crags import REFERENCE,FROZEN_INPUTS,BOOLEAN_POLICY
    root=Path(root)
    for name,expected in FROZEN_INPUTS.items():
        if hashlib.sha256((root/REFERENCE/name).read_bytes()).hexdigest()!=expected:raise ValueError('Frozen crag source drift: '+name)
    measurement=json.loads((root/REFERENCE/'measurements.json').read_bytes())
    existing=[r['pointCm'] for r in measurement['distantRidgeCompositionSeeds']];controls=closure_controls(existing)
    source=root/REFERENCE/'optional_distant_crags.py'
    recipe=importlib.util.spec_from_file_location('owned_original_crag_recipe',source)
    module=importlib.util.module_from_spec(recipe);recipe.loader.exec_module(module)
    # A native staging process may already cache the architecture's Mesh class.
    # Generate this prototype separately rather than replacing that shared module.
    import sys
    frozen_mesh=root/REFERENCE/'patch-src/output/aegis_citadel_mesh.py'
    if Path(sys.modules['aegis_citadel_mesh'].__file__).resolve()!=frozen_mesh.resolve():
        raise ValueError('Generate the frozen crag loft in an isolated CPU process')
    mesh,stations=module.build(controls);payload=mesh.export()
    if payload['collision'] is not False:raise ValueError('Backdrop collision must remain disabled')
    audit=dict(option=SPEC['option'],sourceHashes=copy.deepcopy(FROZEN_INPUTS),originalEightControlsPreserved=True,
        originalControls=existing,closureControls=controls,coordinates='final_unreal_world_cm',
        retainedMountainWorldYBounds=[-52000,52000],closureSeamYRange=[-56000,70000],
        sourceLoftHelperSha256=hashlib.sha256(source.read_bytes()).hexdigest(),meshSha256=digest(payload),
        triangles=len(payload['indices'])//3,stations=len(stations),
        boundsCm=[[min(p[i] for p in payload['positions']) for i in range(3)],[max(p[i] for p in payload['positions']) for i in range(3)]],
        requiredNativePolicy=dict(collisionEnabled='NO_COLLISION',**BOOLEAN_POLICY),
        sourceMeshesChanged=False,collisionChanged=False,navigationChanged=False,lightingChanged=False,
        nativeVerified=False,projectedCoverageVerified=False,visualApproved=False,releaseAcceptance=False)
    return payload,audit


def build_saved_boundary_apron(document,actor_transform):
    """Extend the measured zero-height outer boundary only; add no walkable collision."""
    if actor_transform!=dict(translationCm=[25000,0,0],rotationQuaternion=[0,0,0,1],scale=[1,1,1]):
        raise ValueError('Exact retained terrain transform required for the apron')
    points=[p for row in document['triangles'] for p in row['positions']]
    if any(len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in points):
        raise ValueError('Finite saved boundary points required')
    low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)]
    if low[:2]!=[0,-52000] or high[:2]!=[65000,52000]:raise ValueError('Unreviewed native terrain boundary')
    boundary={tuple(p) for p in points if p[0]==65000 or p[1] in (-52000,52000)}
    if not boundary or any(abs(p[2])>.001 for p in boundary):raise ValueError('Native far/side boundary differs from the measured near-zero rim')
    border_heights={p[:2]:p[2] for p in boundary}
    if len(border_heights)!=len(boundary):raise ValueError('Native rim contains distinct heights at the same XY')
    xs=sorted({p[0]+25000 for p in boundary}|{float(x) for x in range(91500,220001,1500)}|{220000.})
    ys=sorted({p[1] for p in boundary}|{float(y) for y in range(53500,240001,1500)}
        |{float(-y) for y in range(53500,240001,1500)}|{-240000.,240000.})
    mesh=dict(positions=[],normals=[],uvs=[],indices=[],triangleMaterials=[],materials=['prototype_crag_rock'],collision=False)
    lookup={};normals={};boundary_seen=set()
    def vertex(x,y):
        key=(x,y)
        if key not in lookup:
            distance=math.hypot(max(x-90000.,0.),max(abs(y)-52000.,0.))
            fade=smooth(distance/15000.)
            # Continuous low rolling ground sits behind the unchanged retained rim.
            height=border_heights.get((x-25000,y),fade*(1700.*_noise(x/14500.,y/11000.)+450.*_noise(x/5300.,y/6700.)))
            lookup[key]=len(mesh['positions']);mesh['positions'].append([x,y,height]);mesh['normals'].append([0.,0.,1.])
            mesh['uvs'].append([x/2500.,y/2500.])
            if distance==0:boundary_seen.add((x-25000,y,height))
        return lookup[key]
    for a,b in zip(xs,xs[1:]):
        for c,d in zip(ys,ys[1:]):
            if b<=90000 and c>=-52000 and d<=52000:continue
            indices=[vertex(a,c),vertex(b,c),vertex(b,d),vertex(a,d)]
            for tri in (indices[:3],[indices[0],indices[2],indices[3]]):
                mesh['indices'].extend(tri);mesh['triangleMaterials'].append(0)
                p,q,r=[mesh['positions'][i] for i in tri];normal=_cross([q[j]-p[j] for j in range(3)],[r[j]-p[j] for j in range(3)])
                for i in tri:
                    total=normals.setdefault(i,[0.,0.,0.])
                    for j in range(3):total[j]+=normal[j]
    for i in normals:mesh['normals'][i]=_unit(normals[i])
    if any(p not in boundary_seen for p in boundary if p[0]==65000 or abs(p[1])==52000):
        raise ValueError('Apron omitted an exact native outer rim point')
    return mesh,dict(sourceBoundarySha256=digest(sorted(boundary)),sourceBoundaryPoints=len(boundary),
        sourceBoundaryWorldHeightRangeCm=[min(p[2] for p in boundary),max(p[2] for p in boundary)],
        sourceBoundaryPointsPreserved=True,forwardBoundaryExtended=False,
        outputTriangles=len(mesh['indices'])//3,coordinates='final_unreal_world_cm',
        originalRetainedRectangleExcluded=True,maximumActualRiseCm=max(p[2] for p in mesh['positions']),
        collisionChanged=False,navigationChanged=False,walkingRecordsChanged=False,
        nativeVerified=False,visualApproved=False,releaseAcceptance=False)


COLOR_RECIPE=dict(recipeVersion=1,inputs=['P','N','Rock'],worldPositionMask=[1,1,1,1,0],
    normalMask=[0,0,0,0,0],snowStartCm=18000,snowFullCm=28000,gullySlopeMinimum=.18,
    gullySlopeFull=.55,originalTintAndTextureInputPreserved=True,originalNormalAndOrmRootsPreserved=True,
    uvChanges=False,normalRootChanges=False,lightingChanged=False,shaderCompiled=False,visualApproved=False)

COLOR_SHADER=r'''
struct OwnedMountainNoise {
    float Lattice(int2 p) {
        uint v=uint(p.x)*374761393u+uint(p.y)*668265263u;
        v=(v^(v>>13))*1274126177u;
        return float(v^(v>>16))/4294967295.0;
    }
    float Value(float2 p) {
        int2 i=int2(floor(p));float2 f=frac(p);f=f*f*(3.0-2.0*f);
        return lerp(lerp(Lattice(i),Lattice(i+int2(1,0)),f.x),
            lerp(Lattice(i+int2(0,1)),Lattice(i+int2(1,1)),f.x),f.y);
    }
};
OwnedMountainNoise noise;
float warp=(noise.Value(float2(P.x/7200.0,P.y/6500.0))-.5)*1.4;
float channel=pow(.5+.5*cos((P.y+.16*P.x)/1800.0+warp),8.0);
float bedding=pow(.5+.5*sin((P.z+.22*P.x-.11*P.y)/1500.0),6.0);
float detail=noise.Value(float2((P.x-.19*P.y)/700.0,P.y/1100.0));
float up=saturate(-normalize(N).z);
float altitude=smoothstep(18000.0,28000.0,P.z);
float gullySlope=saturate((up-.18)/(.55-.18));
float shelf=smoothstep(.62,.9,up)*(1.0-bedding)*.28;
float snow=saturate(altitude*(channel*gullySlope*.94+shelf));
float3 rock=Rock*lerp(.70,1.10,bedding)*lerp(.90,1.07,detail);
return lerp(rock,float3(.63,.70,.76)*lerp(.91,1.04,detail),snow);
'''
