# Native movement input

The native development character supports camera-relative WASD movement,
Space jumping, NumLock autorun and forward movement while both mouse buttons
are held. Autorun cancels on any movement key, including opposing keys that sum
to zero. Keyboard axes use Enhanced Input's cumulative mode so W/S and A/D
cancel each other. Combined keyboard/mouse intent is normalized before entering
CharacterMovement, preserving the browser's direction without faster diagonals.

Inventory and quest modals block movement and prevent autorun toggles. Existing
autorun pauses while blocked and resumes when the modal closes, matching the
browser's retained toggle state. Death and flying mode clear autorun. The toggle
is local input state; standard CharacterMovement prediction and server movement
validation remain authoritative. No client position RPC was added.

`WarMovementInput` contains the input-combination rules, with native tests for
manual cancellation, opposing keys, simultaneous mouse/keyboard direction,
speed normalization, modal pause/resume, death/flying reset and invalid axes.
The loopback proof drives its actual autonomous character through autorun and
requires independently observed server/remote movement. Modal toggling is also
checked against the live character when `--quest-ui` is used.
Both clients acknowledge loaded character content before the opt-in proof starts,
so a slower client cannot miss the movement phase. The readiness RPCs are inert
without that development-only subsystem and do not change production admission.

Verification on 2026-09-21: 19 native Foundation groups passed in
`artifacts/unreal/editor/test-1789984559127-20436/`, with 75 tooling tests and tools
typecheck passing. The synchronized rendered Editor proof passed in
`artifacts/unreal/network/1789984908882-2952/report.json`; the Windows package and
rendered packaged-client proof passed in
`artifacts/unreal/network/1789985186109-10540/report.json`. The Aegis screenshot
was inspected. Physical keyboard/mouse verification remains open.

This is incomplete movement parity. Touch controls, rebinding/conflict UI,
right-button facing details, jump/gravity tuning, gameplay control effects,
campaign slopes/stairs/lifts and WAN/platform validation remain open. The
existing proof scene and default bindings do not establish those behaviors.
