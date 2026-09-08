# Sunmeadow late-summer nature kit

Seven original environmental assets are authored here. The source follows the
Battle Prelate package's separation of editable geometry, delivery LODs,
material authoring, technical validation and actual-export visual review. These
are stylized game assets; botanical references guide species traits, not a claim
of photographic reconstruction or final user acceptance.

| Runtime key suffix (all begin `frontier_sunmeadow_`) | LOD0 / LOD1 / LOD2 triangles | Materials |
|---|---:|---:|
| `oak_pasture` | 83,874 / 45,124 / 11,548 | 2 |
| `oak_hedgerow` | 63,468 / 34,100 / 8,756 | 2 |
| `ash` | 86,766 / 35,852 / 12,790 | 2 |
| `hawthorn` | 34,272 / 13,584 / 4,140 | 2 |
| `wheat` | 18,144 / 8,208 / 3,600 | 1 |
| `meadow` | 13,308 / 7,282 / 2,666 | 1 |
| `limestone` | 6,402 / 3,202 / 1,602 | 1 |

`source/design.json` contains literal tree trunk and principal bough paths,
species direction, and reference links. `tools/build_nature.py` authors uneven
branch cross-sections, curved secondary branches, connected terminal growth,
raised leaf midribs and lobed leaf outlines. Ash has paired compound leaflets;
hawthorn has deeper leaf lobes, interwoven branches and ripening haws. Wheat
retains individually shaped spikelets, awns and bent flag leaves. Meadow clumps
combine folded green/dry blades, seed heads, knapweed and a few oxeye daisies.
The limestone has three separately shaped fracture masses, exposed sedimentary
beds, eroded ledges, irregular upper planes and loose chips.

No mesh primitive operators, transparent canopy cards, foliage blobs or cone
substitutes are used. Leaves and blades are opaque, double-sided surfaces.
Each LOD is built from the same growth layout with fewer contour samples,
retained foliage subsets, reduced twig work and deliberate blade/crown coverage
compensation. Lower LODs retain actual branch and leaf geometry.

`masters/` holds seven packed Blender files with named editable parts and
separate LOD collections. `source/*_authored_paths.json` records evaluated branch
paths and original controls. `textures/` retains original 1024px base color,
tangent normal and packed occlusion/roughness/metallic maps plus their paint
record. Foliage uses species-specific UV atlas tiles with midrib/vein detail;
bark uses staggered fissures and plates; stone uses bedding, grain and lichen.
These are authored surface fields, not photographic or high-mesh bake claims.
All delivery textures are embedded in the GLBs.

## Placement and performance

Use the exact runtime-axis bounds in `review/*_build.json`, reserving an
additional 0.5m around tree crowns for their LOD coverage changes. Origins mark
the planted base; roots extend approximately 0.2m underground. Tree collision
should follow the trunk, and wheat/meadow remain nonblocking. The hedge is
about 4.8m long; use its full measured width when arranging field boundaries.

Start with tree LOD transitions near 30m and 90m; hedges near 18m and 55m;
wheat/meadow near 12m and 30m, with groundcover culled beyond roughly 80m.
These are integration starting points, not measured frame-rate guarantees.
Batch repeated meshes by asset, LOD and material, preserve culling bounds, and
profile the full scene with actors and effects. The nearest tree meshes should
not be used indiscriminately across a 1.2km landscape. Static foliage currently
has no wind animation, seasonal growth, destruction or collision mesh export.

## Rebuild, review and publish

Run from the repository root with Blender 5.0, its bundled NumPy, and Node:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --threads 4 --python-exit-code 1 --python authoring/blender/sunmeadow-nature/tools/build_nature.py
node authoring/blender/sunmeadow-nature/tools/write_blueprints.mjs
node authoring/blender/sunmeadow-nature/tools/validate_nature.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --threads 4 --python-exit-code 1 --python authoring/blender/sunmeadow-nature/tools/reimport_review.py
node authoring/blender/sunmeadow-nature/tools/publish_nature.mjs --prepare-review
python authoring/blender/sunmeadow-nature/tools/contact_sheet.py
```

Both Blender tools accept `-- --assets oak_pasture,limestone`; the review tool
also accepts `--lods 0,1,2`. Rebuilding changes evidence hashes. Do not rebuild
an asset while its GLB is being rendered. The reimport renderer detects that
race and rejects the resulting evidence.

Review images are `review/frontier_sunmeadow_<kind>_lod<level>_reimport.png`.
`review/*_renders.json` binds each image to its actual GLB hash. Inspect all
three levels and the original scale, then record an explicit `approved` status,
reviewer, ISO date and candid notes in the corresponding entry of
`review/visual_review.json`. Preparing review evidence never approves an asset.
`review/exports_contact_sheet.png` compares all seven assets and their three
LODs at equal pixels per metre within each row. The Pillow contact-sheet tool
uses the unretouched actual export images and checks their model/image hashes;
its sidecar preserves that provenance. The smaller `_preview.png` is for quick
screen review. Hawthorn LOD1 has thinner coverage than LOD0, while its enlarged
LOD2 leaves preserve distant hedge coverage; inspect those transitions in scene.

After that internal review, the integrator can run:

```powershell
node authoring/blender/sunmeadow-nature/tools/publish_nature.mjs --publish
npm run models:registry
```

The publisher also accepts `--assets=oak_pasture,limestone`. It validates all
technical records and all selected visual evidence before changing any public
binary or approved record. It writes the selected standard approved manifests,
all three public GLBs and hash-bound QC sidecars. Embedded textures need no
separate public copy. Registry compilation is deliberately separate; approved
manifests compile to `runtimeReady: true`, `lifecycleStatus: approved` and
`reviewStatus: approved`, with the QC hash needed by the strict frontier loader.

The seven current deliveries passed internal actual-export review and were
published to the local public model directory; their signed review and QC
records retain the exact accepted hashes. Subsequent rebuilds require matching
review evidence before publication. Neither these records nor this README
assert that the wider zone art replacement or target frame rate is complete.
