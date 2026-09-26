# Capital neighborhood expansion

The September 25 pass adds 120 buildings and 12 furnished interiors in each
capital, and replaces 60 repetitive Aegis houses at full architectural scale.
The additions use 33 compositions in Aegis and 36 in Riftspire; the replacements
use all 12 compact compositions, with 12 replacements in each Aegis district.
Its stable layouts combine large kit assemblies, compact modular
townhouses and existing Riftspire source architecture. District palettes separate
wall, roof and trim roles. Existing gameplay, streaming ownership and GM drafts
remain part of the acceptance requirements.

## Authoring and ownership

`scripts/unreal/capital_expansion.py` contains deterministic composition recipes,
district palettes, oriented footprint tests, road/service exclusions and spatial
planning. The planner first fits larger houses, then individually composed small
townhouses into the remaining lots. Buildings are never squeezed onto uniform
pads. Native ground traces reject unsupported or steep lots. Interior definitions
include a home/shop/workshop/inn/guild/civic mix, floor heights and walking routes.

Purchased originals remain unchanged. The staging script selects only required
meshes and verifies their dependency closure and package hashes. Adaptations live
under ignored `/Game/LicensedKits/CapitalExpansion/V1`; receipts, backups and
images live under ignored `artifacts/unreal/capital-expansion/`. Source/license
review and all shipping-platform acceptance remain separate and incomplete.

Static assemblies retain material assignments, vertex data, collision and LODs.
Each new building has its own `WarWorldObject_` identity and source fingerprint,
so the existing native GM catalog can discover it. Furniture and exterior decor
are part of its mesh and move with it. The 38 local, shadowless interior lights
belong to the authored zone level and attach to their building for GM transforms.
They use explicit lumen units (1,800 lumens, 900 cm radius); this avoids the
much brighter default candela interpretation. Shared mesh templates have at
least three conventional LODs, and material instances come from a bounded palette.
New drafts continue to reference trusted template IDs, never kit
Blueprint paths. No purchased construction script or door behavior is executed.

Each city has four homes, two shops, two workshops, two inns, a guild room and a
civic room. Seven interiors per city have upper floors. The layout reserves both
door circulation and the complete upper stair landing before fitting furniture.
Town furniture, bedding, tabletop objects and torch fixtures use selected source
meshes. New entrances use open modular frames; closed merged door leaves are not
used in the enterable templates.

The native GM bounds support distant world origins while retaining Aegis's
existing boundary. A private, explicitly generated replacement admission table
matches each old identity, source fingerprint and transform to an installed
replacement. Only untouched old draft entries can migrate. Owner changes to a
replacement target, copies of a replaced template, forged fingerprints and
unreviewed replacements fail closed. The original draft file is never rewritten
by the authoring scripts. The game proof imports a copy into an isolated folder.

## Reproduction

Close editor/game instances before modifying packages or compiling modules. Run
UnrealEditor-Cmd with `-run=pythonscript -script=<absolute script path>` and
`-unattended -nosplash`. Use `-NullRHI` only where stated below. Require a fresh
success marker and receipt, not merely process exit zero.

1. Run `inspect-capital-expansion.py` in CityKitStaging and AegisWar with
   `-NullRHI` to inventory kits and snapshot the current saved cities.
2. Run `stage-capital-expansion.py` in CityKitStaging with `-NullRHI`.
3. Run `build-capital-expansion-assets.py` in AegisWar with
   `-RenderOffscreen -AllowCommandletRendering`. It merges only explicitly created
   temporary actors in a fresh scratch level and writes per-template receipts.
4. Run `render-capital-expansion-templates.py` with the same rendering flags and
   `-NoTextureStreaming`. These are studio inspections, not saved-city lighting
   approval. Inspect roofs, gables, furniture facing and architectural seams.
5. Run `plan-capital-expansion.py` in AegisWar with `-NullRHI`. Failed placement
   attempts remain in `plan-candidate.json`; only a complete validated layout
   produces `plan.json`.
6. Run `python scripts/unreal/capital_expansion_proof.py` to prepare matching
   native proof views before edits. Run the game with `-WarExpansionProof
   -WarDevelopmentGM -WarExpansionRun=<id> -WarExpansionBefore -RenderOffscreen`
   for baseline views. Use fixed resolution and graphics settings for comparisons.
7. Run `apply-capital-expansion.py` in AegisWar. It backs up affected packages and
   the partition manifest, records a recovery journal before saving, and compares
   every unaffected actor. It modifies only the two authored capital levels.
   A matching rerun verifies hashes and makes no changes. Changed packages fail
   closed. A partial save requires explicit reconciliation using the journal;
   never rerun an old baseline inspector to bypass a conflict.
8. Repeat the native proof without `-WarExpansionBefore`. The opt-in development
   subsystem captures real game views and walks configured interior routes using
   the actual player character. Reports and images live under
   `Saved/CapitalExpansion/<id>/before` and `after`.

The first native walk exposed furniture crossing an upper landing. The recorded
`before-interior-revision` asset/plan/receipt backup and
`revise-capital-interiors.py` apply that specific correction to fingerprint-matched
expansion actors; all surveyed bounds must remain identical. Its journal and map
backups support recovery, and a matching rerun is inert. This revision also
attaches the interior lights. Existing asset packages remain intact.

For the selected existing-house replacements, run `plan-capital-replacements.py`
and inspect its explicit `replacement-plan.json`. It excludes owner-edited or
copied draft templates, tests neighbouring geometry and roads, and traces support
at native scale. `apply-capital-replacements.py` backs up the authored level,
checks the owner draft hash, applies the reviewed set, and creates the private
legacy-draft admission table. `verify-capital-expansion.py` then compares the
saved scene against original actors plus only the recorded edits. Attached-light
rotations compare equivalent quaternion signs without tolerating actual changes
to position, scale, rotation, materials or collision.

`survey-capital-room-clearance.py` also checks room and entrance volumes against
foreign scenery, temporarily enabling collision on nonblocking cliff meshes in
an unsaved survey world. Four Riftspire rooms needed small surveyed offsets, with
one rotation. The frozen `room-refit-plan.json` and
`apply-capital-room-refits.py` record those changes, attached-light transforms,
backups and fingerprints. The final survey found no foreign geometry in any of
the 24 checked interiors or entrances. Never replace an applied refit plan with
a later survey report.

After all passes, run `check-capital-expansion-rerun.py` with `-NullRHI`. It requires
all completion markers, reruns the four guarded apply entry points, and verifies
that maps, receipts, the partition manifest and the owner draft are byte-identical.
For later owner changes, author a new reviewed revision; do not erase markers or
refresh the original baseline to force an old plan through its conflict checks.

## Recorded local verification (September 25)

- Repository: 660 tests across 92 files; the Unreal tooling subset has 126 tests
  across 19 files. All three typechecks, world/model validation and Unreal audit
  passed. The audit still reports four release blockers.
- Authoring: 13 focused Python tests, existing capital layout/appearance/detail
  tests, and 58 native foundation tests passed. Saved-scene verification accounts
  for 16,651 original actors and 278 additions (240 buildings plus 38 lights),
  allowing only the recorded palette, replacement and room-refit edits.
- Walking: `Saved/CapitalExpansion/capital-expansion-revised/after/report.json`
  records all 24 interiors walked with the actual 84 cm diameter, 192 cm tall
  player capsule. The final pass rewalked the four refitted rooms and captured
  all 28 final views in `capital-expansion-final/after/`.
- GM: edit/undo/redo, attached lighting, isolated import of the existing owner
  draft and reload after city travel passed. The original owner draft remained
  unchanged. The standard capital proof also passed gameplay/station interactions,
  six resources and a fresh-process construction reload; the castle proof passed
  all 12 routes. Reports: `artifacts/unreal/capital-proof/crownward-1790342226272/`
  and `crownward-1790342449658/`.
- Streaming: the two-client native zone/lighting isolation proof passed at
  `artifacts/unreal/world-portals/network/1790342086252-4088/report.json`.
- Repeatability: all four guarded apply passes left the ten protected files
  unchanged; see `artifacts/unreal/capital-expansion/repeatability.json`.

The standard capital proof derives expanded catalog totals from fingerprinted
saved-scene receipts (`capital-scene-counts.ts`), rather than rebuilding the city
or trusting the retired builder's obsolete object count.

Matching before/after captures use 1280 x 800 and a 60 FPS cap. P95 sampled frame
time was 16.680 ms before and 16.667 ms after; physical process memory increased
from 3,315.2 MiB to 4,682.6 MiB (+1,367.4 MiB). This increase is material and
requires a shipping memory budget review. These are editor-hosted game samples,
not uncapped CPU/GPU profiles. The largest template has 237,270 LOD0 triangles
and five LODs down to 15,262 triangles; furnished templates also retain reduced
LODs. The pass stages 43 source meshes and a 103-file dependency closure.

`performance-comparison.json` records the measurements and native streaming log
slices. Aegis actor initialization logged 36.03 ms before and 44.71 ms after;
Riftspire component registration logged a 122.23 ms slice after expansion. Unreal
only logs slow slices, so an absent baseline entry is not a zero-cost baseline.
End-to-end streaming latency and uncapped GPU profiling remain unverified.

Rendered review sheets are `capital-aerial-comparison.png`,
`aegis-interior-review.png` and `riftspire-interior-review.png` in the expansion
artifact directory. Full matching street/aerial images live in
`Saved/CapitalExpansion/capital-expansion-comparison/{before,after}/`.
Final interior images are in `capital-expansion-final/after/`; their matching
preconstruction locations are in `capital-expansion-final/before/`. These views
show this pass under saved game lighting, not commandlet studio lighting. They
do not approve the remaining world art or certify shipping visual quality.

The initial full baseline capture stopped after 17 views. To complete it at the
final camera positions, `capture-capital-expansion-baseline.py` runs with ordinary
Python and all Unreal processes closed. It verifies both pre-expansion backup
hashes and current map hashes, saves verified restoration copies and a journal,
temporarily loads the two original maps for the offscreen game, then restores
the final maps in a `finally` block. A timeout also restores them. If the host is
terminated, inspect the retained `capture-restore-*/journal.json` and restore its
verified map copies before opening the editor. This is a capture operation,
not a way to reset or rebuild cities.

## Verification boundaries

Run `python tests/unrealCapitalExpansion.test.py`, the existing relevant capital
Python tests, `npm test`, all three typechecks, `npm run test:unreal`,
`npm run unreal:audit`, `npm run world:validate`, `npm run models:validate`, and
native foundation/zone-network checks. Strict release checking must remain closed.

Layout counts and imported assets alone do not prove interior traversal, GM
reload, art quality, network play or performance. Rendered frame samples and
physical memory are local comparisons, not three-platform certification. Review
the final diff and content destinations before sharing; purchased binaries must
never enter the public repository.
