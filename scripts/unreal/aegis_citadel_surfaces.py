"""One height per XY on bounded, full-width approach fans.

The signed world-X profile supplies both authoring and proof expectations.
Its exact footprint is the union of the original segment rectangles and turn
fans; it does not flatten a short landing over its own incoming ramp.
"""
import hashlib
import json
import math


def profile_height(profile,x):
    knots=profile['knotsCm']
    if type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1_000_000 or not knots[0][0]<=x<=knots[-1][0]:
        raise ValueError('Route surface sample lies outside signed X domain')
    for a,b in zip(knots,knots[1:]):
        if x<=b[0]:
            t=(x-a[0])/(b[0]-a[0]);return a[1]+t*(b[1]-a[1])
    return knots[-1][1]


SURFACE_CAPSULE_POSE_METHOD='signed_piecewise_floor_and_actual_spherical_capsule'


def profile_capsule_offset(profile,x,radius=42,half_height=96,floor_margin=5):
    """Exact vertical rest pose of the spherical capsule over the signed floor.

    Every intersected linear piece contributes its endpoints and analytic
    sphere/plane extremum. This also covers knots beneath the lower hemisphere.
    It changes the survey pose; actual native movement remains authoritative.
    """
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (radius,half_height,floor_margin)):
        raise ValueError('Capsule dimensions must be finite numbers')
    if not 0<radius<=half_height<=1_000_000 or not 0<=floor_margin<=1_000_000:
        raise ValueError('Invalid spherical capsule dimensions or floor margin')
    floor=profile_height(profile,x);left,right=x-radius,x+radius
    if left<profile['knotsCm'][0][0] or right>profile['knotsCm'][-1][0]:
        raise ValueError('Complete capsule footprint escaped the signed floor domain')
    support=-math.inf
    for a,b in zip(profile['knotsCm'],profile['knotsCm'][1:]):
        lo,hi=max(left,a[0]),min(right,b[0])
        if lo>hi:continue
        slope=(b[1]-a[1])/(b[0]-a[0])
        critical=x+radius*slope/math.hypot(1,slope)
        for q in (lo,hi,max(lo,min(hi,critical))):
            delta=q-x
            height=a[1]+slope*(q-a[0])
            support=max(support,height-floor+math.sqrt(max(0,radius*radius-delta*delta)))
    if not math.isfinite(support):raise ValueError('Capsule has no signed floor support')
    return half_height-radius+support+floor_margin


def approach_profile(route):
    # These authored grades are independently checked by the native original
    # survey. They match the immutable graded paving plus a 2 cm surface gap;
    # source-only fixtures do not need a private height-field artifact.
    knots=[[11000,3405.5],[11100,3472.15],[11200,3537.3],[11300,3600.95],
        [11400,3664.6],[11500,3728.2],[11600,3791.85],[11700,3855.5],
        [11800,3919.15],[11900,3982.8],[12000,4046.4],[12100,4110.05],
        [12200,4173.7],[12300,4205.5],[12400,4205.5],[12500,4205.5],
        [12600,4205.5],[12700,4205.5],[12800,4205.5],[12900,4205.5],
        [13000,4205.5],[13100,4205.5],[13200,4205.5],[13300,4205.5],[13400,4205.5]]
    # Actual native endpoint values retain their original float precision.
    for row in knots:
        if row[0]==route['points'][0][0]:row[1]=route['points'][0][2]
    knots.extend([[13900,4210],[14600,4210]])
    return dict(schemaVersion=1,routeId=route['id'],kind='world_x_piecewise_linear',
        meshId='stairs_and_balconies',knotsCm=knots,
        boundaryPolicy='closed_profile_domain_shared_boundaries_same_height',
        construction='continuous_paved_fan_ramp')


def surface_geometry(route,profile):
    # Shared polygon operations partition the exact union, never its bounds.
    from aegis_citadel_mesh import (clean_floor_polygon,union_floor_polygons,
                                   clip_floor_half_plane,floor_union_boundary)
    points=route['points'];width=route['width']/2;polygons=[];normals=[]
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        if length<.01:raise ValueError('Fan route needs a nonzero planar run')
        n=[-dy/length,dx/length];normals.append(n)
        polygons.append(clean_floor_polygon([[a[0]+n[0]*width,a[1]+n[1]*width],
            [a[0]-n[0]*width,a[1]-n[1]*width],[b[0]-n[0]*width,b[1]-n[1]*width],
            [b[0]+n[0]*width,b[1]+n[1]*width]]))
    for i,p in enumerate(points[1:-1],1):
        for sign in (-1,1):
            poly=clean_floor_polygon([p[:2],[p[0]+normals[i-1][0]*width*sign,p[1]+normals[i-1][1]*width*sign],
                [p[0]+normals[i][0]*width*sign,p[1]+normals[i][1]*width*sign]])
            if poly:polygons.append(poly)
    # A threshold extends only 10 cm into the unchanged retained endpoint.
    a=points[0];dx,dy=points[1][0]-a[0],points[1][1]-a[1];length=math.hypot(dx,dy)
    dx,dy=dx/length,dy/length;n=normals[0]
    polygons.append(clean_floor_polygon([[a[0]+dx*t+n[0]*s,a[1]+dy*t+n[1]*s]
        for t,s in ((-10,-width),(10,-width),(10,width),(-10,width))]))
    fragments=union_floor_polygons(polygons);pieces=[]
    for a,b in zip(profile['knotsCm'],profile['knotsCm'][1:]):
        for poly in fragments:
            part=clip_floor_half_plane(poly,[a[0],1],[a[0],0])
            if part:part=clip_floor_half_plane(part,[b[0],0],[b[0],1])
            part=clean_floor_polygon(part,.01)
            if part:pieces.append(part)
    triangles=[]
    for poly in pieces:
        vertices=[[p[0],p[1],profile_height(profile,p[0])] for p in poly]
        triangles.extend([[vertices[0],vertices[i],vertices[i+1]] for i in range(1,len(vertices)-1)])
    boundary=floor_union_boundary(pieces)
    return triangles,boundary


def emit_surface(mesh,route,profile,foundation_bottom=2400):
    triangles,boundary=surface_geometry(route,profile);ordinals=[]
    for face in triangles:
        before=len(mesh.triangle_materials);start=len(mesh.positions);mesh.face(face,'flagstone')
        if len(mesh.triangle_materials)!=before+1:raise ValueError('Degenerate fan surface triangle')
        # Exact rectangle/fan edges retain the complete signed footprint.
        # Generic four-decimal rounding can move a diagonal boundary inward.
        mesh.positions[start:start+3]=[p[:] for p in face]
        ordinals.append(before)
        mesh.face([[p[0],p[1],foundation_bottom] for p in reversed(face)],'stone')
    for a,b in boundary:
        za,zb=profile_height(profile,a[0]),profile_height(profile,b[0])
        mesh.face([[a[0],a[1],foundation_bottom],[b[0],b[1],foundation_bottom],
                   [b[0],b[1],zb],[a[0],a[1],za]],'limestone')
    payload=json.dumps(profile,sort_keys=True,separators=(',',':'))
    return dict(routeId=route['id'],profilePayload=payload,
        profileSha256=hashlib.sha256(payload.encode()).hexdigest(),meshId=mesh.key,
        topTriangleIndices=ordinals)
