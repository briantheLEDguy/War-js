# Sunmeadow fauna authoring

This package is **draft and not approved for runtime publication**. No fauna blueprints, approved records or public models have been published. Resting anatomy and complete motion deformation must both meet the visual bar established by the Battle Prelate reference rebuild.

| Runtime key (prefix `frontier_sunmeadow_`) | Display name | Required clips |
|---|---|---|
| `roe_deer_buck` | Sunmeadow roe deer buck | idle, walk, run, graze |
| `roe_deer_doe` | Sunmeadow roe deer doe | idle, walk, run, graze |
| `brown_hare` | Sunmeadow brown hare | idle, walk, run, graze, hop |
| `red_fox` | Sunmeadow red fox | idle, walk, run, sniff |
| `skylark` | Sunmeadow skylark | idle, hop, fly |
| `barrow_wolf` | Sunmeadow Barrow Wolf | idle, walk, run, attack, hit, death |

The intended builder contract is metre units, runtime scale 1, origin at the ground beneath the body, glTF +Y up/+Z forward and default `idle`. All clips remain in place; authority owns world movement. Exact frozen bounds will be supplied with approved records. Current dimensions are provisional.

`source/anatomy.json` contains original literal anatomical sections, skeletal landmarks, species palettes and source references. `tools/build_fauna.py` builds editable control cages, continuous skin, species features, embedded PBR, three actual LODs and packed Blender masters. `tools/bird_geometry.py` authors opaque curved flight feathers, coverts, rectrices, beak and articulated feet. `tools/motion.py` authors and bakes motion. `tools/quadruped_rig.py` is a local snapshot of the ORVR frontier shared rig/export helper; geometry and gait remain authored here.

The current deer uses continuous anatomical skin, shaped orbit/cheek planes, fused antler grafts, cupped ears and original directional pelt strokes. Other species remain earlier proofs until their anatomy and motion pass the same review. `texture_detail.py` tests Blender/Pillow normal handedness explicitly; `atlas_checks.py` prevents a polygon from interpolating between unrelated material islands.

`inspect_motion.py` samples every literal GLB animation key and the midpoint of each interval. It measures skin strain, loop seams, root movement, floor clearance and planted-foot trajectories. In-place playback speeds are derived from each scaled rig's stride and stance duration in the build report; movement authority must use those speeds or adjust playback rate. `reanimate_fauna.py` can rebake motion on a hash-verified master while verifying that skin geometry remains unchanged.

The 4096×2048 authored PBR master is retained for LOD0. LOD1 uses 2048×1024 and LOD2 uses 1024×512; tangent normals are renormalized after filtering. The validator reads the actual embedded PNG dimensions and estimates uncompressed RGBA8 texture memory including the complete mip chain. These estimates are resource budgets, not a claim that a populated zone meets its frame-rate target.

`validate_fauna.mjs` checks all three exported LODs, complete clips, PBR, joint weights, delivery budgets and the actual motion reports. Technical success cannot grant visual approval. Reimport images exclude Blender's bone display geometry, use the LOD0 scale for all three LOD views, and carry receipts tied to the displayed GLB, source modules, textures, original cage and editable master. A changed model or authored dependency invalidates its previous review evidence.

Example commands from the repository root:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --threads 3 --python-exit-code 1 --python authoring/blender/sunmeadow-fauna/tools/build_fauna.py -- --assets roe_deer_buck
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --threads 3 --python-exit-code 1 --python authoring/blender/sunmeadow-fauna/tools/inspect_motion.py -- --assets roe_deer_buck --lods 0,1,2
node authoring/blender/sunmeadow-fauna/tools/validate_fauna.mjs --assets=roe_deer_buck
node authoring/blender/sunmeadow-fauna/tools/publish_fauna.mjs --assets=roe_deer_buck --prepare-review
```

The publisher requires a matching explicit internal visual decision in `review/visual_review.json`. `--publish` first verifies current model/source/image evidence, then preserves a content-addressed editable release under `releases/<asset>/<review-id>/`, writes the standard blueprint/approved record and public GLBs/QCs, and leaves the global registry and GM catalog to the integration owner. It does not infer approval from a passing technical report. Earlier accepted public bytes are archived before an approved replacement. The frozen source prevents subsequent work on another species from invalidating the source of an already accepted animal.
