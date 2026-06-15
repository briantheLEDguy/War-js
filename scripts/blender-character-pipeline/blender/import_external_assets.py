from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PIPELINE_ROOT.parents[1]
MODEL_DIR = REPO_ROOT / "public" / "assets" / "models"


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    try:
        idx = argv.index("--")
        argv = argv[idx + 1 :]
    except ValueError:
        argv = []
    parser = argparse.ArgumentParser(description="Import externally supplied GLB/FBX assets.")
    parser.add_argument("--spec", required=True, help="Path to external-imports.json")
    parser.add_argument("--only", default=None, help="Optional output filename to import only one asset")
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.actions):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def import_source(source: Path, source_type: str) -> None:
    if source_type == "fbx":
        bpy.ops.import_scene.fbx(filepath=str(source))
        return
    if source_type in {"glb", "gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(source))
        return
    raise RuntimeError(f"Unsupported external source type: {source_type}")


def selected_objects(record: dict) -> list[bpy.types.Object]:
    names = record.get("objects")
    if not names:
        return list(bpy.context.scene.objects)
    objects = []
    missing = []
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj:
            objects.append(obj)
        else:
            missing.append(name)
    if missing:
        raise RuntimeError(f"Missing source object(s) for {record['output']}: {', '.join(missing)}")
    if record.get("includeChildren", True):
        expanded = set(objects)
        for obj in objects:
            expanded.update(obj.children_recursive)
        objects = list(expanded)
    return objects


def prune_unselected(objects: list[bpy.types.Object]) -> list[bpy.types.Object]:
    keep = set(objects)
    for obj in list(bpy.context.scene.objects):
        if obj not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)
    return [obj for obj in bpy.context.scene.objects]


def mesh_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    mins = Vector((math.inf, math.inf, math.inf))
    maxs = Vector((-math.inf, -math.inf, -math.inf))
    found = False
    for obj in objects:
        if obj.type != "MESH":
            continue
        found = True
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, point.x)
            mins.y = min(mins.y, point.y)
            mins.z = min(mins.z, point.z)
            maxs.x = max(maxs.x, point.x)
            maxs.y = max(maxs.y, point.y)
            maxs.z = max(maxs.z, point.z)
    if not found:
        raise RuntimeError("Imported asset has no mesh bounds.")
    return mins, maxs


def transform_roots(objects: list[bpy.types.Object], matrix: Matrix) -> None:
    object_set = set(objects)
    roots = [obj for obj in objects if obj.parent not in object_set]
    for obj in roots:
        obj.matrix_world = matrix @ obj.matrix_world
    bpy.context.view_layer.update()


def normalize(objects: list[bpy.types.Object], record: dict) -> None:
    fit = record.get("fit") or {}
    if not fit and not record.get("recenter", True) and not record.get("ground", True):
        return
    mins, maxs = mesh_bounds(objects)
    size = maxs - mins
    scale = float(fit.get("scale", 1.0))
    if fit.get("height"):
        scale *= float(fit["height"]) / max(size.z, 0.0001)
    if fit.get("footprint"):
        scale *= float(fit["footprint"]) / max(size.x, size.y, 0.0001)
    center_x = (mins.x + maxs.x) * 0.5 if record.get("recenter", True) else 0
    center_y = (mins.y + maxs.y) * 0.5 if record.get("recenter", True) else 0
    ground_z = mins.z if record.get("ground", True) else 0
    matrix = (
        Matrix.Translation(Vector((-center_x * scale, -center_y * scale, -ground_z * scale)))
        @ Matrix.Scale(scale, 4)
    )
    transform_roots(objects, matrix)


def downscale_images(max_size: int | None) -> None:
    if not max_size:
        return
    for image in bpy.data.images:
        width, height = image.size
        if width <= max_size and height <= max_size:
            continue
        ratio = min(max_size / max(width, 1), max_size / max(height, 1))
        next_width = max(1, int(width * ratio))
        next_height = max(1, int(height * ratio))
        try:
            image.scale(next_width, next_height)
        except RuntimeError:
            pass


def triangle_count(obj: bpy.types.Object) -> int:
    if obj.type != "MESH":
        return 0
    return sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)


def decimate_meshes(objects: list[bpy.types.Object], max_tris: int | None) -> None:
    if not max_tris:
        return
    meshes = [obj for obj in objects if obj.type == "MESH"]
    current_tris = sum(triangle_count(obj) for obj in meshes)
    if current_tris <= max_tris or current_tris <= 0:
        return

    ratio = max(0.02, min(1.0, max_tris / current_tris))
    print(f"[external-import] decimating {current_tris} tris to target {max_tris} (ratio {ratio:.3f})")
    for obj in meshes:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        modifier = obj.modifiers.new("Runtime_Decimate", "DECIMATE")
        modifier.ratio = ratio
        try:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        except RuntimeError:
            obj.modifiers.remove(modifier)
    bpy.context.view_layer.update()


def relink_images(record: dict) -> None:
    texture_dirs = [REPO_ROOT / item for item in record.get("textureDirs", [])]
    if not texture_dirs:
        return
    for image in bpy.data.images:
        if image.packed_file:
            continue
        current = Path(bpy.path.abspath(image.filepath)) if image.filepath else None
        if current and current.exists() and image.size[0] > 0 and image.size[1] > 0:
            continue
        replacement = find_texture_replacement(image.name, texture_dirs)
        if not replacement:
            continue
        image.filepath = str(replacement)
        try:
            image.reload()
        except RuntimeError:
            pass


def find_texture_replacement(image_name: str, texture_dirs: list[Path]) -> Path | None:
    normalized = image_name.replace("\\", "/").split("/")[-1]
    stem = Path(normalized).stem
    candidates = [
        normalized,
        f"{normalized}.png",
        f"{stem}.png",
        f"{stem}.jpg",
        f"{stem}.jpeg",
        f"{stem}.tga.png",
    ]
    for directory in texture_dirs:
        if not directory.exists():
            continue
        lower_to_path = {item.name.lower(): item for item in directory.iterdir() if item.is_file()}
        for candidate in candidates:
            found = lower_to_path.get(candidate.lower())
            if found:
                return found
    return None


def force_opaque_materials(objects: list[bpy.types.Object]) -> None:
    seen = set()
    for obj in objects:
        if obj.type != "MESH":
            continue
        for slot in obj.material_slots:
            material = slot.material
            if not material or material.name in seen:
                continue
            seen.add(material.name)
            material.diffuse_color = (
                material.diffuse_color[0],
                material.diffuse_color[1],
                material.diffuse_color[2],
                1.0,
            )
            material.blend_method = "OPAQUE"
            material.use_screen_refraction = False
            material.show_transparent_back = False
            if not material.use_nodes or not material.node_tree:
                continue
            for node in material.node_tree.nodes:
                if node.type != "BSDF_PRINCIPLED":
                    continue
                if "Alpha" in node.inputs:
                    node.inputs["Alpha"].default_value = 1.0
                if "Base Color" in node.inputs:
                    color = list(node.inputs["Base Color"].default_value)
                    if len(color) >= 4:
                        color[3] = 1.0
                        node.inputs["Base Color"].default_value = color


def apply_metadata(objects: list[bpy.types.Object], record: dict) -> None:
    runtime = record.get("runtime") or {}
    asset_key = runtime.get("profileKey") or runtime.get("staticKey") or record["assetId"]
    metadata = {
        "assetId": record["assetId"],
        "assetKit": asset_key,
        "assetCategory": record["category"],
    }
    for obj in objects:
        for key, value in metadata.items():
            obj[key] = value


def export_selected(output_path: Path, objects: list[bpy.types.Object], record: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next((obj for obj in objects if obj.type == "MESH"), objects[0])
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        use_selection=True,
        export_animations=bool(record.get("exportAnimations", False)),
        export_skins=bool(record.get("exportSkins", False)),
        export_extras=True,
        export_apply=True,
        export_yup=True,
        export_draco_mesh_compression_enable=False,
    )


def write_qc(output_path: Path, objects: list[bpy.types.Object], record: dict) -> None:
    meshes = []
    total_tris = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        tris = sum(max(0, len(poly.vertices) - 2) for poly in mesh.polygons)
        total_tris += tris
        meshes.append(
            {
                "name": obj.name,
                "verts": len(mesh.vertices),
                "faces": len(mesh.polygons),
                "tris": tris,
                "materials": len(mesh.materials),
            }
        )
    qc = record.get("qc") or {}
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    checks = {
        "hasModelFile": output_path.exists(),
        "hasExportedMeshes": len(meshes) > 0,
        "fileSizeBudget": file_size_mb <= qc.get("maxFileSizeMb", 12),
        "drawCallBudget": len(meshes) <= qc.get("maxDrawCalls", max(1, len(meshes))),
        "meshObjectBudget": len(meshes) <= qc.get("maxMeshObjects", max(1, len(meshes))),
    }
    if qc.get("maxTris"):
        checks["triangleBudget"] = total_tris <= qc["maxTris"]
    report = {
        "assetId": record["assetId"],
        "category": record["category"],
        "model": record["output"],
        "fileSizeBytes": output_path.stat().st_size,
        "meshCount": len(meshes),
        "totalTris": total_tris,
        "availableClips": sorted(action.name for action in bpy.data.actions),
        "checks": checks,
        "qcPassed": all(checks.values()),
        "meshes": meshes,
        "source": record["source"],
        "manifestVersion": "1.0.0",
    }
    output_path.with_suffix(".qc.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["qcPassed"]:
        failed = ", ".join(name for name, ok in checks.items() if not ok)
        raise RuntimeError(f"QC failed for {record['assetId']}: {failed}")


def import_record(record: dict) -> None:
    clear_scene()
    source = REPO_ROOT / record["source"]
    if not source.exists():
        raise FileNotFoundError(f"External source missing: {source}")
    print(f"[external-import] {record['output']} <- {source}")
    import_source(source, record["sourceType"])
    objects = prune_unselected(selected_objects(record))
    normalize(objects, record)
    decimate_meshes(objects, (record.get("decimate") or {}).get("maxTris"))
    relink_images(record)
    downscale_images(record.get("maxTextureSize"))
    if record.get("forceOpaque") or record.get("category") == "character":
        force_opaque_materials(objects)
    apply_metadata(objects, record)
    output_path = MODEL_DIR / record["output"]
    export_selected(output_path, objects, record)
    write_qc(output_path, objects, record)


def main() -> None:
    args = parse_args()
    spec_path = Path(args.spec)
    if not spec_path.is_absolute():
        spec_path = PIPELINE_ROOT / spec_path
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    for record in spec["imports"]:
        if args.only and record["output"] != args.only:
            continue
        import_record(record)
    print("[external-import] complete")


if __name__ == "__main__":
    main()
