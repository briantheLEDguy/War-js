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

There are 8,712 editable placements using 14 kit mesh types. Ground, roads and
mountains are terrain construction, not primitive scenery substitutes. The
source city and its old workbench remain available for reference. This restores
the source geography and house sites; it does not establish complete parity for
public buildings, every interior, mountain passages, encounters or travel.

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

Verified locally on 2026-09-21: the final 8,712-placement editor-game default
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
