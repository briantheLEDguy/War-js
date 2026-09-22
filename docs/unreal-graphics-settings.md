# Native graphics settings

Open **Graphics** from any character-entry screen or **Options → Graphics** in-game. The same overlay preserves the entry form and returns focus to the originating panel. Camera, audio, key bindings and UI layout remain separate.

## Controls

Windowed mode offers window sizes fitting the current display's usable area. Borderless Fullscreen uses desktop resolution; lower render scale to reduce 3D rendering work while keeping UI text sharp. Fullscreen resolutions come from Unreal's platform enumeration; exclusive fullscreen is unavailable on macOS. Switching between windowed and fullscreen retains a supported size or prefers a smaller available size rather than automatically selecting the largest resolution. Unsupported or unavailable choices are disabled or rejected with an explanation. Display switching is disabled in PIE; use Standalone Game or a game build.

Quality presets use Unreal's Low/Medium/High/Epic scalability groups. View distance can override the preset, producing Custom. Presets preserve display mode, resolution, VSync, frame cap and render scale. Frame caps are bounded to 30–240 FPS. Render scale is bounded to 50–100%, further restricted by engine limits. Engine/launch overrides are reported and may constrain the effective result.

New installations and Restore Defaults use Low, borderless desktop resolution, 75% render scale, 60 FPS and VSync. Existing valid preferences migrate without resetting bindings or camera/audio settings. Restore Defaults edits the draft; it does not immediately change the game.

## Apply and recovery

Editing controls changes only a draft. Apply starts a 15-second real-time preview of all changed settings. Keep changes is available after the actual window matches the request. Revert, Escape, closing the page, deactivation and timeout restore the previous snapshot. The world continues running.

The transaction rejects invalid numbers, invalid dimensions and unsupported modes, rechecks capabilities on Apply and verifies window state after switching. The controller survives widget removal. If restoring the previous mode fails, it tries a window fitting the remaining monitor. Missing enumeration preserves the working mode. Dedicated servers and headless runs cannot apply graphics changes.

Only confirmation persists the candidate. Incidental settings saves and Unreal's automatic window-resize confirmation cannot promote a pending preview. Persistence checks reread the settings file; a failed write reports failure and restores the previous settings. This guards against inaccessible modes and accidental configuration loss, not hardware faults, driver crashes or guaranteed frame rates on every PC.

To recover a problematic launch, add **`-WarSafeGraphics`** to the game's launch options. An early Core-only module selects a 1280×720 window before Unreal preloads display settings; Unreal fits it to the display when necessary. Quality starts at Low, 75% scale, 60 FPS and VSync. Remove the flag for subsequent normal launches. Do not combine recovery with unusual forced-resolution, portrait or monitor overrides.

## Architecture

- `WarGraphicsBootstrap` loads at PostConfigInit, before the Engine preloads the window. It migrates only the graphics section, repairs malformed display values and handles recovery startup.
- `UWarGraphicsSettings` extends GameUserSettings and owns draft/applied/confirmed snapshots, validation, persistence and the core-ticker preview/recovery lifecycle. It applies resolution and non-resolution changes separately, avoiding Unreal's auto-saving combined Apply call.
- `UWarGraphicsWidget` is the shared Slate/UMG overlay with scrolling controls and a fixed confirmation footer. No network messages or gameplay state are involved.

Runtime graphics remains local to the computer. Benchmarks, adaptive quality, refresh-rate/HDR/driver controls, vendor upscalers and power/overclock settings are outside this version.

## Verification

Run `npm run unreal:audit`, `npm run test:unreal`, `npm run typecheck:unreal-tools`, Editor/Game builds, and `npm run unreal:test-native`. Native graphics tests cover validation, presets, capability filtering, draft isolation, automatic resize confirmation, timeout/closure/deactivation, persistence guards, write failure, legacy migration and safe startup.

After building the Editor, run the rendered proof sequentially:

```sh
npx tsx scripts/unreal/graphics-proof.ts --mode smoke --profile review
npx tsx scripts/unreal/graphics-proof.ts --mode interrupt --profile review
npx tsx scripts/unreal/graphics-proof.ts --mode restart --profile review
npx tsx scripts/unreal/graphics-proof.ts --mode safe --profile recovery
```

The proof opens a windowed game, uses dedicated `GraphicsProof-*.ini` files and writes screenshots/logs/reports under `unreal/AegisWar/Saved/GraphicsProof/`. The interrupt mode deliberately terminates only its own proof process during a preview; restart must follow it with the same profile. The smoke requires the configured capital and native development character to be available. All fixtures are disabled in Shipping. Run proof processes one at a time because they share screenshot/report paths. Offscreen runs cannot validate display switching and have that control disabled.

Offscreen rendering and native automation do not establish physical fullscreen switching, monitor hotplug, high-DPI interaction, all GPU/driver combinations, or Linux/macOS acceptance. Those require platform playtests. Existing Steam, packaging and migration release gates remain unchanged.

## Verified on 2026-09-22

Windows Unreal 5.8.2 Editor and Game builds passed, together with 39 native automation groups, 97 tooling tests, tooling typecheck and the migration audit. The strict release check still fails with four migration blockers, as intended.

The real windowed smoke passed at character entry and in-game, including saving confirmed values, real-time timeout, closing a pending preview, restored keyboard focus, resizing from 1280x800 to 1280x720 and restoring the actual window. Entry, in-game and confirmation screenshots were visually inspected. Separate forced-exit/relaunch and safe-startup runs passed. Receipts are `Saved/GraphicsProof/report-smoke.json`, `report-restart.json` and `report-safe.json`; build/test logs are under `artifacts/unreal/graphics-*`.

Exclusive fullscreen, borderless transitions, monitor removal, high-DPI/ultrawide interaction and Linux/macOS remain unverified in real platform sessions. Automated capability/recovery tests cover their validation rules, not hardware acceptance. An unrelated native action-bar test's config-read assertion was corrected during compilation without changing action-bar behavior.
