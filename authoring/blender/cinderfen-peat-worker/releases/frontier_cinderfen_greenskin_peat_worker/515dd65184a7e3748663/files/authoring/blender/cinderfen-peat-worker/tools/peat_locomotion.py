"""Fit the original worker's fall to its actual body, boots, bib and hands."""
import bpy,math,numpy as np
from mathutils import Vector,Quaternion
from tailored_locomotion import _sample_action,_restore_pose,_curves,_solve_chain
from apron_clearance import _surface,_skin

def fit_fall(rig):
    action=bpy.data.actions['death'];poses=_sample_action(rig,action,60)
    body=bpy.data.objects['greenskin_peat_worker_exposed_anatomy'];skin=_surface(body)
    supports=[_surface(o) for o in bpy.context.scene.objects if o.type=='MESH' and
              ('continuous_tailored_surface' in o.name or 'folded_work_apron' in o.name or o.name=='work_belt' or o.name.startswith('forged_buckle'))]
    boots={side:_surface(bpy.data.objects['fitted_boot_'+str(sign)]) for side,sign in [('L',1),('R',-1)]}
    trousers=_surface(bpy.data.objects['trousers_continuous_tailored_surface'])
    hands={}
    for side in ('L','R'):
        member={}
        for name,(indices,weights) in skin[2].items():
            if name.endswith('_'+side) and name.startswith(('hand_','index_','middle_','ring_','pinky_','thumb_')):
                for i,w in zip(indices,weights):member[int(i)]=member.get(int(i),0)+w
        hands[side]=[i for i,w in member.items() if w>.5]
    names=[part+'_'+side for side in ('L','R') for part in ('thigh','shin','foot','toe','upper_arm','forearm','hand')]
    for bag in _curves(action):
        for curve in list(bag.fcurves):
            if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):bag.fcurves.remove(curve)
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    for frame in range(61):
        bpy.context.scene.frame_set(frame);_restore_pose(rig,poses[frame])
        t=max(0,min(1,(frame-12)/31));t=t*t*(3-2*t)
        hips=rig.pose.bones['hips'];matrix=hips.matrix.copy()
        low=min(float(_skin(surface,rig)[:,2].min()) for surface in supports)
        # Body support is measured before limb placement, so the inherited
        # superman-like end pose settles onto real clothing instead of floating.
        matrix.translation.z+=(.007-low)*t
        hips.matrix=matrix;bpy.context.view_layer.update()
        for side,sign in [('L',1),('R',-1)]:
            foot=rig.pose.bones['foot_'+side];thigh=rig.pose.bones['thigh_'+side]
            target=Vector((sign*.235,thigh.head.y+.93,.18))
            ankle=foot.head.lerp(target,t)
            rotation=foot.matrix.to_quaternion().slerp(Quaternion(Vector((1,0,0)),math.pi/2)@foot.bone.matrix_local.to_quaternion(),t)
            for _ in range(4):
                _solve_chain(rig,side,ankle,rotation,hint=Vector((0,0,-1)))
                low=float(_skin(boots[side],rig)[:,2].min());correction=.005-low
                ankle.z+=max(0,correction)+min(0,correction)*t
            upper=rig.pose.bones['upper_arm_'+side];hand=rig.pose.bones['hand_'+side];rest=hand.bone
            target=Vector((sign*.43,upper.head.y-.25,.075))
            wrist=hand.head.lerp(target,t)
            direction=Vector((sign*.12,-1,-.02))
            aligned=(rest.tail_local-rest.head_local).rotation_difference(direction)@rest.matrix_local.to_quaternion()
            rotation=hand.matrix.to_quaternion().slerp(aligned,t)
            for _ in range(5):
                _solve_chain(rig,side,wrist,rotation,('upper_arm','forearm','hand'),Vector((sign,0,-.9)))
                low=float(_skin(skin,rig)[hands[side],2].min());correction=.005-low
                wrist.z+=max(0,correction)+min(0,correction)*t
        # Fitted feet can leave a bent knee lower than the earlier torso-only
        # support estimate. Raise the pelvis by the measured cloth error, then
        # retain the grounded ankle and palm targets through a fresh IK solve.
        for correction_pass in range(4):
            low=float(_skin(trousers,rig)[:,2].min())
            if low>=.004:break
            targets={side:{part:(rig.pose.bones[part+'_'+side].head.copy(),rig.pose.bones[part+'_'+side].matrix.to_quaternion()) for part in ('foot','hand')} for side in ('L','R')}
            matrix=hips.matrix.copy();matrix.translation.z+=(.006-low)*2
            hips.matrix=matrix;bpy.context.view_layer.update()
            for side,sign in [('L',1),('R',-1)]:
                ankle,rotation=targets[side]['foot'];_solve_chain(rig,side,ankle,rotation,hint=Vector((0,0,-1)))
                wrist,rotation=targets[side]['hand'];_solve_chain(rig,side,wrist,rotation,('upper_arm','forearm','hand'),Vector((sign,0,-.9)))
        hips.keyframe_insert('location',frame=frame,group='hips')
        for name in names:
            bone=rig.pose.bones[name];bone.rotation_mode='QUATERNION'
            bone.keyframe_insert('rotation_quaternion',frame=frame,group=name)
            bone.keyframe_insert('location',frame=frame,group=name)
    for bag in _curves(action):
        for curve in bag.fcurves:
            if curve.data_path=='pose.bones["hips"].location' or any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):
                for key in curve.keyframe_points:key.interpolation='LINEAR'
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
