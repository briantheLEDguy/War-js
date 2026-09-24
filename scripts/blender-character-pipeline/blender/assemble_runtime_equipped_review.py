"""Assemble a draft equipped review from already-serialized runtime GLBs.

The verified body GLB owns the only armature and rest pose. Each modular
armor GLB is imported independently, checked against that armature's rest pose,
rebound by canonical bone name, and stripped of its duplicate armature before a
combined review GLB is exported. The emitted file is then imported into a clean
scene and rendered in its rest pose. Native equipped animation is verified separately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector


REQUIRED_CLIPS = ()
EXPECTED_SLOTS = (
    "head",
    "shoulders",
    "chest",
    "hands",
    "waist",
    "legs",
    "feet",
    "back",
    "tabard",
)
RIG_NAME = "humanoid_game_v2"
# The serialized hammer's +Z shaft axis and MPFB's right-hand socket axis do
# not share a grip convention.  This local attachment rotation makes the
# shaft rise from the palm in bind pose; animation remains responsible for
# the carry angle and strike.  It changes no mesh vertices.
HAMMER_GRIP_ROTATION = Quaternion((0.9290, 0.2974, -0.2204, 0.0)).normalized()

def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-glb", required=True)
    parser.add_argument("--modules-dir", required=True)
    parser.add_argument("--hammer-glb", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--report")
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path: Path) -> list[bpy.types.Object]:
    if not path.is_file():
        raise FileNotFoundError(path)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.context.scene.objects if obj not in before]


def delete_objects(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def armature_modifier(mesh: bpy.types.Object) -> bpy.types.ArmatureModifier:
    modifiers = [modifier for modifier in mesh.modifiers if modifier.type == "ARMATURE"]
    if len(modifiers) != 1:
        raise RuntimeError(f"{mesh.name} must have exactly one armature modifier; found {len(modifiers)}")
    return modifiers[0]


def matrix_max_delta(left: Matrix, right: Matrix) -> float:
    return max(abs(left[row][column] - right[row][column]) for row in range(4) for column in range(4))


def compare_rest_rigs(source: bpy.types.Object, target: bpy.types.Object) -> dict:
    source_names = {bone.name for bone in source.data.bones}
    target_names = {bone.name for bone in target.data.bones}
    missing = sorted(target_names - source_names)
    extra = sorted(source_names - target_names)
    deltas = {
        name: matrix_max_delta(source.data.bones[name].matrix_local, target.data.bones[name].matrix_local)
        for name in sorted(source_names & target_names)
    }
    maximum = max(deltas.values(), default=0.0)
    return {
        "sourceBoneCount": len(source_names),
        "targetBoneCount": len(target_names),
        "missingBones": missing,
        "extraBones": extra,
        "maxRestMatrixDelta": maximum,
        "passed": not missing and not extra and maximum <= 1e-5,
    }


def vertex_influence_audit(mesh: bpy.types.Object, bone_names: set[str]) -> dict:
    bone_groups = {group.index for group in mesh.vertex_groups if group.name in bone_names}
    maximum = 0
    unweighted = 0
    for vertex in mesh.data.vertices:
        count = sum(
            1
            for assignment in vertex.groups
            if assignment.group in bone_groups and assignment.weight > 1e-8
        )
        maximum = max(maximum, count)
        if count == 0:
            unweighted += 1
    return {
        "vertexCount": len(mesh.data.vertices),
        "maxInfluences": maximum,
        "unweightedVertices": unweighted,
        "passed": maximum <= 4 and unweighted == 0,
    }


def rebind_module(
    module_path: Path,
    target_rig: bpy.types.Object,
) -> tuple[bpy.types.Object, dict]:
    imported = import_glb(module_path)
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    meshes = [
        obj
        for obj in imported
        if obj.type == "MESH" and str(obj.get("assetId", "")).startswith("arm.")
    ]
    if len(armatures) != 1 or len(meshes) != 1:
        raise RuntimeError(
            f"{module_path.name} must import one armor mesh and one armature; "
            f"found {len(meshes)} mesh(es), {len(armatures)} armature(s)"
        )
    duplicate_rig = armatures[0]
    mesh = meshes[0]
    rest_audit = compare_rest_rigs(duplicate_rig, target_rig)
    if not rest_audit["passed"]:
        raise RuntimeError(f"Rest rig mismatch for {module_path.name}: {rest_audit}")
    modifier = armature_modifier(mesh)
    if modifier.object != duplicate_rig:
        raise RuntimeError(f"{module_path.name} is not bound to its imported armature")
    world = mesh.matrix_world.copy()
    modifier.object = target_rig
    mesh.parent = target_rig
    mesh.matrix_parent_inverse = target_rig.matrix_world.inverted()
    mesh.matrix_world = world
    influence_audit = vertex_influence_audit(mesh, {bone.name for bone in target_rig.data.bones})
    if not influence_audit["passed"]:
        raise RuntimeError(f"Weight audit failed for {module_path.name}: {influence_audit}")
    slot = str(mesh.get("armorSlot", ""))
    if slot not in EXPECTED_SLOTS:
        raise RuntimeError(f"{module_path.name} has invalid armorSlot metadata: {slot}")
    mesh["assemblySource"] = str(module_path)
    mesh["assemblySourceSha256"] = sha256(module_path)
    mesh["assemblyReboundTo"] = RIG_NAME
    mesh["lifecycleStatus"] = "draft"
    mesh["reviewStatus"] = "pending"
    mesh["promotionEligible"] = False
    delete_objects([obj for obj in imported if obj != mesh])
    bpy.context.view_layer.update()
    if modifier.object != target_rig or mesh.parent != target_rig:
        raise RuntimeError(f"Rebind did not persist for {module_path.name}")
    return mesh, {
        "slot": slot,
        "assetId": mesh.get("assetId"),
        "source": str(module_path),
        "sourceSha256": sha256(module_path),
        "restRig": rest_audit,
        "weights": influence_audit,
    }


def attach_hammer(path: Path, socket: bpy.types.Object) -> tuple[list[bpy.types.Object], dict]:
    imported = import_glb(path)
    roots = [obj for obj in imported if obj.parent not in imported]
    root = next((obj for obj in roots if obj.name.startswith("battle_prelate_hammer_root")), None)
    if not root:
        raise RuntimeError(f"Hammer must expose battle_prelate_hammer_root: {path}")
    world_grip = next((obj for obj in imported if obj.name.startswith("weapon_grip_socket_hand_R")), None)
    if not world_grip:
        raise RuntimeError("Hammer is missing weapon_grip_socket_hand_R")
    root.parent = socket
    root.matrix_parent_inverse = Matrix.Identity(4)
    root.location = (0.0, 0.0, 0.0)
    root.rotation_mode = "QUATERNION"
    root.rotation_quaternion = HAMMER_GRIP_ROTATION
    root.scale = (1.0, 1.0, 1.0)
    secondary_grip = next(
        (obj for obj in imported if obj.name.startswith("weapon_grip_socket_hand_L")),
        None,
    )
    if secondary_grip is None:
        secondary_grip = bpy.data.objects.new("weapon_grip_socket_hand_L", None)
        bpy.context.scene.collection.objects.link(secondary_grip)
        secondary_grip.parent = root
        secondary_grip.location = (0.0, 0.0, 0.30)
        secondary_grip.rotation_euler = (0.0, 0.0, 0.0)
        secondary_grip["targetSocket"] = "socket_hand_L"
        secondary_grip["gripRole"] = "secondary"
        imported.append(secondary_grip)
    for obj in imported:
        obj["assemblySource"] = str(path)
        obj["assemblySourceSha256"] = sha256(path)
        obj["lifecycleStatus"] = "draft"
        obj["reviewStatus"] = "pending"
        obj["promotionEligible"] = False
    bpy.context.view_layer.update()
    return imported, {
        "source": str(path),
        "sourceSha256": sha256(path),
        "targetSocket": socket.name,
        "root": root.name,
        "grip": world_grip.name,
        "secondaryGrip": secondary_grip.name,
        "handedness": "two_handed",
        "massClass": "heavy",
    }


def export_combined(output: Path, objects: list[bpy.types.Object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    options = {
        "filepath": str(output),
        "export_format": "GLB",
        "use_selection": True,
        "export_animations": False,
        "export_skins": True,
        "export_morph": True,
        "export_extras": True,
        "export_yup": True,
        "export_apply": False,
        "export_draco_mesh_compression_enable": False,
    }
    available = {prop.identifier for prop in bpy.ops.export_scene.gltf.get_rna_type().properties}
    if "export_animation_mode" in available:
        options["export_animation_mode"] = "ACTIONS"
    if "export_nla_strips" in available:
        options["export_nla_strips"] = False
    if "export_anim_single_armature" in available:
        options["export_anim_single_armature"] = True
    bpy.ops.export_scene.gltf(**options)
    bpy.ops.object.select_all(action="DESELECT")


def glb_document(path: Path) -> dict:
    payload = path.read_bytes()
    if payload[:4] != b"glTF" or int.from_bytes(payload[4:8], "little") != 2:
        raise RuntimeError(f"Not a GLB 2.0 file: {path}")
    offset = 12
    while offset + 8 <= len(payload):
        length = int.from_bytes(payload[offset : offset + 4], "little")
        kind = payload[offset + 4 : offset + 8]
        chunk = payload[offset + 8 : offset + 8 + length]
        if kind == b"JSON":
            return json.loads(chunk.rstrip(b" \t\r\n\x00").decode("utf-8"))
        offset += 8 + length
    raise RuntimeError(f"GLB JSON chunk missing: {path}")


def evaluated_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points = [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def bounds_snapshot(meshes: list[bpy.types.Object]) -> dict:
    rows = {}
    all_minima = []
    all_maxima = []
    for mesh in meshes:
        minimum, maximum = evaluated_bounds(mesh)
        center = (minimum + maximum) * 0.5
        extent = maximum - minimum
        rows[mesh.name] = {
            "assetId": mesh.get("assetId"),
            "minimum": list(minimum),
            "maximum": list(maximum),
            "center": list(center),
            "extent": list(extent),
        }
        all_minima.append(minimum)
        all_maxima.append(maximum)
    minimum = Vector(tuple(min(point[index] for point in all_minima) for index in range(3)))
    maximum = Vector(tuple(max(point[index] for point in all_maxima) for index in range(3)))
    return {
        "meshes": rows,
        "combined": {
            "minimum": list(minimum),
            "maximum": list(maximum),
            "center": list((minimum + maximum) * 0.5),
            "extent": list(maximum - minimum),
        },
    }


def vector(row: list[float]) -> Vector:
    return Vector(tuple(row))


def compare_pose_bounds(bind: dict, idle: dict) -> dict:
    bind_center = vector(bind["combined"]["center"])
    idle_center = vector(idle["combined"]["center"])
    bind_extent = vector(bind["combined"]["extent"])
    idle_extent = vector(idle["combined"]["extent"])
    character_height = max(bind_extent.z, 1e-6)
    combined_center_delta = (idle_center - bind_center).length
    combined_ratios = [idle_extent[index] / max(bind_extent[index], 1e-6) for index in range(3)]
    mesh_rows = []
    for name, bind_row in bind["meshes"].items():
        idle_row = idle["meshes"].get(name)
        if not idle_row:
            mesh_rows.append({"mesh": name, "missingInIdle": True, "passed": False})
            continue
        center_delta = (vector(idle_row["center"]) - vector(bind_row["center"])).length
        bind_mesh_extent = vector(bind_row["extent"])
        idle_mesh_extent = vector(idle_row["extent"])
        ratios = [
            idle_mesh_extent[index] / max(bind_mesh_extent[index], 1e-6)
            for index in range(3)
        ]
        passed = center_delta <= character_height * 0.20 and all(0.45 <= ratio <= 1.75 for ratio in ratios)
        mesh_rows.append({
            "mesh": name,
            "assetId": bind_row["assetId"],
            "centerDelta": center_delta,
            "extentRatios": ratios,
            "passed": passed,
        })
    passed = (
        combined_center_delta <= character_height * 0.12
        and all(0.50 <= ratio <= 1.40 for ratio in combined_ratios)
        and all(row["passed"] for row in mesh_rows)
    )
    return {
        "characterBindHeight": character_height,
        "combinedCenterDelta": combined_center_delta,
        "combinedExtentRatios": combined_ratios,
        "meshDeltas": mesh_rows,
        "thresholds": {
            "combinedCenterFractionOfHeight": 0.12,
            "combinedExtentRatio": [0.50, 1.40],
            "meshCenterFractionOfHeight": 0.20,
            "meshExtentRatio": [0.45, 1.75],
        },
        "passed": passed,
    }


def aim(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_views(meshes: list[bpy.types.Object], output_dir: Path) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for obj in list(bpy.context.scene.objects):
        if obj.get("runtimeAssemblyRenderSupport"):
            bpy.data.objects.remove(obj, do_unlink=True)
    snapshot = bounds_snapshot(meshes)
    minimum = vector(snapshot["combined"]["minimum"])
    maximum = vector(snapshot["combined"]["maximum"])
    center = vector(snapshot["combined"]["center"])
    extent = vector(snapshot["combined"]["extent"])
    distance = max(extent.x, extent.y, extent.z) * 2.25
    camera_data = bpy.data.cameras.new("runtime_assembly_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(extent.z * 1.12, extent.x * 1.18)
    camera = bpy.data.objects.new("runtime_assembly_camera", camera_data)
    camera["runtimeAssemblyRenderSupport"] = True
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    for name, location, energy, size in (
        ("runtime_assembly_key", (-2.6, -3.4, maximum.z + 1.2), 1050, 2.2),
        ("runtime_assembly_fill", (2.8, -1.5, center.z + 0.4), 700, 2.6),
        ("runtime_assembly_rim", (0.6, 3.2, maximum.z + 0.8), 900, 2.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        light["runtimeAssemblyRenderSupport"] = True
        light.location = location
        bpy.context.scene.collection.objects.link(light)
        aim(light, center)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("runtime_assembly_world")
    scene.world.color = (0.025, 0.03, 0.04)
    views = {
        "front": Vector((center.x, minimum.y - distance, center.z)),
        "side": Vector((maximum.x + distance, center.y, center.z)),
        "back": Vector((center.x, maximum.y + distance, center.z)),
        "isometric": Vector((maximum.x + distance * 0.72, minimum.y - distance * 0.72, center.z + extent.z * 0.10)),
    }
    evidence = []
    for name, position in views.items():
        camera.location = position
        aim(camera, center)
        output = output_dir / f"{name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        evidence.append({"view": name, "path": str(output), "sha256": sha256(output)})
    return evidence


def reset_bind_pose(rig: bpy.types.Object) -> None:
    rig.animation_data_create()
    rig.animation_data.action = None
    for pose_bone in rig.pose.bones:
        pose_bone.matrix_basis = Matrix.Identity(4)
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()


def post_import_audit(output: Path, review_dir: Path, expected_bones: list[str]) -> dict:
    clear_scene()
    imported = import_glb(output)
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Combined GLB must import one armature; found {len(armatures)}")
    rig = armatures[0]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    module_meshes = [obj for obj in meshes if str(obj.get("assetId", "")).startswith("arm.")]
    body_meshes = [obj for obj in meshes if str(obj.get("assetId", "")).startswith("body_")]
    weapon_meshes = [obj for obj in meshes if str(obj.get("assetId", "")).startswith("wep.")]
    actual_bones = sorted(bone.name for bone in rig.data.bones)
    clips = sorted(action.name for action in bpy.data.actions)
    bind_checks = {
        "singleArmature": len(armatures) == 1,
        "canonicalBones": actual_bones == sorted(expected_bones),
        "nineModules": len(module_meshes) == 9,
        "fourBodyMeshes": len(body_meshes) == 4,
        "weaponPresent": len(weapon_meshes) == 1,
        "animationFree": clips == sorted(REQUIRED_CLIPS),
        "allModulesBoundToBodyRig": all(
            armature_modifier(mesh).object == rig for mesh in module_meshes
        ),
    }
    reset_bind_pose(rig)
    bind_snapshot = bounds_snapshot(meshes)
    bind_evidence = render_views(meshes, review_dir / "bind")
    document = glb_document(output)
    json_checks = {
        "singleSkin": len(document.get("skins", [])) == 1,
        "noEmbeddedAnimations": sorted(animation.get("name", "") for animation in document.get("animations", []))
        == sorted(REQUIRED_CLIPS),
    }
    passed = all(bind_checks.values()) and all(json_checks.values())
    return {
        "importedObjectCount": len(imported),
        "meshCount": len(meshes),
        "bodyMeshCount": len(body_meshes),
        "moduleMeshCount": len(module_meshes),
        "weaponMeshCount": len(weapon_meshes),
        "boneCount": len(actual_bones),
        "animationClips": clips,
        "checks": bind_checks,
        "glbJsonChecks": json_checks,
        "bindPose": {"bounds": bind_snapshot, "previews": bind_evidence},
        "passed": passed,
    }


def main() -> None:
    args = parse_args()
    body_glb = Path(args.body_glb).resolve()
    modules_dir = Path(args.modules_dir).resolve()
    hammer_glb = Path(args.hammer_glb).resolve()
    output = Path(args.output).resolve()
    review_dir = Path(args.review_dir).resolve()
    report_path = Path(args.report).resolve() if args.report else output.with_suffix(".qc.json")
    clear_scene()
    body_import = import_glb(body_glb)
    body_rigs = [obj for obj in body_import if obj.type == "ARMATURE"]
    body_meshes = [
        obj
        for obj in body_import
        if obj.type == "MESH" and str(obj.get("assetId", "")).startswith("body_")
    ]
    sockets = [obj for obj in body_import if obj.type == "EMPTY" and obj.name.startswith("socket_")]
    if len(body_rigs) != 1 or len(body_meshes) != 4:
        raise RuntimeError(
            f"Verified runtime body must import one armature and four body meshes; "
            f"found {len(body_rigs)} armature(s), {len(body_meshes)} mesh(es)"
        )
    body_rig = body_rigs[0]
    body_rig.name = RIG_NAME
    expected_bones = sorted(bone.name for bone in body_rig.data.bones)
    if sorted(action.name for action in bpy.data.actions) != sorted(REQUIRED_CLIPS):
        raise RuntimeError("Body must not contain embedded actions")
    delete_objects([obj for obj in body_import if obj not in [body_rig, *body_meshes, *sockets]])

    module_paths = sorted(modules_dir.glob("arm_civic_humanoid_v2_battle_prelate_v1_*_m.glb"))
    if len(module_paths) != 9:
        raise RuntimeError(f"Expected exactly nine module GLBs in {modules_dir}; found {len(module_paths)}")
    module_meshes = []
    module_audits = []
    for module_path in module_paths:
        mesh, audit = rebind_module(module_path, body_rig)
        module_meshes.append(mesh)
        module_audits.append(audit)
    slots = sorted(audit["slot"] for audit in module_audits)
    if slots != sorted(EXPECTED_SLOTS):
        raise RuntimeError(f"Module slots do not match the nine-slot contract: {slots}")
    if len([obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]) != 1:
        raise RuntimeError("Duplicate module armatures remain after rebind")

    socket = next((obj for obj in sockets if obj.name == "socket_hand_R"), None)
    if not socket:
        raise RuntimeError("Verified runtime body is missing socket_hand_R")
    hammer_objects, hammer_audit = attach_hammer(hammer_glb, socket)
    hammer_root = next(obj for obj in hammer_objects if obj.name.startswith("battle_prelate_hammer_root"))
    body_rig["assetId"] = "chr.civic_humanoid_v2.battle_prelate_m.runtime_assembled_review"
    body_rig["assetCategory"] = "characterReview"
    body_rig["lifecycleStatus"] = "draft"
    body_rig["reviewStatus"] = "pending"
    body_rig["promotionEligible"] = False
    export_objects = [body_rig, *body_meshes, *module_meshes, *sockets, *hammer_objects]
    export_combined(output, export_objects)
    pre_export_checks = {
        "singleArmature": len([obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]) == 1,
        "fourBodyMeshes": len(body_meshes) == 4,
        "nineModuleMeshes": len(module_meshes) == 9,
        "nineSlots": slots == sorted(EXPECTED_SLOTS),
        "allModulesRebound": all(armature_modifier(mesh).object == body_rig for mesh in module_meshes),
        "animationFree": sorted(action.name for action in bpy.data.actions) == sorted(REQUIRED_CLIPS),
    }
    roundtrip = post_import_audit(output, review_dir, expected_bones)
    report = {
        "schemaVersion": 1,
        "assetId": "chr.civic_humanoid_v2.battle_prelate_m.runtime_assembled_review",
        "model": str(output),
        "modelSha256": sha256(output),
        "fileSizeBytes": output.stat().st_size,
        "lifecycleStatus": "draft",
        "reviewStatus": "pending_human_visual_review",
        "promotionEligible": False,
        "sources": {
            "body": {"path": str(body_glb), "sha256": sha256(body_glb)},
            "modules": module_audits,
            "hammer": hammer_audit,
        },
        "preExportChecks": pre_export_checks,
        "roundTrip": roundtrip,
        "technicalRoundTripPassed": all(pre_export_checks.values()) and roundtrip["passed"],
        "visualApprovalPassed": False,
        "blockingReasons": [
            "human_bind_visual_approval_missing",
            "stress_pose_review_missing",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("[runtime-equipped-assembly] " + json.dumps({
        "output": str(output),
        "report": str(report_path),
        "moduleCount": len(module_meshes),
        "boneCount": len(expected_bones),
        "clipCount": len(REQUIRED_CLIPS),
        "technicalRoundTripPassed": report["technicalRoundTripPassed"],
    }))
    if not report["technicalRoundTripPassed"]:
        raise RuntimeError(f"Runtime equipped assembly audit failed; see {report_path}")


if __name__ == "__main__":
    main()
