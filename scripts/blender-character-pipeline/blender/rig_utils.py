"""
Armature creation and weight-painting utilities for WAR character rigs.

Bone naming convention matches Three.js SkinnedMesh expectations and the
animation keyframe names in anim_library.py.
"""

import bpy
import math


# Bone rest positions relative to character root (y-up, facing +Z).
# Values assume a 1.9-unit tall character; scale proportionally for dwarves etc.
# Each entry: (head_xyz, tail_xyz, parent_name or None, connected)
BONE_DEFS = [
    # name            head                  tail                  parent           connected
    ("root",          (0, 0, 0),            (0, 0.05, 0),         None,            False),
    ("hips",          (0, 0.9, 0),          (0, 1.0,  0),         "root",          False),
    ("spine",         (0, 1.0, 0),          (0, 1.25, 0),         "hips",          True),
    ("chest",         (0, 1.25, 0),         (0, 1.55, 0),         "spine",         True),
    ("neck",          (0, 1.55, 0),         (0, 1.68, 0),         "chest",         True),
    ("head",          (0, 1.68, 0),         (0, 1.90, 0),         "neck",          True),
    # Left arm (character's left = world +X)
    ("shoulder_L",    ( 0.18, 1.52,  0),    ( 0.28, 1.52,  0),    "chest",         False),
    ("upper_arm_L",   ( 0.28, 1.52,  0),    ( 0.52, 1.52,  0),    "shoulder_L",    True),
    ("forearm_L",     ( 0.52, 1.52,  0),    ( 0.76, 1.52,  0),    "upper_arm_L",   True),
    ("hand_L",        ( 0.76, 1.52,  0),    ( 0.88, 1.52,  0),    "forearm_L",     True),
    # Right arm (character's right = world -X)
    ("shoulder_R",    (-0.18, 1.52,  0),    (-0.28, 1.52,  0),    "chest",         False),
    ("upper_arm_R",   (-0.28, 1.52,  0),    (-0.52, 1.52,  0),    "shoulder_R",    True),
    ("forearm_R",     (-0.52, 1.52,  0),    (-0.76, 1.52,  0),    "upper_arm_R",   True),
    ("hand_R",        (-0.76, 1.52,  0),    (-0.88, 1.52,  0),    "forearm_R",     True),
    # Left leg
    ("thigh_L",       ( 0.11, 0.90,  0),    ( 0.11, 0.50,  0),    "hips",          False),
    ("shin_L",        ( 0.11, 0.50,  0),    ( 0.11, 0.14,  0),    "thigh_L",       True),
    ("foot_L",        ( 0.11, 0.14,  0),    ( 0.11, 0.02,  0.1),  "shin_L",        True),
    # Right leg
    ("thigh_R",       (-0.11, 0.90,  0),    (-0.11, 0.50,  0),    "hips",          False),
    ("shin_R",        (-0.11, 0.50,  0),    (-0.11, 0.14,  0),    "thigh_R",       True),
    ("foot_R",        (-0.11, 0.14,  0),    (-0.11, 0.02,  0.1),  "shin_R",        True),
]


def create_humanoid_rig(body_objects: list, body_scale: tuple) -> bpy.types.Object:
    """
    Create a humanoid armature, bind all body_objects to it, and return
    the armature object.

    body_scale: (x, y, z) tuple from character_spec — used to scale bone
    positions proportionally (e.g., 0.82 y for dwarves).
    """
    sx, sy, sz = body_scale

    # Create armature data + object
    arm_data = bpy.data.armatures.new("CharacterArmature")
    arm_obj = bpy.data.objects.new("Armature", arm_data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = arm_data.edit_bones

    bone_map: dict[str, bpy.types.EditBone] = {}

    for name, head, tail, parent_name, connected in BONE_DEFS:
        b = edit_bones.new(name)
        b.head = (head[0] * sx, head[1] * sy, head[2] * sz)
        b.tail = (tail[0] * sx, tail[1] * sy, tail[2] * sz)
        b.use_connect = connected and parent_name is not None
        if parent_name:
            b.parent = bone_map[parent_name]
        bone_map[name] = b

    bpy.ops.object.mode_set(mode='OBJECT')

    # Bind each body mesh to the armature via Armature modifier + auto weights
    for obj in body_objects:
        obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj

    bpy.ops.object.parent_set(type='ARMATURE_AUTO')

    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')

    return arm_obj


def apply_animations(arm_obj: bpy.types.Object, actions: dict) -> None:
    """
    Apply animation clips from anim_library.ACTIONS to the armature.
    Each clip becomes a named Action on the armature's NLA stack.
    """
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj

    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()

    nla = arm_obj.animation_data.nla_tracks

    for action_name, action_def in actions.items():
        action = bpy.data.actions.new(name=action_name)
        action.use_fake_user = True

        for bone_name, keyframe_list in action_def["keyframes"].items():
            pose_bone_path = f'pose.bones["{bone_name}"]'

            for frame, loc, rot in keyframe_list:
                # Location curves
                for i, val in enumerate(loc):
                    fc = action.fcurves.find(f"{pose_bone_path}.location", index=i)
                    if fc is None:
                        fc = action.fcurves.new(f"{pose_bone_path}.location", index=i)
                    kp = fc.keyframe_points.insert(frame, val)
                    kp.interpolation = 'BEZIER'

                # Rotation curves (euler XYZ)
                for i, val in enumerate(rot):
                    fc = action.fcurves.find(f"{pose_bone_path}.rotation_euler", index=i)
                    if fc is None:
                        fc = action.fcurves.new(
                            f"{pose_bone_path}.rotation_euler", index=i
                        )
                    kp = fc.keyframe_points.insert(frame, val)
                    kp.interpolation = 'BEZIER'

        # Mark loop via custom property (Three.js reads GLTF extras)
        action["loop"] = action_def.get("loop", True)

        # Push to NLA so it exports
        track = nla.new()
        track.name = action_name
        strip = track.strips.new(action_name, 1, action)
        strip.action_frame_start = 1
        strip.action_frame_end = action_def["duration_frames"]
        strip.frame_start = 1
        strip.frame_end = action_def["duration_frames"]
