"""Compare existing renders using a fixed authoring-to-reference convention.

Read-only for Blender, source records, reference pixels, and render inputs.
Writes review/comparison* only. There is no camera fitting, image registration,
silhouette optimization, geometry generation, or automatic likeness acceptance.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_ID = "front-authoring-convention-001"
REFERENCE_ORIGIN_X = 254.282
REFERENCE_GROUND_Y = 729.0
METERS_PER_REFERENCE_PIXEL = 1.86 / 633
DISPLAY_SCALE = 3
EXPECTED_CAMERA = {
    "id": "front", "position": [0, -4, 1.50], "target": [0, 0, 1.50],
    "orthographic_scale": 1.01, "resolution": [1100, 1000],
}

# Explicit semantic pairings. Cage locations need not equal evaluated surfaces.
PAIRINGS = [
    ("F01", "head_skin", "crown", "high", "Top of source head cage; subdivision may lower the visible crown."),
    ("F02", "head_skin", "chin", "medium", "Reference chin is partly hidden by the collar."),
    ("F03", "gorget_steel_wall", "front_rim", "high", "Front rim center; reference includes trim thickness."),
    ("F04", "gorget_steel_wall", "side_rim", "medium", "View-dependent visible side rim; pose is not calibrated."),
    ("F05", "left_pauldron_main_shell", "inner_crown", "low", "Candidate main-shell crown pairing; visible guard/shell overlap is ambiguous."),
    ("F09", "breastplate_shell", "upper_neckline", "medium", "Top center is partly obscured by gorget/trim in the illustration."),
    ("F11", "heavy_relic_belt", "upper_front_center", "medium", "Actual belt upper-front center, explicit stable cage vertex v000. Supersedes the earlier breastplate-shell waist-center surrogate."),
]
DIAGNOSTIC_VERTEX_IDS = {("heavy_relic_belt", "upper_front_center"): "v000"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_recorded_evidence(root: Path, build: dict, path: Path) -> str:
    if "evidence" not in build:
        return "hash_not_recorded_by_legacy_build"
    evidence = {key.replace("\\", "/"): value for key, value in build["evidence"].items()}
    key = path.relative_to(root).as_posix()
    if key not in evidence:
        raise ValueError(f"{key} is not evidence from this completed build; do not compare a stale render")
    if evidence[key]["sha256"] != digest(path):
        raise ValueError(f"{key} hash differs from completed build evidence")
    return "verified"


def font(size: int):
    for candidate in (Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\arial.ttf")):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


def reference_pixel(world: list[float]) -> list[float]:
    return [REFERENCE_ORIGIN_X + world[0] / METERS_PER_REFERENCE_PIXEL,
            REFERENCE_GROUND_Y - world[2] / METERS_PER_REFERENCE_PIXEL]


def render_pixel(world: list[float], camera: dict) -> list[float]:
    width, height = camera["resolution"]
    pixels_per_meter = width / camera["orthographic_scale"]
    return [width / 2 + (world[0] - camera["position"][0]) * pixels_per_meter,
            height / 2 - (world[2] - camera["position"][2]) * pixels_per_meter]


def world_point(local: list[float], matrix: list[list[float]]) -> list[float]:
    values = local + [1.0]
    return [sum(matrix[row][column] * values[column] for column in range(4)) for row in range(3)]


def aligned_render(render: Image.Image, camera: dict, crop: list[int]) -> Image.Image:
    """Fixed affine resampling; no image content influences these coefficients."""
    width, height = camera["resolution"]
    if render.size != (width, height):
        raise ValueError(f"Render size {render.size} differs from frozen camera {(width, height)}")
    scale = width / camera["orthographic_scale"]
    a = scale * METERS_PER_REFERENCE_PIXEL / DISPLAY_SCALE
    c = width / 2 + ((crop[0] - REFERENCE_ORIGIN_X) * METERS_PER_REFERENCE_PIXEL - camera["position"][0]) * scale
    f = height / 2 - ((REFERENCE_GROUND_Y - crop[1]) * METERS_PER_REFERENCE_PIXEL - camera["position"][2]) * scale
    output_size = ((crop[2] - crop[0]) * DISPLAY_SCALE, (crop[3] - crop[1]) * DISPLAY_SCALE)
    return render.convert("RGB").transform(output_size, Image.Transform.AFFINE,
                                           (a, 0, c, 0, a, f), Image.Resampling.BICUBIC,
                                           fillcolor="#191D22")


def landmarks(root: Path, scene: dict, measurements: dict, evaluated: dict) -> list[dict]:
    parts = {}
    for path in sorted((root / "source").glob("*.json")):
        if path.name == "scene.json":
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        for part in record["parts"]:
            parts[part["id"]] = {"data": part, "file": str(path.relative_to(root)), "sha256": digest(path)}
    refs = {row["id"]: row for row in measurements["landmarks"]["front"]}
    evaluated_by_name = {part["name"]: part for part in evaluated["parts"]}
    rows = []
    for ref_id, part_id, landmark_id, confidence, note in PAIRINGS:
        if part_id not in parts or part_id not in evaluated_by_name:
            rows.append({"reference_id": ref_id, "part": part_id, "status": "not_available"})
            continue
        entry = parts[part_id]
        part = entry["data"]
        vertex_id = part.get("landmarks", {}).get(landmark_id)
        point_kind = "named_source_landmark"
        if vertex_id is None:
            vertex_id = DIAGNOSTIC_VERTEX_IDS.get((part_id, landmark_id))
            point_kind = "explicit_diagnostic_vertex"
        vertex = next((v for v in part["vertices"] if v["id"] == vertex_id), None)
        if vertex is None:
            rows.append({"reference_id": ref_id, "part": part_id, "status": "missing_named_landmark"})
            continue
        evaluated_part = evaluated_by_name[part_id]
        source_hash = evaluated_part.get("source_sha256")
        if source_hash is not None and source_hash != entry["sha256"]:
            rows.append({"reference_id": ref_id, "part": part_id,
                         "status": "source_changed_since_render_no_measurement",
                         "source_sha256": entry["sha256"], "built_source_sha256": source_hash,
                         "automatic_visual_acceptance": False})
            continue
        world = world_point(vertex["co"], evaluated_part["matrix_world"])
        predicted = reference_pixel(world)
        target = refs[ref_id]["raw_pixel"]
        delta = [predicted[i] - target[i] for i in range(2)]
        error = math.hypot(*delta)
        source_binding = "verified" if source_hash == entry["sha256"] else ("mismatch" if source_hash else "hash_not_recorded_by_build")
        rows.append({
            "reference_id": ref_id, "reference_name": refs[ref_id]["name"], "part": part_id,
            "source_file": entry["file"], "source_sha256": entry["sha256"],
            "render_source_binding": source_binding, "source_landmark": landmark_id, "source_vertex_id": vertex_id,
            "source_point_kind": point_kind,
            "status": "measured_control_cage_only", "correspondence_confidence": confidence, "note": note,
            "world_position_m": world, "render_pixel": render_pixel(world, EXPECTED_CAMERA),
            "reference_pixel": target, "predicted_reference_pixel": predicted,
            "delta_reference_pixels": delta, "image_plane_error_px": error,
            "image_plane_error_m_by_authoring_convention": error * METERS_PER_REFERENCE_PIXEL,
            "reference_uncertainty_radius_px": refs[ref_id]["uncertainty_radius_px"],
            "above_advisory_band": error * METERS_PER_REFERENCE_PIXEL > scene["acceptance"]["major_landmark_tolerance_m"],
            "automatic_visual_acceptance": False,
        })
    return rows


def panel_pair(reference: Image.Image, render: Image.Image, title: str) -> Image.Image:
    gap, header, footer = 24, 66, 73
    width, height = reference.size
    panel = Image.new("RGB", (width * 2 + gap, height + header + footer), "#151B21")
    panel.paste(reference, (0, header))
    panel.paste(render, (width + gap, header))
    draw = ImageDraw.Draw(panel)
    draw.text((16, 18), "ORIGINAL REFERENCE CROP", font=font(25), fill="#EED8A8")
    draw.text((width + gap + 16, 18), title, font=font(25), fill="#EED8A8")
    draw.text((16, height + header + 14), "Fixed 633 px / 1.86 m authoring convention. No camera fitting or image registration.", font=font(20), fill="#D7E0E5")
    draw.text((16, height + header + 41), "Upper-body comparison crop. The illustration is not orthographic; visual likeness remains unapproved.", font=font(19), fill="#ADBCC6")
    return panel


def landmark_panel(reference: Image.Image, rows: list[dict], crop: list[int]) -> Image.Image:
    width, height = reference.size
    panel = Image.new("RGB", (width + 630, max(height + 65, 875)), "#151B21")
    panel.paste(reference, (0, 65))
    draw = ImageDraw.Draw(panel)
    draw.text((16, 18), "FIXED ALIGNMENT: SOURCE CONTROL LANDMARKS", font=font(24), fill="#EED8A8")

    def local(point):
        return ((point[0] - crop[0]) * DISPLAY_SCALE, (point[1] - crop[1]) * DISPLAY_SCALE + 65)

    y = 77
    for row in rows:
        if row["status"] != "measured_control_cage_only":
            continue
        observed, predicted = local(row["reference_pixel"]), local(row["predicted_reference_pixel"])
        draw.line((observed, predicted), fill="#FFE29B", width=2)
        ox, oy = observed
        px, py = predicted
        draw.ellipse((ox - 7, oy - 7, ox + 7, oy + 7), outline="#65E4D2", width=3)
        draw.line((px - 7, py, px + 7, py), fill="#FA74D7", width=3)
        draw.line((px, py - 7, px, py + 7), fill="#FA74D7", width=3)
        dx, dy = row["delta_reference_pixels"]
        draw.text((width + 22, y), f"{row['reference_id']}  {row['source_landmark']}", font=font(21), fill="#E6EBEE")
        draw.text((width + 22, y + 28), f"Delta: ({dx:+.1f}, {dy:+.1f}) px | distance {row['image_plane_error_px']:.1f} px", font=font(18), fill="#BED2DD")
        draw.text((width + 22, y + 51), f"{row['image_plane_error_m_by_authoring_convention'] * 1000:.1f} mm on convention plane; pairing {row['correspondence_confidence']}", font=font(16), fill="#ADBCC6")
        y += 85
    y += 4
    for text in ["Cyan circle: estimated illustration landmark.", "Magenta cross: transformed source cage vertex.",
                 "Distances are 2D authoring-plane discrepancies, not measured 3D error.",
                 "Modifiers can move the rendered surface away from the cage.",
                 "Small errors do not establish facial likeness, surface detail, or visual acceptance."]:
        for line in textwrap.wrap(text, 69):
            draw.text((width + 22, y), line, font=font(16), fill="#ADBCC6")
            y += 23
        y += 5
    return panel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    review = root / "review"
    scene_path = root / "source" / "scene.json"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    camera = next(camera for camera in scene["cameras"] if camera["id"] == "front")
    if any(camera.get(key) != value for key, value in EXPECTED_CAMERA.items()):
        raise ValueError("Front camera differs from comparison convention 001; do not silently fit a new mapping")
    build_path = review / "build_report.json"
    build = json.loads(build_path.read_text(encoding="utf-8"))
    if build["camera_sha256"] != digest(scene_path):
        raise ValueError("Build and current scene hashes differ; render the current frozen scene before comparing")
    measurements_path = root / "references" / "measurements.json"
    measurements = json.loads(measurements_path.read_text(encoding="utf-8"))
    crop = measurements["crops"]["front_upperbody"]["bounds_px"]
    crop_path = root / "references" / measurements["crops"]["front_upperbody"]["file"]
    reference = Image.open(crop_path).convert("RGB")
    expected_size = (crop[2] - crop[0], crop[3] - crop[1])
    if reference.size != expected_size:
        raise ValueError("Stored original reference crop size differs from its measured bounds")
    reference = reference.resize((reference.width * DISPLAY_SCALE, reference.height * DISPLAY_SCALE), Image.Resampling.LANCZOS)
    evaluated_path = review / "evaluated_mesh.json.gz"
    evidence_binding = {str(evaluated_path.relative_to(root)): verify_recorded_evidence(root, build, evaluated_path)}
    with gzip.open(evaluated_path, "rt", encoding="utf-8") as handle:
        evaluated = json.load(handle)
    rows = landmarks(root, scene, measurements, evaluated)
    inputs = {str(path.relative_to(root)): digest(path) for path in (scene_path, build_path, measurements_path, crop_path, evaluated_path)}
    outputs = []
    source_paths = sorted((root / "source").glob("*.json"))
    newer_source_records = {}
    for mode in ("material", "neutral"):
        render_path = review / f"front_{mode}.png"
        if not render_path.exists():
            continue
        evidence_binding[str(render_path.relative_to(root))] = verify_recorded_evidence(root, build, render_path)
        inputs[str(render_path.relative_to(root))] = digest(render_path)
        newer_source_records[mode] = [str(path.relative_to(root)) for path in source_paths if path.stat().st_mtime_ns > render_path.stat().st_mtime_ns]
        aligned = aligned_render(Image.open(render_path), camera, crop)
        name = f"comparison_front_{mode}.png"
        panel_pair(reference, aligned, f"ACTUAL FRONT {mode.upper()} RENDER").save(review / name)
        outputs.append(name)
        if mode == "material":
            overlay = Image.blend(reference, aligned, 0.5)
            overlay_panel = Image.new("RGB", (overlay.width, overlay.height + 118), "#151B21")
            overlay_panel.paste(overlay, (0, 65))
            draw = ImageDraw.Draw(overlay_panel)
            draw.text((16, 18), "50% REFERENCE / 50% RENDER - FIXED ALIGNMENT", font=font(24), fill="#EED8A8")
            draw.text((16, overlay.height + 80), "No image registration. A visual diagnostic, not an acceptance score.", font=font(20), fill="#D7E0E5")
            overlay_panel.save(review / "comparison_front_overlay.png")
            outputs.append("comparison_front_overlay.png")
    if not outputs:
        raise FileNotFoundError("No actual front_material.png or front_neutral.png renders exist")
    landmark_panel(reference, rows, crop).save(review / "comparison_landmarks.png")
    outputs.append("comparison_landmarks.png")
    measured = [row for row in rows if row["status"] == "measured_control_cage_only"]
    report = {
        "schema_version": 1, "calibration_id": CALIBRATION_ID, "pairing_revision": "semantic-correspondences-002", "scene_revision": scene["revision"],
        "visual_status": "diagnostic_review_pending", "automatic_visual_acceptance": False,
        "runtime_promotion": False, "camera_fitted": False, "camera": camera,
        "fixed_mapping": {"x_ref": "254.282 + xWorld / (1.86 / 633)", "y_ref": "729 - zWorld / (1.86 / 633)",
                          "front_orthographic_width_m": 1.01, "image_plane_height_m": 1.01 * 1000 / 1100,
                          "reference_origin_x": REFERENCE_ORIGIN_X, "reference_ground_y": REFERENCE_GROUND_Y,
                          "reference_meters_per_pixel": METERS_PER_REFERENCE_PIXEL,
                          "display_enlargement": DISPLAY_SCALE, "pixel_center_convention": "width/2, height/2"},
        "advisory_distance_band_m": scene["acceptance"]["major_landmark_tolerance_m"],
        "landmarks": rows, "measured_control_landmarks": len(measured),
        "control_landmarks_above_advisory_band": sum(row["above_advisory_band"] for row in measured),
        "current_sources_newer_than_renders": newer_source_records,
        "render_and_mesh_evidence_binding": evidence_binding,
        "input_sha256": inputs, "outputs": outputs,
        "limitations": [
            "The reference is a stylized illustration with non-calibrated orientation, perspective and pose.",
            "The mapping is a declared authoring convention, not camera recovery from pixels.",
            "Landmark errors use current source-control coordinates and saved evaluated-object matrices; modifiers can move the visible surface.",
            "Source/render correspondence is unverified wherever render_source_binding says hash_not_recorded_by_build.",
            "Sparse landmark agreement cannot establish facial likeness, missing detail, silhouette fidelity, materials, or visual acceptance.",
            "Low-confidence pauldron correspondence should be inspected directly before using its displacement as an editing target.",
            "No silhouette IoU, image similarity, 3D recovery accuracy or automatic pass is claimed.",
        ],
    }
    (review / "comparison_report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    notes = """# Fixed reference comparison

This is a read-only review of actual Blender renders and the original reference
crop. The script writes only `review/comparison*`. It does not edit Blender,
source meshes, cameras, materials, or reference pixels, and does not fit images.

The frozen authoring convention is:

```text
x_reference = 254.282 + world_x / (1.86 / 633)
y_reference = 729 - world_z / (1.86 / 633)
```

For the declared front camera, Blender orthographic width is 1.01 m at 1100 x
1000 pixels with square pixels and the default horizontal fit. Image height is
1.01 * 1000 / 1100 m. The optical center uses width/2 and height/2. The script
rejects a changed front camera or a mismatched scene/build hash instead of
silently updating this convention. No matching algorithm is used.

The reference upper-body crop and aligned actual renders are displayed at the
same scale. Reference enlargement does not create new detail. The 50/50 overlay
blends existing pixels; no synthesized character or replacement reference is
used. A cyan landmark circle is the illustration estimate; a magenta cross is
a named source control vertex transformed by the matrix recorded in the build.

Distances are 2D authoring-plane discrepancies. They are not calibrated physical
errors, and control-cage points are not necessarily points on the final
subdivided surface. Reference occlusion, perspective, orientation, illustration
inconsistency, and pose remain unresolved. The nominal distance band is advisory;
even zero landmark error does not establish facial likeness or an acceptable
character. The pauldron-crown pairing is explicitly low confidence.

`comparison_report.json` records input hashes, named pairings, uncertainties,
source/render binding evidence, and source files newer than a render. Missing
source hashes in the build make the current-source/render pairing unverified.
Regenerate after rebuilding and rendering any changed source records.

Semantic pairing revision 002 replaces the earlier F11 breastplate-shell
waist-center surrogate with the actual belt upper-front center: the explicit
stable vertex v000 in heavy_relic_belt. This changes the diagnostic pairing only;
source vertices, camera calibration, and reference pixels remain unchanged.
F05 remains a low-confidence guard/main-shell crown correspondence.

Run with the bundled Python/Pillow interpreter:

```powershell
& 'C:/Users/bschm/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/compare_reference.py
```

This diagnostic does not establish visual acceptance or runtime promotion;
see runtime_visual_review.json for that separate decision.
"""
    (review / "comparison_README.md").write_text(notes, encoding="utf-8")
    print(json.dumps({"outputs": outputs, "report": str(review / "comparison_report.json"),
                      "landmarks": len(measured), "visual_status": report["visual_status"],
                      "control_landmarks_above_advisory_band": report["control_landmarks_above_advisory_band"]}, indent=2))


if __name__ == "__main__":
    main()
