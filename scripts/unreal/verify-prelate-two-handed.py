"""Verify saved native bindings, bind units, limb lengths and compressed poses."""
import json
import math
from pathlib import Path
import sys
import unreal

sys.path.insert(0, str(Path(__file__).parent))
from prelate_two_handed import LIVE_ROLES

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/unreal/two-handed"
(OUT / "verification.json").unlink(missing_ok=True)
receipt = json.loads((OUT / "retarget.json").read_text())
weapon = json.loads((OUT / "weapon.json").read_text())
visual = unreal.load_asset("/Game/MigrationProof/Visual_civic_battle_prelate_m")
if visual.validate_for_spawn(visual.realm) != "":
    raise RuntimeError("Saved visual fails native spawn validation")
registry = json.loads((ROOT / "unreal/AegisWar/Content/Migration/visual-imports.json").read_text())
binding = next(row for row in registry["entries"] if row["profileKey"] == str(visual.profile_key))
if binding["skeletalMeshPath"] != visual.skeletal_mesh.get_path_name() or binding["sourceSha256"] != visual.source_sha256:
    raise RuntimeError("Saved visual differs from the runtime admission registry")
for animation in list(visual.imported_animations.values()) + [visual.idle_animation]:
    if animation.get_path_name() not in binding["animationPaths"]:
        raise RuntimeError("Animation is absent from the runtime admission registry")
options = []
for mode in (unreal.AnimDataEvalType.RAW, unreal.AnimDataEvalType.COMPRESSED):
    option = unreal.AnimPoseEvaluationOptions()
    option.set_editor_properties(dict(evaluation_type=mode, optional_skeletal_mesh=visual.skeletal_mesh))
    options.append(option)
limbs = [(prefix + side, end + side) for side in ("L", "R")
         for prefix, end in (("upper_arm_", "forearm_"), ("forearm_", "hand_"), ("thigh_", "shin_"), ("shin_", "foot_"))]
result = {}
for key, clip in receipt["clips"].items():
    animation = unreal.load_asset(clip["animation"])
    if not unreal.WarImportLibrary.prepare_compressed_animation(animation):
        raise RuntimeError("Missing compressed data for " + key)
    count = round(clip["duration"] * 60) + 1
    error, limb_error = 0., 0.
    ground_clearance = float("inf")
    for index in range(count):
        seconds = min(index / 60, clip["duration"])
        raw, compressed = [unreal.AnimPoseExtensions.get_anim_pose_at_time(animation, seconds, option) for option in options]
        reference_hand = unreal.AnimPoseExtensions.get_ref_bone_pose(raw, "hand_R", unreal.AnimPoseSpaces.WORLD)
        hand = unreal.AnimPoseExtensions.get_bone_pose(compressed, "hand_R", unreal.AnimPoseSpaces.WORLD)
        for point in weapon["weaponBoundsWorld"]:
            local = reference_hand.inverse_transform_location(unreal.Vector(point[0] * 100, -point[1] * 100, point[2] * 100))
            ground_clearance = min(ground_clearance, hand.transform_location(local).z)
        names = unreal.AnimPoseExtensions.get_bone_names(raw)
        positions = []
        for pose in (raw, compressed):
            positions.append({str(bone): unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD).translation for bone in names})
        for bone in names:
            distance = (positions[0][str(bone)] - positions[1][str(bone)]).length()
            if not math.isfinite(distance):
                raise RuntimeError("Nonfinite pose: " + key)
            error = max(error, distance)
        for start, end in limbs:
            reference_a = unreal.AnimPoseExtensions.get_ref_bone_pose(raw, start, unreal.AnimPoseSpaces.WORLD).translation
            reference_b = unreal.AnimPoseExtensions.get_ref_bone_pose(raw, end, unreal.AnimPoseSpaces.WORLD).translation
            limb_error = max(limb_error, abs((positions[0][start] - positions[0][end]).length() - (reference_a - reference_b).length()))
    if error > .1 or limb_error > .01:
        raise RuntimeError(f"{key}: compression={error}cm, limb stretch={limb_error}cm")
    if key in LIVE_ROLES.values() and ground_clearance < 0:
        raise RuntimeError(f"Live clip {key} puts the equipped hammer bounds below the ground: {ground_clearance}cm")
    result[key] = dict(samples=count, maximumCompressionErrorCm=error, maximumLimbLengthErrorCm=limb_error,
                       minimumHammerBoundsHeightCm=ground_clearance)
(OUT / "verification.json").write_text(json.dumps(dict(status="passed", nativeSpawnValidation=True,
    savedRegistryMatches=True, sampleRate=60, clips=result, artApproval=False), indent=2) + "\n")
unreal.log("WAR_PRELATE_TWO_HANDED_VERIFIED")
