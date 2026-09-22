"""Bake original contact-driven gestures on the actual Prelate/Arcanist rigs.

Blender --background --factory-startup --python-exit-code 1 --python this_file.
Creates isolated review assets; never promotes a model or replaces a live binding.
"""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Euler

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/unreal/combat-animation'
CONTRACT = json.loads((Path(__file__).with_name('combat-motions.json')).read_text())
FPS = CONTRACT['fps']


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


choreo = module('contact_choreography', ROOT / 'authoring/blender/battle-prelate-combat/tools/build_animation_pack.py')
conversion = module('combat_conversion', Path(__file__).with_name('convert-model.py'))
grips = module('authored_grip_solver', ROOT/'authoring/blender/battle-prelate-reference-rebuild/tools/correct_animation.py')
heavy = module('two_handed_motion', Path(__file__).with_name('two_handed_motion.py'))


def import_glb(path):
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    added=set(bpy.context.scene.objects)-before
    # Blender 5 creates bone-display icospheres absent from the GLB. They are
    # editor UI, not source meshes, and must never reach the export or review.
    displays={bone.custom_shape for obj in added if obj.type=='ARMATURE'
              for bone in obj.pose.bones if bone.custom_shape}
    for obj in added:
        if obj.type=='ARMATURE':
            for bone in obj.pose.bones: bone.custom_shape=None
    for obj in displays & added: bpy.data.objects.remove(obj,do_unlink=True)


def bend(a, b, c):
    return 180 - math.degrees((a-b).angle(c-b))


def build(character):
    folder=OUT/character
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'build.json').unlink(missing_ok=True)
    (OUT/'native-import.json').unlink(missing_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    model = ('chr_civic_battle_prelate_t1_m.glb' if character == 'prelate'
             else 'chr_civic_ember_arcanist_t1_m.glb')
    source = ROOT / 'public/assets/models' / model
    import_glb(source)
    rig = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
    rig.animation_data.action = next(a for a in bpy.data.actions if a.name == 'idle')
    rig.animation_data.use_nla = False
    scene.frame_set(0)
    bpy.context.view_layer.update()
    neutral = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
    foot_targets = {side: rig.pose.bones['foot_'+side].matrix.copy() for side in ('L','R')}
    sockets = {side: rig.pose.bones['hand_'+side].matrix.inverted() @ bpy.data.objects['socket_hand_'+side].matrix_world for side in ('L','R')}
    rig.animation_data_clear()
    for obj in scene.objects:
        if obj.type=='MESH': obj['combat_slot']='body'
    dependencies=[source]
    # Class bodies intentionally omit surfaces covered by modular clothing.
    # Review the complete outfit, with each module bound to this exact rig.
    class_name='battle_prelate' if character=='prelate' else 'ember_arcanist'
    for slot in ('head','shoulders','chest','hands','waist','legs','feet','back','tabard'):
        path=ROOT/'public/assets/models'/f'arm_civic_{class_name}_{slot}_t1_m.glb'
        before=set(scene.objects)
        import_glb(path)
        added=set(scene.objects)-before
        duplicate=next(obj for obj in added if obj.type=='ARMATURE')
        for bone in duplicate.data.bones:
            if bone.name not in rig.data.bones or max(abs(bone.matrix_local[r][c]-rig.data.bones[bone.name].matrix_local[r][c]) for r in range(4) for c in range(4)) > 1e-5:
                raise ValueError('Outfit bind pose differs: '+str(path))
        for obj in added:
            if obj.type!='MESH': continue
            obj['combat_slot']=slot
            world_matrix=obj.matrix_world.copy()
            for modifier in obj.modifiers:
                if modifier.type=='ARMATURE': modifier.object=rig
            obj.parent=rig
            obj.matrix_parent_inverse=rig.matrix_world.inverted()
            obj.matrix_world=world_matrix
        for obj in added:
            if obj.type!='MESH': bpy.data.objects.remove(obj,do_unlink=True)
        dependencies.append(path)
    # The hammer is rigidly skinned to the hand, using the authored grip offset.
    # Its second grip is solved by IK; neither arm may stretch to satisfy it.
    weapon = None
    grip_offset = Vector((0,0,0))
    if character == 'prelate':
        before = set(scene.objects)
        import_glb(ROOT / 'public/assets/models/wep_civic_battle_prelate_dawn_maul.glb')
        weapon = next(obj for obj in scene.objects if obj not in before and obj.type == 'MESH' and 'secondary_grip_local' in obj)
        dependencies.append(ROOT/'public/assets/models/wep_civic_battle_prelate_dawn_maul.glb')
        secondary = Vector(weapon['secondary_grip_local'])
        shaft = Vector(weapon['head_center_local']).normalized()
        # Move the paired grips toward the pommel: the head needs a useful lever
        # arm, and the unused haft must not spear backward through the torso.
        grip_offset = -shaft*.72
        secondary = -shaft*.28
        weapon['combat_primary_grip_local']=list(grip_offset)
        weapon['combat_secondary_grip_local']=list(grip_offset+secondary)
        # Calibrate the grip at the palm itself. The inherited generic socket
        # offset can put the wrist behind the handle and force hyperextension.
        # A hammer shaft crosses the palm perpendicular to the metacarpals.
        for side in ('L','R'):
            # The shaft rests against the palm surface, not through its bone
            # centre. The signed palmar offset also clears the armored cuff.
            palm=Vector((.025 if side=='R' else -.025,rig.data.bones['hand_'+side].length*1.15,0))
            sockets[side]=Matrix.Translation(palm) @ shaft.rotation_difference(Vector((0,0,1 if side=='R' else -1))).to_matrix().to_4x4()
    controls = choreo.controls(rig)
    for side in ('L','R'):
        for name in ('forearm_','hand_'):
            for constraint in list(rig.pose.bones[name+side].constraints):
                rig.pose.bones[name+side].constraints.remove(constraint)
    # Keep a modest natural bend when IK approaches full extension.
    for side in ('L','R'):
        for name in ('forearm_', 'shin_'):
            rig.pose.bones[name+side].ik_stretch = 0
    baked, audits = {}, []
    mesh_visibility={obj:obj.hide_viewport for obj in scene.objects if obj.type=='MESH'}
    # The solve depends only on bones. Defer expensive clothing skin evaluation
    # to the subsequent clearance audit instead of repeating it per IK iteration.
    for obj in mesh_visibility: obj.hide_viewport=True
    motions = [m for m in CONTRACT['motions'] if m['character'] == character]
    for motion in motions:
        duration, contact = motion['duration'], motion['release']
        samples, errors = [], {'foot': 0., 'wrist': 0., 'grip': 0.}
        bends = {'elbow': [180., 0.], 'knee': [180., 0.], 'wrist':[180.,0.]}
        previous_roll={'L':None,'R':None}
        worst_wrist={}
        hammer = motion['gesture']=='hammer'
        stance = {side:target.copy() for side,target in foot_targets.items()}
        if hammer:
            stance['L'].translation += Vector((.09,-.18,0))
            stance['R'].translation += Vector((-.09,.12,0))
        rest_pos, rest_axis = Vector((-.13,-.56,1.30)), Vector((-.48,0,.88)).normalized()
        for frame in range(round(duration*FPS)+1):
            scene.frame_set(frame)
            time = frame/FPS
            for bone in rig.pose.bones:
                bone.matrix_basis = neutral[bone.name]
            envelope = choreo.interpolate([(0,(0,0,0)),(contact*.55,(.35,0,0)),(contact,(1,0,0)),(contact+.16,(.8,0,0)),(duration,(0,0,0))],time).x
            # Rear-leg load precedes the shoulder turn; the pelvis drives forward
            # before release, and the legs absorb the follow-through.
            drive = choreo.interpolate([(0,(0,0,0)),(contact*.46,(-1,0,0)),
                (contact-.065,(1,0,0)),(contact+.16,(.65,0,0)),
                (duration,(0,0,0))],time).x
            pelvis_yaw = (.17 if hammer else .065)*drive
            chest_drive = choreo.interpolate([(0,(0,0,0)),(contact*.60,(-1,0,0)),
                (contact,(1,0,0)),(contact+.16,(.7,0,0)),(duration,(0,0,0))],time).x
            yaw = (.24 if hammer else .09)*chest_drive
            pitch = (.10 if hammer else .045)*envelope
            if hammer:
                drive = choreo.interpolate([(0,(0,0,0)),(.58,(-1,0,0)),(.77,(-.85,0,0)),
                    (.98,(1,0,0)),(1.26,(.85,0,0)),(1.55,(.65,0,0)),(duration,(0,0,0))],time).x
                chest_drive = choreo.interpolate([(0,(0,0,0)),(.67,(-1,0,0)),(.84,(-.85,0,0)),
                    (1.12,(1,0,0)),(1.38,(.8,0,0)),(duration,(0,0,0))],time).x
                pelvis_yaw = .19*drive
                yaw = .32*chest_drive
                pitch = choreo.interpolate([(0,(.08,0,0)),(.70,(-.12,0,0)),(1.01,(-.03,0,0)),
                    (1.22,(.32,0,0)),(1.45,(.30,0,0)),(1.80,(.05,0,0)),(duration,(.08,0,0))],time).x
                envelope = choreo.interpolate([(0,(.3,0,0)),(.64,(.65,0,0)),(.90,(.35,0,0)),
                    (1.20,(1,0,0)),(1.45,(.95,0,0)),(duration,(.3,0,0))],time).x
            # Small distributed torso rotations; hips stay inside the support polygon.
            for name, amount in [('hips',.35),('spine',.30),('chest',.25),('upper_chest',.10),('head',-.4)]:
                bone = rig.pose.bones[name]
                rest = bone.bone.matrix_local.to_quaternion()
                bone.rotation_mode = 'QUATERNION'
                bone.rotation_quaternion = neutral[name].to_quaternion() @ rest.inverted() @ Euler((pitch*amount,0,pelvis_yaw if name=='hips' else yaw*amount)).to_quaternion() @ rest
            bpy.context.view_layer.update()
            hips = rig.pose.bones['hips']
            matrix = hips.matrix.copy()
            matrix.translation += Vector(((.045 if hammer else .015)*drive,
                -(.10 if hammer else .022)*drive,-(.13 if hammer else .018)*envelope))
            hips.matrix = matrix
            bpy.context.view_layer.update()
            end = min(duration-.20,contact+.16)
            elbow_hints={side:Vector(((.52 if hammer else .42)*(1 if side=='L' else -1),
                                     -.12 if hammer else -.08,1.15 if hammer else .90)) for side in ('L','R')}
            if motion['gesture']=='hammer':
                pos = Vector(heavy.curve([(0,rest_pos),(.60,motion['wind']),(.80,motion['wind']),
                    (.94,(-.24,-.48,1.82)),(1.005,(-.15,-.75,1.54)),(contact,motion['hit']),(1.27,motion['follow']),
                    (1.48,motion['follow']),(1.73,(-.13,-.75,1.48)),(1.90,(-.13,-.59,1.45)),(duration,rest_pos)],time))
                # The head loads behind the right shoulder, clears above it,
                # then descends in the forward plane. Recovery lifts the weight.
                pitch_angle,lateral=heavy.curve([(0,(0,-.48)),(.60,(1.17,-.30)),(.80,(1.17,-.30)),
                    (.94,(.23,-.25)),(contact,(-2.72,-.15)),(1.27,(-2.70,-.10)),
                    (1.48,(-2.70,-.10)),(1.90,(-.4,-.48)),(duration,(0,-.48))],time)
                axis = Vector(heavy.shaft_axis(pitch_angle,lateral))
            else:
                pos, axis = rest_pos.copy(), rest_axis.copy()
            socket = Matrix.Translation(pos) @ (shaft.rotation_difference(axis).to_matrix().to_4x4() if weapon else Matrix.Identity(4))
            free_side = 'L' if weapon else 'R'
            # Project the held weapon as one rigid body into both reachable arm spheres.
            for _ in range(32):
                for side in ('R','L'):
                    if side == free_side and motion['gesture'] != 'hammer':
                        continue
                    target = socket.copy()
                    if side=='L' and weapon: target.translation = socket @ secondary
                    wrist = (target @ sockets[side].inverted()).translation
                    shoulder = rig.pose.bones['upper_arm_'+side].matrix.translation
                    reach = (rig.data.bones['upper_arm_'+side].length+rig.data.bones['forearm_'+side].length)*.96
                    delta = wrist-shoulder
                    if delta.length > reach: socket.translation -= delta.normalized()*(delta.length-reach)
            if weapon:
                socket,_,previous_roll['R']=grips._comfortable_socket(rig,'R',socket.translation,axis,
                    socket.to_quaternion(),sockets['R'],elbow_hints['R'],previous_roll['R'])
            for side in ('L','R'):
                target = socket.copy()
                if side=='L' and weapon: target.translation = socket @ secondary
                if side=='L' and weapon:
                    target,_,previous_roll['L']=grips._comfortable_socket(rig,'L',target.translation,axis,
                        socket.to_quaternion(),sockets['L'],elbow_hints['L'],previous_roll['L'])
                target = target @ sockets[side].inverted()
                if not weapon:
                    target = rig.pose.bones['hand_'+side].matrix.copy()
                if side == free_side and motion['gesture'] != 'hammer':
                    initial = Vector((.30,-.30,1.15)) if weapon else target.translation.copy()
                    target.translation = choreo.interpolate([(0,initial),(contact*.58,motion['wind']),(contact*.76,motion['wind']),(contact,motion['hit']),(end,motion['follow']),(duration,initial)],time)
                    shoulder = rig.pose.bones['upper_arm_'+side].matrix.translation
                    reach = (rig.data.bones['upper_arm_'+side].length+rig.data.bones['forearm_'+side].length)*.90
                    delta = target.translation-shoulder
                    if delta.length > reach: target.translation = shoulder+delta.normalized()*reach
                controls['hand_'+side].matrix_world = target
                controls['foot_'+side].matrix_world = stance[side]
                # Preserve the chosen palm/weapon roll while routing the guiding
                # elbow outward. Re-optimizing that roll for the outward pole
                # rolls the haft back into the steel forearm cuff.
                pole=Vector((-.75,0,1.05)) if hammer and side=='R' else elbow_hints[side]
                grips._solve_arm(rig,side,target,pole)
                if not weapon or (side==free_side and motion['gesture']!='hammer'):
                    hand=rig.pose.bones['hand_'+side]
                    fore=rig.pose.bones['forearm_'+side]
                    current=hand.matrix.copy()
                    rotation=(hand.tail-hand.head).rotation_difference(fore.tail-fore.head) @ current.to_quaternion()
                    hand.matrix=Matrix.Translation(current.translation) @ rotation.to_matrix().to_4x4()
                elif weapon:
                    grips._close_hand(rig,side,socket.translation,axis,.025)
            bpy.context.view_layer.update()
            evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
            poses = {b.name:b.matrix.copy() for b in evaluated.pose.bones}
            samples.append(poses)
            for side in ('L','R'):
                fore=evaluated.pose.bones['forearm_'+side]
                hand=evaluated.pose.bones['hand_'+side]
                wrist=math.degrees((fore.tail-fore.head).angle(hand.tail-hand.head))
                if wrist>bends['wrist'][1]: worst_wrist={'side':side,'frame':frame,'degrees':wrist}
                bends['wrist']=[min(bends['wrist'][0],wrist),max(bends['wrist'][1],wrist)]
                errors['foot'] = max(errors['foot'],(poses['foot_'+side].translation-stance[side].translation).length)
                errors['wrist'] = max(errors['wrist'],(poses['hand_'+side].translation-controls['hand_'+side].matrix_world.translation).length)
                for kind, names in [('elbow',('upper_arm_','forearm_','hand_')),('knee',('thigh_','shin_','foot_'))]:
                    angle = bend(*(poses[name+side].translation for name in names))
                    bends[kind] = [min(bends[kind][0],angle),max(bends[kind][1],angle)]
            if weapon and motion['gesture']=='hammer':
                right = poses['hand_R'] @ sockets['R']
                left = poses['hand_L'] @ sockets['L']
                errors['grip'] = max(errors['grip'],(left.translation-right @ secondary).length)
        if errors['foot'] > .008 or errors['wrist'] > .012 or errors['grip'] > .015:
            raise ValueError(f"Unreachable contact in {motion['id']}: {errors}")
        if bends['elbow'][1] > 150 or bends['knee'][1] > 125 or bends['wrist'][1] > 75:
            raise ValueError(f"Excessive joint flexion in {motion['id']}: {bends}; worst wrist={worst_wrist}")
        baked[motion['id']] = samples
        audits.append({'id':motion['id'],'samples':len(samples),'maxErrorMeters':errors,'bendDegrees':bends})
        print('SOLVED',motion['id'],bends,flush=True)
    for obj,hidden in mesh_visibility.items(): obj.hide_viewport=hidden
    for bone in rig.pose.bones:
        for constraint in list(bone.constraints): bone.constraints.remove(constraint)
    for obj in controls.values(): bpy.data.objects.remove(obj,do_unlink=True)
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    rig.animation_data_create()
    for name, samples in baked.items():
        action = bpy.data.actions.new(name)
        rig.animation_data.action = action
        previous = {}
        for frame, poses in enumerate(samples):
            scene.frame_set(frame)
            for bone in rig.pose.bones:
                kwargs = dict(parent_matrix=poses[bone.parent.name],parent_matrix_local=bone.parent.bone.matrix_local) if bone.parent else {}
                bone.matrix_basis = bone.bone.convert_local_to_pose(poses[bone.name],bone.bone.matrix_local,invert=True,**kwargs)
                bone.rotation_mode='QUATERNION'
                q=bone.rotation_quaternion.copy()
                if bone.name in previous and q.dot(previous[bone.name]) < 0: q.negate()
                bone.rotation_quaternion=q
                previous[bone.name]=q
                bone.keyframe_insert('location',frame=frame)
                bone.keyframe_insert('rotation_quaternion',frame=frame)
            bpy.context.view_layer.update()
        action.use_fake_user=True
        track = rig.animation_data.nla_tracks.new()
        track.name=name
        track.strips.new(name,0,action)
        track.mute=True
    rig.animation_data.action=None
    for bone in rig.pose.bones: bone.matrix_basis=Matrix.Identity(4)
    if weapon:
        weapon.matrix_world = rig.data.bones['hand_R'].matrix_local @ sockets['R'] @ Matrix.Translation(-grip_offset)
        group = weapon.vertex_groups.new(name='hand_R')
        group.add(list(range(len(weapon.data.vertices))),1.,'REPLACE')
        modifier = weapon.modifiers.new('Authored rigid hand attachment','ARMATURE')
        modifier.object = rig
        weapon.parent = rig
        # Named emitter bones follow the real hammer head, not an estimated arc.
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for name, point in [('vfx_weapon_tip', Vector(weapon['head_center_local'])),
                            ('vfx_weapon_base', Vector(weapon['head_center_local'])*.72)]:
            bone = rig.data.edit_bones.new(name)
            bone.head = weapon.matrix_world @ point
            bone.tail = bone.head + Vector((0,0,.025))
            bone.parent = rig.data.edit_bones['hand_R']
        bpy.ops.object.mode_set(mode='OBJECT')
    scene.frame_set(0)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'choreography.blend'))
    bpy.ops.export_scene.gltf(filepath=str(folder/'choreography.glb'),export_format='GLB',export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_frame_range=False,export_extras=True)
    # Reimporting the exported source makes the animation-to-FBX path identical to the model pipeline.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.fps=FPS
    import_glb(folder/'choreography.glb')
    names=list(baked)
    transforms=conversion.rest_transforms()
    bindings=conversion.source_clip_bindings(names)
    samples=conversion.sample_clips(bindings,transforms)
    conversion.clear_animation(transforms)
    for obj in scene.objects:
        if obj.animation_data:
            obj.animation_data.use_nla=True
            for track in obj.animation_data.nla_tracks:
                track.mute=False
                for strip in track.strips: strip.mute=False
    bpy.ops.export_scene.fbx(filepath=str(folder/'choreography.fbx'),object_types={'MESH','ARMATURE','EMPTY'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',add_leaf_bones=False,use_armature_deform_only=False,use_triangles=True,bake_anim=True,bake_anim_use_nla_strips=True,bake_anim_use_all_actions=False,bake_anim_simplify_factor=0.,bake_anim_step=1.,path_mode='COPY',embed_textures=True)
    (folder/'samples.json').write_text(json.dumps(samples,allow_nan=False))
    (folder/'build.json').write_text(json.dumps({'source':str(source.relative_to(ROOT)),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'dependencies':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies},'fbxSha256':hashlib.sha256((folder/'choreography.fbx').read_bytes()).hexdigest(),'clips':audits,'visualApproval':False},indent=2)+'\n')
    print('COMBAT_BAKE',character,json.dumps(audits))


if __name__=='__main__':
    for character in (('prelate',) if '--prelate-only' in sys.argv else ('prelate','ember')): build(character)
