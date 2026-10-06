"""Solid stair and terrace masonry with explicit, vaulted route reservations.

These solids never supply walking floors. They end two centimetres below the
existing deck and subtract the complete signed lanes, including other segments
of the same stair. Convex differences retain their real diagonal boundaries;
neither bounding-box fills nor collision-free decorative substitutes are used.
"""
import math


def sub(a,b):return [a[i]-b[i] for i in range(3)]
def dot(a,b):return sum(a[i]*b[i] for i in range(3))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def unit(a):
    length=math.sqrt(dot(a,a))
    if length<1e-10:raise ValueError('A structural plane needs a nondegenerate normal')
    return [v/length for v in a]


def clean_face(points):
    result=[]
    for p in points:
        if not result or math.dist(p,result[-1])>=.01:result.append(p[:])
    if len(result)>1 and math.dist(result[0],result[-1])<.01:result.pop()
    changed=True
    while changed and len(result)>3:
        changed=False
        for i,b in enumerate(result):
            a,c=result[i-1],result[(i+1)%len(result)]
            edge=sub(c,a);edge2=dot(edge,edge)
            fraction=dot(sub(b,a),edge)/edge2 if edge2 else -1
            distance=(math.sqrt(dot(cross(sub(b,a),edge),cross(sub(b,a),edge))/edge2)
                      if edge2 else float('inf'))
            # Repeated clipping can leave a point on an existing long edge.
            # The same 0.01 cm source sanitation removes it before a quantized
            # fan creates a false sliver; the real boundary stays unchanged.
            if 0<=fraction<=1 and distance<.01:
                result.pop(i);changed=True;break
    return result if len(result)>=3 else []


def planes(solid):
    result=[]
    for face in solid:
        n=unit(cross(sub(face[1],face[0]),sub(face[2],face[0])))
        result.append((n,dot(n,face[0])))
    return result


def bounds(solid):
    points=[p for face in solid for p in face]
    return [[min(p[j] for p in points) for j in range(3)],
            [max(p[j] for p in points) for j in range(3)]]


def overlaps(a,b):return all(min(a[1][j],b[1][j])>max(a[0][j],b[0][j])+1e-7 for j in range(3))


def volume(solid):
    if not solid:return 0.
    points=[p for face in solid for p in face]
    origin=[sum(p[j] for p in points)/len(points) for j in range(3)]
    return abs(sum(dot(sub(face[0],origin),cross(sub(face[i],origin),sub(face[i+1],origin)))/6
        for face in solid for i in range(1,len(face)-1)))


def split_solid(solid,n,d):
    """Closed halves of an outward-oriented solid; inside is dot(n,p)<=d."""
    inside=[];outside=[];cuts=[]
    for face in solid:
        low=[];high=[]
        for a,b in zip(face,face[1:]+face[:1]):
            da,db=dot(n,a)-d,dot(n,b)-d
            if da<=1e-7:low.append(a)
            if da>=-1e-7:high.append(a)
            if (da < -1e-7 and db > 1e-7) or (da > 1e-7 and db < -1e-7):
                t=da/(da-db);p=[a[j]+(b[j]-a[j])*t for j in range(3)]
                low.append(p);high.append(p);cuts.append(p)
            elif abs(da)<=1e-7:cuts.append(a)
        low=clean_face(low);high=clean_face(high)
        if low:inside.append(low)
        if high:outside.append(high)
    unique=[]
    for p in cuts:
        if not any(math.dist(p,q)<.01 for q in unique):unique.append(p)
    if len(unique)>=3 and inside and outside:
        centre=[sum(p[j] for p in unique)/len(unique) for j in range(3)]
        u=unit(cross(n,[0,0,1] if abs(n[2])<.9 else [1,0,0]));v=cross(n,u)
        unique.sort(key=lambda p:math.atan2(dot(sub(p,centre),v),dot(sub(p,centre),u)))
        cap=clean_face(unique)
        if cap:inside.append(cap);outside.append(list(reversed(cap)))
    # Planar faces alone do not constitute a remaining volume.
    def volume_part(part):
        if not part:return []
        box=bounds(part)
        return part if all(box[1][j]-box[0][j]>.01 for j in range(3)) and volume(part)>1e-5 else []
    return volume_part(inside),volume_part(outside)


def subtract_solid(solid,cutter):
    if not overlaps(bounds(solid),bounds(cutter)):return [solid]
    cutters=planes(cutter);inside=solid
    for n,d in cutters:
        inside,_=split_solid(inside,n,d)
        if not inside:return [solid]
    pieces=[];inside=solid
    for n,d in cutters:
        inside,outside=split_solid(inside,n,d)
        if outside:pieces.append(outside)
        if not inside:break
    return pieces


def prism(a,b,width,bottom,cap_offset=-82):
    length=math.hypot(b[0]-a[0],b[1]-a[1])
    if length<.01:raise ValueError('A stair support needs an actual run')
    dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length;nx,ny=-dy,dx
    cap=[[p[0]+side*nx*width/2,p[1]+side*ny*width/2,p[2]+cap_offset]
         for p,side in ((a,-1),(b,-1),(b,1),(a,1))]
    base=[[p[0],p[1],bottom] for p in cap]
    return [list(reversed(base)),cap]+[[base[i],base[(i+1)%4],cap[(i+1)%4],cap[i]] for i in range(4)]


def route_vault(a,b,width):
    """A full-width lower opening with a pointed supporting arch above headroom."""
    half=width/2+47;profile=[[-half,-15],[half,-15],[half,350],
        [half*.8,470],[half*.45,590],[0,650],[-half*.45,590],[-half*.8,470],[-half,350]]
    length=math.hypot(b[0]-a[0],b[1]-a[1]);dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length
    nx,ny=-dy,dx
    rings=[[[p[0]+nx*y,p[1]+ny*y,p[2]+z] for y,z in profile] for p in (a,b)]
    return [list(reversed(rings[0])),rings[1]]+[
        [rings[0][i],rings[0][(i+1)%len(profile)],rings[1][(i+1)%len(profile)],rings[1][i]]
        for i in range(len(profile))]


def junction_vault(point,width):
    # Circumscription preserves all five lane elbows, rather than inscribing a
    # polygon whose corners cut the reserved capsule width.
    sides=12;radius=(width/2+47)/math.cos(math.pi/sides)
    rings=[[[point[0]+radius*math.cos(i*math.tau/sides),
             point[1]+radius*math.sin(i*math.tau/sides),point[2]+z] for i in range(sides)] for z in (-15,650)]
    return [list(reversed(rings[0])),rings[1]]+[
        [rings[0][i],rings[0][(i+1)%sides],rings[1][(i+1)%sides],rings[1][i]] for i in range(sides)]


def spawn_pad_vault(point,width):
    # A spawn pad is a square, so its diagonal corners cannot use a circular
    # lane-junction reservation. Keep the same real capsule margin and roof.
    half=width/2+47
    a=[point[0]-half,point[1],point[2]+650]
    b=[point[0]+half,point[1],point[2]+650]
    return prism(a,b,width+94,point[2]-15,0)


def gate_portal_reservation(leaf):
    # Route headroom alone does not clear the full signed portcullis height.
    # Reserve the complete opening through adjacent stair masonry; the gate
    # leaf itself remains the only stage barrier inside this aperture.
    point=leaf['point'];half_run=447
    top=point[2]+leaf['height']+15
    return prism([point[0]-half_run,point[1],top],
                 [point[0]+half_run,point[1],top],leaf['width']+94,point[2]-15,0)


def reservations(blueprint):
    result=[]
    for route in blueprint['routes']:
        for i,(a,b) in enumerate(zip(route['points'],route['points'][1:])):
            if math.dist(a[:2],b[:2])<.01:continue
            shape=route_vault(a,b,route['width'])
            result.append(dict(route=route['id'],segment=i,solid=shape,bounds=bounds(shape)))
        for i,p in enumerate(route['points']):
            shape=junction_vault(p,route['width'])
            result.append(dict(route=route['id'],junction=i,solid=shape,bounds=bounds(shape)))
    # Spawns are ground anchors, independently of the pictured route graph.
    # Reserve their complete pad and declared exit, so masonry cannot leave a
    # clear centerline while enclosing an enrolled participant inside a support.
    for approach in blueprint.get('spawnApproaches',[]):
        key='spawn_'+str(approach['index'])
        for i,(a,b) in enumerate(zip(approach['points'],approach['points'][1:])):
            if math.dist(a[:2],b[:2])<.01:continue
            shape=route_vault(a,b,approach['widthCm'])
            result.append(dict(route=key,spawnIndex=approach['index'],segment=i,
                               solid=shape,bounds=bounds(shape)))
        for i,p in enumerate(approach['points']):
            shape=spawn_pad_vault(p,approach['widthCm']) if i==0 else junction_vault(p,approach['widthCm'])
            result.append(dict(route=key,spawnIndex=approach['index'],junction=i,
                               solid=shape,bounds=bounds(shape)))
    for gate in blueprint.get('gates',[]):
        for index,leaf in enumerate(gate['leaves']):
            shape=gate_portal_reservation(leaf)
            result.append(dict(route='gate_'+gate['id']+'_'+str(index),gateIndex=gate['index'],
                               solid=shape,bounds=bounds(shape)))
    return result


def emit_support(mesh,solid,reserved,owner=None):
    pieces=[solid];original=bounds(solid);subtractions=0
    for row in reserved:
        if owner==(row.get('route'),row.get('segment')) or not overlaps(original,row['bounds']):continue
        before=len(pieces)
        pieces=[q for p in pieces for q in subtract_solid(p,row['solid'])]
        if pieces:subtractions+=before!=len(pieces)
        if not pieces:break
    start=len(mesh.indices)//3
    for piece in pieces:
        for face in piece:
            # A convex clipping face has one exact supporting plane. Preserve
            # that plane when quantizing its corners; independently deriving a
            # normal for an acute fan triangle amplifies 0.0001 cm rounding.
            exact=clean_face(face)
            if not exact:continue
            n=unit(cross(sub(exact[1],exact[0]),sub(exact[2],exact[0])))
            # Convex cuts can create submillimetre edges. Six-decimal source
            # positions keep their supporting plane coherent; the native
            # float32 Mikk preflight still verifies the actual import boundary.
            points=clean_face([[round(v,6) for v in p] for p in face])
            if not points:continue
            for i in range(1,len(points)-1):
                triangle=[points[0],points[i],points[i+1]]
                actual=cross(sub(triangle[1],triangle[0]),sub(triangle[2],triangle[0]))
                if math.sqrt(dot(actual,actual))<.001:continue
                if (dot(unit(actual),n)<=1-1e-6 or
                        max(abs(dot(sub(p,exact[0]),n)) for p in triangle)>.01):
                    raise ValueError('Quantized support triangle left its authored clipping plane: '+
                        repr(dict(triangle=triangle,exactFace=exact,normal=n,dot=dot(unit(actual),n),
                                  actualArea2=math.sqrt(dot(actual,actual)),
                                  planeErrorCm=max(abs(dot(sub(p,exact[0]),n)) for p in triangle))))
                previous=len(mesh.positions);mesh.face(triangle,'stone')
                axes=[j for j in range(3) if j!=max(range(3),key=lambda k:abs(n[k]))]
                for index in range(previous,len(mesh.positions)):
                    mesh.positions[index]=triangle[index-previous][:]
                    mesh.normals[index]=n[:];mesh.uvs[index]=[mesh.positions[index][j]/360 for j in axes]
    return dict(pieces=len(pieces),triangles=len(mesh.indices)//3-start,subtractions=subtractions)
