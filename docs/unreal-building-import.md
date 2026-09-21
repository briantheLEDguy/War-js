# Representative building import

The repository's `aegis_house_1` is now an admitted import example alongside the
three character sources and command table. It is not a completed world import or
an approved gameplay asset.

Reproduce the conversion with Blender's background Python runner using
`scripts/unreal/convert-model.py -- --profile aegis_house_1`, then run
`npm run unreal:import -- --profile aegis_house_1`. The input is
`public/assets/models/prop_aegis_house_1.glb`; its source SHA-256 is
`bdd63c23c7ac19ccc4dfec37a1c338fc5bd05d7e76cd0bd715626f37c36ce179`.

The importer now accepts PNG/JPEG dependencies contained within
`public/assets/textures`. It rejects remote URLs, absolute paths, path escapes,
ambiguous embedded/external sources and inconsistent MIME/signatures. Receipts
record every image's source path and byte hash; dependencies are checked again
before success is recorded. Embedded image support remains available.

Source material reconstruction includes emissive factors, color textures and
`KHR_materials_emissive_strength`. Unknown extensions and invalid emissive values
fail preflight instead of silently losing material behavior.

## Evidence and limits

On 2026-09-21, Unreal 5.8.2 imported one static mesh, six materials and 15 textures.
Evidence is in `artifacts/unreal/converted/aegis_house_1/editor-import.json` and
`artifacts/unreal/editor/import-1789978695683-32960/`. The mesh is available at
`/Game/Imported/aegis_house_1/aegis_house_1.aegis_house_1`.

Direct inspection in the Unreal static-mesh viewer confirmed textured brick,
wood/metal surfaces and emissive windows after shader compilation. This was a
limited material inspection, not a full geometry, gameplay or art approval.
The viewer reports 9,348 rendered triangles, approximately 912 x 928 x 1,262 cm,
and zero collision primitives. The conversion reports 9,604 source triangles;
source and FBX both contain 240 exactly zero-area faces and 16 additional faces
with areas below 2.4e-9 square meters. These account numerically for the 256-face
difference, consistent with degenerate removal, but individual Unreal faces have
not been matched and geometry acceptance remains open. The diagnostic is saved
in `artifacts/unreal/house-geometry-investigation.json`. Collision,
LODs, world placement, interior traversal, lighting/performance and packaged
rendering remain unverified. No primitive fallback or replacement was introduced.

All ten Python import tests, 74 migration tooling tests and tools typechecking
passed. The release check still fails with four blocker categories. Imported
Unreal packages and generated receipts remain ignored/reproducible local outputs;
they are not committed asset-delivery evidence.
