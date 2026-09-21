# Empire farmer native import

The repository's authored Sunmeadow farmer now imports into Unreal 5.8.2 as a
development candidate. The source is
`public/assets/models/frontier_sunmeadow_empire_farmer_lod0.glb`, SHA-256
`0cea86bf9c67dc5daac6655a8dbdd0d8952d7dc61e72dad62567801773a24903`.
Its frozen authoring release is
`authoring/blender/sunmeadow-farmer/releases/frontier_sunmeadow_empire_farmer/623facce78792ef7cab7`.
The original front render was inspected before conversion; this is a dressed,
continuous authored human model, not one of the rejected segmented bodies.

The 120 Hz Blender conversion retained one mesh, 132,478 triangles, 56 joints
and all nine clips. The Unreal import contains one skeletal mesh, one skeleton,
nine animation sequences, 17 reconstructed materials and 22 source textures.
These counts establish imported content, not production suitability.

The first Unreal import correctly failed its compressed-pose check:
`attack_melee` at 0 seconds had a 0.446638 cm skin-transform error, above the
unchanged 0.1 cm limit. Raw poses passed. Tightening AnimSequence's error scale
did not correct the installed ACL codec. The importer now creates an owned
per-profile ACL settings asset with a 0.0001 cm error threshold, 100 cm virtual
vertex distances and frame stripping disabled. Raw and compressed checks pass
for all nine clips at 17 sampled times each. Existing herbalist, Warbrute and
Dark Elf officer imports also pass with these settings. This does not measure
compression memory/performance on all target platforms.

Reproduce after building the Editor:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/unreal/convert-model.py -- --profile npc_frontier_sunmeadow_empire_farmer
npm run unreal:import -- --profile npc_frontier_sunmeadow_empire_farmer
```

`scripts/unreal/render-proof.py` accepts `--profile`, `--clip` and `--time`.
Run it through UnrealEditor-Cmd with `-AllowCommandletRendering`; it checks fresh
source/import hashes, hides unrelated proof geometry in memory, and writes
front/back/side PNGs plus hash-bound receipts under
`artifacts/unreal/visual-proof/npc_frontier_sunmeadow_empire_farmer/`. It never
saves those preview changes to the proof map. The run pose at 0.2 seconds was
inspected from all three directions: the dressed body, limbs and belt equipment
remain visible and connected. Single-pose images do not establish full-motion
garment, floor-contact or facial quality acceptance.
The final import's terminal death pose at 2 seconds was also inspected from the
side; the character lies prone with intact garments and limbs. Detailed contact
measurements and the intermediate fall still need native review.

Verification on 2026-09-21: repeated farmer import passed in
`artifacts/unreal/editor/import-1789984221539-27584/`; all 18 native Foundation
groups passed in `artifacts/unreal/editor/test-1789984239911-21812/`. Ten importer
tests, four pose-parity tests, 75 migration tooling tests and tools typecheck
passed. The regenerated audit still reports four release blocker categories.

The farmer has no new playable-class assignment or release approval. Native
LOD1/LOD2, fitted interchangeable equipment, sockets, character/GM/world
placements, full animation transitions, commercial provenance review and
performance acceptance remain open. The model ledger must keep these entries
pending, and the browser's old dependencies must remain until replacements are
complete. No visible primitive fallback was added or approved.
