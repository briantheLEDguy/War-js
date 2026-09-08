"""Species-specific in-place motion solved against anatomical limb lengths.

Foot trajectories are authored in ground coordinates. Two-joint limb solutions
are baked to the existing deform skeleton, leaving no runtime IK dependency.
"""
import math
import bpy
from mathutils import Vector, Matrix, Quaternion
from quadruped_rig import key_pose_clip
from gait_curves import foot_trajectory

def smooth(t):return t*t*(3-2*t)

def reset(rig):
    rig.animation_data_create();rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()

def point_bone(rig,name,start,end,matrices):
    bone=rig.pose.bones[name];rest=bone.bone.matrix_local.to_quaternion()
    direction=Vector(end)-Vector(start)
    rotation=(rest@Vector((0,1,0))).rotation_difference(direction.normalized())@rest
    desired=Matrix.LocRotScale(Vector(start),rotation,Vector((1,1,1)))
    if bone.parent:
        basis=bone.bone.convert_local_to_pose(desired,bone.bone.matrix_local,parent_matrix=matrices[bone.parent.name],parent_matrix_local=bone.parent.bone.matrix_local,invert=True)
    else:basis=bone.bone.convert_local_to_pose(desired,bone.bone.matrix_local,invert=True)
    bone.matrix_basis=basis;matrices[name]=desired

def solve_joint(start,end,first,second,pole):
    """Preserve segment lengths, with a stable anatomical elbow/stifle plane."""
    axis=Vector(end)-Vector(start);distance=axis.length
    direction=axis.normalized();reach=min(first+second-.0001,max(abs(first-second)+.0001,distance))
    along=(first*first-second*second+reach*reach)/(2*reach)
    height=math.sqrt(max(0,first*first-along*along))
    bend=Vector(pole);bend=(bend-direction*bend.dot(direction)).normalized()
    joint=Vector(start)+direction*along+bend*height
    return joint,Vector(start)+direction*reach,abs(reach-distance)

def solve_leg(rig,limb,label,foot):
    names=(['shoulder','forearm','carpal','pastern_front','hoof_front'] if limb=='front' else ['thigh','shin','hock','pastern_hind','hoof_hind'])
    names=[name+'_'+label for name in names];bones=[rig.pose.bones[name] for name in names]
    matrices={bone.name:bone.matrix.copy() for bone in rig.pose.bones}
    rest=[bone.bone.head_local.copy() for bone in bones]
    start=bones[0].head.copy();foot=Vector(foot)
    # Distal hock/carpal and pastern orientation remains anatomical during stance.
    ankle=foot+(rest[2]-rest[4]);pastern=foot+(rest[3]-rest[4])
    original_ankle=ankle.copy()
    scapula=rig.pose.bones.get('scapula_'+label) if limb=='front' else None
    if scapula:
        origin=scapula.head.copy();rest_direction=scapula.tail-scapula.head;candidates=[]
        # The mobile shoulder blade supplies reach before the elbow is solved.
        # Choose the smallest anatomical scapular swing that can plant the foot.
        def candidate(angle):
            shoulder=origin+Quaternion(Vector((1,0,0)),angle)@rest_direction
            elbow,reached,error=solve_joint(shoulder,ankle,bones[0].length,bones[1].length,(0,1,0))
            score=error*error*10000+angle*angle*.006
            return (score,shoulder,elbow,reached,error)
        angles=[step*.018 for step in range(-35,36)];best=min(angles,key=lambda angle:candidate(angle)[0])
        # Refine the coarse bracket continuously: a one-degree search grid
        # otherwise leaves visible blade-angle steps between baked samples.
        lo=max(-.63,best-.018);hi=min(.63,best+.018)
        for _ in range(18):
            left=lo+(hi-lo)/3;right=hi-(hi-lo)/3
            if candidate(left)[0]<candidate(right)[0]:hi=right
            else:lo=left
        _,start,joint,ankle,error=candidate((lo+hi)/2)
        point_bone(rig,scapula.name,origin,start,matrices)
    else:joint,ankle,error=solve_joint(start,ankle,bones[0].length,bones[1].length,(0,1 if limb=='front' else -1,0))
    correction=ankle-original_ankle;pastern+=correction;foot+=correction
    points=[start,joint,ankle,pastern,foot]
    for index in range(4):point_bone(rig,names[index],points[index],points[index+1],matrices)
    point_bone(rig,names[4],foot,foot+(bones[4].bone.tail_local-bones[4].bone.head_local),matrices)
    return error

def local_records(rig):
    bpy.context.view_layer.update()
    records={}
    for bone in rig.pose.bones:
        if bone.parent:
            basis=bone.bone.convert_local_to_pose(bone.matrix,bone.bone.matrix_local,parent_matrix=bone.parent.matrix,parent_matrix_local=bone.parent.bone.matrix_local,invert=True)
        else:basis=bone.bone.convert_local_to_pose(bone.matrix,bone.bone.matrix_local,invert=True)
        location,rotation,scale=basis.decompose()
        records[bone.name]={'location':list(location),'rotation_euler':list(rotation.to_euler('XYZ')),'scale':list(scale)}
    return records

def mammal_clips(rig,kind,definition):
    scale=definition.get('scale',1);fps=60;clips=[];reports=[]
    periods={'idle':4,'walk':1.1,'run':.6,'graze':6,'sniff':3,'hop':.9,'attack':1.1,'hit':.7,'death':2.1}
    walking={'front_L':0,'front_R':.5,'hind_L':.75,'hind_R':.25}
    gallop={'front_L':.08,'front_R':.18,'hind_L':.57,'hind_R':.66}
    if kind=='brown_hare':gallop={'front_L':.16,'front_R':.19,'hind_L':.66,'hind_R':.69}
    for clip in definition['clips']:
        duration=periods[clip];last=round(duration*fps);frames=[];maximum_error=0
        for frame in range(last+1):
            reset(rig);phase=frame/last;time=phase*math.tau
            moving=clip in ['walk','run','hop'];running=clip in ['run','hop']
            pelvis=rig.pose.bones['pelvis'];bob=(.006*math.cos(time*2) if clip=='walk' else -.043+.010*math.cos(time*2) if running else .0015*math.sin(time))*scale
            matrix=pelvis.matrix.copy();matrix.translation.z+=bob;pelvis.matrix=matrix
            for name,angle in [('spine',.009*math.sin(time)),('chest',-.006*math.sin(time)),('neck_01',.014*math.sin(time+.5)),('head',.025*math.sin(time*.5))]:
                rig.pose.bones[name].rotation_mode='XYZ';rig.pose.bones[name].rotation_euler.x=angle
            if clip in ['graze','sniff']:
                lower=smooth(min(1,phase/.22))*smooth(min(1,(1-phase)/.22))
                extended='neck_root' in rig.pose.bones
                if extended:rig.pose.bones['neck_root'].rotation_euler.x=.80*lower
                rig.pose.bones['neck_base'].rotation_euler.x=(.55 if extended else 1.4)*lower
                rig.pose.bones['neck_01'].rotation_euler.x=(.35 if extended else .4)*lower
                rig.pose.bones['neck_02'].rotation_euler.x=(.15 if extended else .25)*lower
                rig.pose.bones['head'].rotation_euler.x=(-.05 if extended else -.2)*lower
                rig.pose.bones['jaw'].rotation_euler.x=.10*lower*max(0,math.sin(time*9))
            if clip=='attack':
                lunge=math.sin(math.pi*phase)**4
                rig.pose.bones['neck_01'].rotation_euler.x=-.4*lunge
                rig.pose.bones['jaw'].rotation_euler.x=.50*math.sin(math.pi*phase)**2
            if clip=='hit':
                recoil=math.sin(math.pi*phase)*math.exp(-phase*2)
                rig.pose.bones['chest'].rotation_euler.y=.18*recoil
                rig.pose.bones['head'].rotation_euler.z=-.25*recoil
            bpy.context.view_layer.update()
            for side,label in [(1,'L'),(-1,'R')]:
                if 'ear_'+label in rig.pose.bones:
                    rig.pose.bones['ear_'+label].rotation_euler.y=side*.14*max(0,math.sin(time*2+side*.7))**8
                for limb in ['front','hind']:
                    suffix='hoof_front' if limb=='front' else 'hoof_hind';foot=rig.data.bones[suffix+'_'+label].head_local.copy()
                    if moving:
                        p=(phase+(gallop if running else walking)[limb+'_'+label])%1;stance=.24 if running else .64
                        stride=(.48 if running else .27)*scale
                        offset,height=foot_trajectory(p,stance,stride,(.15 if running else .065)*scale);foot.y+=offset;foot.z+=height
                    maximum_error=max(maximum_error,solve_leg(rig,limb,label,foot))
            for index in range(1,4):
                name=f'tail_{index:02}'
                if name in rig.pose.bones:rig.pose.bones[name].rotation_euler.z=.09*math.sin(time+index*.4)
            if clip=='death':
                collapse=smooth(min(1,phase/.7));p=rig.pose.bones['pelvis'];matrix=p.matrix.copy()
                matrix.translation.z-=.35*scale*collapse;p.matrix=matrix;p.rotation_euler.y+=1.4*collapse
            records=local_records(rig);records['root']={'location':[0,0,0],'rotation_euler':[0,0,0],'scale':[1,1,1]};frames.append((frame,records))
        action=key_pose_clip(rig,clip,frames,fps);clips.append(action)
        locomotion=None
        if clip in ['walk','run','hop']:
            running=clip!='walk';stance=.24 if running else .64;stride=(.48 if running else .27)*scale
            locomotion={'stride_m':stride,'stance_fraction':stance,'phase_offsets':gallop if running else walking,'speed_mps':stride/(stance*duration),'foot_lift_m':(.15 if running else .065)*scale,'trajectory':'constant_velocity_stance_c1_return'}
        reports.append({'clip':clip,'duration':last/fps,'frames':last+1,'maximum_ik_reach_error_m':maximum_error,'loop':clip not in ['attack','hit','death'],'motion_space':'in_place','locomotion':locomotion,'status':'deformation_review_required'})
    reset(rig)
    return clips,reports

def bird_clips(rig,kind,definition):
    actions=[];reports=[]
    for clip,duration in [('idle',4),('hop',.8),('fly',.8)]:
        last=round(duration*30);frames=[]
        for frame in range(last+1):
            reset(rig);phase=frame/last;wave=math.sin(phase*math.tau)
            pelvis=rig.pose.bones['pelvis'];matrix=pelvis.matrix.copy()
            if clip=='hop':matrix.translation.z+=.06*max(0,math.sin(math.pi*phase))**2
            elif clip=='fly':matrix.translation.z+=.007*math.sin(phase*math.tau*2)
            pelvis.matrix=matrix
            rig.pose.bones['head'].rotation_euler.z=.12*math.sin(phase*math.tau)
            rig.pose.bones['jaw'].rotation_euler.x=.06*max(0,math.sin(phase*math.tau*3))**4 if clip=='idle' else 0
            bpy.context.view_layer.update()
            for side,label in [(1,'L'),(-1,'R')]:
                names=[name+'_'+label for name in ['wing_upper','wing_lower','wing_hand']];matrices={bone.name:bone.matrix.copy() for bone in rig.pose.bones};start=rig.pose.bones[names[0]].head.copy()
                folded=[Vector((side*.20,1,-.25)),Vector((side*.02,-1,-.15)),Vector((side*.05,1,-.15))]
                for index,name in enumerate(names):
                    bone=rig.pose.bones[name];rest=bone.bone.tail_local-bone.bone.head_local
                    if clip=='fly':
                        flap=-side*(.78*wave+index*.12*math.sin(phase*math.tau-.55))
                        direction=Quaternion(Vector((0,1,0)),flap)@rest.normalized()
                    else:direction=folded[index].normalized()
                    end=start+direction*bone.length;point_bone(rig,name,start,end,matrices);start=end
                if clip=='fly':
                    rig.pose.bones['bird_thigh_'+label].rotation_euler.x=-.8
                    rig.pose.bones['bird_shin_'+label].rotation_euler.x=1.4
                    rig.pose.bones['bird_foot_'+label].rotation_euler.x=.7
                elif clip=='hop':
                    crouch=-.25*math.cos(phase*math.tau);rig.pose.bones['bird_thigh_'+label].rotation_euler.x=crouch
                    rig.pose.bones['bird_shin_'+label].rotation_euler.x=-crouch*.8
            rig.pose.bones['tail'].rotation_euler.x=.08*wave
            pose=local_records(rig);pose['root']={'location':[0,0,0],'rotation_euler':[0,0,0],'scale':[1,1,1]};frames.append((frame,pose))
        actions.append(key_pose_clip(rig,clip,frames,30));reports.append({'clip':clip,'duration':duration,'frames':last+1,'loop':True,'motion_space':'in_place','status':'deformation_review_required'})
    reset(rig);return actions,reports
