"""
Blender headless character generator for War-js.

Invocation:
    blender --background --python generate_character.py -- \\
        --race empire \\
        --career "Warrior Priest" \\
        --output /absolute/path/to/public/assets/models/character_empire_warrior_priest.glb \\
        --spec /absolute/path/to/data/character_spec.json

Requires Blender 3.6+ (tested on 4.x).
"""

import sys
import os
import json
import argparse
import math

import bpy
import bmesh
from mathutils import Vector, Color


# ─────────────────────────────────────────────────────────────────────────────
# Argument parsing  (Blender passes script args after the -- separator)
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    argv = sys.argv
    try:
        idx = argv.index("--")
        argv = argv[idx + 1:]
    except ValueError:
        argv = []

    parser = argparse.ArgumentParser(description="WAR character GLB generator")
    parser.add_argument("--race",   required=True,
                        choices=["empire", "dwarf", "high_elf", "chaos", "greenskin", "dark_elf"])
    parser.add_argument("--career", required=True, help="Full career name e.g. 'Warrior Priest'")
    parser.add_argument("--output", required=True, help="Absolute path for output .glb")
    parser.add_argument("--spec",   required=True, help="Path to character_spec.json")
    return parser.parse_args(argv)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def hex_to_linear(hex_color: str) -> tuple:
    """Convert #rrggbb hex to Blender linear RGB tuple (r, g, b, 1.0)."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    # sRGB → linear approximation
    def to_lin(c): return c ** 2.2
    return (to_lin(r), to_lin(g), to_lin(b), 1.0)


def make_material(name: str, hex_color: str, roughness=0.6, metallic=0.0,
                  emissive_hex: str = None) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex_to_linear(hex_color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emissive_hex:
        bsdf.inputs["Emission Color"].default_value = hex_to_linear(emissive_hex)
        bsdf.inputs["Emission Strength"].default_value = 1.5
    return mat


def add_mesh_obj(name: str, mesh: bpy.types.Mesh,
                 mat: bpy.types.Material = None,
                 location=(0, 0, 0)) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    if mat:
        obj.data.materials.append(mat)
    return obj


def create_box(name: str, size: tuple, mat: bpy.types.Material,
               location=(0, 0, 0)) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    return add_mesh_obj(name, mesh, mat, location)


def create_cylinder(name: str, radius: float, depth: float, segments: int,
                    mat: bpy.types.Material, location=(0, 0, 0),
                    rotation=(0, 0, 0)) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cylinder(bm, cap_ends=True, cap_tris=False,
                               segments=segments, radius1=radius, radius2=radius,
                               depth=depth)
    bm.to_mesh(mesh)
    bm.free()
    obj = add_mesh_obj(name, mesh, mat, location)
    obj.rotation_euler = rotation
    return obj


def create_sphere(name: str, radius: float, mat: bpy.types.Material,
                  location=(0, 0, 0)) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=radius)
    bm.to_mesh(mesh)
    bm.free()
    return add_mesh_obj(name, mesh, mat, location)


# ─────────────────────────────────────────────────────────────────────────────
# Scene setup
# ─────────────────────────────────────────────────────────────────────────────

def clear_scene() -> None:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes) + list(bpy.data.materials) + \
                  list(bpy.data.armatures) + list(bpy.data.actions):
        bpy.data.batch_remove([block])


# ─────────────────────────────────────────────────────────────────────────────
# Body builder
# ─────────────────────────────────────────────────────────────────────────────

def build_body(race_spec: dict) -> list:
    """Build base humanoid body mesh objects. Returns list of created objects."""
    sx, sy, sz = race_spec["bodyScale"]
    skin_mat  = make_material("skin",  race_spec["skinColor"],  roughness=0.8)
    armor_mat = make_material("armor", race_spec["armorColor"], roughness=0.4, metallic=0.6)
    boot_mat  = make_material("boots", "#2a1c0a", roughness=0.7)

    objects = []

    # Head
    head = create_sphere("head", 0.14 * sx,  skin_mat,
                         location=(0, 1.78 * sy, 0))
    objects.append(head)

    # Neck
    neck = create_cylinder("neck", 0.065 * sx, 0.12 * sy, 8, skin_mat,
                            location=(0, 1.64 * sy, 0))
    objects.append(neck)

    # Torso
    torso = create_box("torso", (0.36 * sx, 0.46 * sy, 0.2 * sz),
                        armor_mat, location=(0, 1.27 * sy, 0))
    objects.append(torso)

    # Hips
    hips = create_box("hips", (0.32 * sx, 0.22 * sy, 0.18 * sz),
                       armor_mat, location=(0, 0.95 * sy, 0))
    objects.append(hips)

    # Upper arms
    for side, x_sign in [("L", 1), ("R", -1)]:
        ua = create_cylinder(f"upper_arm_{side}", 0.07 * sx, 0.26 * sy, 8, armor_mat,
                             location=(x_sign * 0.4 * sx, 1.42 * sy, 0),
                             rotation=(0, 0, math.pi / 2))
        objects.append(ua)

    # Forearms
    for side, x_sign in [("L", 1), ("R", -1)]:
        fa = create_cylinder(f"forearm_{side}", 0.055 * sx, 0.24 * sy, 8, armor_mat,
                             location=(x_sign * 0.64 * sx, 1.42 * sy, 0),
                             rotation=(0, 0, math.pi / 2))
        objects.append(fa)

    # Hands
    for side, x_sign in [("L", 1), ("R", -1)]:
        hand = create_sphere(f"hand_{side}", 0.07 * sx, skin_mat,
                             location=(x_sign * 0.83 * sx, 1.42 * sy, 0))
        objects.append(hand)

    # Thighs
    for side, x_sign in [("L", 1), ("R", -1)]:
        thigh = create_cylinder(f"thigh_{side}", 0.085 * sx, 0.38 * sy, 8, armor_mat,
                                location=(x_sign * 0.13 * sx, 0.70 * sy, 0))
        objects.append(thigh)

    # Shins
    for side, x_sign in [("L", 1), ("R", -1)]:
        shin = create_cylinder(f"shin_{side}", 0.07 * sx, 0.34 * sy, 8, armor_mat,
                               location=(x_sign * 0.13 * sx, 0.32 * sy, 0))
        objects.append(shin)

    # Feet/boots
    for side, x_sign in [("L", 1), ("R", -1)]:
        boot = create_box(f"boot_{side}", (0.12 * sx, 0.12 * sy, 0.22 * sz),
                          boot_mat,
                          location=(x_sign * 0.13 * sx, 0.06 * sy, 0.04 * sz))
        objects.append(boot)

    return objects


# ─────────────────────────────────────────────────────────────────────────────
# Face builder
# ─────────────────────────────────────────────────────────────────────────────

def build_face(race_spec: dict) -> list:
    sx, sy, _ = race_spec["bodyScale"]
    objects = []

    iris_mat = make_material("iris",  race_spec["irisColor"],  roughness=0.1)
    white_mat = make_material("sclera", "#f0ece4", roughness=0.2)

    # Eyes
    for side, x_sign in [("L", 1), ("R", -1)]:
        sclera = create_sphere(f"eye_white_{side}", 0.034 * sx, white_mat,
                               location=(x_sign * 0.055 * sx, 1.795 * sy, 0.118))
        iris   = create_sphere(f"eye_iris_{side}",  0.024 * sx, iris_mat,
                               location=(x_sign * 0.055 * sx, 1.797 * sy, 0.13))
        objects.extend([sclera, iris])

    # Nose bridge
    nose_mat = make_material("nose", race_spec["skinColor"], roughness=0.85)
    nose = create_cylinder("nose", 0.022 * sx, 0.055 * sy, 6, nose_mat,
                           location=(0, 1.75 * sy, 0.13),
                           rotation=(math.pi / 2, 0, 0))
    objects.append(nose)

    # Beard (dwarves always have one)
    if race_spec.get("beard"):
        beard_color = race_spec.get("beardColor", race_spec["hairColor"])
        beard_mat = make_material("beard", beard_color, roughness=0.9)
        beard = create_box("beard", (0.2 * sx, 0.18 * sy, 0.12),
                           beard_mat,
                           location=(0, 1.64 * sy, 0.08))
        objects.append(beard)

    # Elf ears
    if race_spec.get("elfEars"):
        ear_mat = make_material("ears", race_spec["skinColor"], roughness=0.75)
        for side, x_sign in [("L", 1), ("R", -1)]:
            ear = create_box(f"ear_{side}", (0.04, 0.12 * sy, 0.04),
                             ear_mat,
                             location=(x_sign * 0.16 * sx, 1.78 * sy, 0.01))
            ear.rotation_euler = (0, x_sign * 0.4, 0)
            objects.append(ear)
    else:
        # Round human ears
        ear_mat = make_material("ears", race_spec["skinColor"], roughness=0.75)
        for side, x_sign in [("L", 1), ("R", -1)]:
            ear = create_sphere(f"ear_{side}", 0.045 * sx, ear_mat,
                                location=(x_sign * 0.15 * sx, 1.78 * sy, 0))
            objects.append(ear)

    return objects


# ─────────────────────────────────────────────────────────────────────────────
# Armor / equipment builder
# ─────────────────────────────────────────────────────────────────────────────

def build_armor(race_spec: dict, career_spec: dict) -> list:
    sx, sy, sz = race_spec["bodyScale"]
    armor_hex = career_spec.get("armorColorOverride") or race_spec["armorColor"]
    trim_hex  = race_spec["trimColor"]
    objects   = []

    armor_mat = make_material("c_armor", armor_hex, roughness=0.4, metallic=0.7)
    trim_mat  = make_material("c_trim",  trim_hex,  roughness=0.3, metallic=0.8)

    # Pauldrons (shoulder plates)
    for side, x_sign in [("L", 1), ("R", -1)]:
        p = create_box(f"pauldron_{side}",
                       (0.18 * sx, 0.12 * sy, 0.18 * sz),
                       armor_mat,
                       location=(x_sign * 0.42 * sx, 1.52 * sy, 0))
        objects.append(p)

    # Breastplate trim strip
    bp = create_box("breastplate_trim",
                    (0.32 * sx, 0.04 * sy, 0.04 * sz),
                    trim_mat,
                    location=(0, 1.32 * sy, 0.12 * sz))
    objects.append(bp)

    # Helmet
    helm_style = career_spec.get("helmetStyle", "open_face")
    objects.extend(_build_helmet(race_spec, career_spec, helm_style,
                                 armor_mat, trim_mat))

    # Robe overlay (casters / robed careers)
    robe_color = career_spec.get("robeColor")
    if robe_color:
        robe_mat = make_material("robe", robe_color, roughness=0.85)
        robe = create_box("robe",
                          (0.38 * sx, 0.55 * sy, 0.1 * sz),
                          robe_mat,
                          location=(0, 1.1 * sy, -0.06 * sz))
        objects.append(robe)

    # Weapon
    objects.extend(_build_weapon(race_spec, career_spec, trim_mat))

    return objects


def _build_helmet(race_spec, career_spec, style, armor_mat, trim_mat):
    sx, sy, _ = race_spec["bodyScale"]
    objects = []

    if style == "none":
        return objects

    if style == "hood":
        hood_color = career_spec.get("robeColor") or race_spec["armorColor"]
        hood_mat = make_material("hood", hood_color, roughness=0.85)
        h = create_sphere("helmet_hood", 0.17 * sx, hood_mat,
                          location=(0, 1.82 * sy, -0.02))
        objects.append(h)

    elif style == "full_visor":
        h = create_sphere("helmet_full", 0.17 * sx, armor_mat,
                          location=(0, 1.82 * sy, 0))
        visor = create_box("visor", (0.22 * sx, 0.06 * sy, 0.03),
                           trim_mat, location=(0, 1.77 * sy, 0.13))
        objects.extend([h, visor])

    elif style == "open_face":
        h = create_box("helmet_open", (0.28 * sx, 0.22 * sy, 0.24),
                       armor_mat, location=(0, 1.84 * sy, 0))
        objects.append(h)

    elif style == "brimhat":
        crown = create_cylinder("hat_crown", 0.14 * sx, 0.22 * sy, 8, armor_mat,
                                location=(0, 1.89 * sy, 0))
        brim = create_cylinder("hat_brim", 0.24 * sx, 0.03 * sy, 12, armor_mat,
                               location=(0, 1.80 * sy, 0))
        objects.extend([crown, brim])

    elif style in ("full_rune", "open_rune"):
        h = create_sphere("helmet_rune", 0.17 * sx, armor_mat,
                          location=(0, 1.82 * sy, 0))
        rune = create_box("rune_plate", (0.1 * sx, 0.08 * sy, 0.02),
                          trim_mat, location=(0, 1.85 * sy, 0.15))
        objects.extend([h, rune])

    elif style == "mohawk":
        h = create_sphere("helmet_bare", 0.155 * sx, armor_mat,
                          location=(0, 1.80 * sy, 0))
        hair_mat = make_material("mohawk_hair", race_spec["hairColor"], roughness=0.9)
        crest = create_box("mohawk_crest", (0.04 * sx, 0.22 * sy, 0.06),
                           hair_mat, location=(0, 1.88 * sy, 0))
        objects.extend([h, crest])

    elif style == "horned_full":
        h = create_sphere("helmet_chaos", 0.18 * sx, armor_mat,
                          location=(0, 1.82 * sy, 0))
        for side, x_sign in [("L", 1), ("R", -1)]:
            horn = create_cylinder(f"horn_{side}", 0.04 * sx, 0.22 * sy, 6, armor_mat,
                                   location=(x_sign * 0.14 * sx, 1.92 * sy, 0),
                                   rotation=(0, x_sign * 0.4, 0))
            objects.append(horn)
        objects.append(h)

    elif style == "iron_bowl":
        h = create_sphere("helmet_bowl", 0.16 * sx, armor_mat,
                          location=(0, 1.81 * sy, 0))
        objects.append(h)

    elif style == "bone_crown":
        crown_mat = make_material("bone", "#d8c890", roughness=0.7)
        for i in range(5):
            angle = (i / 5) * math.pi * 2
            spike = create_cylinder(f"crown_spike_{i}", 0.025 * sx, 0.1 * sy, 4,
                                    crown_mat,
                                    location=(math.cos(angle) * 0.14 * sx,
                                              1.88 * sy,
                                              math.sin(angle) * 0.08))
            objects.append(spike)

    elif style == "spired_full":
        h = create_sphere("helmet_spired", 0.17 * sx, armor_mat,
                          location=(0, 1.82 * sy, 0))
        spire = create_cylinder("spire", 0.03 * sx, 0.18 * sy, 4, trim_mat,
                                location=(0, 1.96 * sy, 0))
        objects.extend([h, spire])

    elif style in ("goggle_cap", "half_helm", "tall_crest", "horned_hood",
                   "open_skull", "open_spired"):
        # Generic fallback — plain dome
        h = create_sphere("helmet_generic", 0.16 * sx, armor_mat,
                          location=(0, 1.82 * sy, 0))
        objects.append(h)

    return objects


def _build_weapon(race_spec, career_spec, trim_mat):
    sx, sy, sz = race_spec["bodyScale"]
    weapon = career_spec.get("weapon", "sword")
    objects = []

    metal_mat = make_material("weapon_metal", "#909090", roughness=0.3, metallic=0.9)
    wood_mat  = make_material("weapon_wood",  "#5a3818", roughness=0.8)
    blade_mat = make_material("weapon_blade", "#c8c8d8", roughness=0.15, metallic=1.0)

    # All weapons attach at right hand position
    hand_x = -0.83 * sx
    hand_y =  1.42 * sy

    if weapon == "sword":
        grip = create_cylinder("grip", 0.025, 0.22, 6, wood_mat,
                               location=(hand_x, hand_y - 0.16, 0.04))
        blade = create_box("blade", (0.04, 0.54 * sy, 0.008), blade_mat,
                           location=(hand_x, hand_y + 0.14, 0.04))
        guard = create_box("guard", (0.14 * sx, 0.03, 0.02), metal_mat,
                           location=(hand_x, hand_y - 0.02, 0.04))
        objects.extend([grip, blade, guard])

    elif weapon == "hammer":
        haft = create_cylinder("haft", 0.022, 0.42 * sy, 6, wood_mat,
                               location=(hand_x, hand_y + 0.05, 0))
        head = create_box("hammer_head", (0.08 * sx, 0.1 * sy, 0.06), metal_mat,
                          location=(hand_x, hand_y + 0.28, 0))
        objects.extend([haft, head])

    elif weapon == "staff":
        shaft = create_cylinder("shaft", 0.02, 0.72 * sy, 6, wood_mat,
                                location=(hand_x, hand_y + 0.16, 0))
        tip_mat = make_material("staff_tip", "#ffd040", roughness=0.1,
                                emissive_hex="#ffd040")
        tip = create_sphere("staff_tip", 0.05, tip_mat,
                            location=(hand_x, hand_y + 0.54, 0))
        objects.extend([shaft, tip])

    elif weapon in ("axe", "choppa"):
        haft = create_cylinder("axe_haft", 0.022, 0.38 * sy, 6, wood_mat,
                               location=(hand_x, hand_y + 0.03, 0))
        blade = create_box("axe_blade", (0.12 * sx, 0.18 * sy, 0.015), blade_mat,
                           location=(hand_x - 0.06 * sx, hand_y + 0.22, 0))
        objects.extend([haft, blade])

    elif weapon in ("dual_axes", "dual_choppas", "dual_daggers", "pistol_sword"):
        # Main hand
        haft = create_cylinder("axe_haft_R", 0.022, 0.32 * sy, 6, wood_mat,
                               location=(hand_x, hand_y + 0.03, 0))
        blade = create_box("axe_blade_R", (0.1 * sx, 0.16 * sy, 0.012), blade_mat,
                           location=(hand_x - 0.05 * sx, hand_y + 0.20, 0))
        # Off hand (mirrored at left hand)
        off_x = 0.83 * sx
        haft2 = create_cylinder("axe_haft_L", 0.022, 0.32 * sy, 6, wood_mat,
                                location=(off_x, hand_y + 0.03, 0))
        blade2 = create_box("axe_blade_L", (0.1 * sx, 0.16 * sy, 0.012), blade_mat,
                            location=(off_x + 0.05 * sx, hand_y + 0.20, 0))
        objects.extend([haft, blade, haft2, blade2])

    elif weapon == "greatsword":
        grip = create_cylinder("gs_grip", 0.025, 0.32, 6, wood_mat,
                               location=(hand_x, hand_y - 0.18, 0.04))
        blade = create_box("gs_blade", (0.05 * sx, 0.78 * sy, 0.008), blade_mat,
                           location=(hand_x, hand_y + 0.2, 0.04))
        guard = create_box("gs_guard", (0.22 * sx, 0.03, 0.02), metal_mat,
                           location=(hand_x, hand_y - 0.02, 0.04))
        objects.extend([grip, blade, guard])

    elif weapon == "bow":
        bow_mat = make_material("bow", "#5a3818", roughness=0.75)
        bow = create_cylinder("bow_limb", 0.015, 0.7 * sy, 6, bow_mat,
                              location=(hand_x, hand_y + 0.15, 0),
                              rotation=(0, 0.15, 0))
        string_mat = make_material("string", "#d0c890", roughness=0.9)
        string = create_cylinder("bow_string", 0.004, 0.68 * sy, 4, string_mat,
                                 location=(hand_x + 0.04, hand_y + 0.15, 0))
        objects.extend([bow, string])

    elif weapon == "gun":
        barrel = create_cylinder("gun_barrel", 0.025, 0.3, 6, metal_mat,
                                 location=(hand_x, hand_y + 0.1, 0.04),
                                 rotation=(math.pi / 2, 0, 0))
        stock  = create_box("gun_stock", (0.06, 0.14, 0.08), wood_mat,
                            location=(hand_x, hand_y - 0.04, 0))
        objects.extend([barrel, stock])

    elif weapon in ("halberd", "spear"):
        shaft = create_cylinder("halberd_shaft", 0.022, 0.88 * sy, 6, wood_mat,
                                location=(hand_x, hand_y + 0.24, 0))
        head = create_box("halberd_head", (0.05 * sx, 0.2 * sy, 0.012), blade_mat,
                          location=(hand_x, hand_y + 0.7, 0))
        objects.extend([shaft, head])

    elif weapon in ("flail", "disc_staff", "mutant_arm"):
        # Generic elongated weapon
        shaft = create_cylinder("misc_shaft", 0.022, 0.44 * sy, 6, wood_mat,
                                location=(hand_x, hand_y + 0.06, 0))
        tip = create_sphere("misc_tip", 0.06, metal_mat,
                            location=(hand_x, hand_y + 0.32, 0))
        objects.extend([shaft, tip])

    return objects


# ─────────────────────────────────────────────────────────────────────────────
# GLB export
# ─────────────────────────────────────────────────────────────────────────────

def export_glb(output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format='GLB',
        export_animations=True,
        export_skins=True,
        export_apply=True,
        export_yup=True,
        export_draco_mesh_compression_enable=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    with open(args.spec) as f:
        spec = json.load(f)

    race_spec   = spec[args.race]
    career_spec = race_spec["careers"].get(args.career)
    if career_spec is None:
        print(f"ERROR: unknown career '{args.career}' for race '{args.race}'")
        sys.exit(1)

    print(f"[WAR] Generating {args.race} / {args.career} → {args.output}")

    clear_scene()

    body_parts   = build_body(race_spec)
    face_parts   = build_face(race_spec)
    armor_parts  = build_armor(race_spec, career_spec)

    all_objects = body_parts + face_parts + armor_parts

    # Import rig helpers here (same directory)
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(__file__))
    from rig_utils import create_humanoid_rig, apply_animations
    from anim_library import ACTIONS

    armature = create_humanoid_rig(all_objects, tuple(race_spec["bodyScale"]))
    apply_animations(armature, ACTIONS)

    export_glb(args.output)

    print(f"[WAR] SUCCESS: {args.output}")


if __name__ == "__main__":
    main()
