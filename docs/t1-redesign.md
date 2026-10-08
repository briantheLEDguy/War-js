# T1 terrain, story and RvR redesign

The implementation branch is `codex/t1-terrain-story-rvr`. Published and local
baselines were reconciled at `c9634131`; the owner saved and closed Unreal before
the build. Accepted capital scenes and active campaign maps are preserved.
The new environments are private review candidates. No zone or batch is complete.

## Regional topology

Use original Aegis/Riftbound military fantasy, substantial regional architecture
and large landscape silhouettes. Progress from civilian village through working
outskirts and military frontage into contested territory. Reserve 20 buildings,
two furnished accessible homes, services near arrival and an attached military
courtyard. Building marks in the drawings reserve capacity; they are not houses.

| Region | Playable target | Landscape and routes |
| --- | --- | --- |
| [Sunmeadow March](t1-topology/sunmeadow_march.svg) | 1,500 × 1,100 m | Cultivated valley, wooded barrow ridges, Empire limestone/oak village, requisitioned harvests and ancient oak. Valley advance, ridge flank and outer farm road. |
| [Brightfen Approach](t1-topology/brightfen_approach.svg) | 1,700 × 850 m | Winding limestone island chain, High Elf village, pale causeway, reflective pools, willows and reeds. Causeway advance and two island alternatives. |
| [Cinderfen Outskirts](t1-topology/cinderfen_outskirts.svg) | 1,250 × 1,100 m | Crescent geothermal basin, Greenskin timber/basalt, Dark Elf supply compound, mineral chimneys, amber water and pale steam. Curved advance, basalt ridge and peat dyke. |
| [Ashen Steppe](t1-topology/ashen_steppe.svg) | 1,900 × 850 m | Bending dry wash, sandstone plateaus, Chaos stone halls, caravan compounds, standing monuments, bleached grass and silver ash. Wash advance, plateau flank and side gully. |

`scripts/unreal/t1-layouts.ts` authors separate landforms and graded routes,
staggered objectives, two rotation links, staging and optional lair approaches.
Principal routes and rotation links reserve 12 m roads and 9 m centreline
clearance. Six supply itineraries per zone follow their physical graph within
350–750 m. Existing gameplay IDs, counts, capture availability, campaign edges,
quest chains and rewards remain intact. Keep assemblies move together, including
gates, commanders, siege anchors and posterns. Local model collision offsets
remain local; absolute scenery elevations are rebased onto terrain. Measured
scenery envelopes reserve road clearance. This is not live driving acceptance.

## Modular authoring

`scripts/unreal/t1-modules.ts` reserves twenty separate village assemblies:
six homes/housing buildings, shops, crafting workshops, inn/bakery, storage,
stables and a garrison. Military buildings face the connected outgoing frontage;
civilian housing occupies the rear lanes. Four regional arrangements share
oriented footprint, courtyard and service clearance checks. A local circulation
graph connects every planned entrance around the other reserved shells. Two
homes retain explicit interior requirements and no interior acceptance.

These door positions are design sockets. The existing source houses have no
verified accessible openings/interiors, so the sockets and drawn paths do not
prove that a player can enter them. Shops/garrison roles are authoring targets;
native services and occupants have not been rebound to these new shells.

`scripts/unreal/t1-scene-modules.ts` builds small, separately editable first-pair
assemblies: harvested fields/army stores, advance hedgerows, barrow groves,
basalt shelves, peat reeds and mineral rock. Their conservative measured
envelopes preserve roads, objective spaces, camps, keeps and village reservations.
The strict source importer checks actual scaled geometry against each envelope.
Unadmitted assets and placements with no clear space remain explicit pending
entries. Later-batch scenery stays outside native generation.

Module, scene, prototype, terrain, candidate-map and authoring-tool hashes bind
the private build recipe. Component IDs remain stable across regeneration;
each completed revision gets a fresh private collection. The native prototypes
are rendering studies: module collision/gameplay registration, navigation and
ordinary GM assembly persistence still need integration and execution.

## Native clearance and furnished-home studies

`review-t1-clearance.py` binds its input inventory to the saved candidate receipt
and performs forward/reverse native sweeps against actual admitted scenery.
Roads, six supply itineraries, village approaches, services and arrivals are
included. Wide roads receive three character lanes and a 6 × 9 × 3.3 m diagnostic
corridor; six-metre keep approaches retain a 5.4 m corridor with edge clearance.
These upright boxes exclude terrain, whose full-width support is checked
separately. They do not simulate vehicle steering, suspension, navigation or
gate ownership states. Unplaced gate/banner bindings remain explicit.

The initial survey found roads intersecting keep walls/shelters and three
Cinderfen walking links hitting lanterns. Ridge approaches now branch at shared
advance vertices, staging roads skirt complete retained assemblies, and the
eastern advance approaches delivery from below the quartermaster shelter.
Standing fixtures reserve clearance in the village circulation flood. All
four data layouts retain the supply pacing and terrain grade checks; the repaired
first-pair native candidates pass 77,389 obstacle sweeps with no blockers.

`build-t1-home-studies.py` clones each isolated first-pair candidate into fresh
Review/Generated/Authored packages and substitutes its two required home lots
with existing furnished private catalog templates. It checks the full project
dependency closure, original template fingerprints and parent map hashes.
Original kit assets, parent candidates and capital maps are untouched. Native
axis/pivot conversion, single-floor door routes and a twelve-metre study height
are explicit in `t1_native_homes.py`. These are kit interior studies, with regional
architecture and licensed distribution acceptance still open.

`review-t1-homes.py` checks actual floor support and the unchanged 42 cm radius /
96 cm half-height character capsule in both directions. Rounded-foot sweeps
handle porch edges; bounded up/across/down sweeps use the existing 45 cm step
limit. The four routes pass this geometric review. It does not execute character
movement, verify camera collision or certify home accessibility in gameplay.
The source templates include furniture, windows and door openings; capture and
collision receipts alone do not grant visual or furnished-home acceptance.

`AWarPracticalLight` supports a daytime indoor level while its outdoor default
still extinguishes in daylight. `AWarInteriorAtmosphere` supplies a bounded
room exposure component with a 75 cm blend, using the same authority clock.
It inherits regional camera/colour settings and leaves exterior exposure alone.
Private home studies have one interior light/room component per house. Their
lighting, source materials and cultural adaptation remain prototypes.

## Spatial and atmosphere implementation

`shared/worldSpatial.ts` resolves rectangular content bounds, an irregular
playable outline and independent grid dimensions. Validation rejects crossing
outlines, invalid grids and nonfinite data. Segment checks reject concave
shortcuts even when both endpoints are playable. Explicit grids use the same
Float32 triangles as native export; untouched zones retain square footprints and
legacy bilinear authority grounding.

Node map loading, authoritative movement and vehicle exits consume this contract.
Native anchors distinguish content ownership from playable ground, portal
landings require capsule clearance, and player movement rejects exits into
backdrop scenery. The atlas frames rectangular bounds and draws the outline.
T1 origins move to separated ownership envelopes; other origins remain stable.
Reciprocal arrivals are explicitly authored on connected ground. Terrain
inventory checks reject coverage gaps/overlap instead of requiring 16 sectors.
The candidates have 12 planned tiles each; native prototypes use a continuous
heightfield and road overlay. Final tile admission, seams/LODs and streaming
execution remain open.

`AWarEnvironmentState` replicates a UTC anchor tied to synchronized server world
time. The 3,600-second cycle contains dawn 300, day 1,800, dusk 300 and night
1,200 seconds. Regional weather changes every ten minutes, blends over 45 seconds
and eases stronger spells after three minutes. Clients receive the anchor and
transition state; they have no weather setter or local selection RNG.
`UWarZoneLightingSubsystem` reuses six local transient actors for T1 sun/moonlight,
fill and regional fog. Dedicated servers create no cosmetic lights. Non-T1
profiles remain static and Bastion's authored lighting restores exactly. Ashen's
base palette now uses silver ash and bleached sandstone.

Lighting/fog transitions are implemented. Rain/ash particles, steam emitters,
wind and activity-led audio remain unfinished. `AWarPracticalLight` provides
clock-driven, local illumination for admitted lantern fixtures; the first pair
has twenty fixtures per village. Shadows are disabled on these small lights.
The controlled native exposure study records actual directional/fixture
intensities and day/night alternatives. Final night readability and fixture
placement remain unapproved.
Multi-client clock/weather convergence and night readability require live proof.

## Reproduction and preservation

1. Close saved editor/game processes and build the Editor module.
2. Run `npm run unreal:t1-plan`. It clones all 32 maps into ignored
   `artifacts/unreal/t1-redesign/maps`, updates candidate reciprocal arrivals,
   exports four topology SVGs and terrain/roads, and binds original source/private
   package hashes. Active maps are not overwritten. Tracked SVGs are reproducible.
3. Run `python scripts/unreal/prepare-t1-prototypes.py` to verify exact admitted
   source model hashes and export original geometry/material sections. Unsupported
   or unadmitted models remain pending entries.
4. Run `build-t1-prototypes.py` through Unreal's Python commandlet. It creates
   isolated Sunmeadow/Cinderfen review maps with Generated/Authored layers in fresh
   private `WorldRebuild/T1Redesign_…` packages. Completed reruns verify hashes;
   owner edits cause reconciliation errors. Partial attempts remain recoverable.
5. Run `review-t1-prototypes.py` with commandlet rendering enabled for player-height
   dawn/day/dusk/night/weather views of the advance, village, ridge and regional
   scene assemblies, plus ground samples across both road shoulders and
   centreline. Capture frames advance native sky/shadow caches and warm up the
   view. Saved candidate hashes must remain unchanged. Ground sampling is not a
   walk, drive or performance playtest. `study-t1-exposure.py` captures controlled
   lighting alternatives without saving the maps.
6. Run `t1-progress-pictures.py` with a Pillow-equipped Python for four topology
   and four detailed village PNGs. Native views are retained under
   `artifacts/unreal/t1-redesign/views/<plan hash>/`; drawings are schematic.
   Run `python scripts/unreal/t1-progress-gallery.py` after the matching native
   review to build the local `artifacts/unreal/t1-redesign/progress-gallery.html`.

The current first-pair import admits 28 source models / 428 placements with 16 pending
placements: animated gates/posterns and Cinderfen banner bindings. Saved native
maps contain terrain, roads, retained keep architecture, twenty village shells
and twenty lanterns per zone, plus regional scenery/landmark prototypes. They
are not complete villages or accepted keeps. Terrain materials remain basic
regional tints; water, texture detail and broad landscape composition need work. No
primitive scenery fallback, purchase or distribution approval is added.

Route grading now blends overlapping supports continuously. Native collision
sampling covers 8,712 Sunmeadow and 8,631 Cinderfen points, including both road
shoulders, with maximum measured rise/run about .180 and .151. The review fails
above the .22 authoring target. This does not prove vehicle handling or fairness.
All four twelve-tile rectangular inventories pass coverage validation, including
fractional thirds; real coverage gaps/overlap still fail.

## Outstanding acceptance

Sunmeadow/Cinderfen remain batch one. Warden's Hollow and Cindermaw retain their
full lair gates; this brief authors only approaches. Brightfen/Ashen topology
is reviewable, while second-pair native buildout remains gated.

Review terrain, architecture and landmark composition from the gameplay camera
before broad dressing/adoption. Finish the 20-building villages and two furnished
homes, services/garrison/story dressing, cultural forts, water/vegetation/materials
and local atmosphere. Walk and drive crossings, rotations, siege/delivery paths,
doors and camera clearances. Check retained encounters, professions/resources,
services, portals and lair approaches. Play both realms at 18v18 and adjust
reinforcement time, exposure, cover, overlooks and interception against play.

Native rectangular/concave streaming and reciprocal travel, network clock/weather,
regeneration and ordinary GM persistence still need candidate execution. Measure
frame time, memory and travel on Windows/Linux/macOS and complete Steam/release
gates. Tests, exported data, compilation and isolated captures grant no art or
completion acceptance.

Verification: all three typechecks, 1,081 repository tests, 473 Unreal tooling
tests, eight Python coverage/adapter tests and 144 native Foundation tests pass.
Migration audit, 33-map world validation and 906 model records pass. Strict
release checking retains four outstanding gates. Focused T1 tests also pass
after scenery placement and absolute-height corrections.

The initial 2026-10-08 checkpoint was native plan `f597f9bbeb96`: 50 player-height
captures, eight progress drawings, unchanged saved candidate packages, and native
Foundation report `artifacts/unreal/editor/test-1791410986308-33672`. The local
gallery links full-resolution originals; it applies no image enhancement.

The subsequent route-clearance checkpoint is plan `1a4677079d8c`. It retains
50 player-height views and unchanged saved maps, with measured road grades
about .180/.151 for Sunmeadow/Cinderfen. Repository/tool suites now pass
1,081/473 tests, including fixture-circulation regression coverage. Four new
Python adapter/inventory tests pass alongside the four terrain coverage tests.
The home-study receipt and `home-review.json` bind the latest private room maps,
24 actual day/dusk/night captures and four schematic room drawings. Earlier
failed clearance/home receipts are retained privately for diagnosis.

The latest home study is `c3546858f94b`: 4,218 native capsule/foot/step sweeps,
1,372 floor samples, four clear routes, 24 rendered views and unchanged parent/
study maps. Indoor fixtures measure 2,500/2,225/1,400 lumens at day/dusk/night;
bounded exposure uses day bias 2 and night 3.5. Source materials, regional
architecture and roof/window composition remain unapproved. The latest native
Foundation report is `artifacts/unreal/editor/test-1791413941815-24868` (144 pass).
The local gallery now contains 74 native captures and 12 schematic drawings.

Run `review-t1-clearance.py` as a null-RHI Python commandlet after a matching
candidate build. Run `build-t1-home-studies.py`, then `review-t1-homes.py` with
`-AllowCommandletRendering -RenderOffscreen -NoTextureStreaming`. Regenerate
room drawings with `t1-home-pictures.py` using Pillow, and the existing progress
drawings/gallery helpers for the complete checkpoint. Neither helper saves a
reviewed map or changes source kit assets. Close saved editor/game processes
before native module builds or private candidate writes, as required by the
world buildout workflow.

Overnight continuation is active on this chat through 08:00 Amsterdam on
2026-10-08. It continues independent modular implementation and shares meaningful
native/drawing progress. Next work includes verified house openings/interiors,
candidate gameplay/collision registration, regional terrain materials,
weather/audio and live native traversal/persistence/network proof. The owner's
request to continue does not certify appearance or advance the unfinished lair
and release gates.

## Native walking checkpoint — 2026-10-08

`WarT1TraversalGameMode` and `WarT1TraversalProof` provide an opt-in, non-Shipping
local fixture. Both development networking and traversal flags are required.
Configuration selects only a bounded Saved/T1Traversal run and the exact private
Sunmeadow/Cinderfen home Review map. Other zones, owner layers, capitals and
remote admission are excluded. It assigns the existing Sunfire Templar/Warbrute
visual definitions and spawns a normal visible, animated `WarCharacter`; no
frontend, campaign recovery or GM publication is invoked.

The fixture uses native CharacterMovement and repeated movement input. Only
independent route starts are repositioned; subsequent waypoints are walked.
Capsule radius/half-height 42/96 cm, step height 45 cm and maximum movement
speed 600 cm/s remain unchanged. Home input is reduced to normal walking.
Floor traces resolve saved terrain and interior floors separately; feet must
reach each waypoint on walkable ground. Stalls, unsupported movement, outline
departure, flight, missing character models or altered movement geometry fail.

The first complete two-zone receipt passes 80 routes (40 each): both directions
of every configured road and all six physical supply itineraries per region,
plus two village-to-furnished-home/interior/return walks per region. Native
distance totals 18,173.55 m Sunmeadow and 18,820.87 m Cinderfen. Both record zero
airborne time during travel. These runs use a fixed 1/60 simulation timestep
with null RHI; their wall time is neither frame-time nor platform performance
evidence. They exercise static saved collision, while animated gates/banner
bindings and candidate gameplay registration remain incomplete.

The separate rendered home pass completes all four routes in real time:
312.89 m Sunmeadow and 334.07 m Cinderfen, with 12 native screenshots of reached
doorway/interior/return waypoints. The normal local follow camera, indoor mode
and spring-arm collision remain active. Actual renderer output was 888 × 500,
selected by normal graphics settings despite requested window dimensions.
Sunmeadow stone walls remain too dark, source roof/wall gaps remain visible,
and both kit studies still need regional architecture/material review. These
images are unmodified prototypes and grant no camera or appearance approval.

Run `python scripts/unreal/run-t1-traversal.py --headless` after a native build
for all configured routes, or omit `--headless` for rendered real-time home
walks. An optional `--zone` selects one admitted first-pair region. The helper
verifies candidate/source receipt hashes, original WorldRebuild packages,
parent/home maps, frozen kit dependencies, existing Saved/WorldEdit documents
and its implementation/DLL binding. It retains each unique run under
`artifacts/unreal/t1-redesign/traversal/`, then updates the appropriate
`traversal-headless-latest.json` or `traversal-camera-latest.json` only after
all requested routes pass. Failure still checks owner/package preservation.

Use `t1-traversal-pictures.py` with Pillow for two labeled coverage drawings.
They show configured polylines reached, rather than reconstructed footstep
tracks. `t1-progress-gallery.py` adds these and the 12 live screenshots to the
earlier room/terrain views: 86 actual native captures and 14 schematic drawings.
Driving, complete camera clearance, live campaign/services, ordinary GM
persistence, network travel/clock, 18v18, lairs, platform, Steam and release
acceptance remain open.

The final traversal receipts bind the compiled module and implementation hashes,
with 9,361 saved packages and all 13 existing owner GM documents unchanged.
Headless run: `traversal/1791417059002101500-33244`; rendered run:
`traversal/1791417264527414300-9568`. All three typechecks, 1,081 repository
tests, 473 Unreal tooling tests and ten focused Python terrain/adapter/traversal
tests pass. The rebuilt Foundation suite passes 145 tests at
`artifacts/unreal/editor/test-1791416889279-11120`. Migration audit, 33-map world
validation and 906 model records pass; strict release checking still fails with
the four retained release gates. No candidate or zone is accepted for release.

## Regional native material studies — 2026-10-08

`t1_materials.py` resolves the meadow/peat substrate and regional road channels
from exact reviewed repository GLBs. It verifies the binary, external texture,
render-receipt and approval hashes before importing colour and analytical
microrelief normals. Source review permits reuse; it does not approve their new
T1 composition. Both substrates and roads repeat at two physical metres using
world-space source X/-Z axes, independent of rectangular sampling UVs. Broad
53/91 m shade variation and a slope-normal rock tint frame the substrate;
roads retain vertex-alpha verges. No displacement or collision changes occur.

`build-t1-material-studies.py` creates a fresh private
`T1Redesign_Materials_<signature>_<time>` collection with Review, Generated and
reserved Authored layers. Its bounded clone copies static mesh/material
bindings, transforms, collision profiles, tags, 22 practical lights and two
interior volumes per region. Only the terrain/road material overrides change.
Comparison tolerates at most 0.000001 cm/degree numeric reconstruction rounding;
bindings, colours, collision and boolean settings remain exact. All existing
WorldRebuild packages and owner GM documents are fingerprinted and checked even
after failure. Existing private kit dependencies remain frozen and private.

The first material study is
`8ab0d264508e75029b5b2a1be1d564738968090ccbde78d8c1da2319590a3c0e`,
at `/Game/WorldRebuild/T1Redesign_Materials_8ab0d264508e_024400_600929`.
`review-t1-materials.py` verifies saved clone state and compiled shaders before
capturing 52 unmodified 1280 × 800 native day/dusk/night views, including road
detail, village, advance, ridge, scenery and both furnished homes. It repeats
8,712/8,631 full-width native ground samples; maximum route grades remain
0.179626/0.151356. Saved maps remain unchanged and capital lighting restores.

The terrain shader reports 365 pixel instructions and five texture samples;
the translucent road shader reports 1,226 instructions and five samples. These
are compiler statistics, not measured frame time or platform performance.
Road cost needs investigation. Actual pictures also expose yellow daytime
Sunmeadow ground, dark village nights, sparse scenery and unfinished cultural
architecture/roof connections. Keep appearance and camera approval open.

After the Editor build, run
`python scripts/unreal/run-t1-traversal.py --candidate materials --headless`.
The material namespace is separately admitted by the same bounded local fixture;
other study types, capitals, owner layers and later batches remain excluded.
The complete rerun passes 80 configured routes with zero airborne travel and
36,994.42 m total normal movement. Receipt
`traversal/1791420441042931500-15244` binds the implementation/DLL, 11,177 saved
files and all 13 owner documents. It does not transfer parent-map evidence or
grant driving, gameplay, visual, performance or release acceptance. Omitting
`--headless` runs the four real-time home camera walks on these material maps.
Material movement/camera receipts use separate `material-traversal-*-latest.json`
files; parent home receipts remain intact. Material build/review evidence lives
in `materials-latest.json` and `material-review.json`; the local progress gallery
retains all old pictures and adds the new studies.

The rendered material-map rerun also passes all four home approaches/interiors
in real time, covering 646.95 m with zero airborne travel. Its 12 normal follow
camera/indoor-mode pictures are retained at
`traversal/1791420853693274600-28028`, again with unchanged saved packages and
owner documents. The expanded gallery contains 150 actual native pictures and
14 schematic drawings. The live camera and commandlet atmosphere views show
different ground colour/exposure; calibrate against the gameplay camera before
appearance approval. Fixture-controlled indoor mode is not automatic room
camera acceptance, and these movement fixtures do not prove network clock or
live campaign behavior.

The native build and all 145 Foundation tests pass at
`artifacts/unreal/editor/test-1791420644815-23572`. All three typechecks,
1,081 repository tests, 473 Unreal tooling tests and 14 focused Python tests
pass. Migration audit, 33-map world and 906 model validation pass; strict release
checking still returns exit 1 with four retained gates. Active campaign/capital
bindings, first-batch lair acceptance, normal GM/network proof, 18v18, platform
and Steam acceptance remain unchanged and incomplete.
