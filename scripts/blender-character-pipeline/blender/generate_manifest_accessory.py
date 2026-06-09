"""Manifest-driven weapon and jewel accessory generation."""

from __future__ import annotations

import json
from pathlib import Path

import bpy

from export_utils import normalize_y_up_scene_to_blender_z_up, repo_relative_path
from mesh_primitives import box_prism, flat_material, loft_axis, sphere, superellipse_bar, torus


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def material(name: str, color: str, roughness: float, metallic: float = 0.0) -> bpy.types.Material:
    return flat_material(name, color, roughness, metallic)


def apply_metadata(objects: list[bpy.types.Object], manifest: dict) -> None:
    runtime = manifest.get("runtime", {})
    slots = (manifest.get("compatibility") or {}).get("occupiesSlots") or [manifest["category"]]
    for obj in objects:
        obj["assetId"] = manifest["assetId"]
        obj["assetKit"] = runtime.get("itemKey") or manifest["assetId"]
        obj["assetCategory"] = manifest["category"]
        obj["assetSlot"] = slots[0]
        if manifest.get("geometry", {}).get("bodyFamily"):
            obj["bodyFamily"] = manifest["geometry"]["bodyFamily"]


def add_anchor(anchor: dict, manifest: dict) -> bpy.types.Object:
    empty = bpy.data.objects.new(anchor["name"], None)
    empty.empty_display_type = "SPHERE"
    empty.empty_display_size = 0.025
    empty.location = tuple(anchor.get("position", [0, 0, 0]))
    empty["assetId"] = manifest["assetId"]
    empty["anchorParent"] = anchor["parent"]
    empty["assetCategory"] = manifest["category"]
    bpy.context.collection.objects.link(empty)
    return empty


def build_weapon(manifest: dict) -> list[bpy.types.Object]:
    steel = material("mat_weapon_dark_steel", "#2f383a", 0.46, 0.72)
    dark = material("mat_weapon_oiled_grip", "#1d120c", 0.80, 0.0)
    brass = material("mat_weapon_worn_brass", "#b8872f", 0.40, 0.62)
    objects = [
        loft_axis("wep_wrapped_grip", "y", [
            {"coord": -0.30, "rx": 0.030, "rz": 0.030},
            {"coord": 0.55, "rx": 0.026, "rz": 0.026},
            {"coord": 1.05, "rx": 0.030, "rz": 0.030},
        ], dark, segments=32),
        superellipse_bar("wep_head_core", "x", (0.0, 1.10, 0.0), 0.46, 0.105, 0.092, steel, segments=32),
        box_prism("wep_head_left_cap", (-0.275, 1.10, 0.0), (0.075, 0.225, 0.190), steel),
        box_prism("wep_head_right_cap", (0.275, 1.10, 0.0), (0.075, 0.225, 0.190), steel),
        superellipse_bar("wep_upper_bind", "x", (0.0, 1.235, 0.0), 0.55, 0.014, 0.098, brass, segments=24),
        superellipse_bar("wep_lower_bind", "x", (0.0, 0.965, 0.0), 0.55, 0.014, 0.098, brass, segments=24),
        torus("wep_pommel_ring", 0.042, 0.010, brass, (0.0, -0.34, 0.0), rotation=(1.5708, 0, 0),
              major_segments=32, minor_segments=8),
    ]
    for idx, y in enumerate([-0.16, 0.02, 0.20, 0.38]):
        objects.append(torus(f"wep_grip_band_{idx}", 0.031, 0.006, brass, (0.0, y, 0.0),
                             rotation=(1.5708, 0, 0), major_segments=24, minor_segments=8))
    return objects


def build_jewel(manifest: dict) -> list[bpy.types.Object]:
    dark = material("mat_jewel_dark_chain", "#1d2426", 0.50, 0.55)
    brass = material("mat_jewel_antique_brass", "#a97a2b", 0.36, 0.64)
    gem = material("mat_jewel_deep_red_glass", "#7d1115", 0.18, 0.0)
    objects = [
        torus("jwl_neck_chain_arc", 0.115, 0.006, dark, (0.0, 0.0, 0.0), rotation=(1.5708, 0, 0),
              major_segments=64, minor_segments=8),
        torus("jwl_pendant_frame", 0.040, 0.006, brass, (0.0, -0.095, 0.018), rotation=(1.5708, 0, 0),
              major_segments=32, minor_segments=8),
        sphere("jwl_pendant_gem", 0.026, gem, (0.0, -0.095, 0.040), segments=20),
        box_prism("jwl_clasp", (0.0, 0.088, 0.0), (0.070, 0.020, 0.018), brass),
    ]
    return objects


def export_accessory(output_path: Path, objects: list[bpy.types.Object], anchors: list[bpy.types.Object]) -> None:
    normalize_y_up_scene_to_blender_z_up()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [*objects, *anchors]:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_animations=False,
        export_skins=False,
        export_extras=True,
        export_apply=True,
        export_yup=True,
        export_draco_mesh_compression_enable=False,
    )


def write_qc(manifest: dict, output_path: Path, objects: list[bpy.types.Object], artifact_dir: str | None) -> None:
    meshes = []
    total_tris = 0
    for obj in objects:
        tris = sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)
        total_tris += tris
        meshes.append({
            "name": obj.name,
            "verts": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "tris": tris,
            "materials": len(obj.data.materials),
            "assetId": obj.get("assetId"),
            "assetSlot": obj.get("assetSlot"),
        })
    qc = manifest.get("qc", {})
    checks = {
        "drawCallBudget": len(meshes) <= qc.get("maxDrawCalls", 24),
        "meshObjectBudget": len(meshes) <= qc.get("maxMeshObjects", 24),
        "fileSizeBudget": (output_path.stat().st_size / (1024 * 1024)) <= qc.get("maxFileSizeMb", 4),
        "hasColliderPolicy": bool(manifest.get("collision", {}).get("policy")),
        "hasAnchors": bool(manifest.get("attachments")),
    }
    report = {
        "assetId": manifest["assetId"],
        "category": manifest["category"],
        "model": manifest["output"]["model"],
        "fileSizeBytes": output_path.stat().st_size,
        "meshCount": len(meshes),
        "totalTris": total_tris,
        "artifactDir": repo_relative_path(artifact_dir),
        "manifestVersion": manifest["version"],
        "checks": checks,
        "qcPassed": all(checks.values()),
        "meshes": meshes,
    }
    output_path.with_suffix(".qc.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["qcPassed"]:
        failed = ", ".join(name for name, ok in checks.items() if not ok)
        raise RuntimeError(f"Accessory QC failed for {manifest['assetId']}: {failed}")


def generate_manifest_accessory(manifest: dict, output_path: Path, artifact_dir: str | None) -> None:
    clear_scene()
    if manifest["category"] == "weapon":
        objects = build_weapon(manifest)
    elif manifest["category"] == "jewel":
        objects = build_jewel(manifest)
    else:
        raise RuntimeError(f"Unsupported accessory category: {manifest['category']}")
    anchors = [add_anchor(anchor, manifest) for anchor in manifest.get("attachments", [])]
    apply_metadata([*objects, *anchors], manifest)
    export_accessory(output_path, objects, anchors)
    write_qc(manifest, output_path, objects, artifact_dir)
