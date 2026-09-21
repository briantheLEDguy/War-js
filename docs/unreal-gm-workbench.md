# Native capital GM workbench

The editor and development game now start in the [integrated kit capital](unreal-crownward.md)
inside AegisWar, with 8,712 editable placements and 14 kit catalog models. It
preserves the original mountain geography, districts and house sites, and adds
native dispatch/crafting actors. Its draft is `Saved/WorldEdit/crownward-draft.json`.
The reference workbench below retains its original content and separate draft.
CityKitStaging is only an asset-import workspace. These development checks do
not establish complete campaign, interior or shared multiplayer acceptance.

The Aegis development workbench now has an in-game **City Builder**, opened with
`G`. Open `/Game/Capitals/aegis_capital/AegisCapital_Workbench` and use Play in
Editor. Standalone development launches additionally require `-WarDevelopmentGM`.
The map currently contains the authored terrain and 145 residences plus 157 walls, not
the complete capital. Ordinary shared servers and Shipping builds deny these
development GM operations. Trusted account-based multiplayer GM authorization
is still required for the production implementation.

The current panel can place six house, two rowhouse and one wall model, search/select houses, select the nearest one,
move along each world axis in adjustable increments, rotate in adjustable steps,
scale uniformly or enter exact transforms, hide/restore, undo/redo, and save/load a local development draft.
With the panel open, click a building outside the panel to select it directly.
Selection traces the first blocking authored collision volume, ignores your own
pawn, and resolves only registered editable identities. Terrain and other
blocking objects occlude selection; hidden buildings remain selectable through
the list. A miss retains the existing selection. This currently selects by
authored collision rather than exact visible mesh triangles.

Selected geometry has an intentional cyan editor guide. Hidden buildings also
stop blocking movement. Attached collision follows transform edits. Inventory,
quest and builder panels share modal input handling and restore movement/camera
input when closed.

The model catalog and placed-object list have separate search fields. Model
search ignores case, matches every entered word, and reports matching/total
models. A bounded scroll area keeps a growing catalog from consuming the rest
of the panel, and model labels wrap. Repeated map placements share one model
entry with a stable authored template identity; created objects do not add
duplicate catalog entries. The reference map has nine house/rowhouse/wall models;
the integrated Crownward map has 14 kit models. Searching does not admit missing
or unreviewed additional kit assets.

The development panel also exposes **Fly / walk**, **Arrival**, and speed controls
from 0.25x to 6x. Close the panel to fly with normal horizontal movement and
`E` up / `Q` down. Flight bypasses collision for city inspection. Returning to
walking inside blocking geometry is rejected; move into clear space first.
Arrival returns to an unobstructed capital spawn. Traversal settings belong to
the current pawn and reset when it is replaced. These controls remain restricted
to the local development capital; they are not production multiplayer GM access.

Already purchased modular kits may expand the catalog after installation and
review. See [the integration path](unreal-modular-kits.md). Purchased kit meshes
are available in the separate pilot and Crownward maps. Bounds-aware surface
placement handles offset import origins; kit socket/assembly alignment remains pending.

**Grid step** cycles off, 10 cm, 50 cm, 1 m and 2 m. **Turn step** cycles 15°, 45°
and 90°. Axis nudges use the chosen grid distance (1 m when off). **Snap XY / yaw**
aligns the selected object's pivot to the world grid and chosen turn increment;
it preserves height, pitch/roll and scale, including mirrored models. This is an
undoable edit. New placements target 20 metres ahead of the character. The server
snaps that target horizontally, traces authored collision and aligns the rotated
mesh bounds centre in XY and lowest bound in Z to the hit. An offset imported
pivot therefore no longer buries or displaces the model. Yaw snaps when the grid
is enabled; grid-off placement preserves template orientation. Settings last for
the widget session; drafts store final transforms.

**Drop to surface** lowers the selected visible model onto collision beneath its
bounds centre, ignoring itself and the character. It preserves rotation and
scale, including mirrored axes, and supports undo/redo and draft reload. Its trace
starts at the model bottom so overhead floors cannot pull it upstairs. Raise a
buried object before dropping it. No support, missing models, hidden objects or
stale revisions produce an error without changing the draft. This aligns a
bounding box to one support point; whole-footprint slope fitting, sockets, drag
gizmos and kit-specific assembly snapping remain unfinished.

**Repeated construction** places 2-32 copies of the selected model, starting
20 metres ahead. Choose local X or Y and an additional gap from 0 to 100 metres.
Copies retain the selection's rotation and scale, including mirrored axes. The
server uses the oriented model width for spacing, snaps only the row origin to
the chosen grid, and places each piece on its own collision support point.
Every surface and transform must succeed before any piece appears. The entire
row is one undo/redo step; its individual authored identities survive draft
save/reload and remain individually editable. Existing object/collision overlap
is not rejected, and footprint fitting, socket joins, group transforms and drag
chain previews remain pending. Development GM authorization still applies.

**Exact transform** expands nine numeric fields: X/Y/Z in metres, pitch/yaw/roll
in degrees, and per-axis scale magnitudes. Press Enter to commit one field as an
undoable revision; changing focus does not submit unfinished text. Position is
bounded to +/-1000 m, rotation to +/-360 degrees, and scale to 0.05-20. Scale
magnitudes preserve imported mirrored axes. Invalid values leave the world
unchanged and show a range message. These fields bypass grid snapping so exact
values remain exact; attached collision follows every accepted edit.

The house buttons place an authored model about 20 meters in front of the
character, on the first blocking surface below that point. Use the transform
controls to adjust the result; overlapping placements are currently allowed.
Creation copies the trusted model and its authored collision, never a primitive
fallback. Undo removes the created actor, and redo reconstructs it. Up to 1,000
new objects may be retained in a draft. Version-two drafts store template IDs;
version-one edit-only drafts remain readable. A fresh game process reconstructs
created objects when loading the draft. Failed model resolution leaves the
current document unchanged.

Drafts are written to `unreal/AegisWar/Saved/WorldEdit/aegis_capital-draft.json`.
Use **Save draft** before leaving Play, then **Load draft** in the next session.
Loading is undoable. An existing draft must be loaded before it can be overwritten.
The save checks for external changes, uses a writer lock and replaces through a
temporary file. This is local development persistence, not shared publication.
The original imported map packages are not modified by runtime editing.

Each request carries the expected revision. Invalid identities, stale requests,
non-finite/unbounded transforms, zero scale and changes to model handedness are
rejected. Undo retains up to 100 prior states. Drafts include the original object
layout and source model fingerprints. If an import only adds authored objects,
older drafts retain those additions alongside saved edits and created buildings.
The load message reports how many new authored objects were retained. Saving
again records the expanded baseline. If an original object was removed, moved,
rescaled, hidden or assigned a different source model, loading rejects the
conflict without changing the current world. Conflict resolution for those
non-additive updates remains pending. Keep existing draft files when updating
the imported map.

Implementation is split between `WarWorldEditHistory` (validated transactions,
history and draft serialization), `WarWorldEditSubsystem` (session authorization,
actors/collision and file persistence), controller server commands, and
`WarWorldEditWidget` (native in-game controls). Imported buildings carry explicit
world-object IDs; identity does not depend on a naming convention. This includes
the eleven infill houses whose IDs differ from the main city house prefix.

## Verification and remaining work

`npm run unreal:capital-proof -- --rendered` launches a real development game in
the capital and checks grounded movement, GM commands, collision attachment,
hide/restore, construction, stale requests, undo/redo, draft reload, rejection of corrupted or
externally changed drafts, and panel input restoration. Its draft lives in a
unique `Saved/WorldEditProof/` directory, separate from user work. Inspect the
generated screenshot; a success receipt alone is not visual acceptance. A second
game process restores the construction draft and verifies the actual mesh,
transform and blocking collision.

The live workflow passed on Windows, and its readable UI, authored character,
terrain and buildings were inspected after correcting playable daylight exposure.
Native foundation tests include world-edit transactions and draft compatibility.
Full capital/world acceptance remains false.

The Windows Development package also includes the capital when built with
`npm run unreal:package-proof -- --include-capital`. Run its acceptance with
`npm run unreal:capital-proof -- --packaged-root artifacts/unreal/packages/Win64 --rendered`.
For a manual development session, launch
`artifacts/unreal/packages/Win64/AegisWar/Binaries/Win64/AegisWar.exe` with
`/Game/Capitals/aegis_capital/AegisCapital_Workbench -WarDevelopmentGM`, then press
`G`. The package's local draft is under its own `AegisWar/Saved/WorldEdit/`.

Verified on 2026-09-21: 20 native foundation tests, 82 tooling tests and tools
typechecking; rendered editor capital proof
`artifacts/unreal/capital-proof/1789988603741-26392/`; Windows packaging and
rendered packaged capital proof `artifacts/unreal/capital-proof/1789988929168-16520/`;
rendered two-client checks with editor clients and packaged clients (latest:
`artifacts/unreal/network/1789988935779-37400/report.json`). Both remote clients
received rejection for a GM history command. The packaged screenshot was inspected;
window emission differs from the editor and remains a rendering investigation.
The release check still fails with four blocker categories.

Construction verification: native foundation run
`artifacts/unreal/editor/test-1789989737916-6992/` passed all 20 groups;
82 tooling tests and tools typechecking passed. Rendered editor construction and
fresh-process reload passed in `artifacts/unreal/capital-proof/1789989759300-35220/`.
Windows packaging succeeded, and the packaged equivalent passed in
`artifacts/unreal/capital-proof/1789990022385-17756/`. The packaged catalog was
visually inspected after correcting clipped labels into two rows. The earlier
window-emission difference was not reproduced in this rebuilt package; the
current sampled view matches the editor. This does not close full material or
capital visual acceptance.

The packaged two-client run
`artifacts/unreal/network/1789990034513-21024/report.json` also rejected remote
building creation for both clients. A visible packaged-game UI check opened `G`,
clicked each of the six house buttons, observed the corresponding rendered
building and used Undo after each placement. No user draft was saved or changed.

Additive-import compatibility passed all 20 native groups in
`artifacts/unreal/editor/test-1789990593107-37080/`, including legacy drafts,
construction, undo, resaving the expanded baseline, and changed/removed model
conflicts. The real capital proof uses an isolated earlier-baseline fixture,
then checks that its omitted newly imported building and GM creation coexist
after loading. This passed in the editor
(`artifacts/unreal/capital-proof/1789990652567-34144/`) and rebuilt Windows package
(`artifacts/unreal/capital-proof/1789990788698-28456/`), including a separate
reload process. Tooling tests (82) and typechecking also passed. A complete
production world-version migration system is still pending.

Development traversal verification (2026-09-21): all 20 native test groups passed
in `artifacts/unreal/editor/test-1789992290676-35192/`; 83 tooling tests and tools
typechecking passed. Rendered flight, bounded speed, blocked flight exit,
arrival return, grounded recovery and construction/draft checks passed in the
editor (`artifacts/unreal/capital-proof/1789992105708-30424/`) and rebuilt Windows
package (`artifacts/unreal/capital-proof/1789992447438-30408/`). The packaged panel
was visually inspected after shortening its clipped return label to Arrival.
The two editor clients rejected flight and return RPCs in
`artifacts/unreal/network/1789992164276-35120/report.json`; the equivalent packaged
Windows clients also passed in `artifacts/unreal/network/1789992482863-33204/report.json`.
Automated vertical
flight uses movement input directly; physical E/Q keyboard operation has not yet
been separately inspected. Full GM and capital acceptance remain false.

Grid/yaw alignment verification (2026-09-21): all 20 native groups passed in
`artifacts/unreal/editor/test-1789992764729-13288/`, including negative half-grid
rounding, disabled settings, preserved height, pitch/roll and mirrored scale.
Rendered capital alignment, attached collision and undo passed in the editor
(`artifacts/unreal/capital-proof/1789993021093-37620/`) and corrected Windows
package (`artifacts/unreal/capital-proof/1789993891299-24888/`), alongside traversal
and fresh-process draft reload. Visual inspection caught a collapsed selection
list; the panel now sizes to viewport height, and the rebuilt panel shows both
the scrollable list and all controls. Tooling tests (83) and typechecking passed.
This is world-grid alignment, not verification of any purchased modular kit.

Catalog regression verification (2026-09-21): the expanded native suite passed
21 groups in `artifacts/unreal/editor/test-1789994550555-35736/`, including
stable model deduplication, multi-word/case-insensitive search and rejection of
created objects as new templates. The tooling receipt checker now requires this
new group; 83 tooling tests and typechecking passed. Real-map catalog checks and
the rendered editor panel passed in
`artifacts/unreal/capital-proof/1789994608917-34060/`. The rebuilt Windows
package passed construction and fresh-process reload in
`artifacts/unreal/capital-proof/1789994769215-23916/`. A manual packaged UI check
searched for `ROWHOUSE 2`, observed one of eight models, placed the rendered
rowhouse and undid it. The filter persisted through both edits; no user draft
was saved or loaded.

Exact transform verification (2026-09-21): all 21 native groups passed in
`artifacts/unreal/editor/test-1789995260984-27264/`, including unit conversion,
rotation axes, nonuniform mirrored scale, invalid-value rejection and undo.
Rendered editor checks in `artifacts/unreal/capital-proof/1789995312656-37688/`
verified actual actor/collision transforms and draft reload. The Windows package
passed the same checks in `artifacts/unreal/capital-proof/1789995472004-36740/`.
A manual packaged UI check entered a height of 1.234 m, observed the rendered
building rise, then used Undo to restore ground height and the displayed value.
No user draft was saved or loaded. Tooling tests (83) and tools typechecking
passed. Visual review also prompted larger numeric-field and section labels.
The corrected package (`artifacts/unreal/package-gm-exact-labels.log`) was
inspected with all nine fields expanded. Entering zero scale restored the
original displayed value and showed the range error without changing the world.

World selection verification (2026-09-21): 21 native groups passed in
`artifacts/unreal/editor/test-1789996582242-24316/`; 83 tooling tests and tools
typechecking passed. Rendered selection checks passed in the editor
(`artifacts/unreal/capital-proof/1789996633233-36152/`) and Windows package
(`artifacts/unreal/capital-proof/1789996479121-28456/`), including terrain
occlusion, invalid/access-denied rays, hidden/restored objects and draft reload.
The terrain fixture uses a buried building at the clear arrival location,
separate from authored foundations that extend below the ground. The final
package also passed two-client regression in
`artifacts/unreal/network/1789996756616-32744/report.json`. Manual mouse checks
selected a visible building, retained it on a ground click, raised it through
the panel and undid that edit. No user draft was saved or loaded.

Surface placement verification (2026-09-21): all 21 native groups passed in
`artifacts/unreal/editor/test-1790008362211-11092/`, including offset origins,
rotated/nonuniform mirrored bounds and invalid geometry/hits. The rendered
integrated-city run `artifacts/unreal/capital-proof/crownward-1790008410332/`
placed all 14 kit models with matching native bounds/collision and reloaded its
isolated draft in a fresh process; the panel screenshot was inspected. Additional
hidden/no-support rejection checks passed in
`artifacts/unreal/capital-proof/crownward-1790008568769/`. Two editor clients
rejected both new surface RPCs in
`artifacts/unreal/network/1790008598461-6024/report.json`. No owner draft changed.
Tooling tests (85), tools typechecking and the audit passed; release admission
remains closed with four blocker categories. Physical button interaction and
whole-footprint slope fitting are not established by these checks.

The rebuilt private Windows package passed all 14 surface placements, rejection
cases and fresh-process reload in
`artifacts/unreal/capital-proof/crownward-1790008838579/`; packaged clients rejected
the new commands in `artifacts/unreal/network/1790008861148-18884/report.json`.
The offscreen packaged panel was inspected. That capture exposed black
market-stall fabric versus pale fabric in the editor. A recompiled private copy
of the unchanged authored material corrected the sampled packaged view in
`artifacts/unreal/capital-proof/crownward-1790009221819/`; all placement/reload
checks still passed. Full kit material and platform review remain unresolved.

Repeated construction verification (2026-09-21): 21 native groups passed in
`artifacts/unreal/editor/test-1790010873665-8176/`, including oriented spacing,
mirrored scale and atomic history failures. The real capital row proof passed
in `artifacts/unreal/capital-proof/crownward-1790010980788/`; the rebuilt Windows
package passed row creation, undo/redo and fresh reload in
`artifacts/unreal/capital-proof/crownward-1790011271544/`. Its expanded controls
and reload screenshot were inspected. Existing single-model surface placement
passed in `artifacts/unreal/capital-proof/crownward-1790011286958/`. Two editor
clients (`artifacts/unreal/network/1790011011585-35068/report.json`) and packaged
clients (`artifacts/unreal/network/1790011300641-18212/report.json`) rejected the
row RPC. Tooling tests (85), typechecking and audit passed; release admission
remains closed. These use isolated proof drafts and leave the owner's draft intact.
The final packaged capture (`artifacts/unreal/capital-proof/crownward-1790011504055/`)
adds render warm-up after recreation, showing all three pieces and the expanded
controls after undo/redo, as well as after reload. Physical mouse interaction
with the new controls remains untested during background-only work.

Still pending: the remaining building/prefab catalog, drag transforms,
terrain sculpt/paint, runtime walkable-surface authoring, production GM flight,
arbitrary zone/coordinate/character teleport and character tools, shared permissions and replication, durable shared drafts,
publication/version restore, remaining capital content, and Riftspire. Existing
browser GM behavior remains the parity reference. This development panel does
not satisfy the full GM migration gate.
