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


## T1 installed nature studies (9 October 2026)

The installed Medieval Houses kit contains a separate Real_Landscape folder.
Native inspection finds 73 static meshes and preserves 602 purchased source
packages. A bounded fifteen-mesh selection stages seventy dependency packages
(419.2 MiB) byte-for-byte into ignored private Content. Inspection/staging never
executes purchased Blueprint behavior or grants license/distribution approval.

Fresh scene `da8d24dc6eb3`, navigation `c5b86a74d12c` and safe walkthrough
`5792eee29cca` replace 331 Sunmeadow canopy bindings with three installed oaks.
Exact native bounds retain each original height and lowest point; actor identity
and yaw remain. Geometry/materials change, so old collision or appearance
acceptance does not transfer. Source terrain `83b37fc34b68` remains unchanged.
Slope-to-rock coverage is reduced on gentle ground; generated meadow colour
remains outside this candidate.

Fresh checks pass 108 rendered views, 142 configured normal walking routes,
88 pedestrian/convoy navigation queries before save/after reload, exact safe-copy
tile payloads, both ordinary entry/local GM recovery fixtures without draft
writes, and twelve actual normal follow-camera pocket captures. All thirteen
owner documents and pinned parent/capital maps remain preserved. Current
navigation copies have not separately repeated the complete walking suite.
Repository tests pass 1108/172 files, Unreal selection 487/91 and Python 119/32
(including three tests for the separate planting study). All three typechecks,
migration audit and world/model validation pass; strict release exits 1.
Earlier native builds/Foundation tests retain earlier scope; no C++ changed.

`t1_understorey.py` is a separate cosmetic authoring study. An unsaved native
comparison renders 6538 grass, 4912 long-grass, 4112 fern and 410 seedling instances,
reserving roads/services and tapering density near paths. This planting has not
been saved/admitted into the candidate. Source-only transition diagnostics reject
globally narrowed grading bands because existing routes exceed the 0.22 grade
limit. Broad smooth terrain, bare ground, harsh lighting and regional composition
remain unfinished. `progress-report-nature-da8d24dc6eb3.html` embeds fourteen
actual native images; `nature-checkpoint-da8d24dc6eb3.json` records exact results.

Retain appearance, first-batch full lairs, physical driving/turning, closed gates,
18v18, services/resources, ordinary GM persistence, Node additive-prop collision
synchronization, network/audio, performance, three-platform/Steam and release
gates. Later-pair native and full underground environments remain unbuilt.


## T1 saved understorey and local terrain studies (9 October 2026)

Private scene `8cccccfea202`, navigation `2875ce2b59ed` and safe walkthrough
`f4c008c8ba9b` save four installed-plant batches: 6538 grass, 4912 long-grass,
4112 fern and 410 oak seedlings. Sunmeadow now has 25078 cosmetic instances;
Cinderfen retains 6375. Exact native bounds, LOD/material bindings, transforms,
source fingerprints and the retained local/nonblocking/culling policy are checked
on fresh reload. This density has no performance or appearance acceptance.

Fresh checks pass 108 native views, 142 configured normal walking routes,
88 navigation queries before save/after reload, exact safe-copy tile payloads,
both ordinary entry/local GM recovery fixtures without draft writes, and twelve
actual follow-camera pocket captures. All thirteen owner documents and pinned
parent/capital maps remain preserved. Current navigation copies have not
separately repeated the complete walking suite. Repository suites pass 1111/173
files and Unreal selection 490/92; Python passes 119/32. All three typechecks,
migration audit and world/model validation pass; strict release exits 1.
No C++ changed; earlier native builds/Foundation checks retain earlier scope.

Source-only `366c962d85ea` narrows eleven eligible terrain transition bands per
region while retaining the main advance and first rotation. Full-width source
grade maxima are 0.217571 Sunmeadow and 0.216482 Cinderfen. Military pad heights,
route identities, pocket beds and closed water are checked. Native geometry,
collision/walking/navigation, arrivals and appearance for this revision remain
pending; the saved scene still uses source terrain `83b37fc34b68`.

Separate unsaved native comparisons inspect installed grass/forest substrate
and neutral transient daylight. Twelve exact ground texture channels remain
private; neither their use nor daylight overrides are integrated into the saved
candidate. Sky recapture alone does not resolve the harsh look. The first daylight
diagnostic failed to enumerate transient lights; the repaired GameplayStatics
version completes twelve captures while preserving source packages/maps.
`progress-report-understorey-8cccccfea202.html` embeds sixteen actual native images
and labeled source topology drawings; its matching checkpoint JSON records hashes.

Broad smooth terrain, repeated/bare ground, harsh foliage shadows and regional
composition remain unfinished. Retain first-batch full lairs, human appearance,
physical driving/turning, closed gates, 18v18, services/resources, ordinary GM
persistence, Node additive-prop collision synchronization, network/audio,
performance, three-platform/Steam and release gates. Later-pair native and full
underground environments remain unbuilt.


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


## Contact-aware rocks and selected core outcrops (10 October 2026)

Scene `0d633e30966b`, navigation `ff8835fb85c3`, safe copy `b056429b854e`
retain source `cbc1c13f223b` and core `676151d36b96`. `t1_rock_contact.py`
uses unique native rendered LOD0 vertices with exact transforms and shared
triangle grounding. At least eight percent of vertices must be buried two
centimetres in two source quadrants. This is a vertex-contact surrogate, not
contact-area or stability proof. Additional burial is capped at 1.5m, one quarter
of full height and the remaining exposed-height reserve. Scaled minimum bedding
seats broader silhouettes while retaining horizontal footprints and yaw.

Five original Sunmeadow outcrops and seven eligible Cinderfen outcrops now use
the installed clusters. Two unsupported Cinderfen core parents remain. Saved
totals are 168/227 bodies, 93/123 replaced parents and 1/6 retained parents.
Unmatched source meshes, landmarks and shelters remain. Reload repeats committed
LOD0 geometry/four-LOD thresholds, native vertex bedding and component-only
simple/complex exposed-surface traces. Original kit packages remain exact.

Fresh native checks pass 114 views, 150 walking routes, 92 navigation queries
before save/after reload, exact safe navigation copies, both grounded entry/GM
fixtures without draft writes, twelve actual pocket cameras and sixteen saved
rock closeups. All thirteen owner documents, parents and capitals are preserved.
Navigation copies have not separately repeated every walking route. Repository
1125/176 files, Unreal 504/95, Python 148/38, three typechecks, audit and world/
model validation pass; strict release exits 1. No C++ changed. The private
`progress-report-rock-contact-0d633e30966b.html` embeds 24 pictures; its checkpoint
records hashes and signatures. Retain the unresolved earlier recovery failure
and every existing appearance, lair, physical vehicle/18v18, service/resource,
GM persistence, Node additive collision/live play, network/audio, performance,
platform/Steam and release gate. Later native pairs/full underground remain
unbuilt. Proposed drainage cuts remain private source studies, unintegrated.


## Compact drainage source and native prototype (10 October 2026)

Source `aae1209eb967`, core `8d344fd4519e`, scene `93003b49b5f1`,
navigation `b3fd5077cf4c` and safe copy `2693f53b9efc` integrate ten Sunmeadow and six
Cinderfen drainage-inspired cuts. `TerrainField.incisions` is optional, bounded to
64 courses, 64 controls each and 24m depth; compact kernels contribute exactly
zero outside their widths and use maximum union. Untouched fields retain their
original behavior. Authoring tracing follows descending sampled ground, bounds
search and local roughness, and caps depth against downstream controls. This is
not hydrology: nearby radial caps and intersecting kernels can retain uphill
sections despite bounded one-metre sampled steps.

The immutable writer preserves qualified parents, gameplay routes, complete
military anchors, arrivals, pocket beds and closed cosmetic basins. Absolute
scenery rebases with ground. Exact triangle-clipped roads retain their 0.045m
support and soft alpha. Full-width route grades remain below 0.22. Native checks
pass 114 phase/weather views, 150 walking routes, 92 navigation queries before
save/after reload, safe copies, both entry/GM fixtures without draft writes and
twelve pocket cameras. Twenty-four extra day/night captures verify 363 component-only
simple/complex terrain samples and clear playable review-camera footing. New
gullies have not received complete physical exploration or vehicle acceptance.

Repository 1132/177 files, Unreal 511/96, Python 148/38, three typechecks, audit
and world/model validation pass. Strict release exits 1; no C++ changed. The
private `progress-report-drainage-93003b49b5f1.html` embeds 28 pictures. Parent
packages, capitals, seventy nature packages and all thirteen owner documents
remain preserved. Navigation copies have not repeated the full walking suite.

Outer cuts remain too smooth and regular; Sunmeadow's inner cut is suppressed
by route supports. Distant ground, foliage and regional stone remain unfinished.
Retain appearance, first-batch full lairs, actual driving/turning/closed gates,
18v18, services/resources, ordinary GM persistence, the earlier unresolved
recovery failure, Node additive collision/live play, network/audio, performance,
platform/Steam and release gates. Later native pairs and full underground remain
unbuilt. Private owned-mesh residual studies are unintegrated licensed derivatives.


## Private source-derived relief prototype (10 October 2026)

Source `1cd84df61040`, core `bd8812c7434e`, scene `1e7203cb76e2`,
nav `df574d641bb1` and safe copy `e4f6e9fc2090` add owned-mesh erosion residuals.
The optional `TerrainRelief` contract admits complete finite rectangular grids,
bounded heights, bilinear detail and compact smooth edges. Lowlands suppress
detail; legacy fields omit it. Private extraction reads native rendered faces,
chooses the highest triangle at every grid point and rejects missing coverage.
Two 257x257 derivatives subtract an 80m low-pass to retain medium-scale structure.
Original geometry, samples, packages and pictures remain private licensed content.

An unprotected study failed pedestrian route grades. Revised authoring bakes
smooth exclusion aprons around paths, convoy segments, grading corridors and
footings, including counters without flattening controls. Retained gameplay
anchors/arrivals stay within 1cm; road coordinates, pool beds and closed cosmetic
basins pass. Full-width grades remain below 0.22. Exact road clipping retains
0.045m support. Parent packages, capitals, all thirteen owner documents and the
92-package nature/backdrop source union remain preserved.

Fresh native 114 phase/weather views, 150 walking routes, 92 navigation queries
before save/reload, safe copies, both entry/local-GM fixtures, twelve pocket
cameras and 24 extra day/night views pass. Additional component-only simple/
complex traces verify 578 terrain samples and playable camera footing. These
are not complete off-route exploration, physical driving, turning or 18v18.
Navigation copies have not separately repeated every walking route.

The private Node loader admits twenty authority configurations; 4575 cached
terrain queries match exported triangles within 0.031mm. The initial 0.01mm
diagnostic failed on Float32 coordinate quantization; the retained passing
tolerance is 0.1mm. Diagnostic warm-loop timings do not accept performance or
a live Node connection. Native additive collision remains unsynchronized.

Repository 1141/178, Unreal 520/97, Python 148/38, three typechecks, audit and
world/model validation pass; strict release exits 1. No C++ changed. The private
`progress-report-relief-1e7203cb76e2.html` embeds 28 pictures. Broad hills and the
box-shaped road network still look artificial; foliage shading/stone remain
unfinished. Neutral daylight, canopy surveys and simple curve studies are
unintegrated. Preserve earlier recovery-repeatability, appearance, first-batch
full lairs, services/resources, ordinary GM persistence, physical vehicle/combat,
live/network/audio, performance, platform/Steam and release gates. Later native
pairs and full underground remain unbuilt.


## Softer Sunmeadow daylight checkpoint (10 October 2026)

Source `1cd84df61040`, core `409a2b6095c2`, scene `8c1018ccd774`,
nav `54bb95b837a4` and safe walkthrough `9f398cd36999` retain the relief terrain.
Sunmeadow now uses 14000 lux direct sun, 12000 lux diffuse fill and daytime sky
intensity 4, with softer sun/fill/fog colours. The shared native rig applies this
regional sky endpoint in static preview and the continuous cycle. Cinderfen's
amber profile, night moon/sky output and accepted capital restoration stay intact.
Neutral and lower-exposure Cinderfen comparisons were rejected and remain unsaved.

Editor and Game builds pass. All 151 Foundation tests pass, including new
daylight, unchanged night, untouched-region and authored capital-light assertions.
Fresh native 114 phase/weather views, 150 walking routes, 92 navigation queries
before save/reload, both ordinary-entry/local-GM fixtures and twelve pocket
follow-camera pictures pass. Thirteen owner documents, source packages, parent
maps and accepted capitals remain preserved. The navigation copies have not
separately repeated every walking route. Repository 1141/178, Unreal 520/97,
Python 148/38, three typechecks, audit and world/model validation pass. Strict
release exits 1. The private daylight report embeds 21 pictures.

A private connected Sunmeadow route proposal moves flank junctions, sweeps shared
edges and reconnects pockets/overlook approaches. Broader secondary checks
rejected earlier steep variants. A nearest-segment blending experiment was
rejected for height discontinuities. Smooth per-corridor balanced blending passes
the full route set at 0.219347 maximum grade; six supplies remain 350-750m, retained
keep/staging/arrival ground passes and Brookmeadow Pool stays enclosed. These are
unintegrated private source studies; public contract/tests and native proof are
still required. No physical turning, driving or combat acceptance is implied.

Broad green hills, sparse undersized canopy, repeated grass, empty horizons, road
layout and Cinderfen stone remain weak. Full-height watershed, forest scale/cover,
distant ground and underground prototypes remain next work. Preserve the earlier
unresolved recovery-repeatability, human appearance, first-batch full-lair,
vehicle/closed-gate/18v18, services/resources, ordinary GM persistence, live
Node/additive collision, network/audio, performance, platform/Steam and release
gates. Later native pairs and full underground remain unbuilt.


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


## Absolute landform and woodland checkpoint (10 October 2026)

Source `8f3fa2d0ecc2` and scene `2ba289f4c44d` admit an optional bounded absolute
height raster. The first full-height bake produced an artificial boundary cliff
ring and was rejected. The current source raster extends beyond the native
sampling rectangle, with a compact boundary fade. Immutable private receipts
check actual sample and source-package hashes, exact parent signatures and
licensed-derivative/no-distribution flags. Samples and private native packages are
not public repository content. Legacy terrain remains unchanged.

Old routes, complete keep/staging footings, arrivals, pockets and closed water
basins retain their grounding. A narrow 40m blend originally missed a retained
resource approach, causing a native walking failure on a terrain face around
47 degrees. Six qualified native population approaches now participate in raster
protection. The resource approach full-width source grade is 0.18459163; the main
route maximum remains 0.21934734. Native walking criteria were not relaxed.

Sunmeadow adds 190 irregularly clustered 13-22m oaks, with clearings, protected
full-crown lane reserves, retained source geometry/five LODs/three simple
colliders and a strict global canopy budget. The candidate contains 477 installed
canopy actors. The forest-soil mask includes the new trees. Native additive
collision synchronization with Node remains unaccepted. Cinderfen terrain, roads,
pockets and links remain byte-exact; its steep-ground basalt palette is darker.
Installed pale rock-cluster materials need a separate regional adaptation.

The first pair gains one stop of night exposure, continuously fading out during
dawn/dusk. Moon/fill/sky intensities, daytime endpoints, other regions and
accepted capital lighting remain retained. Editor and Game targets build; all
151 Foundation tests pass, including night values and capital restoration.
Fresh native 114 phase/weather views, 150 walking routes, 92 navigation queries
before save/reload, both isolated ordinary-entry/local-GM fixtures and twelve
pocket follow-camera views pass. Thirteen owner documents, parent maps, accepted
capitals and source packages remain preserved. Navigation copies have not
separately repeated every walking route. Repository 1166/184, Unreal 535/101,
Python 153/39, three typechecks, audit and world/model validation pass. Strict
release exits 1. In-process Node admits twenty configurations; 4575 ground samples
match exported triangles within 0.031mm at 0.1mm tolerance. Live owner Node is
untouched, and live authority/additive collision are not established by this.

The native result is still visually weak: artificial graded shoulders, uniform
grass, distant canopy billboards and empty horizons remain. Unsaved terrain-first
route-height, source-derived distant-ground, habitat-palette and canopy-LOD
comparisons are the next iteration. Preserve human appearance, first-batch
full-lair progression, actual vehicle driving/turning/closed gates, 18v18,
services/resources, ordinary GM persistence, the earlier unresolved Cinderfen
recovery-repeatability failure, live Node/additive collision, network/audio,
performance, platform/Steam and release gates. Full underground and later native
pairs remain unbuilt. Scripted checks do not establish enjoyable or fair combat.


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
