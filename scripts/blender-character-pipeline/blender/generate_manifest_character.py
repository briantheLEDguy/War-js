"""
Neutral manifest character builder.

This is the character path used by generate_asset_from_manifest.py. It avoids
class-name-derived output, oversized loose decorations, and bind-pose-only
equipment overlays. The generated character is a cohesive skinned GLB with
embedded basic locomotion/action clips and neutral GLTF extras.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

from anim_library import ACTIONS, make_profile_actions
from export_utils import normalize_y_up_scene_to_blender_z_up, repo_relative_path
from mesh_primitives import (
    box_prism,
    cloth_panel,
    flat_material,
    loft_axis,
    pauldron_shell,
    sphere,
    superellipse_bar,
    textured_material,
    torus,
    torso_shell,
    tube_shell_between,
)
from rig_utils import apply_animations, create_humanoid_rig

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
PLAYABLE_ROSTER_PATH = PIPELINE_ROOT / "data" / "playable-character-roster.json"


PROFILE_STYLES = {
    "human_pyromancer": {
        "cloth": "#7e1712",
        "cloth2": "#241214",
        "metal": "#30363a",
        "trim": "#c0842e",
        "leather": "#301b12",
        "hood": True,
        "helmet": False,
    },
    "human_tracker": {
        "cloth": "#1b1c1d",
        "cloth2": "#3a2116",
        "metal": "#20272b",
        "trim": "#8f6d33",
        "leather": "#24150f",
        "hood": True,
        "helmet": False,
    },
    "human_sun_vanguard": {
        "cloth": "#7a1513",
        "cloth2": "#b9ab82",
        "metal": "#2c383c",
        "trim": "#a98632",
        "leather": "#2b1a11",
        "hood": False,
        "helmet": True,
    },
        "human_devout_guardian": {
        "cloth": "#781714",
        "cloth2": "#b8aa82",
        "metal": "#202b2d",
        "trim": "#9f7d2f",
        "leather": "#221611",
        "hood": False,
        "helmet": True,
    },
}

_PLAYABLE_ROSTER: dict | None = None


def playable_roster() -> dict:
    global _PLAYABLE_ROSTER
    if _PLAYABLE_ROSTER is None:
        if not PLAYABLE_ROSTER_PATH.exists():
            _PLAYABLE_ROSTER = {"races": {}, "classes": [], "bodyVariants": {}}
        else:
            _PLAYABLE_ROSTER = json.loads(PLAYABLE_ROSTER_PATH.read_text(encoding="utf-8"))
    return _PLAYABLE_ROSTER


def playable_profile_key(race: dict, klass: dict, variant_key: str) -> str:
    return f"{race['family']}_{klass['key']}_{variant_key}"


def playable_profile_style(profile: str) -> dict | None:
    roster = playable_roster()
    for klass in roster.get("classes", []):
        race = roster.get("races", {}).get(klass.get("race"))
        if not race:
            continue
        for variant_key, variant in roster.get("bodyVariants", {}).items():
            if playable_profile_key(race, klass, variant_key) != profile:
                continue
            scale = (
                float(race["scale"][0]) * float(variant["scale"][0]),
                float(race["scale"][1]) * float(variant["scale"][1]),
                float(race["scale"][2]) * float(variant["scale"][2]),
            )
            colors = klass.get("colors", {})
            return {
                "profile": profile,
                "raceKey": klass["race"],
                "classKey": klass["key"],
                "className": klass["className"],
                "variant": variant_key,
                "variantLabel": variant.get("label", variant_key),
                "bodyScale": scale,
                "skin": race.get("skin", "#bd8664"),
                "hair": race.get("hair", "#211713"),
                "traits": race.get("traits", []),
                "archetype": klass.get("archetype", "fighter"),
                "animationProfile": klass.get("animationProfile", "sword_shield"),
                "headgear": klass.get("headgear", "helmet"),
                "cloth": colors.get("cloth", "#26242a"),
                "cloth2": colors.get("cloth2", "#5d4f42"),
                "metal": colors.get("metal", "#3f464a"),
                "trim": colors.get("trim", "#a77a34"),
                "leather": colors.get("leather", "#2f1d12"),
                "accent": colors.get("accent", "#b98a35"),
                "hood": klass.get("headgear") == "hood",
                "helmet": klass.get("headgear") not in {"hood", "circlet", "mask"},
            }
    return None


def is_playable_profile(profile: str) -> bool:
    return playable_profile_style(profile) is not None


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def materials(style: dict) -> dict[str, bpy.types.Material]:
    return {
        "skin": textured_material("mat_character_skin", style.get("skin", "#bd8664"), "skin", 0.72, 0.0, 384),
        "hair": textured_material("mat_character_hair", style.get("hair", "#211713"), "leather", 0.88, 0.0, 256),
        "under": textured_material("mat_dark_gambeson", style["cloth"], "cloth", 0.92, 0.0, 384),
        "cloth": textured_material("mat_secondary_cloth", style["cloth2"], "cloth", 0.94, 0.0, 384),
        "metal": textured_material("mat_blackened_plate", style["metal"], "metal", 0.58, 0.64, 512),
        "dark_metal": textured_material("mat_darkened_plate", "#10171a", "metal", 0.64, 0.56, 256),
        "trim": textured_material("mat_worn_brass_trim", style["trim"], "brass", 0.38, 0.62, 384),
        "leather": textured_material("mat_dark_leather_straps", style["leather"], "leather", 0.84, 0.0, 256),
        "accent": textured_material("mat_class_accent", style.get("accent", style["trim"]), "brass", 0.34, 0.35, 256),
        "shadow": flat_material("mat_eye_shadow", "#060708", 0.9, 0.0),
        "eye": flat_material("mat_eye_warm_gray", "#d8d2c5", 0.45, 0.0),
        "ivory": flat_material("mat_worn_ivory", "#d8c090", 0.64, 0.0),
    }


def add_anchor(name: str, parent: str, pos: tuple[float, float, float], manifest: dict) -> bpy.types.Object:
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "SPHERE"
    empty.empty_display_size = 0.035
    empty.location = pos
    empty["assetId"] = manifest["assetId"]
    empty["anchorParent"] = parent
    empty["assetCategory"] = manifest["category"]
    bpy.context.collection.objects.link(empty)
    return empty


def add_manifest_metadata(objects: list[bpy.types.Object], manifest: dict) -> None:
    runtime = manifest.get("runtime", {})
    geometry = manifest.get("geometry", {})
    slots = (manifest.get("compatibility") or {}).get("occupiesSlots") or ["character"]
    metadata = {
        "assetId": manifest["assetId"],
        "assetKit": runtime.get("profileKey") or manifest["assetId"],
        "assetCategory": manifest["category"],
        "assetSlot": slots[0],
        "bodyFamily": geometry.get("bodyFamily"),
        "skeletonId": geometry.get("skeletonId"),
    }
    for obj in objects:
        for key, value in metadata.items():
            if value:
                obj[key] = value


def tag_region(objects: list[bpy.types.Object], region: str) -> None:
    for obj in objects:
        obj["bodyRegion"] = region
        obj["isCharacterBody"] = True


def scale_objects(objects: list[bpy.types.Object], scale: tuple[float, float, float]) -> None:
    sx, sy, sz = scale
    for obj in objects:
        obj.location.x *= sx
        obj.location.y *= sy
        obj.location.z *= sz
        if obj.type != "MESH":
            continue
        for vertex in obj.data.vertices:
            vertex.co.x *= sx
            vertex.co.y *= sy
            vertex.co.z *= sz
        obj.data.update()


def slot_from_manifest(manifest: dict) -> str:
    slots = (manifest.get("compatibility") or {}).get("occupiesSlots") or []
    return slots[0] if slots else "chest"


def add_face_traits(objects: list[bpy.types.Object], style: dict, mats: dict[str, bpy.types.Material]) -> None:
    traits = set(style.get("traits", []))
    for side in (-1, 1):
        eye = loft_axis(f"body_eye_{side}", "z", [
            {"coord": 0.145, "cx": side * 0.050, "cy": 1.795, "rx": 0.022, "ry": 0.012},
            {"coord": 0.160, "cx": side * 0.050, "cy": 1.795, "rx": 0.018, "ry": 0.010},
        ], mats["eye"], segments=16)
        brow = superellipse_bar(f"body_brow_{side}", "x", (side * 0.052, 1.825, 0.145),
                                0.060, 0.008, 0.007, mats["hair"], segments=12)
        objects.extend([eye, brow])

    objects.append(loft_axis("body_nose", "z", [
        {"coord": 0.130, "cx": 0.0, "cy": 1.775, "rx": 0.018, "ry": 0.032},
        {"coord": 0.190, "cx": 0.0, "cy": 1.748, "rx": 0.026, "ry": 0.022},
    ], mats["skin"], segments=18))

    if "beard" in traits:
        objects.append(loft_axis("body_beard", "y", [
            {"coord": 1.43, "rx": 0.135, "rz": 0.050, "cz": 0.130},
            {"coord": 1.55, "rx": 0.150, "rz": 0.065, "cz": 0.145},
            {"coord": 1.66, "rx": 0.125, "rz": 0.052, "cz": 0.135},
        ], mats["hair"], segments=42))

    if "elf_ears" in traits:
        for side in (-1, 1):
            objects.append(loft_axis(f"body_ear_{side}", "x", [
                {"coord": side * 0.130, "cy": 1.785, "cz": 0.012, "ry": 0.040, "rz": 0.018},
                {"coord": side * 0.230, "cy": 1.805, "cz": 0.008, "ry": 0.018, "rz": 0.010},
            ], mats["skin"], segments=16))

    if "tusks" in traits:
        for side in (-1, 1):
            tusk = loft_axis(f"body_tusk_{side}", "z", [
                {"coord": 0.178, "cx": side * 0.055, "cy": 1.635, "rx": 0.018, "ry": 0.016},
                {"coord": 0.285, "cx": side * 0.075, "cy": 1.590, "rx": 0.006, "ry": 0.005},
            ], mats["ivory"], segments=12)
            objects.append(tusk)

    if "scarred" in traits:
        scar = superellipse_bar("body_face_scar", "y", (0.052, 1.805, 0.165),
                                0.165, 0.006, 0.004, mats["accent"], segments=10, rings=5)
        scar.rotation_euler[2] = -0.55
        objects.append(scar)


def build_playable_character(manifest: dict, style: dict) -> tuple[list[bpy.types.Object], bpy.types.Object, list[bpy.types.Object]]:
    mats = materials(style)
    objects: list[bpy.types.Object] = []

    torso = loft_axis("body_under_torso", "y", [
        {"coord": 0.82, "rx": 0.205, "rz": 0.110},
        {"coord": 1.02, "rx": 0.248, "rz": 0.138},
        {"coord": 1.26, "rx": 0.290, "rz": 0.158},
        {"coord": 1.48, "rx": 0.305, "rz": 0.154},
        {"coord": 1.60, "rx": 0.218, "rz": 0.112},
    ], mats["under"], segments=60)
    hips = loft_axis("body_under_hips", "y", [
        {"coord": 0.20, "rx": 0.230, "rz": 0.118},
        {"coord": 0.52, "rx": 0.288, "rz": 0.140},
        {"coord": 0.86, "rx": 0.295, "rz": 0.148},
        {"coord": 1.02, "rx": 0.245, "rz": 0.130},
    ], mats["under"], segments=56)
    tag_region([torso], "torso")
    tag_region([hips], "waist")
    objects.extend([torso, hips])

    neck = loft_axis("body_neck", "y", [
        {"coord": 1.52, "rx": 0.070, "rz": 0.058},
        {"coord": 1.66, "rx": 0.076, "rz": 0.064},
    ], mats["skin"], segments=32)
    head = loft_axis("body_head", "y", [
        {"coord": 1.66, "rx": 0.105, "rz": 0.090, "cz": 0.012},
        {"coord": 1.75, "rx": 0.148, "rz": 0.125, "cz": 0.030},
        {"coord": 1.84, "rx": 0.144, "rz": 0.118, "cz": 0.020},
        {"coord": 1.92, "rx": 0.095, "rz": 0.080, "cz": -0.005},
    ], mats["skin"], segments=54)
    tag_region([neck, head], "head")
    objects.extend([neck, head])
    add_face_traits(objects, style, mats)

    for side in (-1, 1):
        upper_arm = loft_axis(f"body_upper_arm_{side}", "x", [
            {"coord": side * 0.290, "cy": 1.405, "cz": 0.035, "ry": 0.078, "rz": 0.064},
            {"coord": side * 0.430, "cy": 1.230, "cz": 0.060, "ry": 0.068, "rz": 0.055},
        ], mats["under"], segments=30)
        forearm = loft_axis(f"body_forearm_{side}", "x", [
            {"coord": side * 0.430, "cy": 1.230, "cz": 0.060, "ry": 0.066, "rz": 0.054},
            {"coord": side * 0.540, "cy": 1.000, "cz": 0.086, "ry": 0.052, "rz": 0.046},
        ], mats["under"], segments=30)
        hand = loft_axis(f"body_hand_{side}", "x", [
            {"coord": side * 0.535, "cy": 0.980, "cz": 0.094, "ry": 0.045, "rz": 0.036},
            {"coord": side * 0.595, "cy": 0.930, "cz": 0.105, "ry": 0.038, "rz": 0.030},
        ], mats["skin"], segments=22)
        thigh = loft_axis(f"body_thigh_{side}", "y", [
            {"coord": 0.90, "cx": side * 0.135, "cz": 0.010, "rx": 0.085, "rz": 0.070},
            {"coord": 0.55, "cx": side * 0.135, "cz": 0.010, "rx": 0.074, "rz": 0.062},
        ], mats["under"], segments=34)
        shin = loft_axis(f"body_shin_{side}", "y", [
            {"coord": 0.53, "cx": side * 0.135, "cz": 0.010, "rx": 0.066, "rz": 0.058},
            {"coord": 0.17, "cx": side * 0.135, "cz": 0.018, "rx": 0.056, "rz": 0.050},
        ], mats["under"], segments=30)
        foot = loft_axis(f"body_foot_{side}", "y", [
            {"coord": 0.00, "cx": side * 0.135, "cz": 0.095, "rx": 0.075, "rz": 0.135},
            {"coord": 0.14, "cx": side * 0.135, "cz": 0.065, "rx": 0.084, "rz": 0.110},
            {"coord": 0.30, "cx": side * 0.135, "cz": 0.020, "rx": 0.064, "rz": 0.055},
        ], mats["leather"], segments=32)
        tag_region([upper_arm, forearm], "arms")
        tag_region([hand], "hands")
        tag_region([thigh, shin], "legs")
        tag_region([foot], "feet")
        objects.extend([upper_arm, forearm, hand, thigh, shin, foot])

    class_mark = torus("body_class_core", 0.118, 0.009, mats["accent"], (0, 1.30, 0.176), rotation=(math.pi / 2, 0, 0), major_segments=30, minor_segments=8)
    tag_region([class_mark], "torso")
    objects.append(class_mark)

    scale = style["bodyScale"]
    scale_objects(objects, scale)
    add_manifest_metadata(objects, manifest)
    armature = create_humanoid_rig(objects, scale, rig_profile="default")

    anchors: list[bpy.types.Object] = []
    for anchor in manifest.get("attachments", []):
        pos = tuple(anchor.get("position", [0, 0, 0]))
        anchors.append(add_anchor(anchor["name"], anchor["parent"], pos, manifest))
    add_manifest_metadata([armature, *anchors], manifest)
    apply_animations(armature, make_profile_actions(style["animationProfile"]))
    return objects, armature, anchors


def build_head_slot(style: dict, mats: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    mode = style.get("headgear", "helmet")
    objects: list[bpy.types.Object] = []
    if mode == "hood":
        objects.append(loft_axis("armor_hood_cowl", "y", [
            {"coord": 1.55, "rx": 0.190, "rz": 0.130, "cz": -0.012},
            {"coord": 1.72, "rx": 0.215, "rz": 0.165, "cz": -0.010},
            {"coord": 1.90, "rx": 0.162, "rz": 0.130, "cz": -0.020},
            {"coord": 1.99, "rx": 0.066, "rz": 0.060, "cz": -0.030},
        ], mats["cloth"], segments=58))
    elif mode == "circlet":
        objects.append(torus("armor_circlet", 0.142, 0.010, mats["trim"], (0, 1.825, 0.012), rotation=(math.pi / 2, 0, 0), major_segments=42, minor_segments=8))
        objects.append(sphere("armor_circlet_gem", 0.028, mats["accent"], (0, 1.825, 0.160), segments=12))
    elif mode == "hat":
        objects.append(torus("armor_wide_hat_brim", 0.190, 0.012, mats["leather"], (0, 1.835, 0.000), rotation=(math.pi / 2, 0, 0), major_segments=52, minor_segments=8))
        objects.append(loft_axis("armor_hat_crown", "y", [
            {"coord": 1.82, "rx": 0.105, "rz": 0.090},
            {"coord": 2.02, "rx": 0.080, "rz": 0.070},
        ], mats["leather"], segments=36))
    elif mode in {"mask", "goggles"}:
        objects.append(loft_axis("armor_mask_face", "y", [
            {"coord": 1.64, "rx": 0.116, "rz": 0.050, "cz": 0.124},
            {"coord": 1.76, "rx": 0.150, "rz": 0.064, "cz": 0.128},
            {"coord": 1.85, "rx": 0.132, "rz": 0.055, "cz": 0.118},
        ], mats["dark_metal"], segments=34))
        for side in (-1, 1):
            objects.append(torus(f"armor_goggle_{side}", 0.035, 0.006, mats["accent"], (side * 0.052, 1.775, 0.165), rotation=(math.pi / 2, 0, 0), major_segments=18, minor_segments=6))
    else:
        objects.append(loft_axis("armor_helmet_cap", "y", [
            {"coord": 1.700, "rx": 0.170, "rz": 0.142, "cz": 0.010},
            {"coord": 1.760, "rx": 0.178, "rz": 0.150, "cz": 0.012},
            {"coord": 1.845, "rx": 0.162, "rz": 0.136, "cz": 0.004},
            {"coord": 1.930, "rx": 0.108, "rz": 0.090, "cz": -0.006},
        ], mats["metal"], segments=58))
        objects.append(loft_axis("armor_helmet_faceplate", "y", [
            {"coord": 1.630, "rx": 0.118, "rz": 0.060, "cz": 0.112},
            {"coord": 1.735, "rx": 0.148, "rz": 0.074, "cz": 0.120},
            {"coord": 1.855, "rx": 0.142, "rz": 0.068, "cz": 0.112},
        ], mats["dark_metal"], segments=34))
        if mode in {"horned", "crest", "spire"}:
            height = 0.55 if mode == "spire" else 0.34
            objects.append(loft_axis("armor_helm_crest", "y", [
                {"coord": 1.91, "rx": 0.045, "rz": 0.030},
                {"coord": 1.91 + height, "rx": 0.014, "rz": 0.010},
            ], mats["accent"], segments=18))
        if mode == "horned":
            for side in (-1, 1):
                horn = loft_axis(f"armor_horn_{side}", "x", [
                    {"coord": side * 0.120, "cy": 1.905, "cz": 0.000, "ry": 0.040, "rz": 0.030},
                    {"coord": side * 0.310, "cy": 2.020, "cz": -0.010, "ry": 0.014, "rz": 0.010},
                ], mats["ivory"], segments=16)
                objects.append(horn)
    return objects


def build_playable_armor_objects(manifest: dict, style: dict) -> list[bpy.types.Object]:
    mats = materials(style)
    slot = slot_from_manifest(manifest)
    archetype = style.get("archetype", "fighter")
    objects: list[bpy.types.Object] = []

    if slot == "head":
        objects.extend(build_head_slot(style, mats))
    elif slot == "shoulders":
        for side in (-1, 1):
            p = pauldron_shell(f"armor_pauldron_{side}", side, mats["metal"])
            objects.append(p)
            if archetype in {"tank", "bruiser", "mutant"}:
                spike = loft_axis(f"armor_pauldron_spike_{side}", "y", [
                    {"coord": 1.52, "cx": side * 0.44, "cz": 0.02, "rx": 0.045, "rz": 0.030},
                    {"coord": 1.78, "cx": side * 0.50, "cz": 0.02, "rx": 0.012, "rz": 0.008},
                ], mats["accent"], segments=12)
                objects.append(spike)
    elif slot == "chest":
        if archetype in {"caster", "rune_caster", "occult", "ritual", "bog_caster"}:
            objects.append(loft_axis("armor_robed_chest", "y", [
                {"coord": 0.82, "rx": 0.250, "rz": 0.128},
                {"coord": 1.08, "rx": 0.302, "rz": 0.156},
                {"coord": 1.38, "rx": 0.320, "rz": 0.164},
                {"coord": 1.58, "rx": 0.230, "rz": 0.116},
            ], mats["cloth"], segments=60))
        else:
            objects.append(torso_shell("armor_plate_cuirass", 0.98, 1.58, -math.pi, math.pi,
                                      lambda v: 0.235 + 0.076 * math.sin(v * math.pi),
                                      lambda v: 0.146 + 0.038 * math.sin(v * math.pi),
                                      mats["metal"], u_steps=72, v_steps=28, center_z=0.018, thickness=0.020))
            objects.append(torso_shell("armor_front_emblem", 1.12, 1.43, -0.44, 0.44,
                                      lambda _v: 0.120,
                                      lambda _v: 0.188,
                                      mats["accent"], u_steps=20, v_steps=8, center_z=0.035, thickness=0.008))
    elif slot == "hands":
        for side in (-1, 1):
            elbow = Vector((side * 0.430, 1.160, 0.080))
            wrist = Vector((side * 0.535, 1.000, 0.098))
            objects.append(tube_shell_between(f"armor_vambrace_{side}", tuple(elbow), tuple(wrist),
                                              lambda v: 0.074 - 0.012 * v,
                                              lambda v: 0.060 - 0.008 * v,
                                              -1.05, 1.42, mats["metal"], u_steps=28, v_steps=16, thickness=0.012))
            objects.append(loft_axis(f"armor_gauntlet_{side}", "x", [
                {"coord": side * 0.525, "cy": 0.970, "cz": 0.100, "ry": 0.052, "rz": 0.040},
                {"coord": side * 0.610, "cy": 0.920, "cz": 0.110, "ry": 0.044, "rz": 0.034},
            ], mats["leather"], segments=20))
    elif slot == "waist":
        objects.append(torso_shell("armor_belt", 0.90, 1.00, -1.42, 1.42,
                                  lambda _v: 0.315,
                                  lambda _v: 0.180,
                                  mats["leather"], u_steps=56, v_steps=6, center_z=0.018, thickness=0.018))
        for side in (-1, 1):
            objects.append(box_prism(f"armor_belt_pouch_{side}", (side * 0.245, 0.86, 0.150), (0.090, 0.130, 0.055), mats["leather"]))
    elif slot == "legs":
        objects.append(loft_axis("armor_lower_coat", "y", [
            {"coord": 0.18, "rx": 0.205, "rz": 0.118, "cz": 0.004},
            {"coord": 0.48, "rx": 0.245, "rz": 0.135, "cz": 0.000},
            {"coord": 0.76, "rx": 0.278, "rz": 0.148, "cz": -0.002},
            {"coord": 0.98, "rx": 0.300, "rz": 0.154, "cz": 0.000},
        ], mats["cloth" if archetype in {"caster", "rune_caster", "ritual", "occult", "bog_caster"} else "under"], segments=56))
        for side in (-1, 1):
            objects.append(tube_shell_between(f"armor_greave_{side}", (side * 0.135, 0.17, 0.018), (side * 0.135, 0.53, 0.012),
                                              lambda _v: 0.074,
                                              lambda _v: 0.062,
                                              -2.45, -0.70, mats["metal"], u_steps=26, v_steps=20, thickness=0.014))
    elif slot == "feet":
        for side in (-1, 1):
            objects.append(loft_axis(f"armor_boot_{side}", "y", [
                {"coord": 0.00, "cx": side * 0.135, "cz": 0.095, "rx": 0.086, "rz": 0.148},
                {"coord": 0.16, "cx": side * 0.135, "cz": 0.065, "rx": 0.094, "rz": 0.118},
                {"coord": 0.34, "cx": side * 0.135, "cz": 0.020, "rx": 0.070, "rz": 0.060},
            ], mats["leather"], segments=30))
    elif slot == "back":
        if archetype in {"ranger", "hunter", "skirmisher"}:
            objects.append(box_prism("armor_quiver", (-0.210, 1.18, -0.175), (0.115, 0.640, 0.095), mats["leather"], rot_z=-0.28))
            for i in range(4):
                objects.append(superellipse_bar(f"armor_arrow_{i}", "y", (-0.210 + i * 0.018, 1.52, -0.235),
                                                0.55, 0.004, 0.004, mats["accent"], segments=8, rings=4))
        elif archetype in {"engineer", "occult", "ritual", "bog_caster"}:
            objects.append(box_prism("armor_backpack_core", (0, 1.16, -0.185), (0.340, 0.520, 0.125), mats["leather"]))
            objects.append(torus("armor_back_focus", 0.112, 0.010, mats["accent"], (0, 1.35, -0.260), rotation=(math.pi / 2, 0, 0), major_segments=30, minor_segments=8))
        else:
            objects.append(cloth_panel("armor_cape_back", 0.0, 1.48, 0.34, -0.185, 0.260, 0.420, mats["cloth"], u_steps=18, v_steps=32, wave=0.018, thickness=0.006))
    elif slot == "tabard":
        objects.append(cloth_panel("armor_tabard_front", 0.0, 1.22, 0.32, 0.192, 0.180, 0.245, mats["cloth"], u_steps=16, v_steps=30, wave=0.010, thickness=0.006))
        objects.append(cloth_panel("armor_tabard_back", 0.0, 1.16, 0.42, -0.172, 0.145, 0.205, mats["cloth2" if "cloth2" in mats else "cloth"], u_steps=14, v_steps=24, wave=0.008, thickness=0.006))
        objects.append(superellipse_bar("armor_tabard_trim", "y", (0, 0.78, 0.201), 0.82, 0.010, 0.006, mats["accent"], segments=10, rings=5))

    scale_objects(objects, style["bodyScale"])
    return objects


def build_playable_armor_module(manifest: dict, style: dict) -> tuple[list[bpy.types.Object], bpy.types.Object, list[bpy.types.Object]]:
    objects = build_playable_armor_objects(manifest, style)
    add_manifest_metadata(objects, manifest)
    armature = create_humanoid_rig(objects, style["bodyScale"], rig_profile="default")
    add_manifest_metadata([armature], manifest)
    return objects, armature, []


def build_manifest_character(manifest: dict) -> tuple[list[bpy.types.Object], bpy.types.Object, list[bpy.types.Object]]:
    profile = manifest.get("runtime", {}).get("profileKey", "human_devout_guardian")
    playable_style = playable_profile_style(profile)
    if playable_style:
        return build_playable_character(manifest, playable_style)

    style = PROFILE_STYLES.get(profile, PROFILE_STYLES["human_devout_guardian"])
    mats = materials(style)
    objects: list[bpy.types.Object] = []

    # Cohesive underbody: broad dark-fantasy silhouette, no stacked loose torso boxes.
    objects.append(loft_axis("chr_under_torso", "y", [
        {"coord": 0.82, "rx": 0.220, "rz": 0.118},
        {"coord": 1.02, "rx": 0.258, "rz": 0.142},
        {"coord": 1.26, "rx": 0.302, "rz": 0.162},
        {"coord": 1.48, "rx": 0.318, "rz": 0.158},
        {"coord": 1.60, "rx": 0.230, "rz": 0.118},
    ], mats["under"], segments=72))
    objects.append(loft_axis("chr_under_hips", "y", [
        {"coord": 0.20, "rx": 0.245, "rz": 0.125},
        {"coord": 0.52, "rx": 0.300, "rz": 0.145},
        {"coord": 0.86, "rx": 0.305, "rz": 0.152},
        {"coord": 1.02, "rx": 0.255, "rz": 0.135},
    ], mats["under"], segments=64))

    # Head, face, and headgear. Headgear hides the weak bald sculpt problem.
    objects.append(loft_axis("chr_neck", "y", [
        {"coord": 1.52, "rx": 0.070, "rz": 0.058},
        {"coord": 1.66, "rx": 0.076, "rz": 0.064},
    ], mats["skin"], segments=36))
    objects.append(loft_axis("chr_head", "y", [
        {"coord": 1.66, "rx": 0.105, "rz": 0.090, "cz": 0.012},
        {"coord": 1.75, "rx": 0.148, "rz": 0.125, "cz": 0.030},
        {"coord": 1.84, "rx": 0.144, "rz": 0.118, "cz": 0.020},
        {"coord": 1.92, "rx": 0.095, "rz": 0.080, "cz": -0.005},
    ], mats["skin"], segments=64))
    if style["helmet"]:
        objects.append(loft_axis("chr_helmet_cap", "y", [
            {"coord": 1.705, "rx": 0.170, "rz": 0.142, "cz": 0.010},
            {"coord": 1.760, "rx": 0.178, "rz": 0.150, "cz": 0.012},
            {"coord": 1.845, "rx": 0.162, "rz": 0.136, "cz": 0.004},
            {"coord": 1.930, "rx": 0.108, "rz": 0.090, "cz": -0.006},
        ], mats["metal"], segments=72))
        objects.append(loft_axis("chr_helmet_faceplate", "y", [
            {"coord": 1.630, "rx": 0.118, "rz": 0.060, "cz": 0.112},
            {"coord": 1.735, "rx": 0.148, "rz": 0.074, "cz": 0.120},
            {"coord": 1.855, "rx": 0.142, "rz": 0.068, "cz": 0.112},
        ], mats["dark_metal"], segments=48))
        objects.append(box_prism("chr_visor_shadow", (0.0, 1.785, 0.178),
                                 (0.235, 0.040, 0.014), mats["shadow"]))
    elif style["hood"]:
        objects.append(loft_axis("chr_nose", "z", [
            {"coord": 0.132, "cx": 0.0, "cy": 1.775, "rx": 0.020, "ry": 0.035},
            {"coord": 0.190, "cx": 0.0, "cy": 1.748, "rx": 0.028, "ry": 0.024},
        ], mats["skin"], segments=20))
        for side in (-1, 1):
            objects.append(loft_axis(f"chr_eye_{side}", "z", [
                {"coord": 0.145, "cx": side * 0.050, "cy": 1.795, "rx": 0.022, "ry": 0.012},
                {"coord": 0.160, "cx": side * 0.050, "cy": 1.795, "rx": 0.018, "ry": 0.010},
            ], mats["eye"], segments=16))
            objects.append(superellipse_bar(f"chr_brow_{side}", "x", (side * 0.052, 1.825, 0.145),
                                            0.065, 0.009, 0.008, mats["hair"], segments=12))
        objects.append(loft_axis("chr_hood_cowl", "y", [
            {"coord": 1.55, "rx": 0.190, "rz": 0.130, "cz": -0.012},
            {"coord": 1.72, "rx": 0.205, "rz": 0.160, "cz": -0.010},
            {"coord": 1.90, "rx": 0.158, "rz": 0.128, "cz": -0.020},
            {"coord": 1.99, "rx": 0.065, "rz": 0.060, "cz": -0.030},
        ], mats["cloth"], segments=72))

    # Arms and legs are close to the body and weighted to the canonical rig.
    for side in (-1, 1):
        sx = side
        objects.append(loft_axis(f"chr_upper_arm_{side}", "x", [
            {"coord": sx * 0.290, "cy": 1.405, "cz": 0.035, "ry": 0.078, "rz": 0.064},
            {"coord": sx * 0.430, "cy": 1.230, "cz": 0.060, "ry": 0.068, "rz": 0.055},
        ], mats["under"], segments=36))
        objects.append(loft_axis(f"chr_forearm_{side}", "x", [
            {"coord": sx * 0.430, "cy": 1.230, "cz": 0.060, "ry": 0.066, "rz": 0.054},
            {"coord": sx * 0.540, "cy": 1.000, "cz": 0.086, "ry": 0.052, "rz": 0.046},
        ], mats["under"], segments=36))
        objects.append(loft_axis(f"chr_hand_{side}", "x", [
            {"coord": sx * 0.535, "cy": 0.980, "cz": 0.094, "ry": 0.045, "rz": 0.036},
            {"coord": sx * 0.595, "cy": 0.930, "cz": 0.105, "ry": 0.038, "rz": 0.030},
        ], mats["leather"], segments=24))
        objects.append(loft_axis(f"chr_thigh_{side}", "y", [
            {"coord": 0.90, "cx": sx * 0.135, "cz": 0.010, "rx": 0.085, "rz": 0.070},
            {"coord": 0.55, "cx": sx * 0.135, "cz": 0.010, "rx": 0.074, "rz": 0.062},
        ], mats["under"], segments=40))
        objects.append(loft_axis(f"chr_shin_{side}", "y", [
            {"coord": 0.53, "cx": sx * 0.135, "cz": 0.010, "rx": 0.066, "rz": 0.058},
            {"coord": 0.17, "cx": sx * 0.135, "cz": 0.018, "rx": 0.056, "rz": 0.050},
        ], mats["under"], segments=36))
        objects.append(loft_axis(f"chr_boot_{side}", "y", [
            {"coord": 0.00, "cx": sx * 0.135, "cz": 0.095, "rx": 0.075, "rz": 0.135},
            {"coord": 0.14, "cx": sx * 0.135, "cz": 0.065, "rx": 0.084, "rz": 0.110},
            {"coord": 0.30, "cx": sx * 0.135, "cz": 0.020, "rx": 0.064, "rz": 0.055},
        ], mats["leather"], segments=40))

    # Armor: broad silhouette-first shapes, restrained decoration, no loose papers.
    objects.append(torso_shell("chr_plate_full_cuirass", 0.98, 1.58, -math.pi, math.pi,
                               lambda v: 0.235 + 0.076 * math.sin(v * math.pi),
                               lambda v: 0.146 + 0.038 * math.sin(v * math.pi),
                               mats["metal"], u_steps=96, v_steps=36, center_z=0.018, thickness=0.020))
    objects.append(torso_shell("chr_plate_front_overlay", 1.02, 1.55, -1.35, 1.35,
                               lambda v: 0.205 + 0.068 * math.sin(v * math.pi),
                               lambda v: 0.166 + 0.032 * math.sin(v * math.pi),
                               mats["metal"], u_steps=64, v_steps=28, center_z=0.030, thickness=0.022))
    for idx, y in enumerate([1.06, 1.155, 1.25]):
        objects.append(torso_shell(f"chr_abdominal_lame_{idx}", y, y + 0.055, -1.05, 1.05,
                                   lambda _v, i=idx: 0.205 + 0.018 * i,
                                   lambda _v: 0.205,
                                   mats["dark_metal"], u_steps=44, v_steps=5, center_z=0.035, thickness=0.010))
    objects.append(torso_shell("chr_gorget", 1.52, 1.66, -1.22, 1.22,
                               lambda v: 0.185 + 0.060 * math.sin(v * math.pi),
                               lambda v: 0.105 + 0.030 * math.sin(v * math.pi),
                               mats["dark_metal"], u_steps=48, v_steps=12, center_z=0.015, thickness=0.018))
    objects.append(torso_shell("chr_belt", 0.91, 1.00, -1.42, 1.42,
                               lambda _v: 0.315,
                               lambda _v: 0.180,
                               mats["leather"], u_steps=64, v_steps=6, center_z=0.018, thickness=0.018))
    objects.append(loft_axis("chr_lower_coat", "y", [
        {"coord": 0.18, "rx": 0.205, "rz": 0.118, "cz": 0.004},
        {"coord": 0.48, "rx": 0.245, "rz": 0.135, "cz": 0.000},
        {"coord": 0.76, "rx": 0.278, "rz": 0.148, "cz": -0.002},
        {"coord": 0.98, "rx": 0.300, "rz": 0.154, "cz": 0.000},
    ], mats["under"], segments=64))

    for side in (-1, 1):
        objects.append(pauldron_shell(f"chr_pauldron_{side}", side, mats["metal"]))
        shoulder = Vector((side * 0.305, 1.360, 0.060))
        elbow = Vector((side * 0.430, 1.160, 0.080))
        wrist = Vector((side * 0.535, 1.000, 0.098))
        objects.append(tube_shell_between(f"chr_vambrace_{side}", tuple(elbow), tuple(wrist),
                                          lambda v: 0.074 - 0.012 * v,
                                          lambda v: 0.060 - 0.008 * v,
                                          -1.05, 1.42, mats["metal"], u_steps=34, v_steps=18, thickness=0.012))
        objects.append(tube_shell_between(f"chr_upper_plate_{side}", tuple(shoulder), tuple(elbow),
                                          lambda v: 0.085 - 0.010 * v,
                                          lambda v: 0.072 - 0.008 * v,
                                          -1.15, 1.38, mats["dark_metal"], u_steps=34, v_steps=16, thickness=0.012))
        objects.append(tube_shell_between(f"chr_greave_{side}", (side * 0.135, 0.17, 0.018), (side * 0.135, 0.53, 0.012),
                                          lambda _v: 0.074,
                                          lambda _v: 0.062,
                                          -2.45, -0.70, mats["metal"], u_steps=32, v_steps=24, thickness=0.014))

    anchors: list[bpy.types.Object] = []
    for anchor in manifest.get("attachments", []):
        pos = tuple(anchor.get("position", [0, 0, 0]))
        anchors.append(add_anchor(anchor["name"], anchor["parent"], pos, manifest))

    add_manifest_metadata(objects, manifest)
    armature = create_humanoid_rig(objects, (1.0, 1.0, 1.0), rig_profile="default")
    add_manifest_metadata([armature, *anchors], manifest)
    apply_animations(armature, ACTIONS)
    return objects, armature, anchors


def bounds_for(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    min_v = Vector((math.inf, math.inf, math.inf))
    max_v = Vector((-math.inf, -math.inf, -math.inf))
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            min_v.x = min(min_v.x, world.x)
            min_v.y = min(min_v.y, world.y)
            min_v.z = min(min_v.z, world.z)
            max_v.x = max(max_v.x, world.x)
            max_v.y = max(max_v.y, world.y)
            max_v.z = max(max_v.z, world.z)
    return min_v, max_v


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_previews(artifact_dir: str | None, artifact_key: str, objects: list[bpy.types.Object]) -> list[str]:
    if not artifact_dir:
        return []
    out_dir = Path(artifact_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for obj in list(bpy.context.scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)

    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.030, 0.032, 0.034, 1.0)
        bg.inputs["Strength"].default_value = 0.75

    for name, loc, energy, size in [
        ("preview_key", (-3.2, -4.5, 4.0), 780, 4.0),
        ("preview_fill", (3.5, -3.0, 2.4), 140, 5.5),
        ("preview_rim", (0.3, 3.5, 3.2), 360, 2.8),
    ]:
        data = bpy.data.lights.new(name, type="AREA")
        data.energy = energy
        data.size = size
        light = bpy.data.objects.new(name, data)
        light.location = loc
        bpy.context.collection.objects.link(light)

    scene = bpy.context.scene
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1300
    scene.render.film_transparent = False
    try:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 48
    except Exception:
        scene.render.engine = "BLENDER_EEVEE_NEXT"

    cam_data = bpy.data.cameras.new("preview_camera")
    cam = bpy.data.objects.new("preview_camera", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    cam_data.lens = 58

    min_v, max_v = bounds_for(objects)
    center = (min_v + max_v) * 0.5
    size = max_v - min_v
    radius = max(size.x, size.y, size.z * 0.70) * 2.05 + 0.75
    target = center + Vector((0.0, 0.0, size.z * 0.05))
    views = {
        "front": Vector((center.x, center.y - radius, center.z + size.z * 0.10)),
        "side": Vector((center.x + radius, center.y, center.z + size.z * 0.10)),
        "back": Vector((center.x, center.y + radius, center.z + size.z * 0.10)),
        "iso": Vector((center.x + radius * 0.75, center.y - radius, center.z + radius * 0.45)),
    }
    written: list[str] = []
    for suffix, location in views.items():
        cam.location = location
        look_at(cam, target)
        path = out_dir / f"{artifact_key}_{suffix}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        written.append(str(path))
    return written


def export_character(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalize_y_up_scene_to_blender_z_up()
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        export_animations=True,
        export_skins=True,
        export_extras=True,
        export_apply=True,
        export_yup=True,
        export_draco_mesh_compression_enable=False,
    )


def write_character_qc(
    manifest: dict,
    output_path: Path,
    objects: list[bpy.types.Object],
    previews: list[str],
    artifact_dir: str | None,
) -> None:
    meshes = []
    total_tris = 0
    skinned = 0
    min_v, max_v = bounds_for(objects)
    for obj in objects:
        if obj.type != "MESH":
            continue
        tris = sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)
        total_tris += tris
        has_armature = any(mod.type == "ARMATURE" for mod in obj.modifiers)
        has_weights = any(vertex.groups for vertex in obj.data.vertices)
        if has_armature and has_weights:
            skinned += 1
        meshes.append({
            "name": obj.name,
            "verts": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "tris": tris,
            "materials": len(obj.data.materials),
            "skinned": bool(has_armature and has_weights),
            "assetId": obj.get("assetId"),
            "assetSlot": obj.get("assetSlot"),
        })

    required_clips = manifest.get("rigging", {}).get("requiredClips") or []
    available_clips = sorted(action.name for action in bpy.data.actions)
    missing_clips = [clip for clip in required_clips if clip not in available_clips]
    qc = manifest.get("qc", {})
    is_character = manifest.get("category") == "character"
    expected_height = qc.get("expectedHeightM")
    runtime_min = Vector((min_v.x, min_v.z, -max_v.y))
    runtime_max = Vector((max_v.x, max_v.z, -min_v.y))
    runtime_height = runtime_max.y - runtime_min.y
    checks = {
        "grounded": abs(runtime_min.y) <= qc.get("groundToleranceM", 0.03) if is_character else True,
        "heightWithinTolerance": abs(runtime_height - expected_height) <= 0.22 if expected_height else True,
        "allMeshesSkinned": skinned == len(meshes) if qc.get("requiresSkinnedMeshes", True) else True,
        "requiredClipsPresent": len(missing_clips) == 0,
        "meshObjectBudget": len(meshes) <= qc.get("maxMeshObjects", 64),
        "previewWritten": bool(previews) if qc.get("requiresPreview", False) else True,
        "fileSizeBudget": (output_path.stat().st_size / (1024 * 1024)) <= qc.get("maxFileSizeMb", 12),
    }
    report = {
        "assetId": manifest["assetId"],
        "category": manifest["category"],
        "model": manifest["output"]["model"],
        "fileSizeBytes": output_path.stat().st_size if output_path.exists() else 0,
        "boundsYUpMeters": {
            "min": [round(runtime_min.x, 4), round(runtime_min.y, 4), round(runtime_min.z, 4)],
            "max": [round(runtime_max.x, 4), round(runtime_max.y, 4), round(runtime_max.z, 4)],
            "height": round(runtime_height, 4),
        },
        "meshCount": len(meshes),
        "skinnedMeshCount": skinned,
        "totalTris": total_tris,
        "availableClips": available_clips,
        "missingRequiredClips": missing_clips,
        "previewImages": [repo_relative_path(path) for path in previews],
        "artifactDir": repo_relative_path(artifact_dir),
        "manifestVersion": manifest["version"],
        "checks": checks,
        "qcPassed": all(checks.values()),
        "meshes": meshes,
    }
    output_path.with_suffix(".qc.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["qcPassed"]:
        failed = ", ".join(name for name, ok in checks.items() if not ok)
        raise RuntimeError(f"Character QC failed for {manifest['assetId']}: {failed}")


def generate_manifest_character(manifest: dict, output_path: Path, artifact_dir: str | None) -> None:
    clear_scene()
    objects, _armature, _anchors = build_manifest_character(manifest)
    export_character(output_path)
    previews = render_previews(artifact_dir, output_path.stem, objects)
    write_character_qc(manifest, output_path, objects, previews, artifact_dir)


def generate_manifest_armor_module(manifest: dict, output_path: Path, artifact_dir: str | None) -> None:
    profile = manifest.get("generator", {}).get("preset") or manifest.get("runtime", {}).get("profileKey")
    style = playable_profile_style(profile or "")
    if not style:
        raise RuntimeError(f"Unknown playable armor profile: {profile}")
    clear_scene()
    objects, _armature, _anchors = build_playable_armor_module(manifest, style)
    export_character(output_path)
    write_character_qc(manifest, output_path, objects, [], artifact_dir)
