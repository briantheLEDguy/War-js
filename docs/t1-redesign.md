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

## Native regional atmosphere checkpoint

`AWarRegionalAtmosphere` is an opt-in scenery actor on fresh first-pair copies.
It reads `AWarEnvironmentState` for time and regional weather strength; the
server retains control of conditions. Local effect geometry and original
synthesized audio do not change capture rules, collision, navigation, saves or
campaign admission. Dedicated servers disable the actor's tick. Capital maps,
music and environment remain outside this actor's admitted zones.

Rain uses at most 192 short soft quads, geothermal steam at most 24 and the dry
wind/ash profile at most 96. Only Sunmeadow/Cinderfen are generated in native
candidates. Later-batch metadata/rules do not bypass the first-batch lair gate.
Geothermal vent sites derive from existing basalt/mineral scenes, projected onto
ground or their exposed saved rock tops. Bounded room volumes and overhead
visibility queries shelter the observer. These queries affect local presentation
only; weather sections never have collision or navigation influence.

The regional mix combines nature, cosmetic weather, village work and distant
military pressure. Village work quietens at night; frontage proximity and existing
local combat notices influence military intensity. Sound beds are original
deterministic native synthesis, mono 24 kHz PCM, with continuous sample indexing
across quarter-second chunks and less than half a second queued. Master mute
stops/reset the bed. No capital music or licensed recording is reused. Listening,
hardware playback and sound-design acceptance remain open.

Reproduction uses the saved/closed editor workflow above. Run the following
Python scripts in `UnrealEditor-Cmd` with `-run=pythonscript -script=<absolute
script path>` and `-unattended -nop4 -nosplash -nosound`:

- `scripts/unreal/build-t1-atmosphere-studies.py` with `-nullrhi`: validate parent
  material maps/source hashes/private kit, clone the complete mesh/light/room
  inventory into fresh Review/Generated/Authored layers, and add one local actor.
- `scripts/unreal/review-t1-atmosphere.py` with `-AllowCommandletRendering
  -RenderOffscreen -NoTextureStreaming`: check saved bindings and shader, capture
  native dawn/day/dusk/night/strong-weather views and export eight-second WAV data
  previews. These are synthesized studies, not hardware playback recordings.
- `python scripts/unreal/run-t1-traversal.py --candidate atmosphere --headless`:
  independently walk both directions of every configured road/supply itinerary
  plus home routes. Omit `--headless` for four real-time home walks, normal cameras
  and effect/shelter observations at reached waypoints. Atmosphere copies use the
  actual local authoritative clock rather than the parent fixture's day preview.

The fresh collection signature is `3915005bbaf3`; private build/review evidence
lives in `atmosphere-latest.json` and `atmosphere-review.json`. The review retains
45 native pictures and 12 synthesized WAV studies, with exact preserved parent
scenery/rooms/lights and saved packages. The initial shader-pin failure and first
placement study remain in private logs/candidates. The revised study shortened
rain streaks and moved buried vents to exposed rock tops. Steam remains visually
weak. The refreshed mineral camera searches grounded viewpoints and rejects
terrain-occluded views and positions inside scenery bounds. These are unfinished
prototypes requiring another visibility pass. Dark shaded scenery, sparse
dressing, generic furnished-house culture and roof/wall gaps also remain open.

The independent fixed-timestep traversal passes all 80 configured routes on the
atmosphere copies, covering 36,994.42 m with zero airborne travel. Its receipt
`traversal/1791425807306220400-22156` binds source/DLL state, 11,198 saved files and
13 unchanged owner GM documents. Static walking does not grant vehicle, camera,
gameplay, visual, persistence, network, platform or release acceptance. First-pair
full lairs and 18v18 remain incomplete.

The four real-time atmosphere home routes also pass, covering 646.93 m with zero
airborne travel and 12 normal-camera pictures at reached waypoints. Receipt
`traversal/1791426053017861300-31748` observes one active, non-replicated,
non-colliding atmosphere actor, zero effect quads indoors and bounded queued audio
bytes. Both zones are sampled in daylight using their authority clocks. Sunmeadow's
strong spell fades during travel: exterior frames show 154 then 123 quads;
Cinderfen's sampled mild conditions show 12. `-nosound` intentionally leaves
`audioPlaying=false`; this proves queued-data bounds, not audible hardware playback.
The expanded gallery has 207 native pictures, 14 drawings and 12 WAV controls.

A Windows Development Game build exposed existing Editor-only API use in city
classification, shader witnesses and proof binary checks. The bounded repair
uses `CLASS_CompiledFromBlueprint`, guards `BaseMaterialId` with `WITH_EDITOR`,
and introduces `WarProofBinary.h`: modular Editor builds bind their actual loaded
module, while monolithic Game builds bind the executable. Receipt hashes/path
checks and production admission remain strict; no package or authored lighting
is edited. Game and Editor builds pass. The refreshed atmosphere copies bind the
new Editor DLL; their movement/camera evidence must be generated independently.
The independent reruns above pass against that DLL. The earlier atmosphere copies
and their nighttime movement evidence remain private as historical studies.

Final verification passes both Windows Development targets, all 146 native
Foundation tests (`artifacts/unreal/editor/test-1791426966600-21836`), 1,081
repository tests, 473 Unreal tooling tests, 19 focused Python tests and all three
typechecks. The migration audit retains 39 feature contracts and four blockers;
33-map world and 906 model validation pass. Strict release checking returns exit
1 as required. No active campaign package, accepted capital scene, owner document
or licensed source kit is changed or published. Native gameplay/services/Node
collision integration, ordinary GM persistence, reciprocal network travel/clock,
hardware audio, visual approval, driving, 18v18, full first-batch lairs, three
platforms, Steam and release acceptance remain incomplete.

## Modular furnished-home roof checkpoint, 2026-10-08

`build-t1-shell-studies.py` constructs new assemblies from the frozen capital
catalog's final component placements. It references 88 fingerprinted kit
dependencies, reconciled against the original staging receipt, and never edits
the source templates or capital scenes. All wall, doorway, floor and furniture
transforms/material bindings remain exact. Shared bed-frame, mattress, pillow
and sheet pivots are resolved as one bounds group, preserving their assembly.

The kit slate roof uses Z=0 as its eave datum and extends its decorative skirt
10 cm below that plane. Normalizing the skirt's bottom to the wall top lifted
the 1.5-scaled main roofs by 15 cm and the porch roofs by 10 cm. The reusable
refit repairs those attachments and lowers each roof's chimney by the same
15 cm. It refuses an unexpected skirt, a changed attachment datum, a second
repair or a multi-storey/non-home recipe. Four source LODs and the original
material slot ordering are retained; distant LOD appearance remains unverified.

Fresh first-pair copies preserve terrain, road/scenery transforms and collision,
22 practical lights, two room volumes and the frozen local weather/audio
settings per region. Their separate `shells-latest.json` receipt identifies the
study as `home-shell-refit`; its native map remains an isolated atmosphere
candidate in the existing first-pair fixture namespace. Active campaign
admission and default capital maps are unchanged. Previous candidates and
failed authoring attempts remain private historical data.

Reproduce after saving/closing Editor and game processes:

1. Run `build-t1-shell-studies.py` through the rendering commandlet, using
   `-AllowCommandletRendering -RenderOffscreen -NoTextureStreaming`.
2. Run `review-t1-shells.py` in a fresh process. Its LOD0 triangle witnesses
   compare both parents and refits: 60 sampled rays escaped the original eave
   strips; zero escape the refits. This is sampled seam evidence, not full roof,
   window, weather-sealing or distant LOD acceptance.
3. Run `review-t1-homes.py` with the Unreal command-line flag `-WarT1Shells` and
   rendering enabled. All four homes pass 4,218 native capsule checks and 34
   swept step transitions. Its 24 day/dusk/night interior/exterior pictures
   retain unapproved dark roof undersides and generic stone architecture.
4. Run `python scripts/unreal/run-t1-traversal.py --candidate shells --headless`.
   The independent saved copies complete all 80 normal-character routes,
   36,994.42 m, with zero airborne time, jumps or in-route teleports. The receipt
   is `traversal/1791430240123320200-9668` under the private T1 directory.
5. Run the same command without `--headless` for live home walks, authority
   clock/weather shelter observations and normal gameplay-camera screenshots.
   Regenerate the local gallery with `t1-progress-gallery.py`.

The final live receipt is `traversal/1791430444252484500-24572`: four home
routes, 646.97 m, zero airborne time and 12 normal-camera pictures. Authority
daylight progresses through dusk in Sunmeadow and into night in Cinderfen;
indoor waypoints suppress local weather particles. These are local clock and
shelter observations, not network synchronization or hardware audio acceptance.
The refreshed private gallery contains 243 native captures, 15 labeled drawings
and the existing 12 synthesized audio previews. A roof datum schematic labels
its exaggerated offset; the native images remain the appearance evidence.

The headless run verifies 11,257 saved bindings and preserves all 13 owner GM
documents. Repository and Unreal tooling suites pass 1,081 and 473 tests;
focused Python passes 24, along with all three typechecks. The migration audit retains four
blockers; 33 world maps and 906 model records validate. Strict release checking
still fails as required. No native C++ changes or new binary build are needed
for these assembly adapters; they bind the previously verified Editor DLL.
Ordinary candidate gameplay/services/Node collision, GM persistence, network
travel/clock, vehicle/siege/human traversal, 18v18, full first-batch lairs,
hardware audio, regional appearance, platform performance, Steam and release
acceptance remain open. Later native batches remain gated by those lairs.

## Modular timber-ceiling checkpoint, 2026-10-08

`t1_home_ceiling.py` derives six or nine 300 cm bays from each frozen furnished
home's measured room footprint. It admits only the first-pair, single-storey
homes, refuses a second installation and rejects changed timber dimensions or
less than 250 cm bounds clearance. The staged `SM_MH_02_Wood_Floor_01` is rotated
180 degrees so its original textured plank face looks into the room; no
two-sided override or visible primitive is introduced. Its measured 25.2 cm
depth fits below the 310.2 cm wall/eave top, retaining about 275 cm minimum
clearance above the original floor.

`build-t1-ceiling-studies.py` checks the roof/capsule parent receipts, freezes
89 source-kit dependencies against the original staging inventory and creates
new Review/Generated/empty Authored layers. Four ceiling meshes retain separate
source-derived material instances and three native LODs: 2,256/1,128/452
triangles for the smaller rooms and 3,384/1,692/676 for the larger ones. Every
existing house mesh, doorway, furniture, scenery, practical light and room
volume binding stays exact. One new shadowless interior fill per home follows
the existing authority clock, at 5,000 day/3,000 night lumens, a 700 cm radius
and regional warm colour. This improves some plank readability; perimeter
darkness, light spill, overall contrast and performance still need review.

Native overhead review passes 120 upward triangle witnesses on a 150 cm grid.
Each home has one foreground hit on its unchanged merged house. The receipt
records those hits, then ignores that house only to inspect the ceiling behind
it. This is ceiling surface sampling, not full roof/weather sealing or global
headroom acceptance. The independent home capsule review ignores no furniture
and passes all 4,218 checks and 34 swept step transitions. Day/dusk/night
reviews capture 12 ceiling details plus 24 normal interior/exterior views.

Reproduce after saving/closing Editor and game processes:

1. Run `build-t1-ceiling-studies.py` through the rendering commandlet with
   `-AllowCommandletRendering -RenderOffscreen -NoTextureStreaming`.
2. Run `review-t1-ceilings.py` in a fresh rendering process. Then run
   `review-t1-homes.py` with the Unreal command-line flag `-WarT1Ceilings`.
3. Run `python scripts/unreal/run-t1-traversal.py --candidate ceilings --headless`
   for all road/supply/home walks; omit `--headless` for real-time home cameras
   and local clock/weather shelter observations.
4. Use the bundled Pillow Python to run `t1-ceiling-pictures.py`, then regenerate
   the gallery with `t1-progress-gallery.py`. Drawings are labeled schematics;
   native captures remain the actual appearance evidence.

The final isolated ceiling study is `7ee15f64ea52`, recorded separately in
`ceilings-latest.json`. The initial transform comparison failure, the first dark
ceiling study and unsaved fill-light diagnostic remain private history. Existing
maps, source assets and all owner GM documents are preserved. No native C++ or
binary change is required; prior native Foundation/build results are retained
as prior evidence rather than claimed as new runs.

The new saved copies independently complete all 80 configured normal-character
routes, 36,994.42 m, with zero airborne time, jumps or in-route teleports. Their
headless receipt is `traversal/1791433257531651500-13604`; it verifies 11,293 saved
bindings and preserves all 13 owner GM documents. This is fixed-timestep walking
evidence, retaining human traversal, vehicle and gameplay acceptance gates.

The separate live receipt is `traversal/1791433468443562700-19576`: four home
routes, 646.93 m, zero airborne time and 12 normal gameplay-camera captures.
Local authority-clock/weather shelter validation passes at the reached indoor
waypoints. The gallery now contains 291 native captures, 16 labeled drawings
and the existing 12 synthesized audio previews. Network synchronization and
hardware audio remain unverified; these are local development fixtures.

Repository tests pass 1,081, Unreal tooling passes 473 and focused Python passes
29, along with all three typechecks. The migration audit retains four blockers,
33 world maps and 906 model records validate, and strict release checking still
fails as required. Cultural architecture, shading/ceiling LOD appearance,
ordinary gameplay/services/Node collision, GM persistence, reciprocal network
travel/clock, vehicle/siege/human traversal, 18v18, full first-pair lairs, actual
audio, platform performance, Steam and release acceptance remain open.

## Retained population and stronger-relief checkpoint, 2026-10-08

The owner found the previous screenshots unreadable and the terrain too flat.
Progress images are now attached directly through native image output rather
than relying on the broken local-image links. The latest native captures still
show overly dark daylight, sparse villages, broad smooth slopes and generic
architecture. They are prototypes, not visual approval or completed regions.

`t1_population.py` reconciles frozen first-pair candidates against canonical
content, saved native actors, exact profile imports and reviewed resource
catalogs. It permits coordinates/orientations to change while refusing changed
names, roles, quest/resource rules, rewards, visual identities or material slot
order. Six staged camp additions absent from the canonical content manifest stay
pending; they cannot admit themselves through an imported profile. The two
preexisting generated-map hash mismatches are recorded against the installed
source, without rewriting the active manifest or canonical maps.

`build-t1-population-studies.py` freezes the native dependency closure and copies
six exact retained `WarCityNpc` actors plus four `WarResourceNode` herb patches
into new private ceiling candidates. Existing replacement idle clips and the
Cinderfen officer's catalog sidearm are preserved, without activating paused
procedural animation studies. NPCs/resources keep their authored NoCollision;
terrain, scenery and the normal player capsule still provide the measured
approach collision. Grounding traces ignore every actor except the actual
terrain; foot support and swept capsules ignore no scenery. Bounds sit 2 cm
above measured ground. All ten admitted actors retain their authored horizontal
coordinates, source rules and exact mesh/material/equipment state.

Cinderfen herb nodes 04 and 07 failed access within the bounded local search and
remain pending. A proposed shoulder relocation was rejected by automatic
approval review as exceeding the local adjustment scope; it was not performed.
The builder proceeds with independently verified actors and records the failed
terrain/capsule witnesses. Thirteen NPCs, twenty resource sites including these
two, and all six complete crafting stations remain pending across the first
pair. Native placement does not prove vendor/trainer/quest services or harvest
transactions. Node geometry is not synchronized with these private overrides.

The isolated population study is `e3beee613ed7`. Cold-load review verifies all
ten bindings and 1,412 approach samples, with forty native dawn/day/dusk/night
views. Normal character walking completes 90 routes, 38,343.91 m, with no jumps
or in-route teleports. The separate live diagnostic was rejected by its source
guard when relief selection changed the launcher while it was running; no
verified population live receipt is claimed. Two measured population topology
drawings label ready actors, connected roads and failed access sites.

`t1_relief.py` responds to the requested stronger landscapes with elongated
valley ridges, escarpments and broken geothermal rim masses. It preserves the
terrain's XY vertices, triangle topology and UVs, then recalculates upward
area-weighted normals, including the existing clockwise native winding.
Road corridors have a 20 m protection pad and 85 m relief transition. Anchor
terraces, 209 Sunmeadow/233 Cinderfen content bounds and all ten verified actor
approaches are protected separately. Fresh terrain meshes retain the exact
regional source-derived material; other terrain/road, house, furniture, light,
room, population and atmosphere bindings are unchanged.

The isolated dramatic-relief study is `f1cbf55b2c6e`: 29,403 Sunmeadow vertices
and 19,096 Cinderfen vertices gain height, up to 164.98 m and 134.99 m respectively.
Native comparison passes 17,343 full-width road samples with exactly zero
parent/child height difference and unchanged actor approach floors. Forty-eight
native before/after day/dusk/night pictures use identical player-height camera
positions/directions, clock settings and original lighting. The taller terrain
is present, but erosion, cliff treatment, vegetation, culturally distinct village
composition, lighting and additional traversable off-road relief remain
unfinished. No off-road, siege sight-line, competitive or visual gate is granted.

Reproduce after saving/closing Editor and game processes:

1. Run `build-t1-population-studies.py` through the Python commandlet, then
   `review-t1-population.py` with rendering enabled. Use `t1-population-pictures.py`
   with the bundled Pillow Python for measured drawings.
2. Run `python scripts/unreal/run-t1-traversal.py --candidate population --headless`
   for the isolated population movement proof.
3. Run `build-t1-relief-studies.py` through the commandlet. Run
   `review-t1-relief.py` with rendering enabled for saved-ground comparisons and
   matched views. Use `run-t1-traversal.py --candidate relief` with/without
   `--headless` for normal walking and real-time cameras.
4. Regenerate `t1-progress-gallery.py`. Private maps/meshes/receipts and licensed
   source assets stay out of the public repository; accepted capitals, active
   campaign layers and all owner GM documents remain exact.

First-pair full lairs, later native batches, service/resource/Node integration,
ordinary GM persistence, reciprocal network travel/clock, human walk/drive,
vehicle/siege/18v18, hardware audio, platform performance, Steam and release
acceptance remain held. Prior native Foundation and Editor/Game build results
remain prior evidence; this increment changes authoring code and private scenes,
not native C++ or binaries.

The raised copies separately complete all 90 configured normal-character
routes, 38,343.91 m, with zero airborne time, jumps or in-route teleports. The
headless receipt is `traversal/1791438414902167500-30912`, verifying 11,624 saved
bindings and preserving all 13 owner GM documents. Full suites pass 1,081
repository and 473 Unreal tooling tests; all 41 focused Python tests and three
typechecks pass. Two persistence tests initially timed out in concurrent full
runs; all 106 persistence cases pass in isolation and both full suites pass
when repeated serially. The migration audit retains 39 contracts/four blockers,
33 world maps and 906 model records validate, and strict release still fails
as required. No timeout or assertion was weakened. Additional read-only herb
shoulder/road-centre probes found no verified alternative within 50 m; neither
pending resource was spawned or relocated.

The final live relief receipt is `traversal/1791438703650517100-16128`: fourteen
normal-character home/actor approach-and-return routes, 1,996.33 m, zero
airborne time, jumps or in-route teleports and forty-two native gameplay-camera
pictures. The stable launcher/source guards pass, along with reached-waypoint
local authority-clock/weather and indoor shelter checks. Nameplates and the
retained native actors run in the live world; their service/harvest actions are
still unverified. The refreshed gallery contains 421 native captures, eighteen
labeled drawings and the existing twelve synthesized audio previews. Dark
daylight/night readability, camera acceptance, actual hardware audio, network
synchronization and all other held gates remain open.

## Interactive walkthrough repair

The first interactive launch incorrectly opened the raw dramatic-relief
`Review` map. Its `WarZoneAnchor` was still at native `[0,0,0]`, below the actual
terrain, and the map was not admitted to local GM tools. Configured traversal
tests explicitly placed their own pawn, so they did not cover ordinary entry.
Those movement receipts remain valid within their stated scope; they did not
establish a usable owner walkthrough.

`stage-t1-review.py` creates fresh `T1HumanReview_<revision>/<zone>/Walkthrough`
routing wrappers. They reference the exact parent content layers and change
only the regional anchor's safe arrival/orientation and explicit game mode.
Arrival uses the retained `spawnPoint`, terrain-only height, full foot support,
playable outline and unobstructed native 42/96 cm capsule checks. Source maps,
meshes, materials, population, startup configuration and owner GM documents are
fingerprinted before/after; partial failed wrappers are preserved as diagnostics
and never accepted or reused by the launcher.

`WarWorldEditMap` admits these two exact region/revision identities only when
the process selects the same map. Existing local authority, possessed-character,
development-world and non-Shipping conditions still apply. Each walkthrough has
its own `WorldEdit/PrivateReviews/.../draft.json` path; it never falls back to the
capital draft. The existing GM recovery/flight functions remain in use.

Reproduce with saved Editor/game sessions closed: run `stage-t1-review.py` in
the main project's native Python commandlet, then
`python scripts/unreal/launch-t1-review.py --zone sunmeadow_march --proof` and
the equivalent Cinderfen command. The opt-in runtime fixture invokes ordinary
character creation through the retained frontend controller path, requires
grounded arrival, enables GM flight, moves its disposable pawn below terrain,
uses Return to spawn, resumes walking and checks stable terrain support. It
does not write drafts. Omit `--proof` to launch interactive play, with normal
login/character entry and the explicit local GM flag. Selected-map configuration
is process-local; the accepted campaign/default capital stays unchanged.

This fixes review entry/recovery only. T1 world-builder catalog expansion,
save/load persistence, normal online admission, network roles, performance,
appearance, services/resources, full lairs, vehicle/siege/18v18 and release
acceptance remain unverified.

The verified wrapper revision is `4db1efef0aff`, based on relief `f1cbf55b2c6e`.
Sunmeadow's anchor centre is native `[-28000,-58500,599.49]` cm over ground
`500.49` cm; Cinderfen uses `[-29000,38000,1299.49]` cm over `1200.49` cm.
Both rendered ordinary-entry/recovery fixtures pass, including stable ground
after returning from 25 m below the arrival. Each verifies 543 saved bindings
and all 13 existing owner GM documents, without writing a draft. Native captures
and reports are in `interactive/a30638079ecf45bbb703faeb7a1bc0c7` and
`interactive/981bce54a45f48a1b3b35316e11a8e4b`. Windows Editor and Game builds
pass, as do all 146 native Foundation tests, including the expanded map/draft
admission checks. The first fixture used a name with a digit and was rejected
by ordinary name validation; only the corrected, passing runs are accepted.
The two staging exceptions were likewise repaired in fresh copies, preserving
their partial diagnostic packages and all source content. Older terrain walking
receipts retain their original binary scope; these recovery checks do not
reclassify vehicle, persistence, camera or gameplay acceptance.

Four focused Python launch/arrival tests and all three typechecks pass. World
validation covers 33 maps and model validation 906 records; the migration audit
retains 39 contracts/four blockers, and strict release still fails as required.
Both full repository runs pass 1,080 tests and time out only the existing
reference-citadel generation test at its unchanged 75-second limit. The exact
Unreal selection passes all 473 tests/85 files when run directly with
`npx vitest run unreal --maxWorkers=1`, including that case, while the owner game
stays open. Do not report either full repository run as green. No assertion or
timeout was weakened, and no unrelated citadel implementation was changed.

## Connected battlefield terrain prototype

The perimeter-only relief study remains historical evidence. The new first-pair
prototype changes terrain within the route network: open battle spaces, a middle
saddle/reveal, ridge back slopes and gentler cross-country links. Broad ridge
fingers, variable-width basalt shelves and authored drainage share a coherent
heightfield; seeded rolls provide smaller variation. This is authored landform
construction, not a simulated erosion solver or accepted landscape composition.
The first native views still show overly smooth, sparse terrain. Scenery cells
and material adaptations are camera-review prototypes; broad dressing remains open.

`shared/terrainField.ts` is a bounded, serializable source contract used by
`shared/orvrTerrain.ts`. Ridge branches share height rather than stacking into
cones. Explicit grids retain Float32 triangle correspondence; first-pair sampling
uses four-metre spacing. Legacy square/bilinear terrain and unmodified maps retain
their previous evaluation. Settlement/home pads can explicitly preserve footing
against nearby road shoulders. Their blends remain graded; objective pads retain
the established route-priority behavior.

`t1-battlefield-landscape.ts` retains XY gameplay identities and routes, changes
their elevation profiles, moves keep anchors as complete assemblies and rebases
absolute scenery onto the new ground. Three deliberate off-road links per region
share road-intersection heights without painted overlays. Retained furnished-home
approaches are part of the ground contract. The initial Cinderfen native walk
failed on a home approach: a neighboring road shoulder raised settlement ground.
Explicit footing priority and graded entrance links repair that regression;
outside route targets now use actual new ground, while interiors move rigidly.

`prepare-t1-battlefield.ts` writes immutable signature-qualified bundles under
`artifacts/unreal/t1-redesign/battlefield`, including all 32 candidate maps and
reciprocal arrivals. `build-t1-battlefield.py` creates fresh private native copies
from preserved retained-content receipts. Prior source bundles, old native
packages, accepted capitals and every existing owner draft remain unchanged.
Owner-authored content is never merged into or overwritten by these prototypes.

`t1-battlefield-scenes.ts` reserves four small camera-review cells, admitting 71
Sunmeadow and 52 Cinderfen sockets from existing source models. Grove, limestone,
basalt and reed clusters keep the road/off-road corridors, objectives and keeps
clear. Broad rock bases embed beneath surrounding ground without flattening the
hillside. These conservative reservations do not certify combat cover, camera
collision, visual quality, native foliage performance or asset distribution.
Private source-channel adaptations change grass/peat/rock balance while retaining
the exact reviewed texture inputs; materials and daylight readability remain open.

The road exporter previously omitted the ribbon's vertex alpha, leaving native
verges opaque. Export now retains that channel and the first pair uses a three-metre
transition with intermediate fade bands, preserving the solid nine-metre centre
on twelve-metre roads. Render-only roads keep collision on the terrain. Rotated
detail at 1.83 times the primary texture scale, irregular macro variation and
verge breakup reuse the reviewed color/normal channels. Outside this optional
recipe, earlier material behavior remains unchanged; no source bitmap is edited.

`t1-battlefield-grades.ts` measures combined climb and sideways bank in two-metre
lanes. The original three-lane longitudinal check missed a Cinderfen village-front
bank. Broader settlement transitions and a lower frontage junction correct it
without moving XY identities or keep assemblies independently. Native review
checks actual collision-face normals as well as source correspondence. The .22
surface-grade target is an authoring limit; it does not certify driving.

Rendered review also checks the committed native road's corner alpha and rejects
shader fallback warnings through `t1_render_log.py`. Null-RHI material construction
alone does not prove shader compilation. The first variation graph connected an
alpha mask to VertexColor's RGB output and fell back on SM6; that private receipt
is explicitly rejected and a fresh candidate fixes the alpha pin.

Reproduce with saved Editor/game processes closed:

1. Run `npm run unreal:t1-battlefield`, then `build-t1-battlefield.py` through the
   project's native Python commandlet. Preserve existing source revisions; reuse
   a verified bundle for native copies, or generate a fresh revision after changes.
2. Run `npm run unreal:t1-battlefield-scenes`, then
   `build-t1-battlefield-scenes.py` for fresh private scene candidates.
3. Run `review-t1-battlefield.py -WarT1BattlefieldScenes` with commandlet rendering,
   then `python scripts/unreal/run-t1-traversal.py --candidate battlefield-scenes
   --headless`. Review checks full-width native ground, source correspondence,
   arrivals and retained bindings. Walking uses the unchanged normal character.
4. Run `t1-battlefield-pictures.py` with NumPy/Pillow for measured contour/profile
   PNGs. The drawings are authoring diagrams; native images remain unmodified.
5. After matching native review/walking receipts, run `stage-t1-review.py
   -WarT1BattlefieldScenes`. Launch with `launch-t1-review.py` and use `--proof`
   to verify ordinary entry/GM recovery before interactive inspection.

Source checks retain the .22 grade target, six 350–750 m supply itineraries,
two uncapturable staging camps, two keeps, three objectives and campaign/lair
identities. Native ground/capsule checks, configured walking and pictures grant
no vehicle, 18v18, online gameplay, persistence or appearance acceptance. Full
Warden's Hollow/Cindermaw environments still gate batch progression. Brightfen/
Ashen native buildout and all platform/Steam/release gates remain outstanding.

The final source bundle is `fcb02f40d24d`, native core `e0e713ba3347`, scene cells
`12cc9a6e4683` and safe walkthrough `c8b15f5ac634`. Source preparation binds the
qualified original walkthrough and scene-parent receipts. Staging now changes
only the latest routing pointer; it cannot invalidate a dependency on itself.
No source/native asset, capital or owner document was overwritten.

Rendered review passes 35,378 Sunmeadow and 36,918 Cinderfen ground samples,
including native collision-face slopes across two-metre lanes. Maximum combined
grades are .208023 and .211396; main advances are .208023 and .191891. Source/native
ground error stays below .000371 cm. All 163,815/163,167 native road corner colors
match the exported fade. Sixty-four player-height dawn/day/dusk/night PNGs and
the rendered D3D12/SM6 log pass without shader fallback. Landscape appearance
remains unapproved: broad slopes are still too smooth/sparse and Cinderfen daylight
remains too dark. The texture/road improvements do not finish regional art.

`traversal/1791454724817444700-4008/summary.json` records all 110 configured routes:
56 Sunmeadow (20,732.86 m) and 54 Cinderfen (21,779.81 m). Normal character movement
retains the 42/96 cm capsule, 45 cm step and 600 cm/s speed, with no jumps or
in-route teleports. It checks 11,768 saved bindings and preserves 13 owner documents.
The fresh walkthrough fixtures in `interactive/22e05113fd814660b0733fe9a81df7c1`
and `interactive/8dc5a074898b44bbbccaf559547c1fcf` pass ordinary character entry,
GM flight, return from 25 m below terrain and stable walking afterward. Each
verifies 660 bindings and writes no owner draft. Ordinary persistence and online
GM admission remain separate gates.

Final repository verification passes 1,097 tests/169 files, the explicit Unreal
selection 479 tests/88 files, 23 focused Python tests and all three typechecks.
World/model validation passes 33 maps/906 records. The migration audit retains
39 contracts/four blockers; strict release exits 1 as required. No C++ changed in
this pass. Existing Windows builds/146 Foundation checks retain their earlier
binary/report scope; native terrain/render/walking/entry proofs above are fresh.
The private `progress-report.html` labels actual native pictures, gameplay
recovery images and authoring diagrams separately. Native/licensed content stays
private, and every outstanding visual, lair, vehicle/combat, service/resource,
persistence, network, audio, platform/Steam and release gate remains open.


## 2026-10-09 landscape and ecology checkpoint

The owner authorized continued reversible iteration while AFK, including later
source studies, without questions or waiting for a visual response. That does not
approve the appearance or close the formal batch/release gates. The drawings and
screenshots still show sparse dressing and smooth terrain; the first pair is not
finished, and no zone is described as nailed.

Optional `TerrainField.weathering` warps ridges and drainage together, adds
multiscale height breakup masked by the ridge mass, and smooths basalt bedding
into ledges. This is bounded authored weathering, not a physical erosion
simulation. Omitted controls retain the legacy field exactly. Broader road/pad
feathers reduce abrupt cut bowls while preserved village/home footing stays fixed.

Eight landscape neighborhoods per region now reserve groves, field edges,
basalt shoulders, peat margins and reed pockets. Embedded rock varies horizontal
proportions and bedding angle; trees remain upright. Roads, objectives, keeps,
services, arrivals and unpainted counterclimbs retain conservative exclusions.
This admits sockets; it does not certify combat cover, line of sight or camera
collision. Reviewed rock color channels use three-axis projection on steep ground;
normal mixing, rotated detail and irregular substrate patches retain source hashes.
Cinderfen alone receives more readable daylight and charcoal basalt adaptations.

`t1-landscape-pockets.ts` reserves two Sunmeadow and four Cinderfen pockets on
sampled ground. Every admission rechecks the new approach together with existing
roads, home entries and off-road links at the unchanged .22 combined-grade limit.
Initial site choices damaged the peat counterclimb; candidate-wide rechecking
rejects those choices. A closed basin is required for active water. Brookmeadow,
Amber Runoff and Cinderreed contain water; Hearthroot, Rustsedge and Embervein are
seasonal dry hollows in this revision. Their labels describe design targets, not
new quests, hazards, encounters or completed exploration gameplay.

`t1_landscape_ecology.py` exports terrain-clipped shallow water and deterministic,
road/service-aware cosmetic source-model clumps. `AWarLandscapeDetail` admits
1�12,000 finite bounded transforms atomically, preserves existing instances when
rejected, and disables collision, overlaps, navigation, ticking and replication.
Native HISM culling ends at 120m; high-detail source grass is still subject to
runtime frame/memory review. Dedicated servers hide the local visuals. Actual
terrain retains grounding and all gameplay actors remain separate. Native reload
verification covers every saved instance transform, source mesh and material,
plus the identity actor frame, non-replication, no shadows and exact cull distances.

Three pools use the native single-layer water shader, local small ripple normals
and smooth wet-substrate blending around their measured elevation. Water is
cosmetic, with a .45m authored shallow bed; no swimming or new hazard mechanics
are added. Native winding initially culled the water from above. Correct clockwise
front faces and a focused regression check repair it. Water appearance remains
unfinished: dark, flat-looking views and shoreline composition still need work.

The immutable first-pair source is `c6e02c216f4b`, native core `8aa73d07bd01` and
scene candidate `0a8a35baca3a` (preserved render/walking checkpoint). The fresh rendered review checks 35,682/37,638
full-width Sunmeadow/Cinderfen samples, with maximum native grades .213925/.205313
and maximum source error below .000217cm. It verifies 4,133/2,271 saved cosmetic
instances and three water surfaces. All 98 unedited player-height captures across
four clock phases, stronger weather, landscape neighborhoods and pockets export
without shader fallback. Render and source checks grant no human art approval.

`traversal/1791561257244359900-6172/summary.json` passes all 122 configured normal
walking routes (60 Sunmeadow, 62 Cinderfen), including the new pocket approaches,
with unchanged capsule/step/speed and no route jumps or teleports. Safe routing,
ordinary entry and local GM recovery are re-proved separately for each final
revision. Headless movement is not vehicle, performance or 18v18 acceptance.

`t1-second-pair-landscape.ts` adds source-only Brightfen limestone islands,
inter-island channels and narrow causeway shoulders, plus Ashen layered sandstone
plateaus, a bending wash and tributary gullies. `prepare-t1-second-pair.ts` exports
immutable map/terrain/road bundles without active-map changes. Brightfen's first
broad embankments merged its islands; narrower shoulders, smaller relief widths
and water divides repair the source study. Ashen's rectangular sampling respects
the shared 512-segment limit. Source `fa4505c39eb6` checks 32,529/33,852 full-width
samples at maximum grades .100346/.155696. Three focused tests preserve original
keeps, six itineraries, objective IDs, services, encounters and resource identities.
Native later-pair architecture, scenery, collision and gameplay remain unbuilt.

`t1-landscape-atlas.py` draws all four measured layouts, with keeps, objectives,
rotations, villages, staging and optional lair branches. Blue Brightfen areas are
proposed water in an authoring diagram. Native screenshots, real gameplay-camera
captures and these diagrams are explicitly separate in the private progress report.
No underground environment has been built; that request remains outstanding.

Windows Editor and Game builds succeed; the fresh Foundation suite passes 147
checks, including new atomic detail admission and Cinderfen lighting/night checks.
The repository suite passes 1,103 tests/171 files and the Unreal selection 484/90.
The final second-pair revision additionally passes its three focused tests; the
three typechecks pass. Sixty focused T1 Python checks pass. World/model validation
passes 33 maps/906 records; audit retains 39 contracts/four blockers and strict
release exits 1. Preserve every outstanding full-lair, human visual, vehicle,
18v18, service/resource behavior, ordinary GM persistence, online authority,
network/audio, frame/memory/travel, platform/Steam and release gate.


The stricter saved-detail check produces scene `e6eaa25eb1f7`, with the same
geometry and fresh 98-view/native-ground/shader checks. Its normal walking run
`traversal/1791561821442281900-20276/summary.json` passes all 122 routes.
`ecology-gameplay/1791561829890042300-34864/summary.json` adds twelve actual
gameplay-camera PNGs while a normal visible character walks all six pockets.
The replicated clock reaches dawn/daylight during this run; a previous preserved
revision covers actual night. All 13 owner documents and saved candidate bindings
remain unchanged. These checks confirm movement and rendering, not appearance.
The daylight water reveals overly regular ripple patterns and strong amber
color; organic wave variation and shoreline art remain explicit next work.


Final safe walkthrough `c59d9f80a94a` retains scene `e6eaa25eb1f7`. Its fresh
ordinary-entry/local-GM fixtures verify grounded spawn, flight, return from 25m
below terrain and stable walking, with no draft writes. The private checkpoint
`natural-checkpoint-e6eaa25eb1f7.json` links exact receipts; the matching qualified
HTML progress report embeds unmodified native PNGs and measured drawings directly,
fixing dependence on relative image links. It explicitly labels unfinished art.


## 2026-10-09 shoreline and texture iteration

`t1_water_surface.py` replaces the two regular cardinal ripple axes with three
unequal oblique wavelengths (4.6/7.3/2.9m), gentle opposing phase speeds and a
bounded total normal slope below .021. A fingerprinted regional color channel
perturbs phase. This changes only local shading; collision, terrain and gameplay
remain unchanged. Pure checks cover slope, continuity and finite inputs. The
fresh native render removes the obvious grid, but the shallow water still needs
composition and color work; no appearance acceptance is granted.

Dark source color had been used directly in macro/detail masks, suppressing
variation. `t1_surface_variation.py` now admits an explicit bounded linear-channel
range; the material graph clamps and smoothsteps that range before mixing scales
and macro brightness. Sunmeadow uses .04–.24 and Cinderfen .008–.075, informed by
measured source PNG channels after sRGB decoding. Terrain and road shaders retain
world-space scale and their original reviewed textures. Sunmeadow's green tint
is reduced, with stronger soft substrate patches rather than hard color borders.

`t1_pocket_dressing.py` builds uneven elevation-following bank patches from the
already admitted parent shrub/reed/rock meshes. It rejects full corridor widths,
services, preserved footings and overlapping reservations. Fresh private scene
`66ce92c05559` admits 125/143 additional bank placements and 4,470/2,740 saved
cosmetic ground-cover instances in Sunmeadow/Cinderfen. Three wet and three dry
pockets remain; no new quest, encounter, hazard or underground environment is
implied. All 98 fresh native captures pass saved bindings, source/native grade
and shader-fallback checks. Normal walking and ordinary-entry receipts must match
this exact candidate before it replaces the safe walkthrough.


Candidate `66ce92c05559` passes all 122 configured normal walking routes in
`traversal/1791562764861658000-1688/summary.json`. Its twelve actual gameplay-camera
captures in `ecology-gameplay/1791562848406262800-17228/summary.json` cover all six
pockets with visible normal characters. Safe walkthrough `cd0c11467c46` separately
passes ordinary entry and local GM flight/below-terrain recovery for both regions,
with no draft writes. All 13 owner documents and pinned saved bindings remain
unchanged. The matching private checkpoint/report embeds ten unedited PNGs and
labeled drawings. Sixty-five focused Python checks pass; the Unreal regression
selection passes 484 checks across 90 files. Previous build/native Foundation and
three-platform/release results keep their previously documented scope; no new
C++ build or release acceptance is inferred from this shading/scenery iteration.


## 2026-10-09 counterable scarps and continuous ends

The shared `escarpment` profile gives directed ridges a shorter exposed face and
broader back. Scaling only the cross-section keeps radial end caps continuous.
The initial profile produced a 12.36m jump across an extended crest in a regression
fixture; that prototype is superseded. Rounded/shelf recipes retain exact legacy
formulas. Sunmeadow limestone and Cinderfen fault studies now have two explicit
12m back climbs each, joining an unpainted overlook. The initial taller scarp
failed two-access admission and was lowered/regraded; no clearance or grade limit
was relaxed. Existing main routes, keep assemblies, objectives and identities stay
aligned. Source export now grades both climbs with roads, off-road links and pocket
approaches. Native checks independently cover full-width triangle support below .22.

`t1_landscape_walks.py` bounds source search and tests actual saved native capsule
clearance. The admitted authored pair takes precedence; a blocked/steep/incomplete
pair fails rather than granting access acceptance. `t1_traversal.py` includes both
normal walking directions. Ten scenery neighborhoods per region preserve full
corridors, services and the overlook. Cliff shading restrains painted source-atlas
joints with bounded geological color variation; it is still too smooth in places.
Soft-verge noise uses the normalized source channel, and wet-bed soil now extends
below shallow water rather than exposing bright grass under the pool.

Source `5b00d5211792` produces private native scene `f27c9bdf8572`, with safe
walkthrough `d2edaa5c27c8`. All 102 fresh native captures pass saved bindings,
shader-fallback rejection, source/native triangle correspondence and full-width
grade checks. Maximum native grade is .213926/.205313 for Sunmeadow/Cinderfen.
Normal-character traversal `1791565384921369000-24504` passes 138 configured routes
(68/70). Counter gameplay run `1791565380262943000-19920` provides eight real climb
camera images; pocket run `1791565670787699900-28872` supplies twelve images of six
pockets. Ordinary entry/local GM fixtures `8864bb84af7b4b5a8e580400e632cc12` and
`49416dbf54d24d41abad0e40906de9e8` prove grounded spawn, flight, below-terrain recovery
and stable walking with no draft writes. All 13 owner documents and pinned saved
bindings are preserved. Cosmetic cover counts are 4,447/2,740; bank placements are
129/151. The qualified private HTML report embeds fourteen images, combining unedited
native PNGs and labeled drawings; it grants no art acceptance.

The full repository rerun passes 1,105 tests/171 files, the Unreal selection passes
484/90 and all three typechecks pass. Seventy focused Python checks pass. One
5-second persistence tamper fixture timed out during concurrent work; both cases
passed unchanged on focused retry, then the full suites passed on rerun. World/model
validation passes 33 maps/906 records. Audit retains 39 contracts/four blockers;
strict release exits 1 as required. No C++ changes occurred; earlier Windows
Editor/Game builds and 147 native Foundation tests keep their documented scope.

Brightfen/Ashen source `5501fff6e60c` refreshes its shared-input bindings without
altering legacy profile geometry. Atlas `8a861b9d103d` labels all four measured
layouts, with first-pair back climbs distinguished from vehicle routes. Later-pair
native environments and underground environments remain unbuilt. Preserve the
first-batch full-lair gate and every human visual, vehicle, 18v18, service/resource
behavior, ordinary GM persistence, online/network/audio, frame/memory/travel,
platform/Steam and release requirement. Continue rock-face, ecology, settlement
and exploration work; technical traversal is not appearance or combat approval.
