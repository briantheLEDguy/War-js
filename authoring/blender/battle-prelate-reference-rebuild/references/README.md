# Battle Prelate reference measurements

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
