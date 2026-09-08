# Expanded ORvR verification — 7 September 2026

These results cover the expanded layouts and local authoritative playtest in
the working tree. They do not certify a completed regional art rebuild
or a production multiplayer launch.

## Verified implementation

| Check | Result |
|---|---|
| `npm test -- --maxWorkers=2 --reporter=json --outputFile=artifacts/orvr/gm-navigation-tests.json` | 131 files, 1,127 tests passed |
| `npm run build` | TypeScript and production bundle passed; existing large-chunk warning remains |
| `npm run typecheck:server` | Passed |
| `npm run world:validate` | All 33 map files passed |
| `npm run models:validate` | 759 manifest/index/QC records passed |
| `npm run builder:validate` | 342 generated definitions passed, including all approved characters and enemies |
| Actual GM approval resolution | Every reviewed catalog entry resolves the real on-disk QC and model identity |
| GM placement browser review | Approved guard placed, saved and reloaded; revised pasture oak placed through the actual game runtime |
| GM and shared ground support | Focused tests cover mesh footing, ramps, rotated/scaled support, finite-height gates and lintels |
| Published Sunmeadow binary/provenance validation | All 87 GLBs across 29 assets passed; zero Khronos errors or warnings |
| Staged siege/supply binary/provenance validation | All 15 GLBs passed; zero Khronos errors or warnings; runtime approval remains pending |
| Road and terrain regression tests | Connected routes, clearance, rounded junctions, terrain contact, LOD borders and signed texture bytes passed in the full suite |
| Local browser entry | Created a recruit and joined the shared authority |
| Fresh authority movement/reconnect | 53 live snapshots, 26.1 metres travelled, zero ground disagreement; reconnect preserved position and focused tests rejected the previous command sequence |
| Final local browser art review | Inspected Sunmeadow settlement, woodland and fitted keep approach; verified the published rounded road junction and soft verges in game |
| Final road rendering review | Ashen staging end is rounded; the Sunmeadow overhead inspection shows continuous roads after correcting distant depth precision |
| Local browser travel | Sunmeadow → Ashen → Sunmeadow; destination changed without a stale-activation notice |
| Local browser ability | Martyr's Ward reduced displayed mana from 100 to 86 after the server response |

The focused tests include real WebSocket clients, 18 players per realm plus
overflow, opposing combat and class rules, supply delivery and spending, keep
breaches and captures, front transitions, queueing, reconnects, authentication
boundaries, checkpoint rollback and process leases. Changed maps or ability rules
reject an incompatible checkpoint without erasing it. Actual generated Sunmeadow
and Ashen routes were exercised through server movement and delivery; all 108
outdoor supply routes have static collision-clearance checks.

The current local authority uses `sunmeadow-gm-navigation-20260907`; the earlier
road-review checkpoint was preserved. Reconnection now resumes an existing
character's authoritative position and command sequence instead of resetting
travel to staging. Explicit zone transfers and queue admission still use staging.
The repeatable live check is
`npx tsx authoring/blender/sunmeadow-terrain/review_shared_navigation.ts`, with its
receipt in `artifacts/orvr/shared-navigation-live-review.json`. This short movement
check traverses staging ground; raised floors and gates have separate focused tests.

Runtime road ends use feathered rounded caps. A depth bias keeps the physically
offset road surfaces visible when distant road and ground samples quantize to
the same depth value. Exported Sunmeadow geometry was checked at 71,800 samples
per LOD, with no terrain penetration and at least 41.39 mm clearance. Exact
triangle-overlap checks of Ashen's runtime roads found at least 43.2 mm clearance.
The distant rendering correction leaves the authored geometry and movement
survey unchanged.

Database tests run the migration in PGlite's PostgreSQL engine with explicit
authentication-role fixtures. They cover ownership, immutable realm membership,
recruit limits, compare-and-swap revisions, duplicate journal events and atomic
rollback. They do not exercise hosted Supabase Auth or remote deployment.

## Art and performance boundaries

All eighteen outdoor maps remain `layout-ready-art-pending`. The thirty regional
briefs define planned climate, architecture, vegetation and populations; they are
not thirty delivered environments. Sunmeadow now uses sixteen authored terrain
sectors, six regional architecture assets and seven vegetation/rock assets, each
with three reviewed exported LODs. The other seventeen outdoor terrains remain
transitional. Complete Sunmeadow/Cinderfen populations, fauna, animated logistics
and the remaining regional environments are unfinished. The revised Sunmeadow
canopies are published with three reviewed LODs. The dwarf draft remains rejected;
Cinderfen construction is technically verified but its material finish remains in review.

The Sunmeadow sources live in `authoring/blender/sunmeadow-{terrain,architecture,nature}/`.
Terrain GLBs match the shared Float32 movement survey, preserve all border samples
across LODs, and export road-shoulder alpha through glTF `COLOR_0`. External texture
URIs and bytes must match signed QC; the loader gives glTF parsing the verified
bytes and releases their blob URLs. Missing approved terrain installs a complete
transitional ground-and-road surface instead of partial sectors. Separate terrain
collision-model keys remain planned; the shared survey supplies current ground.

Both Sunmeadow keeps use fitted gatehouses, curtain walls and animated double
leaves. Model-space wall joins, open gate passages, NPC headroom, building/road
clearance and service access have measured checks. Defender posterns use fixed,
realm-checked landings; oil controls sit on accessible courtyard ground. The
shared Battle Prelate now wears the reviewed modular armor and maul, with matching
rigs/LODs, sky reflection lighting and nearby shadows. These changes do not certify
all faction/race populations or complete character progression.

Five new siege/supply assets have editable Blender sources, painted and baked
materials, three exported LODs and an inspection viewer. Their current technical
and visual evidence lives under
`authoring/blender/orvr-frontier/review/`. They remain staged rather than approved
runtime replacements. Export validity, polygon count and a successful screenshot
do not establish the Battle Prelate craftsmanship benchmark.

The [LOD comparison](../authoring/blender/orvr-frontier/review/final_lod_contact_sheet.png)
shows the inspected exports. Canvas fit, invalid normal projections and eight
degenerate tangent vectors were corrected. The remaining art work includes
fuller canvas seam/tie-down construction, less repetitive wear, regional identity,
gameplay animation and complete environment context.

Client prediction, complete network progression/inventory, warband management,
persistent pets/deployables and shared multilevel capital navigation remain
unfinished. Shared travel currently uses the front-transfer menu; generated
portal and optional-lair traversal still runs through the existing local game.
No remote migration or deployment was performed. The local CPU
fixture in `server/README.md` is not a GPU benchmark; 1080p/60 FPS with a completed
18-versus-18 keep encounter has not been verified.
