"""
Armature creation and weight-painting utilities for manifest character rigs.

Bone naming convention matches Three.js SkinnedMesh expectations and the
animation keyframe names in anim_library.py.
"""

import bpy
import math
from mathutils import Vector


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


RELAXED_HERO_BONE_DEFS = [
    # name            head                  tail                  parent           connected
    ("root",          (0, 0, 0),            (0, 0.05, 0),         None,            False),
    ("hips",          (0, 0.9, 0),          (0, 1.0,  0),         "root",          False),
    ("spine",         (0, 1.0, 0),          (0, 1.25, 0),         "hips",          True),
    ("chest",         (0, 1.25, 0),         (0, 1.55, 0),         "spine",         True),
    ("neck",          (0, 1.55, 0),         (0, 1.68, 0),         "chest",         True),
    ("head",          (0, 1.68, 0),         (0, 1.90, 0),         "neck",          True),
    # Relaxed A-pose arms for hero meshes. The authored mesh, armor, and weapon
    # grip follow these bone centers so idle no longer presents as a T-pose.
    ("shoulder_L",    ( 0.18, 1.50, 0.00),  ( 0.29, 1.420, 0.020), "chest",        False),
    ("upper_arm_L",   ( 0.29, 1.420, 0.020), ( 0.37, 1.200, 0.045), "shoulder_L",   True),
    ("forearm_L",     ( 0.37, 1.200, 0.045), ( 0.44, 0.980, 0.080), "upper_arm_L",  True),
    ("hand_L",        ( 0.44, 0.980, 0.080), ( 0.52, 0.920, 0.100), "forearm_L",    True),
    ("shoulder_R",    (-0.18, 1.50, 0.00),  (-0.29, 1.420, 0.020), "chest",        False),
    ("upper_arm_R",   (-0.29, 1.420, 0.020), (-0.37, 1.200, 0.045), "shoulder_R",   True),
    ("forearm_R",     (-0.37, 1.200, 0.045), (-0.44, 0.980, 0.080), "upper_arm_R",  True),
    ("hand_R",        (-0.44, 0.980, 0.080), (-0.52, 0.920, 0.100), "forearm_R",    True),
    ("thigh_L",       ( 0.11, 0.90, 0),     ( 0.11, 0.50, 0),      "hips",         False),
    ("shin_L",        ( 0.11, 0.50, 0),     ( 0.11, 0.14, 0),      "thigh_L",      True),
    ("foot_L",        ( 0.11, 0.14, 0),     ( 0.11, 0.02, 0.1),    "shin_L",       True),
    ("thigh_R",       (-0.11, 0.90, 0),     (-0.11, 0.50, 0),      "hips",         False),
    ("shin_R",        (-0.11, 0.50, 0),     (-0.11, 0.14, 0),      "thigh_R",      True),
    ("foot_R",        (-0.11, 0.14, 0),     (-0.11, 0.02, 0.1),    "shin_R",       True),
]


BONE_PROFILES = {
    "default": BONE_DEFS,
    "hero_relaxed": RELAXED_HERO_BONE_DEFS,
}


def create_humanoid_rig(body_objects: list, body_scale: tuple, rig_profile: str = "default") -> bpy.types.Object:
    """
    Create a humanoid armature, bind all body_objects to it, and return
    the armature object.

    body_scale: (x, y, z) tuple from the manifest body profile, used to scale bone
    positions proportionally (e.g., 0.82 y for dwarves).
    """
    sx, sy, sz = body_scale
    bone_defs = BONE_PROFILES.get(rig_profile, BONE_DEFS)

    # Create armature data + object
    arm_data = bpy.data.armatures.new("CharacterArmature")
    arm_obj = bpy.data.objects.new("Armature", arm_data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = arm_data.edit_bones

    bone_map: dict[str, bpy.types.EditBone] = {}

    for name, head, tail, parent_name, connected in bone_defs:
        b = edit_bones.new(name)
        b.head = (head[0] * sx, head[1] * sy, head[2] * sz)
        b.tail = (tail[0] * sx, tail[1] * sy, tail[2] * sz)
        b.use_connect = connected and parent_name is not None
        if parent_name:
            b.parent = bone_map[parent_name]
        bone_map[name] = b

    bpy.ops.object.mode_set(mode='OBJECT')

    # Bind each body mesh to the armature via Armature modifier + auto weights
    bpy.ops.object.select_all(action='DESELECT')
    for obj in body_objects:
        obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj

    bpy.ops.object.parent_set(type='ARMATURE_AUTO')

    ensure_fallback_skinning(body_objects, arm_obj, bone_defs, body_scale)

    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')

    return arm_obj


def ensure_fallback_skinning(
    body_objects: list,
    arm_obj: bpy.types.Object,
    bone_defs: list,
    body_scale: tuple,
) -> None:
    """Give deterministic weights to meshes Blender's automatic heat solve missed."""
    weighted = 0
    for obj in body_objects:
        if obj.type != "MESH":
            continue
        if object_has_skin_weights(obj, arm_obj):
            continue
        apply_nearest_bone_weights(obj, arm_obj, bone_defs, body_scale)
        weighted += 1
    if weighted:
        print(f"[asset-pipeline] Applied fallback skin weights to {weighted} mesh objects")


def object_has_skin_weights(obj: bpy.types.Object, arm_obj: bpy.types.Object) -> bool:
    has_armature = any(
        mod.type == "ARMATURE" and getattr(mod, "object", None) == arm_obj
        for mod in obj.modifiers
    )
    if not has_armature:
        return False
    if not obj.vertex_groups:
        return False
    return any(vertex.groups for vertex in obj.data.vertices)


def apply_nearest_bone_weights(
    obj: bpy.types.Object,
    arm_obj: bpy.types.Object,
    bone_defs: list,
    body_scale: tuple,
) -> None:
    obj.vertex_groups.clear()
    groups = {name: obj.vertex_groups.new(name=name) for name, *_rest in bone_defs}
    segments = fallback_bone_segments(bone_defs, body_scale)

    armature_mod = next(
        (
            mod for mod in obj.modifiers
            if mod.type == "ARMATURE" and getattr(mod, "object", None) == arm_obj
        ),
        None,
    )
    if armature_mod is None:
        armature_mod = obj.modifiers.new(name="Armature", type="ARMATURE")
        armature_mod.object = arm_obj

    special_bone = special_attachment_bone(obj.name)
    for vertex in obj.data.vertices:
        point = vertex.co.copy()
        if special_bone:
            groups[special_bone].add([vertex.index], 1.0, "REPLACE")
            continue

        nearest = sorted(
            (
                (distance_to_segment(point, head, tail), name)
                for name, head, tail in segments
            ),
            key=lambda item: item[0],
        )[:3]
        raw = [(name, 1.0 / ((distance + 0.035) ** 2)) for distance, name in nearest]
        total = sum(weight for _name, weight in raw)
        for name, weight in raw:
            groups[name].add([vertex.index], weight / total, "REPLACE")


def fallback_bone_segments(bone_defs: list, body_scale: tuple) -> list[tuple[str, Vector, Vector]]:
    sx, sy, sz = body_scale
    segments = []
    for name, head, tail, _parent_name, _connected in bone_defs:
        if name == "root":
            continue
        segments.append((
            name,
            Vector((head[0] * sx, head[1] * sy, head[2] * sz)),
            Vector((tail[0] * sx, tail[1] * sy, tail[2] * sz)),
        ))
    return segments


def distance_to_segment(point: Vector, start: Vector, end: Vector) -> float:
    axis = end - start
    length_sq = axis.length_squared
    if length_sq <= 0.000001:
        return (point - start).length
    t = max(0.0, min(1.0, (point - start).dot(axis) / length_sq))
    return (point - (start + axis * t)).length


def special_attachment_bone(name: str) -> str | None:
    lower = name.lower()
    if "wep_" in lower or "staff" in lower or "rapier" in lower or "sword" in lower:
        return "hand_R"
    if "pistol" in lower or "shield" in lower:
        return "hand_L"
    if (
        "hat" in lower
        or "helmet" in lower
        or "helm" in lower
        or "hood" in lower
        or "skullcap" in lower
        or "beard" in lower
        or "circlet" in lower
        or "moustache" in lower
    ):
        return "head"
    if "boot" in lower or "sabaton" in lower:
        return "foot_R" if "_-1" in lower else "foot_L"
    if "gauntlet" in lower or "vambrace" in lower:
        return "forearm_R" if "_-1" in lower else "forearm_L"
    if "book" in lower or "pouch" in lower or "belt" in lower or "script" in lower:
        return "hips"
    if "breastplate" in lower or "gorget" in lower or "clasp" in lower:
        return "chest"
    if "cape" in lower or "coat_back" in lower or "backplate" in lower or "back_plate" in lower:
        return "chest"
    if "tabard" in lower or "parchment" in lower:
        return "hips"
    if "pauldron" in lower and "_-1" in lower:
        return "shoulder_R"
    if "pauldron" in lower and "_1" in lower:
        return "shoulder_L"
    return None


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
        arm_obj.animation_data.action = action

        for bone_name, keyframe_list in action_def["keyframes"].items():
            pose_bone = arm_obj.pose.bones.get(bone_name)
            if pose_bone is None:
                continue
            pose_bone.rotation_mode = 'XYZ'

            for frame, loc, rot in keyframe_list:
                # Blender 5 stores Action data behind the animation API rather
                # than direct action.fcurves access. keyframe_insert works
                # across Blender 3.6-5.x and still exports to GLB clips.
                pose_bone.location = loc
                pose_bone.rotation_euler = rot
                pose_bone.keyframe_insert(data_path="location", frame=frame)
                pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame)

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

    arm_obj.animation_data.action = None
    for pose_bone in arm_obj.pose.bones:
        pose_bone.rotation_mode = 'XYZ'
        pose_bone.location = (0, 0, 0)
        pose_bone.rotation_euler = (0, 0, 0)
        pose_bone.scale = (1, 1, 1)
    bpy.context.view_layer.update()
