"""Fit civilian gestures to the retained broad shoulder and chest envelope."""
import math
import bpy
from mathutils import Matrix,Vector
from tailored_locomotion import _sample_action,_restore_pose,_curves,_solve_chain


def fit_arm_motion(rig,include_death=True):
    names=[part+'_'+side for side in ('L','R') for part in ('upper_arm','forearm','hand')]
    specs=[('walk',30),('run',20),('attack_melee',30),('attack_ranged',40),('cast',60)]
    if include_death:specs.append(('death',60))
    for clip,duration in specs:
        print('Fitting broad-shoulder arm movement: '+clip,flush=True)
        action=bpy.data.actions[clip];poses=_sample_action(rig,action,duration)
        for bag in _curves(action):
            for curve in list(bag.fcurves):
                if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):bag.fcurves.remove(curve)
        for frame in range(duration+1):
            bpy.context.scene.frame_set(frame);_restore_pose(rig,poses[frame])
            chest=rig.pose.bones['upper_chest'];space=chest.matrix@chest.bone.matrix_local.inverted()
            for side,sign,offset in [('L',1,0),('R',-1,.5)]:
                phase=frame/duration;swing=math.cos((phase+offset)*math.tau)
                shoulder=rig.data.bones['upper_arm_'+side].head_local
                target=shoulder+Vector((sign*.13,-.13,-.39))
                if clip=='walk':target=shoulder+Vector((sign*.23,-.09+.16*swing,-.40-.025*swing))
                elif clip=='run':target=shoulder+Vector((sign*.24,-.10+.23*swing,-.34-.04*swing))
                elif clip in ('attack_melee','attack_ranged'):
                    target=shoulder+Vector((sign*.075,-.32,-.22))
                    if side=='R' and clip=='attack_melee':
                        strike=math.exp(-((phase-.48)/.14)**2)
                        target+=Vector((.03*strike,-.22*strike,.07*strike))
                    elif side=='R':
                        wind=math.exp(-((phase-.27)/.14)**2);release=math.exp(-((phase-.58)/.12)**2)
                        target+=Vector((-.035*wind,.14*wind-.21*release,.14*wind+.04*release))
                elif clip=='cast':
                    gesture=math.sin(math.pi*phase)**2
                    target=shoulder+Vector((sign*(.075+.035*gesture),-.30-.14*gesture,-.24+.12*gesture))
                hand=rig.data.bones['hand_'+side]
                # A lateral elbow plane lets the upper sleeve travel outside
                # the chest; the narrow-rig canonical lateral raise folded
                # this much broader sleeve through its fitted waistcoat.
                rotation=space.to_quaternion()@hand.matrix_local.to_quaternion()
                _solve_chain(rig,side,space@target,rotation,('upper_arm','forearm','hand'),space.to_3x3()@Vector((sign,0,-.35)))
                lower=rig.pose.bones['forearm_'+side];wrist=rig.pose.bones['hand_'+side]
                rotation=lower.matrix.to_quaternion()@lower.bone.matrix_local.to_quaternion().inverted()@hand.matrix_local.to_quaternion()
                wrist.matrix=Matrix.LocRotScale(wrist.head.copy(),rotation,Vector((1,1,1)))
                bpy.context.view_layer.update()
            for name in names:
                bone=rig.pose.bones[name];bone.rotation_mode='QUATERNION'
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=name)
                bone.keyframe_insert('location',frame=frame,group=name)
        for bag in _curves(action):
            for curve in bag.fcurves:
                if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
