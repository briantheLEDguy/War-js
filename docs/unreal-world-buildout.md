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


## T1 verified local terrain transitions (9 October 2026)

Source `366c962d85ea`, native core `34d1d21ece98`, scene `9e58646034c1`,
navigation `dce65a371320` and safe walkthrough `d703c535e7fc` now have fresh
native proof. Eleven transition bands per zone narrow while the main advance
and first rotation retain broad grading support. Native full-width maxima are
0.21757068 Sunmeadow and 0.21648207 Cinderfen, below the retained 0.22 limit.
Military pads, route identities, pocket beds and closed water remain checked.

Fresh checks pass 108 rendered views, 142 configured normal walking routes,
88 pedestrian/convoy navigation queries before save/after reload, exact safe-copy
tile payloads, both grounded ordinary-entry/local-GM recovery fixtures without
draft writes, and twelve actual follow-camera pocket captures. All thirteen
owner documents and pinned parent/capital maps remain preserved. Navigation
copies have not separately repeated the complete walking suite.

The first scenery attempt stopped at an obsolete fixed 331-canopy guard.
The repair freezes exact source-derived identities for each revision and checks
a bounded 200-500 inventory. Five focused canopy tests pass. Revised terrain
produces 329 canopies, 24722 Sunmeadow cosmetic cover instances and 6221 Cinderfen
instances. Installed Sunmeadow understorey is 6345 grass, 4816 long-grass,
4092 fern and 429 seedlings. No density performance acceptance is implied.
Repository tests pass 1111/173 files, Unreal selection 490/92 and Python 121/32.
All three typechecks, migration audit and world/model validation pass; strict
release exits 1. No C++ changed; earlier native builds/Foundation retain scope.

`progress-report-local-terrain-9e58646034c1.html` embeds fourteen actual native
images and labeled topology drawings; the matching local-terrain checkpoint JSON
records signatures, hashes and exact results. An unsaved twelve-image foliage
parameter comparison gives little visible improvement and remains unintegrated.
Installed foliage already has masked two-sided subsurface shading. Engine setter
return values are unreliable here; the study validates exact parameter readback.
A separate spatial forest-floor/data-mask study remains outside the saved scene.

Smooth empty ground, harsh trees, repeated materials and blocky rock assemblies
remain unfinished. Retain human appearance, first-batch full lairs, physical
vehicle driving/turning, closed gates, 18v18, services/resources, ordinary GM
persistence, Node additive-prop collision synchronization, network/audio,
performance, three-platform/Steam and release gates. Later-pair native and full
underground environments remain unbuilt.


## T1 tactical spurs and contour walking counters (9 October 2026)

Source `a2d01beb1da7`, native core `8db842585edd`, scene `4420b969b33d`,
navigation `06977d038ac7` and safe walkthrough `264e8c31ec86` have fresh native
proof. Two original regional terrain ribbons per zone add a western overlook
and eastern low shoulder. Two four-metre pedestrian counters per overlook follow
existing contours without grading the ground. Existing military assembly heights,
vehicle routes, six supply itineraries, pocket beds and closed water stay checked.
Painted walking paths reserve scenery sockets independently of grading corridors.

Fresh checks pass 114 rendered views, 150 configured normal walking routes,
92 navigation queries before save/after reload, exact safe-copy navigation payloads,
both ordinary grounded entry/local-GM recovery fixtures without draft writes,
and twelve actual follow-camera pocket captures. Native full-width maxima remain
0.21757068 Sunmeadow and 0.21648207 Cinderfen. Four-metre paths use pedestrian
navigation probes; they do not claim the retained 6.4-metre convoy envelope.
All thirteen owner documents and pinned parent/capital maps remain preserved.
Navigation copies have not separately repeated the complete walking suite.

The first native attempt failed a Cinderfen grade of 0.231697, underestimated by
a centred source derivative at a triangle boundary. The repaired contour sampler
checks adjacent faces and segment grades. The next render failed because a camera
focus was on a steep face. Camera footing remains walkable; focus uses a separate
native terrain-only height/normal check. Failed candidates were not admitted.
Repository tests pass 1119/175 files, Unreal selection 498/94 and Python 125/32.
All three typechecks, migration audit and world/model validation pass; strict
release exits 1. No C++ changed; earlier native builds/Foundation retain scope.

`progress-report-tactical-spurs-4420b969b33d.html` embeds nineteen actual native
images and measured topology drawings; its matching checkpoint JSON records
signatures and hashes. Saved cosmetic cover totals 23859 Sunmeadow / 6268 Cinderfen.
Separate unsaved comparisons combine spatial forest-floor blending, stochastic
near/far texture sampling, 7829 focal plants and transient neutral daylight. These
preserve purchased source packages/maps and remain unintegrated/unapproved.

Smooth bare hills, harsh foliage, repeated ground and blocky rocks remain unfinished.
Road triangles can dip below terrain between samples, producing visible grass
cutouts; exact triangle fitting is a separate private study, not this checkpoint.
Retain human appearance, first-batch full lairs, physical driving/turning, closed
gates, 18v18, services/resources, ordinary GM persistence, Node additive-prop
collision/live playtest, network/audio, performance, platforms/Steam and release
gates. Shared terrain-sampler parity is not live Node playtest acceptance. Later-pair
native and full underground environments remain unbuilt.


## T1 terrain-conformed cosmetic roads (9 October 2026)

Source `cbc1c13f223b`, core `676151d36b96`, scene `db75d41d4864`, navigation
`8cbc1cf8593e` and safe walkthrough `ec800afac2d0` have fresh native proof.
Cosmetic road ribbons now follow each rectangular terrain cell and diagonal,
preserving interpolated UVs and soft verge alpha. Terrain and gameplay routes
remain byte-preserved. Microscopic clipping slivers are omitted; clockwise
native front faces and upward normals have a regression test. Initial import
slivers and a manually rejected backface-culled candidate were repaired before
admission. Automated renders alone did not catch the wrong winding.

Fresh checks pass 114 rendered views, 150 normal walking routes, 92 navigation
queries before save/after reload, exact safe-copy payloads, both grounded entry
and local-GM recovery fixtures without draft writes, and twelve actual pocket
follow-camera captures. All thirteen owner documents and parent/capital maps
remain preserved. Navigation copies have not separately repeated all walking.
Road triangles increase to 246228 Sunmeadow / 255434 Cinderfen; vertices to
129066 / 133710. Triangle centroids and edge midpoints clear ground by 0.045m
within 1e-5m. Increased mesh cost remains unaccepted for performance.

Repository suites pass 1125 tests/176 files, Unreal 504/95, Python 125/32.
All three typechecks, migration audit and world/model validation pass; strict
release exits 1. No C++ changed. Earlier native build/Foundation scope remains.
Private `progress-report-road-conformance-db75d41d4864.html` embeds 22 actual
native images and measured source drawings; its matching checkpoint records
signatures and hashes. Unsaved installed-rock geometry/palette studies retain
four LODs but use NoCollision and remain unintegrated/unapproved. Source rock
packages are preserved; original rocks lack simple collision.

Natural composition, repeated ground, harsh foliage and saved blocky rocks remain
unfinished. Preserve appearance, first-batch full lairs, physical vehicle drive
and turning, closed gates, 18v18, services/resources, ordinary GM persistence,
Node additive-prop collision/live playtest, network/audio, performance, platforms,
Steam and release gates. Shared terrain parity is not live Node proof. Later-pair
native and full underground environments remain unbuilt.


## Sunmeadow forest floor and focal colonies (9 October 2026)

Scene `50fd67b23afc`, navigation `3c65777e5c5e`, walkthrough `d7e7d2ba1534`
retain source `cbc1c13f223b` and core `676151d36b96`. New pure/native helpers
`t1_forest_floor.py` / `t1_forest_floor_native.py` blend exact private installed
grass and forest colour/normal channels with matching stochastic translations,
soft canopy masks in rectangular bounds, and retained steep rock layers. A 1024
data mask covers 321 installed canopies. Near tiles are 3.2m; far colour is 7.5m
at 35 percent distance blend. Native shader compilation/rendered review pass.

`t1_focal_planting.py` / `t1_focal_planting_native.py` add four bounded colonies
with continuous edge/clump variation, road/pocket/service/military/water/grade
reserves, and 0.6m spacing from existing and newly added plants. Exact installed
plants retain their LOD/material inventory, NoCollision, local cosmetic behavior
and 35-120m culling. New counts are 3574 grass, 2415 long-grass and 527 fern;
total cover is 30375 Sunmeadow / 6268 Cinderfen. Increased cost is unaccepted.

Fresh checks pass 114 rendered views, 150 walking routes, 92 navigation queries
before save/after reload, exact safe-copy payloads, two grounded entry/local-GM
fixtures, twelve actual pocket follow-camera pictures and eight focal views.
The first Cinderfen recovery attempt failed during a concurrent render study:
initial arrival was 42.125cm from its anchor. Three isolated reruns passed with
no code/map changes. Cause remains unresolved; retain entry/recovery repeatability
as a gate. The failed run is `dcbcb193399f4842a39880a921709851`. No runtime repair
is claimed. All thirteen owner documents and parent/capital maps remain preserved.
Navigation copies have not separately repeated the full walking suite.

Repository suites pass 1125/176 files, Unreal 504/95 and Python 133/34, including
eight new reserve/spacing and mask-projection/union/PNG tests. Three typechecks,
migration audit and world/model validation pass; strict release exits 1. No C++
changed. Earlier native build/Foundation scope remains. The private
`progress-report-forest-focal-50fd67b23afc.html` embeds 24 native pictures and
source drawings; its matching checkpoint records exact signatures and hashes.
Neutral daylight and collision-enabled installed-rock comparisons remain unsaved
and unintegrated. Original rock packages are preserved; clone-only simple/complex
trace counts match 24/25, 23/25 and 22/25. This is not candidate collision approval.

Bare slopes, harsh foliage, repeated distant ground and blocky saved rocks remain
unfinished. Retain appearance, first-batch full lairs, actual vehicle/closed-gate
and 18v18 play, services/resources, ordinary GM persistence and recovery
repeatability, Node additive geometry/live play, network/audio, performance,
platforms/Steam and release gates. Later native pairs/full underground remain
unbuilt. Shared terrain parity is not a live Node playtest.


## Collision rock clusters and offline sky review (10 October 2026)

Scene `c53c9611204b`, navigation `3e3926be9ff0` and walkthrough `df033792d07f`
retain source `cbc1c13f223b` and core `676151d36b96`. New pure/native helpers
`t1_rock_clusters.py` / `t1_rock_clusters_native.py` fit three exact installed
rock shapes inside retained parent reserves. Rotated full bounds, modest yaw
variation, native pivot offsets, minimum-of-25 terrain footing and exposed-height
checks replace 88 Sunmeadow parents with 163 bodies and 116 Cinderfen parents
with 217 bodies. One/four unscalable or buried parents retain their previous
assemblies. Shelters, original core outcrops, terrain, roads and gameplay
assemblies retain their bindings. The clones preserve committed LOD0 geometry,
four LODs and source thresholds. Private material copies zero inspected pixel
depth offsets; source packages remain exact. Complex-as-simple triangle collision
is explicit. Nine component-only rays per body prove matching simple/complex
surfaces and exposed actual geometry; saved reload repeats those checks.

Initial commandlet clones returned zeroed transient LOD thresholds even though
reloaded packages matched the source. Explicit copied thresholds and saved-mesh
rechecks repair that construction path. Earlier failed build logs are retained.
`t1_sky_preview.py` explicitly updates the one tagged local regional skylight for
offline captures, whose engine path skips real-time sky capture. It restores
transient rig modes on exit/failure and refuses missing/ambiguous rigs. Authored
regional/capital lighting profiles remain unchanged.

Fresh checks pass 114 rendered phase/weather views, 150 normal walking routes,
92 navigation queries before save/after reload, exact safe navigation copies,
two grounded entry/local-GM fixtures without draft writes, twelve actual pocket
follow-camera pictures and sixteen saved-rock day/night views. All thirteen owner
documents, parent candidates, capitals and seventy nature source packages remain
preserved. Navigation copies have not separately repeated the full walking suite.
Full-width grade maxima remain 0.21757068 Sunmeadow and 0.21648207 Cinderfen.
Both entries pass now; the previous concurrent Cinderfen recovery failure remains
unresolved, with repeatability and ordinary GM persistence still gated.

Repository suites pass 1125/176 files, Unreal 504/95 and Python 140/36, including
seven new fitting/reserve/pivot/burial/input and sky-restoration/order tests.
Three typechecks, migration audit and world/model validation pass. Strict release
exits 1; no C++ changed. Earlier native build/Foundation scope remains. The private
`progress-report-rock-clusters-c53c9611204b.html` embeds 24 actual native pictures
and measured source drawings; its checkpoint records signatures and image hashes.

Distant slopes remain smooth, foliage harsh and rock colour insufficiently
regional. Increased actor/material/collision cost and existing heavy collision
export warnings remain unaccepted. Eroded owned-kit backdrop inspection/staging
is private; any unsaved composition study remains outside admitted ownership
bounds and is not an integrated landscape. Preserve human appearance, first-batch
full lairs, physical vehicle driving/turning/closed gates, 18v18, services/resources,
Node additive geometry/live play, network/audio, performance, three platforms,
Steam and release gates. Later-pair native and full underground environments
remain unbuilt. Shared sampler parity is not a live Node playtest.


### Private rock contact checkpoint - 10 October 2026

Scene `0d633e30966b` / navigation `ff8835fb85c3` / safe copy `b056429b854e`
add bounded unique-LOD0-vertex bedding and five/seven selected original outcrop
replacements. Source/core terrain and gameplay assemblies remain retained.
Native reload repeats bedding, source geometry/LOD thresholds and component
simple/complex surface checks. Fresh 114 views, 150 walks, 92 navigation queries,
two entry/local-GM fixtures, twelve pocket cameras and sixteen closeups pass.
Thirteen owner documents and parent/capital/source packages remain preserved.
Python 148/38, repository 1125/176, Unreal 504/95 and required typechecks/audit/
world/model validation pass; strict release exits 1. No C++ changed. Detailed
evidence and limitations are in `docs/t1-redesign.md` and the private matching
checkpoint. All previous batch/visual/vehicle/combat/persistence/network/
performance/platform/Steam/release gates remain; drainage studies are unintegrated.


## T1 compact drainage checkpoint - 10 October 2026

Source `aae1209eb967` / core `8d344fd4519e` / scene `93003b49b5f1` /
nav `b3fd5077cf4c` / safe `2693f53b9efc` qualify bounded first-pair incision authoring.
Roads, military assemblies, arrivals and closed cosmetic basins remain retained.
Native 114 views, 150 walking routes, 92 navigation queries before save/reload,
both entry/local-GM fixtures, twelve pocket cameras and twenty-four day/night captures
pass. Extra terrain rays verify 363 incision controls; camera capsule footing
is clear. This does not accept complete gully walking, physical driving or combat.
Repository 1132/177, Unreal 511/96, Python 148/38, three typechecks, audit and
world/model validation pass; strict release exits 1. No C++ changed. Owner thirteen,
parent maps, capitals and seventy nature source packages remain preserved.
The private drainage report embeds 28 images; smooth/regular slopes remain an
art defect. Keep prior recovery, first-batch lair, appearance, persistence, live
Node/additive geometry, network, performance, platforms/Steam and release gates.
Later native batches/full underground and owned-mesh residual integration remain
unbuilt. Native/licensed candidates and receipts stay private.


## T1 private source-derived relief checkpoint - 10 October 2026

Source `1cd84df61040` / core `bd8812c7434e` / scene `1e7203cb76e2` /
nav `df574d641bb1` / safe `e4f6e9fc2090` qualify bounded rectangular owned-mesh
height detail and smooth route/footing exclusions. Private derivatives use exact
native rendered faces and complete 257x257 coverage. Native 114 views, 150 walking
routes, 92 navigation queries before save/reload, both entry/GM fixtures, twelve
pocket cameras, 24 extra views and 578 terrain ray locations pass. Node loader
terrain parity is within 0.031mm over 4575 samples; live/additive collision remains
unverified. Owner thirteen, parent maps, capitals and 92 source packages remain
preserved. Repository 1141/178, Unreal 520/97, Python 148/38, three typechecks,
audit and world/model validation pass; strict release exits 1. No C++ changed.
The embedded 28-picture relief report records remaining art defects and all
appearance, recovery, lair, vehicle/18v18, persistence, services, live/network,
performance and platform/Steam/release gates. Later native/full underground,
neutral daylight and route-curve studies remain unintegrated.


### T1 softer daylight receipt (10 October 2026)

Source `1cd84df61040` / core `409a2b6095c2` / scene `8c1018ccd774` /
nav `54bb95b837a4` / safe `9f398cd36999` qualify Sunmeadow's softer direct/diffuse
lighting. Cinderfen warmth, night output and capital restoration remain retained.
Editor/Game builds, 151 Foundation tests, fresh native 114 views/150 walking
routes/92 navigation queries, both entry/GM fixtures and twelve pocket cameras
pass. Owner thirteen, source/parent packages and capitals remain preserved.
Repository 1141/178, Unreal 520/97, Python 148/38, three typechecks, audit and
world/model validation pass; strict release exits 1. The private 21-picture report
retains unfinished landscape/forest/horizon/stone and every outstanding gate.
Connected route reflow and balanced corridor sampling remain private source
studies, with no native, physical vehicle/combat or human appearance acceptance.


## Connected Sunmeadow route checkpoint (10 October 2026)

Source `cdb9823acbd2`, core `2463ad3179f5`, scene `89ad16819d66`,
nav `259de7f1a48b` and safe walkthrough `f21040e0c9af` integrate connected
Sunmeadow flank/rotation curves. Shared edges are authored once and reused by
supply itineraries; pocket/overlook branches reconnect and pedestrian counters
are regenerated. Main advance geometry, complete keep/staging assemblies,
arrivals and protected western overlooks remain retained. Cinderfen region,
terrain, pockets and links remain byte-exact to the previous source revision.

`balancedCorridors` is an optional shared terrain control: normalize each
corridor before blending overlaps so densely sampled curves do not gain extra
global influence. Legacy absent/false behavior stays unchanged. Focused tests
cover flat-route subdivision, unequal-slope continuity, compact edges and native
float triangle parity. Sloped re-sampling is not mathematically invariant. The
nearest-segment study remains rejected for discontinuities. Full-width route
grades peak at 0.21934734; six Sunmeadow supplies remain 350-750m. Exact clipped
roads retain 0.045m support and soft alpha. Increased mesh cost is unaccepted.

Fresh native 114 phase/weather views, 150 walking routes, 92 navigation queries
before save/reload, both isolated ordinary-entry/local-GM fixtures and twelve
pocket gameplay-camera pictures pass. Thirteen owner documents, source packages,
parent maps and accepted capitals remain preserved. Navigation copies have not
separately repeated every walking route. The in-process Node loader admits twenty
configurations; 4575 samples match exported triangles within 0.031mm, at 0.1mm
tolerance. Live Node and native additive collision are not verified by this proof.

Repository 1153/181 files, Unreal 527/99, Python 148/38, three typechecks, audit
and world/model validation pass. Strict release exits 1 as expected. No C++ changed;
Editor/Game builds and 151 Foundation results remain prior checkpoint evidence.
The private `progress-report-route-reflow-89ad16819d66.html` embeds 21 pictures,
including a corrected topology drawing whose rotation labels locate shared main
route junctions. Its receipt records exact signatures, image hashes and caveats.

Haze-only Cinderfen studies offered little improvement and remain rejected,
unsaved prototypes. Broad smooth hills, undersized sparse canopy, repeated grass,
empty horizons and pale Cinderfen stone remain weak. Larger woodland/shadows,
darker source-derived stone and full-height watershed studies are next. Preserve
human appearance, first-batch full-lair progression, actual vehicle driving/turning/
closed gates, 18v18, services/resources, ordinary GM persistence, earlier unresolved
recovery-repeatability, live Node/additive collision, network/audio, performance,
platform/Steam and release gates. Later native pairs and full underground remain
unbuilt. None of these source or scripted checks establish fun or fair combat.


## T1 absolute surface and woodland proof (10 October 2026)

Private source `8f3fa2d0ecc2`, scene `2ba289f4c44d` and navigation
`3ee658ec9006` integrate bounded absolute terrain sampling, protected retained
population approaches, 190 clustered Sunmeadow oaks, darker Cinderfen
steep-ground stone and a one-stop first-pair night exposure lift. Immutable
source/asset fingerprints and existing owner/capital protections remain active.
The first narrow-blend candidate failed a resource approach on approximately
47-degree terrain; the repair extends grounding protection to six qualified
native population approaches. Walking thresholds remain unchanged.

Editor/Game builds and 151 Foundation tests pass. Fresh native 114 phase/weather
views, 150 walks, 92 navigation queries before save/reload, both isolated
ordinary-entry/local-GM fixtures and twelve pocket follow-camera views pass.
Thirteen owner documents and accepted capitals/source packages/parent maps stay
preserved. Repository 1166/184, Unreal 535/101, Python 153/39, three typechecks,
audit and world/model validation pass; strict release exits 1. In-process Node
triangle parity covers 4575 samples across twenty admitted configurations; it
does not verify the running owner server or native additive tree collision.

This checkpoint is unfinished. Artificial shoulders, uniform grass, distant
billboard trees and empty horizons require further native comparison. Retain
human appearance, first-batch full lairs, physical vehicles/turning/closed gates,
18v18, services/resources, ordinary GM persistence, the earlier unresolved
Cinderfen recovery-repeatability failure, live/additive collision, network/audio,
performance, platforms/Steam and release gates. Later native pairs and full
underground remain unbuilt; navigation copies have not separately repeated all
walking routes. New purchased or source assets have not gained distribution
rights through these checks.


## Terrain-first habitat checkpoint (10 October 2026)

Source `bceed4031308`, core `1b060443009e`, scene `4f514cc02cc3`,
nav `21d93d390a99` and safe walkthrough `ba81710cca60` qualify a terrain-first
Sunmeadow iteration. Routes and foundations now follow the full landform through
`scripts/unreal/t1-grade-network.ts` and `t1-landform-first.ts`. Shared and nearby
route constraints keep the elevation graph coherent. Complete keeps receive one
vertical translation; ninety source keep props use qualified native parent
frames. Eight registered gate/postern props remain unbuilt and physical gate
behavior remains unaccepted.

`t1-pocket-grounding.ts` reconciles retained shallow beds and approaches, checking
closed cosmetic-water rims. `t1-route-reserves.ts` gives exploration links bounded
tangent detours around shelter footprints. Three retained cross-country links
are now explicit dirt paths and scenery reservations. The previous native run
hit Hearthroot's rock pier on the eastern counterroute; the corrected route
passes without relaxing movement criteria. Full-width route grade peaks at
0.21399721; six retained population approaches peak at 0.12348266.

`t1_habitat_palette.py` adds smoothly blended dry soil and broad colour variation
with no extra forest-floor texture lookups. Private Cinderfen rock materials gain
a darker regional adaptation with original geometry/LODs and source packages
preserved. Planting is deterministically thinned within the existing 24000-instance
limit after the first candidate exceeded that limit. Cinderfen source region,
terrain, roads, pockets and links remain byte-exact to the qualified parent.

Fresh native 114 phase/weather views, 150 walking routes, 92 navigation queries
before save/reload, both isolated ordinary-entry/local-GM fixtures and twelve
pocket follow-camera views pass. Thirteen owner documents, accepted capitals,
source packages and parent maps remain preserved. Navigation copies have not
separately repeated all walking routes. Repository 1181/187 files, Unreal 550/104,
Python 158/40, three typechecks, audit and world/model validation pass; strict
release exits 1. No C++ changed: Editor/Game builds and 151 Foundation tests are
prior-checkpoint evidence. In-process Node admits twenty configurations and
4575 samples match exported triangles within 0.031mm at 0.1mm tolerance; the live
owner server is untouched. Ninety source keep frame positions match the qualified
native parent plus assembly translation within floating-point precision.

Appearance remains unfinished: empty horizons, uniform roads, sparse fields and
Cinderfen's rounded barren terrain need further work. Exact installed mountain
studies remain private unsaved prototypes. Preserve human appearance, first-batch
full-lair progression, actual vehicles/turning/closed gates, 18v18, services and
resources, ordinary GM persistence, the earlier unresolved Cinderfen recovery
repeatability failure, live authority/additive collision, network/audio,
performance, platform/Steam and release gates. Full underground and later native
pairs remain unbuilt. Scripted checks do not establish enjoyable or fair combat.


## Sunmeadow distant scenery and sampling bounds (10 October 2026)

Source `03ec8464c80c`, core `53ef11ad5ac8`, scene `1d2ce3f276bb`,
nav `dc228f84565b` and safe walkthrough `5e56e6d5d1c1`.
Four exact privately installed eroded mountains and a connecting cosmetic terrain
skirt now frame Sunmeadow's valley. Native component verification confirms all
five components stay inside its ownership envelope, with collision, navigation
influence, overlap events, shadows and distance-field lighting disabled. Original
source packages and licensed derivatives remain private. This adds distant scenery,
not playable acreage; appearance, licensing/distribution and performance are open.

`ZoneSpatial.terrainBounds` separates the retained triangle sampling rectangle
from content ownership. Shared/Node height sampling, native terrain import, road
fitting, portal export and atlas projection use that extent. Absent metadata
preserves legacy behavior. Sunmeadow alone moves to a separated world origin;
accepted capital and other region origins remain retained. Forty source content
files remain byte-identical; the two Sunmeadow definitions differ only in spatial
metadata. Terrain, roads and military placements remain retained.

The skirt contains 13552 vertices and 24008 triangles. All 1500 playable boundary
vertices match terrain heights exactly; every skirt triangle remains outside the
sampling rectangle. The first scene build failed on a commandlet subsystem and
was repaired using the established fallback. Navigation then rejected the large
scenery envelope. `NavigationBounds` now validates the playable outline inside
ownership and derives its bounded envelope before exterior exclusions and tile
budgeting. The original footprint and tile limits remain unchanged. Regression
checks cover distant ownership, legacy rectangles, escapes and oversized play.

Editor/Game builds and all 152 Foundation tests pass. Only the Editor navigation
DLL changed after scene rendering and walking; the gameplay DLL remains
byte-identical. Fresh native evidence covers 114 phase/weather views, 150 walking
routes, 92 navigation queries before save/reload, two isolated entry/local-GM
fixtures and twelve pocket follow-camera views. Navigation copies have not
separately repeated all walking routes. Thirteen owner documents, accepted
capitals, parent maps and installed source packages remain preserved. Repository
1188/189 files, Unreal tooling 557/106, Python 162/41, three typechecks, audit and
world/model validation pass; strict release exits 1. In-process Node admits twenty
configurations; 4575 ground samples match within 0.031mm at 0.1mm tolerance. The
live owner server remains untouched.

Appearance remains unfinished: broad pale roads, sparse fields, unnatural local
shoulders and Cinderfen landforms need further work. Worn-earth/gravel comparisons
are next. Keep human appearance, first-batch full-lair progression, full underground
and later native pairs, actual vehicles/turning/closed gates, 18v18, services and
resources, ordinary GM persistence, earlier unresolved Cinderfen recovery
repeatability, live streaming ownership, live/additive collision, network/audio,
performance, platform/Steam and release gates open. Scripted checks do not establish
enjoyable or fair combat.


## Sunmeadow earth/gravel roads (10 October 2026)

Source `03ec8464c80c`, core `53ef11ad5ac8`, scene `b06f83f1f499`,
nav `cd5646e29d3d` and safe walkthrough `fc6ecc8bd2f3`.
`t1_road_earth.py` supplies a bounded, separately tested recipe for smooth
settlement-to-earth transitions, broad stochastic variation and matching colour
and normal weights. Its native adapter fingerprints exact installed bare-earth
channels and adapts a fresh private Sunmeadow material. Original soft verges,
roughness, road geometry and collision remain retained. Cinderfen road materials
remain unchanged. Twelve stochastic colour/normal lookups are additional to the
retained opacity/roughness graph; rendered material cost remains unaccepted.

Fresh native 114 phase/weather views, 150 walks, 92 navigation save/reload queries,
two isolated entry/GM fixtures and twelve pocket follow-camera views pass. Owner
documents, accepted capitals, parent maps and source packages remain preserved.
Navigation copies have not separately repeated every walk. No C++ changed:
Editor/Game builds and 152 Foundation tests are prior-checkpoint evidence.
Repository 1188/189, Unreal tooling 557/106, Python 166/42, three typechecks, audit
and world/model validation pass; strict release exits 1. The live Node is untouched.
The private progress report embeds 22 actual screenshots and labeled drawings.

A duplicated shader helper in the first unsaved study was repaired; darker
leaf-litter roads and sparse crop-clump prototypes were rejected and remain
unintegrated. Appearance is unfinished: smooth banks, empty fields and Cinderfen
landforms need work. Source diagnosis measures excavation up to 26.27m in
Sunmeadow and 25.94m in Cinderfen; alternative cut/fill grading remains private
study work. Preserve human appearance, first-batch full-lair progression, full
underground/later native pairs, actual driving/turning/closed gates, 18v18,
services/resources, ordinary GM persistence, earlier unresolved Cinderfen recovery
repeatability, live streaming/authority/additive collision, network/audio,
licensing/distribution, performance, platform/Steam and release gates.


## Opt-in balanced terrain grading studies (10 October 2026)

`t1-balanced-grade.ts` computes the midpoint of feasible lower/upper network
height envelopes. It preserves the existing centreline grade, shared junctions,
flat footings, metadata and bounded inventories while allowing cut and fill.
Source fields are sampled once per graph node. The original cut-only grader and
all admitted terrain sources remain unchanged. The correction metrics describe
graph nodes; full terrain, route width and native movement require separate checks.

Five behavior tests cover a known valley, feasible ground and height limits,
shared footings/input preservation, deterministic translation/slope invariants
and rejected malformed inputs. Repository 1193/190, Unreal tooling 562/107,
Python 166/42, three typechecks, audit and world/model validation pass; strict
release exits 1. No C++ or saved native candidates changed in this authoring pass.

Private unsaved comparisons retain exact source fingerprints, complete keep
translations, individual foliage rebasing and conformed cosmetic roads. Both
studies pass 289 native terrain collision-height probes and retain exact distant
skirt boundary heights. The first provides twelve native views; a later natural
fold/drainage study provides fourteen. Owner documents, accepted capitals and
parent maps remain preserved. Narrower smoothing variants with steep pool or
counterroute grades were rejected. Coherent pool grading repairs source grades,
but the captures still look smooth and empty. These terrain studies remain
unintegrated and do not supersede scene `b06f83f1f499` or grant appearance,
walking, driving, authority, hydrology, performance or release acceptance.
All first-batch full-lair, underground/later-pair, combat, persistence/network,
licensing/platform/Steam and other outstanding gates remain open.


## Natural meadow and local relief studies (10 October 2026)

`scripts/unreal/t1_meadow_patches.py` is an opt-in cosmetic authoring system.
Continuous radial masks use smooth noise to form irregular meadow edges and
worn verges. Deterministic placements respect playable outlines, retained route
widths, foundations, services and terrain grades. Explicit narrower visual
tracks can receive cosmetic verge planting without changing authoritative
vehicle ground widths. Sampling and instance inventories are bounded; overlapping
patch order does not change the output. Four behavior tests cover these contracts.
This generator is not connected to saved candidate generation yet.

The isolated native comparison contains six player-height views. Its irregular
patch uses 7246 installed source grass instances, versus 13843 in the denser
rectangular study. Collision remains disabled; original geometry, materials,
parent maps, accepted capitals and owner documents remain preserved. This does
not approve rendering cost, combat cover, complete regional dressing or ordinary
persistence. Actual native pictures are embedded in the private progress report.

Strong isolated peak prototypes were rejected for artificial silhouettes. Lower
elongated spurs and asymmetric scarps retain explicit graded walking counters;
the latter passes source full-width grades at 0.17942 against the unchanged 0.22
limit. Native unsaved comparisons pass 289 simple/complex terrain height probes
and retain exact distant-skirt seams, with eighteen pictures per comparison.
Installed rock colour/normal projections and narrower visual tracks remain
private experiments. These studies do not supersede source `03ec8464c80c` or saved
scene `b06f83f1f499`. Complete anchor/source relocation, native walking/driving,
authority integration and appearance acceptance remain outstanding. The terrain
still needs more convincing local detail and content.

Keep all first-batch full-lair, underground/later native pair, human appearance,
actual vehicles/turning/closed gates, 18v18, services/resources, ordinary GM
persistence, unresolved earlier Cinderfen recovery repeatability, live streaming
and additive collision, network/audio, licensing/distribution, performance,
three-platform/Steam and release gates open. No C++ changed in this pass.

The opt-in `t1_meadow_native.py` adapter now verifies the exact staged mesh,
material, bounds and LOD inventory before spawning anything. It rejects occupied
actor identities and per-species inventories above the native 12000-instance
limit, rolls back new actors on configuration failure, and verifies NoCollision
and 80-180m culling. Four adapter tests cover units, rollback, owner preservation
and native limits. A fresh six-view native run reproduces 7246 instances (5836
short grass, 1410 long grass), verifies both bindings and preserves saved maps,
accepted capitals and owner documents. This remains an unsaved prototype and is
not wired into saved candidate generation or approved for performance/persistence.

Verification for the meadow authoring/adapter pass: all 1193 repository tests in
190 files, 562 Unreal tooling tests in 107 files and 174 T1 Python tests in 44
files pass. All three typechecks, migration audit, world and model validation
pass. The initial concurrent suites timed out in the same five-second ordinary
GM persistence test; isolated reruns of that file and each full suite pass with
the original time limits unchanged. Strict release still fails as required by
outstanding native/platform/Steam gates. No C++ changed; no fresh native module
build or C++ automation result is claimed for this pass.

The meadow adapter also rejects unrelated loaded worlds before reading assets or spawning actors, even when a caller supplies a fresh output folder. The guarded native rerun verifies the isolated Sunmeadow map binding; 174 Python tests in 44 files pass.


## Explicit landform anchor revisions (10 October 2026)

`t1-terrain-anchor-revision.ts` provides a separate, opt-in revision operation for
already authored absolute first-pair terrain. It clones the original source,
retains sampling bounds/grid and verifies all boundary vertices against the
retained distant seam. Foundations and existing ground-corridor identities must
remain present. Keeps and their fitted absolute props move rigidly; qualified
native frames can retain exact prop datums. Staging camps, objective aliases,
spawn/trigger/arrival heights, absolute scenery and absolute population follow
the revised ground, while relative offsets and gameplay rules remain retained.
Ground-relative population/services still require fresh native alignment proof.
The reciprocal-arrival helper refreshes incoming landings from a unique connected,
terrain-supported reciprocal without changing the campaign graph.

All 1197 repository tests in 191 files and 566 Unreal tooling tests in 108 files
pass, including four focused anchor-revision tests. All three typechecks, migration
audit, world and model validation pass. The unchanged Python modules retain their
174-test/44-file verified checkpoint. Strict release still fails for outstanding
native/platform/Steam gates. No C++ changed in this pass.

An isolated private connected-spur source study
aligns 90 qualified keep-prop frames and all 32 maps/70 directed portals, updating
three incoming Sunmeadow landing records. It preserves exported terrain triangles
byte for byte, retains zero boundary error and passes full-width source grades
at 0.17895. Cinderfen source remains unchanged. No global source receipt or saved
candidate is replaced; native population/complete-assembly, walking/driving,
18v18, appearance, persistence/network, first-batch lairs, performance/platform,
Steam and release acceptance remain outstanding.


## Connected-spur native prototype and resting worksite props (10 October 2026)

The opt-in terrain revision now has a separate private first-pair candidate: source
`15c2b7d20a52`, core `4d46cc30d985`, scene `7c35d60eb8ab`. Its full 32-map/70-arrow
source bundle updates reciprocal Sunmeadow landings and retains Cinderfen source
byte for byte. Global source `03ec8464c80c`, saved scene `b06f83f1f499` and accepted
capital/owner content remain unchanged. This candidate is not visually accepted.

The saved prototype passes 150 configured normal-character routes over 49604.08m
with zero airborne travel, jumps or in-route teleports. Native full-width checks
cover 86360 samples, with maximum grades 0.17895 in Sunmeadow and 0.21648 in
Cinderfen; all eight arrivals pass. The rendered review contains 114 regional
dawn/day/dusk/night/strong-weather views and passes material compilation checks.
A separate reload verifies all 8798 meadow transforms, source/material bindings,
nonblocking policy and 80-180m culling. Base vegetation retains its separate
35-120m policy. The private review adapter checks both without loosening either.

The authored counter-route planner no longer selects fixed waypoint indices from
a resampled flank. It projects onto the nearest flank segment, then uses bounded
ground connectors with a 0.22 grade cap and native clearance checks before the
retained climb. A sampling-density regression test protects that behavior.

`t1_rest_scene.py` provides bounded static resting-scene adaptation for reviewed
unskinned prop hierarchies. It composes parent translations/rotations/uniform
scales, preserves geometry/material buffers and rejects skinning, morph geometry,
matrices, nonuniform scales, cycles/shared ownership and excessive depth. Six
focused tests include noncommuting rotations. The private approved-source wagon
study compares all 63892 vertices against independent hierarchy matrices with
zero world-position error. Native committed triangle corners, normals, UVs,
colours and six material sections match; position rounding is below 0.000016cm.
The wagon remains unsaved scenery, not a physical convoy/vehicle acceptance.

All 181 T1 Python tests in 45 files, 1197 repository tests and 566 Unreal
tooling tests pass, alongside all three typechecks, migration audit, world
and model validation. The strict release check still exits 1 as required.
Navigation candidate `026e779fc971` passes 92 configured route probes before
saving and the same 92 after reloading, across pedestrian and siege-convoy
agents. Baked tile payloads remain exact. This is not physical driving proof. No C++ changed. Actual native pictures and a labeled
source topology drawing are embedded in the private progress report. The images
still show sparse/uniform terrain and a bare village; further dressing is needed.

Retain all human appearance, full first-pair lair/underground and later native
batch gates, actual driving/turning/closed gates, 18v18, services, ordinary GM
persistence and unresolved Cinderfen recovery repeatability, live authority/
streaming/additive collision/network/audio, licensing/distribution, performance,
three-platform/Steam and release gates. Scripted movement does not establish fun
or multiplayer fairness.


## Small ground folds and village worksite studies (10 October 2026)

`t1_ground_detail.py` adds opt-in, bounded source-derived folds to an absolute
terrain raster. One to four independently oriented reflected sampling layers
share a four-metre amplitude budget. Wavelengths respect source grid resolution;
source data is immutable and zero-strength derivatives retain serialized values.
An explicit rendered sampling rectangle can sit inside the larger source raster.
Its boundary interpolation support receives an explicit protected band. Five
focused tests cover rectangular seams, nonaligned sampling boundaries, layer
orientation, continuous reflected edges, aliasing and invalid/bounded inputs.

The first private small-fold study failed its native seam guard because it had
preserved the larger source raster boundary instead of the rendered terrain join.
The failed evidence and tool snapshot remain private. The repaired source study
`80e841f6fdda` preserves all 1500 sampled boundary vertices with zero error and
passes full-width route grades at 0.17687. Its separate unsaved native comparison
checks 289 simple/complex terrain probes and records twelve before/after views,
then restores the saved scene's actor and foliage bindings. This is not a saved
candidate, full walking proof, live Node geometry revision or visual acceptance.
The source fold addition reaches 2.795m; its visual effect is still subtle and the
large terrain forms still need stronger composition and material/outcrop work.

Separate unsaved village studies add seven soft-edged footways, two irregular
worn-earth yards, an approved-source parked wagon, three barrels and two crates.
Native overlay triangle corners and vertex fades match their source; all 937
configured village capsule samples clear. A measured-bound planting view adds
13228 nonblocking grass instances without changing authoritative reservations or
terrain. The broad village foundation remains overly flat. Three trial kit
exteriors retain all five actual rendered LODs and source materials; committed
mesh descriptions are unavailable for that installed asset, so the check uses
actual rendered faces. Interior, regional architecture, collision performance,
license/distribution and visual acceptance remain open. Original actors and
installed packages are restored/preserved; the studies do not replace twenty
buildings or constitute a finished settlement.

Navigation candidate `026e779fc971` is wrapped by isolated safe review `7bcf41abe25a`.
Both ordinary local entry/GM recovery proofs pass, and six configured exploration
pocket walks produce twelve normal-gameplay-camera captures. Global launch and
source receipts remain unchanged. Prior Cinderfen recovery repeatability is not
closed by these additional passes. The private 26-picture report embeds actual
native images and two labeled source drawings; a separate compact transport copy
verifies identical decoded pixels and retains original capture files.

All 186 T1 Python tests in 46 files, 1197 repository tests and 566 Unreal
tooling tests pass, alongside all three typechecks, migration audit and world/model
validation. The strict release check still exits 1 as required. A final formatting
cleanup preserves the exact Python AST and reruns all five focused fold tests;
regenerated private source folds remain byte-identical. No C++ changed. Preserve
all full first-pair lair and
later native batch, human appearance, driving/turning/closed-gate/siege, 18v18,
services/resources, ordinary persistence/live authority/streaming/network/audio,
license/distribution, performance/platform/Steam and release gates. Technical
probes and before/after pictures do not establish multiplayer fun or fairness.


## Western farmstead prototype (10 October 2026)

Private recipe `5ebf940bdf96` adds a connected Sunmeadow farm-country section
to a separate copy of scene `7c35d60eb8ab`: a kit farmhouse, approved-source
parked wagon, six worksite props, low stone boundaries, six oaks, a feathered
yard and two contour-following paths. Existing terrain, campaign source,
objectives, main routes, accepted capitals and owner content remain unchanged.
This is a saved prototype, not a finished zone or active campaign launch.

The initial straight approaches failed the full-width grade cap at 0.569.
Following existing contours reduces the maximum to 0.114 without editing ground.
Native sweeps caught a boundary wall clipping the orchard path; the repaired gap
passes 804 configured three-lane capsule samples across the new paths. Nearby
retained main-route sweeps pass too. No population fixture lies within the site's
130m review radius, so this does not add service/resource acceptance.

Player-height images exposed an oak in flooded ground. Conservative basin
envelopes now screen new roots and path lanes; the tree, working props and
wagon were moved onto dry ground. Full foundation/wheel contact remains open.
Fresh private collision clones preserve source materials and actual rendered
LODs. A saved/reloaded copy verifies static bindings, 4987 new nonblocking grass
transforms and 268 centreline capsule samples. An initial reload verifier
misclassified the new grass as base foliage; the repaired adapter checks the
inventories independently without relaxing either strict culling policy. Raw
failed studies and logs remain private.

Four configured normal-character walks cover both directions of both paths over
243.348m with zero airborne travel, jumps or in-route teleports. Six native
player-height views, eight actual gameplay-camera captures and one labeled source
drawing are embedded in the private farmstead report. Standalone lossless PNG
copies verify identical decoded pixels. The pictures still show smooth/sparse
terrain, repeated surfaces and unaccepted architecture. These checks do not
certify the intended look, entertaining battles, interiors or ordinary entry/GM.

Additional navigation and authoritative scenery registration remain unaccepted.
Retain full contact/interiors, first-pair lairs/underground, later native zones,
visual approval, real vehicle/turning/gate/siege and 18v18 play, services, ordinary
GM persistence/recovery, live authority/streaming/network/audio, licensing,
performance/platform/Steam and release gates. Next: qualify worksite contact and
navigation, then improve the enclosing geology and field/grove composition using
this saved section for consistent comparisons.

Required repository checks pass: 1197 tests in 191 files, 566 Unreal tooling
tests in 108 files, all three typechecks, migration audit and world/model
validation. Strict release correctly exits 1. No C++ changed; prior 186 Python
tests remain retained evidence, not a rerun in this checkpoint. An additional
source-only four-wheel bottom/pivot diagnostic finds up to 24.69cm of vertical
contact error on the parked wagon. Its pose needs correction and actual native
contact checks before that detail can be accepted.
