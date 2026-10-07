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
