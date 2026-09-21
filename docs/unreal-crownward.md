# Integrated Aegis capital and castle

Open `unreal/AegisWar/AegisWar.uproject`. **AegisWar is the game project**;
`artifacts/unreal/licensed-kits/CityKitStaging` is only a private import workspace.
Both the editor startup and development game default map are
`/Game/Capitals/crownward/AegisCapital_Workbench`. CityKitStaging does not contain
the game module and should not be used to play or build the game.

Press Play in AegisWar. **G** opens City Builder, **I** inventory/crafting,
**L** the quest log and **E** interacts with a nearby NPC or station. Standalone
development GM sessions additionally require `-WarDevelopmentGM`. Production
admission remains closed pending Steam ownership and all migration gates.

## Original geography, purchased architecture

The earlier flat city grid has been replaced. The level shares the original
Aegis terrain and canals and retains all 145 house-site identities, the five
source districts (Gateward Market, Cinderbank, Lantern Quays, Bellfound Court,
Crownwatch), and the 30 source road paths. Complete purchased house assemblies
are fitted within the existing plots while retaining their authored height. The main road winds uphill from the lower
city to the 42-metre citadel terrace. The modular castle occupies that terrace:
curtain enclosure, four projecting towers, twin-tower gatehouse, courtyard,
multistorey keep and battlements. The original eroded granite massif rises
behind it; its authored GLB geometry and repository textures are reused. Two
zero-area edge triangles are discarded during native import.

There are 8,704 editable placements using 14 kit mesh types. Ground, roads and
mountains are terrain construction, not primitive scenery substitutes. The
source city and its old workbench remain available for reference. This restores
the source geography and house sites; it does not establish complete parity for
public buildings, every interior, mountain passages, encounters or travel.

The keep and courtyard stair modules now face uphill in their assembled runs.
Eight roof tiles above the keep stairwell were removed, leaving a clear exit
onto the roof; all unrelated placement identities remain unchanged. The native
character has walked up and down both the keep-to-roof and courtyard-to-battlement
routes. These sampled routes do not establish access to every tower, interior
or rampart. Existing earlier proof drafts have a different roof baseline; owner
drafts still block regeneration and require explicit reconciliation.

## Gameplay integration

The city runs the main project's `WarGameMode`, `WarCharacter`, player state,
ability system, inventory, quest HUD and GM subsystem. Mara Vell is placed at her
original capital position and uses the existing native quest NPC class and
catalog identity. All five source crafting stations retain their kinds, positions
and interaction radii, using an imported authored command-table model. Their
specialized visual dressing and the dispatch character's final art approval
remain pending. The existing development characters remain a limited roster.
Fresh development sessions do not establish durable online progression.

CityKitStaging provides only selected purchased static assets and their verified
dependency closure. Native code, gameplay content, map assembly and packaging
remain in AegisWar. Raw purchased packages stay private and Git-ignored.

## Editing and reproduction

Crownward drafts use `Saved/WorldEdit/crownward-draft.json`; the reference capital
uses its own draft. Drafts are revision checked and bounded to 8 MB. Compact JSON keeps city-scale
saves within that limit; older pretty-printed drafts remain readable. The generator
refuses regeneration if an owner draft exists or the map changed after its last
generation receipt. Save in-game drafts before leaving Play. Existing drafts
require explicit baseline reconciliation before changing generated geography.

1. Stage the licensed selections in CityKitStaging using `stage-capital-kit.py`,
   `inspect-capital-kit-props.py` and `stage-capital-kit-props.py`.
2. In AegisWar, run `build-kit-capital.py` via an unattended Unreal Python commandlet.
   It requires the original terrain import, admitted development characters and
   imported command table. `capital_geography.py` reads the original source;
   `capital_kit_layout.py` builds the modular plan; `capital_game_world.py` assembles
   terrain and existing native gameplay actors.
   `capital_materials.py` duplicates/recompiles the legacy market cloth material
   without changing its shader graph, textures or subsurface model, then binds
   that native copy to the adapted mesh. It can also run as a standalone Python
   commandlet to update the mesh without regenerating the city or changing drafts.
   Its private hash receipt rejects changed sources, edited adaptations and
   unrecorded destination assets. Original purchased material files stay intact.
3. Run `npm run unreal:crownward-proof`. Its first process uses the configured
   default game map, with no explicit map override. Tests cover the sampled
   459-metre grounded ascent, native quest range/acceptance/retry, station ranges and kinds, GM
   construction/undo/redo and isolated fresh-process draft reload.
4. Run `render-kit-capital.py` with `-RenderOffscreen -AllowCommandletRendering
   -NoTextureStreaming` for screenshots without desktop input.
5. Use `npm run unreal:package-proof -- --include-crownward` for a private
   Development package containing the city and existing test map. This is not
   release or licensed-distribution approval. Verify the packaged client with
   `npm run unreal:crownward-proof -- --packaged-root artifacts/unreal/packages/Win64`.

`python tests/unrealCapitalLayout.test.py` checks geography, source identities,
castle elevation, complete house types, paired market frames and owner-draft
protection. Full interior/seam traversal, performance, shared GM authentication,
Linux/macOS and Steam release checks remain required.

For builder surface placement, run `npm run unreal:crownward-proof --
--surface-placement --rendered`. This separately exercises all 14 kit meshes
through the placement RPC, checks their actual bounds/collision, verifies drop,
rejected operations, undo/redo and fresh-process reload, and captures the panel
offscreen. Add `--packaged-root artifacts/unreal/packages/Win64` after rebuilding
the package to run the same checks outside the editor. It does not replace the
grounded ascent/gameplay proof above or establish full visual acceptance.

Use `npm run unreal:crownward-proof -- --construction-row --rendered` for the
separate row-construction check. It creates three rotated wall modules, verifies
their spacing and support, rejects invalid/unsupported rows without partial
placement, undoes/redoes the whole row, and reloads all three in a fresh process.
The same `--packaged-root` option runs this check on the Windows package.

Use `npm run unreal:crownward-proof -- --castle-traversal --rendered` to walk the
six castle routes in both directions: entrances to the roof, battlement and
four upper keep floors. The character uses ordinary collision
and walking at 3 m/s, with no jumping or flight. Each focused route begins at a
checked teleport location; movement must reach the specified landing height.
The rendered capture returns to the already walked keep roof after all twelve
legs pass. This mode does not edit or load any draft and does not claim a fresh
draft reload. Add `--packaged-root artifacts/unreal/packages/Win64` to test the
packaged client. The default proof still covers the original city approach.

Verified locally on 2026-09-21: the earlier 8,712-placement editor-game default
launch, grounded walk, quest/station checks and fresh-process GM reload passed
at `artifacts/unreal/capital-proof/crownward-1790007084260/report.json`.
The saved draft measured 5,676,420 bytes. All 21 native foundation groups passed,
including a 10,000-object draft and legacy-format loading, at
`artifacts/unreal/editor/test-1790007041396-30036`. Offscreen city, avenue, castle,
courtyard and market views were produced; the city and avenue were inspected
after fixing wall spans, road lips and house height. Further visual acceptance
and complete interiors remain pending.

The private Windows Development package built successfully and passed the same
native default-launch/walk/gameplay/draft sequence outside the editor at
`artifacts/unreal/capital-proof/crownward-1790007424996/report.json`.
The package is under `artifacts/unreal/packages/Win64`. This packaged run used
NullRHI; the screenshots above are editor commandlet captures, not a packaged
rendering/performance claim. Tooling verification: 85 tests, nine Python tests
and TypeScript checks passed. The release check still reports four blocking
categories and all 39 full-parity contracts remain pending.

Packaged cloth correction (2026-09-21): an offscreen placement capture revealed
black market fabric in Windows while the editor rendered it pale. Recompiling
an unchanged copy of the authored material corrected the sampled Windows view
in `artifacts/unreal/capital-proof/crownward-1790009221819/`, which also passed all
14 placement, rejected-operation and fresh-process reload checks. The package
succeeded after AutomationTool recovered from a transient Zen cache-service
disconnect. No shader inputs or shading model were replaced. Five material
protection tests (`python tests/unrealCapitalMaterials.test.py`) and all nine
layout tests passed; a native commandlet verified the saved adaptation receipt.
Complete material and three-platform visual acceptance remain open.

Castle traversal correction (2026-09-21): reversed 24 imported stair modules
and opened the keep roof stairwell. The current map has 8,704 editable kit
placements. A colliding character walked both routes up and down in the editor
(`artifacts/unreal/capital-proof/crownward-1790011814371`) and rendered Windows
package (`artifacts/unreal/capital-proof/crownward-1790012050589`). No flight or
jump was used. The packaged default city approach, quest/station interactions,
GM edits and fresh-process draft reload also passed at
`artifacts/unreal/capital-proof/crownward-1790012096191`. Ten layout tests,
85 tooling tests and tooling typechecking passed. Other towers, interiors,
platforms and full visual acceptance remain unverified; release remains closed.

Capital gathering integration: the source herb patch and fertile soil node use
`aegis_flowerbed_violets`, preserving their IDs, source positions, yaw, scale,
profession, loot, radius and cooldown definitions. These are authored flowerbeds
with reconstructed source materials, not generated placeholder geometry. Use
the normal nearby interaction binding to gather. Low decorative beds have no
blocking collision. `capital_resources.py` rejects missing, duplicate, moved or
replaced source visual bindings; regeneration requires a current native import.
The build receipt lists the remaining water and relic nodes as pending. Their
legacy visuals are not silently substituted. Full asset approval and LOD review
remain open. Run `python tests/unrealCapitalResources.test.py` for binding checks.

Gathering verification (2026-09-21): editor-game interactions and city/GM reload
passed at `artifacts/unreal/capital-proof/crownward-1790012512431`. Each node was
checked nearby, outside its range, hidden, with a stale inventory revision and
on cooldown. Profession XP and node cooldown identity matched the source.
Offscreen editor captures `crownward-herb-patch.png` and
`crownward-soil-patch.png` under `artifacts/unreal/licensed-kits/` were inspected:
flowers, soil and stone borders are visible at both source sites. These captures
are not packaged rendering or performance acceptance. Three resource-binding
tests (including five invalid-binding cases), ten layout tests, 85 tooling tests
and tooling typechecking passed. Release admission still fails with four
blocking categories and 39 full-parity contracts pending.

The standalone Windows package also passed the gathering, city traversal,
quest/station and fresh-process GM reload sequence at
`artifacts/unreal/capital-proof/crownward-1790012814624`. This run used NullRHI;
only the editor gathering captures were visually reviewed. Ten import-preflight
and five material-protection tests also passed.

Purchased supply visuals: four source scrap/ore node identities now map to the
already staged `/Game/LicensedKits/Crownward/SM_Crate.SM_Crate`, retaining source
locations, yaw and gathering definitions. A uniform 2.5 multiplier on each
source visual scale fits the single purchased crate to the former supply-stack
footprint; it does not reintroduce the old generated box stack. The build
receipt records each exact native mesh path and scale. Runtime gathering
explicitly admits this crate in addition to imported repository models, while
engine fallback meshes remain rejected. The source-binding tests cover all six
nodes. The crate is decorative/nonblocking like the flowerbed nodes. These
placements do not add a merchant transaction system or GM resource editing.

Six-node verification: editor gathering/range/hidden/revision/cooldown/XP checks,
the grounded approach and fresh-process GM reload passed at
`artifacts/unreal/capital-proof/crownward-1790013015753`. The purchased crate's
native editor capture (`artifacts/unreal/licensed-kits/crownward-supplies.png`)
was inspected. All 21 native foundation groups passed at
`artifacts/unreal/editor/test-1790013129531-34112`, alongside 85 tooling tests,
tooling typechecking, four resource-binding tests and ten layout tests.

The six-node Windows package passed the same interaction/city/GM reload checks
at `artifacts/unreal/capital-proof/crownward-1790013219333`. Import binding
validation also rejects conflicting direct model filenames and non-finite or
boolean transform values, in addition to missing/replaced source profiles.

The two packaged Windows clients also passed the loopback UDP multiplayer
regression at `artifacts/unreal/network/1790013274409-4448/report.json`, including
inventory/crafting/gathering/progression and remote GM rejection. Its server is
an Unreal Editor dedicated process, not a packaged Linux server; Steam and
three-platform networking acceptance remain open. Release admission remains
closed with four blocker categories and all 39 full-parity contracts pending.

Expanded keep access (2026-09-21): all twelve walking legs passed in
`artifacts/unreal/capital-proof/crownward-1790014126478`. Each keep route starts
outside its entrance; the battlement route starts outside the curtain gate.
The four intermediate floors require ordinary walking onto their actual floor
surfaces and returning downstairs. This adds access evidence, not furniture,
tower stairs, doors, or complete interior acceptance.

The owner had Unreal Editor open; an Editor DLL rebuild failed with LNK1104.
The standalone Game target was then built with UAT `-skipbuildeditor -skipcook`
against the previously cooked city in an isolated archive,
`artifacts/unreal/packages/castle-access/Win64`. No working map was regenerated.
A newer owner save occurred during this work; its hash remains different from
the generation receipt and must be preserved. This proof therefore describes
the previous cooked geometry, not acceptance of the owner's latest map edits.
The editor DLL still needs rebuilding after it is released. Eleven layout tests,
85 tooling tests and tooling typechecking passed. Release remains closed.
