# Regional character runtime review — 2026-09-20

## Local culling and LOD correction

The delivered dwarf was invisible at its authored position `(-413, 0, -257)`.
An offline reproduction parsed all three published GLBs with their actual meshes,
skins and animation tracks; only textures were omitted for Node compatibility.
The old visibility code measured its center at `(-826.00046, 0.68209, -513.98792)`,
culled the object, and left LOD0 selected at 45 m.

`SkinnedMesh.updateMatrixWorld()` refreshes the attached skin's bind inverse;
`Object3D.updateWorldMatrix()` bypassed that override. The fix updates parent and
skin matrices correctly and recomputes stale skinned bounds before measurement.
The same actual GLBs now measure `(-413.00046, 0.68209, -256.98792)` and remain
visible at 5/45/100 m with LOD0/1/2 respectively.

Implementation: `src/game/CharacterVisibility.ts`. Regressions in
`tests/characterVisibility.test.ts` cover translated animated skins, three LODs,
visibility restoration and previously cached incorrect bounds. Combined with
`tests/regionalNpcPresentation.test.ts`, the focused run passed 8/8 tests.

## Shared presentation and GM contracts

Reviewed `src/game/network/SharedCampaignRenderer.ts`,
`src/game/network/CampaignCharacterPresentation.ts`, `src/game/AssetLoader.ts`,
`src/world/editor/BuilderAssetPresentation.ts` and
`scripts/generate-builder-catalog.mjs`.

The dwarf and the farmer/peat-worker profile keys retain their complete fitted
models and their own skeletons. They receive no campaign equipment overlays, no
external animation pack, and no canonical Prelate siege-crew animation. The shared
clip sanitizer removes root/scale tracks; examination of the delivered dwarf and
current draft farmer/peat LOD0 idle tracks found all removed tracks constant and
identical to their rest transforms. Their authored idle therefore remains intact.
This finding does not confer readiness on either incoming draft package.

Package-local `builder-metadata.json` files are automatically discovered. Matching
registry/model hashes supply the GM scale, footprint, collision and idle defaults;
the current dwarf catalog entry includes all three approved LODs.

## Shared missing-primary-model correction

Shared actor creation previously stopped when `resolveCharacterAsset()` returned
null for an unavailable LOD0, even when approved LOD1/2 files were available.
`resolveCampaignCharacter()` now lets the known regional complete-outfit profiles
request their own QC-approved LOD list in that case. The existing per-level loader
tries those models individually. Their embedded rigs, fitted meshes and idle clips
remain intact; modular characters still require compatible presentation metadata.
Unapproved profiles and entirely missing model sets remain unavailable without
substituting another character or primitive.

Focused regressions invoke the production shared renderer's actor creation with
the actual dwarf registry/QC and real LOD1/2 geometry, skins and clips, simulating
HTTP 404 for missing primary levels. They verify the available LOD is selected,
its original mesh/bone identities are preserved, its embedded idle animates, and
requesting the failed near LOD leaves the working model visible. Entirely missing
levels, missing approval and missing modular metadata also have regression cases.
The new cases reproduced four failures before the fix. The six related shared
presentation/renderer suites now pass 44/44 tests; `npm run typecheck` passes.

Full network gameplay and end-to-end shared browser rendering were not verified;
the evidence above is source review, focused tests and actual-GLB offline
reproduction. Test GLB parsing omits textures for Node compatibility and does not
change the delivered files.
