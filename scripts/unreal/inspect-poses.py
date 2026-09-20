"""Export actual Unreal component-space bone samples for import diagnostics."""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
for profile in ("npc_frontier_sunmeadow_empire_herbalist", "mire_warbrute_m"):
    folder = ROOT / "artifacts/unreal/converted" / profile
    receipt = json.loads((folder / "editor-import.json").read_text())
    source = json.loads((folder / "animation-samples.json").read_text())["source"]
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property("evaluation_type", unreal.AnimDataEvalType.RAW)
    result = {}
    for clip in receipt["animations"]:
        name = clip["sourceClipName"]
        animation = unreal.load_asset(clip["path"])
        frames = []
        for time in source[name]["sampleTimesSeconds"]:
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(animation, time, options)
            joints = {}
            for bone in unreal.AnimPoseExtensions.get_bone_names(pose):
                transform = unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
                point = transform.translation
                reference = unreal.AnimPoseExtensions.get_ref_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
                basis = []
                for xyz in ((0, 0, 0), (100, 0, 0), (0, 100, 0), (0, 0, 100)):
                    vertex = transform.transform_location(reference.inverse_transform_location(unreal.Vector(*xyz)))
                    basis.append([vertex.x, vertex.y, vertex.z])
                joints[str(bone)] = {"position": [point.x, point.y, point.z], "deformedBasis": basis}
            frames.append(joints)
        result[name] = frames
    (folder / "unreal-pose-samples.json").write_text(json.dumps(result, indent=2) + "\n")
