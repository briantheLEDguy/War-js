# World build checkpoint — September 20, 2026

## Sunmeadow herbalist/scout and expanded keep gameplay checks

Serra Brightfield and Mira Stonewake now use their original fitted Empire
herbalist and High Elf scout models in the game and GM builder. Existing IDs,
names, titles, roles and positions are preserved. Frozen releases are
`63072b851393b42f4329` and `d12b92a97fb9806ee882`. The herbalist passes nine
technical gates, including zero belt/cloth crossings through all clips. The scout
passes thirteen gates, including 32 equipment/seam attachments and the corrected
LOD2 boot surface; LOD0/1 were preserved. Both retain packed editable masters,
PBR textures, nine clips and 18 actual-import views. All six GLBs have zero
Khronos errors/warnings.

Production Game/NpcSpawner verifies visible LOD0/1/2 at 6.2/45.2/100.2m:
herbalist 156,290/90,647/42,197 triangles; scout 168,246/97,542/49,336.
Serra stands on the shelter floor and Mira retains her forward-scout position.
Each package retains exact runtime hashes and limits. One unavailable legacy
asset remains in the scene. The scout's bow remains stowed; this is not a
bow-drawing gameplay or arbitrary equipment compatibility claim.

The production Game/Player also held all 16 exterior corner attempts and eight
closed gates across both Sunmeadow and Cinderfen keeps. Every one of Cinderfen's
16 stairs reached the 6.3m wall walk, and all 32 upper-rail presses held at
5.075m after 0.609–0.613m lateral travel. Full results/source hashes are saved in
`authoring/blender/orvr-frontier/review/keep-gameplay-20260920.json`. This expands
the earlier bounded check to all Cinderfen stair assemblies; it does not claim
an exhaustive live walk through all 36 campaign keeps.

Production build passes; 33 maps, 903 model records and 450 GM definitions
validate. The combined suite passes **1,436 tests in 170 files**, saved in
`artifacts/orvr/sunmeadow-cast-delivery-tests.json`. The quartermaster,
Empire field captain and universal command table remain in production. Full
shared-campaign, performance and final zone acceptance remain open.

## Universal field arms rack delivery

All 36 keeps and the GM builder now include the original four-polearm rack.
Frozen release `6eac77928a01ab79cb2e` retains six packed editable Blender masters,
five embedded PBR material sets and three actual exports: 28,246 / 17,116 / 9,606
triangles. Mortised rails, shaped heel sockets, riveted braces, forged blades and
continuous leather grips retain 162 verified fitting contacts. All three GLBs
have zero Khronos errors/warnings and valid material tangent bases.

Five measured collision masses match the GM contract. All 36 keep approaches and
breach paths, 144 skid support probes and four regional wall/stair/furnishing
mesh checks pass. An actual Cinderfen Game/Player northward press stops at
(-358, 0, 2.562); the rack is visibly grounded and clear of surrounding structures.
The integration receipt retains exact hashes and the bounded-check limitation.
One unavailable legacy asset remains. This is static racked scenery without pickup.

The complete suite passes **1,428 tests in 170 files**, recorded in
`artifacts/orvr/arms-rack-final-tests.json`. An earlier concurrent run hit one
enclosure timeout; all 75 enclosure checks passed unchanged before the full
single-worker rerun. Production build passes; 33 maps, 897 model records and
448 GM definitions validate. Herbalist L, scout K and quartermaster F remain in
technical fitting. Full shared-campaign, performance and zone acceptance remain open.

## Cinderfen supply officer delivery

Nyra Vex now uses the authored female Dark Elf supply-officer uniform in the
game and GM builder. Her ID, name, campaign-marshal title, guard role and
position are preserved. Frozen release `fd4e6fa6555fd764edb2` retains the packed
editable master, generating inputs, full PBR textures, three actual LODs and
nine clips. Thirteen technical gates pass; all three GLBs have zero validator
errors and warnings. Ledger loops attach to both the belt and carrier across
all clips and LODs, with zero equipment/clothing/anatomy crossings.

Actual production Game/NpcSpawner checks show visible LOD0/1/2 at
6.2 / 45.2 / 100.2m: 144,038 / 83,541 / 38,889 triangles. Exact map, model and
harness hashes are retained in the package runtime integration receipt.
One unavailable legacy asset remains; this is a bounded local check, without
full shared-campaign or performance acceptance.

All **1,420 tests in 169 files** pass, recorded in
`artifacts/orvr/supply-officer-delivery-tests.json`. Production build and client
typecheck pass; 33 maps, 894 model records and 447 GM definitions validate.
Herbalist and scout continue all-clip fitting. The next character is Vask Rauth,
using the planned Greenskin presentation while preserving his vendor identity.

## Universal supply chest delivery

The original iron-bound field chest is published in all 36 keeps and the GM
builder. Three LODs retain 29,776 / 14,380 / 6,128 triangles, four embedded PBR
material sets and five geometry-derived colliders. Six packed editable masters
retain the dovetail boards, arched lid, real receiving cuts, hinges, carrying
bails and leather grips. Sixty-three fitting contacts pass, and all three GLBs
have zero validator errors/warnings with unit orthogonal tangent bases.
Frozen release: `9869eaf9d6e8f9747a30`; GLB sizes are 11.13 / 4.14 / 1.30 MB.

All 36 keep boundaries, gate progression and furnishing fronts remain accessible
under the existing collision checks. Four Sunmeadow/Cinderfen chests clear actual
wall/stair/furnishing triangles; 144 skid probes stay within 9 mm of support.
The Cinderfen local gameplay press stops at (-342, 0, 13.867), with the chest
visible and grounded. The package integration receipt retains exact hashes and
the bounded-check limitation. This is static closed scenery, without a loot or
opening interaction. Full campaign/performance acceptance remains unfinished.

The combined suite passes **1,416 tests in 169 files**, saved locally as
`artifacts/orvr/field-supply-chest-tests.json`. Production build and client
typecheck pass; 33 maps, 891 model records and 446 GM definitions validate.
The three character agents continue technical fitting and all-clip validation.

## Universal keep preparation furnishings

The same published apothecary table now supplies all 36 keeps, in addition to
the two village stations. Regional exteriors are unchanged. All three keep
furnishings have reachable working fronts and exact final standing approaches;
all 36 enclosures retain closed boundaries, outer-court and commander access
through the appropriate breached gates. Four authored Sunmeadow/Cinderfen keep
tables also clear actual nearby wall/stair/furnishing triangles. The new
Cinderfen keep table holds a local player press at (-358, 0, 13.960).
The separate keep integration receipt retains all 36 placement/map hashes and
the bounded gameplay result. Eighty-seven keep/furnishing/integration checks
pass across three files. The final combined suite passes **1,412 tests in 168
files**, recorded in artifacts/orvr/keep-furnishings-final-tests.json.

Character publication now requires actual side and rear views and retained
equipment-attachment evidence for the three active female character packages.
Supply-officer E is held for visibly detached case straps despite passing its
original numeric gates; the agent is correcting this construction defect.
Herbalist and scout fit/motion checks remain in progress.

## Shared apothecary and shelter-floor delivery

The original field apothecary table is published with 38,574 / 19,512 / 8,694
triangles, nine PBR material batches, six packed editable masters and 19 measured
colliders. Frozen release: `839beb3b995788c0ccb2`. The GLBs are 18.29 / 6.97 /
2.18 MB; broader download/render performance remains unaccepted.

Both existing apothecary services now have this table inside their regional
shelter. Sunmeadow's rear placement clears the NPC route; Cinderfen's approach
passes beside the resource warden. Mesh tests verify actual host clearance and
four supported feet; navigation tests verify a 0.5m actor can reach both working
fronts and original station centers. Eighteen furnishing/floor tests and 24
regional identity/publication tests pass. All 33 maps, 888 model records and 445
GM definitions validate. The final full suite passes **1,409 tests in 168 files**,
with production build and client/server typechecks passing. Initial concurrent
testing hit three five-second timeouts during Blender work; those 83 focused
checks passed unchanged, followed by the complete suite with two test workers.
Reports are retained locally under artifacts/orvr/apothecary-delivery*.json.
Both actual-game two-second table presses stop the
player correctly at .086m / .35m floor height. Exact map/model/harness hashes and
bounded-check limitations are saved in the package runtime integration receipt.

All eight Sunmeadow supply-post floor surfaces were also measured against the
actual board mesh; the earlier floor checkpoint retains a successful local
walk from floor to terrain and back. Herbalist, supply officer and High Elf
scout authoring continues in parallel. No zone is declared complete.

## Delivered regional civilians — preceding continuation checkpoint

Edric Hayward (Empire farmer) and Barrek Reedhauler (Greenskin peat worker) are
published in Sunmeadow and Cinderfen and in the GM builder. Each retains an
editable packed Blender master, fitted clothing and carried equipment, three
LOD exports and nine named clips. Publication freezes exact generating sources,
validators and evidence. Farmer passed five package gates; peat worker passed
eleven. Both have zero glTF validator errors and warnings. Large audit JSONs
were compacted without changing their values or model bytes.

Actual production Game/NpcSpawner review verified visibility at 6.2/45.2/100.2m:
farmer 132,478/76,837/35,769 triangles; peat worker 133,208/77,251/35,849.
Each package saves a runtime-integration-20260920.json receipt. Sunmeadow's
supply-cradle front also held a two-second walk press; its worksite receipt
records the resulting position. Existing legacy sky/guard fallbacks remain;
no new regional-character fallback was observed. These are bounded local checks,
not shared-network or full campaign acceptance.

The final regression run passes **1,386 tests in 166 files**, recorded in
artifacts/orvr/regional-civilian-delivery-final-tests.json. Production build,
client/server typechecks, 33-map validation, all 885 model records and the
444-definition GM catalog check pass. The initial delivery run retained in
regional-civilian-delivery-tests.json exposed an incorrect expected NPC ID and
a navigation-test rectangle that ended before the farmer's field. The authored
ID and expanded collision-path search now pass. The model semantic validator
also has a narrow exact-field exception for this original Empire identity;
legacy name blocking remains covered. Existing bundle-size and world-life mock
warnings remain.

Next character roles are Empire herbalist, High Elf field scout and Dark Elf
supply officer. Modular equipment/crew compatibility, broader settlement
composition and complete campaign/performance acceptance remain unfinished.
The active production board and hourly continuation remain in effect; animals
stay last. No push, merge or deployment was performed.

Work remains active on `codex/world-quality-continuation`. The user resumed the
build and grants standing asset approval; technical validation, source retention
and runtime integration remain required. Characters, equipment and town/siege
items take priority. Animals remain last, with the buck accepted for now.

This checkpoint supersedes the outstanding-work statements in the historical
[September 9 pause handoff](world-build-paused-2026-09-09.md). It does not declare
the full campaign or any zone art-complete. No merge or deployment is claimed here.

## Keep access and collision

Generic keep wall apertures now meet the actual scaled gate and door leaves,
closing the side gaps without extending invisible barriers beyond the models.
All **36 keeps** pass enclosure and breach-progression tests: closed gates hold,
the outer breach opens the forecourt, and both breaches permit inner access.
Owner postern access remains covered. Inner roads fit the narrower real doorways
while preserving the broad outer approach and supply delivery route. Sunmeadow
and Cinderfen retain their surveyed terrain corridors.

Local player movement uses horizontal substeps so a slow frame cannot skip a
thin gate, wall or railing. Cinderfen's corner gangways extend 1.414m into the
courtyard; the resulting **16 placed stair assemblies** have no curtain-wall or
gatehouse triangle intersections. Continuous elevated collision follows the
authored rails, with 147 measured segments. Stair support, head clearance and
ground-level passage remain tested.

Actual local `Game`/`Player` browser checks used
`/authoring/blender/orvr-frontier/runtime-keep-review.html`:

| Check | Observed result |
|---|---|
| Greybrook closed outer gate | Starting at z = -27m, the player stopped at z = -24.225m. |
| Cinderfen stair ascent | The 40-waypoint route reached the wall walk at 6.3m. |
| Cinderfen upper left rail | A two-second outward press travelled 0.611m laterally and held elevation at 5.075m. |
| Cinderfen upper right rail | A two-second outward press travelled 0.612m laterally and held elevation at 5.075m. |

The rail measurements include approach travel before contact. They demonstrate
containment at the tested upper-flight positions, not exhaustive testing of
every collision surface. Legacy `sky.hdr` and `guard_male` fallbacks were observed
during the local review and remain recorded limitations.

## Character and siege delivery

- Dwarf artisan revision l is published at three LODs with nine clips and assigned
  to Sunmeadow's existing craft mentor. Its export checks and fitted garment/boot
  evidence are retained in `authoring/blender/frontier-population/`.
- The corrected buck is integrated with idle motion. Fox, hare and wolf are
  rest-pose scenery; skylark is rest-pose LOD0. Their unfinished motion/LOD work
  is explicit. Twelve placements stay clear of travel and objective corridors.
- Equipment and all delivered regional assets are included in the GM builder.
  Shared siege equipment and keep interiors remain universal; exterior
  architecture, towns, terrain and nature retain regional themes.
- Ram crew animation packs operate on the existing equipped male Battle Prelate
  avatars. Stable physical seats follow authoritative movement and heading;
  strike timing follows the confirmed zone clock. Dismount restores held gear.
  Blocked voluntary exits preserve the occupied seat; forced release does not
  invent a teleport across an obstruction. Legacy seat records are normalized.

The ram browser review verified two loaded equipped avatars, live driving at
2.50m/s, a quarter turn, an accepted strike frozen at 0.70 seconds, the same pose
across LOD0/1/2, left dismount with restored hammer and ground placement, the right
operator retaining its side, and successful reboarding. The review uses the
production presenters and simulation in an isolated in-memory campaign. It is
not a full networked multiplayer siege acceptance. Other character bodies
require their own crew fitting and are not replaced with another body.

See the [ram runtime receipt](../authoring/blender/siege-crew/review/runtime-integration-20260920.json)
and [crew work state](../authoring/blender/siege-crew/WORK_STATE.md).

## Shared keep workshop

The original repair bench and ammunition cradle are published at three LODs
each, with full PBR material maps and retained editable masters. All six fresh
GLB reimports pass topology, export-image and Khronos checks (zero errors or
warnings). Runtime records sign every external texture; a delivered-asset
regression protects this loader requirement. The first browser inspection
caught missing texture references in the publisher; those records were corrected
before the successful runtime check.

Campaign maps now contain **72 grounded workshop placements across all 36 keeps**.
The bench has 12 measured solid-part collision boxes, the cradle 13; their
working fronts and gate/commander routes stay clear. Cinderfen retains its
canonical prop order after road/region regeneration. Both props are static
scenery; repair and ammunition-stock interactions are not implemented.

Registry `approved-f9b3eda3d5936d96` contains **254 static props, 69 character
profiles and 57 equipment records**. The GM builder has **442 definitions**,
including both workshop items with the same measured collision. Their 16m/42m
LOD distances are shared by local, shared-campaign and GM presentations;
campaign visibility ends at 160m.

In the actual Cinderfen local game, both props loaded without fallback. From
z = 10.5m, a two-second northward walk stopped at z = 8.861m for the bench and
z = 8.994m for the cradle, both on the ground at their visible front edges.
The two unrelated legacy fallbacks remained. See the
[workshop runtime receipt](../authoring/blender/frontier-workshop-items/review/runtime-integration-20260920.json).

## Verification and remaining work

### Regional continuation checkpoint

The next integrated pass adds four village furnishings: one repair bench and one
supply cradle inside each existing Sunmeadow/Cinderfen salvage building. Source
GLB triangles verify foot contact, host clearance and clear working fronts. The
Sunmeadow bench moved 0.55m rearward after a regression exposed overlap with the
salvage standing point; the exact station center now clears a 0.5m actor. Route
tests use measured oriented collision, including the regional refresh passes.

Actual Cinderfen local gameplay stopped the player at x = 484.639m against the
bench and x = 481.506m against the cradle, both at y = 0.600m and z = -252.5m.
Sunmeadow's supply post was also visually checked in the actual game. Existing
legacy sky/guard fallbacks remain; no new worksite fallback was observed.

Local regional NPCs now keep their fitted embedded idle across distance-selected
LODs. The browser caught an initial double-translation bug in attached skin bounds;
the corrected dwarf remained visible at 6.2/45.2/100.2m, selecting 150,766/87,444/
40,705 triangles. Missing regional art preserves service identity without adding
proxy geometry. The review page uses an isolated character and does not save its
inspection position. See [the runtime review](regional-runtime-review-2026-09-20.md)
for shared renderer findings. The subsequent missing-LOD0 correction retries
approved siblings from the same regional profile; 44 focused presentation tests
and the client typecheck pass. Full shared network gameplay remains unverified.

After these changes, **1,349 tests in 164 files passed**, with zero failures in
`artifacts/orvr/regional-inhabitant-integration-tests.json`. The production build,
server typecheck, 33-map validator and 442-definition GM check passed. This replaces
the intermediate 1,341-pass/one-failure worksite run. Empire farmer and Greenskin
peat-worker packages remain technically unfinished drafts at this checkpoint;
their editable masters and exact current status are saved in their own folders.

### Earlier integrated checkpoint

The final integrated suite passed **1,322 tests in 160 files**, with zero failures,
recorded in [the local regression report](../artifacts/orvr/world-quality-final-tests.json).
Production build and both client/server typechecks passed. Focused verification
also includes 40 ram/presenter/authority/dependency tests, all 39 road tests,
the 36-keep enclosure checks, Cinderfen stair geometry/navigation checks, and
workshop texture/collision publication regressions. The final suite supersedes
the intermediate workshop run that exposed Cinderfen's prop-order regression.
The production build retains the existing bundle-size warning.

The world validator passes all 33 maps, model validation passes 879 records,
and the GM catalog check passes all 442 definitions. Previously delivered assets
are already integrated; this is not an aesthetic approval queue.

Remaining work includes regional civilian/service characters, further town and
zone composition, shared siege effects, additional crew body fits, and complete
campaign advance/counterpush playthroughs. Full campaign visual and representative
performance acceptance remain incomplete. Preserve the source-only woodland floor
and unfinished animal work behind the current priorities. The active sequence is
maintained in the [production board](orvr-production-board.md).

Operational note: authoring HTML inline scripts remained stale in Vite's HTML
proxy cache during these checks despite browser reload. Restarting the local
preview served the updated harness. Recheck the served script after similar
authoring changes before recording fresh browser evidence.
