"""Closed sewn welts taken from the actual finished boot surface."""
import math
from mathutils import Vector
from surface_bindings import ClothSurface, bind_detail


def sole_contour(surface,height):
    points={};adjacent={}
    for triangle in surface.triangles:
        hits=[]
        for ia,ib in zip(triangle,triangle[1:]+triangle[:1]):
            a,b=surface.points[ia],surface.points[ib]
            if (a.z-height)*(b.z-height)<0:
                point=a.lerp(b,(height-a.z)/(b.z-a.z))
                # Shared edge identity avoids round-off cracks at a mesh edge.
                key=tuple(sorted((ia,ib)))
                points[key]=point;hits.append(key)
        if len(set(hits))==2:
            a,b=hits;adjacent.setdefault(a,set()).add(b);adjacent.setdefault(b,set()).add(a)
    if not adjacent or any(len(neighbors)!=2 for neighbors in adjacent.values()):
        raise RuntimeError('Finished sole contour is not a closed surface section')
    remaining=set(adjacent);loops=[]
    while remaining:
        start=min(remaining);current=start;previous=None;loop=[]
        while True:
            loop.append(points[current]);remaining.discard(current)
            following=next(key for key in sorted(adjacent[current]) if key!=previous)
            if following==start:break
            previous,current=current,following
            if len(loop)>len(adjacent):raise RuntimeError('Sole contour failed to close')
        loops.append(loop)
    # Solidified footwear has an exterior and a lining. Use the outer contour.
    area=lambda loop:sum(a.x*b.y-b.x*a.y for a,b in zip(loop,loop[1:]+loop[:1]))*.5
    contour=max(loops,key=lambda loop:abs(area(loop)))
    if area(contour)<0:contour.reverse()
    return contour


def sew_sole_welt(boot,make,material,height,side):
    support=ClothSurface(boot);contour=sole_contour(support,height)
    segments=list(zip(contour,contour[1:]+contour[:1]));lengths=[(b-a).length for a,b in segments]
    total=sum(lengths);count=max(96,math.ceil(total/.004))
    def along(distance):
        for (a,b),length in zip(segments,lengths):
            if distance<=length:return a.lerp(b,distance/max(length,1e-10))
            distance-=length
        return contour[0].copy()
    path=[along(index*total/count) for index in range(count)]
    vertices=[];faces=[];sides=6
    for index,point in enumerate(path):
        tangent=(path[(index+1)%count]-path[(index-1)%count]).normalized()
        hit,normal,_,_=support.tree.find_nearest(point)
        normal=(normal-tangent*normal.dot(tangent)).normalized()
        across=tangent.cross(normal).normalized()
        center=hit+normal*.0005
        for column in range(sides):
            angle=column*math.tau/sides
            vertices.append(center+.002*(normal*math.cos(angle)+across*math.sin(angle)))
        for column in range(sides):
            faces.append((index*sides+column,index*sides+(column+1)%sides,
                          ((index+1)%count)*sides+(column+1)%sides,((index+1)%count)*sides+column))
    welt=make('welt_stitch_'+str(side),vertices,faces,material)
    bind_detail(welt,[support])
    return welt
