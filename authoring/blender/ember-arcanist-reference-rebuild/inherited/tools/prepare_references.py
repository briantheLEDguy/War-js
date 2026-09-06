"""Crop and annotate the supplied board using literal, estimated pixel records.

This script does not generate character geometry or synthetic image content.
Pillow copies source pixels, enlarges review crops, and draws measurement marks.
Coordinates describe an illustrated reference, not calibrated orthographic data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


SOURCE = Path(r"C:\Users\bschm\Downloads\Codex Image Aug 31, 2026, 07_28_04 PM.png")
SOURCE_SHA256 = "070983f09ee18cc83385a1719df7055f63eaddd26c0708e2c731f5e661f7cec0"
OUTPUT = Path(__file__).resolve().parents[1] / "references"
SIZE = (1448, 1086)

# Bounds are [left, top, right, bottom], right/bottom exclusive (Pillow convention).
CROPS = {
    "front_whole": [17, 88, 454, 731],
    "front_upperbody": [128, 90, 452, 335],
    "threequarter_whole": [469, 97, 753, 625],
    "side_whole": [772, 99, 934, 622],
    "back_whole": [948, 98, 1250, 624],
    "detail_front_head_gorget": [216, 91, 329, 224],
    "detail_front_left_pauldron": [327, 135, 450, 288],
    "detail_front_breastplate": [175, 190, 375, 333],
    "detail_front_belt_tabard": [126, 317, 387, 631],
    "detail_front_tome": [308, 326, 397, 451],
    "detail_front_hammer": [2, 100, 128, 714],
    "detail_gorget_inset": [468, 641, 592, 779],
    "detail_medallion_inset": [651, 638, 771, 788],
    "detail_prayer_seal_inset": [838, 645, 907, 792],
    "detail_tome_inset": [464, 799, 576, 947],
    "detail_censer_inset": [661, 797, 786, 947],
    "detail_shoulder_icon_inset": [818, 797, 937, 947],
    "detail_modular_head": [1004, 666, 1073, 745],
    "detail_palette": [1250, 632, 1438, 1074],
}

# id, name, source x, source y, uncertainty radius in source pixels, visibility.
# Anatomical left is image-right in the main front view.
LANDMARKS = {
    "front": [
        ("F01", "crown", 273, 96, 3, "visible"),
        ("F02", "chin", 271, 166, 7, "partly_occluded_by_gorget"),
        ("F03", "collar_front_rim_center", 268, 170, 4, "visible"),
        ("F04", "collar_left_side_rim", 309, 151, 5, "partly_occluded"),
        ("F05", "left_pauldron_peak", 371, 147, 4, "visible"),
        ("F06", "left_pauldron_outer_edge", 443, 255, 5, "visible"),
        ("F07", "right_pauldron_peak", 208, 148, 5, "visible"),
        ("F08", "right_pauldron_outer_edge", 143, 246, 5, "visible"),
        ("F09", "breastplate_top_center", 263, 208, 7, "partly_occluded_by_trim"),
        ("F10", "chest_medallion_center", 248, 258, 4, "visible"),
        ("F11", "waist_belt_upper_center", 252, 324, 7, "partly_occluded_by_ornament"),
        ("F12", "belt_buckle_center", 240, 354, 5, "visible"),
        ("F13", "tabard_center_hem", 246, 613, 7, "frayed_edge"),
        ("F14", "left_knee_center", 348, 551, 6, "visible"),
        ("F15", "right_knee_center", 167, 541, 6, "visible"),
        ("F16", "left_ankle_plate_center", 374, 663, 7, "joint_under_armor"),
        ("F17", "right_ankle_plate_center", 137, 649, 7, "joint_under_armor"),
        ("F18", "lowest_boot_contact", 372, 729, 3, "visible"),
        ("F19", "right_boot_contact", 140, 709, 4, "visible"),
        ("F20", "hammer_top_finial", 48, 104, 3, "visible"),
        ("F21", "hammer_bottom_finial", 70, 710, 3, "visible"),
        ("F22", "hammer_head_center", 62, 213, 6, "visible"),
        ("F23", "left_glove_center", 417, 431, 8, "visible"),
        ("F24", "right_gripping_hand_center", 52, 324, 7, "visible"),
    ],
    "threequarter": [
        ("Q01", "crown", 611, 106, 3, "visible"),
        ("Q02", "chin", 606, 160, 6, "partly_occluded_by_gorget"),
        ("Q03", "collar_front_rim", 587, 164, 5, "visible"),
        ("Q04", "near_pauldron_peak", 662, 145, 5, "visible"),
        ("Q05", "near_pauldron_outer_edge", 736, 232, 5, "visible"),
        ("Q06", "chest_medallion_center", 567, 230, 5, "visible"),
        ("Q07", "waist_belt_upper_center", 585, 286, 7, "partly_occluded"),
        ("Q08", "tabard_center_hem", 572, 514, 6, "frayed_edge"),
        ("Q09", "near_knee_center", 653, 466, 5, "visible"),
        ("Q10", "far_knee_center", 527, 473, 7, "oblique"),
        ("Q11", "near_ankle_plate_center", 670, 560, 6, "joint_under_armor"),
        ("Q12", "lowest_boot_contact", 670, 618, 3, "visible"),
        ("Q13", "hammer_top_finial", 514, 142, 3, "visible"),
        ("Q14", "hammer_bottom_finial", 481, 597, 4, "visible"),
    ],
    "side": [
        ("S01", "crown", 854, 107, 3, "visible"),
        ("S02", "chin", 836, 160, 7, "partly_occluded_by_gorget"),
        ("S03", "collar_front_rim", 812, 168, 5, "visible"),
        ("S04", "collar_back_rim", 887, 149, 5, "visible"),
        ("S05", "pauldron_peak", 862, 153, 5, "visible"),
        ("S06", "pauldron_back_edge", 927, 235, 5, "visible"),
        ("S07", "chest_front_projection", 792, 225, 7, "partly_occluded_by_seals"),
        ("S08", "waist_belt_front", 791, 286, 6, "partly_occluded_by_book"),
        ("S09", "tabard_front_hem", 785, 548, 8, "partly_occluded"),
        ("S10", "near_knee_center", 814, 472, 6, "visible"),
        ("S11", "near_ankle_plate_center", 854, 563, 7, "joint_under_armor"),
        ("S12", "lowest_boot_contact", 821, 618, 3, "visible"),
        ("S13", "nose_tip", 823, 139, 3, "visible"),
        ("S14", "back_skull", 881, 124, 4, "visible"),
    ],
    "back": [
        ("B01", "crown", 1100, 106, 3, "visible"),
        ("B02", "collar_back_rim_center", 1096, 144, 4, "visible"),
        ("B03", "left_pauldron_peak_image_left", 1017, 149, 5, "visible"),
        ("B04", "right_pauldron_peak_image_right", 1170, 149, 5, "visible"),
        ("B05", "left_pauldron_outer_edge", 968, 235, 5, "visible"),
        ("B06", "right_pauldron_outer_edge", 1234, 232, 5, "visible"),
        ("B07", "backplate_icon_center", 1093, 203, 5, "visible"),
        ("B08", "waist_belt_upper_center", 1096, 287, 6, "visible"),
        ("B09", "rear_tabard_hem_center", 1094, 568, 7, "frayed_edge"),
        ("B10", "left_knee_level_estimate", 1026, 470, 13, "occluded_by_cloth"),
        ("B11", "right_knee_level_estimate", 1161, 470, 13, "occluded_by_cloth"),
        ("B12", "left_ankle_center", 1013, 565, 8, "joint_under_armor"),
        ("B13", "right_ankle_center", 1169, 569, 8, "joint_under_armor"),
        ("B14", "lowest_boot_contact", 1168, 616, 4, "visible"),
    ],
}

# Deliberately sparse, hand-traced visible outlines. No automatic segmentation.
# Small decorations, separate dangling objects and hammer are excluded.
SILHOUETTES = {
    "front": [
        [273, 96], [290, 100], [300, 114], [302, 136], [299, 150],
        [315, 148], [327, 162], [342, 165], [355, 155], [371, 147],
        [388, 158], [419, 176], [432, 202], [429, 223], [443, 255],
        [441, 268], [451, 301], [445, 326], [452, 354], [440, 402],
        [447, 426], [434, 452], [414, 465], [396, 454], [407, 491],
        [401, 523], [405, 567], [413, 611], [428, 651], [414, 654],
        [402, 679], [409, 706], [401, 723], [379, 729], [351, 724],
        [331, 711], [326, 691], [334, 669], [318, 648], [301, 600],
        [286, 627], [261, 631], [239, 650], [207, 638], [206, 608],
        [191, 638], [187, 667], [178, 694], [161, 706], [129, 711],
        [100, 706], [96, 692], [110, 672], [125, 652], [134, 601],
        [136, 562], [140, 535], [136, 485], [150, 451], [145, 420],
        [157, 370], [171, 343], [155, 329], [136, 347], [110, 357],
        [82, 349], [63, 356], [40, 352], [28, 339], [25, 321],
        [34, 303], [53, 296], [75, 309], [104, 296], [126, 287],
        [139, 266], [143, 246], [157, 224], [157, 189], [177, 180],
        [192, 164], [204, 149], [213, 149], [223, 165], [240, 168],
        [247, 150], [244, 130], [247, 110], [257, 100],
    ],
    "threequarter": [
        [611, 106], [628, 110], [636, 127], [635, 143], [649, 146],
        [662, 145], [680, 154], [708, 165], [722, 184], [725, 211],
        [736, 232], [730, 249], [734, 277], [743, 300], [731, 343],
        [726, 370], [717, 394], [697, 402], [704, 432], [696, 462],
        [713, 501], [720, 546], [706, 550], [702, 575], [705, 596],
        [692, 614], [667, 618], [641, 613], [627, 603], [630, 580],
        [620, 553], [604, 521], [587, 522], [572, 515], [554, 530],
        [546, 566], [540, 587], [524, 602], [500, 602], [491, 593],
        [500, 575], [515, 557], [516, 528], [517, 491], [516, 464],
        [526, 422], [520, 395], [531, 351], [541, 322], [533, 307],
        [516, 324], [497, 327], [486, 315], [487, 298], [500, 286],
        [516, 291], [530, 273], [538, 240], [544, 207], [557, 190],
        [569, 177], [572, 159], [590, 153], [591, 131], [590, 117],
    ],
    "side": [
        [854, 107], [868, 109], [879, 118], [881, 133], [873, 145],
        [897, 147], [914, 158], [923, 186], [925, 217], [928, 236],
        [913, 248], [913, 272], [919, 291], [914, 321], [916, 349],
        [904, 373], [887, 390], [887, 419], [906, 452], [911, 494],
        [925, 549], [910, 552], [904, 581], [898, 603], [879, 610],
        [851, 617], [818, 619], [789, 617], [782, 609], [790, 596],
        [810, 583], [823, 574], [822, 550], [810, 521], [807, 494],
        [798, 482], [798, 454], [803, 435], [793, 419], [784, 435],
        [780, 408], [783, 376], [778, 352], [781, 316], [785, 284],
        [788, 252], [791, 224], [805, 199], [804, 174], [815, 164],
        [831, 158], [830, 150], [823, 141], [828, 136], [830, 122],
    ],
    "back": [
        [1100, 106], [1113, 109], [1120, 123], [1121, 142],
        [1141, 141], [1145, 158], [1161, 164], [1170, 149],
        [1185, 160], [1209, 172], [1223, 191], [1227, 215],
        [1234, 232], [1223, 250], [1233, 274], [1238, 301],
        [1223, 331], [1217, 346], [1224, 368], [1211, 389],
        [1198, 398], [1198, 437], [1203, 477], [1190, 521],
        [1202, 566], [1187, 580], [1191, 601], [1180, 615],
        [1156, 616], [1144, 607], [1147, 577], [1126, 575],
        [1108, 580], [1085, 573], [1062, 573], [1044, 569],
        [1044, 595], [1035, 611], [1013, 616], [991, 611],
        [979, 600], [988, 579], [988, 552], [981, 514],
        [988, 477], [981, 445], [986, 416], [976, 391],
        [974, 367], [977, 347], [963, 331], [964, 306],
        [970, 279], [978, 252], [968, 235], [980, 219],
        [981, 191], [994, 175], [1017, 149], [1024, 161],
        [1031, 169], [1055, 158], [1057, 145], [1084, 144],
        [1082, 130], [1085, 115],
    ],
}

# Separate trace of the image-right/anatomical-left pauldron and lower shell.
DETAIL_TRACES = {
    "front_left_pauldron_main_shell": [
        [371, 147], [387, 157], [402, 165], [419, 176], [429, 193],
        [426, 210], [413, 221], [397, 232], [378, 240], [359, 235],
        [344, 220], [337, 201], [337, 180], [343, 164], [355, 155],
    ],
    "front_left_pauldron_lower_shell": [
        [404, 220], [418, 216], [429, 227], [435, 242], [443, 255],
        [437, 266], [419, 269], [398, 263], [382, 253], [378, 240],
    ],
}

# Review-label offsets in output pixels; close chin/rim points need separate tags.
LABEL_OFFSETS = {"F02": (-38, -31), "F03": (8, 4)}

DISAGREEMENTS = [
    {
        "id": "scale_and_camera",
        "observation": "The main front character occupies 633 px; the other figures occupy about 510-512 px. The sheet is not four equal-scale orthographic projections.",
        "decision": "Use the main front's 1.86 m / 633 px convention for approximate vertical comparisons only. Do not apply its pixel-to-meter factor to other views.",
    },
    {
        "id": "feet_and_pose",
        "observation": "The front boot contacts differ by about 20 px; the front head, torso, and weight-bearing stance are offset. The arm holding the hammer is extended differently in other views.",
        "decision": "The lowest front boot contact defines the chosen scale. Do not infer limb-length asymmetry, flatten the soles to a pixel row, or bake pose offsets into rest anatomy.",
    },
    {
        "id": "head_and_collar",
        "observation": "The collar obscures the chin, while the side profile exposes a different jaw/nose silhouette. No camera calibration fixes their correspondence.",
        "decision": "Treat the chin as +/-7 px in the front. Use the side primarily for depth/profile and the front for breadth; keep the source head centered as specified in CONTRACT.md.",
    },
    {
        "id": "pauldron_occlusion",
        "observation": "The far/front-image-left pauldron is foreshortened and overlaps the arm/mail differently. Raised borders and icons obscure exact plate boundaries.",
        "decision": "Use the anatomical-left/front-image-right pauldron as the proof component. Main and lower shell traces are interpretive visible contours, not exact seam topology.",
    },
    {
        "id": "cloth_and_accessories",
        "observation": "Tabard split, fringe, mail exposure, tome tilt, seals, and hanging censer differ in placement and overlap across views. Rear knees are obscured.",
        "decision": "Preserve the reference's general placement and density with one coherent model. Do not triangulate hidden knee points or treat individual fringe tips as fixed 3D targets.",
    },
    {
        "id": "lighting_and_surface",
        "observation": "Highlights, cast shadows, painted edge wear, and ambient shading are embedded in the illustrated pixels; inset views also use different framing.",
        "decision": "Use crops for visual study. They are not clean albedo, roughness, normal, or displacement maps and are not evidence of measured physical dimensions.",
    },
    {
        "id": "hammer",
        "observation": "Main front hammer endpoints are y=104 and y=710, while the character endpoints are y=96 and y=729. The weapon is angled and shown at differing sizes in the insets.",
        "decision": "Exclude the hammer from character scale; separate endpoints and head-center measurements are for placement review only.",
    },
]


def font(size: int) -> ImageFont.ImageFont:
    for candidate in (Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\arial.ttf")):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


def landmark_records() -> dict[str, list[dict]]:
    result = {}
    for view, points in LANDMARKS.items():
        result[view] = []
        for ident, name, x, y, uncertainty, visibility in points:
            row = {"id": ident, "name": name, "raw_pixel": [x, y],
                   "uncertainty_radius_px": uncertainty, "visibility": visibility,
                   "method": "literal_manual_visual_estimate"}
            if view == "front":
                row["approximate_front_vertical_z_m"] = round((729 - y) * 1.86 / 633, 4)
            result[view].append(row)
    return result


def annotation(source: Image.Image, view: str, crop_name: str, scale: int = 2) -> Image.Image:
    box = CROPS[crop_name]
    cropped = source.crop(box)
    selected = [p for p in LANDMARKS[view] if box[0] <= p[2] < box[2] and box[1] <= p[3] < box[3]]
    width, height = cropped.width * scale, cropped.height * scale
    panel_width = 520
    output_height = max(height + 82, 110 + len(selected) * 38 + 145)
    canvas = Image.new("RGB", (width + panel_width, output_height), "#141A20")
    canvas.paste(cropped.resize((width, height), Image.Resampling.LANCZOS), (0, 58))
    draw = ImageDraw.Draw(canvas)
    draw.text((18, 13), crop_name.replace("_", " ").upper(), font=font(23), fill="#F4E3BA")
    draw.text((width + 20, 18), "ESTIMATED SOURCE PIXELS", font=font(21), fill="#F4E3BA")

    def local(p):
        return ((p[0] - box[0]) * scale, (p[1] - box[1]) * scale + 58)

    # Clipping onto a source-sized transparent overlay prevents traces outside
    # upper-body crops from drawing into the annotation key below the image.
    overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    outline = SILHOUETTES[view]
    overlay_draw.line([tuple(p) for p in outline + outline[:1]], fill=(64, 224, 210, 220), width=2)
    if view == "front":
        for trace in DETAIL_TRACES.values():
            overlay_draw.line([tuple(p) for p in trace + trace[:1]], fill=(242, 143, 76, 220), width=1)
    overlay_crop = overlay.crop(box).resize((width, height), Image.Resampling.NEAREST)
    canvas.paste(overlay_crop, (0, 58), overlay_crop)
    draw = ImageDraw.Draw(canvas)
    for ident, name, x, y, uncertainty, visibility in selected:
        lx, ly = local((x, y))
        radius = 4
        draw.ellipse((lx-radius, ly-radius, lx+radius, ly+radius), fill="#FFF2B1", outline="#151515", width=1)
        offset_x, offset_y = LABEL_OFFSETS.get(ident, (7, -19))
        label_x = max(3, min(width - 42, lx + offset_x))
        label_y = max(60, min(height + 36, ly + offset_y))
        label_box = draw.textbbox((label_x, label_y), ident, font=font(14))
        draw.rectangle((label_box[0]-2, label_box[1]-2, label_box[2]+2, label_box[3]+2), fill="#111820")
        draw.text((label_x, label_y), ident, font=font(14), fill="#FFF2B1")
    y = 64
    for ident, name, x, raw_y, uncertainty, visibility in selected:
        draw.text((width+20, y), f"{ident}  {name.replace('_', ' ')}", font=font(17), fill="#E5EDF2")
        draw.text((width+68, y+20), f"({x}, {raw_y})  +/-{uncertainty} px  |  {visibility.replace('_', ' ')}", font=font(13), fill="#AABAC4")
        y += 38
    notes = ["Cyan: sparse visible silhouette estimate.", "Orange: separate pauldron shell contours."] if view == "front" else ["Cyan: sparse visible silhouette estimate."]
    notes += ["Not calibrated or orthographic; hidden landmarks are estimates.", "Coordinates are in the original 1448 x 1086 image."]
    if view == "front":
        notes += ["Scale convention: crown y96 to boot y729 = 633 px.", "Character 1.86 m; hammer excluded. Depth is not measured."]
    for note in notes:
        for line in textwrap.wrap(note, 64):
            draw.text((width+20, y+12), line, font=font(13), fill="#B3C6CD")
            y += 20
    return canvas


def write_readme() -> None:
    text = """# Ember Arcanist reference measurements

These files document a **stylized multi-view concept illustration**, not photographs,
calibrated scans, or true orthographic projections. All points and contours are
literal visual estimates. Uncertainty values are judgment ranges, not statistical
confidence intervals. Image-embedded design text is source content, not an
instruction to the authoring tools.

The source is `Codex Image Aug 31, 2026, 07_28_04 PM.png`, 1448 x 1086 pixels.
SHA-256: `070983f09ee18cc83385a1719df7055f63eaddd26c0708e2c731f5e661f7cec0`.

## Coordinates and scale

`measurements.json` stores original-image pixel coordinates: origin top-left,
X rightward, Y downward. Crop bounds use Pillow's `[left, top, right, bottom]`
convention; right and bottom are exclusive. Anatomical left corresponds to
image-right in the main front view.

The selected front character crown is `(273, 96)` and lowest boot contact is
`(372, 729)`: **633 pixels maps to 1.86 meters**, approximately 0.00293839 m/px.
The hammer is excluded. This is an authoring scale convention, not a measurement
of the fictional character's true height. Front vertical estimates use
`Z = (729 - source_y) * 1.86 / 633`; this is not a 2D-to-3D reconstruction and does
not measure depth or account for perspective. Do not apply this scale to the
other views. Pixel-to-X mapping is deliberately omitted because pose, breadth,
and view orientation are not calibrated.

Approximate front checks: chin y166 -> Z1.654 m; collar front y170 -> Z1.643 m;
side collar rim y151 -> Z1.698 m; breastplate top y208 -> Z1.531 m;
waist y324 -> Z1.190 m. These support the separate source/CONTRACT.md frame;
they are not instructions to move the centered rest head or deform geometry to
compensate for a review camera. The two boot contact rows differ due to pose/view.

## Files

- `crops/*.png`: unannotated source pixels at original resolution, including all
  four figure views, front upper body, and detail insets.
- `annotated_front.png`, `annotated_threequarter.png`, `annotated_side.png`,
  `annotated_back.png`: enlarged review views with numbered keys, literal pixel
  coordinates, and uncertainty. Cyan traces approximate the visible silhouette.
- `annotated_front_upperbody.png`: enlarged proof-component view; orange traces
  identify the main anatomical-left pauldron shell and overlapping lower shell.
- `measurements.json`: machine-readable crops, landmarks, silhouettes, scale,
  and recorded disagreements. No field is automatically derived by segmentation.
- `view_disagreements.md`: observations and interpretation decisions.

Enlargement improves annotation readability; it adds no reference detail. All
material colors, lighting, shading, scratches, and shadows remain those of the
original illustration. Crops are not ready-made PBR texture maps.

Regenerate from this directory's parent:

```powershell
& 'C:/Users/bschm/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/prepare_references.py
```

The script checks the source size/hash and landmark bounds before writing only
this `references/` directory. It creates no geometry and makes no Blender changes.
"""
    (OUTPUT / "README.md").write_text(text, encoding="utf-8")
    disagreements = "# View disagreements and interpretation\n\nThese are observations about source art, not proof of exact 3D geometry.\n"
    for item in DISAGREEMENTS:
        disagreements += f"\n## {item['id'].replace('_', ' ').title()}\n\n{item['observation']}\n\n{item['decision']}\n"
    (OUTPUT / "view_disagreements.md").write_text(disagreements, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != SOURCE_SHA256:
        raise ValueError(f"Reference hash differs: {actual_hash}")
    source = Image.open(args.source).convert("RGB")
    if source.size != SIZE:
        raise ValueError(f"Expected source size {SIZE}; got {source.size}")
    for name, box in CROPS.items():
        if not (0 <= box[0] < box[2] <= SIZE[0] and 0 <= box[1] < box[3] <= SIZE[1]):
            raise ValueError(f"Out-of-bounds crop: {name}")
    records = landmark_records()
    for view, rows in records.items():
        for row in rows:
            x, y = row["raw_pixel"]
            if not (0 <= x < SIZE[0] and 0 <= y < SIZE[1]):
                raise ValueError(f"Out-of-bounds landmark: {view}:{row['id']}")
    if LANDMARKS["front"][17][3] - LANDMARKS["front"][0][3] != 633:
        raise ValueError("Front character scale must remain 633 px")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "crops").mkdir(exist_ok=True)
    for name, box in CROPS.items():
        source.crop(box).save(OUTPUT / "crops" / f"{name}.png")
    dataset = {
        "schema_version": 1,
        "source": {"path": str(args.source.resolve()), "sha256": actual_hash, "size_px": list(SIZE),
                   "kind": "stylized_multiview_concept_illustration", "calibrated": False, "orthographic": False},
        "coordinate_frame": {"origin": "top_left", "x_axis": "right", "y_axis": "down", "units": "source_pixels",
                             "left_right": "anatomical_left_is_image_right_in_front"},
        "scale_convention": {"view": "front", "crown_landmark": "F01", "ground_landmark": "F18",
                             "character_height_px": 633, "chosen_character_height_m": 1.86,
                             "approximate_m_per_front_vertical_px": 1.86 / 633, "hammer_excluded": True,
                             "not_valid_for": ["other_view_pixel_scales", "depth", "camera_calibration", "exact_anatomy"]},
        "crop_bounds_convention": "left_top_right_bottom_exclusive",
        "crops": {name: {"bounds_px": bounds, "file": f"crops/{name}.png"} for name, bounds in CROPS.items()},
        "landmarks": records,
        "silhouettes": {name: {"raw_pixels": points, "closed": True,
                                "uncertainty_px": {"typical": 8, "cloth_or_occluded_edges": 20},
                                "method": "literal_manual_sparse_visible_outline", "excludes": ["hammer", "small_dangling_accessories"]}
                        for name, points in SILHOUETTES.items()},
        "detail_contours": {name: {"raw_pixels": points, "closed": True, "uncertainty_px": 4,
                                    "method": "literal_manual_visible_plate_boundary"} for name, points in DETAIL_TRACES.items()},
        "view_disagreements": DISAGREEMENTS,
    }
    (OUTPUT / "measurements.json").write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")
    for view in LANDMARKS:
        annotation(source, view, f"{view}_whole").save(OUTPUT / f"annotated_{view}.png")
    annotation(source, "front", "front_upperbody", scale=3).save(OUTPUT / "annotated_front_upperbody.png")
    write_readme()
    print(json.dumps({"output": str(OUTPUT), "source_sha256": actual_hash, "crops": len(CROPS),
                      "landmarks": sum(len(rows) for rows in records.values()), "annotated_images": 5,
                      "front_character_height_px": 633, "chosen_character_height_m": 1.86}, indent=2))


if __name__ == "__main__":
    main()
