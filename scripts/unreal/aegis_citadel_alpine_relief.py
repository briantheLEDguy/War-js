"""Private highland render refinement; the measured gameplay collision stays intact.

Refine actual native triangles above the occupied precinct into continuous ridged
rock. Low terrain corners remain verbatim. This is a render-only study and grants
no visual, traversal or performance approval.
"""
import math

SPEC = dict(recipeVersion=1, minimumHeightCm=16000, fullHeightCm=22000,
    subdivisions=8, maximumRiseCm=950, ridgePeriodCm=3400, detailPeriodCm=900,
    collisionChanged=False, nativeSourcePreserved=True, visualApproved=False)


def _vector(value, size):
    return (isinstance(value, list) and len(value) == size
        and all(type(v) in (int, float) and math.isfinite(v) for v in value))


def _unit(value):
    length=math.sqrt(sum(v*v for v in value))
    if length<1e-10:raise ValueError('Degenerate alpine surface normal')
    return [v/length for v in value]


def _cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def _noise(x,y):
    """Stable integer lattice noise, independent of Python hash randomization."""
    i,j=math.floor(x),math.floor(y);x-=i;y-=j
    x=x*x*(3-2*x);y=y*y*(3-2*y)
    def lattice(a,b):
        value=(a*374761393+b*668265263)&0xffffffff
        value=((value^(value>>13))*1274126177)&0xffffffff
        return (value^(value>>16))/4294967295
    lo=lattice(i,j)*(1-x)+lattice(i+1,j)*x
    hi=lattice(i,j+1)*(1-x)+lattice(i+1,j+1)*x
    return lo*(1-y)+hi*y


def relief_height(point):
    if point[2]<=SPEC['minimumHeightCm']:return 0.0
    fade=min(1,(point[2]-SPEC['minimumHeightCm'])/(SPEC['fullHeightCm']-SPEC['minimumHeightCm']))
    fade=fade*fade*(3-2*fade)
    # Slanted, unequal scales form connected rock ribs rather than a regular grid.
    x,y=point[:2];period=SPEC['ridgePeriodCm'];detail=SPEC['detailPeriodCm']
    broad=1-abs(2*_noise((x+.38*y)/period,(y-.13*x)/(period*.73))-1)
    fine=1-abs(2*_noise((x-.21*y)/detail,(y+.31*x)/(detail*1.4))-1)
    return fade*SPEC['maximumRiseCm']*(.78*broad**5+.22*fine**4)


def refine_native_highland(document):
    if (not isinstance(document,dict) or document.get('schemaVersion')!=1
            or any(document.get(k) is not True for k in ('readOnly','available','valid'))
            or document.get('policy')!='actual_render_index_order_oriented_triangle_corners'
            or document.get('lod')!=0 or document.get('invalidValues')!=0
            or not isinstance(document.get('mesh'),str)
            or not isinstance(document.get('triangles'),list)
            or not 1<=len(document['triangles'])<=100_000):
        raise ValueError('Complete bounded actual native mountain triangles are required')
    mesh=dict(positions=[],normals=[],uvs=[],indices=[],triangleMaterials=[])
    accumulated={};refined=0;unchanged=0;maximum_rise=0;identities=set()
    def vertex(p,n,uv):
        nonlocal maximum_rise
        rise=relief_height(p);maximum_rise=max(maximum_rise,rise)
        p=[p[0],p[1],p[2]+rise]
        index=len(mesh['positions']);mesh['positions'].append(p)
        mesh['normals'].append(n);mesh['uvs'].append(uv)
        return index
    def triangle(ids,material):
        mesh['indices'].extend(ids);mesh['triangleMaterials'].append(material)
        points=[mesh['positions'][i] for i in ids]
        a,b,c=points
        normal=_cross([b[j]-a[j] for j in range(3)],[c[j]-a[j] for j in range(3)])
        _unit(normal)
        # Preserve the measured winding/normal convention at the native boundary.
        source=[sum(mesh['normals'][i][j] for i in ids) for j in range(3)]
        if sum(a*b for a,b in zip(normal,source))<0:normal=[-v for v in normal]
        for i,p in zip(ids,points):
            if p[2]<=SPEC['minimumHeightCm']:continue
            key=tuple(round(v,5) for v in p)
            bucket=accumulated.setdefault(key,[0.,0.,0.])
            for j in range(3):bucket[j]+=normal[j]
    for face in document['triangles']:
        if (not isinstance(face,dict) or type(face.get('index')) is not int or face['index'] in identities
                or face.get('materialIndex')!=0
                or not isinstance(face.get('positions'),list) or len(face['positions'])!=3
                or not all(_vector(p,3) for p in face['positions'])
                or not isinstance(face.get('normals'),list) or len(face['normals'])!=3
                or not all(_vector(n,3) and sum(v*v for v in n)>.25 for n in face['normals'])
                or not isinstance(face.get('uvChannels'),list) or not face['uvChannels']
                or len(face['uvChannels'][0])!=3 or not all(_vector(uv,2) for uv in face['uvChannels'][0])):
            raise ValueError('Actual mountain corners, identities or material are incomplete')
        identities.add(face['index'])
        positions,normals,uvs=face['positions'],face['normals'],face['uvChannels'][0]
        if max(p[2] for p in positions)<=SPEC['minimumHeightCm']:
            ids=[vertex(p[:],n[:],uv[:]) for p,n,uv in zip(positions,normals,uvs)]
            triangle(ids,0);unchanged+=1;continue
        refined+=1;count=SPEC['subdivisions'];grid={}
        for row in range(count+1):
            for col in range(count-row+1):
                weights=[(count-row-col)/count,row/count,col/count]
                def interpolate(values):
                    return [sum(weights[k]*values[k][j] for k in range(3)) for j in range(len(values[0]))]
                grid[row,col]=vertex(interpolate(positions),_unit(interpolate(normals)),interpolate(uvs))
        for row in range(count):
            for col in range(count-row):
                triangle([grid[row,col],grid[row+1,col],grid[row,col+1]],0)
                if col<count-row-1:
                    triangle([grid[row+1,col],grid[row+1,col+1],grid[row,col+1]],0)
    for i,p in enumerate(mesh['positions']):
        if p[2]>SPEC['minimumHeightCm']:
            mesh['normals'][i]=_unit(accumulated[tuple(round(v,5) for v in p)])
    return mesh,dict(spec=SPEC,sourceMesh=document['mesh'],sourceTriangles=len(document['triangles']),
        untouchedLowTriangles=unchanged,refinedHighTriangles=refined,
        outputTriangles=len(mesh['triangleMaterials']),maximumActualRiseCm=maximum_rise,
        untouchedLowCornersPreserved=True,existingCollisionActorRequired=True,
        collisionChanged=False,visualApproved=False,performanceVerified=False)
