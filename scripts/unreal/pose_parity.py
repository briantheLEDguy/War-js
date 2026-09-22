"""Compare source skinning with Unreal using the fixed FBX X/-Y/Z basis."""
import math

TOLERANCE_CM = 0.1
SOURCE_PROBES = ((0, 0, 0), (1, 0, 0), (0, -1, 0), (0, 0, 1))


def to_unreal(point):
    return [point[0] * 100, -point[1] * 100, point[2] * 100]


def compare_frame(source, actual):
    maximum_joint = 0.0
    maximum_skin = 0.0
    for key, position in source["joints"].items():
        bone = key.split("/")[-1]
        if bone not in actual:
            raise ValueError(f"Unreal lost source bone {key}")
        joint_error = math.dist(to_unreal(position), actual[bone]["position"])
        if not math.isfinite(joint_error):
            raise ValueError(f"Nonfinite joint transform for {key}")
        maximum_joint = max(maximum_joint, joint_error)
        matrix = source["deformations"][key]
        for index, point in enumerate(SOURCE_PROBES):
            transformed = [sum(matrix[row * 4 + column] * point[column] for column in range(3))
                           + matrix[row * 4 + 3] for row in range(3)]
            error = math.dist(to_unreal(transformed), actual[bone]["deformedBasis"][index])
            if not math.isfinite(error):
                raise ValueError(f"Nonfinite skinning transform for {key}")
            maximum_skin = max(maximum_skin, error)
    if maximum_joint > TOLERANCE_CM or maximum_skin > TOLERANCE_CM:
        raise ValueError(f"Unreal pose mismatch: joints={maximum_joint:.6f}cm, skin={maximum_skin:.6f}cm")
    return maximum_joint, maximum_skin


def evaluate_frame(unreal, animation, seconds, options):
    # glTF float32 endpoints can exceed the imported duration by sub-microseconds.
    # Unreal returns a reference pose outside the clip instead of its final pose.
    seconds = bounded_sample_time(seconds, float(unreal.AnimationLibrary.get_sequence_length(animation)))
    pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(animation, seconds, options)
    result = {}
    for bone in unreal.AnimPoseExtensions.get_bone_names(pose):
        transform = unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
        reference = unreal.AnimPoseExtensions.get_ref_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
        point = transform.translation
        probes = []
        for xyz in ((0, 0, 0), (100, 0, 0), (0, 100, 0), (0, 0, 100)):
            vertex = transform.transform_location(reference.inverse_transform_location(unreal.Vector(*xyz)))
            probes.append([vertex.x, vertex.y, vertex.z])
        result[str(bone)] = {"position": [point.x, point.y, point.z], "deformedBasis": probes}
    return result


def bounded_sample_time(seconds, duration):
    if not math.isfinite(seconds) or not math.isfinite(duration) or duration < 0 or seconds < 0 or seconds > duration + 0.000001:
        raise ValueError("Animation sample is outside the imported duration")
    return min(seconds, duration)


def verify_animations(unreal, records, source):
    results = []
    for record in records:
        name = record["sourceClipName"]
        animation = unreal.load_asset(record["path"])
        if not unreal.WarImportLibrary.prepare_compressed_animation(animation):
            raise ValueError(f"Clip {name}: current-platform compression is unavailable")
        for mode in (unreal.AnimDataEvalType.RAW, unreal.AnimDataEvalType.COMPRESSED):
            options = unreal.AnimPoseEvaluationOptions()
            options.set_editor_property("evaluation_type", mode)
            maxima = [0.0, 0.0]
            for seconds, frame in zip(source[name]["sampleTimesSeconds"], source[name]["samples"], strict=True):
                try:
                    errors = compare_frame(frame, evaluate_frame(unreal, animation, seconds, options))
                except ValueError as error:
                    raise ValueError(f"Clip {name}, {mode}, time {seconds:.6f}s: {error}") from error
                maxima = [max(before, after) for before, after in zip(maxima, errors)]
            results.append({"clip": name, "evaluation": str(mode), "samples": len(source[name]["samples"]),
                            "maxJointErrorCm": maxima[0], "maxSkinTransformErrorCm": maxima[1]})
    return {"status": "passed", "basis": "X,-Y,Z; meters to centimeters", "toleranceCm": TOLERANCE_CM,
            "clips": results, "visualApproval": False}
