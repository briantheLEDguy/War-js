"""Fit the retained Prelate hammer to each new palm and fixed-length support arm."""
import json
import math
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).parent))
from class_character_native import OUT, read, sha
from animation_replacement import visual_path
from supplied_stow import between, inverse, unit

library = unreal.EditorAssetLibrary
sets = read(OUT / 'retarget.json')['profiles']
records = read(OUT / 'model-sources.json')['profiles']
anchors = read(Path(__file__).parent / 'animation-recipes/corrections/prelate-grip.json')['gripsWorld']
point = lambda name: unreal.Vector(anchors[name][0]*100, -anchors[name][1]*100, anchors[name][2]*100)
primary, head = point('primary_grip_local'), point('head_center_local')
report = dict(profiles={}, retargetSha256=sha(OUT / 'retarget.json'), passed=False)

for profile, record in records.items():
    if record['classId'] != 'battle_prelate': continue
    entry = sets[profile]
    visual = unreal.load_asset(visual_path(profile))
    mesh = unreal.load_asset(entry['mesh'])
    options = unreal.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh, evaluation_type=unreal.AnimDataEvalType.RAW)
    initial = unreal.AnimPoseExtensions.get_anim_pose_at_time(unreal.load_asset(entry['clips']['two.idle']['animation']), 0, options)
    reference = lambda bone: unreal.AnimPoseExtensions.get_ref_bone_pose(initial, bone, unreal.AnimPoseSpaces.WORLD)
    palms = {}
    for side in ('R', 'L'):
        wrist = reference('hand_' + side)
        knuckles = sum((reference(name + '_01_' + side).translation for name in ('index', 'middle', 'ring', 'pinky')), unreal.Vector()) / 4
        palms[side] = wrist.inverse_transform_location(wrist.translation*.45 + knuckles*.55)
    grip = visual.weapon_grip
    grip.translation = palms['R'] - (grip.transform_location(primary)-grip.translation)
    visual.set_editor_property('weapon_grip', grip)
    if not library.save_loaded_asset(visual, False): raise RuntimeError('Could not save own-rig palm fit')
    shaft = unit(grip.transform_location(head)-grip.transform_location(primary))
    description = visual.weapon_mesh.get_static_mesh_description(0)
    vertices = [grip.transform_location(description.get_vertex_position(unreal.VertexID(i)))
                for i in range(description.get_vertex_count())]
    measured = {}
    for key, clip in entry['clips'].items():
        if not key.startswith('two.') or key in ('two.invocation', 'two.death'): continue
        animation = unreal.load_asset(clip['animation'])
        count = round(clip['duration']*30)+1
        tracks = {bone: [] for bone in ('hand_R', 'upper_arm_L', 'forearm_L', 'hand_L')}
        max_error, max_adjustment = 0., 0.
        for frame in range(count):
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(animation, min(frame/30, clip['duration']), options)
            world = lambda name: unreal.AnimPoseExtensions.get_bone_pose(pose, name, unreal.AnimPoseSpaces.WORLD)
            local = lambda name: unreal.AnimPoseExtensions.get_bone_pose(pose, name, unreal.AnimPoseSpaces.LOCAL)
            right, left = world('hand_R'), world('hand_L')
            scale = right.scale3d.x
            right_palm, left_palm = right.transform_location(palms['R']), left.transform_location(palms['L'])
            rotation = between(right.rotation.rotate_vector(shaft), right_palm-left_palm)*right.rotation

            def minimum_height(q):
                vertical = inverse(q).rotate_vector(unreal.Vector(0, 0, 1))
                return right.translation.z + min(v.dot(vertical)*scale for v in vertices)

            if minimum_height(rotation) < 3:
                axis = rotation.rotate_vector(shaft)
                horizontal = unit(unreal.Vector(axis.x, axis.y, 0))
                if horizontal.length() < .5: horizontal = unreal.Vector(0, 1, 0)
                change = between(axis, horizontal)
                def candidate(alpha):
                    q = unreal.Quat(change.x*alpha, change.y*alpha, change.z*alpha, 1-alpha+change.w*alpha)
                    q.normalize()
                    return q*rotation
                if minimum_height(candidate(1)) < 3: raise RuntimeError('No ground-clear own-rig hammer orientation: ' + profile + ': ' + key)
                low, high = 0., 1.
                for _ in range(16):
                    middle = (low+high)/2
                    if minimum_height(candidate(middle)) < 3: low = middle
                    else: high = middle
                rotation = candidate(high)
            right_palm = right.translation + rotation.rotate_vector(palms['R']*scale)
            axis = rotation.rotate_vector(shaft)
            shoulder, elbow = world('upper_arm_L'), world('forearm_L')
            start = shoulder.translation
            a, b = (elbow.translation-start).length(), (left.translation-elbow.translation).length()
            radius = a+b-.1
            spacing = max(8., min(40., (right_palm-left_palm).dot(axis)))
            palm_vector = left.rotation.rotate_vector(palms['L']*left.scale3d.x)
            base = right_palm-palm_vector-start
            axial = base.dot(axis)
            discriminant = radius*radius-(base.dot(base)-axial*axial)
            if discriminant >= 0:
                lower, upper = max(4., axial-math.sqrt(discriminant)), min(60., axial+math.sqrt(discriminant))
                if lower <= upper: spacing = max(lower, min(upper, spacing))
            contact = right_palm-axis*spacing
            left_rotation = left.rotation
            wrist = contact-palm_vector
            for step in range(1, 21):
                if (wrist-start).length() <= radius: break
                direction = palm_vector*(1-step/20) + unit(contact-start)*palm_vector.length()*(step/20)
                left_rotation = between(palm_vector, direction)*left.rotation
                wrist = contact-left_rotation.rotate_vector(palms['L']*left.scale3d.x)
            delta = wrist-start
            distance = max(abs(a-b)+.1, min(radius, delta.length()))
            max_error = max(max_error, abs(distance-delta.length()))
            direction = unit(delta)
            hint = elbow.translation-start
            pole = unit(hint-direction*hint.dot(direction))
            along = (a*a-b*b+distance*distance)/(2*distance)
            joint = start+direction*along+pole*math.sqrt(max(0., a*a-along*along))
            end = start+direction*distance
            upper = between(elbow.translation-start, joint-start)*shoulder.rotation
            lower = between(left.translation-elbow.translation, end-joint)*elbow.rotation
            rotations = dict(hand_R=inverse(world('forearm_R').rotation)*rotation,
                upper_arm_L=inverse(world('shoulder_L').rotation)*upper,
                forearm_L=inverse(upper)*lower, hand_L=inverse(lower)*left_rotation)
            max_adjustment = max(max_adjustment, (end-left.translation).length())
            for bone, q in rotations.items():
                value = local(bone); value.rotation = q; tracks[bone].append(value)
        if max_error > .1: raise RuntimeError('Own-rig support palm exceeds unchanged arm reach: ' + profile + ': ' + key + ': ' + str(max_error))
        data = animation.controller
        data.open_bracket('Own-rig palm and fixed-length hammer fit', False)
        for bone, values in tracks.items():
            if not data.set_bone_track_keys(bone, [v.translation for v in values], [v.rotation for v in values], [v.scale3d for v in values], False):
                raise RuntimeError('Could not write own-rig grip track')
        data.close_bracket(False)
        if not unreal.WarImportLibrary.finalize_animation_sampling(animation): raise RuntimeError('Own-rig grip compression failed')
        if not library.save_loaded_asset(animation, False): raise RuntimeError('Could not save own-rig grip animation')
        measured[key] = dict(maximumSupportReachErrorCm=max_error, maximumSupportAdjustmentCm=max_adjustment)
    report['profiles'][profile] = measured
report['passed'] = len(report['profiles']) == 2
(OUT / 'equipment-fit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
if not report['passed']: raise RuntimeError('Both own Prelate body fits are required')
