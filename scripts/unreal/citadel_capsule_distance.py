"""Independent double-precision contact diagnostics; never grants admission.

Inputs must be actual cooked world triangles and the recorded full capsule axis.
Render/source geometry alone cannot establish native collision clearance.
"""
import math
from decimal import Decimal,localcontext

MAX_COORDINATE_CM=1_000_000


def _v(value):
    if not isinstance(value,(list,tuple)) or len(value)!=3 or any(type(x) not in (int,float)
            or not math.isfinite(x) or abs(x)>MAX_COORDINATE_CM for x in value):
        raise ValueError('Contact coordinates must be three finite numbers within the supported 10 km world bound')
    return tuple(float(x) for x in value)


def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def scale(a,s):return tuple(x*s for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def clamp(x):return max(0.,min(1.,x))


def _point_segment(p,a,b):
    d=sub(b,a);length=dot(d,d)
    q=a if length==0 else add(a,scale(d,clamp(dot(sub(p,a),d)/length)))
    return dot(sub(p,q),sub(p,q))


def _segments(p,q,a,b):
    u,v,w=sub(q,p),sub(b,a),sub(p,a)
    aa,bb,ab,aw,bw=dot(u,u),dot(v,v),dot(u,v),dot(u,w),dot(v,w)
    if aa==0:return _point_segment(p,a,b)
    if bb==0:return _point_segment(a,p,q)
    determinant=aa*bb-ab*ab
    if determinant<=1e-15*aa*bb:
        # A near-parallel edge can still cross the capsule axis. Preserve the
        # actual binary inputs and resolve cancellation instead of declaring it parallel.
        with localcontext() as context:
            context.prec=80
            du,dv,dw=[tuple(Decimal.from_float(x) for x in vector) for vector in (u,v,w)]
            ddot=lambda x,y:sum((i*j for i,j in zip(x,y)),Decimal(0))
            da,db,dab,daw,dbw=ddot(du,du),ddot(dv,dv),ddot(du,dv),ddot(du,dw),ddot(dv,dw)
            ddet=da*db-dab*dab;dc=lambda x:max(Decimal(0),min(Decimal(1),x))
            ds=dc((dab*dbw-db*daw)/ddet) if ddet>0 else Decimal(0)
            dt=(dab*ds+dbw)/db
            if dt<0:dt=Decimal(0);ds=dc(-daw/da)
            elif dt>1:dt=Decimal(1);ds=dc((dab-daw)/da)
            delta=tuple(dw[i]+du[i]*ds-dv[i]*dt for i in range(3))
            result=float(ddot(delta,delta))
            if not math.isfinite(result):raise ValueError('Nonfinite contact distance')
            return result
    s=clamp((ab*bw-bb*aw)/determinant)
    t=(ab*s+bw)/bb
    if t<0:t=0.;s=clamp(-aw/aa)
    elif t>1:t=1.;s=clamp((ab-aw)/aa)
    delta=sub(add(p,scale(u,s)),add(a,scale(v,t)))
    return dot(delta,delta)


def _inside(p,a,b,c,n):
    # Orient all three edges against the same triangle normal. Translation
    # relative to a nearby vertex avoids large world-coordinate dot products.
    return all(dot(cross(sub(y,x),sub(p,x)),n)>=0 for x,y in ((a,b),(b,c),(c,a)))


def _point_triangle(p,a,b,c,n,n2):
    if n2:
        height=dot(sub(p,a),n)
        projection=sub(p,scale(n,height/n2))
        if _inside(projection,a,b,c,n):return height*height/n2
    return min(_point_segment(p,a,b),_point_segment(p,b,c),_point_segment(p,c,a))


def segment_triangle_distance_squared(start,end,triangle):
    """Minimum distance including plane crossings, edges and degenerate faces."""
    p,q=_v(start),_v(end)
    if len(triangle)!=3:raise ValueError('A cooked triangle needs exactly three vertices')
    a,b,c=map(_v,triangle);n=cross(sub(b,a),sub(c,a));n2=dot(n,n)
    if n2:
        d0,d1=dot(sub(p,a),n),dot(sub(q,a),n)
        if d0!=d1:
            t=d0/(d0-d1)
            if 0<=t<=1 and _inside(add(p,scale(sub(q,p),t)),a,b,c,n):return 0.
    result=min(_point_triangle(p,a,b,c,n,n2),_point_triangle(q,a,b,c,n,n2),
        _segments(p,q,a,b),_segments(p,q,b,c),_segments(p,q,c,a))
    if not math.isfinite(result):raise ValueError('Nonfinite contact distance')
    return max(0.,result)


def capsule_triangle_clearance(start,end,radius,triangle):
    # This local surface gap is not a body's minimum translation distance.
    if type(radius) not in (int,float) or not math.isfinite(radius) or not 0<radius<=MAX_COORDINATE_CM:
        raise ValueError('The actual full capsule radius must be positive and finite')
    return math.sqrt(segment_triangle_distance_squared(start,end,triangle))-radius
