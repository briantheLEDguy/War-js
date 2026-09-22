# Native login and character setup

Ordinary `WarGameMode` startup opens `WarFrontendWidget` through the owning
`WarPlayerController` and waits without spawning a pawn. The existing capital
remains the editor/game default; its map bytes are unchanged.

Screens provide Steam sign-in status, development character setup, and a review
with name, race, career, body, realm and intended capital. All six races, 24
original careers and both bodies are listed. Names accept 3-24 characters with
at least three letters, plus spaces, apostrophes and hyphens. Changing race resets
the career to that race's first valid career.

The shared Slate presentation uses a gold-framed midnight panel, ivory headings,
three entry-step indicators and distinct primary/secondary controls. Persistent
styles own field and button brushes, including hover, pressed and focus states.
A downscaling frame and scrollable content keep the form within smaller windows.

Steam authentication, persistent account characters, multiple character slots
and rendered character previews remain unimplemented. The Steam button reports
the unavailable service; it does not fabricate a login. Development setup is
non-Shipping standalone only, not an offline product mode. Drafts are explicitly
session-only and are not saved to disk.

`WarPlayerControllerFrontend.cpp` validates creation on authority, matches the
exact race/career/body against configured native visuals and checks provenance
through `WarContentSubsystem`. Empire / Battle Prelate / Male uses the recovered
body, armor and hammer assembly to enter the configured Aegis capital. Playable
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
