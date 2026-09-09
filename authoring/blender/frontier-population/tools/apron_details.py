"""Continuous bound perimeter and fitted neck loop for the leather apron."""
import math
import bpy
from mathutils import Vector
from surface_bindings import ClothSurface


def make_apron_details(apron,make,shape,leather):
    # Follow the subdivided open panel boundary; a control-cage outline extends
    # beyond rounded corners and reads as loose wire after subdivision.
    muted=[modifier for modifier in apron.modifiers if modifier.type in ('SOLIDIFY','ARMATURE') and modifier.show_viewport]
    for modifier in muted:modifier.show_viewport=False
    bpy.context.view_layer.update()
    evaluated=apron.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    points=[evaluated.matrix_world@vertex.co for vertex in mesh.vertices];edges={}
    for face in mesh.polygons:
        ids=tuple(face.vertices)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
    adjacency={}
    for (a,b),count in edges.items():
        if count==1:adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
    if any(len(values)!=2 for values in adjacency.values()):raise RuntimeError('Apron perimeter is not a closed sewn loop')
    start=min(adjacency);ordered=[start];previous=None;current=start
    while True:
        following=next(index for index in adjacency[current] if index!=previous)
        if following==start:break
        if following in ordered:raise RuntimeError('Apron binding boundary crosses itself')
        ordered.append(following);previous,current=current,following
    centers=[points[index]+Vector((0,-.001,0)) for index in ordered]
    evaluated.to_mesh_clear()
    for modifier in muted:modifier.show_viewport=True
    bpy.context.view_layer.update()
    vertices=[];sides=6;count=len(centers)
    for index,center in enumerate(centers):
        tangent=centers[(index+1)%count]-centers[(index-1)%count]
        rotation=tangent.to_track_quat('Z','Y')
        for side in range(sides):
            angle=side*math.tau/sides
            vertices.append(center+rotation@Vector((.0018*math.cos(angle),.0018*math.sin(angle),0)))
    make('apron_bound_perimeter',vertices,[(r*sides+c,r*sides+(c+1)%sides,((r+1)%count)*sides+(c+1)%sides,((r+1)%count)*sides+c)
                                        for r in range(count) for c in range(sides)],leather)

    supports=[ClothSurface(obj) for obj in bpy.context.scene.objects
              if obj==apron or 'shirt_continuous_tailored_surface' in obj.name or 'standing_shirt_collar' in obj.name]
    half=[(-.087,-.20,1.405),(-.105,-.12,1.51),(-.125,-.03,1.615),(-.108,.055,1.625),(-.060,.115,1.62),(0,.14,1.615)]
    stations=[shape(point) for point in half]+[shape((-x,y,z)) for x,y,z in reversed(half[:-1])]
    path=[]
    for index in range(len(stations)-1):
        a=stations[max(0,index-1)];b=stations[index];c=stations[index+1];d=stations[min(len(stations)-1,index+2)]
        for step in range(6):
            t=step/6
            path.append((2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)*.5)
    path.append(stations[-1])
    centers=[];normals=[]
    for point in path:
        hit,normal,_,_=min((surface.tree.find_nearest(point) for surface in supports),key=lambda row:row[3])
        outward=Vector((point.x,point.y,.15))
        if normal.dot(outward)<0:normal=-normal
        centers.append(hit+normal*.005);normals.append(normal)
    vertices=[]
    for index,(center,normal) in enumerate(zip(centers,normals)):
        tangent=centers[min(index+1,len(centers)-1)]-centers[max(index-1,0)]
        lateral=tangent.cross(normal).normalized()
        for offset in [-.0105,.0105]:
            point=center+lateral*offset
            hit,normal,_,_=min((surface.tree.find_nearest(point) for surface in supports),key=lambda row:row[3])
            if normal.dot(Vector((point.x,point.y,.15)))<0:normal=-normal
            vertices.append(hit+normal*.005)
    strap=make('apron_continuous_neck_loop',vertices,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(centers)-1)],leather)
    solid=strap.modifiers.new('Continuous_strap_leather','SOLIDIFY');solid.thickness=.003
