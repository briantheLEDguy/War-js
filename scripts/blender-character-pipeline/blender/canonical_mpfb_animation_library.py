"""MPFB-aware animation overrides for the canonical humanoid game rig.

The legacy project keyframes in :mod:`anim_library` were authored against a
different rest-axis convention.  These overrides express rotations around the
Blender armature axes instead:

* X: sagittal pitch (forward/back)
* Y: lateral roll (out/in)
* Z: vertical yaw (left/right)

The adapter converts those armature-space deltas into each MPFB bone's local
rest basis before keying.  Locations retain the legacy Y-up tuple convention
so the existing deterministic translation conversion remains the only one.
"""

from __future__ import annotations

from copy import deepcopy

from anim_library import ACTIONS


DEFAULT_ANIMATION_PROFILE = "unarmed"
ANIMATION_PROFILES = (DEFAULT_ANIMATION_PROFILE, "battle_prelate_hammer")


# Narrow, in-place locomotion shared by every MPFB humanoid.  Rotating around
# armature X avoids the mirrored thigh rest axes that made the old local-X
# values throw both knees sideways.
MPFB_BASE_OVERRIDES = {
    "walk": {
        "rotation_space": "ARMATURE",
        "keyframes": {
            "hips": [
                (0, (0, 0.000, 0), (0.000, 0.000, -0.018)),
                (7, (0, 0.020, 0), (0.000, 0.000, 0.000)),
                (15, (0, 0.000, 0), (0.000, 0.000, 0.018)),
                (22, (0, 0.020, 0), (0.000, 0.000, 0.000)),
                (30, (0, 0.000, 0), (0.000, 0.000, -0.018)),
            ],
            "spine": [
                (0, (0, 0, 0), (0.035, 0.000, 0.012)),
                (15, (0, 0, 0), (0.035, 0.000, -0.012)),
                (30, (0, 0, 0), (0.035, 0.000, 0.012)),
            ],
            "thigh_L": [
                (0, (0, 0, 0), (-0.36, 0.000, 0.000)),
                (7, (0, 0, 0), (-0.08, 0.000, 0.000)),
                (15, (0, 0, 0), (0.34, 0.000, 0.000)),
                (22, (0, 0, 0), (0.05, 0.000, 0.000)),
                (30, (0, 0, 0), (-0.36, 0.000, 0.000)),
            ],
            "thigh_R": [
                (0, (0, 0, 0), (0.34, 0.000, 0.000)),
                (7, (0, 0, 0), (0.05, 0.000, 0.000)),
                (15, (0, 0, 0), (-0.36, 0.000, 0.000)),
                (22, (0, 0, 0), (-0.08, 0.000, 0.000)),
                (30, (0, 0, 0), (0.34, 0.000, 0.000)),
            ],
            "shin_L": [
                (0, (0, 0, 0), (0.18, 0.000, 0.000)),
                (7, (0, 0, 0), (0.72, 0.000, 0.000)),
                (15, (0, 0, 0), (0.08, 0.000, 0.000)),
                (22, (0, 0, 0), (0.12, 0.000, 0.000)),
                (30, (0, 0, 0), (0.18, 0.000, 0.000)),
            ],
            "shin_R": [
                (0, (0, 0, 0), (0.08, 0.000, 0.000)),
                (7, (0, 0, 0), (0.12, 0.000, 0.000)),
                (15, (0, 0, 0), (0.18, 0.000, 0.000)),
                (22, (0, 0, 0), (0.72, 0.000, 0.000)),
                (30, (0, 0, 0), (0.08, 0.000, 0.000)),
            ],
            "foot_L": [
                (0, (0, 0, 0), (-0.08, 0.000, 0.000)),
                (7, (0, 0, 0), (0.14, 0.000, 0.000)),
                (15, (0, 0, 0), (0.04, 0.000, 0.000)),
                (30, (0, 0, 0), (-0.08, 0.000, 0.000)),
            ],
            "foot_R": [
                (0, (0, 0, 0), (0.04, 0.000, 0.000)),
                (15, (0, 0, 0), (-0.08, 0.000, 0.000)),
                (22, (0, 0, 0), (0.14, 0.000, 0.000)),
                (30, (0, 0, 0), (0.04, 0.000, 0.000)),
            ],
            "upper_arm_L": [
                (0, (0, 0, 0), (0.24, -0.02, 0.000)),
                (15, (0, 0, 0), (-0.24, -0.02, 0.000)),
                (30, (0, 0, 0), (0.24, -0.02, 0.000)),
            ],
            "upper_arm_R": [
                (0, (0, 0, 0), (-0.24, 0.02, 0.000)),
                (15, (0, 0, 0), (0.24, 0.02, 0.000)),
                (30, (0, 0, 0), (-0.24, 0.02, 0.000)),
            ],
        },
    },
    "run": {
        "rotation_space": "ARMATURE",
        "keyframes": {
            "hips": [
                (0, (0, 0.000, 0), (0.000, 0.000, -0.026)),
                (5, (0, 0.035, 0), (0.000, 0.000, 0.000)),
                (10, (0, 0.000, 0), (0.000, 0.000, 0.026)),
                (15, (0, 0.035, 0), (0.000, 0.000, 0.000)),
                (20, (0, 0.000, 0), (0.000, 0.000, -0.026)),
            ],
            "spine": [
                (0, (0, 0, 0), (0.12, 0.000, 0.018)),
                (10, (0, 0, 0), (0.10, 0.000, -0.018)),
                (20, (0, 0, 0), (0.12, 0.000, 0.018)),
            ],
            "chest": [
                (0, (0, 0, 0), (0.045, 0.000, -0.018)),
                (10, (0, 0, 0), (0.045, 0.000, 0.018)),
                (20, (0, 0, 0), (0.045, 0.000, -0.018)),
            ],
            "thigh_L": [
                (0, (0, 0, 0), (-0.62, 0.000, 0.000)),
                (5, (0, 0, 0), (-0.12, 0.000, 0.000)),
                (10, (0, 0, 0), (0.55, 0.000, 0.000)),
                (15, (0, 0, 0), (0.10, 0.000, 0.000)),
                (20, (0, 0, 0), (-0.62, 0.000, 0.000)),
            ],
            "thigh_R": [
                (0, (0, 0, 0), (0.55, 0.000, 0.000)),
                (5, (0, 0, 0), (0.10, 0.000, 0.000)),
                (10, (0, 0, 0), (-0.62, 0.000, 0.000)),
                (15, (0, 0, 0), (-0.12, 0.000, 0.000)),
                (20, (0, 0, 0), (0.55, 0.000, 0.000)),
            ],
            "shin_L": [
                (0, (0, 0, 0), (0.28, 0.000, 0.000)),
                (5, (0, 0, 0), (1.25, 0.000, 0.000)),
                (10, (0, 0, 0), (0.10, 0.000, 0.000)),
                (15, (0, 0, 0), (0.18, 0.000, 0.000)),
                (20, (0, 0, 0), (0.28, 0.000, 0.000)),
            ],
            "shin_R": [
                (0, (0, 0, 0), (0.10, 0.000, 0.000)),
                (5, (0, 0, 0), (0.18, 0.000, 0.000)),
                (10, (0, 0, 0), (0.28, 0.000, 0.000)),
                (15, (0, 0, 0), (1.25, 0.000, 0.000)),
                (20, (0, 0, 0), (0.10, 0.000, 0.000)),
            ],
            "foot_L": [
                (0, (0, 0, 0), (-0.12, 0.000, 0.000)),
                (5, (0, 0, 0), (0.20, 0.000, 0.000)),
                (10, (0, 0, 0), (0.06, 0.000, 0.000)),
                (20, (0, 0, 0), (-0.12, 0.000, 0.000)),
            ],
            "foot_R": [
                (0, (0, 0, 0), (0.06, 0.000, 0.000)),
                (10, (0, 0, 0), (-0.12, 0.000, 0.000)),
                (15, (0, 0, 0), (0.20, 0.000, 0.000)),
                (20, (0, 0, 0), (0.06, 0.000, 0.000)),
            ],
            "upper_arm_L": [
                (0, (0, 0, 0), (0.48, -0.03, 0.000)),
                (10, (0, 0, 0), (-0.42, -0.03, 0.000)),
                (20, (0, 0, 0), (0.48, -0.03, 0.000)),
            ],
            "upper_arm_R": [
                (0, (0, 0, 0), (-0.42, 0.03, 0.000)),
                (10, (0, 0, 0), (0.48, 0.03, 0.000)),
                (20, (0, 0, 0), (-0.42, 0.03, 0.000)),
            ],
        },
    },
}


_HAMMER_CARRY = {
    # Low-rib one-hand shoulder carry: the grip stays below the chest while
    # the attachment cant places the head behind the right shoulder.
    "shoulder_R": (0.00, 0.02, -0.02),
    "upper_arm_R": (-0.16, 0.06, -0.04),
    "forearm_R": (-0.40, 0.02, -0.05),
    # The attachment adapter aligns the shaft with the palm.  The wrist only
    # supplies a modest, reviewable carry angle instead of compensating for a
    # mismatched socket with an anatomically impossible bend.
    "hand_R": (0.08, -0.15, -0.06),
}


def _held_pose(frames: tuple[int, ...], breathing: float = 0.0) -> dict:
    result = {}
    midpoint = frames[len(frames) // 2]
    for bone_name, rotation in _HAMMER_CARRY.items():
        rows = []
        for frame in frames:
            delta = breathing if frame == midpoint else 0.0
            adjusted = (
                rotation[0] + (delta if bone_name in {"upper_arm_R", "forearm_R"} else 0.0),
                rotation[1],
                rotation[2],
            )
            rows.append((frame, (0, 0, 0), adjusted))
        result[bone_name] = rows
    return result


BATTLE_PRELATE_HAMMER_OVERRIDES = {
    "idle": {
        "rotation_space": "ARMATURE",
        "keyframes": {
            "hips": [
                (0, (0, 0, 0), (0.000, 0.000, -0.025)),
                (30, (0, 0.008, 0), (0.000, 0.000, -0.020)),
                (60, (0, 0, 0), (0.000, 0.000, -0.025)),
            ],
            "spine": [
                (0, (0, 0, 0), (0.025, 0.000, 0.020)),
                (30, (0, 0, 0), (0.035, 0.000, 0.015)),
                (60, (0, 0, 0), (0.025, 0.000, 0.020)),
            ],
            "upper_arm_L": [
                (0, (0, 0, 0), (0.04, -0.03, 0.02)),
                (30, (0, 0, 0), (0.02, -0.03, 0.02)),
                (60, (0, 0, 0), (0.04, -0.03, 0.02)),
            ],
            **_held_pose((0, 30, 60), breathing=0.015),
        },
    },
    "walk": {
        "rotation_space": "ARMATURE",
        "keyframes": {
            **_held_pose((0, 7, 15, 22, 30), breathing=0.018),
        },
    },
    "run": {
        "rotation_space": "ARMATURE",
        "keyframes": {
            **_held_pose((0, 5, 10, 15, 20), breathing=0.025),
            "shoulder_R": [
                (0, (0, 0, 0), (0.00, 0.06, -0.06)),
                (5, (0, 0, 0), (0.01, 0.07, -0.06)),
                (10, (0, 0, 0), (0.00, 0.06, -0.06)),
                (15, (0, 0, 0), (0.01, 0.07, -0.06)),
                (20, (0, 0, 0), (0.00, 0.06, -0.06)),
            ],
        },
    },
    "combat_idle": {
        "rotation_space": "ARMATURE",
        "keyframes": {
            "hips": [
                (0, (0, -0.025, 0), (0.055, 0.000, -0.08)),
                (40, (0, -0.018, 0), (0.060, 0.000, -0.06)),
                (80, (0, -0.025, 0), (0.055, 0.000, -0.08)),
            ],
            "spine": [
                (0, (0, 0, 0), (0.080, 0.000, 0.08)),
                (40, (0, 0, 0), (0.070, 0.000, 0.06)),
                (80, (0, 0, 0), (0.080, 0.000, 0.08)),
            ],
            "thigh_L": [
                (0, (0, 0, 0), (-0.08, 0.000, 0.000)),
                (40, (0, 0, 0), (-0.07, 0.000, 0.000)),
                (80, (0, 0, 0), (-0.08, 0.000, 0.000)),
            ],
            "thigh_R": [
                (0, (0, 0, 0), (0.10, 0.000, 0.000)),
                (40, (0, 0, 0), (0.09, 0.000, 0.000)),
                (80, (0, 0, 0), (0.10, 0.000, 0.000)),
            ],
            "upper_arm_L": [
                (0, (0, 0, 0), (-0.28, -0.10, 0.10)),
                (40, (0, 0, 0), (-0.25, -0.10, 0.08)),
                (80, (0, 0, 0), (-0.28, -0.10, 0.10)),
            ],
            **_held_pose((0, 40, 80), breathing=0.020),
        },
    },
    "attack_melee": {
        "rotation_space": "ARMATURE",
        "keyframes": {
            "hips": [
                (0, (0, 0, 0), (0.045, 0.000, -0.08)),
                (7, (0, 0, 0), (0.030, 0.000, -0.18)),
                (14, (0, 0.025, -0.015), (0.090, 0.000, 0.20)),
                (21, (0, 0.012, -0.006), (0.070, 0.000, 0.12)),
                (30, (0, 0, 0), (0.045, 0.000, -0.08)),
            ],
            "spine": [
                (0, (0, 0, 0), (0.060, 0.000, 0.08)),
                (7, (0, 0, 0), (0.020, 0.000, -0.24)),
                (14, (0, 0, 0), (0.180, 0.000, 0.34)),
                (21, (0, 0, 0), (0.130, 0.000, 0.22)),
                (30, (0, 0, 0), (0.060, 0.000, 0.08)),
            ],
            "chest": [
                (0, (0, 0, 0), (0.020, 0.000, 0.04)),
                (7, (0, 0, 0), (-0.050, 0.000, -0.20)),
                (14, (0, 0, 0), (0.130, 0.000, 0.30)),
                (21, (0, 0, 0), (0.080, 0.000, 0.16)),
                (30, (0, 0, 0), (0.020, 0.000, 0.04)),
            ],
            "upper_chest": [
                (0, (0, 0, 0), (0.000, 0.000, 0.02)),
                (7, (0, 0, 0), (-0.040, 0.000, -0.12)),
                (14, (0, 0, 0), (0.090, 0.000, 0.18)),
                (21, (0, 0, 0), (0.050, 0.000, 0.10)),
                (30, (0, 0, 0), (0.000, 0.000, 0.02)),
            ],
            "shoulder_R": [
                (0, (0, 0, 0), (0.00, 0.02, -0.02)),
                (7, (0, 0, 0), (0.12, 0.30, -0.12)),
                (14, (0, 0, 0), (-0.10, 0.08, 0.14)),
                (21, (0, 0, 0), (-0.03, 0.06, 0.05)),
                (30, (0, 0, 0), (0.00, 0.02, -0.02)),
            ],
            "upper_arm_R": [
                (0, (0, 0, 0), (-0.16, 0.06, -0.04)),
                (7, (0, 0, 0), (0.45, 1.28, -0.25)),
                (14, (0, 0, 0), (-0.62, 0.05, 0.20)),
                (21, (0, 0, 0), (-0.40, 0.16, 0.10)),
                (30, (0, 0, 0), (-0.16, 0.06, -0.04)),
            ],
            "forearm_R": [
                (0, (0, 0, 0), (-0.40, 0.02, -0.05)),
                (7, (0, 0, 0), (-0.85, 0.08, -0.14)),
                (14, (0, 0, 0), (-0.08, 0.02, 0.10)),
                (21, (0, 0, 0), (-0.28, 0.02, 0.03)),
                (30, (0, 0, 0), (-0.40, 0.02, -0.05)),
            ],
            "hand_R": [
                (0, (0, 0, 0), (0.08, -0.15, -0.06)),
                (7, (0, 0, 0), (0.10, -0.30, -0.20)),
                (12, (0, 0, 0), (0.55, 0.10, 0.25)),
                (14, (0, 0, 0), (0.85, 0.35, 0.45)),
                (21, (0, 0, 0), (0.45, 0.15, 0.30)),
                (30, (0, 0, 0), (0.08, -0.15, -0.06)),
            ],
            "upper_arm_L": [
                (0, (0, 0, 0), (-0.12, -0.08, 0.08)),
                (7, (0, 0, 0), (-0.48, -0.18, 0.18)),
                (14, (0, 0, 0), (0.24, -0.12, -0.16)),
                (21, (0, 0, 0), (0.08, -0.08, -0.08)),
                (30, (0, 0, 0), (-0.12, -0.08, 0.08)),
            ],
            "forearm_L": [
                (0, (0, 0, 0), (-0.20, 0.00, 0.00)),
                (7, (0, 0, 0), (-0.58, 0.00, 0.08)),
                (14, (0, 0, 0), (-0.14, 0.00, -0.06)),
                (30, (0, 0, 0), (-0.20, 0.00, 0.00)),
            ],
        },
    },
}


PROFILE_OVERRIDES = {
    "battle_prelate_hammer": BATTLE_PRELATE_HAMMER_OVERRIDES,
}


def _merge_clip(target: dict, override: dict) -> None:
    if "duration_frames" in override:
        target["duration_frames"] = override["duration_frames"]
    if "loop" in override:
        target["loop"] = override["loop"]
    if "rotation_space" in override:
        target["rotation_space"] = override["rotation_space"]
    if "keyframes" in override:
        target.setdefault("keyframes", {}).update(deepcopy(override["keyframes"]))


def make_canonical_mpfb_actions(profile: str = DEFAULT_ANIMATION_PROFILE) -> dict:
    """Return legacy clips with MPFB locomotion and optional equipment poses."""
    if profile not in ANIMATION_PROFILES:
        raise ValueError(f"Unsupported canonical MPFB animation profile: {profile}")
    actions = deepcopy(ACTIONS)
    for name, override in MPFB_BASE_OVERRIDES.items():
        _merge_clip(actions[name], override)
    for name, override in PROFILE_OVERRIDES.get(profile, {}).items():
        _merge_clip(actions[name], override)
    return actions
