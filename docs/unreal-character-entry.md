# Native login and character setup

Ordinary `WarGameMode` startup opens `WarFrontendWidget` through the owning
`WarPlayerController` and waits without spawning a pawn. The existing capital
remains the editor/game default; its map bytes are unchanged.

Screens provide Steam sign-in status, development character setup, and a review
with name, race, career, body, realm and intended capital. The current installed
roster exposes male Empire Battle Prelate, Sunfire Templar and Ember Arcanist,
and male Greenskin Warbrute. Names accept 3-24 characters with
at least three letters, plus spaces, apostrophes and hyphens. Changing race resets
the career to that race's first valid career.

The Slate presentation uses a translucent midnight panel on the left, ivory
headings, three entry-step indicators and distinct primary/secondary controls.
Persistent styles own field and button brushes, including hover, pressed and
focus states. A scaling frame and scrollable content keep smaller windows usable.

Steam authentication, persistent account characters and multiple character slots
remain unimplemented. The Steam button reports
the unavailable service; it does not fabricate a login. Development setup is
non-Shipping standalone only, not an offline product mode. Drafts are explicitly
session-only and are not saved to disk.

`WarPlayerControllerFrontend.cpp` validates creation on authority, matches the
exact race/career/body against configured native visuals and checks provenance
through `WarContentSubsystem`. Installed male Empire Battle Prelate, Sunfire
Templar and Ember Arcanist profiles enter the configured Aegis capital. Playable
visuals reject NPC/different-profile source substitutions. See
`docs/unreal-battle-prelate-recovery.md`. Other selections return recoverable errors. Riftbound
entry remains blocked until its capital flow exists. The controller retains the
selected visual for respawns; gameplay state stays on PlayerState. Existing
development combat/progression limits still apply.

Character entry is asynchronous: the controller retains the validated visual and
marks entry pending before `RestartPlayer`. The review shows "Loading starting city..."
and disables entry/edit/back buttons while `WarGameMode` waits for zone readiness.
`FinishRestartPlayer` completes entry only after possession. `RecordEntryFailure`
releases pending state and preserves the actual error for retry. A missing pawn
immediately after requesting a restart is not evidence of a collision failure.
Repeated submissions during loading do nothing; after possession they resume the
existing session. Network/build admission checks remain separate from pawn state.
Zone readiness excludes the level's default editor builder brush, whose lack of
a runtime physics body previously kept entry pending until timeout. Authored
blocking volumes and arrival-floor traces remain required. A timeout logs the
specific missing level, collision component, equipment or arrival floor.

Explicit `WarNetworkProof`, `WarCapitalProof`, `WarInterfaceProof` and `WarCityPopulationProof`
non-Shipping fixtures keep direct entry. Production admission remains closed;
no model approval or release gate changes.

Run `npm run unreal:build -- --target Editor`, `npm run unreal:test-native`,
`npm run test:unreal`, `npm run typecheck:unreal-tools` and `npm run unreal:audit`.
`AegisWar.Foundation.CharacterFrontend` checks names, no-spawn startup, delayed
restart/possession, duplicate submissions, failure/retry and missing-start reporting.

Manual verification: launch, inspect login, open development setup, check
race-dependent careers and invalid-name feedback, review a named default
character, return to edit, and enter the city. Try an unavailable model and confirm
the review remains usable. Compilation and runtime evidence must be reported
separately from source/tooling checks.

Verified on Windows with Unreal 5.8.2: Editor build, all 24 native foundation
tests (including CharacterFrontend), 87 Unreal tooling tests, tooling typecheck
and migration audit. The earlier interactive setup/review used a named Female draft backed by an
herbalist NPC; that substitution has been retired. Recovery validation is
recorded separately in `docs/unreal-battle-prelate-recovery.md`. Steam,
packaged builds, Linux/macOS and full roster entry are not accepted by these checks.

September 22 asynchronous-entry fix: all 94 tooling tests, the report-validator
recheck, tooling typecheck and migration audit passed (release blockers remain).
After the editor/game closed, the Editor rebuild succeeded and all 35 native
foundation tests passed, including delayed entry/possession and failure/retry.
`scripts/unreal/verify-character-entry.py` provides an additional capital-map PIE
check through the normal creation RPC. Run it with a fresh editor using `-nullrhi
-ExecutePythonScript=<absolute script path>` and standalone, one-client play settings;
inspect `artifacts/unreal/character-entry/runtime.json`, not just the exit code.

The final capital PIE check passed: the ordinary creation RPC possessed the
equipped `PrelateTwoHanded` mesh, removed the frontend, and retained the character
on the floor at approximately (-11800, 0, 101.15) cm. The same fresh-map check read
back sun priority 1 and fill priority 0. This headless check verifies entry and
saved settings; it is not visual animation or lighting approval.

September 24 arrival-content repair: a gameplay export changed `content.json`'s
source fingerprint without updating the reviewed `world-visuals.json` catalog.
The three Aegis training targets consequently failed validation, and zone readiness
blocked every installed Aegis character with the generic arrival timeout.

`scripts/unreal/stage-content.ts`, called by `npm run unreal:stage`, now carries
the existing reviewed bindings forward only when their source maps are unchanged
and every recorded source-model and native-package hash still matches. It preserves
binding identity, mesh, ordered materials, collision and development-only status.
Changed assets or a catalog already stale against the installed manifest stop
staging before either live catalog is replaced; they require explicit review.
No runtime readiness or missing-model gate is relaxed. Restart the play session
after repairing/staging content because the subsystem loads catalogs at startup.

For an arrival timeout, inspect `Saved/Logs` for `Arrival readiness timeout` and
`WAR_ENEMY_CONTENT_BLOCKED`; repeated entry attempts cannot repair an invalid catalog.
The local repair preserved 26 bindings, checked 36 native packages and matched
all four bound map sources against the authored world-plan receipt. Its evidence
is in `artifacts/unreal/character-entry/catalog-repair.json`, with the original
catalog retained beside it.

Set `WAR_ENTRY_CAREER` to `battle_prelate`, `sunfire_templar` or `ember_arcanist`
before running `verify-character-entry.py` in a fresh headless editor. Each run
writes `artifacts/unreal/character-entry/runtime-<career>.json`, verifies the exact
equipped mesh, possession, frontend removal and a stable arrival floor. Without
the variable it retains the original Battle Prelate check and `runtime.json` path.

Windows verification for this repair: all three career entry receipts passed in
Unreal 5.8.2 with the expected equipped mesh and arrival at (-11800, 0, 101.15) cm.
The installed native foundation suite passed 54 tests; `npm test` passed 649,
including the 12 new staging cases. The Unreal tooling subset passed 124 tests;
all three typechecks, migration audit, world and model validation passed.
The release check still fails on the existing four acceptance blockers. These
headless checks establish local entry, not graphical, Steam or platform acceptance.

## Cinematic frontend

The login, developer-account, creation and review pages use the supplied
`aegislogo.png`, `button.png` and `window.png` from `unreal/AegisWar/graphics-new`.
Run `scripts/unreal/import-frontend-artwork.py` with the Unreal Python commandlet
to generate private textures/materials under `/Game/UI/Frontend/Artwork` (covered
by the existing frontend cook directory). Original PNG bytes are preserved.
UI materials crop transparent margins and render the art in bronze, removing
its original blue tones. Inputs, dropdown selection, buttons and the translucent
portrait backing use matching warm colors. The importer rejects unexpected
canvas dimensions and assets it does not own. Its hash receipt is written to
`artifacts/unreal/frontend/artwork.json`; the frontend proof requires all three
artwork resources to be installed.

Artwork verification: Windows Editor build, 58 native tests (including installed
UI material/texture checks), 660 shared tests, 126 Unreal tooling tests, all three
typechecks, migration audit, world and model validation passed. Rendered login
and creation screens were inspected for the logo, bronze ornamentation, readable
labels and retained portrait backing. All three supplied PNG hashes still match
the import receipt. This is development UI evidence, not release acceptance.

`WarFrontendWidget` owns the Slate layout and a `WarFrontendPresentation` object.
The presentation owns two `FPreviewScene` city worlds and a separate character
world. These worlds have no physics, navigation, audio, campaign actors, player
pawns or replicated authority. Capital scenery is grouped into instanced static
meshes; the source actor classes and their behaviors are never copied.

The private `/Game/UI/Frontend/CapitalPresentation` data asset contains two camera
views per capital, source-derived geometry/material references and presentation
lighting. Views alternate Aegis/Riftspire with 18-second holds and 3-second
crossfades. Captures are capped at 30 Hz and 1600×900 per city; only transitions
need both city captures. The portrait target is 800×1000. Camera transforms and
explicit exposure prevent gameplay camera state from affecting the menu.

Initial login shows cities alone. Setup reveals the selected draft using the
same playable definition and provenance checks as authoritative entry. Its
approved idle, materials, weapon/shield grips and caster stowed bindings are
retained. Previewing never creates a gameplay character or authorizes entry.
Drag the portrait to rotate; focused portraits also accept Left/Right and Home.
The portrait has a rounded translucent dark backdrop and faint gold border to
separate its silhouette from the city without hiding the background completely.
Reduced motion freezes the current city composition and character pose. Settings
and the draft last for this frontend session; account persistence is unchanged.

Selections cancel older loads and invalidate stale callbacks. Missing character
content clears the old preview and displays a retryable error. Missing capital
content exposes retry without replacing it with primitive geometry. Hidden or
minimized frontends stop captures; removing the frontend releases preview worlds,
targets and asynchronous handles. Scene packages and material adaptations remain
private under ignored native Content paths, preserving existing license gates.

`npm run unreal:build -- --target Editor` refreshes stale frontend content after
compilation when a private world is installed. `npm run unreal:frontend-proof`
also refreshes before capturing evidence. After saving city edits, close the
Editor/game and run `npm run unreal:frontend-refresh` before reopening the game.
Use `-- --check` for a read-only freshness check. Unsaved edits and live server
state are not reflected in these saved scenery snapshots.

`frontend_sources.py` resolves the manifest named by the active world build,
requires its map to match `GameDefaultMap`, and selects every layer for both
capitals, including architecture and population. The Aegis persistent shell is
also retained; extraction filters actors by owning package to avoid duplicates.
`frontend-content.ts` checks recipe/routing, source-package and output hashes,
then invokes `build-frontend-presentation.py` only when stale. The builder saves
only owned frontend assets, checks that source packages/routing stayed unchanged,
and records schema-2 evidence in `artifacts/unreal/frontend/build.json`.
Material adaptations enable instancing on private copies, preserving originals.

The 2026-09-29 refresh includes 10,060 Aegis and 7,594 Riftspire scenery instances,
including the active Dutch Bastion geometry. Source package hashes remained
unchanged. The 1920x1080 frontend proof passed and both capital screenshots were
inspected at `artifacts/unreal/frontend/1920x1080-1153ae8e-b103-4042-a096-6f507e0b440c/`.
All 704 repository tests (including 139 Unreal tooling tests and six Python
snapshot regression cases), typechecks, migration audit and world/model
validation passed. The release check retains its four independent blockers.

`AegisWar.Foundation.FrontendPresentation` covers camera validation, transition
timing, reduced motion, selection invalidation and resource release.
`npm run unreal:frontend-proof` follows ordinary no-pawn startup offscreen,
exercises the four installed profiles and produces screenshots plus timing and
process-memory evidence under `artifacts/unreal/frontend/`. Pass
`-- --width 1280 --height 720` or `-- --width 2560 --height 1080` for layout checks.
Proof success is behavioral evidence; inspect the rendered images separately.
This work does not establish packaged, Steam, Linux/macOS or full-roster approval.

Windows verification on 2026-09-25: the Editor build and all 56 native foundation
tests passed, including `FrontendPresentation` and `CharacterFrontend`. The
frontend proof passed at 1280x720, 1920x1080 and 2560x1080, with rendered portraits inspected
for equipment framing and the translucent backdrop. The source-package check
confirmed all 408 recorded packages were unchanged. Shared tests, Unreal tooling
tests, typechecks, migration audit, world and model validation also passed; the
release check still correctly fails on the four outstanding acceptance gates.
