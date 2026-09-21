# Native capital GM workbench

The Aegis development workbench now has an in-game **City Builder**, opened with
`G`. Open `/Game/Capitals/aegis_capital/AegisCapital_Workbench` and use Play in
Editor. Standalone development launches additionally require `-WarDevelopmentGM`.
The map currently contains the authored terrain and 145 residential placements, not
the complete capital. Ordinary shared servers and Shipping builds deny these
development GM operations. Trusted account-based multiplayer GM authorization
is still required for the production implementation.

The current panel can place six house and two rowhouse models, search/select houses, select the nearest one,
move along each world axis in one-meter increments, rotate in 15-degree steps,
scale uniformly, hide/restore, undo/redo, and save/load a local development draft.
Selected geometry has an intentional cyan editor guide. Hidden buildings also
stop blocking movement. Attached collision follows transform edits. Inventory,
quest and builder panels share modal input handling and restore movement/camera
input when closed.

The development panel also exposes **Fly / walk**, **Arrival**, and speed controls
from 0.25x to 6x. Close the panel to fly with normal horizontal movement and
`E` up / `Q` down. Flight bypasses collision for city inspection. Returning to
walking inside blocking geometry is rejected; move into clear space first.
Arrival returns to an unobstructed capital spawn. Traversal settings belong to
the current pawn and reset when it is replaced. These controls remain restricted
to the local development capital; they are not production multiplayer GM access.

Already purchased modular kits may expand the catalog after installation and
review. See [the integration path](unreal-modular-kits.md). No purchased kit is
currently admitted, and grid/pivot snapping is still pending.

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

Still pending: the remaining building/prefab catalog, arbitrary/drag transforms,
terrain sculpt/paint, runtime walkable-surface authoring, production GM flight,
arbitrary zone/coordinate/character teleport and character tools, shared permissions and replication, durable shared drafts,
publication/version restore, remaining capital content, and Riftspire. Existing
browser GM behavior remains the parity reference. This development panel does
not satisfy the full GM migration gate.
