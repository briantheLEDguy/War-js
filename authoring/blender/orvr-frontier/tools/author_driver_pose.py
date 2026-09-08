"""Fit a seated teamster pose to the existing canonical, equipped humanoid.

No character geometry or rest skeleton is replaced. The exported pack contains
only in-place animation; the wagon adapter owns the documented world offset.
"""
import json
import importlib.util
import math
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_collection as build
import quadruped_rig as animation

ROOT = build.ROOT
ASSET = 'frontier_teamster_animations'
SOURCE = ROOT.parent / 'battle-prelate-novitiate-set/battle_prelate_novitiate_game_master.blend'
HIP_HEIGHT = 1.65
HAND_HEIGHT = 1.93


def two_link(start, target, first_length, second_length, pole):
    delta = target - start
    distance = delta.length
    if not abs(first_length-second_length) + 1e-5 < distance < first_length+second_length-1e-5:
        raise ValueError('Seated target is outside the unchanged limb reach')
    axis = delta.normalized()
    bend = pole-start-axis*(pole-start).dot(axis)
    bend.normalize()
    along = (first_length**2-second_length**2+distance**2)/(2*distance)
    return start+axis*along+bend*math.sqrt(max(0, first_length**2-along**2))


def aimed_matrix(bone, head, tail):
    turn = (bone.tail_local-bone.head_local).rotation_difference(tail-head)
    return Matrix.Translation(head) @ turn.to_matrix().to_4x4() @ bone.matrix_local.to_quaternion().to_matrix().to_4x4()


def seated_pose(rig):
    root_height = HIP_HEIGHT-rig.data.bones['hips'].head_local.z
    desired = {}
    for sign, side in [(1, 'L'), (-1, 'R')]:
        thigh, shin, foot = (rig.data.bones[f'{name}_{side}'] for name in ['thigh', 'shin', 'foot'])
        hip = thigh.head_local.copy()
        ankle = Vector((sign*.20, -.395, 1.228-root_height))
        knee = two_link(hip, ankle, thigh.length, shin.length, Vector((sign*.22, -1, 1.04)))
        desired[thigh.name] = aimed_matrix(thigh, hip, knee)
        desired[shin.name] = aimed_matrix(shin, knee, ankle)
        desired[foot.name] = Matrix.Translation(ankle) @ foot.matrix_local.to_quaternion().to_matrix().to_4x4()
        upper, lower, hand = (rig.data.bones[f'{name}_{side}'] for name in ['upper_arm', 'forearm', 'hand'])
        shoulder = upper.head_local.copy()
        wrist = Vector((sign*.20, -.17, HAND_HEIGHT-root_height))
        elbow = two_link(shoulder, wrist, upper.length, lower.length, Vector((sign*.66, .05, 1.27)))
        desired[upper.name] = aimed_matrix(upper, shoulder, elbow)
        desired[lower.name] = aimed_matrix(lower, elbow, wrist)
        direction = Vector((-sign*.006, -.042, -.018)).normalized()*hand.length
        desired[hand.name] = aimed_matrix(hand, wrist, wrist+direction)
    # Use desired parent matrices explicitly: sequential pose writes otherwise
    # observe stale parent evaluation and compound child rotations.
    for bone in rig.data.bones:
        if bone.name not in desired:
            desired[bone.name] = (desired[bone.parent.name] @ bone.parent.matrix_local.inverted() @ bone.matrix_local
                                  if bone.parent else bone.matrix_local.copy())
    pose = {}
    for bone in rig.data.bones:
        args = dict(parent_matrix=desired[bone.parent.name], parent_matrix_local=bone.parent.matrix_local) if bone.parent else {}
        basis = bone.convert_local_to_pose(desired[bone.name], bone.matrix_local, invert=True, **args)
        pose[bone.name] = {'location': list(basis.to_translation()), 'rotation_euler': list(basis.to_euler()), 'scale': list(basis.to_scale())}
    return pose, root_height


def main():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    rig.animation_data_clear()
    rig.location = (0, 0, 0)
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
        for constraint in list(bone.constraints): bone.constraints.remove(constraint)
    modules = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and obj.parent == rig and obj.name.endswith('_lod0')]
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.hide_render = obj not in modules
            obj.hide_set(obj not in modules)
    pose, root_height = seated_pose(rig)
    for name, values in pose.items():
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'XYZ'
        bone.location = values['location']
        bone.rotation_euler = values['rotation_euler']
        bone.scale = values['scale']
    bpy.context.view_layer.update()
    grip_source = ROOT.parent/'battle-prelate-reference-rebuild/tools/correct_animation.py'
    spec = importlib.util.spec_from_file_location('canonical_hand_fit', grip_source)
    grip = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grip)
    finger_fit = {}
    for sign, side in [(1, 'L'), (-1, 'R')]:
        primary = Vector((sign*.20, -.23, 1.895-root_height))
        axis = Vector((sign*.12, -.59, -.085)).normalized()
        finger_fit[side] = grip._close_hand(rig, side, primary, axis, .008)
    for bone in rig.pose.bones:
        basis = bone.matrix_basis
        pose[bone.name] = {'location':list(basis.to_translation()), 'rotation_euler':list(basis.to_euler()), 'scale':list(basis.to_scale())}
    frames = [(frame, pose) for frame in range(0, 121, 5)]
    action = animation.key_pose_clip(rig, 'driver_seated', frames)
    track = rig.animation_data.nla_tracks.new()
    track.name = 'driver_seated'
    strip = track.strips.new('driver_seated', 140, action)
    strip.extrapolation = 'NOTHING'
    if action.slots: strip.action_slot = action.slots[0]
    bpy.context.scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    destination = ROOT / 'runtime' / f'{ASSET}.glb'
    bpy.ops.export_scene.gltf(filepath=str(destination), export_format='GLB', use_selection=True,
        export_animations=True, export_animation_mode='NLA_TRACKS', export_anim_slide_to_zero=True,
        export_frame_range=False, export_skins=True, export_def_bones=True)
    master = ROOT / 'masters' / f'{ASSET}.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(master))
    track.mute = True
    animation.pin_action(rig, action, 0)
    fitted = {name: list(rig.pose.bones[name].head) for name in ['hips','hand_L','hand_R','foot_L','foot_R']}
    rig.location = (0, -1.38, root_height)
    bpy.context.view_layer.update()
    prior = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'runtime/frontier_supply_wagon_lod0.glb'))
    wagon = [obj for obj in bpy.context.scene.objects if obj not in prior and obj.type == 'MESH' and not obj.hide_render]
    build.set_view(modules + wagon, ROOT / 'review/frontier_seated_driver_fit.png')
    report = {'asset_id': ASSET, 'status': 'pending_actual_equipped_visual_review',
        'source_master': str(SOURCE), 'source_master_sha256': build.sha(SOURCE),
        'author_source_sha256': build.sha(Path(__file__)), 'master': str(master.relative_to(ROOT)), 'master_sha256': build.sha(master),
        'path': str(destination.relative_to(ROOT)), 'sha256': build.sha(destination),
        'rig_profile': 'humanoid_game_v2', 'clips': [{'name':'driver_seated', 'seconds':4, 'root_motion':False}],
        'avatar_origin_wagon_local_gltf':[0,root_height,1.38],
        'bench_contact_wagon_local_gltf':[0,1.54,1.38],
        'fitted_bone_heads_avatar_local_blender':fitted,
        'finger_fit':finger_fit, 'grip_helper_sha256':build.sha(grip_source),
        'rein_grip_wagon_local_gltf':[[.20,1.895,1.61],[-.20,1.895,1.61]],
        'notes':['Pose retains every canonical rest-bone matrix.', 'The pack fits only humanoid_game_v2 actors at scale 1.',
                 'This first proof uses existing equipped source modules. Literal published GLB equipment must still be checked.']}
    (ROOT / 'review' / f'{ASSET}_build.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__': main()
