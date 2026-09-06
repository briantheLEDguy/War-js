# Authored material paint sources

`paint_strokes.json` contains the complete literal paint record: palettes, brush
outlines, individual paths and spots, opacity, brush softness, and each affected
material channel. `../tools/paint_materials.py` only rasterizes those records with
Pillow. It does not make random marks, noise, scatter, weave, or sample pixels
from the reference illustration. Metal wear appears in material color, roughness
and relief; studio highlights and cast shadows are not painted into the maps.

Run with a Python environment containing Pillow:

```powershell
python tools/paint_materials.py
```

The script writes 24 maps in `source/`, a hash and channel manifest, a base-color
contact sheet, and a complete channel contact sheet. It validates the literal
record before painting. All tiles are 1024 by 1024 pixels.

| Material | Treatment |
| --- | --- |
| steel | Cool metal color, restrained uneven patina, small oxide islands, fine etched scratches and isolated pits |
| dark_steel | Darker metal using the same explicitly authored wear arrangement |
| brass | Subdued warm metal, broad handling wear, small recess patina, fine scratches |
| leather | Dark brown, worn color patches, hand-authored scars and crease marks |
| crimson | Deep red dye, soft fading, fixed fiber-scuff groups and thread fragments |
| parchment | Warm beige, soft age toning and individually authored pale/brown fibers |

Load `*_basecolor.png` as **sRGB**. Roughness, metallic and height are **Non-Color**
data. Metallic is zero throughout leather, crimson and parchment; local painted
oxidation lowers metallic on the metals. These are material-source tiles for the
final UV atlas bake, not finished character atlases.

Height uses 128 as its neutral level. Start the normal bake with a peak-to-peak
height range of 0.0005 m for metals, 0.0004 m for leather and 0.0002 m for cloth or
parchment. The actual painted range is narrower than the full 0–255 range, so
relief is deliberately subtle. Retain authored geometry for the major borders,
folds, facial structure and emblems. Bake occlusion from the assembled geometry;
do not substitute painted color stains for an occlusion map.

Dedicated face paint is recorded separately in `skin_paint_strokes.json` and
rasterized by `../tools/paint_skin.py` at 2048 pixels. Named UV landmarks check
placement against the authored head. The main head half reuses its UVs through
Mirror; generic ear UVs need the separate constant skin material. The paint
preview is useful for placement, but does not establish facial likeness.

Chainmail maps are actual geometry bakes. `../source/chainmail_detail.dat` retains
the newly authored closed link cage (48 vertices and 48 quads), allowed Subdivision
Surface finishing, and 49 explicit copied placements. `../tools/bake_chainmail.py`
loads that finite data and bakes base color, roughness, metallic, tangent normals
and occlusion at 1024 pixels. Base color and scalar materials use emission baking
to exclude studio illumination; normals and occlusion come from the link surfaces.
The flat backing and receiver are bake infrastructure, not character substitutes.
`chainmail_bake_source.blend`, `chainmail_bake_report.json`, and
`chainmail_material_preview.png` retain the inspectable source, hashes and channels.

The tile spans three horizontal link pitches and six rows. Literal UV scale,
offset and seam-corner records in the arms, legs and body-underlayer serializers
place it on visible joint/hip surfaces at approximately 8-10 mm link diameter.
Every final UV coordinate is written into the corresponding source JSON face
corner. `chainmail_remap_report.json` confirms coordinates, topology, transforms,
modifiers and binding metadata were unchanged. Hidden interface caps retain their
original materials; the torso shirt remains padded leather.

These are authored material inputs inspected as contact sheets. Their final
appearance still needs evaluation on the rendered and imported character; they
do not independently establish a photorealistic result.
