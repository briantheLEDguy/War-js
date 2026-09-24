"""Fit the retained apron panel over the real animated trouser surface."""
import math
import bpy
import numpy as np
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree


def _surface(obj):
    modifiers=[modifier for modifier in obj.modifiers if modifier.type=='ARMATURE']
    enabled=[modifier.show_viewport for modifier in modifiers]
    try:
        for modifier in modifiers:modifier.show_viewport=False
        bpy.context.view_layer.update()
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
        coordinates=np.ones((len(mesh.vertices),4),dtype=np.float64)
        coordinates[:,:3]=[vertex.co[:] for vertex in mesh.vertices]
        fields={}
        for vertex in mesh.vertices:
            for entry in vertex.groups:
                if entry.weight>1e-7:fields.setdefault(obj.vertex_groups[entry.group].name,[]).append((vertex.index,entry.weight))
        triangles=[tuple(triangle.vertices) for triangle in mesh.loop_triangles]
        evaluated.to_mesh_clear()
        return coordinates,triangles,{name:(np.array([i for i,w in rows]),np.array([w for i,w in rows])) for name,rows in fields.items()},obj.matrix_world.copy()
    finally:
        for modifier,value in zip(modifiers,enabled):modifier.show_viewport=value
        bpy.context.view_layer.update()


def _skin(surface,rig):
    points,_,fields,world=surface
    result=np.zeros((len(points),3),dtype=np.float64)
    for name,(indices,weights) in fields.items():
        bone=rig.pose.bones[name]
        matrix=np.array(rig.matrix_world@bone.matrix@bone.bone.matrix_local.inverted()@rig.matrix_world.inverted()@world)
        result[indices]+=(points[indices]@matrix.T)[:,:3]*weights[:,None]
    return result


def _fold(rig,angle):
    hinge=rig.pose.bones['apron_lower'];basis=hinge.bone.matrix_local.to_3x3().normalized()
    hinge.rotation_mode='QUATERNION'
    hinge.rotation_quaternion=(basis.inverted()@Quaternion(Vector((1,0,0)),-angle).to_matrix()@basis).to_quaternion()
    bpy.context.view_layer.update()


def _clear(apron,rig,probes):
    tree=BVHTree.FromPolygons(_skin(apron,rig),apron[1],all_triangles=True)
    for point in probes:
        hit=tree.ray_cast(Vector((point[0],-2,point[2])),Vector((0,1,0)),3)[0]
        if hit is not None and point[1]<hit.y+.008:return False
    return True
