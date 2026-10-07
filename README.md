# AegisWar

T1 redesign work on `codex/t1-terrain-story-rvr` adds irregular/rectangular spatial
support, four terrain/RvR topology candidates and a replicated 60-minute native
clock with regional lighting/fog. Modular village and scenery recipes reserve
twenty buildings, services, circulation, terrain support and road clearances;
local lanterns follow the clock. Run `npm run unreal:t1-plan` for private
candidate maps and topology drawings. Sunmeadow/Cinderfen native prototypes are
isolated from the accepted capital and active campaign. Interiors/gameplay integration,
weather/audio effects, camera approval, walking/driving/18v18, GM/network proof
and platform performance remain open; batch two retains the lair gate. See
[implementation and reproduction](docs/t1-redesign.md).

The isolated T1 checks now include bidirectional native obstacle sweeps, repaired
keep/staging approaches and fixture-aware village circulation. Private furnished
home studies reuse fingerprinted existing kit templates, with explicit door
routes, floor/step probes and bounded interior exposure. These studies retain
their license, regional appearance, live walking and ordinary GM acceptance gates.

The combined local Development build selects
`/Game/WorldRebuild/AegisCitadel_62df5e965e66/CampaignCandidate` through both
`GameDefaultMap` and `EditorStartupMap`. Campaign, frontend and canonical siege
scenery use the same furnished city, retaining the accepted exterior, 56 decor
objects, 34 practical lights and eight residents. Mouse input uses full pixel
deltas, and the complete 32-zone campaign retains all 70 directed portal routes.

Normal rendering uses virtual shadow maps with bounded light/page capacity.
The final normal-startup diagnostic on the RX 7700 XT measures courtyard FPS
13.19 → 88.28 and forehall FPS 14.72 → 72.65 while retaining all 56 active point
shadow casters and the authored sun/fill. Both versions use a 2560×1440 viewport,
1552×873 rendered pixels and quality 3. Lighting/reflection rebuild counts are
zero; both static navigation profiles load 5,763/2,519 actual tiles with clean
state and connected queries for 17 pedestrian anchors and three convoy legs.
See `docs/unreal-aegis-citadel.md` for raw wall/thread/GPU measurement and repair
verification. Populated siege and other-platform performance remain unverified.

Run `npm run build` for the installed private-content Editor Development build.
Normal game startup uses the configured map; the normal-campaign proof and
launcher reject map overrides and require its ordinary GM storage. The journaled
`integrate-citadel-development.py` tool preserves prior bindings and rollback
bytes; it does not grant competitive siege or release acceptance.

Final repair checks pass 1,064 repository tests, including 456 Unreal-tool
tests, all three typechecks, migration audit and world/model validation. The
combined native build passes all 142 Foundation tests. A fresh three-process
normal-default GM run verifies Save, Load/local Publish and startup restoration,
plus exact scene counts and the actual pixel camera handler with state restored.
The repaired-map run binds 782 source/config/tooling files and the tested DLL;
all 13 original GM documents remain exact and its owned proof files are archived.
The run does not certify physical mouse hardware or ordinary Steam login.
The strict release check still fails at its four required outstanding gates.

The repaired normal-startup campaign passes all 92 directed physical walks,
27,680 full-width samples, 288 gate sweeps, 88 objective samples and 150 spawn
samples without failures. The source/DLL, city and original GM document bindings
remain exact; physical traversal does not grant full siege or visual acceptance.

Fresh post-repair normal-default portal execution passes all 70 routes, 20 resource gathers,
streaming failure/cancellation controls, GM history and inventory continuity.
The earlier cold decor inspection passes the original mesh/material, 360 floor probes,
184 paired mount samples (368 endpoint traces),
eight resident, four emitter and 12 light-to-floor checks after waiting for asset
compilation with the existing read-only helper. The initial evidence-path failure
and pre-flush exact hearth-probe miss are retained; no geometry or tolerance was
changed. Functional frontend rendering also passes. The performance
repair removes the stray stationary template sun, rebuilds only the campaign's
two static navigation profiles and removes its identical duplicate bounds.
All 13,124 other native Content files and 23,179 retained actors remain exact.
Visual approval stays open. Unreal still logs a non-Nanite marking-queue
performance notice; its complete-page fallback preserves rendered shadows.

Native Content stays local/private. The configured companion repository has no
approved distribution roots, so merging public source does not distribute those
assets. Five component/tabletop proposals remain source-only, and rejected
character or scenery studies remain inactive. Earlier private-review evidence
below retains its original map, source and test bindings.

The current private decor candidate is `62df5e965e66`, retaining the accepted
`0284fb4947a8` exterior and all 52 prior mesh placements. It adds paired lower
lantern fixtures beside the archive and treasury desks, terrace return barrels
and dispatch crates: 56 added objects, 456,364 source triangles and 34 attached
practical lights. The preceding appearance pass `0cead0939e03` moves mounted
emitters clear of their housings and adapts two turquoise paint roles to satin
navy. Cold inspection verifies 360 floor samples, 184 mount contacts, eight
resident clearances and all 12 sampled lower-light paths to the native floors.
The new lantern glass preserves its source emissive strength of 2.

GM furnishing clones now retain their trusted authored point lights through
movement, hiding, undo and draft recreation. Renderer values come from the map
template; draft and authority schemas stay unchanged. All 139 native Foundation
tests pass. Three independent processes verify actual GM save, load/local
publication and restart on `0cead0939e03` with a lit catalog furnishing and nine
existing WorldEdit documents preserved. Repository tests pass 1,051 checks,
Unreal tools pass 443, and the three typechecks, migration audit and world/model
validation pass. Fresh traversal on `62df5e965e66` passes all 92 walks and its
gate, objective and spawn checks. Its own three-process GM proof passes with
11 existing documents preserved. All 16 runtime decor views were inspected:
desk lighting is clearer, while bright exterior stone, shaded interiors and
hard ceiling shadows still need polish. Diagnostic p95 frame times range from
8.57 to 55.29 ms; populated performance remains unverified. Active city
definitions and release gates remain unchanged. Earlier evidence is retained below.

The owner accepted the castle exterior for now on October 7. Keep the current
shell and route layout while furnishing the interiors and terraces. The first
additional decor ledger places 36 reviewed Aegis assemblies: seating, archive
shelves, weapon/provision racks, hearths, carts, planters and lanterns.
`scripts/unreal/citadel_decor.py` checks actual transformed model bounds against
all eight structural groups, nine floor probes per prop, routes, spawns,
objectives, gates, services, existing furnishings and resident reservations.
Seven focused Python controls and the three furnishing test wrappers pass.
Private revision `d62f3833c9f8` saves those additions with 14 warm practical
lights. Fourteen pieces face their intended room spaces, and the retained main
archive bookcase faces into the room. Cold reload checks pass all 324 furnishing
floor samples and eight resident clearances, with original saved packages and
GM drafts preserved. Three independent native processes pass local GM save,
load/publication and startup restoration using a catalog sentinel. Ordinary
login and direct manipulation of every new furnishing are not certified by
that fixture.

The following private revision, `604efb759fc2`, retains those 36 pieces and adds
eight chandeliers and eight wall lanterns across the forehall, throne hall,
archive and treasury: 52 additional decor objects and 30 warm practical lights.
All 184 native attachment contacts pass within 0.2 cm, with all 324 floor probes
and eight resident clearances retained. Saved material readback confirms the two
mounted models' authored emissive-strength multiplier. Eight opposite-boundary
queries hit the outer Gothic roof 2 cm above the source's inner slab boundary;
that diagnostic does not claim complete boundary correspondence. Original saved
content and GM drafts remain exact. Repository tests pass 1,050 checks, Unreal
tools pass 442 on the render-idle retry, and all three typechecks, migration
audit and world/model validation pass. The final revision's three-process GM
save/load/local-publication/restart proof passes. Twelve runtime views were
inspected: vaults show warm chandelier pools, but archive/treasury floor lighting
and some furnishing materials still need polish. Visual and populated-performance
approval remain open. Fresh final-revision evidence passes all 92 directed walks,
27,680 width samples, 288 gate checks, 88 objective probes and 150 spawn probes.
Active city definitions remain unchanged.

Private revision `0284fb4947a8` corrects inward-facing arch rings, reveals and
one-sided window panes, with explicit outward orientation on both side walls.
Seven focused orientation checks, seven crown checks and 75 architecture checks
pass. The fresh Blender export retains all 45 models and 74 furnishing
arrangements; all 17 established gameplay fields and the full surveyed baseline
match `252ca2f6ef88` exactly. Native import and all 139 navigation points pass.
Fresh evidence passes 92 directed walks, 27,680 width samples, 288 gate checks,
88 objective probes and 150 spawn probes. All eight native views were inspected;
earlier inspection recorded lighting, mountain and architectural detail concerns.
The owner's subsequent exterior acceptance pauses further shell iterations.
Crowd, equipped-character, GM and complete siege checks remain required before adoption.

`scripts/unreal/citadel_private_architecture_rebuild.py` prepares fresh owned
architectural sources from exact file hashes and source face selections. It
retains every unselected oriented triangle, material role and original position,
normal and UV0 entry, including unused entries, before appending reviewed details.
Eleven focused Python controls pass. The current source assembly replaces plain
rails and stiff standards with Gothic balustrades, curved cloth and shallow stone
mouldings; it retains 841,937 triangles and adds 475,620. Native packing,
generated lightmap UVs, reduced LODs, collision correspondence, GM persistence and
visual approval require fresh evidence. Original packages and active city
definitions remain preserved. A fresh private native comparison and independent
cold reload now pass mesh, collision-owner, saved material-graph and attachment
checks. That diagnostic has not been adopted into the accepted exterior.

Private mage review tooling lives in the Editor-only `WarMageReviewLibrary`,
`WarMageReferenceRestore` and `WarMageMeshBufferReadback` classes. The first two
inspect native references and restore exact reference data on a fresh diagnostic
copy. The readback class exposes actual LOD0 positions, UVs, normals, section
indices and skin weights decoded through native bone maps, without rebuilding
buffers or changing CPU access. Missing native CPU data produces an explicit
unavailable result. All 138 native Foundation tests pass, including two readback
suites. Saved animation parity, source correspondence, equipped clearance and
artistic approval are separate checks; diagnostic assets do not change active
character presentations.

The saved private mage face matches its source across all 31,008 oriented
triangles, including actual named skin weights; all 25 copied clips and 2,507
frames per RAW/COMPRESSED evaluation retain exact reference/pose parity after
cold reload. These results preserve the original character and do not approve
the face's appearance or armor fit. A separate adult-face revision and cloth
fit review remain in progress.

Private mountain geometry study `c19ed137dd36` passes cold render-policy,
collision and retained-gameplay checks. Its three new crag material roles use
the same bounded intended-shader readiness gate as other private surfaces.
All 16 matched geometry-control/treated views were inspected and rejected for
corrugated distant peaks, coarse highland detail and unfinished architecture
and lighting. Saved full-basis/UV correspondence, fresh traversal and populated
performance remain required. The current repository suite passes 1,048 tests,
Unreal tooling passes 440 tests, and all three typechecks plus world/model and
migration validation pass. Release readiness remains false.

Private repaired density revision `252ca2f6ef88` moves 15 older furnishings clear
of facade, stair and gameplay-pad reservations and retains 26 additional reviewed
table, bench and barrel arrangements. Its Blender export preserves 45 models and
17 checked gameplay/lighting fields. All 74 dressing arrangements now pass
source architecture and reservation checks, including 666 floor probes. Native
import passed with 101 owned packages and navigation reaches all 139 ledger
points. Fresh walking, camera and crowd acceptance are required before adoption.
The earlier `75641ea12130` revision passed all 92 native walks, 27,680 width samples,
288 gate checks, 88 objective probes and 150 spawn probes; those receipts do not
verify the repaired geometry. The default selection remains separately signed.

Private citadel recipe 12 strengthens the crown masonry, selected upper piers
and carved crest while preserving all signed routes, objectives, spawns and
rooms. Revision `423a3d57fd65` imported 45 native models and six normal textures;
the saved navigation build reaches all 139 ledger points. Fresh physical
traversal and visual review remain pending. Private Lumen comparisons use fresh copied levels, process-only
startup settings and tagged temporary runtime settings restored on exit.
The native resource inventory and blended-view diagnostic do not certify
renderer pass selection or lighting quality. See [citadel verification](docs/unreal-aegis-citadel.md).
Views-only `--cinematic-view` comparisons request temporary full-resolution
rendering, antialiasing and shadows; they restore prior settings and confer no
populated-performance acceptance.
Earlier eight-view comparisons retained their source/DLL bindings. Subsequent
render-proxy inspection found that both private-material hero views used
WorldGrid fallback shaders, although their later plaza views used the intended
materials. Private captures now wait for intended, non-fallback shaders before
camera settling and recheck them before capture. Asset-byte preservation and
resource readiness do not prove screenshot pixel bindings; the Editor-built
fallback query can also queue normal shader work.
An independently opt-in original distant-crag study adds fresh private packages
only. Editor staging and cold game collision/shadow controls pass; navigation
octree membership and visual acceptance remain unverified.
Its authoring inputs are private frozen artifacts, separate from portable
contract tests. No study promotes shared scenery or opens full-siege admission.

An independent private masonry/sculpture material study preserves original
geometry, UVs, normal and ORM graphs. Native read-only accessors inspect exact
expression pins and 21 material roots, including Python-hidden depth and
displacement inputs. Both surface studies staged successfully and their ten
material graphs passed cold Editor reload checks. Shader-ready eight-view
comparisons completed but still fail reference fidelity. The optional retained
mountain bridge now preserves the actually bound tinted instance, its direct
parent, all overrides, PBR inputs and actor collision. Fresh copied control and
treated studies pass staging, cold reload and exact material-readiness checks.
All 16 native views were personally inspected and rejected for smooth coarse
rock, faceted snow caps and exposed terrain edges. It is not a shared scenery
revision, and combining it with twilight remains disabled. The Editor's strict
vector-parameter readback and bridge controls pass; all 124 native Foundation
tests pass. The independent private
`WAR_CITADEL_TWILIGHT_FIRE_STUDY=1` comparison adjusts the seven existing fixtures
and 18 signed practical lights. Both off/on copies passed cold saved-property
checks and matched eight-view camera runs. The first twilight look remains
rejected for dark plaza/stair/balcony routes. Recipe two retains the key and
practicals while raising and rotating the existing cool directional fill and
raising sky contribution; twelve focused checks pass. Both repaired-revision
copies staged, passed cold saved-property checks and completed eight rendered
views. Plaza, stair and balcony readability improves, but coarse mountains and
architectural detail still fail reference fidelity. No lighting adoption is approved.

The convoy's initial navigation projection can be bypassed only within 20 cm
and only when the native agent corridor confirms the next point is reachable
directly. Later corners, hull collision, gate docking and encounter ownership
remain enforced. All 118 native Foundation tests pass. The 600-second ordinary
encounter diagnostic reached the four lower-city claims, both sides and center,
with concurrent side progress, occupied locked-center checks and unrelated-player
cleanup protection. Its 75/68 convoy recoveries still prevent clean-traversal
acceptance; commander outcomes and a full siege remain unverified. The original
launcher failed after normal convoy cleanup; a stage-aware parser revalidated the
preserved native receipt without replaying or rewriting it.

The Development-only ordinary GM persistence proof uses the exact private review
wrapper storage and three native GUI launches: save, independent draft load
and local publication, then automatic publication restore. It refuses occupied
ordinary storage, binds native packages/DLL/source bytes, and checks existing
WorldEdit files without replacing them. See [GM persistence verification](docs/unreal-gm-workbench.md).
Run `c2f8968b4a3a40d0b1ec2d3655a3adee` passed all three launches for private
wrapper `CitadelHumanReview_20261007_6e0fe6829e5b`, against DLL `c77abbdb…`.
This verifies normal private development persistence, not ordinary login or
shared publication.


Mouse camera input retains physical pixel deltas before applying the saved look
sensitivity and inversion preferences. `DefaultInput.ini` overrides Unreal's
inherited 0.07 mouse-axis scale; `CameraControls` verifies the merged settings
and actual Enhanced Input mappings at 30, 60 and 120 Hz. Restart the native game
after changing input configuration.

Zone streaming keeps the server's union of occupied and requested zones.
Per-player streaming notifications require a real network connection, preventing
connectionless development controllers from applying their own subset to the
server. The native `ZoneStreaming` regression exercises that engine RPC behavior.
Recovery proofs also retain bounded, read-only loading diagnostics; see
[portal streaming verification](docs/unreal-world-portals.md).

Private citadel walkthroughs clone the complete prepared campaign, retaining
routes, destination layers and city services. Their editor check reads every
streaming declaration, including unloaded destinations, before launch with a
process-local selected-map override.

[Fluid combat](docs/unreal-combat-fluidity.md) separates gameplay timing from
animation recovery: movement cancels stationary spells, melee continues while
moving, and baseline combat uses a 1-second shared cooldown. The guide covers
GM timing compatibility, cancellation/refunds, equipped locomotion, impact
feedback, combat-only staging and native/network verification. It also documents
full-cycle equipped captures and production impact-audio review exports.

Confirmed outgoing damage and effective healing now float above each receiving
player or NPC, following them independently of target selection. Isolated numbers
rise for one second; rapid procs accelerate the stream up to five times faster.
Each head has a bounded 160 x 112 UI-pixel region (scaled with the HUD), six visible
numbers at most, and a 32-number total limit. See the
[floating-number behavior and verification](docs/unreal-combat-fluidity.md#floating-damage-and-healing).

All visible nearby allied and enemy combat characters also have compact overhead
health bars by default, including damageable NPCs. Blue ally and red enemy bars
read current replicated health every frame, so damage from any source and healing
update them immediately. Bars sit below the floating numbers and follow the same
zone, range and visibility rules as combat targeting.

[Combat UI editing](docs/unreal-combat-ui.md) adds local friendly/enemy styling
to Edit UI: reticles, overhead bars, damage/critical/healing streams, target-panel
children, hit marker and combat messages. Slate body outlines and isolated mock
events preview edits; drag release and committed controls autosave separately
from action-bar layouts. `WarCombatUiSettings` owns validation/persistence,
`WarCombatUiDrawing` supplies shared Canvas/Slate layout, and
`SWarCombatUiEditor` provides runtime controls. See the guide for rendered and
owner/client verification commands and remaining acceptance evidence. The
combat UI network/live proof runners share `combat-ui-process.ts` to report
launch failures and confirm owned-process shutdown before releasing resources.

[Shared capital scenery](docs/unreal-shared-cities.md) gives campaign cities,
siege and the loading/menu presentation the same native scenery levels, meshes
and materials. With Unreal closed, `npm run unreal:city-sync` migrates or updates
bindings; `-- --check` verifies current sources. City changes invalidate affected
siege navigation/visual reviews instead of allowing an older city to launch.
Local lower-city admission now uses fresh crowd, convoy, gate and rendered
evidence for the current shared city. Full-siege and release acceptance remain separate.

The [reference citadel replacement](docs/unreal-aegis-citadel.md) adds a signed
architectural sheet and bidirectional route ledger, surveys actual native
geometry and stages Gothic scenery in private candidate packages. The version 2
siege progresses through the lower city, independent permanent side captures,
the locked central plaza and commander. Its encounter actor separates enrollment
from stat normalization; scenario and live campaign adapters share the rules.
The Node bridge owns readiness and durable settlement, validates the owning
native host and suspends legacy city combat during its lease. Critical inventory,
progression, quest and reward mutations flush a full private character document
before reporting success, then replay through the owning host's revision and
sequence checks. Interrupted native recovery, transient combat effects and
physical character returns still need complete acceptance evidence. Fresh geometry, full 18v18 scenario/live
capital, evacuation, recovery and rendered evidence are required before admission.
Participant and visitor evacuation documents have separate per-realm durable
budgets, so remote enrollment cannot consume the capital's evacuation capacity.
Recipe 10 imports the reviewed furniture's original PBR materials, atlas UVs and
smooth normals. It adds 32 furnishing arrangements across six areas, corrects the
throne's facing and scale, and removes exactly repeated oriented stair faces
while preserving opposite solid boundaries and route-surface triangle bindings.
Collapsed furniture seam UVs receive a bounded quarter-texel repair; native LOD
render-buffer checks still require valid orthogonal tangents at every vertex.

For a new private walkthrough, bake navigation before preparing campaign copies,
then run `stage-citadel-campaign-navigation.py` in separate `stage` and `verify`
processes. `stage-citadel-review-world.py` clones that full prepared campaign,
retains every portal, destination and service, and adds an isolated resident
gameplay layer. Its receipt supplies a process-local `GameDefaultMap` override
for the existing standalone GM gate. `citadel_review_world.py` validates exact
map names, explicit route bindings and resident reservations. These residents
remain private review content until shared gameplay publication is verified.
Run `npx tsx scripts/unreal/citadel-review-launch.ts --receipt <staged.json>` to
open the exact private walkthrough. `--dry-run` verifies every owned and protected
native package before printing the process-local launch arguments. The launcher
leaves normal startup configuration and shared capital GM drafts untouched.
`world-builder-proof.ts --review-receipt <staged.json>` exercises the rendered
builder, pointer placement and publication reload on the same verified wrapper.

Use `npm run unreal:citadel-proof -- --blueprint <file> --map <candidate>
--city-revision <revision>` for exact-revision physical routes and gate sweeps.
Native import explicitly converts source triangle winding while retaining outward
normals. Route checks cover five lanes across each signed corridor width, and
architectural captures temporarily hide and restore local HUDs.
Cloud render-resource diagnostics are saved separately from capture completion;
a fallback material cannot establish cloud visibility or lighting approval.
Private alpine render and sculpture-material studies preserve source packages and
terrain collision; their portable continuity tests do not establish visual approval
or acceptable populated-scene performance.
The furnished full scenario currently fails at the convoy escort checkpoint;
walking-route success does not establish full-siege admission. Bounded unfinished
scenario diagnostics record actual convoy and capture conditions separately from
outcome acceptance. See `docs/unreal-aegis-citadel.md` for the command and limits.
The first safe-steering trial increased measured ram travel from 17 to 109 metres
within its diagnostic window. Exact rotated-hull path checks, stable bot flank
seats and stationary-cast preflight now support both encounter adapters; fresh
checkpoint and full-siege runs must verify them before admission.
The latest full scenario still timed out after two lower-city milestones. Its
actual convoy path crosses the defender spawn protection radius. Recipe 11
adds an explicit survey-bound defender spawn overlay adjustment onto unchanged
lower-city paving, preserving all objective anchors, routes, gates and the
750 cm protection rule. It also adds supported crest backing, foundation and
roof detailing, 48 furniture arrangements and verified native normal-texture
conversion requirements. The current private revision imported all 45 native
meshes and passed 92 reference-route walks and 27,680 width samples before the
navigation save. Fresh navigation now connects all 139 ledger points. The extra
lower-spawn replay passed four grounded walks using measured floor profiles,
but failed 410 lateral clearance samples; two-metre crowd width is unverified.
Siege readiness now uses the participant navigation profile and bounded query;
recipe 11 launchers reject missing or stale navigation before enrollment.
The combined GM/navigation build, all 110 native Foundation tests, 409 Unreal
tooling tests and tooling typecheck passed. Its frozen full scenario then timed
out after two lower-city milestones with live engineers but no qualifying
attackers on the uphill approach. The floor-sampling correction and stronger
physical locked-center witness passed native unit checks. A subsequent frozen
360-second diagnostic earned two milestones, then found a character blocking
the padded ram sweep just outside its unpadded recovery query. The correction
aligns recovery and escape checks with the existing eight-centimetre maximum
movement padding; collision, capture rules and timers remain intact. Fresh gameplay, recovery, crowd and
visual evidence remain outstanding; these checks do not establish art approval.
The current private captures are rejected for reference fidelity; older route diagnostics retain their failures,
they do not authorize publication or full-siege admission.
The older recipe 5 diagnostic retains 70 failures across 27,460 width samples. Exact
game-world overlap/sweep and direct-body diagnostics investigate those contacts
without changing corridor admission. Recipe 6 source binds the lower spawn's
surveyed ramp gradient and corrects gate, gallery, foundation and bounded approach
wall geometry. Private revision `8bb3168368e3` includes the gallery tangent
correction, a fresh read-only native survey and 139 connected native waypoints.
Its final schema 4 traversal passed, as recorded below. Live cooked contact
diagnostics use exact affine transforms and retain both failed movement and
destination contacts. Their candidate-face distance statistics never grant admission.
Versioned winning-plane diagnostics export full capsule/triangle intervals for
an independent Decimal projection audit; saved certificates never authorize movement.
Width proof schema 3 confines fresh typed live separation checks to route
placements, retaining raw gate admission and native floor/StepUp/movement vetoes.
Each sample records query accounting and independently audited full-capsule
certificates. The later schema 4 run supplies complete traversal for that revision.
Schema 4 requires the unchanged native character's full 64-channel collision
policy and continuous checks of capsule dimensions, scale, axis, gravity and
walking limits. Its first rehearsal passed 27,680 width samples but was stopped
after 24 walks to add the geometry guard; it remains diagnostic history.
The final guard accounts for Unreal's one-ULP slope rounding at spawn, then pins
the actual runtime and class-default limits exactly. All 100 native Foundation
tests passed. Fresh schema 4 run `1791300014775-28176` completed all 92 actual
walks and 27,680 width samples with zero route or physical failures; both
independent width auditors passed. These receipts bind only revision `8bb3168368e3`.
Recipe 7 `eb00703a2a63` adds articulated upper spires and supported dormers;
its 70 architecture controls, native staging and 139-waypoint navigation passed.
Fresh run `1791302524498-26280` passed all 92 walks, 27,680 width samples,
288 gate checks, 88 objective checks and 150 spawn checks, with eight game-camera
  captures. Both width auditors passed. Each receipt remains bound to its own geometry.
  Recipe 8 `d7936ad95609` adds the supported taller central standard; its asset
  build, 71 architecture controls, native staging and 139-waypoint navigation
  passed. Fresh complete native proof `1791305174868-5128` passed all 92 walks,
  27,680 width samples and all gate, objective and spawn checks, with eight views.
  Both independent width auditors passed. Visual and full siege approval remain open.
Recipe 9 `4069b99e5f8d` repairs bounded wing footings and strengthens the stepped
façade hierarchy while preserving objective, route, gate, spawn and room data.
Its asset build, 73 architecture controls, 68-package private staging and all
139 navigation waypoints passed. Native replay matched all 144 signed ground
samples exactly. Fresh native proof `1791308126754-24160` passed all 92 walks,
27,680 width samples and all gate, objective and spawn checks; both independent
width audits passed. Private campaign preparation and strict content validation
passed, with canonical packages preserved. The tooling suite passed 295 tests.
Crash recovery and cinematic visual review remain open for this revision.
Live campaign startup exposed streamed navigation being discarded in game.
The private campaign now owns both baked profiles and their bounds; a separate
native reload preserved all 5,765 character and 2,523 convoy tiles byte for byte,
and strict content validation passed. Runtime convoy and recovery checks remain
pending. Canonical campaign packages and the isolated scenario remain intact.
The local campaign journal now retries brief Windows sharing violations during
atomic replacement, retaining the durable checkpoint and flushed pending file.
Persistent or unrelated storage failures still pause authority without an ACK.
The preceding schema 3 run completed all 92 walks with zero physical failures.
Full siege acceptance, visual fidelity and cinematic lighting remain unapproved.
Seven source-bound lighting fixtures, shadowed architectural lights and native
clouds are being checked in isolated game-camera studies. New stair supports,
sculpted sentinels and a bounded native mountain carve require fresh evidence.
The carve checks every stored native corner, including unused attributes, and
binds original mesh policy to a separate read-only survey. Character return
requires a durable full current document; a restore acknowledgement cannot
release return custody. Native reconnect and crash verification remain pending.
Version 2 character recovery records supported effects and cooldowns with absolute
expiry times and their applied definitions. Elapsed downtime reduces remaining
duration; offline damage and healing ticks are skipped. Native regression tests
cover this codec, while actual process-crash acceptance remains separate.

Version 2 encounter navigation uses a bounded 8,192-node query filter; ordinary
players and recorded version 1 rounds retain the engine default. The new private
recipe records full-width spawn approaches and requires actual capsule checks
across every pad. Recipe 6 binds the retained ramp footprint to a fresh native
support survey without changing its anchor or clearance limits. Source checks
and the earlier 95-test native Foundation suite have passed. The older recipe 5 candidate
completed 92 center walks but still fails width and gate/spawn checks; fresh
complete traversal and cinematic approval remain pending. Diagnostic-only runs
cannot grant admission.


[GM rendering diagnostics](docs/unreal-gm-rendering.md) compare pointer-driven GM
controls, direct commands and an idle session using isolated preferences and
drafts. The persistent muted-color report remains under investigation until a
rendered before/after reproduction establishes its cause and verifies the fix.

[Portal travel and model candidates](docs/unreal-portal-models.md) covers the
capsule-entry fix, Interact retry, saved-world survey and reference-based Blender
authoring. Both model variants are installed at all 70 local campaign entrances;
reference-fidelity, sculpted collision and release acceptance remain unfinished.
The same guide documents the portal-visual installer and saved-world verifier;
the campaign must be closed in Unreal before its routing map can be updated.

The [Dutch Bastion revision](docs/unreal-dutch-bastion.md) rebuilds all five
districts with adjoining gabled brick houses, winding streets, enclosed courts,
fifteen public venues and deliberate gathering/combat spaces. Shared wall planes
replace isolated-house spacing. Guarded native revisions preserve services,
other zones and GM drafts. Revision `d105951f4aab` is active in the default game
and editor campaign, correcting overlapping floors and exterior corner trim.
Native review includes 157 city views, 42 supplemental corner views and 139 passed capsule routes.
Commands, measured performance costs and independent release gates are in the
revision notes.

The [imported population workflow](docs/unreal-imported-population.md) assigns 18
supplied character models to both capitals and four starter-zone PvE camps.
Its shared assignment ledger, private native animation recipes and guarded
placement survey preserve existing services. Native material, equipped-motion
and placement review are required before activating new appearances.

Native gameplay keeps the cursor visible: click allies or enemies to select,
**middle-click** selects the nearest visible enemy, and **Tab** cycles enemies.
Selected characters have bold blue (friendly) or red (enemy) corner reticles.
Camera dragging and clickable action bars remain available. See the
[control and targeting notes](docs/unreal-interface.md#configurable-action-bars-and-edit-ui).

The [lower-city siege playtest](docs/unreal-city-siege.md#lower-city-development-round)
adds a loopback server/two-client launcher, preparation and rematch UI, separate
lower-city victory rules, player squad orders and combat feedback. This work
includes native Summon Idol, fitted caster armor, authored encounter models and
crowd-aware objective navigation. The six-class roster and encounter assets are
equipped-frame reviewed; the current shared city still needs new siege route
acceptance before admission. Once accepted, start `npm run scenario:host`, launch the main game and enter your
character. Keep the host running while playing. If the Scenario panel reports a
connection failure, start the host and select **Connect / retry** in that panel.
Open **Escape → Scenario**, ready your party, queue and accept the
match. Your existing realm, class and equipment carry into a separate scenario
instance. The recorded lower-city rules retain 6v6; the replacement full siege
uses 18v18 after its fresh admission checks pass. **Leave scenario and return** restores your campaign character and
position. The shared coordinator owns instance allocation and recovery; see
[scenario queue setup](docs/unreal-scenario-queues.md).
The lower-city escort includes an authored battering ram and field catapult,
pushed by four Greenskin engineers. Claimed objectives raise Riftbound standards.
Equipment models, fitted push poses and ownership bindings are maintained through
the [siege equipment recipe and route proof](docs/unreal-city-siege.md#siege-equipment-and-ownership).
For the separate two-client fixture, run `npm run unreal:siege-playtest` and press
**Ready in both windows**.
`-- --automated` runs three normal-timed network rounds and rematches;
`-- --dry-run` inspects the launcher without starting Unreal. Full three-stage
siege, Steam and release acceptance remain separate and unapproved.

The GM City Builder includes [Remote world sync](docs/unreal-world-sync.md):
authenticated snapshot publishing and pulls with recovery, undo and revision
conflict checks. `npm run dev:check` diagnoses the connection. Local Auth is
configured, but the gateway address, owner login and hosted sync deployment are
still outstanding; this does not deploy an active game server.

The native [cinematic frontend](docs/unreal-character-entry.md#cinematic-frontend)
loads the same shared scenery levels into isolated presentation worlds, with
campaign lighting profiles and equipped character previews. After saving city
edits, close the Editor/game and run `npm run unreal:city-sync` before reopening.
Use `npm run unreal:frontend-refresh -- --check` to check presentation bindings.
This tracks saved native content. Run `npm run unreal:frontend-proof` for offscreen
login, selection and transition evidence; `-- --width 1280 --height 720` and
`-- --width 2560 --height 1080` exercise small and ultrawide layouts. Presentation
binding updates never rewrite source city maps or copy their materials.
Import the owner's login logo, button and window PNGs from `graphics-new` with
`scripts/unreal/import-frontend-artwork.py` through the same Python commandlet.
Private UI materials apply bronze coloring and transparent-margin cropping;
the supplied files remain unchanged.

The [Bastion siege runtime](docs/unreal-city-siege.md) adds three-stage rules,
population scaling, bot squads and local GM controls. Its isolated capital map
has stage blockades, objective props and navigation through all 17 required
anchors. The lower-city test uses a separate development admission flag; the
courtyard, commander and larger-population siege remain unapproved.

Native Unreal Engine **5.8.2** fantasy RPG: Aegis Accord versus Riftbound Host.
The browser application is retired. Node/TypeScript remains for shared content,
asset tooling and campaign/account/persistence infrastructure still awaiting
native integration. Production Steam admission and release remain gated.

The native [GM Ability Workshop](docs/unreal-ability-workshop.md) adds a class
spreadsheet, shared-ability composer, conditional effects, numeric overrides,
local recovery and shared-draft persistence contracts. The native executor
captures immutable cast/periodic definitions and synchronizes catalog changes.
The workshop also includes calculated condition scenarios, affected-class
before/after review, and common TypeScript/Unreal conformance fixtures.
In your local GM development session, **Review & Publish > Deploy draft to this
game** activates edited abilities for new casts. Saved versions support rollback
and automatic restoration on the next GM launch. The journal lives alongside
draft recovery in `Saved/AbilityWorkshop/deployments/`.
The full workshop plan is **not yet complete**: the interactive online arena,
native shared admission/GM authority and gateway-to-server deployment bridge
remain outstanding. Shared publication and deployment stay closed.

The active [free development environment](docs/development-environment.md) adds
identity and persistence foundations. **It is not yet a usable shared server:**
OAuth setup, native saves/admission/shared GM, Linux server deployment, content
onboarding and two-machine acceptance remain outstanding. The VM is provisioned;
resume NetBird setup from the [checkpoint](docs/development-setup-checkpoint-2026-09-23.md). The
[dated strategy](docs/architecture/mmo-hosting-2026-09-23.md) preserves paid options.

The supplied-animation pipeline covers 44 clips and explicit presentations for
forty abilities across Battle Prelate, Sunfire Templar, Warbrute and Ember Arcanist.
It includes a native blended state machine, replicated action timing, equipped
casting transitions and Icon of Wrath. See the
[animation workflow](docs/unreal-animation-import.md) for generation, gameplay
proofs, deletion receipts and visual/release acceptance gates.
The [Windows verification record](docs/unreal-animation-verification-2026-09-24.md)
links the passing gameplay, multiplayer, capture and removal evidence.

The native world builder (**G**) keeps movement and right-drag camera orbit active.
Choose a model to preview it in green, point at ground or a wall, then click to
place it. **Cancel placement** returns to selection. **Publish draft to local
game** persists the current layout and restores it on the next authorized local
GM launch; **Save draft / Load draft** remain separate recovery controls. Remote
authoring snapshots have their own sync controls; active shared-world deployment
remains unavailable. See [builder controls](docs/unreal-gm-workbench.md).
Selected private citadel walkthroughs retain the standalone development GM gate
and use separate per-wrapper draft/publication directories; their model catalog
still requires valid authored identities and collision.
Run `npm run unreal:builder-proof` for the isolated rendered placement/publication
check and fresh-process restoration.

## Architecture

| Location | Responsibility |
|---|---|
| `unreal/AegisWar/` | Native C++ gameplay, Editor tools, configuration and build targets |
| `shared/` | Browser-independent catalogs, rules, protocols, geometry and guide data |
| `shared/game/abilities/workshop/` | Ability workspaces, stable assignments/effect IDs, conditional rules, validation and spreadsheet transactions |
| `server/` | Retained trusted Node campaign authority, authentication and persistence |
| `server/development/` | Development PKCE companion, account gateway and owner administration |
| `supabase/` | Database migrations, RLS and campaign seed data |
| `scripts/unreal/` | Content export, asset audit, imports, build/proof tools and collaboration checks |
| `scripts/campaign/`, `scripts/blender-character-pipeline/` | World generation and asset authoring/validation |
| `public/assets/`, `authoring/` | Retained source maps, models, textures and provenance; the path does not imply a website |
| `migration/` | Native policies, frozen reference fixtures, retirement and content manifests |
| `tests/` | Retained shared/backend/database/tooling tests and native Python tooling checks |
| `.mcp.json` | Project-local Blender character MCP configuration; uses the retained authoring server |

Unreal owns native live gameplay. The retained Node authority is a separate
reference/backend process; it has not been connected to native production play.
Each persistent datum must have one trusted owner at a future cutover. Do not
silently discard campaign, inventory, economy or runtime GM requirements.

The [model storage cleanup](docs/model-storage-cleanup-2026-09-24.md) removes
obsolete model iterations, recovery payloads and nine inactive checkouts. Current
authoring sources and imported runtime assets remain separate required inputs.
Run `python scripts/unreal/verify-animation-removal.py` to check retired paths,
Blender version backups, hidden recovery models and embedded character tracks.

## Setup and verification

Choose **Quit Game** below **Graphics** on the login screen to close the game
without signing in.

Choose **Local development login** on the entry screen for session character
testing; it does not require the optional developer-account companion. Once in
game, open **Escape > GM Tools > Set level** and choose
**1-45**. This updates stats and ability unlocks, resets current XP, and restores
health/mana for the session. See [GM controls](docs/unreal-gm-workbench.md).

`npm run unreal:stage` keeps installed world visual bindings synchronized with
gameplay exports after verifying unchanged source maps, models and native packages.
Changed or already stale bindings stop staging for review. Restart the play session
after staging; see [character-entry diagnostics](docs/unreal-character-entry.md).

Install Node 22.19+ and run `npm ci`. Install exact Unreal 5.8.2 and its supported
C++ toolchain, then set `UNREAL_ENGINE_ROOT` if outside the standard Windows path.
Fetch full Git history including `browser-reference-before-retirement-20260922`;
historical source hashes are verified through Git without retaining a runnable
browser application in this checkout.

```powershell
npm run typecheck
npm run typecheck:server
npm run typecheck:unreal-tools
npm test
npm run test:development
npm run world:validate
npm run models:validate
npm run builder:validate
npm run unreal:audit
npm run unreal:build -- --target Editor
npm run unreal:test-native
```

`unreal:release-check` must still fail until complete gameplay, model, platform,
Steam and operational acceptance is recorded. Passing tooling or native rule
tests does not certify visual or production readiness. The retired browser's
fixtures are immutable; the fixture commands now verify them. Native automation
tests the implementation against those references.

## Native content and collaboration

Native content is local/private, outside the public code repository. The private
companion is `briantheLEDguy/War-js-content`, pinned by
`migration/native-content.lock.json`. Its initial inventory is **not distributable**:
source/license review is pending, so fresh-machine setup is not yet complete.
Do not force-add Content, purchased kits or supplied animation sources here.

See [collaboration setup and blockers](docs/unreal-collaboration.md). Collaboration
is closed pending a licensed Windows VM, suitable guest graphics, verified content
and remote isolation tests. The host's existing **work Tailscale account is
forbidden** for this project. A separate project account belongs inside the guest
only. No collaborator receives host login, filesystem, desktop or LAN access.

## Project requirements and history

- [Migration requirements and acceptance](docs/unreal-migration.md)
- [Browser retirement and branch dispositions](docs/browser-retirement.md)
- [Original class and ability system](ability-system.md)
- [Native abilities](docs/unreal-abilities.md), [interface](docs/unreal-interface.md),
  [world buildout](docs/unreal-world-buildout.md), [runtime GM tools](docs/unreal-gm-workbench.md)
- [Supplied animation handling](docs/unreal-animation-import.md)
- [Purchased modular kit review](docs/unreal-modular-kits.md)
- [Capital expansion authoring and verification](docs/unreal-capital-expansion.md)

Browser source and retired tests remain in the tagged Git history. Recovery
snapshots and unfinished asset-worktree candidates remain private under ignored
`artifacts/retirement-recovery/`; keep the original worktrees until their remaining
local material is reviewed. These same-disk snapshots do not protect against disk
loss and should be copied to encrypted off-device storage.

Scenario queue architecture, local-host setup and acceptance guidance: [In-game scenario queues](docs/unreal-scenario-queues.md).
