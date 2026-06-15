"""
Manifest-driven Blender asset generator.

This is the single entrypoint used by the Node CLI and MCP server. Existing
procedural builders are kept behind neutral manifest presets so generated
filenames, GLTF extras, and runtime asset IDs are manifest-first.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PIPELINE_ROOT.parents[1]
MODEL_DIR = REPO_ROOT / "public" / "assets" / "models"
STATIC_SPEC = PIPELINE_ROOT / "data" / "static_asset_spec.json"

sys.path.insert(0, str(SCRIPT_DIR))

from export_utils import repo_relative_path


CHARACTER_PRESETS = {
    "human_pyromancer",
    "human_tracker",
    "human_sun_vanguard",
    "human_devout_guardian",
}

STATIC_PRESETS = {
    "dummy": "dummy",
    "preview_twisted_tree": "preview_twisted_tree",
    "preview_blight_shrub": "preview_blight_shrub",
    "preview_jagged_stone": "preview_jagged_stone",
    "preview_dreary_reeds": "preview_dreary_reeds",
    "creature_ash_hound": "creature_ash_hound",
    "creature_barrow_wolf": "creature_barrow_wolf",
    "creature_lair_spider": "creature_lair_spider",
    "creature_mire_hound": "creature_mire_hound",
    "creature_rift_hound": "creature_rift_hound",
    "creature_war_boar": "creature_war_boar",
    "creature_wild_stag": "creature_wild_stag",
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    try:
        idx = argv.index("--")
        argv = argv[idx + 1:]
    except ValueError:
        argv = []

    parser = argparse.ArgumentParser(description="Generate a GLB from an asset manifest.")
    parser.add_argument("--manifest", required=True, help="Path to .asset.json manifest")
    parser.add_argument("--output", required=True, help="Absolute output .glb path")
    parser.add_argument("--artifact-dir", default=None, help="Optional preview/QC artifact directory")
    return parser.parse_args(argv)


def read_manifest(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def set_script_argv(script_name: str, script_args: list[str]) -> list[str]:
    previous = list(sys.argv)
    sys.argv = [script_name, "--", *script_args]
    return previous


def restore_argv(previous: list[str]) -> None:
    sys.argv = previous


def metadata_args(manifest: dict) -> list[str]:
    geometry = manifest.get("geometry", {})
    runtime = manifest.get("runtime", {})
    compat = manifest.get("compatibility", {})
    slots = compat.get("occupiesSlots") or []
    slot = slots[0] if slots else None
    args = [
        "--asset-id", manifest["assetId"],
        "--asset-kit", runtime.get("profileKey") or runtime.get("itemKey") or runtime.get("staticKey") or manifest["assetId"],
        "--asset-category", manifest["category"],
    ]
    if slot:
        args.extend(["--asset-slot", slot])
    if geometry.get("bodyFamily"):
        args.extend(["--body-family", geometry["bodyFamily"]])
    if geometry.get("skeletonId"):
        args.extend(["--skeleton-id", geometry["skeletonId"]])
    return args


def write_qc_report(
    manifest: dict,
    output_path: Path,
    artifact_dir: str | None,
    notes: dict | None = None,
    exported_objects: list[bpy.types.Object] | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_objects = exported_objects if exported_objects is not None else list(bpy.context.scene.objects)
    meshes = []
    total_tris = 0
    for obj in source_objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        tris = sum(max(0, len(poly.vertices) - 2) for poly in mesh.polygons)
        total_tris += tris
        meshes.append({
            "name": obj.name,
            "verts": len(mesh.vertices),
            "faces": len(mesh.polygons),
            "tris": tris,
            "materials": len(mesh.materials),
            "assetSlot": obj.get("assetSlot"),
        })

    qc = manifest.get("qc", {})
    required_clips = manifest.get("rigging", {}).get("requiredClips") or []
    available_clips = sorted(action.name for action in bpy.data.actions)
    missing_clips = [clip for clip in required_clips if clip not in available_clips]
    file_size_mb = (output_path.stat().st_size / (1024 * 1024)) if output_path.exists() else 0
    checks = {
        "hasModelFile": output_path.exists(),
        "hasExportedMeshes": len(meshes) > 0,
        "fileSizeBudget": file_size_mb <= qc.get("maxFileSizeMb", 12),
        "drawCallBudget": len(meshes) <= qc.get("maxDrawCalls", max(1, len(meshes))),
        "meshObjectBudget": len(meshes) <= qc.get("maxMeshObjects", max(1, len(meshes))),
        "requiredClipsPresent": len(missing_clips) == 0,
        "hasColliderPolicy": bool(manifest.get("collision", {}).get("policy")),
    }
    report = {
        "assetId": manifest["assetId"],
        "category": manifest["category"],
        "model": manifest["output"]["model"],
        "fileSizeBytes": output_path.stat().st_size if output_path.exists() else 0,
        "meshCount": len(meshes),
        "totalTris": total_tris,
        "availableClips": available_clips,
        "missingRequiredClips": missing_clips,
        "checks": checks,
        "qcPassed": all(checks.values()),
        "meshes": meshes,
        "artifactDir": repo_relative_path(artifact_dir),
        "manifestVersion": manifest["version"],
        "notes": notes or {},
    }
    output_path.with_suffix(".qc.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["qcPassed"]:
        failed = ", ".join(name for name, ok in checks.items() if not ok)
        raise RuntimeError(f"QC failed for {manifest['assetId']}: {failed}")


def run_character_preset(manifest: dict, output_path: Path, artifact_dir: str | None) -> None:
    preset = manifest["generator"]["preset"]
    from generate_manifest_character import generate_manifest_character, is_playable_profile
    if preset not in CHARACTER_PRESETS and not is_playable_profile(preset):
        raise RuntimeError(f"Unknown character preset: {preset}")
    generate_manifest_character(manifest, output_path, artifact_dir)


def run_static_preset(manifest: dict, output_path: Path, artifact_dir: str | None) -> None:
    preset = manifest["generator"]["preset"]
    if preset not in STATIC_PRESETS:
        raise RuntimeError(f"Unknown static preset: {preset}")
    args = [
        "--asset", STATIC_PRESETS[preset],
        "--output", str(output_path),
        "--spec", str(STATIC_SPEC),
        *metadata_args(manifest),
    ]
    previous = set_script_argv("generate_static_asset.py", args)
    try:
        import generate_static_asset
        generate_static_asset.main()
    finally:
        restore_argv(previous)
    write_qc_report(manifest, output_path, artifact_dir, {"preset": preset})


def apply_manifest_metadata(objects: list[bpy.types.Object], manifest: dict) -> None:
    runtime = manifest.get("runtime", {})
    geometry = manifest.get("geometry", {})
    slots = (manifest.get("compatibility") or {}).get("occupiesSlots") or []
    metadata = {
        "assetId": manifest["assetId"],
        "assetKit": runtime.get("profileKey") or runtime.get("itemKey") or runtime.get("staticKey") or manifest["assetId"],
        "assetCategory": manifest["category"],
        "assetSlot": slots[0] if slots else None,
        "bodyFamily": geometry.get("bodyFamily"),
        "skeletonId": geometry.get("skeletonId"),
    }
    for obj in objects:
        for key, value in metadata.items():
            if value:
                obj[key] = value


def export_selected(path: Path, objects: list[bpy.types.Object]) -> None:
    if not objects:
        raise RuntimeError("No objects selected for manifest export.")
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_animations=False,
        export_skins=False,
        export_extras=True,
        export_apply=True,
        export_yup=True,
        export_draco_mesh_compression_enable=False,
    )
    bpy.ops.object.select_all(action="DESELECT")


def build_base_and_armor():
    from generate_base_male_armor_showcase import (
        BASE_BLEND,
        apply_modifiers,
        build_armor,
        bounds_for,
        enhance_base_materials,
    )

    if not Path(BASE_BLEND).exists():
        raise FileNotFoundError(f"Missing baseline blend: {BASE_BLEND}")
    bpy.ops.wm.open_mainfile(filepath=str(BASE_BLEND))
    base_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not base_meshes:
        raise RuntimeError(f"No mesh found in {BASE_BLEND}")
    base = max(base_meshes, key=lambda obj: len(obj.data.vertices))
    for obj in list(bpy.context.scene.objects):
        if obj != base:
            bpy.data.objects.remove(obj, do_unlink=True)
    base.name = "asset_body_reference"
    base.data.name = "asset_body_reference_mesh"
    base.hide_render = False
    base.hide_viewport = False
    enhance_base_materials(base)
    base_bounds = bounds_for(base)
    armor_objects, report = build_armor(base, base_bounds)
    apply_modifiers()
    return base, armor_objects, report


def run_body_module(manifest: dict, output_path: Path, artifact_dir: str | None) -> None:
    base, _armor_objects, report = build_base_and_armor()
    apply_manifest_metadata([base], manifest)
    export_selected(output_path, [base])
    write_qc_report(manifest, output_path, artifact_dir, report, [base])


def run_armor_module(manifest: dict, output_path: Path, artifact_dir: str | None) -> None:
    preset = manifest.get("generator", {}).get("preset")
    if preset:
        from generate_manifest_character import generate_manifest_armor_module, is_playable_profile
        if is_playable_profile(preset):
            generate_manifest_armor_module(manifest, output_path, artifact_dir)
            return

    _base, armor_objects, report = build_base_and_armor()
    prefixes = manifest["generator"].get("objectNamePrefixes") or []
    module_objects = [
        obj for obj in armor_objects
        if any(obj.name.startswith(prefix) for prefix in prefixes)
    ]
    apply_manifest_metadata(module_objects, manifest)
    export_selected(output_path, module_objects)
    write_qc_report(manifest, output_path, artifact_dir, report, module_objects)


def copy_existing(manifest: dict, output_path: Path, artifact_dir: str | None) -> None:
    source = MODEL_DIR / manifest["generator"]["copyFrom"]
    if not source.exists():
        raise FileNotFoundError(f"copyExisting source missing: {source}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(source.read_bytes())
    write_qc_report(manifest, output_path, artifact_dir, {"copyFrom": str(source)})


def main() -> None:
    args = parse_args()
    manifest = read_manifest(args.manifest)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_dir = args.artifact_dir
    if artifact_dir:
        Path(artifact_dir).mkdir(parents=True, exist_ok=True)

    kind = manifest.get("generator", {}).get("kind")
    print(f"[asset-pipeline] Generating {manifest['assetId']} ({kind}) -> {output_path}")
    if kind == "characterPreset":
        run_character_preset(manifest, output_path, artifact_dir)
    elif kind == "staticPreset":
        run_static_preset(manifest, output_path, artifact_dir)
    elif kind == "bodyModule":
        run_body_module(manifest, output_path, artifact_dir)
    elif kind == "armorModule":
        run_armor_module(manifest, output_path, artifact_dir)
    elif kind in {"weaponModule", "jewelModule"}:
        from generate_manifest_accessory import generate_manifest_accessory
        generate_manifest_accessory(manifest, output_path, artifact_dir)
    elif kind == "copyExisting":
        copy_existing(manifest, output_path, artifact_dir)
    else:
        raise RuntimeError(f"Unsupported generator kind: {kind}")
    print(f"[asset-pipeline] SUCCESS: {output_path}")


if __name__ == "__main__":
    main()
