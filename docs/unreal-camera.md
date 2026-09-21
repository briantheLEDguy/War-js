# Native camera controls

`WarCameraRules` preserves the browser camera's seven-metre outdoor starting
distance, 3–14 metre outdoor zoom, 1.65–3.8 metre indoor zoom, 2.2 metre indoor
entry distance, pitch limits and indoor/outdoor view restoration. Re-entering
the same mode does not overwrite the saved outdoor state. Sensitivities retain
the source's 0.25–3 range and invalid-input rejection prevents a non-finite view.

`WarCharacter` connects mouse-wheel zoom and either mouse-button drag to Enhanced
Input. Orbit uses the source's angular sensitivity magnitudes; the adapter
accounts for Unreal's upward-positive mouse Y. A native wheel notch corresponds
to a conventional 100-pixel browser wheel step. Hardware-specific input and
high-resolution trackpad acceptance remain open.

The native spring arm retains collision testing, with a 35 cm probe and a focus
90 cm above the character's feet. This is an engine collision implementation;
city/terrain/camera-obstruction parity still needs the imported world and runtime
checks. Camera state lives on the owning player controller, survives pawn
replacement and drives its follow-camera rotation. Other players do not receive
these preferences. Inventory/quest modal panels block zoom and orbit.

`SetCameraIndoorMode` and `SetCameraPreferences` are local integration hooks.
No campaign interiors currently invoke the indoor hook, and preferences are not
yet persisted to disk or exposed in a settings panel. Touch orbit/pinch, binding
remapping, full camera/UI behavior and three-platform hardware acceptance remain
unfinished. The development camera starts aligned with its authored PlayerStart;
full zone arrival/facing behavior remains part of world/travel integration.

Native camera tests cover both zoom ranges, pitch limits, inversion, sensitivity
clamping, invalid inputs and repeated indoor/outdoor restoration. The network
proof's `--quest-ui` mode additionally checks the real spring-arm state, orbit,
zoom, indoor restoration and modal isolation on both clients. Its respawn phase
checks that the defender retains a changed zoom and orbit after the pawn is
replaced. Test receipts and screenshots require separate review; these checks
do not approve full movement/camera parity.

Verification on 2026-09-21: all 18 native Foundation groups passed in
`artifacts/unreal/editor/test-1789982917178-27820/`. The rendered Editor-client
network proof passed in `artifacts/unreal/network/1789983117024-24828/report.json`,
including camera modal isolation, restoration and actual pawn-replacement
continuity. The 74 migration tooling tests and tools typecheck also passed.
The Windows Development package and rendered two-client proof passed in
`artifacts/unreal/network/1789983324770-16520/report.json`; both screenshots were
inspected for visible characters and readable quest panels. Physical wheel/drag
input and full camera obstruction acceptance remain open.
Release admission remains closed with four blocker categories.
