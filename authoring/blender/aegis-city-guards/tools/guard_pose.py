"""Analytical two-bone guard holds layered over the canonical locomotion clips."""
import math
import bpy
from mathutils import Vector, Matrix, Quaternion

GRIP_LOCAL=Vector((0,.075,-.01))
GRIPS={
    'standard':{'R':(-.32,-.26,1.13),'L':(.32,-.22,1.12)},
    'halberd':{'R':(-.22,-.30,1.15),'L':(.13,-.30,1.47)},
    'crossbow':{'R':(-.25,-.30094,1.26531),'L':(.20,-.33609,1.31453)},
    'captain':{'R':(-.33,-.11,1.03),'L':(.32,-.18,1.08)},
}


def aim(rig,name,direction):
    bone=rig.pose.bones[name]
    rest=bone.bone.matrix_local.to_quaternion()
    rotation=(rest @ Vector((0,1,0))).rotation_difference(Vector(direction).normalized()) @ rest
    bone.matrix=Matrix.LocRotScale(bone.head.copy(),rotation,Vector((1,1,1)))
    bpy.context.view_layer.update()


def hold(rig,side,target,bend):
    upper=rig.pose.bones['upper_arm_'+side]; fore=rig.pose.bones['forearm_'+side]
    origin=upper.head.copy(); target=Vector(target)
    direction=target-origin; distance=direction.length; direction.normalize()
    a=upper.length; b=fore.length
    distance=min(distance,a+b-.0001)
    along=(a*a-b*b+distance*distance)/(2*distance)
    height=math.sqrt(max(0,a*a-along*along))
    normal=Vector(bend)-origin; normal-=direction*normal.dot(direction); normal.normalize()
    elbow=origin+direction*along+normal*height
    aim(rig,upper.name,elbow-origin)
    aim(rig,fore.name,target-fore.head)
    aim(rig,'hand_'+side,(0,-.7,-.7))


def hold_grip(rig,side,grip,bend):
    aim(rig,'hand_'+side,(0,-.7,-.7))
    offset=rig.pose.bones['hand_'+side].matrix.to_quaternion() @ GRIP_LOCAL
    hold(rig,side,Vector(grip)-offset,bend)


def correct(rig,variant):
    rig.animation_data_create(); rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks: track.mute=True
    rig.data.pose_position='POSE'
    for bone in rig.pose.bones: bone.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    for side in ['R','L']:
        hold_grip(rig,side,GRIPS[variant][side],(-.42 if side=='R' else .42,-.03,1.20))
    names=[f'{bone}_{side}' for side in ['L','R'] for bone in ['shoulder','upper_arm','forearm','hand']]
    for bone in rig.pose.bones:
        if any(bone.name.startswith(prefix) for prefix in ['index_','middle_','ring_','pinky_']):
            bone.rotation_mode='QUATERNION'; bone.rotation_quaternion=Quaternion((1,0,0),.95)
            names.append(bone.name)
        elif bone.name.startswith('thumb_'):
            bone.rotation_mode='QUATERNION'; bone.rotation_quaternion=Quaternion((0,0,1),.35)
            names.append(bone.name)
    rotations={name:rig.pose.bones[name].matrix_basis.to_quaternion().copy() for name in names}
    bpy.context.view_layer.update()
    deformations={side:rig.pose.bones['hand_'+side].matrix @ rig.data.bones['hand_'+side].matrix_local.inverted() for side in ['L','R']}
    wrists={side:rig.pose.bones['hand_'+side].head.copy() for side in ['L','R']}
    # Bake constant arm holds per clip; the chest/root motion still drives the arms.
    # Clip-specific attack/reload gestures remain a later animation refinement.
    for action in list(bpy.data.actions):
        if not action.slots: continue
        start,end=map(float,action.frame_range)
        curves=action.layers[0].strips[0].channelbag(action.slots[0]).fcurves
        for name,rotation in rotations.items():
            prefix=f'pose.bones["{name}"].'
            for curve in list(curves):
                if curve.data_path.startswith(prefix): curves.remove(curve)
            for axis,value in enumerate(rotation):
                curve=curves.new(prefix+'rotation_quaternion',index=axis)
                curve.keyframe_points.insert(start,value)
                curve.keyframe_points.insert(end,value)
    rig.animation_data.action=None
    rig.data.pose_position='REST'
    return deformations,wrists


def place_weapon(obj,variant,deformations,wrists,bone):
    if bone not in {'hand_L','hand_R'}: return
    side=bone[-1]; wrist=wrists[side]
    if variant=='halberd':
        right=Vector(GRIPS[variant]['R']); left=Vector(GRIPS[variant]['L'])
        rotation=Vector((0,0,1)).rotation_difference((left-right).normalized()).to_matrix().to_4x4()
        placement=Matrix.Translation(right) @ rotation @ Matrix.Translation((.55,.26,-1.15))
    else:
        grip=Vector(GRIPS[variant][side])
        if variant=='crossbow': offset=Vector((0,0,.12))
        elif side=='R': offset=Vector((grip.x+.55,grip.y+.26,0))
        else: offset=Vector((grip.x+.06-.54,grip.y-.09+.345,grip.z-.04-1.075))
        placement=Matrix.Translation(offset)
    obj.data.transform(deformations[side].inverted() @ placement)


def audit_holds(rig,variant,deformations):
    records=[]
    rig.data.pose_position='POSE'
    for action in list(bpy.data.actions):
        if not action.slots: continue
        rig.animation_data.action=action; rig.animation_data.action_slot=action.slots[0]
        start,end=action.frame_range
        for step in range(5):
            frame=start+(end-start)*step/4
            bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame))
            for side in ['R','L']:
                if variant=='captain': continue
                driver='R' if variant in {'crossbow','halberd'} else side
                hand=rig.pose.bones['hand_'+side].matrix @ GRIP_LOCAL
                bind=deformations[driver].inverted() @ Vector(GRIPS[variant][side])
                weapon=(rig.pose.bones['hand_'+driver].matrix @ rig.data.bones['hand_'+driver].matrix_local.inverted()) @ bind
                records.append({'clip':action.name,'frame':round(frame,3),'hand':side,'gap_m':round((hand-weapon).length,6)})
    rig.animation_data.action=None; rig.data.pose_position='REST'
    maximum=max((r['gap_m'] for r in records),default=0)
    print('GRIP_AUDIT',variant,maximum,flush=True)
    if maximum>.015: raise ValueError(f'{variant}: grip gap exceeds 15mm: {maximum}')
    return {'max_gap_m':maximum,'samples':records}
