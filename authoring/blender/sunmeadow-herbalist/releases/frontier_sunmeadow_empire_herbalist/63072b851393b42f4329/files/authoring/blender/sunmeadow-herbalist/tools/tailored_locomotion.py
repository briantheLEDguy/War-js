"""Fit civilian strides to the actual shortened leg chain and footwear."""
import math
import bpy
from mathutils import Matrix, Quaternion, Vector


def _dressed_legs():
    """Contact includes the divided oversmock, not only hidden trousers."""
    import numpy as np
    from apron_clearance import _surface
    coordinates=[];triangles=[];fields={};offset=0
    for obj in bpy.context.scene.objects:
        if not (obj.name=='trousers_continuous_tailored_surface' or obj.name.startswith(('herbalist_divided_smock_lappet','herbalist_lappet_turned_binding'))):continue
        points,faces,weights,world=_surface(obj);points=points@np.array(world).T
        coordinates.append(points);triangles.extend(tuple(i+offset for i in face) for face in faces)
        for name,(indices,values) in weights.items():fields.setdefault(name,[]).append((indices+offset,values))
        offset+=len(points)
    return np.concatenate(coordinates),triangles,{name:(np.concatenate([i for i,w in rows]),np.concatenate([w for i,w in rows])) for name,rows in fields.items()},Matrix.Identity(4)


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
        print('Fitting farmer ground contact: '+clip,flush=True)
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
            # The authored human hip bob may exceed the shortened farmer chain.
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
                    lowest=min((evaluated.matrix_world@vertex.co).z for vertex in evaluated.data.vertices)
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
    fit_stride_arms(rig)
    fit_action_arms(rig)
    fit_prone_contact(rig)


def fit_stride_arms(rig):
    """Counter-swing bent arms around the fitted chest, opposite each foot."""
    names=[part+'_'+side for side in ('L','R') for part in ('upper_arm','forearm','hand')]
    fingers=[bone.name for bone in rig.pose.bones if bone.name.startswith(('index_','middle_','ring_','pinky_','thumb_'))]
    for clip,duration in [('idle',60),('walk',30),('run',20)]:
        print('Fitting farmer arm counter-swing: '+clip,flush=True)
        action=bpy.data.actions[clip];poses=_sample_action(rig,action,duration)
        for bag in _curves(action):
            for curve in list(bag.fcurves):
                if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names+fingers):bag.fcurves.remove(curve)
        for frame in range(duration+1):
            bpy.context.scene.frame_set(frame);_restore_pose(rig,poses[frame])
            for side,sign,offset in [('L',1,0),('R',-1,.5)]:
                swing=math.cos((frame/duration+offset)*math.tau)
                shoulder=rig.pose.bones['upper_arm_'+side].head
                if clip=='run':
                    target=Vector((sign*(.315+.018*swing),-.08+.23*swing,shoulder.z-.42-.055*swing))
                    forward=Vector((sign*.06,-.70,-.55-.35*swing))
                elif clip=='walk':
                    target=Vector((sign*.325,-.065+.15*swing,shoulder.z-.52-.025*swing))
                    forward=Vector((sign*.04,-.25,-1))
                else:
                    target=Vector((sign*.305,-.075+.006*swing,shoulder.z-.58))
                    forward=Vector((sign*.025,-.14,-1))
                hand=rig.data.bones['hand_'+side]
                rotation=(hand.tail_local-hand.head_local).rotation_difference(forward)@hand.matrix_local.to_quaternion()
                _solve_chain(rig,side,target,rotation,('upper_arm','forearm','hand'),Vector((sign*1.0,.65,-1.5)))
                # A fixed world-facing palm breaks the wrist as the forearm
                # counter-swings behind the hip. Retain the anatomical wrist
                # alignment within that solved forearm's moving frame.
                lower=rig.pose.bones['forearm_'+side];wrist=rig.pose.bones['hand_'+side]
                rotation=lower.matrix.to_quaternion()@lower.bone.matrix_local.to_quaternion().inverted()@hand.matrix_local.to_quaternion()
                wrist.matrix=Matrix.LocRotScale(wrist.head.copy(),rotation,Vector((1,1,1)))
                bpy.context.view_layer.update()
                palm=hand.matrix_local.to_3x3().col[2].normalized()
                for name in (name for name in fingers if name.endswith('_'+side)):
                    bone=rig.pose.bones[name];rest=bone.bone
                    axis=(rest.tail_local-rest.head_local).normalized().cross(palm).normalized()
                    local_axis=rest.matrix_local.to_3x3().inverted()@axis
                    segment=int(name.split('_')[1])
                    flex=([12,24,17] if clip=='run' else [7,13,9])[segment-1]
                    if name.startswith('thumb_'):flex*=.45
                    bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion(local_axis,math.radians(flex))
            for name in names+fingers:
                bone=rig.pose.bones[name];bone.rotation_mode='QUATERNION'
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=name)
                bone.keyframe_insert('location',frame=frame,group=name)
        for bag in _curves(action):
            for curve in bag.fcurves:
                if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names+fingers):
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()


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
                target=Vector((sign*.30,-.34,1.28))
                forward=Vector((sign*.12,-1,-.04))
                if clip=='attack_melee' and side=='R':
                    strike=math.exp(-((phase-.48)/.14)**2)
                    target+=Vector((.025*strike,-.25*strike,.035*strike))
                elif clip=='attack_ranged' and side=='R':
                    wind=math.exp(-((phase-.27)/.14)**2);release=math.exp(-((phase-.58)/.12)**2)
                    target+=Vector((-.03*wind+.08*release,.19*wind-.23*release,.22*wind+.02*release))
                elif clip=='cast':
                    gesture=math.sin(math.pi*phase)**2
                    target=Vector((sign*(.18+.13*gesture),-.31-.16*gesture,1.30+.10*gesture))
                    forward=Vector((sign*.10,-1,.30*gesture))
                # Retain elbow flexion on the female foundation instead of
                # letting a fully extended reach sweep the sleeve into the torso.
                shoulder=rig.pose.bones['upper_arm_'+side].head
                delta=target-shoulder
                reach=(rig.pose.bones['upper_arm_'+side].length+rig.pose.bones['forearm_'+side].length)*.90
                if delta.length>reach:target=shoulder+delta.normalized()*reach
                hand=rig.data.bones['hand_'+side]
                rotation=(hand.tail_local-hand.head_local).rotation_difference(forward)@hand.matrix_local.to_quaternion()
                _solve_chain(rig,side,target,rotation,('upper_arm','forearm','hand'),Vector((sign*1.6,0,-.25)))
            for name in names:
                bone=rig.pose.bones[name];bone.rotation_mode='QUATERNION'
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=name);bone.keyframe_insert('location',frame=frame,group=name)
        for bag in _curves(action):
            for curve in bag.fcurves:
                if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def fit_prone_contact(rig):
    """Let the shortened body fall onto its forearms and extended boot soles."""
    print('Fitting farmer forearm/boot contact: death',flush=True)
    action=bpy.data.actions['death'];rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    names=[part+'_'+side for side in ('L','R') for part in ('thigh','shin','foot','toe','upper_arm','forearm','hand')]+['spine']
    # Sample the original action before replacing its limb channels.
    poses=_sample_action(rig,action,60)
    from apron_clearance import _surface,_skin
    skin_surface=_surface(bpy.data.objects['empire_herbalist_exposed_anatomy'])
    carried_surfaces=[_surface(obj) for obj in bpy.context.scene.objects if obj.type=='MESH'
                      and (obj.name=='work_belt' or obj.name.startswith('forged_buckle_frame') or 'folded_work_apron' in obj.name)]
    torso_surface=_surface(bpy.data.objects['herbalist_fitted_smock_torso'])
    torso_indices=[i for i,p in enumerate(torso_surface[0]) if 1.12<p[2]<1.45 and abs(p[0])<.19]
    if not torso_indices:raise RuntimeError('Missing actual torso support surface')
    trouser_surface=_dressed_legs()
    knee_indices={side:[i for i,p in enumerate(trouser_surface[0]) if .4<p[2]<.92 and p[0]*sign>.08] for side,sign in [('L',1),('R',-1)]}
    hand_indices={}
    for side in ('L','R'):
        membership={}
        for name,(indices,weights) in skin_surface[2].items():
            if name.endswith('_'+side) and name.startswith(('hand_','index_','middle_','ring_','pinky_','thumb_')):
                for index,weight in zip(indices,weights):membership[int(index)]=membership.get(int(index),0)+weight
        # Tiny inherited cross-hand weights must not make one hand react to
        # the other hand's unfinished pose during sequential contact fitting.
        hand_indices[side]=[index for index,weight in membership.items() if weight>.5]
    for bag in _curves(action):
        for curve in list(bag.fcurves):
            if any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):bag.fcurves.remove(curve)
    for frame in range(61):
        bpy.context.scene.frame_set(frame)
        _restore_pose(rig,poses[frame])
        t=max(0,min(1,(frame-10)/30));t=t*t*(3-2*t)
        # The broad pelvis rests slightly higher than the original human fall;
        # the long leather panel folds at its real waist seam as it contacts it.
        hips=rig.pose.bones['hips'];matrix=hips.matrix.copy();matrix.translation.z-=.24*t
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
        # The exposed buckle supports the prone torso before the hands settle.
        # Fit its real skin surface instead of hiding hardware below the floor.
        lowest=min([float(_skin(surface,rig)[:,2].min()) for surface in carried_surfaces]+[float(_skin(torso_surface,rig)[torso_indices,2].min())])
        settle=max(0,min(1,(t-.65)/.30));settle=settle*settle*(3-2*settle)
        adjustment=max(0,.004-lowest)+min(0,.004-lowest)*settle
        matrix=hips.matrix.copy();matrix.translation.z+=adjustment
        hips.matrix=matrix;bpy.context.view_layer.update()
        hips.keyframe_insert('location',frame=frame,group='hips')
        for side,sign in [('L',1),('R',-1)]:
            foot=rig.pose.bones['foot_'+side]
            hips=rig.pose.bones['thigh_'+side].head
            length=rig.pose.bones['thigh_'+side].length+rig.pose.bones['shin_'+side].length
            target=Vector((sign*.21,hips.y+length*.94,.34))
            ankle=foot.head.lerp(target,t)
            rotation=foot.matrix.to_quaternion().slerp(Quaternion(Vector((1,0,0)),math.pi/2)@rig.data.bones['foot_'+side].matrix_local.to_quaternion(),t)
            _solve_chain(rig,side,ankle,rotation,hint=Vector((0,0,-1)))
            # A safe final toe direction does not guarantee that the slerped
            # sole clears the floor halfway through the fall. Fit its actual
            # evaluated surface at every authored key, as in the planted gait.
            boot=bpy.data.objects['fitted_boot_'+str(sign)]
            for _ in range(2):
                evaluated=boot.evaluated_get(bpy.context.evaluated_depsgraph_get())
                lowest=min((evaluated.matrix_world@vertex.co).z for vertex in evaluated.data.vertices)
                adjustment=max(0,.004-lowest)
                if adjustment<.0001:break
                ankle.z+=adjustment
                _solve_chain(rig,side,ankle,rotation,hint=Vector((0,0,-1)))
            # The prone pole points toward the ground. Extend the actual leg
            # until its dressed knee clears it; ankle height alone cannot prove
            # this contact when the pelvis settles onto the torso support.
            for attempt in range(16):
                knee_low=float(_skin(trouser_surface,rig)[knee_indices[side],2].min())
                if knee_low>=.0035:break
                ankle.y+=.012
                _solve_chain(rig,side,ankle,rotation,hint=Vector((0,0,-1)))
            if knee_low<-.002:raise RuntimeError('Prone knee cannot clear ground: '+side+' '+str(frame))
            hand=rig.pose.bones['hand_'+side];rest=rig.data.bones['hand_'+side]
            shoulder=rig.pose.bones['upper_arm_'+side].head
            grounded_target=Vector((shoulder.x+sign*.11,shoulder.y-.18,.075))
            wrist=hand.head.lerp(grounded_target,t)
            # The fitted female sleeves need room around the oversmock while
            # the arms swing forward to brace. Widen the intermediate reach;
            # retain the existing supported terminal hand placement.
            wrist.x+=sign*.20*math.sin(math.pi*t)
            aligned=(rest.tail_local-rest.head_local).rotation_difference(Vector((sign*.08,-1,0)))@rest.matrix_local.to_quaternion()
            aligned=Quaternion(Vector((1,0,0)),-.35)@aligned
            rotation=hand.matrix.to_quaternion().slerp(aligned,t)
            hint=Vector((sign,0,-.85*t))
            _solve_chain(rig,side,wrist,rotation,('upper_arm','forearm','hand'),hint)
            # Fit fingertips as well as the wrist: their retained anatomy reaches
            # below the nominal palm plane during the final fall transition.
            for _ in range(2):
                lowest=min(_skin(skin_surface,rig)[hand_indices[side],2])
                settle=max(0,min(1,(t-.70)/.25));settle=settle*settle*(3-2*settle)
                correction=.004-lowest
                adjustment=max(0,correction)+min(0,correction)*settle
                if abs(adjustment)<.0001:break
                wrist.z+=adjustment
                _solve_chain(rig,side,wrist,rotation,('upper_arm','forearm','hand'),hint)
        for name in names:
            bone=rig.pose.bones[name];bone.rotation_mode='QUATERNION'
            bone.keyframe_insert('rotation_quaternion',frame=frame,group=name);bone.keyframe_insert('location',frame=frame,group=name)
    for bag in _curves(action):
        for curve in bag.fcurves:
            # Preserve the sampled parent rotation. Linearizing untouched,
            # sparse hip keys after IK moves the fitted hands off the ground.
            if curve.data_path=='pose.bones["hips"].location' or any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names+['apron_lower']):
                for key in curve.keyframe_points:key.interpolation='LINEAR'
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def refine_sole_contacts(rig):
    """Re-evaluate baked poses and fit both soles after all parent motion exists."""
    stationary={'idle','combat_idle','attack_melee','attack_ranged','cast'}
    from apron_clearance import _surface,_skin
    trousers=_dressed_legs()
    knees={side:[i for i,p in enumerate(trousers[0]) if .4<p[2]<.92 and p[0]*sign>.08] for side,sign in [('L',1),('R',-1)]}
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
                low=min((evaluated.matrix_world@vertex.co).z for vertex in evaluated.data.vertices)
                foot=rig.pose.bones['foot_'+side]
                ankle=foot.head.copy();correction=.004-low if clip in stationary or clip=='death' else max(0,.004-low)
                ankle.z+=correction
                if clip in stationary:lowering=max(lowering,-correction)
                targets.append((side,ankle,foot.matrix.to_quaternion()))
            # Keep both planted targets reachable for the shortened chain.
            if lowering>0:
                hips=rig.pose.bones['hips'];matrix=hips.matrix.copy();matrix.translation.z-=lowering+.002
                hips.matrix=matrix;bpy.context.view_layer.update()
            for side,ankle,rotation in targets:
                _solve_chain(rig,side,ankle,rotation,hint=Vector((0,0,-1)) if clip=='death' else Vector((0,-1,0)))
                if clip=='death' and frame>=20:
                    # The final ankle correction must retain the dressed knee
                    # contact. Solve both actual surfaces together after all
                    # parent channels have been baked.
                    boot=bpy.data.objects['fitted_boot_'+str(1 if side=='L' else -1)]
                    for attempt in range(32):
                        knee_low=float(_skin(trousers,rig)[knees[side],2].min())
                        evaluated=boot.evaluated_get(bpy.context.evaluated_depsgraph_get())
                        sole_low=min((evaluated.matrix_world@vertex.co).z for vertex in evaluated.data.vertices)
                        if knee_low>=.006:break
                        ankle.z+=.004-sole_low
                        if knee_low<.006:ankle.y+=.004
                        _solve_chain(rig,side,ankle,rotation,hint=Vector((0,0,-1)))
                    if knee_low<.002 or sole_low<-.002:raise RuntimeError('Final prone leg contact failed: '+side+' '+str(frame)+' knee='+str(knee_low)+' sole='+str(sole_low))
            for name in names:
                bone=rig.pose.bones[name]
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=name)
                bone.keyframe_insert('location',frame=frame,group=name)
            rig.pose.bones['hips'].keyframe_insert('location',frame=frame,group='hips')
        for bag in _curves(action):
            for curve in bag.fcurves:
                if curve.data_path=='pose.bones["hips"].location' or any(curve.data_path.startswith('pose.bones["'+name+'"]') for name in names):
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.view_layer.update()
