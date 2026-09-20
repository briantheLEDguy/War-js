# Universal field supply chest

Original iron-bound logistics chest for campaign villages and keep workshops.
Published September 20, 2026, in all 36 keeps and the GM builder.
The chest is static scenery; no loot, inventory or opening interaction is claimed.

Frozen release: `9869eaf9d6e8f9747a30`. The integration receipt records all 36
map/placement hashes, exact authored-scene clearance and grounding checks, and a
bounded Cinderfen player collision press. Full campaign/performance acceptance
remains separate.

Construction: three rows of shouldered dovetail wall planks, actual receiving
notches in the end boards, raised slatted floor, two shaped ground skids, seven
arched lid staves, fitted end caps, three forged lid straps, two knuckled rear
hinges, a closed front hasp and end carrying bails. The visible parts are authored
polygon surfaces and section sweeps, without Blender primitive operators.

`tools/mesh_authoring.py` is retained literally from the original repository
package `authoring/blender/field-apothecary/tools/mesh_authoring.py`. It supplies
polygon construction helpers, not finished chest meshes. New construction,
materials, three LODs and saved masters belong to this package. Each finished
master retains the original per-part editable construction cages.

The three LODs contain 29,776 / 14,380 / 6,128 triangles and four PBR material
batches. Source textures use 1024 / 512 / 256 pixel maps; all channels are embedded
in each GLB. Six packed editable masters retain construction and finished states.

`tools/inspect_construction.py` measures 63 named fitting contacts across the
three sources. `tools/audit_masters.py` checks saved topology, packed images,
planed feet and the five geometry-derived collision masses. Reimport reviews
retain actual exported topology, PBR and unretouched close/game-distance views.
The validator checks literal hashes, unit orthogonal normal-map bases, real LOD
reductions and Khronos results. No tolerance is relaxed for a failed export.

```powershell
python authoring/blender/field-supply-chest/tools/make_textures.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --threads 2 --python authoring/blender/field-supply-chest/tools/build_chest.py -- --lods 0,1,2
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --threads 2 --python authoring/blender/field-supply-chest/tools/audit_masters.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --threads 2 --python authoring/blender/field-supply-chest/tools/inspect_construction.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --threads 2 --python authoring/blender/field-supply-chest/tools/review_chest.py -- --lods 0 --views neutral,rear,detail,joinery,gameplay
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --threads 2 --python authoring/blender/field-supply-chest/tools/review_chest.py -- --lods 1,2 --views neutral,gameplay
python authoring/blender/field-supply-chest/tools/consolidate_build.py
node authoring/blender/field-supply-chest/tools/validate_chest.mjs
node scripts/campaign/publish-field-supply-chest.mjs --check
```

Inspect the current views before promotion. The package publisher freezes every
generation/inspection input before registry writes; `--publish` uses standing
user approval after the same technical gates. Game and GM integration follow
the frozen release, with separate authored-scene fit and movement checks.
