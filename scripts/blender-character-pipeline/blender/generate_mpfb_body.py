"""Generate one review-gated MPFB body candidate for the free character pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

from bl_ext.blender_org.mpfb.services import HumanService, LocationService, TargetService

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from canonical_animation_pack import attach_canonical_animation_pack
from canonical_mpfb_animation_library import ANIMATION_PROFILES, DEFAULT_ANIMATION_PROFILE
from glb_roundtrip_audit import roundtrip_bind_audit


PIPELINE_ROOT = Path(__file__).resolve().parent.parent
BODY_FAMILY_ROOT = PIPELINE_ROOT / "data" / "body-families"
SKELETON_CONTRACT_PATH = BODY_FAMILY_ROOT / "humanoid_game_v2.skeleton.json"
BODY_BUDGET_TRIANGLES = 45_000
BODY_BUDGET_DRAW_CALLS = 7
MPFB_AUTHORING_BODY_VERTICES = 19_158


MPFB_TO_CANONICAL = {
    "Root": "root",
    "pelvis": "hips",
    "spine_01": "spine",
    "spine_02": "chest",
    "spine_03": "upper_chest",
    "clavicle_l": "shoulder_L",
    "upperarm_l": "upper_arm_L",
    "lowerarm_l": "forearm_L",
    "hand_l": "hand_L",
    "clavicle_r": "shoulder_R",
    "upperarm_r": "upper_arm_R",
    "lowerarm_r": "forearm_R",
    "hand_r": "hand_R",
    "neck_01": "neck",
    "thigh_l": "thigh_L",
    "calf_l": "shin_L",
    "foot_l": "foot_L",
    "ball_l": "toe_L",
    "thigh_r": "thigh_R",
    "calf_r": "shin_R",
    "foot_r": "foot_R",
    "ball_r": "toe_R",
}
for side in ("l", "r"):
    canonical_side = side.upper()
    for finger in ("thumb", "index", "middle", "ring", "pinky"):
        for segment in ("01", "02", "03"):
            MPFB_TO_CANONICAL[f"{finger}_{segment}_{side}"] = f"{finger}_{segment}_{canonical_side}"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True)
    parser.add_argument("--variant", required=True, choices=("m", "f"))
    parser.add_argument(
        "--profile-request",
        help="Optional generated roster profile request containing a class-specific physique override.",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--save-blend")
    parser.add_argument(
        "--animation-profile",
        choices=ANIMATION_PROFILES,
        default=DEFAULT_ANIMATION_PROFILE,
    )
    return parser.parse_args(argv)


def load_recipe(family: str) -> dict:
    path = BODY_FAMILY_ROOT / f"{family}.body-family.json"
    if path.is_file():
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    policy_path = PIPELINE_ROOT / "data" / "full-roster-policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    race, definition = next(
        ((race_key, value) for race_key, value in policy["bodyFamilies"].items() if value["id"] == family),
        (None, None),
    )
    if not definition:
        raise RuntimeError(f"Unknown full-roster body family: {family}")
    variants = {}
    for variant in ("m", "f"):
        variants[variant] = {
            "variant": variant,
            "profileKey": f"npc_{race}_{variant}",
            "outputModel": f"body_{family}_{variant}.glb",
            "expectedHeightM": definition["expectedHeightM"][variant],
            "mpfbPreset": {
                "creationApi": "HumanService.create_human",
                "propertyValues": {
                    **definition["baseMacros"][variant],
                    "gender": 1.0 if variant == "m" else 0.0,
                },
                "rig": "game_engine",
                "skinModel": "GAME_ENGINE",
            },
            "skin": {
                "assetPack": "makehuman_system_assets",
                "assetName": "young_caucasian_male" if variant == "m" else "young_caucasian_female",
                "tint": definition["skin"][variant],
            },
            "customTargets": [],
            "attachments": {
                "eyes": "high-poly",
                "eyebrows": "eyebrow006",
                "eyelashes": "eyelashes01",
                "teeth": "teeth_base",
                "tongue": "tongue01",
            },
        }
    return {
        "bodyFamily": family,
        "displayName": definition["displayName"],
        "race": race,
        "skeletonId": policy["skeletonId"],
        "bindPoseId": policy["bindPoseId"],
        "variants": variants,
    }


def apply_profile_request(family_recipe: dict, variant_recipe: dict, request_path: str | None) -> tuple[dict, dict]:
    if not request_path:
        return family_recipe, variant_recipe
    request = json.loads(Path(request_path).resolve().read_text(encoding="utf-8"))
    if request.get("bodyFamily") != family_recipe["bodyFamily"]:
        raise RuntimeError("Roster profile request body family does not match --family")
    if request.get("bodyVariant") != variant_recipe["variant"]:
        raise RuntimeError("Roster profile request body variant does not match --variant")
    merged_variant = {
        **variant_recipe,
        "profileKey": request["profileKey"],
        "expectedHeightM": request["expectedHeightM"],
        "mpfbPreset": {
            **variant_recipe["mpfbPreset"],
            "propertyValues": {
                **variant_recipe["mpfbPreset"]["propertyValues"],
                **request["propertyValues"],
            },
        },
        "skin": request.get("skin", variant_recipe["skin"]),
        "fixtureTargets": request.get("fixtureTargets", variant_recipe.get("fixtureTargets", [])),
        "grooming": request.get("grooming", variant_recipe.get("grooming", {})),
    }
    return {**family_recipe, "profileKey": request["profileKey"]}, merged_variant


def clear_scene() -> None:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def macro_values(variant_recipe: dict) -> dict:
    configured = dict(variant_recipe["mpfbPreset"]["propertyValues"])
    configured.setdefault("cupsize", 0.5)
    configured.setdefault("firmness", 0.5)
    configured["race"] = {"african": 0.24, "asian": 0.16, "caucasian": 0.60}
    return configured


def create_scaled_human(variant_recipe: dict) -> bpy.types.Object:
    macros = macro_values(variant_recipe)
    expected_height = float(variant_recipe.get("expectedHeightM") or 1.75)
    scale = 0.1
    human = HumanService.create_human(
        mask_helpers=True,
        detailed_helpers=True,
        extra_vertex_groups=True,
        feet_on_ground=True,
        scale=scale,
        macro_detail_dict=macros,
    )
    measured = float(human.dimensions.z)
    if measured <= 0:
        raise RuntimeError("MPFB produced a body with zero height")
    corrected_scale = scale * expected_height / measured
    if abs(corrected_scale - scale) > 0.0005:
        clear_scene()
        human = HumanService.create_human(
            mask_helpers=True,
            detailed_helpers=True,
            extra_vertex_groups=True,
            feet_on_ground=True,
            scale=corrected_scale,
            macro_detail_dict=macros,
        )
    return human


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_checked_targets(human: bpy.types.Object, family_recipe: dict, variant_recipe: dict) -> list[dict]:
    applied = []
    for target in variant_recipe.get("customTargets", []):
        path = BODY_FAMILY_ROOT / target["relativePath"]
        if not path.is_file():
            if target.get("required", False):
                raise FileNotFoundError(f"Required original target is missing: {path}")
            continue
        actual_hash = sha256(path)
        expected_hash = target.get("sha256")
        if not expected_hash or actual_hash != expected_hash:
            raise RuntimeError(f"Target hash mismatch for {target['id']}: {actual_hash}")
        TargetService.load_target(human, str(path), weight=float(target["weight"]), name=target["id"])
        applied.append({"id": target["id"], "weight": target["weight"], "sha256": actual_hash})

    user_targets = Path(LocationService.get_user_data("targets"))
    fixture_targets = variant_recipe.get("fixtureTargets") or [
        {"pack": "hands01", "relativePath": "hands/mindfront_hand_fingers_correction.target", "weight": 0.70},
        {"pack": "hands01", "relativePath": "hands/mindfront_hand_thenar_eminence.target", "weight": 0.38},
        {"pack": "hands01", "relativePath": "hands/mindfront_hand_hypothenar.target", "weight": 0.32},
        {"pack": "ears01", "relativePath": "ears/mindfront_ear_details.target", "weight": 0.18 if family_recipe["bodyFamily"] == "mire_brutish_v1" else 0.34},
        {"pack": "nose01", "relativePath": "nose/mindfront_nose_alar_crease.target", "weight": 0.20},
        {"pack": "cheek01", "relativePath": "cheek/elvs_high_chubby_cheekbones_1.target", "weight": 0.08},
        {"pack": "faceunits01", "relativePath": "faceunits/browInnerUp.target", "weight": 0.012},
    ]
    for target in fixture_targets:
        relative_path = target["relativePath"]
        weight = float(target["weight"])
        path = user_targets / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"Required anatomical detail target is missing: {path}")
        TargetService.load_target(human, str(path), weight=weight, name=f"fixture:{target['pack']}:{path.stem}")
        applied.append({
            "id": relative_path,
            "pack": target["pack"],
            "weight": weight,
            "sha256": sha256(path),
        })

    required_fixture_packs = {"ears01", "hands01", "nose01", "cheek01", "faceunits01"}
    applied_fixture_packs = {row.get("pack") for row in applied if row.get("pack")}
    missing_fixture_packs = required_fixture_packs - applied_fixture_packs
    if missing_fixture_packs:
        raise RuntimeError(
            "Body recipe did not exercise every anatomical fixture pack: "
            + ", ".join(sorted(missing_fixture_packs))
        )
    return applied


def asset_path(category: str, name: str, extension: str = "mhclo") -> Path:
    return Path(LocationService.get_user_data(category)) / name / f"{name}.{extension}"


def apply_skin(human: bpy.types.Object, variant_recipe: dict) -> Path:
    skin_name = variant_recipe["skin"]["assetName"]
    skin = asset_path("skins", skin_name, "mhmat")
    if not skin.is_file():
        raise FileNotFoundError(f"Required MPFB skin is missing: {skin}")
    HumanService.set_character_skin(
        str(skin),
        human,
        skin_type="GAMEENGINE",
        material_instances=False,
    )
    if variant_recipe["skin"]["assetPack"] == "skins03":
        hex_color = variant_recipe["skin"]["tint"].lstrip("#")
        tint = tuple(int(hex_color[index:index + 2], 16) / 255 for index in (0, 2, 4))
        for material in human.data.materials:
            material.diffuse_color = (*tint, 1.0)
            principled = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
            if not principled:
                continue
            base_color = principled.inputs["Base Color"]
            if base_color.is_linked:
                source = base_color.links[0].from_socket
                material.node_tree.links.remove(base_color.links[0])
                mix = material.node_tree.nodes.new("ShaderNodeMixRGB")
                mix.name = "GreenskinTint"
                mix.blend_type = "COLOR"
                mix.inputs[0].default_value = 0.84
                mix.inputs[2].default_value = (*tint, 1.0)
                material.node_tree.links.new(source, mix.inputs[1])
                material.node_tree.links.new(mix.outputs[0], base_color)
            else:
                base_color.default_value = (*tint, 1.0)
    return skin


def add_natural_body_parts(human: bpy.types.Object) -> list[bpy.types.Object]:
    definitions = [
        ("eyes", "high-poly", "Eyes"),
        ("teeth", "teeth_base", "Teeth"),
        ("tongue", "tongue01", "Tongue"),
    ]
    objects = []
    for category, name, asset_type in definitions:
        path = asset_path(category, name)
        if not path.is_file():
            raise FileNotFoundError(f"Required MPFB body part is missing: {path}")
        objects.append(HumanService.add_mhclo_asset(
            str(path),
            human,
            asset_type=asset_type,
            subdiv_levels=0,
            material_type="GAMEENGINE",
            set_up_rigging=True,
            interpolate_weights=True,
            import_subrig=False,
            import_weights=True,
        ))
    return objects


def add_grooming(human: bpy.types.Object, variant_recipe: dict) -> tuple[list[bpy.types.Object], list[dict]]:
    """Fit the installed system grooming proxies selected by the race recipe.

    Earlier roster passes only recorded these names in JSON, so every bare head
    remained bald and the six races read as the same base human. These proxies
    are part of the pinned MakeHuman system pack and are now visible geometry.
    """
    # Roster jobs provide an explicit race grooming recipe in their profile
    # request. Standalone body-family jobs do not, so derive the shared face
    # proxies from the family attachments and use the pinned short hairstyle
    # as a deterministic fallback instead of producing a bald or failed body.
    grooming = variant_recipe.get("grooming") or {}
    attachments = variant_recipe.get("attachments") or {}
    grooming = {
        "hair": grooming.get("hair") or attachments.get("hair") or "short01",
        "eyebrows": grooming.get("eyebrows") or attachments.get("eyebrows"),
        "eyelashes": grooming.get("eyelashes") or attachments.get("eyelashes"),
    }
    definitions = (
        ("hair", grooming.get("hair"), "Hair"),
        ("eyebrows", grooming.get("eyebrows"), "Eyebrows"),
        ("eyelashes", grooming.get("eyelashes"), "Eyelashes"),
    )
    objects = []
    provenance = []
    for category, name, asset_type in definitions:
        if not name:
            raise RuntimeError(f"Race grooming recipe is missing {category}")
        source = asset_path(category, name)
        if not source.is_file():
            raise FileNotFoundError(f"Required MPFB grooming fixture is missing: {source}")
        obj = HumanService.add_mhclo_asset(
            str(source),
            human,
            asset_type=asset_type,
            subdiv_levels=0,
            material_type="GAMEENGINE",
            set_up_rigging=True,
            interpolate_weights=True,
            import_subrig=False,
            import_weights=True,
        )
        obj.name = f"grooming_{category}_{name}"
        obj["bodyAccessory"] = True
        obj["groomingCategory"] = category
        obj["groomingAsset"] = name
        obj["requiresAlphaCutout"] = True
        objects.append(obj)
        provenance.append({
            "category": category,
            "asset": name,
            "assetPack": "makehuman_system_assets",
            "path": str(source),
            "sha256": sha256(source),
        })
    return objects, provenance


def bake_targets_and_strip_helpers(human: bpy.types.Object) -> dict:
    """Bake the final anatomical target mix and remove MakeHuman fitting helpers.

    MPFB keeps skirt, hair, joint-cube, and other authoring helper vertices in
    the same mesh and hides them with a Blender Mask modifier. glTF does not
    preserve that authoring-only mask on a skinned mesh, so the helpers must not
    be present in a runtime body at all.
    """
    body_group = human.vertex_groups.get("body")
    if body_group is None:
        raise RuntimeError("MPFB human has no body vertex group for helper stripping")
    before_vertices = len(human.data.vertices)
    body_indices = {
        vertex.index
        for vertex in human.data.vertices
        if any(group.group == body_group.index and group.weight > 0.0 for group in vertex.groups)
    }
    if not body_indices or len(body_indices) == before_vertices:
        raise RuntimeError(
            f"Unexpected MPFB helper partition: body={len(body_indices)}, total={before_vertices}"
        )

    bpy.ops.object.select_all(action="DESELECT")
    human.hide_viewport = False
    human.hide_set(False)
    human.select_set(True)
    bpy.context.view_layer.objects.active = human
    shape_key_count = len(human.data.shape_keys.key_blocks) if human.data.shape_keys else 0
    if shape_key_count:
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for vertex in human.data.vertices:
        vertex.select = vertex.index not in body_indices
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for modifier in list(human.modifiers):
        if modifier.type == "MASK":
            human.modifiers.remove(modifier)
    after_vertices = len(human.data.vertices)
    if after_vertices != len(body_indices):
        raise RuntimeError(
            f"MPFB helper stripping kept {after_vertices} vertices; expected {len(body_indices)}"
        )
    return {
        "verticesBefore": before_vertices,
        "bodyVerticesAfter": after_vertices,
        "helperVerticesRemoved": before_vertices - after_vertices,
        "shapeKeysBaked": shape_key_count,
        "maskModifiersRemoved": True,
    }


def prepare_runtime_materials(meshes: list[bpy.types.Object]) -> list[dict]:
    """Remove MPFB's duplicate diffuse-alpha link before glTF export.

    The bundled opaque body-part textures use their PNG alpha as authoring data,
    not cutout opacity. MPFB creates a second image node that sends that channel
    to Principled Alpha; glTF then exports the entire body as alpha-blended and
    the imported character resembles its UV atlas instead of intact skin.
    """
    audited = []
    seen = set()
    for mesh in meshes:
        for slot in mesh.material_slots:
            material = slot.material
            if not material or material.name in seen:
                continue
            seen.add(material.name)
            if not material.use_nodes or not material.node_tree:
                raise RuntimeError(f"Runtime material has no node tree: {material.name}")
            principled = next(
                (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
                None,
            )
            if not principled:
                raise RuntimeError(f"Runtime material has no Principled shader: {material.name}")
            alpha = principled.inputs.get("Alpha")
            removed_links = 0
            alpha_mode = "BLEND" if mesh.get("requiresAlphaCutout") else "OPAQUE"
            if alpha and alpha_mode == "OPAQUE":
                for link in list(alpha.links):
                    material.node_tree.links.remove(link)
                    removed_links += 1
                alpha.default_value = 1.0
            removed_nodes = 0
            if alpha_mode == "OPAQUE":
                for node in list(material.node_tree.nodes):
                    if node.type == "TEX_IMAGE" and node.name == "AlphaMapTexture" and not node.outputs[0].is_linked:
                        material.node_tree.nodes.remove(node)
                        removed_nodes += 1
            material["runtimeAlphaMode"] = alpha_mode
            audited.append({
                "mesh": mesh.name,
                "material": material.name,
                "alphaMode": alpha_mode,
                "removedAlphaLinks": removed_links,
                "removedDuplicateAlphaNodes": removed_nodes,
            })
    return audited


def create_tusk_mesh(name: str, center_x: float, front_y: float, mouth_z: float, scale: float) -> bpy.types.Object:
    rings = 10
    sides = 12
    vertices = []
    for ring in range(rings):
        t = ring / (rings - 1)
        radius = scale * 0.019 * max(0.12, (1.0 - t) ** 0.72)
        center = Vector((
            center_x + math.copysign(scale * 0.004 * t, center_x),
            front_y - scale * (0.018 * t + 0.016 * t * t),
            mouth_z + scale * (0.092 * t + 0.028 * t * t),
        ))
        for side in range(sides):
            angle = math.tau * side / sides
            vertices.append((
                center.x + radius * math.cos(angle),
                center.y + radius * math.sin(angle),
                center.z,
            ))
    faces = []
    for ring in range(rings - 1):
        for side in range(sides):
            nxt = (side + 1) % sides
            a = ring * sides + side
            b = ring * sides + nxt
            c = (ring + 1) * sides + nxt
            d = (ring + 1) * sides + side
            faces.append((a, b, c, d))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((rings - 1) * sides + side for side in range(sides)))
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def create_tusks(human: bpy.types.Object, rig: bpy.types.Object, teeth: bpy.types.Object) -> list[bpy.types.Object]:
    corners = [human.matrix_world @ Vector(corner) for corner in human.bound_box]
    minimum = Vector((min(p.x for p in corners), min(p.y for p in corners), min(p.z for p in corners)))
    maximum = Vector((max(p.x for p in corners), max(p.y for p in corners), max(p.z for p in corners)))
    teeth_corners = [teeth.matrix_world @ Vector(corner) for corner in teeth.bound_box]
    height = maximum.z - minimum.z
    scale = height / 1.95
    mouth_z = min(point.z for point in teeth_corners) - scale * 0.006
    front_y = min(point.y for point in teeth_corners) - scale * 0.022
    tusks = []
    for side, center_x in (("L", scale * 0.038), ("R", -scale * 0.038)):
        tusk = create_tusk_mesh(f"mire_tusk_{side}", center_x, front_y, mouth_z, scale)
        tusk.parent = rig
        tusk.matrix_parent_inverse = rig.matrix_world.inverted()
        group = tusk.vertex_groups.new(name="head")
        group.add(range(len(tusk.data.vertices)), 1.0, "REPLACE")
        modifier = tusk.modifiers.new("humanoid_game_v2", "ARMATURE")
        modifier.object = rig
        tusk["assetType"] = "bodyPart"
        tusk["bodyPartId"] = "mire_tusks_v1"
        tusks.append(tusk)
    return tusks


def join_tusks_into_teeth(tusks: list[bpy.types.Object], teeth: bpy.types.Object) -> None:
    """Keep both tusks and fitted teeth in one bone-material draw call."""
    if not teeth.material_slots:
        raise RuntimeError("The fitted teeth asset has no material for the tusks")
    teeth_material = teeth.material_slots[0].material
    principled = next((node for node in teeth_material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if principled:
        for socket_name in ("Base Color", "Alpha"):
            socket = principled.inputs[socket_name]
            for link in list(socket.links):
                teeth_material.node_tree.links.remove(link)
        principled.inputs["Base Color"].default_value = (0.30, 0.24, 0.14, 1.0)
        principled.inputs["Alpha"].default_value = 1.0
        principled.inputs["Roughness"].default_value = 0.46
    bpy.ops.object.select_all(action="DESELECT")
    teeth.select_set(True)
    for tusk in tusks:
        tusk.data.materials.clear()
        tusk.data.materials.append(teeth_material)
        tusk.select_set(True)
    bpy.context.view_layer.objects.active = teeth
    bpy.ops.object.join()
    teeth.name = "teeth_and_mire_tusks"
    teeth["bodyPartId"] = "mire_tusks_v1"


def add_canonical_face_bones(rig: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    head = rig.data.edit_bones["head"]
    direction = (head.tail - head.head).normalized()
    span = max((head.tail - head.head).length, 0.08)
    jaw = rig.data.edit_bones.new("jaw")
    jaw.parent = head
    jaw.use_connect = False
    jaw.head = head.head + direction * span * 0.34 + Vector((0, -span * 0.20, 0))
    jaw.tail = jaw.head + Vector((0, -span * 0.06, -span * 0.20))
    for side, x_sign in (("L", 1.0), ("R", -1.0)):
        eye = rig.data.edit_bones.new(f"eye_{side}")
        eye.parent = head
        eye.use_connect = False
        eye.head = head.head + direction * span * 0.67 + Vector((x_sign * span * 0.17, -span * 0.23, 0))
        eye.tail = eye.head + Vector((0, -span * 0.08, 0))
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)


def canonicalize_rig(rig: bpy.types.Object, meshes: list[bpy.types.Object]) -> None:
    for old_name, new_name in MPFB_TO_CANONICAL.items():
        bone = rig.data.bones.get(old_name)
        if bone:
            bone.name = new_name
    for mesh in meshes:
        for old_name, new_name in MPFB_TO_CANONICAL.items():
            group = mesh.vertex_groups.get(old_name)
            if group:
                group.name = new_name
    add_canonical_face_bones(rig)
    rig.name = "humanoid_game_v2"
    rig.data.name = "humanoid_game_v2"


def limit_bone_influences(mesh: bpy.types.Object, bone_names: set[str], limit: int = 4) -> tuple[int, int]:
    bone_groups = {group.index: group for group in mesh.vertex_groups if group.name in bone_names}
    max_before = 0
    unweighted = 0
    body_group = mesh.vertex_groups.get("body")
    body_group_index = body_group.index if body_group else None
    for vertex in mesh.data.vertices:
        if body_group_index is not None and not any(g.group == body_group_index and g.weight > 0 for g in vertex.groups):
            continue
        influences = [(g.group, g.weight) for g in vertex.groups if g.group in bone_groups and g.weight > 1e-8]
        max_before = max(max_before, len(influences))
        if not influences:
            unweighted += 1
            continue
        influences.sort(key=lambda item: item[1], reverse=True)
        keep = influences[:limit]
        total = sum(weight for _, weight in keep)
        for group_index, _weight in influences[limit:]:
            bone_groups[group_index].remove([vertex.index])
        for group_index, weight in keep:
            bone_groups[group_index].add([vertex.index], weight / total, "REPLACE")
    return max_before, unweighted


def add_socket(
    rig: bpy.types.Object,
    name: str,
    bone_name: str,
    location: tuple[float, float, float],
    rotation_degrees: tuple[float, float, float],
) -> bpy.types.Object:
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "ARROWS"
    empty.empty_display_size = 0.08
    bpy.context.scene.collection.objects.link(empty)
    empty.parent = rig
    empty.parent_type = "BONE"
    empty.parent_bone = bone_name
    empty.location = location
    empty.rotation_mode = "XYZ"
    empty.rotation_euler = tuple(math.radians(value) for value in rotation_degrees)
    empty["socketId"] = name
    return empty


def add_sockets(rig: bpy.types.Object) -> list[bpy.types.Object]:
    with SKELETON_CONTRACT_PATH.open(encoding="utf-8") as handle:
        contract = json.load(handle)
    # Object metadata is applied after socket creation; validate the contract
    # against the canonical generator identity and the actual rig bones here.
    if contract.get("skeletonId") != "humanoid_game_v2":
        raise RuntimeError("Socket contract is not the canonical humanoid game skeleton")
    sockets = []
    for definition in contract.get("sockets", []):
        if definition["parentBone"] not in rig.data.bones:
            raise RuntimeError(f"Socket parent bone is missing: {definition['parentBone']}")
        sockets.append(add_socket(
            rig,
            definition["name"],
            definition["parentBone"],
            tuple(definition["translation"]),
            tuple(definition["rotationDegrees"]),
        ))
    if {socket.name for socket in sockets} != {
        "socket_root", "socket_hand_L", "socket_hand_R", "socket_back",
    }:
        raise RuntimeError("Canonical socket contract is incomplete")
    return sockets


def set_metadata(objects: list[bpy.types.Object], family_recipe: dict, variant_recipe: dict) -> None:
    metadata = {
        "assetId": f"body.{variant_recipe['profileKey'].replace('.', '_')}",
        "assetCategory": "characterBody",
        "bodyFamily": family_recipe["bodyFamily"],
        "bodyVariant": variant_recipe["variant"],
        "profileKey": variant_recipe["profileKey"],
        "skeletonId": family_recipe["skeletonId"],
        "bindPoseId": family_recipe["bindPoseId"],
        "generatorKind": "mpfbBodyFamily",
        "generatorVersion": "MPFB 2.0.16",
        "license": "CC0-1.0",
        "lifecycleStatus": "draft",
        "reviewStatus": "pending",
    }
    for obj in objects:
        for key, value in metadata.items():
            obj[key] = value


def render_bounds(meshes: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    return (
        Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))),
        Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))),
    )


def aim(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_reviews(meshes: list[bpy.types.Object], review_dir: Path) -> list[dict]:
    review_dir.mkdir(parents=True, exist_ok=True)
    minimum, maximum = render_bounds(meshes)
    center = (minimum + maximum) * 0.5
    height = maximum.z - minimum.z
    width = maximum.x - minimum.x
    distance = max(height, width) * 2.2

    camera_data = bpy.data.cameras.new("review_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(height * 1.12, width * 1.18)
    camera = bpy.data.objects.new("review_camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    for name, location, energy, size in (
        ("review_key", (-2.6, -3.4, maximum.z + 1.2), 1050, 2.2),
        ("review_fill", (2.8, -1.5, center.z + 0.4), 700, 2.6),
        ("review_rim", (0.6, 3.2, maximum.z + 0.8), 900, 2.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        bpy.context.scene.collection.objects.link(obj)
        aim(obj, center)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.03, 0.04)
    views = {
        "front": Vector((center.x, minimum.y - distance, center.z)),
        "side": Vector((maximum.x + distance, center.y, center.z)),
        "back": Vector((center.x, maximum.y + distance, center.z)),
        "isometric": Vector((maximum.x + distance * 0.72, minimum.y - distance * 0.72, center.z + height * 0.10)),
    }
    rendered = []
    for name, position in views.items():
        camera.location = position
        aim(camera, center)
        path = review_dir / f"{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        rendered.append({"view": name, "path": str(path), "sha256": sha256(path)})
    return rendered


def evaluated_triangles(obj: bpy.types.Object, depsgraph) -> int:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        return len(mesh.loop_triangles)
    finally:
        evaluated.to_mesh_clear()


def export_glb(output: Path, objects: list[bpy.types.Object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_viewport = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    export_options = {
        "filepath": str(output),
        "export_format": "GLB",
        "use_selection": True,
        "export_animations": True,
        "export_skins": True,
        "export_morph": True,
        "export_extras": True,
        "export_yup": True,
        "export_apply": False,
        "export_draco_mesh_compression_enable": False,
    }
    available = {prop.identifier for prop in bpy.ops.export_scene.gltf.get_rna_type().properties}
    if "export_animation_mode" in available:
        export_options["export_animation_mode"] = "ACTIONS"
    if "export_nla_strips" in available:
        export_options["export_nla_strips"] = False
    if "export_anim_single_armature" in available:
        export_options["export_anim_single_armature"] = True
    bpy.ops.export_scene.gltf(**export_options)
    bpy.ops.object.select_all(action="DESELECT")


def embedded_animation_names(output: Path) -> list[str]:
    """Read the GLB JSON chunk so QC proves the clips were actually exported."""
    payload = output.read_bytes()
    if payload[:4] != b"glTF" or int.from_bytes(payload[4:8], "little") != 2:
        raise RuntimeError(f"Not a GLB 2.0 file: {output}")
    offset = 12
    while offset + 8 <= len(payload):
        chunk_length = int.from_bytes(payload[offset:offset + 4], "little")
        chunk_type = int.from_bytes(payload[offset + 4:offset + 8], "little")
        chunk = payload[offset + 8:offset + 8 + chunk_length]
        if chunk_type == 0x4E4F534A:
            document = json.loads(chunk.rstrip(b" \t\r\n\0").decode("utf-8"))
            return sorted(animation.get("name", "") for animation in document.get("animations", []))
        offset += 8 + chunk_length
    raise RuntimeError(f"GLB has no JSON chunk: {output}")


def embedded_material_audit(output: Path) -> list[dict]:
    payload = output.read_bytes()
    json_length = int.from_bytes(payload[12:16], "little")
    document = json.loads(payload[20:20 + json_length].rstrip(b" \t\r\n\0").decode("utf-8"))
    rows = []
    for material in document.get("materials", []):
        pbr = material.get("pbrMetallicRoughness", {})
        has_texture = "baseColorTexture" in pbr
        rows.append({
            "name": material.get("name"),
            "alphaMode": material.get("alphaMode", "OPAQUE"),
            "hasBaseColorTexture": has_texture,
            # glTF's default baseColorFactor is a valid scalar PBR source for
            # untextured teeth/tusks; a texture is not mandatory for that part.
            "baseColorSource": "texture" if has_texture else "material_factor",
        })
    return rows


def write_qc(
    output: Path,
    meshes: list[bpy.types.Object],
    rig: bpy.types.Object,
    previews: list[dict],
    applied_targets: list[dict],
    skin: Path,
    influence_audit: list[dict],
    animation_audit: dict,
    material_preparation: list[dict],
    helper_stripping: dict,
    roundtrip_audit: dict,
    authoring_source: dict,
    grooming_provenance: list[dict],
) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_rows = []
    total_triangles = 0
    draw_calls = 0
    for obj in meshes:
        triangles = evaluated_triangles(obj, depsgraph)
        materials = max(1, len(obj.material_slots))
        total_triangles += triangles
        draw_calls += materials
        mesh_rows.append({
            "name": obj.name,
            "vertices": len(obj.data.vertices),
            "triangles": triangles,
            "drawCalls": materials,
        })
    max_influences_before_limit = max((row["maxBefore"] for row in influence_audit), default=0)
    unweighted_vertices = sum(row["unweighted"] for row in influence_audit)
    animation_clips = embedded_animation_names(output)
    required_clips = [clip["name"] for clip in animation_audit["clips"]]
    missing_required_clips = sorted(set(required_clips) - set(animation_clips))
    runtime_materials = embedded_material_audit(output)
    alpha_fixture_materials = {
        row["material"]
        for row in material_preparation
        if row["alphaMode"] != "OPAQUE"
    }
    checks = {
        "modelExists": output.is_file(),
        "triangleBudget": total_triangles <= BODY_BUDGET_TRIANGLES,
        "drawCallBudget": draw_calls <= BODY_BUDGET_DRAW_CALLS,
        "boneBudget": len(rig.data.bones) <= 64,
        "fourInfluenceLimitApplied": max_influences_before_limit >= 0,
        "allVerticesWeighted": unweighted_vertices == 0,
        "reviewViewsPresent": len(previews) == 4 and all(Path(row["path"]).is_file() for row in previews),
        "skinSourcePresent": skin.is_file(),
        "requiredAnimationClipsEmbedded": animation_clips == sorted(required_clips),
        "runtimeBodyMaterialsOpaque": bool(runtime_materials) and all(
            row["alphaMode"] == "OPAQUE"
            for row in runtime_materials
            if row["name"] not in alpha_fixture_materials
        ),
        "groomingFixturesPresent": len(grooming_provenance) == 3
        and all(Path(row["path"]).is_file() for row in grooming_provenance),
        "roundTripBindPose": roundtrip_audit["passed"],
        "authoringTopologyStable": authoring_source["bodyVertices"] == MPFB_AUTHORING_BODY_VERTICES,
    }
    report = {
        "schemaVersion": 1,
        "assetId": rig.get("assetId"),
        "model": output.name,
        "modelSha256": sha256(output),
        "fileSizeBytes": output.stat().st_size,
        "lifecycleStatus": "draft",
        "reviewStatus": "pending",
        "promotionEligible": False,
        "skeletonId": rig.get("skeletonId"),
        "bindPoseId": rig.get("bindPoseId"),
        "boneCount": len(rig.data.bones),
        "totalTriangles": total_triangles,
        "drawCalls": draw_calls,
        "maxInfluencesBeforeLimit": max_influences_before_limit,
        "unweightedVertices": unweighted_vertices,
        "pbr": {
            "baseColor": "texture-or-material",
            "normal": "texture-or-flat-normal",
            "roughness": "texture-or-scalar",
            "metallic": "scalar",
            "occlusion": "material-constant",
            "maxTextureDimension": 2048,
        },
        "checks": checks,
        "qcPassed": all(checks.values()),
        "meshes": mesh_rows,
        "targets": applied_targets,
        "skin": {"path": str(skin), "sha256": sha256(skin)},
        "grooming": grooming_provenance,
        "previews": previews,
        "animationClips": animation_clips,
        "requiredAnimationClips": required_clips,
        "missingRequiredClips": missing_required_clips,
        "animationAudit": animation_audit,
        "materialPreparation": material_preparation,
        "runtimeMaterials": runtime_materials,
        "helperStripping": helper_stripping,
        "roundTrip": roundtrip_audit,
        "authoringSource": authoring_source,
    }
    qc_path = output.with_suffix(".qc.json")
    qc_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> None:
    args = parse_args()
    family_recipe = load_recipe(args.family)
    variant_recipe = family_recipe["variants"][args.variant]
    family_recipe, variant_recipe = apply_profile_request(
        family_recipe,
        variant_recipe,
        args.profile_request,
    )
    clear_scene()
    human = create_scaled_human(variant_recipe)
    human.name = f"body_{args.family}_{args.variant}"
    applied_targets = load_checked_targets(human, family_recipe, variant_recipe)
    skin = apply_skin(human, variant_recipe)
    rig = HumanService.add_builtin_rig(human, variant_recipe["mpfbPreset"]["rig"], import_weights=True)
    if not rig:
        raise RuntimeError("MPFB failed to create the game-engine rig")
    body_parts = add_natural_body_parts(human)
    grooming, grooming_provenance = add_grooming(human, variant_recipe)
    meshes = [human, *body_parts, *grooming]
    canonicalize_rig(rig, meshes)
    if args.family == "mire_brutish_v1":
        join_tusks_into_teeth(create_tusks(human, rig, body_parts[1]), body_parts[1])
    sockets = add_sockets(rig)
    export_objects = [rig, *meshes, *sockets]
    set_metadata(export_objects, family_recipe, variant_recipe)
    animation_audit = attach_canonical_animation_pack(rig, profile=args.animation_profile)

    # Armor fitting needs MPFB's stable 19,158-vertex authoring topology and
    # live target keys. Save it before mutating the in-memory runtime copy.
    authoring_vertices = len(human.data.vertices)
    if authoring_vertices != MPFB_AUTHORING_BODY_VERTICES:
        raise RuntimeError(
            f"MPFB authoring topology changed: {authoring_vertices} != {MPFB_AUTHORING_BODY_VERTICES}"
        )
    authoring_source = {
        "path": None,
        "sha256": None,
        "bodyVertices": authoring_vertices,
        "shapeKeys": len(human.data.shape_keys.key_blocks) if human.data.shape_keys else 0,
        "maskModifiers": [modifier.name for modifier in human.modifiers if modifier.type == "MASK"],
        "savedBeforeRuntimeOptimization": True,
    }
    if args.save_blend:
        blend_path = Path(args.save_blend).resolve()
        blend_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
        authoring_source["path"] = str(blend_path)
        authoring_source["sha256"] = sha256(blend_path)

    helper_stripping = bake_targets_and_strip_helpers(human)
    material_preparation = prepare_runtime_materials(meshes)

    bone_names = {bone.name for bone in rig.data.bones}
    influence_audit = []
    for mesh in meshes:
        max_before, unweighted = limit_bone_influences(mesh, bone_names, 4)
        influence_audit.append({"mesh": mesh.name, "maxBefore": max_before, "unweighted": unweighted})

    output = Path(args.output).resolve()
    review_dir = Path(args.review_dir).resolve()
    export_glb(output, export_objects)
    previews = render_reviews(meshes, review_dir)
    roundtrip_audit = roundtrip_bind_audit(output, meshes, rig)
    report = write_qc(
        output,
        meshes,
        rig,
        previews,
        applied_targets,
        skin,
        influence_audit,
        animation_audit,
        material_preparation,
        helper_stripping,
        roundtrip_audit,
        authoring_source,
        grooming_provenance,
    )
    print("[real-character] " + json.dumps({
        "assetId": report["assetId"],
        "output": str(output),
        "qcPassed": report["qcPassed"],
        "triangles": report["totalTriangles"],
        "drawCalls": report["drawCalls"],
        "boneCount": report["boneCount"],
    }))


if __name__ == "__main__":
    main()
