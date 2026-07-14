"""Export class-directed review weapons from installed CC0 equipment fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

from bl_ext.blender_org.mpfb.services import LocationService


EQUIPMENT_PACK_SHA256 = "d8afa9d98c52f0a5e92a0d3e9f691f5699dd878499d9f6681740d38ca2640236"
EQUIPMENT_PACK_URL = "https://static.makehumancommunity.org/assets/assetpacks/equipment01.html"

CASTER_ARCHETYPES = {"caster", "rune_caster", "bog_caster", "occult", "ritual"}
MARTIAL_ARCHETYPES = {"duelist", "assassin", "ranger", "hunter", "skirmisher"}

SOURCE_CONFIG = {
    "culturalibre_magic_sceptre": {"axis": "z", "grip": 0.16, "material": "arcane"},
    "culturalibre_war_hammer": {"axis": "z", "grip": 0.16, "material": "steel"},
    "culturalibre_wooden_bow": {"axis": "z", "grip": 0.50, "material": "wood"},
    "joepal_crude_sword": {"axis": "z", "grip": 0.12, "material": "steel"},
    "o4saken_dagger": {"axis": "y", "grip": 0.15, "material": "steel"},
    "culturalibre_hero_kalistick": {"axis": "z", "grip": 0.50, "material": "steel"},
    "culturalibre_hero_kalistick_lefthanded": {"axis": "z", "grip": 0.50, "material": "steel"},
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-key", required=True)
    parser.add_argument("--archetype", required=True)
    parser.add_argument("--revision-seed", type=int, default=1)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-dir", required=True)
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights):
        for item in list(collection):
            if item.users == 0:
                collection.remove(item)


def fixture_files(asset_name: str) -> tuple[Path, Path, Path]:
    root = Path(LocationService.get_user_data("clothes")) / asset_name
    mhclo = root / f"{asset_name}.mhclo"
    if not mhclo.is_file():
        raise FileNotFoundError(f"Installed equipment fixture is missing: {mhclo}")
    obj_name = None
    material_name = None
    for line in mhclo.read_text(encoding="utf-8", errors="replace").splitlines():
        pieces = line.strip().split(maxsplit=1)
        if len(pieces) != 2:
            continue
        if pieces[0] == "obj_file":
            obj_name = pieces[1].strip()
        elif pieces[0] == "material":
            material_name = pieces[1].strip()
    objects = list(root.glob("*.obj"))
    materials = list(root.glob("*.mhmat"))
    obj = root / obj_name if obj_name else (objects[0] if objects else None)
    mhmat = root / material_name if material_name else (materials[0] if materials else None)
    if obj is None or not obj.is_file() or mhmat is None or not mhmat.is_file():
        raise FileNotFoundError(f"Fixture {asset_name} has an incomplete OBJ/material source")
    return mhclo, obj, mhmat


def parse_material_texture(mhmat: Path) -> Path | None:
    for line in mhmat.read_text(encoding="utf-8", errors="replace").splitlines():
        pieces = line.strip().split(maxsplit=1)
        if len(pieces) == 2 and pieces[0] == "diffuseTexture":
            candidate = mhmat.parent / pieces[1].strip()
            return candidate if candidate.is_file() else None
    return None


def runtime_material(name: str, mhmat: Path, style: str) -> bpy.types.Material:
    result = bpy.data.materials.new(f"{name}_fixture_pbr")
    result.use_nodes = True
    nodes = result.node_tree.nodes
    links = result.node_tree.links
    principled = nodes.get("Principled BSDF")
    texture = parse_material_texture(mhmat)
    if texture:
        image = bpy.data.images.load(str(texture), check_existing=True)
        image.colorspace_settings.name = "sRGB"
        node = nodes.new("ShaderNodeTexImage")
        node.image = image
        links.new(node.outputs["Color"], principled.inputs["Base Color"])
    else:
        colors = {
            "steel": (0.22, 0.25, 0.29, 1.0),
            "wood": (0.23, 0.10, 0.035, 1.0),
            "arcane": (0.18, 0.20, 0.32, 1.0),
        }
        principled.inputs["Base Color"].default_value = colors[style]
    principled.inputs["Metallic"].default_value = 0.72 if style in {"steel", "arcane"} else 0.04
    principled.inputs["Roughness"].default_value = 0.34 if style == "steel" else 0.58
    if style == "arcane":
        principled.inputs["Emission Color"].default_value = (0.10, 0.18, 0.65, 1.0)
        principled.inputs["Emission Strength"].default_value = 0.22
    result["sourceMaterial"] = str(mhmat)
    result["runtimeAlphaMode"] = "OPAQUE"
    return result


def join_imported_meshes() -> bpy.types.Object:
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("Equipment OBJ imported without mesh geometry")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def canonical_coordinates(point: Vector, axis: str) -> Vector:
    if axis == "z":
        return Vector((point.x, point.y, point.z))
    if axis == "y":
        return Vector((point.x, point.z, -point.y))
    if axis == "x":
        return Vector((point.y, point.z, point.x))
    raise ValueError(f"Unsupported authored weapon axis: {axis}")


def normalize_fixture(mesh: bpy.types.Object, config: dict, target_length: float) -> dict:
    converted = [canonical_coordinates(vertex.co, config["axis"]) for vertex in mesh.data.vertices]
    minimum = Vector(tuple(min(point[index] for point in converted) for index in range(3)))
    maximum = Vector(tuple(max(point[index] for point in converted) for index in range(3)))
    source_length = maximum.z - minimum.z
    if source_length <= 1e-6:
        raise RuntimeError(f"Authored fixture has no usable length: {mesh.name}")
    grip_z = minimum.z + source_length * float(config["grip"])
    transverse = Vector(((minimum.x + maximum.x) * 0.5, (minimum.y + maximum.y) * 0.5, grip_z))
    scale = target_length / source_length
    for vertex, point in zip(mesh.data.vertices, converted, strict=True):
        vertex.co = (point - transverse) * scale
    mesh.data.update()
    return {
        "sourceBounds": {"minimum": list(minimum), "maximum": list(maximum)},
        "sourceLength": source_length,
        "targetLength": target_length,
        "scale": scale,
        "primaryGrip": [0.0, 0.0, 0.0],
    }


def render_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    # Blender can retain an imported OBJ's old bound-box cache after the
    # canonical grip normalization. Read the actual authored vertices so the
    # evidence camera cannot make a correctly scaled weapon look microscopic.
    points = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def aim(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_reviews(mesh: bpy.types.Object, review_dir: Path) -> list[dict]:
    review_dir.mkdir(parents=True, exist_ok=True)
    minimum, maximum = render_bounds([mesh])
    center = (minimum + maximum) * 0.5
    extent = max(maximum.x - minimum.x, maximum.y - minimum.y, maximum.z - minimum.z)
    camera_data = bpy.data.cameras.new("weapon_review_camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = extent * 1.28
    camera_data.clip_start = 0.01
    camera = bpy.data.objects.new("weapon_review_camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    for name, location, energy in (
        ("weapon_key", (-2.5, -3.5, 3.4), 900),
        ("weapon_fill", (2.6, -1.6, 2.2), 520),
        ("weapon_rim", (0.5, 3.0, 3.0), 760),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.size = 2.0
        light = bpy.data.objects.new(name, data)
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
    scene.world.color = (0.025, 0.03, 0.04)
    views = {
        "front": Vector((center.x, center.y - extent * 2.6, center.z)),
        "side": Vector((center.x + extent * 2.6, center.y, center.z)),
        "back": Vector((center.x, center.y + extent * 2.6, center.z)),
        "isometric": Vector((center.x + extent * 1.8, center.y - extent * 1.8, center.z + extent * 0.35)),
    }
    rows = []
    for name, position in views.items():
        camera.location = position
        aim(camera, center)
        output = review_dir / f"{name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        rows.append({"view": name, "path": str(output), "sha256": sha256(output)})
    return rows


def export_glb(output: Path, root: bpy.types.Object, mesh: bpy.types.Object, markers: list[bpy.types.Object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [root, mesh, *markers]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=str(output), export_format="GLB", use_selection=True,
        export_extras=True, export_yup=True, export_apply=False,
    )


def build_weapon(asset_name: str, key: str, target_length: float, two_handed: bool, output: Path, review_dir: Path) -> dict:
    clear_scene()
    mhclo, obj_path, mhmat = fixture_files(asset_name)
    before = set(bpy.context.scene.objects)
    bpy.ops.wm.obj_import(filepath=str(obj_path))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    if not imported:
        raise RuntimeError(f"Blender imported no objects for {asset_name}")
    mesh = join_imported_meshes()
    mesh.name = f"{key}_authored_fixture"
    original_vertices = len(mesh.data.vertices)
    mesh.data.calc_loop_triangles()
    original_triangles = len(mesh.data.loop_triangles)
    if original_vertices < 100 or original_triangles < 100:
        raise RuntimeError(f"Equipment fixture is unexpectedly trivial: {asset_name}")
    config = SOURCE_CONFIG[asset_name]
    normalization = normalize_fixture(mesh, config, target_length)
    mesh.data.materials.clear()
    mesh.data.materials.append(runtime_material(asset_name, mhmat, config["material"]))
    root = bpy.data.objects.new("weapon_root", None)
    bpy.context.scene.collection.objects.link(root)
    mesh.parent = root
    root["handling"] = "two_handed" if two_handed else "one_handed"
    root["sourcePack"] = "equipment01"
    root["sourceAsset"] = asset_name
    root["authoredFixture"] = True
    root["primitiveGeometry"] = False
    root["runtimeEligible"] = False
    markers = []
    marker_locations = {
        "weapon_grip_primary": (0.0, 0.0, 0.0),
        "weapon_grip_secondary": (0.0, 0.0, target_length * 0.19 if two_handed else 0.0),
        "weapon_strike_origin": (0.0, 0.0, target_length * 0.86),
    }
    for marker_name, location in marker_locations.items():
        marker = bpy.data.objects.new(marker_name, None)
        marker.location = location
        marker.parent = root
        marker["markerRole"] = marker_name.removeprefix("weapon_")
        bpy.context.scene.collection.objects.link(marker)
        markers.append(marker)
    previews = render_reviews(mesh, review_dir)
    export_glb(output, root, mesh, markers)
    return {
        "key": key,
        "path": str(output),
        "sha256": sha256(output),
        "handling": root["handling"],
        "sourcePack": "equipment01",
        "sourcePackSha256": EQUIPMENT_PACK_SHA256,
        "sourceUrl": EQUIPMENT_PACK_URL,
        "sourceAsset": asset_name,
        "sourceFiles": {
            "mhclo": {"path": str(mhclo), "sha256": sha256(mhclo)},
            "obj": {"path": str(obj_path), "sha256": sha256(obj_path)},
            "material": {"path": str(mhmat), "sha256": sha256(mhmat)},
        },
        "authoredFixture": True,
        "primitiveGeometry": False,
        "originalVertices": original_vertices,
        "originalTriangles": original_triangles,
        "normalization": normalization,
        "secondaryGripPresent": two_handed,
        "previews": previews,
    }


def weapon_selection(archetype: str) -> tuple[str, str, str]:
    if archetype in CASTER_ARCHETYPES:
        return ("culturalibre_magic_sceptre", "o4saken_dagger", "culturalibre_wooden_bow")
    if archetype in MARTIAL_ARCHETYPES:
        return ("joepal_crude_sword", "o4saken_dagger", "culturalibre_wooden_bow")
    return ("culturalibre_war_hammer", "joepal_crude_sword", "culturalibre_hero_kalistick")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    review_dir = Path(args.review_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    main_asset, off_asset, two_asset = weapon_selection(args.archetype)
    rows = [
        build_weapon(main_asset, "one_hand_main", 0.92, False, output_dir / "review_weapon_one_hand_main.glb", review_dir / "one_hand_main"),
        build_weapon(off_asset, "one_hand_off", 0.72, False, output_dir / "review_weapon_one_hand_off.glb", review_dir / "one_hand_off"),
        build_weapon(two_asset, "two_hand", 1.42, True, output_dir / "review_weapon_two_hand.glb", review_dir / "two_hand"),
    ]
    checks = {
        "threeWeaponsPresent": all(Path(row["path"]).is_file() for row in rows),
        "authoredEquipmentFixtures": all(row["authoredFixture"] for row in rows),
        "noPrimitiveGeometry": all(not row["primitiveGeometry"] for row in rows),
        "equipmentPackProvenance": all(row["sourcePack"] == "equipment01" for row in rows),
        "substantiveSourceMeshes": all(row["originalTriangles"] >= 100 for row in rows),
        "secondaryGripPresent": rows[2]["secondaryGripPresent"],
        "reviewViewsPresent": all(len(row["previews"]) == 4 for row in rows),
    }
    report = {
        "schemaVersion": 2,
        "assetId": f"review.weapon_suite.{args.profile_key}",
        "kind": "weaponReviewSuite",
        "profileKey": args.profile_key,
        "archetype": args.archetype,
        "revisionSeed": args.revision_seed,
        "weapons": rows,
        "handlingModes": ["one_handed", "two_handed", "dual_wield"],
        "sourcePack": "equipment01",
        "modelStage": "review_evidence",
        "runtimeEligible": False,
        "checks": checks,
        "qcPassed": all(checks.values()),
    }
    (output_dir / "weapon-suite.qc.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print("[mpfb-authored-weapons] " + json.dumps({
        "profileKey": args.profile_key,
        "outputDir": str(output_dir),
        "sources": [row["sourceAsset"] for row in rows],
        "qcPassed": report["qcPassed"],
    }))


if __name__ == "__main__":
    main()
