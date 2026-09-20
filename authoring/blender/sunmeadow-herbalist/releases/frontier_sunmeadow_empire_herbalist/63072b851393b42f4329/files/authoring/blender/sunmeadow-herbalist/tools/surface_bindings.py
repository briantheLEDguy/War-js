"""Fit garment details to the actual finished cloth and its skinning field."""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
from apron_clearance import _surface


class ClothSurface:
    def __init__(self,obj):
        coordinates,self.triangles,fields,world=_surface(obj)
        self.points=[world@Vector(point[:3]) for point in coordinates]
        self.tree=BVHTree.FromPolygons(self.points,self.triangles,all_triangles=True)
        self.fields=[{} for _ in self.points]
        for name,(indices,weights) in fields.items():
            for index,weight in zip(indices,weights):self.fields[int(index)][name]=float(weight)

    def weights(self,point,triangle):
        ids=self.triangles[triangle];a,b,c=(self.points[index] for index in ids)
        bary=barycentric_transform(point,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        result={}
        for index,fraction in zip(ids,bary):
            for name,weight in self.fields[index].items():result[name]=result.get(name,0)+weight*max(0,fraction)
        total=sum(result.values())
        if total<=0:raise RuntimeError('Finished cloth has no usable skinning field')
        return {name:weight/total for name,weight in result.items() if weight>1e-7}


def bind_detail(obj,surfaces,minimum_distance=0,select=None):
    inverse=obj.matrix_world.inverted()
    for vertex in obj.data.vertices:
        point=obj.matrix_world@vertex.co
        if select and not select(point):continue
        candidates=[(surface,surface.tree.find_nearest(point)) for surface in surfaces]
        surface,(hit,normal,triangle,distance)=min(candidates,key=lambda row:row[1][3])
        if distance<minimum_distance:
            direction=(point-hit).normalized() if distance>1e-7 else normal
            vertex.co=inverse@(hit+direction*minimum_distance)
        for group in obj.vertex_groups:group.remove([vertex.index])
        for name,weight in surface.weights(hit,triangle).items():
            group=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
            group.add([vertex.index],weight,'REPLACE')
    obj.data.update()
    bpy.context.view_layer.update()
