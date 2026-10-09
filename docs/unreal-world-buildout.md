# Aegis/Riftbound world buildout

Interactive T1 launches must use the isolated `T1HumanReview_<revision>`
walkthroughs and `launch-t1-review.py`. The raw terrain studies retain their
technical anchor at zero; ordinary Play there could spawn below ground and
cannot use the GM workbench. `stage-t1-review.py` duplicates only routing and
places its regional anchor at a native ground/capsule-verified village arrival.
The launcher selects that map only for its process and opts into local GM.
Normal character entry and recovery are verified by `--proof`; GM draft storage
is isolated from capital/owner documents. Broader T1 world-builder catalog,
ordinary persistence, network and gameplay acceptance remain open.

The [T1 redesign](t1-redesign.md) now provides four terrain/topology candidates,
shared spatial support, a replicated regional clock and isolated first-pair
native prototypes. Active campaign/capital packages remain preserved. Village
completion, effects/audio, visual and live play acceptance remain open; the
existing first-pair lair and batch sequence gates still apply.

Read-only T1 obstacle checks now cover retained keep approaches and village
circulation. Separate private furnished-home studies provide measured doorway,
floor and step routes with local interior exposure; their regional appearance,
GM persistence and license acceptance remain outstanding. A separate development
fixture now walks first-pair roads/supply routes in both directions and four
furnished-home routes with normal native CharacterMovement. Real-time home
captures use the normal follow camera. These receipts establish configured
walking/collision evidence; driving, full camera and gameplay acceptance remain
outstanding. See the T1 reproduction commands and private coverage/gallery receipts.

The next isolated copies add source-reviewed regional ground materials, with
world-space metre scales and compiled native colour/normal graphs. Their saved
mesh/collision, practical-light and furnished-room inventories match the parent
home studies. Read-only material reviews retain player-height day/dusk/night
pictures and full-width ground samples. Material copies have their own normal
walking receipts; no parent movement or appearance acceptance transfers to them.
Lighting calibration, translucent road cost and denser regional dressing remain
open. The active campaign continues to use its accepted capital bindings.

Fresh first-pair atmosphere layers now opt into local bounded weather geometry
and original synthesized activity sound beds. The actor consumes the authoritative
regional clock/weather without mutating campaign state, disables itself on
dedicated servers and fades nature/work/military pressure according to location,
daylight and shelter. Authoring preserves the parent room/light/scenery inventory;
read-only native captures and WAV previews remain private. Normal home traversal
can record actual effect activation and sheltered interiors using the world clock.
Steam readability, some mineral camera views, listening approval, hardware audio,
network synchronization and performance remain unverified.

The approved scope is 32 existing zones and 70 directed portals in the main
AegisWar project. Implementation has begun with shared foundations and
Sunmeadow March/Cinderfen Outskirts. **No zone or batch is complete.**

## Saved world and ownership

The owner's FinalAppearance capital retains its startup map, architecture,
population, lighting, detail and existing GM baseline. The former combined
campaign was copied into a routing level and 32 pairs of Generated/Authored zone
levels. Routing retains all 32 anchors and 70 portals. The 16,369 original
campaign actors were compared before/after copying for identity, transforms,
tags, mesh/material assignments and collision. The original combined level and
pre-attachment main-map backup remain local.

Managed edits check package/source fingerprints, back up generated levels, and
refuse conflicts instead of overwriting owner edits. Regeneration does not write
an Authored level. `partition-capital.py` copies the complete saved capital into
its authored level, preserving private brush data, 9,150 actors and all compared
component state. Its unchanged 25-actor population level also streams with Bastion.
The original startup map path is retained as a lightweight persistent container.
The extraction receipt records backups and before/after package fingerprints.

GM history retains stable IDs and source fingerprints while actors unload.
Soft model/material references avoid retaining capital assets through the catalog;
level reload rebinds authored actors and reapplies the current draft. Created
objects return in their template's level. Missing or changed originals produce a
conflict without replacing the draft, undo/redo or markers. Broader zone-aware
GM construction/catalog support remains unfinished.

`artifacts/unreal/world-portals/zone-manifest.json` records identities, source
hashes, level references, dependencies, routes, counts, native mesh/material/
collision inventories, pending content and separate environment, gameplay,
traversal, visual, network and release states. `coverage.json` inspects the saved
world and lists NPCs, resources, missing enemies, mechanisms and objectives by
source identity. Inventories do not grant visual or gameplay acceptance.

The nine placed combat NPCs have exact [equipment bindings](unreal-npc-equipment.md),
including bone-attached spears, shields and sidearms and the scout's embedded bow.
Missing required equipment blocks native combat readiness and zone admission.
The catalog uses soft asset references, and generated attachments do not modify
the saved capital or zone packages. Unbuilt combatants remain explicit coverage gaps.

## Travel and asset admission

`UWarZoneStreamingSubsystem` loads the server's occupied/requested zones and
requests only each remote player's occupied/requested levels on that client.
Travel waits for server collision and the client's engine visibility
acknowledgement, then reruns reciprocal-route, range, cooldown, ground, slope and
capsule-clearance checks. Only the entering pawn moves. Walking out, death, pawn
changes, lost visual readiness or a 30-second deadline cancel pending travel.
Missing destination references fail without moving the player. GM travel and
respawn also wait for content. Unoccupied campaign levels, including the capital,
unload after the brief travel hold. In the editor, Unreal loads referenced sublevels
for world authoring; seeing the whole layout there does not establish runtime
residency. For focused editing, open a zone level from its manifest.

All loaded zones incur memory and scene-management costs even when out of view;
visible meshes, lights and shadows may add GPU cost. Runtime isolation therefore
matters. Actor/level residency checks do not measure FPS or production memory.

These are development-session level loads within one server. Durable online
handoffs, Steam ownership, admission queues, reconnect recovery, 18 players per
realm per contested zone and production GM roles remain closed.

Resource interaction resolves an exact `world-visuals.json` binding for purpose,
zone, node, source visual, mesh, ordered material slots and collision profile.
An imported folder name alone no longer admits a model. The catalog is tied to
the staged gameplay source revision and records source/native package hashes;
missing or changed bindings return a recoverable error. The initial catalog
preserves six working Aegis and eight Riftspire nodes and adds two Sunmeadow and
four Cinderfen herb patches. `migration/world-resource-sources.json` reviews exact
source replacements and model fingerprints; complete multi-material source
surfaces are retained. `record-world-visuals.py`
checks prior placement receipts and writes changes to a conflict file instead
of replacing existing bindings. These bindings are Development only. Skeletal
imports retain separate exact mesh/animation/source validation. General
scenery/GM admission and per-kit release/license review remain open.

## First batch

Sunmeadow and Cinderfen now use complete 4x4 sets of source terrain sectors:
32 ground surfaces, 19 road overlays and 9 water surfaces. Conversion retains
vertex colors and source alpha behavior. Road/water overlays do not support
collision. Footprints and locations remain unchanged. Native LODs, biome detail,
shoreline/interior walking, navigation and final visual review still need work.

Six exact source characters are placed with imported idle animations:

- Sunmeadow: farmer, herbalist, High Elf scout and Dwarf artisan.
- Cinderfen: Dark Elf supply officer and Greenskin peat worker.

The three added characters passed Blender roundtrip and native raw/compressed
animation checks for all nine source clips. The importer can retry compression
with full-precision rotations while retaining the 1 mm deformation tolerance.
Placement does not implement guard AI or trainer/service transactions. All six
pass saved-scene height, source-facing and foot-clearance checks. Inspected
aerial and character-height captures exposed dark inherited lighting, sparse
scenery and editor nameplate placeholders. The new lighting profiles address the
inherited environment; visual acceptance remains pending.

The six herb patches retain source locations, profession requirements, loot and
cooldowns. The live proof checks full inventory atomically, stale revisions,
successful gathering and repeated requests across all 20 installed sites.
Wood, ore, water and many other required gathering models remain missing.

## Zone lighting

`UWarZoneLightingSubsystem` applies one local-view environment from the current
player's zone. The 32 profiles in `WarZoneLightingProfiles.cpp` specify distinct
sun direction/color/intensity, fill, fog and exposure/grading: warm limestone
farmland, amber geothermal marsh, cool gorge, snowy pass, slate moor, volcanic
gate and separate lair themes. Bastion uses its preserved authored environment.
Transient lights do not replicate, change saved maps or follow other players on
the shared server. Dedicated servers do not create these cosmetic actors.
Authored local lamps remain part of their zone. Editor previews use the same
profiles explicitly; native automation verifies restoration and bounded actor
counts. `inspect-world-lighting.py` captures all 32 approaches and checks saved
hashes and restoration. Profiles/captures alone do not grant art acceptance.

Sunmeadow now has its three source Campaign Raiders using an exact imported
visual. Native development behavior includes server-owned chasing, ordinary
melee, leash reset, atomic XP/loot/quest attribution, death and safe respawn.
Enemy state outlives zone unloading. The source Hamstring special, navigation,
equipment/visual acceptance and network combat checks remain open. See
[native enemy implementation and checks](unreal-enemies.md).

Cinderfen's expedition remains assigned to Cinderfen. Its dispatch model,
native enemies and live kill attribution still need implementation. The Aegis
expedition stays in Brightfen for batch two. Sunmeadow receives no replacement
quest chain. Warden's Hollow and Cindermaw Pit remain unfinished and must
complete alongside the first pair before advancing.

## Remaining sequence and gates

`world_zones.py` fixes the approved order, including optional lairs in the first
six batches: Sunmeadow/Cinderfen; Brightfen/Ashen; Greybrook/Bleakroot;
Glassriver/Gorepine; Ironwood/Vilemere; Highvale/Obsidian; Crownworks;
Dawnline/Shatterline; Starfall/Voidgate; final capitals. Capital services and
adjoining approaches accompany early batches.

Each zone still needs its full grounded environment/navigation, materials and
vegetation, settlements/interiors, mechanisms, NPCs/encounters, resources,
atmosphere and atlas presentation. Lairs require bosses, supporting encounters,
rewards and return travel. Require live walking/combat/quest/resource/reward
tests, full-inventory/retry failures, repeat-build preservation, player-view art
review and measured frame, memory and travel performance before completion.

Broader native enemy AI, patrols, navigation, shared kill attribution, keep encounters,
capture/defense, caravans, siege, campaign progression, authoritative world
publication, wider GM catalog expansion and full performance
acceptance remain substantial work. The RPG pairs precede wider warfare.
Steam, Windows/Linux/macOS clients and Linux servers remain mandatory release
gates. No new assets were purchased and no release approval was granted.

## Reproduction and evidence

Close saved editor/game processes before changing maps or native modules. Run
all commandlets in the main AegisWar project. Python exceptions can accompany
a successful process exit; require a fresh success marker and receipt.

1. On an unpartitioned build, run `partition-world.py`, inspect its candidate
   and actor snapshots, then `attach-partition.py`. Run `partition-capital.py`
   to extract the preserved capital and its population. `attach-world.py` refuses to
   replace an attached partition with the old layer.
2. Export sectors with `python scripts/unreal/world_landscapes.py`, then run
   `apply-world-landscapes.py` in Unreal. Matching reruns do not edit maps;
   changed inputs/packages require reconciliation.
3. Convert/import exact profiles through `convert-model.py` and
   `npm run unreal:import -- --profile <key>`, then run `populate-world.py`.
4. Run `populate-world-resources.py`, `record-world-visuals.py`,
   `inspect-world-coverage.py`, `render-world-portals.py` and
   `inspect-world-lighting.py`. Rendering requires
   `-AllowCommandletRendering -RenderOffscreen`; lighting previews are transient.
5. Run the main map with `-game -WarDevelopmentGM -WarPortalProof -nullrhi`;
   save its log as `artifacts/unreal/world-portals/traversal-main.log`, then run
   `python scripts/unreal/verify-world.py`. It requires all 70 routes, deferred
   loading, failure/cancellation, all 20 resource identities and final respawn.
   It also saves a disposable GM edit before travel and checks actor state,
   unload, undo/redo and draft reload after respawn. Proof drafts use a unique directory
   under `Saved/WorldEditPortalProof`; the owner's normal draft is untouched.
6. `npm run unreal:zone-network-proof` starts a background dedicated server and
   two loopback clients. It checks per-client loading, other-player isolation,
   inventory/pawn retention, vacant-capital unload and actual-client residency
   with saved-package hashes. Clients report only their current zone's content,
   zero persistent static meshes and their own active lighting profile.
   This does not establish Steam or rendering performance acceptance.
7. Run `npm run unreal:test-native`, `npm run test:unreal`,
   `npm run typecheck:unreal-tools`, `npm run unreal:audit`, and focused Python
   tests `unrealWorldZones`, `unrealWorldStatic`, `unrealWorldLandscapes`,
   `unrealWorldResources`, `unrealModelImport` and `unrealPoseParity`.
   `npm run unreal:release-check` must still fail.

Native assets, backups and purchased dependencies remain private/ignored.
`build.json`, `zone-manifest.json`, `coverage.json`, `verification.json`,
`render-verification.json`, network reports and each profile's
`editor-import.json` describe distinct evidence; none substitutes for another.

## Verified development checkpoint, 2026-09-22

`continuation-receipt.json` records the current evidence and explicit incomplete
gates. Editor and Game builds passed, along with 33 native automation groups,
94 tooling tests, 33 focused Python tests, tooling typechecking and the Unreal
audit. Strict release checking returned exit 1 as required.

The final 70-route run retained inventory, gathered all 20 installed sites and
restored GM draft/undo/redo after actual capital unload, reload and respawn.
The two-client loopback proof recorded only Sunmeadow's two levels (2,593 actors)
on its client and Riftspire's two levels (7,473 actors) on the other, with zero
persistent static-mesh actors on either client. The vacant capital unloaded on
the server. These are scene-residency observations, not measured FPS gains.

A fresh process compared all 9,150 capital actors to the preserved source state,
confirmed the unchanged music setup, and checked extraction rerun idempotence.
All 32 lighting profiles were captured from grounded approach views without
changing saved maps or authored environment settings. Saved-scene checks cover
70 portal labels, six source NPCs and six frontier herb patches. Later zones
remain sparse and some shaded views need further tuning; visual acceptance and
all zone/batch completion remain pending.

## Isolated T1 assembly studies

The T1 terrain/story/RvR candidates and their exact verification commands are
documented in [T1 redesign](t1-redesign.md). Furnished-home shell studies use
fresh Review/Generated/Authored copies of the first-pair atmosphere maps.
`build-t1-shell-studies.py` reconstructs frozen modular parts with corrected
roof attachment datums, retaining source packages, doorway/floor/furniture
geometry, material slots and surrounding scene state. `review-t1-shells.py`
provides parent/refit native eave witnesses; `review-t1-homes.py -WarT1Shells`
(flag on the Unreal command line) and `run-t1-traversal.py --candidate shells`
provide independent saved-scene clearance, rendered and walking evidence.
These fixtures retain ordinary GM, campaign/network, appearance, vehicles,
competitive, licensed distribution, platform and release acceptance gates.

`build-t1-ceiling-studies.py` extends fresh shell copies with separately merged
kit timber bays and a bounded interior fill, preserving every existing actor
binding. `review-t1-ceilings.py` records ceiling-only upward grid witnesses;
foreground house hits remain explicit and the independent capsule review uses
all furniture collision. `review-t1-homes.py -WarT1Ceilings` and
`run-t1-traversal.py --candidate ceilings` produce independent saved-scene and
normal walking/camera evidence. Source kit assets and accepted capital/campaign
layers remain private and unchanged; these studies grant no additional gates.

`build-t1-population-studies.py` preserves canonical NPC/resource rules and
catalogs while installing exact ready native actor classes in fresh copies.
`review-t1-population.py` cold-loads bindings/equipment, samples ground and
checks supported capsule approaches. Failed terrain access stays pending;
native actor placement does not accept service/harvest actions or Node geometry.
`build-t1-relief-studies.py` then raises enclosing ridges and basin walls in
separate terrain meshes. Masks preserve roads, anchor terraces, existing content
bounds and those actor approaches. `review-t1-relief.py` compares full-width
road heights against the parent and captures matched native player-height
vistas; `run-t1-traversal.py --candidate relief` proves normal walking in the
new copies. Source normals retain the original clockwise triangle topology.
Unverified cliffs/erosion, lighting, off-road movement, siege/vehicle/sight-line
fairness, ordinary GM/network, first-pair lairs and release gates remain open.

The next first-pair battlefield pass uses `shared/terrainField.ts` and
`t1-battlefield-landscape.ts` for connected ridge/drainage mass, elevated roads
and three unpainted off-road links per zone. `prepare-t1-battlefield.ts` writes
new immutable Node/terrain source bundles; `build-t1-battlefield.py` creates
fresh private copies with complete keep/home assemblies rebased vertically.
Explicit home footing and approach grading repair a Cinderfen walking regression
from a neighboring road shoulder. Old source/native scenes and owner drafts
remain preserved; active campaign/native acceptance stays unchanged.

`t1-battlefield-scenes.ts` prepares four small camera-review cells from retained
source assets. `build-t1-battlefield-scenes.py` clones private candidates with
embedded rocks, grove/reed groups and source-channel material adaptations.
`review-t1-battlefield.py -WarT1BattlefieldScenes` verifies native ground/grades
and renders player-height views. `run-t1-traversal.py --candidate battlefield-scenes`
with `--headless` checks configured normal walking, including all unpainted ground
links and retained homes. After matching native review/walking receipts,
`stage-t1-review.py -WarT1BattlefieldScenes` stages safe interactive GM routing.
These prototypes do not accept appearance, cover balance, vehicle/siege/18v18,
ordinary GM persistence, network, full lairs, platform/Steam or release gates.

Road surface export must retain vertex alpha. First-pair terrain-field candidates
use three-metre verges and mixed-scale, rotated source-channel detail; the optional
variation graph preserves legacy material recipes elsewhere. Validate combined
surface slope across two-metre lanes, including sideways bank, and compare native
collision normals against the .22 target. Rendered review checks committed road
corner alpha and the explicit `-abslog` for shader fallbacks before publishing a
usable review receipt. A successful null-RHI build or commandlet exit cannot grant
shader/render acceptance. See `tests/unrealT1RoadVerge.test.ts` and the focused
surface-variation/render-log Python checks.

Preserve baseline references by qualified receipt, rather than `review-latest`
or a mutable scene-parent pointer. The final first-pair scene `12cc9a6e4683`
passes 72,296 ground samples, saved road fades, rendered shader checks and 110
configured normal walking routes. Walkthrough `c8b15f5ac634` passes ordinary entry
and local GM recovery for both regions, preserving all 13 owner documents.
These results leave landscape appearance, driving/combat and other release gates
open. Exact receipt paths and test scope are recorded in `docs/t1-redesign.md`.


### 2026-10-09 T1 landscape/ecology iteration

First-pair candidate `e6eaa25eb1f7` adds broader terrain transitions, optional
watershed weathering, eight scenery neighborhoods per region, source-channel
substrate/rock variation, bounded native HISM cover and three shallow cosmetic
pools. `review-t1-battlefield.py -WarT1BattlefieldScenes` verifies saved instances,
98 rendered views/shaders and full-width native ground; configured normal walking
passes 122 routes. Keep raw Review maps as authoring inputs; stage fresh safe
Walkthrough routing and use `launch-t1-review.py --proof` for each final revision.
All work is isolated from accepted capitals, active maps and owner-authored layers.

The native detail actor has no collision/navigation/replication and uses 120m
culling; this is not a frame/memory budget acceptance. Source grass remains high
detail. Water is a terrain-supported cosmetic study, not new swimming/hazard
behavior. Water, terrain composition, regional scenery and all appearance remain
unfinished despite successful technical checks. First-pair full-lair gates remain.

`npx tsx scripts/unreal/prepare-t1-second-pair.ts` prepares source-only Brightfen
island-chain/causeway and Ashen layered-plateau/wash experiments. It does not
advance native batch acceptance. After both first/second source bundles exist,
`python scripts/unreal/t1-landscape-atlas.py` writes labeled measured drawings.
Later-pair native environments and underground spaces are still outstanding.
See `docs/t1-redesign.md` and private signature-qualified receipts for precise
verification; retain all human, combat, persistence, network/platform and release
gates. Close saved Editor/game processes before any native module/content rebuild.


The isolated shoreline iteration `66ce92c05559` / safe walkthrough `cd0c11467c46`
adds terrain-following bank groups, denser cosmetic sedge/grass, corrected source
mask ranges and gentle oblique water ripples. Fresh native render, 122 configured
walking routes, twelve actual gameplay-camera views and both ordinary-entry/local
GM recovery fixtures pass. The private report embeds images directly. This is a
verified technical checkpoint with unfinished terrain and shoreline art; every
human, vehicle/combat, lair, persistence/network/platform and release gate remains.


The counterable-scarp checkpoint `f27c9bdf8572` / safe walkthrough `d2edaa5c27c8`
adds two full-width graded back climbs per region, native capsule admission and
continuous radial ridge ends. The initial taller scarp and discontinuous end cap
were rejected/repaired before this checkpoint. Fresh source/native full-width
ground/grade, 102 rendered views, 138 normal walking routes, twenty gameplay-camera
pictures and both ordinary-entry/local GM recovery fixtures pass. All 13 owner
documents and saved bindings remain unchanged. The private report embeds PNGs.
Repository: 1,105 tests; Unreal selection: 484; focused Python: 70; three typechecks;
33 maps/906 model records. A timed-out fixture passed unchanged on retry and full
rerun; prior native build/Foundation results retain their scope. Terrain/art remain
unfinished, later native batches/underground remain unbuilt, and every existing
lair, human, combat, persistence/network/platform and release gate remains open.


## T1 geological detail and sharper Cinderfen face (9 October 2026)

Private checkpoint `07b8d1ada507` uses source `708c945e1304`, core
`98a83452c28b` and safe walkthrough `23a7dff0f18d`. Its qualified private HTML
report embeds fourteen unedited native images/labeled drawings, with no external
image links. Source-derived rock normals are bounded cosmetic detail, with a
20-120cm pixel-footprint fade; collision geometry is unchanged by the shader.
Cinderfen counter-climb transitions narrow to 20m while Sunmeadow keeps 40m:
Sunmeadow's narrower variants failed grade admission. Cinderfen's measured exposed
section rises from grade 0.312 to 0.809; full-width native route maxima remain
0.213925/0.205313 against the unchanged 0.22 limit.

Fresh checks pass 102 rendered views, all 138 configured normal walking routes,
eight scarp-camera and twelve pocket-camera images. Ordinary entry/GM recovery
fixtures `3d7d91b194d344cd9dfe453a1675026c` and
`e2b303c4ccec4a749e3651f1a256705e` pass without draft writes. All 13 owner
documents and saved candidate bindings remain preserved. Atlas `32e39b35c7a9`
labels all four source studies. Repository verification passes 1105 tests/171
files, Unreal 484/90, focused Python 76/20 and three typechecks; world/models
remain 33/906 and strict release exits 1 as required. No C++ changed in this
checkpoint; earlier native build/Foundation evidence retains its earlier scope.

Read-only `current-navigation-inventory.json` verifies zero bounds and zero
Recast actors in both current candidates. Native AI and convoy navigation is
missing; walking success grants no driving acceptance. Dedicated private T1
navigation copies are the next integration step. Ground repetition, sparse
scenery and larger landscape composition still need work. Later-pair native and
all underground environments remain unbuilt; first-batch lairs, human visual,
actual vehicle driving/18v18, service/resource behavior, ordinary GM persistence,
online/network/audio, platform/performance/Steam and release gates remain open.


## T1 private navigation and gate passage checkpoint (9 October 2026)

Source `83b37fc34b68`, core `d1be86347dfc` and landscape scene
`581f4f8c8327` add candidate-only 7.5m gate openings and 8m approach roads.
Gatehouses, leaves, source collision and gate metadata receive the same lateral
adaptation; IDs, positions, height, depth, interaction state and assembly anchors
remain retained. Four native gatehouses are adapted. Four animated native gate
leaf assemblies remain pending, so closed-gate behavior is not verified.

New editor-only T1 navigation tooling bakes both retained profiles in isolated
routing copies. Convex nonblocking exclusions exactly cover the exterior of
rectangular or concave playable outlines. Existing bounds, modifiers and Recast
data are never replaced. Static tile inventories are bounded and compared across
save/reload, using the existing default query budget and original agent sizes.
The earlier diagnostic passed 84/88 queries; all four failures were convoy keep
approaches through 6m gates, narrower than the retained 6.4m agent diameter.
After the aligned passage repair, navigation `d54e08045a9e` passes all 88 route /
profile queries before save and after reload. This proves navigation connectivity,
not physical driving, turning clearance, closed gates or combat fairness.

Safe walkthrough `7318b5347d1a` preserves both exact baked tile payloads after
routing-copy save/reload. Ordinary entry/local GM recovery fixtures
`3b4097e2846f4720b8423be3febfbfd4` and `68fa1cb65398431ba4359f2998fba091`
pass without draft writes. Fresh landscape checks pass 102 rendered views and
138 normal walking routes. Full-width grades remain below the unchanged 0.22
limit. All 13 owner documents and pinned parent/capital maps remain preserved.

Verification: 1,108 repository tests / 172 files, Unreal selection 487 / 91,
85 focused Python checks / 22 files, and 151 native Foundation tests pass.
The current Windows Editor build passes; the earlier Windows Game build retains
its editor-only-change scope. Three typechecks, migration audit and world/model
validation pass. Strict release still exits 1. Heavy native collision export
warnings remain unresolved performance work; warnings were not suppressed.

Ground repetition, sparse scenery and harsh foliage shading remain unfinished.
A separate private foliage experiment preserves original LOD-zero geometry and
creates three descending native detail levels; this is not integrated landscape,
visual or performance acceptance. Later-pair native environments and underground
environments remain unbuilt. Preserve first-batch full-lair progression, human
visual, actual walk/drive/18v18, service/resource behavior, ordinary GM persistence,
network/audio, platform/performance/Steam and release gates.


The navigation copies additionally pass all 138 normal walking routes in run
`1791569592501202300-20396`. Private report
`progress-report-navigation-d54e08045a9e.html` embeds fourteen fresh, unedited
native images/labeled topology drawings. Its qualified receipt is
`navigation-checkpoint-d54e08045a9e.json`; it grants no art/driving acceptance.


## T1 foliage and shallow-water checkpoint (9 October 2026)

Private scene `76b47c33f5d8`, navigation `e716cd49820d` and safe walkthrough
`266b62bcfce3` retain source `83b37fc34b68` and the existing battlefield terrain.
Fresh private grass assets preserve exact original LOD-zero geometry/source
channels and add three descending native detail levels. Deterministic short-grass
colonies produce 9,106 Sunmeadow and 6,375 Cinderfen instances, retaining the
12,000-instance ceiling, local-only/no-collision policy and 35-120m culling.
Leaf-only private overrides adapt 331 Sunmeadow tree/shrub actors while preserving
bark, geometry and collision. More instances alone did not solve sparse scenery.

Bounded water normals and optical coefficients make shallow pools more readable
through the normal gameplay camera. Terrain, surface geometry and collision are
unchanged. Twelve actual follow-camera images cover all six exploration pockets;
three have water. Uniform banks, repeated ground and harsh small-tree silhouettes
remain unfinished. No visual or performance acceptance is claimed.

Fresh verification passes 102 rendered views, 138 configured normal walking
routes, 88 pedestrian/convoy navigation queries before save and after reload,
exact safe-copy tile payloads, and both ordinary entry/local GM recovery fixtures
without draft writes. Entry runs are `833e2ecd85f34964beaf0642a5e8c1b5` and
`dbe7255bac964b128563a7b4939643d9`. All 13 owner documents and pinned parent /
capital maps remain preserved. The additional navigation-copy walking rerun
belongs to earlier `d54e08045a9e`, not the current navigation copy.

Repository tests pass 1108/172 files, Unreal selection 487/91, focused Python
90/24 and all three typechecks. Migration audit and world/model validation pass;
strict release exits 1 as required. No C++ changed; earlier Windows Editor/Game
builds and 151 native Foundation tests retain their documented earlier scope.
Private `progress-report-foliage-76b47c33f5d8.html` embeds fourteen actual native
images/labeled drawings; `foliage-checkpoint-76b47c33f5d8.json` records their hashes.

Retain human visual, full first-batch lairs, actual vehicle driving/turning,
closed animated gates, 18v18, service/resource behavior, ordinary GM persistence,
online/network/audio, frame/memory/travel, three-platform/Steam and release gates.
Later-pair native environments and underground environments remain unbuilt.


## T1 habitat and geology checkpoint (9 October 2026)

Private scene `b99d62c9cd25`, navigation `eedfcb75c61a` and safe walkthrough
`5321f9e28380` retain source `83b37fc34b68` and the original battlefield terrain.
Continuous world-space habitat masks vary soil, macro colour and shoreline
moisture. Soft regional strata fade below pixel scale; normals do not displace
terrain. Fresh canopy assets preserve source positions, topology, UVs, colours,
bark normals/materials and collision policy while adapting leaf normals.

Source width/depth/height must map to native depth/width/height. Correcting this
mapping makes nonuniform outcrops follow the intended ridge direction. The
superseded `19e40f345b04` experiment was deliberately stopped during read-only
walking before navigation/entry admission. The corrected candidate places 13
Sunmeadow and 23 Cinderfen broken outcrops, reserving routes, anchors and overlooks.
Oriented footing samples embed rock feet; estimated centre exposure is an
authoring filter, not a measured minimum visible height.

Fresh checks pass 104 rendered views, 138 configured normal walking routes,
88 pedestrian/convoy navigation queries before save and after reload, exact safe
navigation payloads, both ordinary entry/local GM recovery fixtures without draft
writes, and 12 actual follow-camera pocket captures. All 13 owner documents and
pinned parent/capital maps remain preserved. Current navigation copies have not
separately repeated the walking suite. Repository tests pass 1108/172 files,
Unreal selection 487/91 and focused Python 105/28. Three typechecks, migration
audit and world/model validation pass; strict release exits 1. Full JS/TS suites
ran during the Python-only v4/v5 iteration. Earlier native builds and 151
Foundation tests retain their earlier scope; no C++ changed.

Private `progress-report-habitat-b99d62c9cd25.html` embeds 14 actual native images
and labeled authoring drawings; `habitat-checkpoint-b99d62c9cd25.json` records hashes.
Pale smooth hills, bare foregrounds and harsh trees remain visibly unfinished.
Node terrain matches the source, but additive scene prop collision is not yet
synchronized with Node authority; receipts explicitly retain this integration gate.
Navigation distances remain within 350-750m for all six convoy itineraries per
zone. Sunmeadow's east objective measures about 609m Aegis versus 368m Riftbound;
reinforcement time, exposure/counterplay and combat fairness remain unverified.

Retain appearance, full first-batch lairs, physical vehicle driving/turning,
closed animated gates, 18v18, services/resources, ordinary GM persistence,
online/network/audio, frame/memory/travel, platform/Steam and release gates.
Later-pair native environments and underground environments remain unbuilt.


## T1 two-ended rock shelter studies (9 October 2026)

Private scene `e611847abf0b`, navigation `9779f302d3d3` and safe walkthrough
`e5ff10dc58eb` retain source terrain `83b37fc34b68`. `t1_rock_shelters.py` derives
Hearthroot Fallen Chamber and Rustsedge Fracture Shelter from exact native source
rock bounds, accounting for off-centre roots and width/depth axis conversion.
Each study has two unequal piers, one fallen cap, two open ends and a six-metre
walking lane. Roof bounds sit >=5.7m above the highest sampled walking floor.
No terrain holes, rewards, quests or lair completion are introduced.

Native full-capsule support and bounded 4.2m camera-height samples pass. These do
not grant full camera acceptance. Fresh checks pass 108 rendered views, 142
configured normal walking routes (including both directions through shelters),
88 navigation queries before save/after reload, exact safe-copy tile payloads,
both ordinary entry/local GM recovery fixtures without draft writes, and four
actual follow-camera shelter captures. All 13 owner documents and pinned parent /
capital maps remain preserved. Additive prop collision still requires Node
synchronization; the current navigation copies have not separately repeated the
complete walking suite. Repository tests pass 1108/172 files, Unreal selection
487/91, focused Python 109/29 and all three typechecks. Migration audit and
world/model validation pass; strict release exits 1. Earlier native builds and
151 Foundation tests retain earlier scope; no C++ changed.

Private `progress-report-shelters-e611847abf0b.html` embeds fourteen unedited native
images/labeled drawings; `shelter-checkpoint-e611847abf0b.json` records hashes.
The shelters currently read as oversized monumental assemblies. Natural cave
composition, lighting, bare surroundings and appearance remain unfinished.
Full underground and later-pair native environments remain unbuilt.

An original meadow colour study generated with the built-in image_gen tool stays
private under `artifacts/unreal/t1-redesign/material-studies/`. Its JSON records
the exact prompt and source hash. A non-power-of-two import exposed distant noise;
a separate native import verifies twelve mip levels at 2048x2048. Three-way native
comparisons isolate colour versus slope-to-rock coverage. The study is not
integrated into this scene and has no seamlessness, art or performance approval.
Retain first-batch full-lair, visual, actual driving/turning/closed gates, 18v18,
services/resources, ordinary GM persistence, online/network/audio, performance,
three-platform/Steam and release gates.


## Local T1 terrain transition studies

`prepare-t1-local-terrain-transitions.ts` reads the exact qualified immutable
battlefield source, exports a separate first-pair terrain/map bundle and rejects
an already revised parent. `t1-local-terrain-transitions.ts` changes eligible
transition widths while preserving advance/first-rotation supports, military
pads and route identities. Full-width source grades retain the 0.22 limit.
The exporter checks retained pocket beds, closed water and reciprocal arrivals.

This export alone does not change native scenes. A fresh `build-t1-battlefield.py`
core, `prepare-t1-battlefield-scenes.ts` recipe and scene build/review must precede
new walking/navigation/safe-stage/entry proofs. Never transfer old native receipts
to new terrain geometry. Use `launch-t1-review.py` only after that full chain.
Installed cosmetic understorey batches use `t1_understorey_native.py`; their exact
selected mesh/bounds/LOD/material inventories remain separate from source-derived
three-LOD grass. Licensed packages, comparisons and reports stay private.
