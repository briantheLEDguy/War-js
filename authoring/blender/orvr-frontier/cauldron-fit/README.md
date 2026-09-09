# Cauldron ornament surface fit

Published replacement for `frontier_oil_cauldron`, reviewed on 2026-09-09.
The six original forged washers now follow the finished bowl at each LOD.
No primitive meshes are introduced. Original pour keys, fixed assembly nodes,
operator sockets and material design remain unchanged.

`tools/fit_cauldron.py` derives an isolated source from the retained original
collection, projects the existing washer cages onto the evaluated bowl and
preserves their raised relief and UVs. LOD2 is fitted after its final bowl
reduction is selected. The original package remains the comparison baseline;
this directory owns the replacement sources, masters, baked textures and GLBs.

`tools/review_exports.py` imports each final GLB into a clean scene. It measures
all six actual washer contacts, renders ready/pour views and a close contact
view, and rejects files that change while rendering. Contact measurement welds
only coincident glTF UV/normal seam vertices at one micrometre. Each ornament
must meet the bowl, retain visible relief and stay within the shell seating
budget. All 18 contacts passed; maximum seating depth is 3.22 mm.

`tools/validate_repair.mjs` verifies source/tool/master/texture hashes, PBR data,
Khronos validation, decreasing LOD budgets, exact original animation accessor
bytes, fixed-node world matrices, contact measurements and every review image.
The published LODs contain 23,648 / 5,986 / 2,782 triangles with zero validation
errors or warnings. `review/accepted-review.json` binds the internal visual
decision to `review/validated-inventory.json` and all seven reviewed images.

Rebuild and review sequentially, with no concurrent edits to this directory:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/orvr-frontier/cauldron-fit/tools/fit_cauldron.py -- --build
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/orvr-frontier/cauldron-fit/tools/review_exports.py
node authoring/blender/orvr-frontier/cauldron-fit/tools/validate_repair.mjs
```

Changed exports require a new actual visual decision. The scoped
`tools/publish_repair.mjs --publish` command accepts only the exact signed
inventory and changes only the cauldron models/QC, approved manifest, blueprint
and existing GM metadata. Follow it with `npm run models:registry` and
`npm run builder:validate`. `orvrCauldronFit.test.ts` verifies current publication,
contact rejection cases and unchanged original pour data.

The runtime review is `/authoring/blender/orvr-frontier/runtime-siege-review.html`.
Liquid effects, fitted operating crew and final populated-zone performance
remain separate unfinished work. The earlier source proof renders are retained
as diagnostics; publication relies on the actual export views.
