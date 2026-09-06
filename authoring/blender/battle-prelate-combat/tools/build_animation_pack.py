"""Original contact-driven combat choreography; bake control constraints, never geometry.

Run in Blender 5: --background --factory-startup --python-exit-code 1 --python this_file.
The editable scene retains keyed wrist/foot targets and the untouched reference body.
Runtime exports contain only canonical nodes and baked animation tracks.
"""
from pathlib import Path
import json
import math
import hashlib
import struct
import bpy
from mathutils import Matrix, Quaternion, Vector, Euler

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
MODEL = REPO / 'public/assets/models'
CONTRACT = json.loads((REPO / 'src/game/animation/battlePrelateMotions.json').read_text())
# Dense bake limits grip error when Three.js interpolates between contact poses.
FPS = 120


def smooth(t):
    t = max(0, min(1, t))
    return t*t*(3-2*t)


def interpolate(keys, t, through_contact=False):
    for i, ((ta, a), (tb, b)) in enumerate(zip(keys, keys[1:])):
        if t <= tb:
            if through_contact:
                u=max(0,min(1,(t-ta)/max(.0001,tb-ta)))
                # Only contact retains velocity; windup and recovery settle.
                def tangent(index):
                    contact_index = len(keys)-3
                    if index!=contact_index: return Vector((0,0,0))
                    return (Vector(keys[index+1][1])-Vector(keys[index-1][1]))/(keys[index+1][0]-keys[index-1][0])
                return Vector(a)*(2*u**3-3*u*u+1)+Vector(b)*(-2*u**3+3*u*u)+tangent(i)*(u**3-2*u*u+u)*(tb-ta)+tangent(i+1)*(u**3-u*u)*(tb-ta)
            return Vector(a).lerp(Vector(b), smooth((t-ta)/max(.0001, tb-ta)))
    return Vector(keys[-1][1])


def target(name):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.empty_display_type = 'ARROWS'
    obj.empty_display_size = .08
    obj.rotation_mode = 'QUATERNION'
    return obj


def controls(rig):
    result = {}
    for side in ['L', 'R']:
        for end, parent in [('hand', 'forearm'), ('foot', 'shin')]:
            name = f'{end}_{side}'
            ctl = target(f'CTL_{name}')
            ctl.matrix_world = rig.pose.bones[name].matrix.copy()
            ik = rig.pose.bones[f'{parent}_{side}'].constraints.new('IK')
            ik.name = 'Contact position (baked for runtime)'
            ik.target = ctl
            ik.chain_count = 2
            ik.use_stretch = False
            ik.iterations = 128
            rotation = rig.pose.bones[name].constraints.new('COPY_ROTATION')
            rotation.name = 'Contact orientation (baked for runtime)'
            rotation.target = ctl
            rotation.owner_space = 'WORLD'
            rotation.target_space = 'WORLD'
            result[name] = ctl
    return result


# Positions are Blender metres, forward -Y. Each tuple defines wrist-socket
# position, shaft direction and body yaw at anticipation/contact/follow-through.
GESTURES = {
    'diagonal': ((-.31,-.27,1.49),(-.72,.06,.69), (.15,-.55,1.08),(-.48,-.82,-.30), (.22,-.42,.99),(-.20,-.67,-.71), -.24,.28),
    'return': ((.39,-.08,1.20),(.95,-.28,.04), (-.28,-.55,1.16),(-.90,-.43,.04), (-.46,-.13,1.23),(-.70,.71,.04), .54,-.54),
    'descending': ((-.34,-.02,1.66),(-.48,.71,.51), (-.16,-.54,1.04),(-.76,-.49,-.43), (-.31,-.27,.86),(-.42,.12,-.90), -.40,.32),
    'empowered': ((-.42,.02,1.52),(-.67,.68,.30), (.20,-.59,1.15),(-.46,-.87,-.15), (.29,-.25,.91),(.10,-.29,-.95), -.55,.52),
    'drive': ((-.36,-.07,.98),(-.84,.43,.33), (-.12,-.61,1.07),(-.78,-.60,-.17), (-.27,-.36,1.20),(-.86,-.33,.39), -.30,.27),
    'overhead': ((-.08,.02,1.89),(-.18,.86,.48), (-.06,-.55,1.01),(-.58,-.59,-.56), (-.12,-.27,.73),(-.27,.12,-.95), -.14,.16),
    'thrust': ((-.30,-.12,1.39),(-.72,-.68,.05), (-.12,-.62,1.40),(-.72,-.69,.05), (-.14,-.54,1.40),(-.72,-.69,.05), -.24,.22),
    'ward': ((-.16,-.37,1.33),(-.6,0,.8), (-.16,-.43,1.36),(-.50,-.10,.86), (-.14,-.40,1.32),(-.65,0,.76), -.07,.02),
    'chant': ((-.17,-.35,1.29),(-.70,0,.71), (-.15,-.37,1.33),(-.65,0,.76), (-.15,-.36,1.31),(-.70,0,.71), -.03,.03),
    'heal': ((-.17,-.32,1.28),(-.70,0,.71), (-.18,-.40,1.36),(-.62,-.08,.78), (-.16,-.37,1.32),(-.70,0,.71), -.07,.04),
    'place': ((-.21,-.29,1.17),(-.72,0,.69), (-.23,-.37,1.06),(-.75,-.1,.65), (-.22,-.34,1.09),(-.74,0,.67), -.07,.06),
    'sermon': ((-.15,-.32,1.37),(-.55,.03,.84), (-.18,-.32,1.58),(-.50,-.03,.86), (-.18,-.33,1.54),(-.55,0,.84), -.07,.05),
}
FREE_HAND = {'ward': (.20,-.58,1.46), 'chant': (.27,-.40,1.43), 'heal': (.38,-.44,1.34), 'place': (.16,-.48,.84), 'sermon': (.40,-.34,1.52)}


def build():
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT/'review').mkdir(exist_ok=True)
    bpy.ops.import_scene.gltf(filepath=str(MODEL/'chr_civic_battle_prelate_t1_m.glb'))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    original_actions = list(bpy.data.actions)
    rig.animation_data.action = next(a for a in original_actions if a.name == 'idle')
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    neutral = {b.name: b.matrix_basis.copy() for b in rig.pose.bones}
    # Evaluate actual socket offsets from the frozen canonical rest hierarchy.
    hand_socket = {}
    for side in ['L','R']:
        hand = rig.pose.bones[f'hand_{side}']
        socket = bpy.data.objects[f'socket_hand_{side}']
        hand_socket[side] = hand.matrix.inverted() @ socket.matrix_world
    # Preserve the embedded opening's timing/path, then enlarge it before IK.
    opening = next(a for a in original_actions if a.name == 'attack_melee')
    rig.animation_data.action = opening
    opening_samples = []
    opening_rotations = []
    start, end = opening.frame_range
    for i in range(121):
        source_frame = start+(end-start)*i/120
        bpy.context.scene.frame_set(int(source_frame), subframe=source_frame % 1)
        bpy.context.view_layer.update()
        opening_samples.append(bpy.data.objects['socket_hand_R'].matrix_world.copy())
        rotation = opening_samples[-1].to_quaternion()
        if opening_rotations and rotation.dot(opening_rotations[-1]) < 0: rotation.negate()
        opening_rotations.append(rotation)
    rig.animation_data_clear()
    bpy.ops.import_scene.gltf(filepath=str(MODEL/'wep_civic_battle_prelate_dawn_maul.glb'))
    weapon = next(o for o in bpy.context.scene.objects if 'head_center_local' in o)
    shaft_local = Vector(weapon['head_center_local']).normalized()
    secondary_local = Vector(weapon['secondary_grip_local'])
    weapon_constraint = weapon.constraints.new('COPY_TRANSFORMS')
    weapon_constraint.target = bpy.data.objects['socket_hand_R']
    ctl = controls(rig)
    scene = bpy.context.scene
    scene.render.fps = FPS
    baked = {}
    audits = []
    motion_list = CONTRACT['motions'] + [dict(clip='combat_idle',durationSec=2.4,contact=.9,style='guard'), dict(clip='prelate_land',durationSec=.25,contact=.08,style='land')]
    for motion in motion_list:
        name, duration, style = motion['clip'], motion['durationSec'], motion['style']
        frames = round(duration*FPS)
        rig.animation_data_create()
        action = bpy.data.actions.new('AUTHOR_'+name)
        rig.animation_data.action = action
        for obj in ctl.values():
            obj.animation_data_clear()
        samples = []
        foot_error = 0
        hand_error = 0
        for frame in range(frames+1):
            scene.frame_set(frame)
            t = frame/FPS
            p = t/duration
            for bone in rig.pose.bones:
                bone.matrix_basis = neutral[bone.name]
            rest_position = Vector((-.13,-.38,1.25))
            rest_axis = Vector((-.75,0,.66)).normalized()
            if style in ['guard','land']:
                breath = math.sin(2*math.pi*p)*.006 if style=='guard' else -math.sin(math.pi*p)*.045
                pos = rest_position + Vector((0,0,breath))
                axis = rest_axis
                yaw = -.035 + math.sin(2*math.pi*p)*.012
                drive = math.sin(math.pi*p)*.25 if style=='land' else 0
                release = 0
            else:
                wind, waxis, hit, haxis, follow, faxis, wyaw, hyaw = GESTURES[style]
                c = motion['contact']
                # Establish the load early, hold briefly, then accelerate into contact.
                anticipation = c*.54
                loaded = c*.73
                after = min(duration*.78,c+.13)
                pos = interpolate([(0,rest_position),(anticipation,wind),(loaded,wind),(c,hit),(after,follow),(duration,rest_position)],t,style not in FREE_HAND)
                axis = interpolate([(0,rest_axis),(anticipation,waxis),(loaded,waxis),(c,haxis),(after,faxis),(duration,rest_axis)],t,style not in FREE_HAND).normalized()
                # Pelvis leads the chest and hammer by a small, visible interval.
                yaw = interpolate([(0,(0,0,0)),(anticipation*.82,(wyaw,0,0)),(max(anticipation,c-.045),(hyaw,0,0)),(after,(hyaw*.7,0,0)),(duration,(0,0,0))],t).x
                drive = interpolate([(0,(0,0,0)),(anticipation,(.18,0,0)),(c,(1,0,0)),(after,(.65,0,0)),(duration,(0,0,0))],t).x
                release = smooth(t/max(.01,c*.8))*(1-smooth((t-duration*.72)/(duration*.28))) if style in FREE_HAND else 0
            strike = style in GESTURES and style not in FREE_HAND
            if style == 'diagonal':
                sample = min(119, int(p*120))
                fraction = min(1, p*120-sample)
                source = opening_samples[sample].lerp(opening_samples[sample+1], fraction)
                origin = opening_samples[0]
                pos = origin.translation+(source.translation-origin.translation)*1.35
                source_rotation = opening_rotations[sample].slerp(opening_rotations[sample+1], fraction)
                delta = opening_rotations[0].rotation_difference(source_rotation)
                axis_angle, angle = delta.to_axis_angle()
                opening_rotation = opening_rotations[0] @ Quaternion(axis_angle, angle*1.22)
                axis = opening_rotation @ shaft_local
            yaw *= 1.65 if strike else 1.25
            pitch = drive*(.30 if style in ['overhead','descending'] else .16 if strike else .20 if style=='place' else .09)
            hips = rig.pose.bones['hips']
            hips.matrix = Matrix.Translation(Vector((yaw*.14,0,.975-drive*(.10 if style in ['overhead','place','land'] else .04)))) @ Euler((pitch,0,yaw*.6)).to_matrix().to_4x4() @ hips.bone.matrix_local.to_quaternion().to_matrix().to_4x4()
            torso = 1.5 if strike else 1
            for bname, angles in [('spine',(pitch*.4,0,yaw*.22*torso)),('chest',(pitch*.35,0,yaw*.18*torso)),('upper_chest',(pitch*.2,0,yaw*.12*torso)),('head',(-pitch*.6,0,-yaw*.48))]:
                bone = rig.pose.bones[bname]
                rest = bone.bone.matrix_local.to_quaternion()
                bone.rotation_mode = 'QUATERNION'
                bone.rotation_quaternion = neutral[bname].to_quaternion() @ rest.inverted() @ Euler(angles).to_quaternion() @ rest
            socket_q = opening_rotation if style == 'diagonal' else shaft_local.rotation_difference(axis)
            socket_matrix = Matrix.Translation(pos) @ socket_q.to_matrix().to_4x4()
            bpy.context.view_layer.update()
            # Solve a common weapon translation inside both arm reach spheres.
            # This preserves the shaft/grip relationship instead of stretching arms.
            for _ in range(24):
                for side in ['R','L']:
                    if side=='L' and release>.01: continue
                    candidate=socket_matrix.copy()
                    if side=='L': candidate.translation=socket_matrix @ secondary_local
                    wrist=(candidate @ hand_socket[side].inverted()).translation
                    shoulder=rig.pose.bones['upper_arm_'+side].matrix.translation
                    reach=(rig.data.bones['upper_arm_'+side].length+rig.data.bones['forearm_'+side].length)*.92
                    delta=wrist-shoulder
                    if delta.length>reach:
                        socket_matrix.translation-=delta.normalized()*(delta.length-reach)
            ctl['hand_R'].matrix_world = socket_matrix @ hand_socket['R'].inverted()
            left_socket = socket_matrix.copy()
            left_socket.translation = socket_matrix @ secondary_local
            if release:
                left_socket.translation = left_socket.translation.lerp(Vector(FREE_HAND[style]),release)
            ctl['hand_L'].matrix_world = left_socket @ hand_socket['L'].inverted()
            if release:
                shoulder=rig.pose.bones['upper_arm_L'].matrix.translation
                delta=ctl['hand_L'].matrix_world.translation-shoulder
                reach=(rig.data.bones['upper_arm_L'].length+rig.data.bones['forearm_L'].length)*.92
                if delta.length>reach: ctl['hand_L'].matrix_world.translation=shoulder+delta.normalized()*reach
            for side, x, y in [('L',.19,-.08),('R',-.19,.07)]:
                foot = rig.pose.bones['foot_'+side]
                ctl['foot_'+side].matrix_world = foot.bone.matrix_local.copy()
                ctl['foot_'+side].matrix_world.translation = Vector((x,y,.077))
            for obj in ctl.values():
                obj.keyframe_insert('location',frame=frame)
                obj.keyframe_insert('rotation_quaternion',frame=frame)
            for bone in rig.pose.bones:
                bone.rotation_mode = 'QUATERNION'
                bone.keyframe_insert('location',frame=frame)
                bone.keyframe_insert('rotation_quaternion',frame=frame)
            bpy.context.view_layer.update()
            evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
            samples.append({b.name:b.matrix.copy() for b in evaluated.pose.bones})
            for side in ['L','R']:
                foot_error=max(foot_error,(evaluated.pose.bones['foot_'+side].matrix.translation-ctl['foot_'+side].matrix_world.translation).length)
                hand_error=max(hand_error,(evaluated.pose.bones['hand_'+side].matrix.translation-ctl['hand_'+side].matrix_world.translation).length)
        baked[name] = samples
        action.use_fake_user = True
        for obj in ctl.values():
            if obj.animation_data and obj.animation_data.action:
                obj.animation_data.action.name=f'{name}_{obj.name}'
                obj.animation_data.action.use_fake_user=True
        audits.append(dict(clip=name,frames=frames+1,maxFootTargetErrorM=foot_error,maxWristTargetErrorM=hand_error))
    scene.frame_set(0)
    scene.frame_end=round(CONTRACT['motions'][-1]['durationSec']*FPS)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'battle_prelate_combat_master.blend'))
    # Export from the same rest skeleton after baking the evaluated constraint result.
    rig.animation_data_clear()
    for bone in rig.pose.bones:
        for constraint in list(bone.constraints): bone.constraints.remove(constraint)
    for obj in ctl.values(): bpy.data.objects.remove(obj,do_unlink=True)
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    rig.animation_data_create()
    for name,samples in baked.items():
        action=bpy.data.actions.new(name)
        rig.animation_data.action=action
        previous={}
        for frame,poses in enumerate(samples):
            scene.frame_set(frame)
            for bone in rig.pose.bones:
                kwargs = dict(parent_matrix=poses[bone.parent.name], parent_matrix_local=bone.parent.bone.matrix_local) if bone.parent else {}
                bone.matrix_basis=bone.bone.convert_local_to_pose(poses[bone.name], bone.bone.matrix_local, invert=True, **kwargs)
                bone.rotation_mode='QUATERNION'
                q=bone.rotation_quaternion.copy()
                if bone.name in previous and q.dot(previous[bone.name])<0: q.negate()
                bone.rotation_quaternion=q
                previous[bone.name]=q
                bone.keyframe_insert('location',frame=frame)
                bone.keyframe_insert('rotation_quaternion',frame=frame)
            bpy.context.view_layer.update()
        action.use_fake_user=True
    rig.animation_data.action=None
    for bone in rig.pose.bones: bone.matrix_basis=Matrix.Identity(4)
    for obj in bpy.context.scene.objects: obj.select_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    output=MODEL/'anim_battle_prelate_combat.glb'
    bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_skins=True,export_def_bones=False,export_yup=True,export_extras=True)
    report=dict(skeletonId=CONTRACT['skeletonId'],bindPoseId=CONTRACT['bindPoseId'],fps=FPS,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),clips=audits)
    (ROOT/'review/bake_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('COMBAT_PACK',json.dumps(report))


if __name__=='__main__': build()
