# Aegis civic locomotion derivatives

Two ambient-only walking derivatives of the reviewed civilian male/female middle LODs. The original stationary models and their approved records remain unchanged. The male retains 100,487 triangles and the female 81,770 triangles; this package does not decimate or rebake appearance.

The source civic rig has leg bones but no weighted leg geometry. `tools/build_walk_assets.mjs` repairs only lower-body joint/weight buffers, using connected garment pieces for the long skirt and sewn trim. All other source buffer views are hashed and verified unchanged, including positions, topology, normals, UVs and embedded images. Original material descriptions, skeleton nodes and idle animation remain unchanged.

The builder bakes `src/world/CivicLocomotion.ts` against the actual civic rest axes. Its planted-foot phase matches 0.9 m/s travel; the runtime scales the clip rate to route speed and actor scale. This is a gentle walking clip, with no combat or canonical-rig retargeting claim.

Run from the repository root:

```powershell
node authoring/blender/aegis-civic-locomotion/tools/build_walk_assets.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python authoring/blender/aegis-civic-locomotion/tools/review_walk.py
node node_modules/vitest/vitest.mjs run tests/civicLocomotion.test.ts tests/worldLifeReviewed.test.ts tests/worldLife.test.ts tests/worldLifeMotion.test.ts
```

Inspect the exported contact, swing and side renders before updating `review/approval.json`. `tools/publish_reviewed.mjs` requires matching model and image hashes, then writes only these two new profiles, their QC records and review artifacts. Run `npm run models:registry` after publishing. Tests check the shipped models' actual weighted boot contact, skin deformation, skirt continuity, ground clearance and preserved appearance bytes.

`WorldLife` selects these profiles only for ambient Aegis civilians. It shares cached GLB geometry/materials/textures, gives each actor its own skeleton, and bounds rig updates by distance and sampling rate. Static NPCs and house residents continue using the original reviewed idle profiles.
