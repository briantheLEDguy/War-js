"""Pure ownership, triangle-exclusion and exact playable-edge checks for distant scenery skirts."""
import math
from t1_battlefield import terrain_sampling_bounds


def qualify_distant_skirt(source, terrain, mesh):
    spatial=source['spatial']; bounds=spatial['bounds']; sampled=terrain_sampling_bounds(spatial)
    positions=mesh.get('positions',[]); normals=mesh.get('normals',[]); uvs=mesh.get('uvs',[]); indices=mesh.get('indices',[])
    if not spatial.get('terrainBounds') or not 4<=len(positions)<=50000 or len(normals)!=len(positions) or len(uvs)!=len(positions) or not indices or len(indices)%3 or len(indices)>300000:
        raise ValueError('Invalid bounded distant skirt inventory')
    for p,n,uv in zip(positions,normals,uvs):
        if len(p)!=3 or len(n)!=3 or len(uv)!=2 or any(not math.isfinite(v) for v in [*p,*n,*uv]) or abs(math.hypot(*n)-1)>.001:
            raise ValueError('Invalid distant skirt vertex')
        x,z=p[1]/100,p[0]/100
        if not bounds['minX']-.001<=x<=bounds['maxX']+.001 or not bounds['minZ']-.001<=z<=bounds['maxZ']+.001:
            raise ValueError('Distant skirt escapes owned content')
    if any(isinstance(i,bool) or not isinstance(i,int) or not 0<=i<len(positions) for i in indices):raise ValueError('Invalid distant skirt triangle index')
    for i in range(0,len(indices),3):
        tri=[positions[j] for j in indices[i:i+3]]
        # Every entire triangle stays in one exterior half-plane, including concave playable footprints.
        if not any(all(sign*(p[axis]/100-value)>=-1e-6 for p in tri) for axis,value,sign in [(1,sampled['minX'],-1),(1,sampled['maxX'],1),(0,sampled['minZ'],-1),(0,sampled['maxZ'],1)]):
            raise ValueError('Distant skirt triangle crosses playable sampling')
        a,b,c=tri;cross=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        if cross>=-1e-7:raise ValueError('Distant skirt must retain native clockwise winding')
    edges={}
    for p,n in zip(terrain['positions'],terrain['normals']):
        x,z=p[1]/100,p[0]/100
        if min(abs(x-sampled['minX']),abs(x-sampled['maxX']),abs(z-sampled['minZ']),abs(z-sampled['maxZ']))<1e-5:
            edges[round(x,5),round(z,5)]=(p[2],n)
    actual={}
    for p,n in zip(positions,normals):
        key=round(p[1]/100,5),round(p[0]/100,5)
        if key in edges:actual.setdefault(key,[]).append((p[2],n))
    if not edges or set(actual)!=set(edges):raise ValueError('Distant skirt misses a playable boundary vertex')
    height_error=normal_error=0
    for key,(height,normal) in edges.items():
        for observed,n in actual[key]:
            height_error=max(height_error,abs(observed-height));normal_error=max(normal_error,math.dist(n,normal))
    if height_error>.001 or normal_error>1e-6:raise ValueError('Distant skirt edge height or normal differs')
    return dict(vertices=len(positions),triangles=len(indices)//3,boundaryVertices=len(edges),maximumBoundaryHeightErrorCm=height_error,
                maximumBoundaryNormalError=normal_error,trianglesOutsideSampling=True,collision='NoCollision',appearanceApproved=False,performanceAccepted=False)
