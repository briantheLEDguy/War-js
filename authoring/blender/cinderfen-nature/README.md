# Cinderfen authored ecology

Four original models for the autumn geothermal marsh: a steam-damaged alder,
reed colony, rust sedge with marsh horsetail, and irregular fractured basalt.
This package is staged for actual-export review; no model is approved yet.
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
roughness, ambient occlusion and zero metallic. Height source images remain
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
  becomes true only on publication after internal visual acceptance.

## Rebuild and verify

Run commands from the repository root, checking each exit status before moving
on. Coordinate CPU resources with other asset work. Blender uses three threads.

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

