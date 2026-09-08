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


def fit_apron_clearance(rig):
    from tailored_locomotion import _sample_action,_restore_pose,_curves
    apron_obj=next(obj for obj in bpy.context.scene.objects if 'folded_work_apron' in obj.name)
    trousers_obj=next(obj for obj in bpy.context.scene.objects if 'trousers_continuous_tailored_surface' in obj.name)
    apron=_surface(apron_obj);trousers=_surface(trousers_obj)
    belt=rig.data.bones['apron_lower'].head_local.z
    rest=trousers[0]
    probe_indices=np.flatnonzero((rest[:,2]>belt-.39)&(rest[:,2]<belt-.035)&(rest[:,1]<-.035)&(np.abs(rest[:,0])<.31))
    for clip,duration in [('walk',30),('run',20),('jump',40)]:
        print('Fitting actual apron/trouser clearance: '+clip,flush=True)
        action=bpy.data.actions[clip];poses=_sample_action(rig,action,duration);angles=[]
        for frame in range(duration+1):
            bpy.context.scene.frame_set(frame);_restore_pose(rig,poses[frame])
            probes=_skin(trousers,rig)[probe_indices]
            # A thigh outside the apron silhouette is free to move past its edge.
            # Inside that silhouette the leather must remain in front of it.
            angle=0.;_fold(rig,angle)
            while not _clear(apron,rig,probes) and angle<1.4:
                angle+=.05;_fold(rig,angle)
            if not _clear(apron,rig,probes):raise RuntimeError(f'Apron clearance unresolved: {clip} frame {frame}')
            angles.append(angle+.025 if angle else 0.)
        # A compact envelope eases the fabric ahead of the knee without reducing
        # the measured clearance at any key. Loop endpoints share the same pose.
        cyclic=clip in ('walk','run')
        smooth=[]
        for frame in range(duration+1):
            values=[]
            for offset in range(-3,4):
                other=(frame+offset)%duration if cyclic else min(duration,max(0,frame+offset))
                values.append(angles[other]*math.exp(-.24*offset*offset))
            smooth.append(max(values))
        for frame,angle in enumerate(smooth):
            bpy.context.scene.frame_set(frame);_restore_pose(rig,poses[frame]);_fold(rig,angle)
            rig.pose.bones['apron_lower'].keyframe_insert('rotation_quaternion',frame=frame,group='apron_lower')
        for bag in _curves(action):
            for curve in bag.fcurves:
                if curve.data_path.startswith('pose.bones["apron_lower"]'):
                    for point in curve.keyframe_points:point.interpolation='LINEAR'
        print(f'{clip} apron maximum fold {math.degrees(max(smooth)):.1f} degrees',flush=True)
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
