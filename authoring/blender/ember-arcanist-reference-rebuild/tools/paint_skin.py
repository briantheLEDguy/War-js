"""Replay literal facial-UV paint and show the authored UV wire for placement QA."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
TEXTURES = ROOT / "textures"
RECORD = TEXTURES / "skin_paint_strokes.json"


def uv_pixels(point, size):
    u, v = point
    if not 0 <= u <= 1 or not 0 <= v <= 1:
        raise ValueError(f"Paint point outside the explicit UV tile: {point}")
    return round(u*(size-1)), round((1-v)*(size-1))


def verify_uv_associations(record, head):
    uv = {}
    for face in head["faces"]:
        for vertex, value in zip(face["vertices"], face["uv"]):
            uv.setdefault(vertex, []).append(value)
    for vertex, expected in record["landmark_uv"].items():
        if expected not in uv.get(vertex, []):
            raise ValueError(f"Head UV landmark changed: {vertex}; update the authored paint placement")


def mask_for_layer(layer, size):
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    if layer["kind"] == "polygons":
        for polygon in layer["shapes"]:
            draw.polygon([uv_pixels(point, size) for point in polygon], fill=layer["opacity"])
    elif layer["kind"] == "paths":
        for path in layer["shapes"]:
            draw.line([uv_pixels(point, size) for point in path], fill=layer["opacity"],
                      width=layer["width"], joint="curve")
    elif layer["kind"] == "spots":
        radius = layer["radius"]
        for point in layer["points"]:
            x, y = uv_pixels(point, size)
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=layer["opacity"])
    else:
        raise ValueError("Only explicit polygon, path and spot paint records are supported")
    return mask.filter(ImageFilter.GaussianBlur(layer.get("softness", 0)))


def placement_preview(basecolor, head, record):
    wire = basecolor.convert("RGBA")
    overlay = Image.new("RGBA", wire.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for face in head["faces"]:
        pts = [uv_pixels(point, record["resolution"]) for point in face["uv"]]
        draw.line(pts+[pts[0]], fill=(48, 64, 65, 128), width=1)
    for vertex, point in record["landmark_uv"].items():
        x, y = uv_pixels(point, record["resolution"])
        draw.ellipse((x-4, y-4, x+4, y+4), fill=(242, 222, 146, 240))
    wire = Image.alpha_composite(wire, overlay).convert("RGB")
    crop = (983, 0, 1852, 1750)
    raw = basecolor.crop(crop).resize((695, 1400), Image.Resampling.LANCZOS)
    wired = wire.crop(crop).resize((695, 1400), Image.Resampling.LANCZOS)
    sheet = Image.new("RGB", (1480, 1530), (28, 30, 34))
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 25)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    draw = ImageDraw.Draw(sheet)
    draw.text((22, 14), "SKIN PAINT / AUTHORED HALF-HEAD UV PLACEMENT", fill=(229, 223, 209), font=font)
    draw.text((22, 50), "Literal pigment, age creases and stubble; no painted lighting. Mirrored geometry shares this half-head UV.", fill=(174, 181, 190), font=small)
    sheet.paste(raw, (22, 93))
    sheet.paste(wired, (758, 93))
    draw.text((32, 103), "BASE COLOR", fill=(245, 237, 217), font=small)
    draw.text((768, 103), "UV WIRE + LANDMARKS", fill=(245, 237, 217), font=small)
    sheet.save(TEXTURES / "skin_uv_paint_preview.png", optimize=True)


def main():
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    if record["resolution"] != 2048 or record["schema_version"] != 1:
        raise ValueError("Expected the authored 2048 skin paint record")
    source = json.loads((ROOT / "source/head.json").read_text(encoding="utf-8"))
    head = next(part for part in source["parts"] if part["id"] == "head_skin")
    verify_uv_associations(record, head)
    size = record["resolution"]
    maps = {channel: Image.new("RGB" if channel == "basecolor" else "L", (size, size),
                               tuple(value) if isinstance(value, list) else value)
            for channel, value in record["base"].items()}
    for layer in record["layers"]:
        mask = mask_for_layer(layer, size)
        for channel, value in layer["paint"].items():
            color = tuple(value) if isinstance(value, list) else value
            paint = Image.new(maps[channel].mode, (size, size), color)
            maps[channel].paste(paint, (0, 0), mask)
    digest = hashlib.sha256(RECORD.read_bytes()).hexdigest()
    output = {}
    for channel, image in maps.items():
        path = TEXTURES / "source" / f"skin_{channel}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Authoring", "Literal facial UV brush records: textures/skin_paint_strokes.json")
        metadata.add_text("PaintSourceSHA256", digest)
        metadata.add_text("ColorSpace", "sRGB" if channel == "basecolor" else "Non-Color / linear data")
        image.save(path, pnginfo=metadata, optimize=True)
        output[channel] = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "extrema": image.getextrema()}
        with Image.open(path) as verify:
            assert verify.size == (2048, 2048)
            assert verify.mode == ("RGB" if channel == "basecolor" else "L")
            verify.verify()
    placement_preview(maps["basecolor"], head, record)
    print(json.dumps({"status": "painted and UV associations verified",
                      "paint_source_sha256": digest, "maps": output}, indent=2))


if __name__ == "__main__":
    main()
