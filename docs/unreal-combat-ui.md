# Combat UI customization

Open **UI Settings → Edit UI**. Action-bar handles remain available along the
bottom. The combat preview uses a virtual viewport between the element list and
properties panel; screen positions are normalized within that viewport. The
blue friendly and red enemy body outlines are Slate lines only. No actor or
gameplay model is created for a preview.

Select a preview or an element in the list. Drag to move it, or enter precise
X/Y values in Properties. Hidden elements can still be selected in the list;
the yellow selection outline remains draggable. Properties collapse to reduce
clutter. Numeric controls support dragging and typed values; colors have
swatches, hexadecimal input, RGBA channels and overall element opacity.

Friendly and enemy styles are independent for target reticles, overhead health,
normal damage, critical damage, healing and selected-target panels. Each panel
has independently selectable name, health bar, health text and cast elements.
The hit marker and five-type combat-message feed are shared. Reticles use body
offsets; bars/numbers use head offsets; panel children use parent offsets.
Target panels, hit marker and feed use screen fractions. When the two target
panels overlap, the editor separates them for comparison and displays a note;
their saved coordinates remain unchanged. Gameplay only displays the selected
target's panel.

**Reset element**, **Copy to other side** and **Reset combat UI** affect only
combat styles. Copy acts on the corresponding element, not the entire side or
its panel children. Preferences apply to all characters on this computer in
the versioned `AegisWar.CombatUi.v1` section of `GGameUserSettingsIni`. Missing,
malformed or unsupported values fall back per setting. Drag release, control
commit, Done and Escape save. There is no cloud synchronization or profile UI.

**Single hit**, **20-proc burst**, **Healing**, **Pause** and **Replay** control
a deterministic local timeline. Mock health and casts change with playback.
The preview never calls abilities, combat RPCs, rewards, sounds or camera shake.
Edit UI owns paired movement/look locks and consumes preview input. Done/Escape
return through UI Settings; panel handoffs, entry interruption and controller
shutdown remove the editor and release its locks.

## Runtime boundaries

- `WarCombatUiSettings` defines typed styles, range validation, local INI
  serialization and target/parent/screen-relative movement.
- `WarCombatUiDrawing` generates drawing commands consumed by Canvas gameplay
  and Slate preview adapters. Both use the same layout, style and bounded
  floating-number calculations.
- `WarFloatingCombatText` retains server-confirmed relationship metadata,
  per-type lifetime and burst speed, and recipient-shared lanes/counts.
  Hidden categories occupy no slots. Numbers retain the recipient relationship
  when an actor is unmapped or destroyed; self-healing is friendly.
- `WarPlayerControllerCombatUi` exposes update/reset/copy/save operations;
  `WarPlayerControllerUiLayout` owns the editor lifecycle.
- `SWarCombatUiEditor` and `UWarCombatUiEditorWidget` implement runtime Slate
  selection, dragging, properties, color controls and Escape handling.
- `WarCombatHud` and `WarOverheadHealthHud` read these styles while retaining
  replicated health, target eligibility, range, zone, readiness and sight rules.

Defaults retain blue/red combat targeting and overhead bars, cream damage,
orange critical damage, green healing, one-second isolated numbers and up to
5× burst speed. Lifetime supports 0.25–2 seconds, rise 16–128 UI pixels and burst
speed 1–8×. The 350 ms burst window, final-path fade, six-number recipient cap
and 32-number total cap are shared across number categories. The region is
160×112 logical pixels at default scale and at most 2× that size; long numbers
fit their lane, and rise is bounded by the available region and text height.
HUD resolution scaling applies to all logical pixel dimensions.

Noncombat NPC labels, player vitals, minimap and other HUD systems are outside
this editor. Existing platform, Steam and release gates remain unchanged.

## Verification

Run the Editor build and `npm run unreal:test-native`. Foundation tests include
`CombatUiSettings`, `CombatUiPreview`, `FloatingCombatText`, `OverheadHealth`,
`TargetSelection` and `ActionBars`. Persistence tests use disposable INI files.

Rendered interaction checks use isolated preferences:

```powershell
npm run unreal:combat-ui-proof -- --width 1280 --height 720
npm run unreal:combat-ui-proof -- --width 1920 --height 1080
npm run unreal:combat-ui-proof -- --width 2560 --height 1080
npx tsx scripts/unreal/combat-ui-network-proof.ts
npx tsx scripts/unreal/combat-ui-live-proof.ts
```

The rendered runner routes Slate pointer/key events, verifies selection/drag,
hidden drag recovery, numeric/hex commits, copy/autosave/reopening, action bars
and exit/interruption cleanup. It saves default, hidden and extreme-size PNGs
plus a report under `artifacts/unreal/combat-ui/`. Screenshots need visual review;
unit tests alone do not establish rendered acceptance. The separate network
runner uses an actual loopback owner/server connection with 80 ms latency,
20 ms variance and 2% packet loss; it verifies relationship metadata, unmapped
friendly feedback, self-healing and replicated NPC movement/health. It does not
establish Steam or cross-platform multiplayer acceptance.

The interaction runner also closes the game and launches a fresh process using
the same isolated preferences. It checks custom motion, hidden position and
copied colors before opening the editor, then captures `restart.png` and writes
`restart.json`. The live runner opens three actual loopback player connections
and two NPC recipients. Only the owner client renders; the remote clients and
server use NullRHI. It moves recipients, changes authoritative health, sends real
owner feedback and switches the owner's selected target between all four
recipients. Four native screenshots and per-recipient head/health receipts are
saved under `artifacts/unreal/combat-ui-live/`. This exercises the gameplay HUD,
not the editor mock timeline. Both new checks require a rebuilt Editor binary;
their implementation alone does not establish a passing result.

Also run `npm test`, `npm run test:unreal`, all three typechecks,
`npm run unreal:audit`, `npm run world:validate` and `npm run models:validate`.
Record completed evidence separately from visual and live-play acceptance.

### Verification checkpoint — 2026-10-04

- Editor Win64 Development build passed (`artifacts/combat-ui-build-coordinated-final.log`);
  the final screenshot-harness correction also built successfully
  (`artifacts/combat-ui-build-proof-final.log`).
- Native suite completed 77 tests: 74 passed, including combat UI preferences,
  preview, floating text, overhead health, targeting and action bars. The three
  failures were `SiegeAuthorityAndNormalization`, `SiegeOwnership` and
  `SiegeRules`, whose legacy expectations belong to the concurrent citadel/siege
  changes. They are recorded separately in `artifacts/combat-ui-native-tests-final.log`.
- Repository tests passed 722/722; Unreal tooling passed 157/157. All three
  typechecks passed. World validation passed 33 zones; model validation passed
  906 records. Migration audit completed with four existing release blockers;
  `readyForRelease` remains false. These are checkpoint results in a shared
  worktree, not certification of subsequent unrelated changes.
- Rendered interaction runs passed at 1280×720, 1920×1080 and 2560×1080.
  Default and maximum number-size captures were inspected for outline identity,
  panel readability, bounded numbers and bar spacing. Hidden selection/drag
  is independently asserted; a deferred screenshot timing correction keeps
  the hidden element selected for its capture. Final capture runs are logged
  in `artifacts/combat-ui-render-*-reviewed.log`, with PNGs and reports under
  `artifacts/unreal/combat-ui/`.
- Actual owner/client loopback networking passed with 80 ms lag, 20 ms variance
  and 2% packet loss. Enemy/allied NPC feedback, self-healing, unresolved friendly
  recipient metadata, NPC movement and replicated health were verified in
  `artifacts/unreal/combat-ui-network/1791114070052-19084/proof.json`.

At that checkpoint, disk reload and editor reopening were verified; a full game
restart, moving remote-player visual review and live target-switching review
were still outstanding. The later checks below extend that evidence.

### Follow-up verification — 2026-10-05

The 1920×1080 interaction run and a fresh second game process passed using the
same isolated INI. Custom motion, hidden element position and copied colors
survived process exit and reload; `restart.png` was visually reviewed.
Evidence: `artifacts/unreal/combat-ui/1920x1080-64585f29-6e92-4c94-b9f1-be666dab5e15/`.
The coordinated Editor rebuild passed, including the isolated proof additions;
Unreal-tools typechecking passed. Production combat UI code was unchanged.

The later shared native checkpoint at
`artifacts/unreal/editor/test-1791146258379-23980/index.json` contains 94 passes
(86 successes and eight successes with warnings), zero failures, including all
four combat UI/floating/overhead test groups. This supersedes the three unrelated
siege failures above. A full native-suite repetition is unnecessary for the
proof-only follow-up; live rendered evidence is recorded independently.

The rendered live proof passed on three actual loopback player connections with
80 ms lag, 20 ms variance and 2% loss. All four moving recipients retained the
correct relationship and head anchor; overhead bars matched replicated health.
Selecting enemy player, friendly player, enemy NPC and friendly NPC updated the
live reticle and target panel. All four 1920×1080 captures were inspected for
recipient attachment, bounded number regions, bar/fill colors and panel identity.
Evidence: `artifacts/unreal/combat-ui-live/1f654098-2201-4304-9dbb-07cd0e8e494a/`.
The proof server drives movement and health changes; these are rendered gameplay
HUD checks over real connections, not a claim of manual player-input testing.
This completes the deferred restart, moving-recipient and target-switching
evidence for the combat UI feature. No production UI changes were needed.

Steam, multi-platform and full migration acceptance remain separate.

### Proof-runner resource cleanup

The network and live proof runners attach process tracking immediately after
launch, report spawn failures during readiness checks, and await each owned
process's close event during cleanup. Cleanup tolerates an earlier close and
escalates only that child after ten seconds; an additional ten seconds without
closure reports unconfirmed shutdown. It never terminates processes by name.
An unconfirmed shutdown requires checking the reported PID before handing the
native/GPU slot to another task.

Portable lifecycle coverage runs with
`npx vitest run tests/unrealCombatUiProcess.test.ts --maxWorkers=1`. It exercises
failed launches, early exit, real Node child shutdown, escalation and timeout
reporting without starting Unreal. These tooling checks do not replace rendered
or network acceptance evidence above.

On 2026-10-05 the five lifecycle tests, all 278 portable Unreal-tooling tests,
and `typecheck:unreal-tools` passed after this runner change. No Unreal process
was launched for these portable checks.
