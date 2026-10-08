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
