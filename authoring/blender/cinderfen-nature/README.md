# Cinderfen authored ecology

Four original models for the autumn geothermal marsh: a steam-damaged alder,
reed colony, rust sedge with marsh horsetail, and irregular fractured basalt.
All four assets are internally accepted and published at exact reviewed hashes.
Their separate receipts retain the original reviewed build and image evidence.
The accepted architecture package is separate and remains frozen.

The source retains the main bole and limb paths, asymmetrical cross-sections,
rounded alder and lanceolate grass outlines, reed attachment points, sedge tufts,
rock fracture surveys and expanded mesh/UV records for all three LODs. Main
alder roots and limbs form one joined bark shell. The master retains their
original cages; exact union and a small concave-junction finish preserve the UV
fields. A 0.05mm cleanup removes intersection slivers below float32 tangent
resolution, leaving the fine shoots untouched. Leaves have physical rims and
midrib folds. Distant
organs retain closed outlines and reduced branch/leaf populations. Rocks retain
four unequal cleavage masses with localized chips and shared-edge finishing.
No Blender primitive constructors, generic imported models or canopy cards are
used. The models are static: they do not claim wind or skeletal animation.

Eight original 1024-pixel painted fields provide base color, tangent normal,
roughness, ambient occlusion and zero metallic. The alder additionally uses a
continuous object-space bark field with age-weighted longitudinal fissures,
broad pigment variation, damp roots and restrained lichen, baked into measured
4096/2048/1024 atlases. Basalt uses continuous object-space mineral pigment,
pitting and fracture fields baked into 2048/1024/512 atlases. Its original triangle
positions are unchanged; one microscopic bevel facet has a recorded geometric
normal correction to remove an invalid tangent. Original UVs and shader sources remain in the master;
runtime exports contain only their actual bake UV. Basalt uses continuous
mineral, weathering and cooling-fracture fields baked to 2048/1024/512 atlases.
Its finished triangle positions are independently checked against the previous
actual exports; one sub-square-millimetre bevel facet uses its geometric normal
to resolve an undefined tangent from the inherited weighted normals. Height source images remain
inspectable. Plant fibres and leaf veins follow the authored UV direction.
Pillow writes rows from top to bottom, so normal RGB derives from
`(-dH/dx, +dH/dy, +1)`; a focused test verifies that signed convention against
every saved height image. Shared GLB textures are content-addressed and signed
in each LOD and QC record. Repeated organs intentionally share material UVs.

## Files

- `source/nature.json`: original design and explicit LOD mesh records.
- `source/provenance.json`: exact tool and retained utility reference hashes.
- `textures/paint-records.json`: painter/source channel hashes.
- `masters/`: editable packed Blender masters, one per model.
- `runtime/`: staged actual GLBs; `textures/cinderfen_nature/`: shared images.
- `review/`: actual GLB reimport images, positional topology, distance cameras,
  validation reports and the internal visual-acceptance receipt.
- `build-report.json`: measured triangles, bounds and complete current hashes.
- `builder-metadata.json`: model-space navigation/placement metadata; readiness
  is tracked per asset after internal visual acceptance. Package readiness remains
  false until every model is accepted; this never hides accepted siblings.

## Rebuild and verify

Run commands from the repository root, checking each exit status before moving
on. Coordinate CPU resources with other asset work. Blender uses three threads.
These are authoring commands, not a publication refresh: preserve the accepted
masters, models, textures and receipts. New revisions need isolated outputs and
a new visual review before replacing a published asset.

```powershell
python authoring/blender/cinderfen-nature/tools/author_nature.py
python authoring/blender/cinderfen-nature/tools/paint_nature.py
python authoring/blender/cinderfen-nature/tools/test_source.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python-exit-code 1 --threads 3 --python authoring/blender/cinderfen-nature/tools/build_nature.py
python authoring/blender/cinderfen-nature/tools/share_textures.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python-exit-code 1 --threads 3 --python authoring/blender/cinderfen-nature/tools/audit_alder_joins.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python-exit-code 1 --threads 3 --python authoring/blender/cinderfen-nature/tools/review_nature.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python-exit-code 1 --threads 3 --python authoring/blender/cinderfen-nature/tools/review_alder_joins.py
python authoring/blender/cinderfen-nature/tools/contact_sheet.py
python authoring/blender/cinderfen-nature/tools/write_provenance.py
node authoring/blender/cinderfen-nature/tools/validate_nature.mjs
```

Technical checks do not approve appearance. Review the 12 neutral and 12 measured
distance views plus four material close views and the lower alder junction view. Then retain named, dated internal
acceptance in `review/review.json`, binding the final build, both contact sheets
and every required image plus the actual trunk-join audit. `validate_nature.mjs --publish` rejects changed hashes,
incomplete PBR, unsigned textures, missing views, open positional mesh shells or
an absent acceptance receipt. It publishes only this package's unique assets,
approved records and QC sidecars. It does not compile the global runtime registry
or alter campaign maps; root owns that integration.

Selected assets can be validated and published separately with
`--assets=frontier_cinderfen_reed_clump,frontier_cinderfen_sedge_horsetail`.
The sorted selection determines separate build, validation and review filenames
under `review/`; its receipt must identify exactly those assets and bind every
actual-export image and the selected build. `test_published.mjs` accepts the same
selection and verifies public model, QC, texture and GM defaults. Refresh
`write_provenance.py` after deliberate tool changes and coordinate edits while
validating. Never broaden a selection to a sibling still under correction.
JSON receipts are replaced atomically so concurrent readers cannot see partial files.

## Placement

Units are metres, runtime +Y up and +Z forward. Place on local Y0; roots and stone
toes intentionally extend below the planted datum. Reed and sedge colonies are
nonblocking. The alder has a trunk collider; keep the crown out of architecture.
The outcrop uses separate solid mass footprints instead of a single box spanning
its clefts. These models supply no flat walkable platforms or service sockets.
Actual bounds and hash-matched GM defaults are generated from the final exports.

## Reference reading

The botanical structure draws on the [RHS alder profile](https://www.rhs.org.uk/plants/897/alnus-glutinosa/details),
[reed profile](https://www.rhs.org.uk/plants/54026/phragmites-australis/details)
and [marsh horsetail profile](https://www.rhs.org.uk/plants/131504/equisetum-palustre/details).
Cinderfen's damage, scale composition and autumn colors are original art direction.
[USGS cooling-fracture notes](https://www.usgs.gov/observatories/hvo/news/volcano-watch-columnar-jointing-provides-clues-cooling-history-lava-flows)
informed the irregular basalt cleavage. No reference photographs or geometry
were copied. Retained architecture tools document reused finishing/export
mechanics only; all botanical/rock source and texture pixels are new.

