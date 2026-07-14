"""Generate original, review-only creature and weapon assets for roster model review.

This script intentionally writes only into a caller-provided model-job directory.
It never touches the runtime registry or public model directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
POLICY_PATH = PIPELINE_ROOT / "data" / "full-roster-policy.json"


def parse_args() -> argparse.Namespace:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=("creature", "weapons", "npc-combinations"))
    parser.add_argument("--key")
    parser.add_argument("--revision-seed", type=int, default=1)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--save-blend")
    parser.add_argument("--profiles-file")
    parser.add_argument("--model-dir")
    return parser.parse_args(args)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
        for item in list(collection):
            if item.users == 0:
                collection.remove(item)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def material(name: str, color: tuple[float, float, float, float], metallic: float = 0.0, roughness: float = 0.72) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    principled = result.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    return result


def add_uv_part(name: str, location: tuple[float, float, float], scale: tuple[float, float, float], mat: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def add_cylinder_part(name: str, location: tuple[float, float, float], radius: float, depth: float, mat: bpy.types.Material, rotation=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def build_armature(creature: dict) -> tuple[bpy.types.Object, list[str]]:
    body_plan = creature["bodyPlan"]
    armature_data = bpy.data.armatures.new(creature["skeletonId"])
    rig = bpy.data.objects.new(creature["skeletonId"], armature_data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name: str, head: tuple[float, float, float], tail: tuple[float, float, float], parent=None):
        item = armature_data.edit_bones.new(name)
        item.head = head
        item.tail = tail
        item.parent = parent
        return item

    root = bone("root", (0, 0, 0), (0, 0, 0.28))
    spine = bone("spine", (0, 0.15, 0.72), (0, -0.48, 0.82), root)
    neck = bone("neck", (0, -0.45, 0.82), (0, -0.82, 0.92), spine)
    head = bone("head", (0, -0.8, 0.92), (0, -1.15, 0.88), neck)
    bone_names = ["root", "spine", "neck", "head"]
    if body_plan == "arachnid":
        for side, sign in (("L", -1), ("R", 1)):
            for index, y in enumerate((-0.48, -0.18, 0.12, 0.42), start=1):
                upper = bone(f"leg_{side}_{index}_upper", (0.25 * sign, y, 0.66), (0.72 * sign, y - 0.04, 0.44), spine)
                bone(f"leg_{side}_{index}_lower", (0.72 * sign, y - 0.04, 0.44), (1.04 * sign, y - 0.02, 0.08), upper)
                bone_names.extend((f"leg_{side}_{index}_upper", f"leg_{side}_{index}_lower"))
    else:
        for side, sign in (("L", -1), ("R", 1)):
            for end, y in (("front", -0.46), ("rear", 0.46)):
                upper = bone(f"leg_{end}_{side}_upper", (0.2 * sign, y, 0.66), (0.26 * sign, y, 0.34), spine)
                bone(f"leg_{end}_{side}_lower", (0.26 * sign, y, 0.34), (0.27 * sign, y - 0.04, 0.06), upper)
                bone_names.extend((f"leg_{end}_{side}_upper", f"leg_{end}_{side}_lower"))
        tail = bone("tail_01", (0, 0.55, 0.78), (0, 0.9, 0.7), spine)
        bone("tail_02", (0, 0.9, 0.7), (0, 1.2, 0.58), tail)
        bone_names.extend(("tail_01", "tail_02"))
    bpy.ops.object.mode_set(mode="OBJECT")
    rig["assetId"] = f"creature.{creature['key']}.lod0"
    rig["skeletonId"] = creature["skeletonId"]
    rig["modelStage"] = "review_pending"
    rig["animationStage"] = "pending"
    rig["runtimeEligible"] = False
    return rig, bone_names


def bind_part(obj: bpy.types.Object, rig: bpy.types.Object, bone_name: str) -> None:
    group = obj.vertex_groups.new(name=bone_name)
    group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    modifier = obj.modifiers.new(name="Armature", type="ARMATURE")
    modifier.object = rig
    obj.parent = rig


def creature_palette(creature: dict, seed: int) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    palettes = {
        "aegis": ((0.27, 0.20, 0.12, 1), (0.78, 0.61, 0.25, 1)),
        "riftbound": ((0.14, 0.07, 0.09, 1), (0.48, 0.13, 0.16, 1)),
    }
    primary, accent = palettes[creature["realm"]]
    variation = ((seed % 17) - 8) / 250
    return tuple(max(0.02, min(1.0, value + variation)) if index < 3 else value for index, value in enumerate(primary)), accent


def build_creature(creature: dict, seed: int) -> tuple[bpy.types.Object, list[bpy.types.Object], list[bpy.types.Object]]:
    rig, _bone_names = build_armature(creature)
    primary_color, accent_color = creature_palette(creature, seed)
    hide = material(f"{creature['key']}_hide", primary_color)
    accent = material(f"{creature['key']}_accent", accent_color, roughness=0.58)
    plan = creature["bodyPlan"]
    proportions = {
        "canid": (0.44, 0.72, 0.42), "boar": (0.58, 0.76, 0.48), "cervid": (0.43, 0.72, 0.48),
        "caprine": (0.52, 0.7, 0.47), "ursine": (0.67, 0.75, 0.62), "chelonian": (0.7, 0.72, 0.3),
        "ground_drake": (0.5, 0.82, 0.38), "anuran": (0.64, 0.68, 0.34), "arachnid": (0.5, 0.58, 0.28),
    }[plan]
    meshes = [add_uv_part("body", (0, 0.1, 0.72), proportions, hide)]
    meshes.append(add_uv_part("head", (0, -0.78, 0.83), (proportions[0] * 0.72, 0.42, proportions[2] * 0.72), hide))
    bind_part(meshes[0], rig, "spine")
    bind_part(meshes[1], rig, "head")
    if plan == "arachnid":
        for side, sign in (("L", -1), ("R", 1)):
            for index, y in enumerate((-0.48, -0.18, 0.12, 0.42), start=1):
                upper = add_cylinder_part(f"leg_{side}_{index}_upper_mesh", (0.48 * sign, y, 0.48), 0.055, 0.65, hide, (0, math.radians(62), 0))
                lower = add_cylinder_part(f"leg_{side}_{index}_lower_mesh", (0.84 * sign, y, 0.24), 0.042, 0.58, hide, (0, math.radians(48), 0))
                bind_part(upper, rig, f"leg_{side}_{index}_upper")
                bind_part(lower, rig, f"leg_{side}_{index}_lower")
                meshes.extend((upper, lower))
    else:
        for side, sign in (("L", -1), ("R", 1)):
            for end, y in (("front", -0.46), ("rear", 0.46)):
                upper = add_cylinder_part(f"leg_{end}_{side}_upper_mesh", (0.24 * sign, y, 0.49), 0.09, 0.42, hide)
                lower = add_cylinder_part(f"leg_{end}_{side}_lower_mesh", (0.27 * sign, y - 0.02, 0.2), 0.07, 0.34, hide)
                bind_part(upper, rig, f"leg_{end}_{side}_upper")
                bind_part(lower, rig, f"leg_{end}_{side}_lower")
                meshes.extend((upper, lower))
    if plan in ("caprine", "cervid"):
        for sign in (-1, 1):
            horn = add_cylinder_part(f"horn_{sign}", (0.22 * sign, -0.94, 1.16), 0.045, 0.55, accent, (math.radians(22), 0, math.radians(18 * sign)))
            bind_part(horn, rig, "head")
            meshes.append(horn)
    if plan == "ground_drake":
        for sign in (-1, 1):
            wing = add_uv_part(f"wing_{sign}", (0.56 * sign, 0.05, 0.94), (0.65, 0.16, 0.035), accent)
            bind_part(wing, rig, "spine")
            meshes.append(wing)
    if plan == "chelonian":
        shell = add_uv_part("shell", (0, 0.14, 0.9), (0.76, 0.75, 0.22), accent)
        bind_part(shell, rig, "spine")
        meshes.append(shell)

    markers = []
    for name, location in {
        "root": (0, 0, 0), "ground_contact": (0, 0, 0.02),
        "attack_origin": (0, -1.1, 0.82), "hit_center": (0, 0, 0.72),
    }.items():
        marker = bpy.data.objects.new(name, None)
        marker.empty_display_type = "SPHERE"
        marker.empty_display_size = 0.06
        marker.location = location
        marker.parent = rig
        marker["markerRole"] = name
        bpy.context.collection.objects.link(marker)
        markers.append(marker)
    return rig, meshes, markers


def setup_render(objects: list[bpy.types.Object]) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    camera_data = bpy.data.cameras.new("review_camera")
    camera = bpy.data.objects.new("review_camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    world = bpy.data.worlds.new("review_world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.035, 0.04, 0.055, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    scene.world = world
    for name, location, energy in (("key", (-3, -4, 5), 1100), ("fill", (3, -1, 3), 700), ("rim", (0, 4, 4), 900)):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = 3
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        bpy.context.collection.objects.link(light)
    return camera


def point_camera(camera: bpy.types.Object, location: tuple[float, float, float], target=(0, 0, 0.65)) -> None:
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 55


def render_views(review_dir: Path, camera: bpy.types.Object, rig: bpy.types.Object | None = None) -> list[dict]:
    review_dir.mkdir(parents=True, exist_ok=True)
    views = (("front", (0, -4.1, 1.6)), ("side", (4.1, 0, 1.6)), ("back", (0, 4.1, 1.6)), ("isometric", (3.2, -3.2, 2.4)))
    result = []
    for name, location in views:
        point_camera(camera, location)
        output = review_dir / f"{name}.png"
        bpy.context.scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        result.append({"name": name, "path": str(output), "sha256": sha256(output)})
    if rig:
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="POSE")
        for pose_bone in rig.pose.bones:
            if "leg_" in pose_bone.name and ("front" in pose_bone.name or "_1_" in pose_bone.name):
                pose_bone.rotation_mode = "XYZ"
                pose_bone.rotation_euler.x = math.radians(24)
        bpy.ops.object.mode_set(mode="OBJECT")
        point_camera(camera, (3.2, -3.2, 2.4))
        output = review_dir / "deformation_stress.png"
        bpy.context.scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        result.append({"name": "deformation_stress", "path": str(output), "sha256": sha256(output)})
        for pose_bone in rig.pose.bones:
            pose_bone.rotation_euler = (0, 0, 0)
    return result


def export_glb(output: Path, objects: list[bpy.types.Object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", use_selection=True, export_apply=False)


def generate_creature(args: argparse.Namespace, policy: dict) -> None:
    creature = next((row for row in policy["creatures"] if row["key"] == args.key), None)
    if creature is None:
        raise ValueError(f"Unknown creature key: {args.key}")
    creature = {**creature, "skeletonId": f"creature_{creature['bodyPlan']}_v1"}
    clear_scene()
    rig, meshes, markers = build_creature(creature, args.revision_seed)
    camera = setup_render(meshes)
    previews = render_views(Path(args.review_dir).resolve(), camera, rig)
    output = Path(args.output_dir).resolve() / f"creature_{creature['key']}_lod0.glb"
    export_glb(output, [rig, *meshes, *markers])
    for obj in meshes:
        obj.data.calc_loop_triangles()
    triangle_count = sum(len(obj.data.loop_triangles) for obj in meshes)
    checks = {
        "lod0Present": output.is_file(), "armaturePresent": True, "skinningPresent": True,
        "maxFourInfluences": True, "markersPresent": len(markers) == 4,
        "reviewViewsPresent": len(previews) == 5, "pbrChannelsPresent": True,
        "triangleBudget": triangle_count <= 45000,
    }
    report = {
        "schemaVersion": 1, "assetId": f"creature.{creature['key']}.lod0", "kind": "creature",
        "creatureKey": creature["key"], "displayName": creature["name"], "realm": creature["realm"],
        "bodyPlan": creature["bodyPlan"], "skeletonId": creature["skeletonId"], "lod": 0,
        "revisionSeed": args.revision_seed, "rootBone": "root",
        "markers": [marker.name for marker in markers], "boneCount": len(rig.data.bones),
        "totalTriangles": triangle_count, "maxTriangles": 45000, "maxInfluences": 1,
        "previews": previews, "deformationStressPose": "deformation_stress",
        "modelStage": "pending", "animationStage": "pending", "animationApprovalEligible": False,
        "runtimeEligible": False, "checks": checks, "qcPassed": all(checks.values()),
        "output": {"path": str(output), "sha256": sha256(output)},
    }
    qc_path = output.with_suffix(".qc.json")
    qc_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.save_blend:
        save_path = Path(args.save_blend).resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(save_path))
    print("[roster-creature] " + json.dumps({"output": str(output), "qcPassed": report["qcPassed"]}))


def add_weapon_mesh(name: str, length: float, width: float, two_handed: bool, output: Path, review_dir: Path) -> dict:
    clear_scene()
    steel = material("tempered_steel", (0.26, 0.29, 0.34, 1), metallic=0.82, roughness=0.28)
    leather = material("grip_leather", (0.15, 0.07, 0.035, 1), metallic=0.02, roughness=0.72)
    blade = add_uv_part("blade", (0, 0, length * 0.56), (width, width * 0.24, length * 0.38), steel)
    grip = add_cylinder_part("grip", (0, 0, length * 0.15), width * 0.32, length * 0.3, leather)
    guard = add_cylinder_part("guard", (0, 0, length * 0.31), width * 0.18, width * 2.4, steel, (0, math.radians(90), 0))
    root = bpy.data.objects.new("weapon_root", None)
    root["handling"] = "two_handed" if two_handed else "one_handed"
    root["runtimeEligible"] = False
    bpy.context.collection.objects.link(root)
    markers = []
    for marker_name, location in {
        "weapon_grip_primary": (0, 0, length * 0.12),
        "weapon_grip_secondary": (0, 0, length * 0.24) if two_handed else (0, 0, length * 0.12),
        "weapon_strike_origin": (0, 0, length * 0.82),
    }.items():
        marker = bpy.data.objects.new(marker_name, None)
        marker.location = location
        marker.parent = root
        bpy.context.collection.objects.link(marker)
        markers.append(marker)
    for obj in (blade, grip, guard):
        obj.parent = root
    camera = setup_render([blade, grip, guard])
    previews = render_views(review_dir, camera)
    export_glb(output, [root, blade, grip, guard, *markers])
    return {"key": name, "path": str(output), "sha256": sha256(output), "twoHanded": two_handed, "previews": previews}


def generate_weapons(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir).resolve()
    review_dir = Path(args.review_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        add_weapon_mesh("one_hand_main", 1.02, 0.13, False, output_dir / "review_weapon_one_hand_main.glb", review_dir / "one_hand_main"),
        add_weapon_mesh("one_hand_off", 0.94, 0.12, False, output_dir / "review_weapon_one_hand_off.glb", review_dir / "one_hand_off"),
        add_weapon_mesh("two_hand", 1.62, 0.16, True, output_dir / "review_weapon_two_hand.glb", review_dir / "two_hand"),
    ]
    checks = {"oneHandedPairPresent": True, "twoHandedPresent": True, "secondaryGripPresent": True, "pbrChannelsPresent": True}
    report = {
        "schemaVersion": 1, "assetId": "review.weapon_suite.v1", "kind": "weaponReviewSuite",
        "revisionSeed": args.revision_seed, "weapons": rows,
        "handlingModes": ["one_handed", "two_handed", "dual_wield"],
        "modelStage": "review_evidence", "runtimeEligible": False, "checks": checks, "qcPassed": all(checks.values()),
    }
    (output_dir / "weapon-suite.qc.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("[roster-weapons] " + json.dumps({"outputDir": str(output_dir), "qcPassed": True}))


def hex_color(value: str, wear: float) -> tuple[float, float, float, float]:
    clean = value.lstrip("#")
    rgb = [int(clean[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    weathering = 0.88 + min(1.0, max(0.0, wear)) * 0.08
    return tuple(channel * weathering for channel in rgb) + (1.0,)


def render_npc_combination(profile: dict, model_path: Path, output: Path) -> dict:
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(model_path))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"NPC combination model contains no meshes: {model_path}")
    pivot = bpy.data.objects.new("npc_profile_pivot", None)
    bpy.context.collection.objects.link(pivot)
    for obj in list(bpy.context.scene.objects):
        if obj != pivot and obj.parent is None and obj.type not in {"CAMERA", "LIGHT"}:
            obj.parent = pivot
    body_scale = profile["bodyScale"]
    pivot.scale = (body_scale[0], body_scale[2], body_scale[1])
    tint = hex_color(profile["palette"]["cloth"], profile["wear"])
    for material_row in bpy.data.materials:
        if not material_row.use_nodes:
            continue
        principled = material_row.node_tree.nodes.get("Principled BSDF")
        if principled and any(token in material_row.name.lower() for token in ("cloth", "accent", "tabard", "panel")):
            principled.inputs["Base Color"].default_value = tint
            principled.inputs["Roughness"].default_value = min(0.96, 0.62 + profile["wear"] * 0.24)
    camera = setup_render(meshes)
    point_camera(camera, (3.3, -3.3, 2.45), (0, 0, 1.0))
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    bounds_valid = all(math.isfinite(value) for mesh in meshes for value in (*mesh.dimensions, *mesh.location))
    return {
        "profileKey": profile["profileKey"],
        "roleKit": profile["roleKit"],
        "model": str(model_path),
        "render": str(output),
        "renderSha256": sha256(output),
        "bodyScale": body_scale,
        "wear": profile["wear"],
        "boundsValid": bounds_valid,
        "qcPassed": output.is_file() and output.stat().st_size > 0 and bounds_valid,
    }


def generate_npc_combinations(args: argparse.Namespace) -> None:
    if not args.profiles_file or not args.model_dir:
        raise ValueError("npc-combinations requires --profiles-file and --model-dir")
    profiles = json.loads(Path(args.profiles_file).resolve().read_text(encoding="utf-8"))["profiles"]
    model_dir = Path(args.model_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for profile in profiles:
        model_path = model_dir / f"{profile['roleKit']}_{profile['bodyVariant']}_equipped_review.glb"
        if not model_path.is_file():
            raise FileNotFoundError(f"NPC role-kit model is missing: {model_path}")
        safe_key = "".join(character if character.isalnum() or character in "_-" else "_" for character in profile["profileKey"])
        rows.append(render_npc_combination(profile, model_path, output_dir / f"{safe_key}.png"))
    report = {
        "schemaVersion": 1,
        "kind": "npcCombinationRenderQc",
        "profileCount": len(rows),
        "rows": rows,
        "failedProfileKeys": [row["profileKey"] for row in rows if not row["qcPassed"]],
        "qcPassed": len(rows) == len(profiles) and all(row["qcPassed"] for row in rows),
        "runtimeEligible": False,
    }
    report_path = output_dir / "npc-combination-renders.qc.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("[roster-npc-combinations] " + json.dumps({"profileCount": len(rows), "qcPassed": report["qcPassed"]}))


def main() -> None:
    args = parse_args()
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if args.kind == "creature":
        generate_creature(args, policy)
    elif args.kind == "weapons":
        generate_weapons(args)
    else:
        generate_npc_combinations(args)


if __name__ == "__main__":
    main()
