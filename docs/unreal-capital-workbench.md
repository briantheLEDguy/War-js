# Capital restoration workbench

Bastion's authored ground is available locally at
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

All 78 migration tooling tests and tools typechecking pass. Three new focused
tests cover axes/winding/UVs, canal separation and malformed elevation rejection.
The release gate remains closed; no full feature or model approval is added.
