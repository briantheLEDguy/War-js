# Native capital GM workbench

The Aegis development workbench now has an in-game **City Builder**, opened with
`G`. Open `/Game/Capitals/aegis_capital/AegisCapital_Workbench` and use Play in
Editor. Standalone development launches additionally require `-WarDevelopmentGM`.
The map currently contains the authored terrain and 109 house placements, not
the complete capital. Ordinary shared servers and Shipping builds deny these
development GM operations. Trusted account-based multiplayer GM authorization
is still required for the production implementation.

The current panel can search/select existing houses, select the nearest one,
move along each world axis in one-meter increments, rotate in 15-degree steps,
scale uniformly, hide/restore, undo/redo, and save/load a local development draft.
Selected geometry has an intentional cyan editor guide. Hidden buildings also
stop blocking movement. Attached collision follows transform edits. Inventory,
quest and builder panels share modal input handling and restore movement/camera
input when closed.

Drafts are written to `unreal/AegisWar/Saved/WorldEdit/aegis_capital-draft.json`.
Use **Save draft** before leaving Play, then **Load draft** in the next session.
Loading is undoable. An existing draft must be loaded before it can be overwritten.
The save checks for external changes, uses a writer lock and replaces through a
temporary file. This is local development persistence, not shared publication.
The original imported map packages are not modified by runtime editing.

Each request carries the expected revision. Invalid identities, stale requests,
non-finite/unbounded transforms, zero scale and changes to model handedness are
rejected. Undo retains up to 100 prior states. Drafts include the original object
layout and source model fingerprints; a different authored world revision is
rejected rather than silently overwriting it. Reconciliation of drafts after
new baseline imports remains pending. Keep existing draft files when updating
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
hide/restore, stale requests, undo/redo, draft reload, rejection of corrupted or
externally changed drafts, and panel input restoration. Its draft lives in a
unique `Saved/WorldEditProof/` directory, separate from user work. Inspect the
generated screenshot; a success receipt alone is not visual acceptance.

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

Still pending: adding new buildings from the catalog, arbitrary/drag transforms,
terrain sculpt/paint, runtime walkable-surface authoring, GM flight/teleport and
character tools, shared permissions and replication, durable shared drafts,
publication/version restore, remaining capital content, and Riftspire. Existing
browser GM behavior remains the parity reference. This development panel does
not satisfy the full GM migration gate.
