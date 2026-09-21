# Capital restoration workbench

Bastion's authored ground and first 18 house placements are available locally at
`/Game/Capitals/aegis_capital/AegisCapital_Workbench`. This is a terrain workbench,
not a restored capital or a functioning runtime GM editor. Buildings, residents,
encounters, travel and GM construction remain unfinished. Riftspire must retain
its authored crater, suspended floors and lifts; this exporter rejects that zone
instead of inventing flat ground.

`scripts/unreal/capital-terrain.ts` exports the original elevation triangles,
canal openings, water and canal beds in Unreal centimeters. It preserves the
browser height interpolation and texture scale. Ground and beds use native
complex collision; water is nonblocking. The editor module builds static meshes
from this terrain construction geometry. No character or scenery substitute is
created. Ownership metadata prevents overwriting unrelated assets or actors.

Reproduce with `npx tsx scripts/unreal/capital-terrain.ts`, then run
`scripts/unreal/prepare-capital-terrain.py` through UnrealEditor-Cmd's Python
commandlet. Run `verify-capital-terrain.py` the same way for actual collision.
Run `render-capital-terrain.py` with `-AllowCommandletRendering` for native images.
Generated assets under `Content/Capitals/` and receipts under
`artifacts/unreal/capitals/aegis_capital/` are local reproducible outputs.

On 2026-09-21, the Windows Editor target compiled and native construction produced
96,666 ground triangles, 232 water triangles and 232 bed triangles. All 43 native
blocking traces matched browser-derived heights within 0.2 cm, including the
arrival, raised ground and canal centers. The rendered overview and raised-ground
views were inspected after correcting daylight and persistent capture exposure.
The flagstone source texture renders, and elevation/canal topology is visible.
Full traversal, weathering/mountain materials, water presentation, performance,
packaged capital access and cross-platform acceptance remain open. Sampled traces
do not establish complete terrain collision or city readiness.

The terrain increment passed 78 migration tooling tests and tools typechecking. Three focused
tests cover axes/winding/UVs, canal separation and malformed elevation rejection.
The release gate remains closed; no full feature or model approval is added.

## First authored building placements

`capital-props.ts` retains all 1,880 original prop identities and exports the first
18 `aegis_house_1` placements. `prepare-capital-buildings.py` places the imported
complex house mesh with its exact source position, scale and yaw, and attaches
the original invisible collision volumes. The importer rejects unsupported
interactions or conditional collision rather than silently omitting behavior.
The other 1,862 identities remain explicitly pending in `buildings-import.json`.

FBX model axes require a quarter-turn and one reflected local scale axis to
match the world coordinate contract. Three focused tests check asymmetric points,
legacy/model collision conventions and invalid transforms. Actual saved Unreal
transforms and 90 traces across the walls/tops of 18 houses passed at 0.2 cm
tolerance (`buildings-proof.json`). Native front/back renders show the source
materials and emissive windows. Deep shadows still limit doorway inspection;
this does not resolve the earlier house geometry/LOD review or establish full
traversal. Dynamic skylight capture is enabled for the workbench.

After constructing the terrain, run `npx tsx scripts/unreal/capital-props.ts`,
then the `prepare-capital-buildings.py` and `verify-capital-buildings.py` Unreal
Python commandlets. The renderer includes building-import fingerprints when
buildings are present. Runtime GM selection, transforms, construction, undo,
drafts, publication, rollback and terrain editing are still pending.

The building increment compiled in Unreal 5.8.2, passed all 19 native foundation
tests, 81 migration tooling tests and tools typechecking. Repeating placement
and reloading the saved map passed the same 90 traces without duplicate volumes.
