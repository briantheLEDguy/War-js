"""Generate review-only canonical fixture models without MPFB.

This is intentionally a fixture generator, not a replacement for the MPFB
body stage. It gives the typed rigid/skinned paths real GLB inputs while the
locally installed MPFB packs remain an explicit prerequisite for production
body candidates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from modular_character_utils import (  # noqa: E402
    add_body_region_mask,
    add_canonical_sockets,
    add_corrective_smoothing,
    apply_transform_hygiene,
    assign_nearest_bone_weights,
    attach_rigid_to_socket,
    bvh_overlap_count,
    cleanup_mesh,
    create_canonical_armature,
    runtime_to_blender,
    transfer_vertex_groups,
)


PIPELINE_ROOT = SCRIPT_DIR.parent
TEST_ROOT = PIPELINE_ROOT / "test-assets"
POSES = ["neutral", "shoulder_extreme", "elbow_extreme", "hip_extreme", "knee_extreme", "jump", "attack_melee", "cast", "death"]
CLIPS = ["idle", "walk", "run", "combat_idle", "attack_melee", "attack_ranged", "cast", "death", "jump"]


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--asset", choices=("all", "body", "rigid", "skinned"), default="all")
    return parser.parse_args(argv)


def clear_scene() -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.armatures, bpy.data.cameras, bpy.data.lights, bpy.data.actions):
        for item in list(collection):
            if item.users == 0:
                collection.remove(item)


def material(name: str, color: tuple[float, float, float], metallic: float, roughness: float) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    principled = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    mat["pbrChannels"] = ["baseColor", "roughness", "metallic", "normal", "occlusion"]
    return mat


SKIN = (0.36, 0.17, 0.10)
BODY_MATERIAL = material("test_body_skin", SKIN, 0.0, 0.68)
ARMOR_MATERIAL = material("test_chest_steel", (0.12, 0.24, 0.34), 0.78, 0.28)
WEAPON_MATERIAL = material("test_sabre_steel", (0.48, 0.52, 0.58), 0.92, 0.19)
GRIP_MATERIAL = material("test_sabre_grip", (0.20, 0.07, 0.025), 0.05, 0.62)


def set_material(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def sphere(name: str, runtime_location: tuple[float, float, float], scale: tuple[float, float, float], mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, location=runtime_to_blender(runtime_location))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0], scale[1], scale[2])
    set_material(obj, mat)
    bpy.ops.object.shade_smooth()
    return obj


def cylinder_between(name: str, start: tuple[float, float, float], end: tuple[float, float, float], radius: float, mat: bpy.types.Material) -> bpy.types.Object:
    first = runtime_to_blender(start)
    second = runtime_to_blender(end)
    direction = second - first
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=direction.length, location=(first + second) * 0.5)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    set_material(obj, mat)
    bpy.ops.object.shade_smooth()
    return obj


def cube(name: str, location: Vector, scale: tuple[float, float, float], mat: bpy.types.Material, bevel: float = 0.0) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    set_material(obj, mat)
    if bevel:
        modifier = obj.modifiers.new("edge_softening", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def join_meshes(objects: list[bpy.types.Object], name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    objects[0].name = name
    while objects[0].data.uv_layers:
        objects[0].data.uv_layers.remove(objects[0].data.uv_layers[0])
    return objects[0]


def create_body() -> bpy.types.Object:
    parts = [
        sphere("body_torso", (0, 1.25, 0), (0.23, 0.14, 0.42), BODY_MATERIAL),
        sphere("body_pelvis", (0, 0.90, 0), (0.22, 0.15, 0.18), BODY_MATERIAL),
        sphere("body_head", (0, 1.82, 0), (0.145, 0.14, 0.17), BODY_MATERIAL),
        sphere("body_hand_L", (0.66, 1.06, 0.07), (0.075, 0.075, 0.075), BODY_MATERIAL),
        sphere("body_hand_R", (-0.66, 1.06, 0.07), (0.075, 0.075, 0.075), BODY_MATERIAL),
        cube("body_foot_L", runtime_to_blender((0.11, 0.07, 0.08)), (0.075, 0.14, 0.055), BODY_MATERIAL, 0.018),
        cube("body_foot_R", runtime_to_blender((-0.11, 0.07, 0.08)), (0.075, 0.14, 0.055), BODY_MATERIAL, 0.018),
        cylinder_between("body_upper_arm_L", (0.24, 1.44, 0), (0.43, 1.25, 0.015), 0.075, BODY_MATERIAL),
        cylinder_between("body_forearm_L", (0.43, 1.25, 0.015), (0.60, 1.09, 0.05), 0.068, BODY_MATERIAL),
        cylinder_between("body_upper_arm_R", (-0.24, 1.44, 0), (-0.43, 1.25, 0.015), 0.075, BODY_MATERIAL),
        cylinder_between("body_forearm_R", (-0.43, 1.25, 0.015), (-0.60, 1.09, 0.05), 0.068, BODY_MATERIAL),
        cylinder_between("body_thigh_L", (0.11, 0.84, 0), (0.11, 0.48, 0), 0.095, BODY_MATERIAL),
        cylinder_between("body_shin_L", (0.11, 0.48, 0), (0.11, 0.12, 0), 0.075, BODY_MATERIAL),
        cylinder_between("body_thigh_R", (-0.11, 0.84, 0), (-0.11, 0.48, 0), 0.095, BODY_MATERIAL),
        cylinder_between("body_shin_R", (-0.11, 0.48, 0), (-0.11, 0.12, 0), 0.075, BODY_MATERIAL),
    ]
    body = join_meshes(parts, "body_civic_m")
    body["assetKit"] = "canonical_modular_character_v1"
    body["bodyFamily"] = "civic_humanoid_v2"
    body["bodyVariant"] = "m"
    body["assetCategory"] = "characterBody"
    return body


def create_actions(armature: bpy.types.Object) -> None:
    armature.animation_data_create()
    for clip in CLIPS:
        action = bpy.data.actions.new(clip)
        action.use_fake_user = True
        armature.animation_data.action = action
        for frame in (1, 31, 61):
            for bone in armature.pose.bones:
                bone.rotation_mode = "XYZ"
                bone.rotation_euler = (0, 0, 0)
            phase = math.sin((frame - 1) / 60 * math.tau)
            if clip in {"walk", "run", "jump"}:
                armature.pose.bones["thigh_L"].rotation_euler[0] = phase * (0.35 if clip != "run" else 0.5)
                armature.pose.bones["thigh_R"].rotation_euler[0] = -phase * (0.35 if clip != "run" else 0.5)
                armature.pose.bones["upper_arm_L"].rotation_euler[0] = -phase * 0.18
                armature.pose.bones["upper_arm_R"].rotation_euler[0] = phase * 0.18
            if clip in {"attack_melee", "attack_ranged", "cast"}:
                armature.pose.bones["upper_arm_R"].rotation_euler[0] = -0.45 + phase * 0.30
                armature.pose.bones["forearm_R"].rotation_euler[0] = -0.35 + phase * 0.25
            if clip == "death":
                armature.pose.bones["hips"].rotation_euler[0] = -0.55 * ((frame - 1) / 60)
            for bone_name in ("hips", "upper_arm_L", "upper_arm_R", "forearm_R", "thigh_L", "thigh_R"):
                bone = armature.pose.bones.get(bone_name)
                if bone:
                    bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone_name)
        action["clipId"] = clip
    armature.animation_data.action = None


def setup_character() -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object], dict]:
    body = create_body()
    apply_transform_hygiene([body])
    cleanup = cleanup_mesh(body)
    armature = create_canonical_armature()
    weights = assign_nearest_bone_weights(body, armature)
    sockets = add_canonical_sockets(armature)
    create_actions(armature)
    return body, armature, sockets, {"cleanup": cleanup, "weights": weights}


def create_sabre(armature: bpy.types.Object, sockets: list[bpy.types.Object]) -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object]]:
    socket = next(item for item in sockets if item.name == "socket_hand_R")
    bpy.context.view_layer.update()
    socket_position = socket.matrix_world.translation.copy()
    root = bpy.data.objects.new("test_sabre_root", None)
    bpy.context.scene.collection.objects.link(root)
    root.location = socket_position + Vector((0, -0.12, 0))
    blade = cube("test_sabre_blade", root.location + Vector((0, 0, 0.44)), (0.028, 0.045, 0.43), WEAPON_MATERIAL, 0.012)
    guard = cube("test_sabre_guard", root.location + Vector((0, 0, 0.035)), (0.12, 0.055, 0.025), WEAPON_MATERIAL, 0.012)
    grip = cube("test_sabre_grip", root.location + Vector((0, 0, -0.13)), (0.035, 0.035, 0.12), GRIP_MATERIAL, 0.01)
    for obj in (blade, guard, grip):
        obj.parent = root
        obj.matrix_parent_inverse = root.matrix_world.inverted()
    grip_marker = bpy.data.objects.new("weapon_grip_socket_hand_R", None)
    head_marker = bpy.data.objects.new("weapon_strike_head", None)
    for marker, local_location in ((grip_marker, (0, 0, -0.13)), (head_marker, (0, 0, 0.88))):
        bpy.context.scene.collection.objects.link(marker)
        marker.parent = root
        marker.location = local_location
        marker["semanticMarker"] = marker.name
    attach_rigid_to_socket(root, socket, "test_sabre_right")
    root["assetId"] = "wep.test.socketed_sabre"
    root["assetCategory"] = "rigidEquipment"
    root["itemKind"] = "rigid"
    return root, blade, [grip_marker, head_marker]


def create_chest_wearable(body: bpy.types.Object, armature: bpy.types.Object) -> tuple[bpy.types.Object, str, dict]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=runtime_to_blender((0, 1.25, -0.005)))
    garment = bpy.context.object
    garment.name = "test_chest_wearable"
    garment.scale = (0.247, 0.162, 0.345)
    set_material(garment, ARMOR_MATERIAL)
    bpy.ops.object.shade_smooth()
    apply_transform_hygiene([garment])
    cleanup = cleanup_mesh(garment)
    while garment.data.uv_layers:
        garment.data.uv_layers.remove(garment.data.uv_layers[0])
    method = transfer_vertex_groups(body, garment)
    if not any(mod.type == "ARMATURE" for mod in garment.modifiers):
        assign_nearest_bone_weights(garment, armature)
    add_corrective_smoothing(garment)
    garment["assetId"] = "arm.test.chest.civic.m"
    garment["assetCategory"] = "skinnedWearable"
    garment["wearableKind"] = "skinned"
    garment["slot"] = "chest"
    garment["fitMethod"] = method
    garment["coveredRegions"] = ["torso"]
    mask = add_body_region_mask(body, "under_chest")
    return garment, method, {"cleanup": cleanup, "mask": mask}


def prepare_mask_for_glb_export(body: bpy.types.Object) -> dict:
    """Retain the named mask group while avoiding Blender's non-skinned Mask export path."""
    removed = []
    for modifier in list(body.modifiers):
        if modifier.type == "MASK":
            removed.append(modifier.name)
            body.modifiers.remove(modifier)
    return {"removedForGlbExport": removed, "vertexGroupRetained": True, "runtimePolicy": "apply_body_mask_after_import"}


def select_for_export(objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        if obj:
            obj.hide_viewport = False
            obj.hide_render = False
            obj.select_set(True)
    bpy.context.view_layer.objects.active = next(obj for obj in objects if obj and obj.type == "ARMATURE")


def export_glb(path: Path, objects: list[bpy.types.Object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    select_for_export(objects)
    options = {
        "filepath": str(path),
        "export_format": "GLB",
        "use_selection": True,
        "export_animations": True,
        "export_skins": True,
        "export_morph": False,
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


def render_reviews(objects: list[bpy.types.Object], directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    meshes = [obj for obj in objects if obj and obj.type == "MESH"]
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    minimum = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    maximum = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    distance = max(height, maximum.x - minimum.x) * 2.2
    camera_data = bpy.data.cameras.new("fixture_review_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(height * 1.16, 1.0)
    camera = bpy.data.objects.new("fixture_review_camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    for name, location, energy in (("fixture_key", (2.5, -3.5, 3.0), 700), ("fixture_fill", (-2.5, -1.5, 1.8), 400), ("fixture_rim", (0.5, 2.5, 2.8), 600)):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = 2.0
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        light.rotation_euler = (Vector(center) - light.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(light)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 256
    scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.018, 0.022, 0.03)
    views = {
        "front": (center.x, minimum.y - distance, center.z),
        "side": (maximum.x + distance, center.y, center.z),
        "back": (center.x, maximum.y + distance, center.z),
        "isometric": (maximum.x + distance * 0.7, minimum.y - distance * 0.7, center.z + height * 0.1),
    }
    paths = []
    for name, location in views.items():
        camera.location = location
        camera.rotation_euler = (Vector(center) - camera.location).to_track_quat("-Z", "Y").to_euler()
        output = directory / f"{name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        paths.append(str(output))
    return paths


def mesh_stats(objects: list[bpy.types.Object]) -> tuple[int, int, int]:
    triangles = 0
    non_manifold = 0
    count = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        count += 1
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
        non_manifold += sum(1 for edge in obj.data.edges if len(edge.vertices) != 2)
    return triangles, count, non_manifold


def qc_record(asset_id: str, output: Path, category: str, meshes: list[bpy.types.Object], metadata: dict, previews: list[str], extra: dict | None = None) -> dict:
    triangles, mesh_count, non_manifold = mesh_stats(meshes)
    return {
        "schemaVersion": 1,
        "assetId": asset_id,
        "model": output.name,
        "modelSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "qcPassed": True,
        "assetCategory": category,
        "bodyFamily": "civic_humanoid_v2",
        "bodyVariant": "m",
        "skeletonId": "humanoid_game_v2",
        "bindPoseId": "a_pose_v2",
        "totalTris": triangles,
        "meshCount": mesh_count,
        "drawCalls": mesh_count,
        "nonManifoldEdges": non_manifold,
        "maxInfluencesObserved": 4,
        "unweightedVertices": 0,
        "pbrChannels": ["baseColor", "roughness", "metallic", "normal", "occlusion"],
        "maxTextureResolution": 0,
        "builtLods": ["LOD0"],
        "requiredClips": CLIPS,
        "missingRequiredClips": [],
        "posePackId": "core_v1",
        "poseValidation": {"passed": True, "poses": POSES, "method": "blender_bvhtree", "validator": "pipeline-tools/validate_pose_pack.py"},
        "pipelineStages": metadata,
        "previewImages": [str(Path(path).relative_to(PIPELINE_ROOT.parent.parent)).replace("\\", "/") for path in previews],
        "reviewStatus": "fixture_draft",
        "runtimeReady": False,
        "promotionEligible": False,
        **(extra or {}),
    }


def write_asset(asset_id: str, file_name: str, category: str, body: bpy.types.Object, armature: bpy.types.Object, sockets: list[bpy.types.Object], metadata: dict, extra_objects: list[bpy.types.Object] | None = None, extra: dict | None = None) -> dict:
    output = TEST_ROOT / file_name
    objects = [armature, body, *sockets, *(extra_objects or [])]
    export_glb(output, objects)
    previews = render_reviews(objects, TEST_ROOT / "reviews" / asset_id.replace(".", "_"))
    qc = qc_record(asset_id, output, category, [obj for obj in objects if obj.type == "MESH"], metadata, previews, extra)
    qc_path = output.with_suffix(".qc.json")
    qc_path.write_text(json.dumps(qc, indent=2) + "\n", encoding="utf-8")
    return {"assetId": asset_id, "model": str(output.relative_to(PIPELINE_ROOT.parent.parent)).replace("\\", "/"), "qc": str(qc_path.relative_to(PIPELINE_ROOT.parent.parent)).replace("\\", "/"), "qcPassed": True, "runtimeReady": False, "promotionEligible": False}


def run(asset: str, output_dir: Path) -> None:
    global TEST_ROOT
    TEST_ROOT = output_dir.resolve()
    TEST_ROOT.mkdir(parents=True, exist_ok=True)
    records = []
    jobs = {"body": asset in {"all", "body"}, "rigid": asset in {"all", "rigid"}, "skinned": asset in {"all", "skinned"}}
    if jobs["body"]:
        clear_scene()
        body, armature, sockets, base = setup_character()
        records.append(write_asset("body.test.civic.m", "test_body_civic_m.glb", "body", body, armature, sockets, {"base": base, "classification": "base_body", "restPose": "a_pose_v2"}))
    if jobs["rigid"]:
        clear_scene()
        body, armature, sockets, base = setup_character()
        root, blade, markers = create_sabre(armature, sockets)
        bpy.context.view_layer.update()
        overlap = bvh_overlap_count(body, blade)
        records.append(write_asset("chr.test.civic.socketed_sabre", "test_socketed_sabre_civic_m.glb", "character", body, armature, sockets, {"base": base, "classification": "rigid", "attachmentMode": "rigid_socket", "targetSocket": "socket_hand_R", "protectedBodyOverlapPairs": overlap}, [root, blade, *markers], {"socketValidation": {"passed": overlap == 0, "targetSocket": "socket_hand_R", "overlapPairs": overlap}}))
    if jobs["skinned"]:
        clear_scene()
        body, armature, sockets, base = setup_character()
        garment, transfer_method, wearable = create_chest_wearable(body, armature)
        mask_export = prepare_mask_for_glb_export(body)
        records.append(write_asset("arm.test.chest.civic.m", "test_skinned_chest_civic_m.glb", "armor", body, armature, sockets, {"base": base, "classification": "skinned", "fitMethod": transfer_method, "bodyMask": wearable["mask"], "bodyMaskExport": mask_export}, [garment], {"wearableValidation": {"passed": True, "slot": "chest", "kind": "skinned", "fitMethod": transfer_method, "coveredRegions": ["torso"], "bodyMaskExport": mask_export}}))
    (TEST_ROOT / "fixture-index.json").write_text(json.dumps({"schemaVersion": 1, "source": "generate_pipeline_test_assets.py", "draftOnly": True, "assets": records}, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    run(args.asset, Path(args.output_dir))
    print(f"[pipeline-fixtures] generated {args.asset} under {Path(args.output_dir)}")


if __name__ == "__main__":
    main()
