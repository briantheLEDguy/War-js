"""Differential stone detail changes pixel normals only, preserving native terrain contacts."""
import math

NORMAL_SHADER = r"""
float3 n=normalize(N),px=ddx(P),py=ddy(P);
float3 r1=cross(py,n),r2=cross(n,px);
float determinant=dot(px,r1);
float detailWeight=1-smoothstep(20,120,max(length(px),length(py)));
float3 gradient=detailWeight*sign(determinant)*(ddx(H)*r1+ddy(H)*r2);
float3 result=abs(determinant)>1e-8 ? normalize(abs(determinant)*n-gradient) : n;
return normalize(TransformWorldVectorToTangent(Parameters.TangentToWorld,result));
"""


def differential_normal(normal, position_dx, position_dy, height_dx, height_dy):
    """Reference world-space normal; screen orientation must not change the surface gradient."""
    vectors=(normal,position_dx,position_dy)
    if any(len(v)!=3 or any(not math.isfinite(x) for x in v) for v in vectors) or not all(math.isfinite(x) for x in (height_dx,height_dy)):
        raise ValueError('Invalid differential stone inputs')
    weight=detail_weight(max(math.sqrt(sum(x*x for x in v)) for v in (position_dx,position_dy)))
    def unit(v):
        length=math.sqrt(sum(x*x for x in v))
        if length<1e-12:raise ValueError('Differential stone needs a nonzero surface normal')
        return [x/length for x in v]
    def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    n=unit(normal);r1=cross(position_dy,n);r2=cross(n,position_dx)
    determinant=sum(a*b for a,b in zip(position_dx,r1))
    if abs(determinant)<=1e-8:return n
    sign=1 if determinant>0 else -1
    return unit([abs(determinant)*a-weight*sign*(height_dx*b+height_dy*c) for a,b,c in zip(n,r1,r2)])


def bump_controls(geology):
    bump=geology['bumpHeightCm']
    if len(bump)!=2 or any(not math.isfinite(v) or not 0<=v<=80 for v in bump):
        raise ValueError('Geological bump exceeds its cosmetic bounds')
    return bump


def bump_height(geology,coarse,fine):
    bump=bump_controls(geology)
    if any(not math.isfinite(v) or not 0<=v<=1 for v in (coarse,fine)):
        raise ValueError('Invalid geological noise sample')
    return (coarse-.5)*bump[0]+(fine-.5)*bump[1]


def detail_weight(footprint_cm):
    """Fade unfiltered subpixel stone detail over a 20-120cm world-space pixel footprint."""
    if not math.isfinite(footprint_cm) or footprint_cm<0:raise ValueError('Invalid stone pixel footprint')
    t=max(0,min(1,(footprint_cm-20)/100))
    return 1-t*t*(3-2*t)
