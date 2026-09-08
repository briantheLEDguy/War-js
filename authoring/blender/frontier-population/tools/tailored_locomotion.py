"""Fit civilian strides to the actual shortened leg chain and footwear."""
import math
import bpy
from mathutils import Matrix, Quaternion, Vector


def _curves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield bag


def _solve_chain(rig, side, ankle, rotation, parts=('thigh','shin','foot'), hint=Vector((0,-1,0))):
    upper=rig.pose.bones[parts[0]+'_'+side];lower=rig.pose.bones[parts[1]+'_'+side];foot=rig.pose.bones[parts[2]+'_'+side]
    start=upper.head.copy();delta=ankle-start;a=upper.length;b=lower.length
    distance=min(max(delta.length,abs(a-b)+.001),a+b-.001)
    axis=delta.normalized();bend=(hint-axis*hint.dot(axis)).normalized()
    along=(a*a-b*b+distance*distance)/(2*distance)
    knee=start+axis*along+bend*math.sqrt(max(0,a*a-along*along));end=start+axis*distance
    q=(upper.tail-upper.head).rotation_difference(knee-start)@upper.matrix.to_quaternion()
    upper.matrix=Matrix.LocRotScale(start,q,Vector((1,1,1)));bpy.context.view_layer.update()
    q=(lower.tail-lower.head).rotation_difference(end-lower.head)@lower.matrix.to_quaternion()
    lower.matrix=Matrix.LocRotScale(lower.head.copy(),q,Vector((1,1,1)));bpy.context.view_layer.update()
    foot.matrix=Matrix.LocRotScale(foot.head.copy(),rotation,Vector((1,1,1)));bpy.context.view_layer.update()


def _solve_leg(rig, side, ankle, rotation):
    _solve_chain(rig,side,ankle,rotation)


def _sample_action(rig,action,duration):
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    poses=[]
    for frame in range(duration+1):
        for bone in rig.pose.bones:bone.matrix_basis.identity()
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        poses.append({bone.name:bone.matrix_basis.copy() for bone in rig.pose.bones})
    return poses


def _restore_pose(rig,pose):
    for name,matrix in pose.items():rig.pose.bones[name].matrix_basis=matrix
    bpy.context.view_layer.update()


def fit_locomotion(rig):
    names=[part+'_'+side for side in ('L','R') for part in ('thigh','shin','foot','toe')]
    rotations={side:rig.data.bones['foot_'+side].matrix_local.to_quaternion() for side in ('L','R')}
    specs=[('walk',30,.16,.11),('run',20,.23,.16),('idle',60,0,0),('combat_idle',80,0,0),
           ('attack_melee',30,0,0),('attack_ranged',40,0,0),('cast',60,0,0),('jump',40,0,0)]
    for clip,duration,stride,lift in specs:
        print('Fitting dwarf ground contact: '+clip,flush=True)
        action=bpy.data.actions[clip]
        poses=_sample_action(rig,action,duration)
        for bag in _curves(action):
            for curve in list(bag.fcurves):
                if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):bag.fcurves.remove(curve)
        rig.animation_data.action=action
        if action.slots:rig.animation_data.action_slot=action.slots[0]
        for frame in range(duration+1):
            bpy.context.scene.frame_set(frame)
            _restore_pose(rig,poses[frame])
            for name in names:rig.pose.bones[name].matrix_basis.identity()
            bpy.context.view_layer.update()
            # The authored human hip bob may exceed the shortened dwarf chain.
            # Lower the pelvis before IK so planted soles can reach the ground.
            if clip!='jump':
                excess=0
                for side,sign,offset in [('L',1,0),('R',-1,.5)]:
                    phase=(frame/duration+offset)%1
                    if stride and math.sin((phase-.5)*math.tau)>.001:continue
                    upper=rig.pose.bones['thigh_'+side];lower=rig.pose.bones['shin_'+side]
                    target=Vector((sign*.205,-stride*math.cos(phase*math.tau),.081))
                    delta=upper.head-target;reach=upper.length+lower.length-.012
                    height=math.sqrt(max(.001,reach*reach-delta.x*delta.x-delta.y*delta.y))
                    excess=max(excess,delta.z-height)
                if excess>0:
                    hips=rig.pose.bones['hips'];matrix=hips.matrix.copy();matrix.translation.z-=excess
                    hips.matrix=matrix;bpy.context.view_layer.update()
            for side,sign,offset in [('L',1,0),('R',-1,.5)]:
                phase=(frame/duration+offset)%1
                swing=max(0,math.sin((phase-.5)*math.tau))
                y=-stride*math.cos(phase*math.tau)
                jump_height=max(0,rig.pose.bones['hips'].head.z-rig.data.bones['hips'].head_local.z) if clip=='jump' else 0
                ankle=Vector((sign*.205,y,.081+lift*swing+jump_height))
                pitch=math.radians(-8*math.cos(phase*math.tau)+8*math.sin(phase*math.tau)) if stride else 0
                rotation=Quaternion(Vector((1,0,0)),pitch)@rotations[side]
                _solve_leg(rig,side,ankle,rotation)
                # Fit the planted sole, including its curved toe and heel, to the
                # ground. A foot-bone angle alone can drive the toe through it.
                boot=bpy.data.objects['fitted_boot_'+str(sign)]
                for _ in range(2):
                    evaluated=boot.evaluated_get(bpy.context.evaluated_depsgraph_get())
                    lowest=min((evaluated.matrix_world@Vector(corner)).z for corner in evaluated.bound_box)
                    grounded=swing<.001 and jump_height<.001
                    adjustment=.004-lowest if grounded else max(0,.004-lowest)
                    if abs(adjustment)<.0001:break
                    ankle.z+=adjustment
                    _solve_leg(rig,side,ankle,rotation)
            for name in names:
                bone=rig.pose.bones[name];bone.rotation_mode='QUATERNION'
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=name)
                bone.keyframe_insert('location',frame=frame,group=name)
            rig.pose.bones['hips'].keyframe_insert('location',frame=frame,group='hips')
        for bag in _curves(action):
            for curve in bag.fcurves:
                if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    fit_action_arms(rig)
    fit_prone_contact(rig)


def fit_action_arms(rig):
    """Fit compact unarmed defense, throw and spell gestures to the real chest."""
    names=[part+'_'+side for side in ('L','R') for part in ('upper_arm','forearm','hand')]
    for clip,duration in [('attack_melee',30),('attack_ranged',40),('cast',60)]:
        action=bpy.data.actions[clip];poses=_sample_action(rig,action,duration)
        for bag in _curves(action):
            for curve in list(bag.fcurves):
                if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):bag.fcurves.remove(curve)
        for frame in range(duration+1):
            bpy.context.scene.frame_set(frame);_restore_pose(rig,poses[frame]);phase=frame/duration
            for side,sign in [('L',1),('R',-1)]:
                target=Vector((sign*.30,-.34,.96))
                forward=Vector((sign*.12,-1,-.04))
                if clip=='attack_melee' and side=='R':
                    strike=math.exp(-((phase-.48)/.14)**2)
                    target+=Vector((.10*strike,-.25*strike,.035*strike))
                elif clip=='attack_ranged' and side=='R':
                    wind=math.exp(-((phase-.27)/.14)**2);release=math.exp(-((phase-.58)/.12)**2)
                    target+=Vector((-.03*wind+.08*release,.19*wind-.23*release,.22*wind+.02*release))
                elif clip=='cast':
                    gesture=math.sin(math.pi*phase)**2
                    target=Vector((sign*(.18+.13*gesture),-.31-.16*gesture,.98+.10*gesture))
                    forward=Vector((sign*.10,-1,.30*gesture))
                hand=rig.data.bones['hand_'+side]
                rotation=(hand.tail_local-hand.head_local).rotation_difference(forward)@hand.matrix_local.to_quaternion()
                _solve_chain(rig,side,target,rotation,('upper_arm','forearm','hand'),Vector((sign,0,-.25)))
            for name in names:
                bone=rig.pose.bones[name];bone.rotation_mode='QUATERNION'
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=name);bone.keyframe_insert('location',frame=frame,group=name)
        for bag in _curves(action):
            for curve in bag.fcurves:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def fit_prone_contact(rig):
    """Let the shortened body fall onto its forearms and extended boot soles."""
    print('Fitting dwarf forearm/boot contact: death',flush=True)
    action=bpy.data.actions['death'];rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    names=[part+'_'+side for side in ('L','R') for part in ('thigh','shin','foot','toe','upper_arm','forearm','hand')]+['spine']
    # Sample the original action before replacing its limb channels.
    poses=_sample_action(rig,action,60)
    for bag in _curves(action):
        for curve in list(bag.fcurves):
            if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):bag.fcurves.remove(curve)
    for frame in range(61):
        bpy.context.scene.frame_set(frame)
        _restore_pose(rig,poses[frame])
        t=max(0,min(1,(frame-10)/30));t=t*t*(3-2*t)
        # The broad pelvis rests slightly higher than the original human fall;
        # the long leather panel folds at its real waist seam as it contacts it.
        hips=rig.pose.bones['hips'];matrix=hips.matrix.copy();matrix.translation.z+=.095*t
        hips.matrix=matrix;bpy.context.view_layer.update()
        spine=rig.pose.bones['spine']
        spine.matrix=Matrix.LocRotScale(spine.head.copy(),Quaternion(Vector((1,0,0)),.20*t)@spine.matrix.to_quaternion(),Vector((1,1,1)))
        bpy.context.view_layer.update()
        hinge=rig.pose.bones.get('apron_lower')
        if hinge:
            basis=hinge.bone.matrix_local.to_3x3().normalized()
            hinge.rotation_mode='QUATERNION'
            hinge.rotation_quaternion=(basis.inverted()@Quaternion(Vector((1,0,0)),.62*t).to_matrix()@basis).to_quaternion()
            hinge.keyframe_insert('rotation_quaternion',frame=frame,group=hinge.name)
        hips.keyframe_insert('location',frame=frame,group='hips')
        for side,sign in [('L',1),('R',-1)]:
            foot=rig.pose.bones['foot_'+side]
            hips=rig.pose.bones['thigh_'+side].head
            length=rig.pose.bones['thigh_'+side].length+rig.pose.bones['shin_'+side].length
            target=Vector((sign*.21,hips.y+length*.87,.34))
            ankle=foot.head.lerp(target,t)
            rotation=foot.matrix.to_quaternion().slerp(Quaternion(Vector((1,0,0)),math.pi/2)@rig.data.bones['foot_'+side].matrix_local.to_quaternion(),t)
            _solve_chain(rig,side,ankle,rotation,hint=Vector((0,0,-1)))
            # A safe final toe direction does not guarantee that the slerped
            # sole clears the floor halfway through the fall. Fit its actual
            # evaluated surface at every authored key, as in the planted gait.
            boot=bpy.data.objects['fitted_boot_'+str(sign)]
            for _ in range(2):
                evaluated=boot.evaluated_get(bpy.context.evaluated_depsgraph_get())
                lowest=min((evaluated.matrix_world@Vector(corner)).z for corner in evaluated.bound_box)
                adjustment=max(0,.004-lowest)
                if adjustment<.0001:break
                ankle.z+=adjustment
                _solve_chain(rig,side,ankle,rotation,hint=Vector((0,0,-1)))
            hand=rig.pose.bones['hand_'+side];rest=rig.data.bones['hand_'+side]
            wrist=hand.head.lerp(Vector((sign*.54,.055,.10)),t)
            aligned=(rest.tail_local-rest.head_local).rotation_difference(Vector((sign*.08,-1,0)))@rest.matrix_local.to_quaternion()
            rotation=hand.matrix.to_quaternion().slerp(aligned,t)
            _solve_chain(rig,side,wrist,rotation,('upper_arm','forearm','hand'),Vector((sign,0,0)))
        for name in names:
            bone=rig.pose.bones[name];bone.rotation_mode='QUATERNION'
            bone.keyframe_insert('rotation_quaternion',frame=frame,group=name);bone.keyframe_insert('location',frame=frame,group=name)
    for bag in _curves(action):
        for curve in bag.fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def refine_sole_contacts(rig):
    """Re-evaluate baked poses and fit both soles after all parent motion exists."""
    stationary={'idle','combat_idle','attack_melee','attack_ranged','cast'}
    names=[part+'_'+side for side in ('L','R') for part in ('thigh','shin','foot')]
    for clip,duration in [('idle',60),('combat_idle',80),('attack_melee',30),('attack_ranged',40),
                          ('cast',60),('walk',30),('run',20),('jump',40),('death',60)]:
        print('Refining baked sole contact: '+clip,flush=True)
        action=bpy.data.actions[clip];poses=_sample_action(rig,action,duration)
        for frame in range(duration+1):
            bpy.context.scene.frame_set(frame);_restore_pose(rig,poses[frame])
            targets=[];lowering=0.
            for side,sign in [('L',1),('R',-1)]:
                boot=bpy.data.objects['fitted_boot_'+str(sign)]
                evaluated=boot.evaluated_get(bpy.context.evaluated_depsgraph_get())
                low=min((evaluated.matrix_world@Vector(corner)).z for corner in evaluated.bound_box)
                foot=rig.pose.bones['foot_'+side]
                ankle=foot.head.copy();correction=.004-low if clip in stationary else max(0,.004-low)
                ankle.z+=correction
                if clip in stationary:lowering=max(lowering,-correction)
                targets.append((side,ankle,foot.matrix.to_quaternion()))
            # Keep both planted targets reachable for the shortened chain.
            if lowering>0:
                hips=rig.pose.bones['hips'];matrix=hips.matrix.copy();matrix.translation.z-=lowering+.002
                hips.matrix=matrix;bpy.context.view_layer.update()
            for side,ankle,rotation in targets:
                _solve_chain(rig,side,ankle,rotation,hint=Vector((0,0,-1)) if clip=='death' else Vector((0,-1,0)))
            for name in names:
                bone=rig.pose.bones[name]
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=name)
                bone.keyframe_insert('location',frame=frame,group=name)
            rig.pose.bones['hips'].keyframe_insert('location',frame=frame,group='hips')
        for bag in _curves(action):
            for curve in bag.fcurves:
                if curve.data_path.startswith('pose.bones["hips"]') or any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
