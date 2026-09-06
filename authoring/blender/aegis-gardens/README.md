# Aegis city planting

Four original planting assets: branching linden, narrow cypress, red rose bed and
violet bed. Individual leaves, curled petals, stems, roots and beveled curb stones
are retained in editable Blender masters. Opaque, double-sided leaf geometry
avoids overlapping transparent canopy cards. Three shared 2048px PBR maps provide
fine grain; material factors preserve the separate botanical colors.

`sources/` contains the masters; `runtime/` contains twelve GLBs. Every kind has
three LODs, with wood and stone structure preserved while planting is reduced.
`review/all-exports.png` compares all LODs from actual GLB imports, and
`review/flowerbeds.png` checks close detail. `build-report.json`, `validation.json`
and the hash-bound visual review accompany the published blueprints and QC files.

Rebuild from the repository root using Blender 5, Python with Pillow, and Node:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --threads 6 --python-exit-code 1 --python authoring/blender/aegis-gardens/tools/build_gardens.py
python authoring/blender/aegis-gardens/tools/share_textures.py
python authoring/blender/aegis-gardens/tools/repair_tangents.py
python authoring/blender/aegis-gardens/tools/finish_materials.py
node authoring/blender/aegis-gardens/tools/publish_gardens.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --threads 6 --python-exit-code 1 --python authoring/blender/aegis-gardens/tools/review_gardens.py
```

Inspect the finished renders and update `review/review.json` with their SHA-256s
and the build-report hash. Run `publish_gardens.mjs --publish`, followed by
`npm run models:registry`, `npm run campaign:generate`, `npm run builder:generate`
and their validation commands. The publisher copies only textures referenced by
the delivery files; intermediate surface files remain in the authoring package.

`scripts/campaign/aegis-city-infill.mjs` places these assets and existing house
variants on clear plots in all five city districts. Full crowns and roof
overhangs reserve space, and houses/beds require level existing terrain. GM
Builder retains individual models and collision, while `CityInstances` batches
the repeated static meshes during play.
