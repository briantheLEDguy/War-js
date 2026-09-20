# Universal field command table

Published 2026-09-20: release `8f77f8a5152929d95d5c`, all 36 keeps and the GM
builder. All-placement support/access, four regional geometry checks and three
actual Cinderfen Game/Player collision presses pass. Frozen authoring evidence
remains unchanged; see `review/runtime-integration-20260920.json` for runtime
hashes, verification and limits. Static chart/tools only.

Original static keep and village logistics scenery. The editable build retains
explicit timber profiles, receiving mortises and supported small equipment.
No mesh primitive operators or gameplay map interaction are used.

`tools/` owns deterministic geometry, original PBR/map artwork and verification.
`masters/` retains source construction and finished packed masters for all LODs.
`runtime/` contains three actual reduced GLBs. `review/` holds exact-byte geometry,
contact, ground/collision and actual-import image evidence. `builder-contract.json`
describes measured collision masses and a reserved front approach.

The map is original schematic artwork using both realms' campaign routes. Its
2048 × 1146 base-color image preserves physical lettering aspect; smaller PBR
detail maps keep the package compact. Six material batches cover oak, iron, brass,
leather, ceramic and parchment. The PNG source textures are retained and packed.
LOD reduction changes parchment tessellation, tool profiles, edge bevels and seam
stitches; it does not publish three copies of one mesh.

Named finished-part receipts are captured before material batching. The contact
inspector first matches those surfaces against the actual imported GLB vertices
in both directions and checks triangle counts, then measures all joinery and
equipment supports. Collision masses cover every visible component exactly once.
Source and final masters preserve editable construction cages and receiving-cut
profiles. Export tangent repair only resolves zero vectors from the same authored
UV derivatives and records the changes.

Run `python authoring/blender/field-command-table/tools/run_delivery.py` to build
and verify. Blender is run in background with two threads. Root performs manifest,
GM and live placement integration after the package passes its technical gates.
Current status and unverified work are recorded in `WORK_STATE.md`.
