"""Rasterize inspectable fixed brush records into authored material image maps.

This is a paint-record player. It contains no random marks, noise functions,
scatter, weave generation, source-image sampling, or illumination synthesis.
Only the literal paths, spots and polygon outlines in paint_strokes.json draw.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
TEXTURES = ROOT / "textures"
SOURCE = TEXTURES / "source"
RECORD = TEXTURES / "paint_strokes.json"
CHANNELS = ("basecolor", "roughness", "metallic", "height")


def validate_records(record):
    resolution = record["resolution"]
    if not isinstance(resolution, int) or not 64 <= resolution <= 1024:
        raise ValueError("Material source tiles must be at most 1024 pixels")
    if record["schema_version"] != 1:
        raise ValueError("Unsupported paint record schema")
    for name, brush in record["brushes"].items():
        kind = brush["kind"]
        if kind not in ("paths", "polygons", "spots"):
            raise ValueError(f"{name}: unsupported brush operation")
        shapes = [brush["points"]] if kind == "spots" else brush["shapes"]
        for shape in shapes:
            if not shape or kind == "polygons" and len(shape) < 3 or kind == "paths" and len(shape) < 2:
                raise ValueError(f"{name}: incomplete explicit shape")
            for point in shape:
                if len(point) != 2 or any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or v >= resolution for v in point):
                    raise ValueError(f"{name}: invalid authored point {point}")
    for name, material in record["materials"].items():
        if set(material["base"]) != set(CHANNELS):
            raise ValueError(f"{name}: all four source channels are required")
        layer_ids = set()
        for layer in material["layers"]:
            if layer["id"] in layer_ids or layer["brush"] not in record["brushes"]:
                raise ValueError(f"{name}: duplicate layer or undefined brush")
            layer_ids.add(layer["id"])
            if not 0 <= layer["opacity"] <= 255 or not 0 <= layer.get("softness", 0) <= 64:
                raise ValueError(f"{name}: invalid brush opacity/softness")
            for channel, value in layer["paint"].items():
                if channel not in CHANNELS:
                    raise ValueError(f"{name}: unsupported channel {channel}")
                values = value if isinstance(value, list) else [value]
                if len(values) != (3 if channel == "basecolor" else 1) or any(not isinstance(v, int) or not 0 <= v <= 255 for v in values):
                    raise ValueError(f"{name}: invalid paint value")


def brush_mask(brush, layer, size):
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    opacity = layer["opacity"]
    if brush["kind"] == "polygons":
        for shape in brush["shapes"]:
            draw.polygon([tuple(point) for point in shape], fill=opacity)
    elif brush["kind"] == "paths":
        for shape in brush["shapes"]:
            draw.line([tuple(point) for point in shape], fill=opacity,
                      width=layer["width"], joint="curve")
    else:
        radius = layer["radius"]
        for x, y in brush["points"]:
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=opacity)
    if layer.get("softness", 0):
        mask = mask.filter(ImageFilter.GaussianBlur(layer["softness"]))
    return mask


def preview_sheet(material_images):
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    sheet = Image.new("RGB", (1040, 762), (28, 30, 34))
    draw = ImageDraw.Draw(sheet)
    draw.text((24, 15), "AUTHORED PAINT — BASE COLOR MAPS", fill=(222, 216, 202), font=font)
    draw.text((24, 47), "Fixed brush records; no lighting, reference pixels or generated noise.", fill=(162, 168, 176), font=small)
    placements = [(18, 82), (362, 82), (706, 82), (18, 417), (362, 417), (706, 417)]
    for (name, maps), (x, y) in zip(material_images.items(), placements):
        tile = maps["basecolor"].resize((316, 285), Image.Resampling.LANCZOS)
        sheet.paste(tile, (x, y))
        draw.text((x+5, y+292), name.replace("_", " ").upper(), fill=(224, 218, 207), font=small)
    sheet.save(TEXTURES / "painted_material_samples.png", optimize=True)

    channels = Image.new("RGB", (1120, 1810), (28, 30, 34))
    draw = ImageDraw.Draw(channels)
    draw.text((18, 15), "PAINT CHANNEL INSPECTION", fill=(222, 216, 202), font=font)
    for col, name in enumerate(CHANNELS):
        draw.text((col*278+20, 48), name.upper(), fill=(177, 183, 191), font=small)
    for row, (name, maps) in enumerate(material_images.items()):
        top = 78+row*286
        for col, channel in enumerate(CHANNELS):
            tile = maps[channel].convert("RGB").resize((258, 250), Image.Resampling.LANCZOS)
            channels.paste(tile, (col*278+12, top))
        draw.text((18, top+254), name.upper(), fill=(224, 218, 207), font=small)
    channels.save(TEXTURES / "painted_material_channels.png", optimize=True)


def main():
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    validate_records(record)
    SOURCE.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(RECORD.read_bytes()).hexdigest()
    size = record["resolution"]
    manifest = {"schema_version": 1, "paint_source_sha256": digest,
                "resolution": [size, size], "method": record["method"],
                "height_convention": record["height_convention"],
                "status": "Authored material source maps; final geometry bake and visual review still required",
                "materials": {}, "total_bytes": 0}
    material_images = {}
    mask_cache = {}
    for name, material in record["materials"].items():
        maps = {channel: Image.new("RGB" if channel == "basecolor" else "L", (size, size),
                                   tuple(value) if isinstance(value, list) else value)
                for channel, value in material["base"].items()}
        for layer in material["layers"]:
            key = json.dumps({k: layer[k] for k in ("brush", "opacity", "softness", "width", "radius") if k in layer}, sort_keys=True)
            if key not in mask_cache:
                mask_cache[key] = brush_mask(record["brushes"][layer["brush"]], layer, size)
            for channel, value in layer["paint"].items():
                color = tuple(value) if isinstance(value, list) else value
                paint = Image.new(maps[channel].mode, (size, size), color)
                maps[channel].paste(paint, (0, 0), mask_cache[key])
        result = {"layer_ids": [layer["id"] for layer in material["layers"]], "maps": {}}
        for channel, image in maps.items():
            path = SOURCE / f"{name}_{channel}.png"
            metadata = PngImagePlugin.PngInfo()
            metadata.add_text("Authoring", "Literal brush records: textures/paint_strokes.json")
            metadata.add_text("PaintSourceSHA256", digest)
            metadata.add_text("ColorSpace", "sRGB" if channel == "basecolor" else "Non-Color / linear data")
            image.save(path, pnginfo=metadata, optimize=True)
            payload = path.read_bytes()
            result["maps"][channel] = {"path": str(path.relative_to(TEXTURES)).replace("\\", "/"),
                "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload),
                "mode": image.mode, "extrema": image.getextrema(),
                "color_space": "sRGB" if channel == "basecolor" else "Non-Color"}
            manifest["total_bytes"] += len(payload)
        manifest["materials"][name] = result
        material_images[name] = maps
    preview_sheet(material_images)
    (TEXTURES / "paint_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "painted", "materials": list(material_images),
                      "maps": len(material_images)*4, "bytes": manifest["total_bytes"],
                      "paint_source_sha256": digest}, indent=2))


if __name__ == "__main__":
    main()
