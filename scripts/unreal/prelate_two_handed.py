"""Roles and bone chains for the owner's local Mixamo two-handed animation set."""
CLIPS = {
    "idle": "Great Sword Idle.fbx",
    "idle_relaxed": "Great Sword Idle (1).fbx",
    "walk": "Great Sword Walk.fbx",
    "strafe": "Great Sword Strafe.fbx",
    "slash": "Great Sword Slash.fbx",
    "slash_alternate": "Great Sword Slash (1).fbx",
    "jump": "Great Sword Jump.fbx",
    "jump_alternate": "Great Sword Jump (1).fbx",
    "jump_attack": "Great Sword Jump Attack.fbx",
    "slide_attack": "Great Sword Slide Attack.fbx",
    "spin_attack": "Great Sword High Spin Attack.fbx",
}

# Jump and specials remain explicit library entries until their movement/action
# timing is integrated. No supplied run/death/cast is substituted with a walk.
LIVE_ROLES = {"idle": "idle", "combat_idle": "idle", "walk": "walk", "attack_melee": "slash_alternate"}


def merge_bindings(existing, imported, grip_report):
    if set(imported) != set(CLIPS) or len(set(imported.values())) != len(CLIPS):
        raise ValueError("Every supplied clip needs its own imported animation")
    for clip in set(LIVE_ROLES.values()):
        error = grip_report.get(clip, {}).get("maximumUnreachableCm", float("inf"))
        if not 0 <= error <= .1:
            raise ValueError("Unreachable support grip in live clip: " + clip)
    result = dict(existing)
    result.update({"two_handed_" + key: value for key, value in imported.items()})
    result.update({role: imported[key] for role, key in LIVE_ROLES.items()})
    return result

# Endpoints are anatomical chains, not matching local bone axes.
CHAINS = [
    ("Spine", "Spine", "Spine2", "spine", "upper_chest"),
    ("Head", "Neck", "Head", "neck", "head"),
]
for side, suffix in (("Left", "L"), ("Right", "R")):
    CHAINS.extend([
        (side + "Clavicle", side + "Shoulder", side + "Shoulder", "shoulder_" + suffix, "shoulder_" + suffix),
        (side + "Arm", side + "Arm", side + "Hand", "upper_arm_" + suffix, "hand_" + suffix),
        (side + "Leg", side + "UpLeg", side + "Foot", "thigh_" + suffix, "foot_" + suffix),
        (side + "Toe", side + "ToeBase", side + "ToeBase", "toe_" + suffix, "toe_" + suffix),
    ])
    for finger in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
        CHAINS.append((side + finger, side + "Hand" + finger + "1", side + "Hand" + finger + "3",
                       finger.lower() + "_01_" + suffix, finger.lower() + "_03_" + suffix))
