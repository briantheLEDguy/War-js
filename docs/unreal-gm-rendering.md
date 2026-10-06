# GM rendering diagnostics

The reported failure changes the world's colors after using **Escape → GM
Tools**, including flight, speed and teleport, and persists after closing the
panel. Restarting restores the appearance. Its root cause is not yet confirmed.

City Builder currently exempts its lifetime from Slate interaction throttling;
the separate GM menu does not. Flight and speed commands do not directly change
graphics settings. A throttling discrepancy alone does not prove the cause of a
persistent color change, particularly in editor-launched Standalone play.

## Reproduction

Build the Windows Editor target first, closing an existing editor if it holds
the module DLL open. The configured `GameDefaultMap` and its private native
content must be installed. Run these sequentially:

```powershell
npx tsx scripts/unreal/gm-rendering-proof.ts --mode idle
npx tsx scripts/unreal/gm-rendering-proof.ts --mode direct
npx tsx scripts/unreal/gm-rendering-proof.ts --mode pointer
npx tsx scripts/unreal/gm-rendering-proof.ts --mode pointer --host pie
npx tsx scripts/unreal/gm-rendering-proof.ts --mode input --host pie
npx tsx scripts/unreal/gm-rendering-proof.ts --mode manual --host pie
python scripts/unreal/compare-gm-rendering.py <printed-run-folder>
```

The launcher uses a unique `Saved/GmRenderingProof/<run>/` folder, copies local
graphics preferences into `GmRenderingProof.ini` when available, and gives world
editing a separate `Saved/WorldEditProof/<run>/` location. It does not save maps
or overwrite owner drafts/preferences. The PIE variant starts a separate editor
process; it does not attach to or close an existing editor. Automatic runs have a
five-minute timeout; manual capture allows fifteen minutes.

The native fixture requires explicit development/proof flags and isolated
preferences and draft identity. It is disabled in Shipping. Flight and speed
`pointer` checks route down/move/up events through the actual Slate widget path.
`input` uses Slate's normal mouse processing and hit testing, holds the button
across frames, and checks capture and the resulting gameplay state. Both are
synthetic input, distinct from desktop mouse testing in `manual` mode.

Manual mode opens a visible disposable window, waits 35 seconds for its baseline,
then records every five seconds without issuing gameplay commands. In embedded
PIE, Escape normally stops Play: create `open-menu.txt` in the printed run folder
to open the same in-game menu, and use its Resume button to close it. This avoids
changing the owner's editor shortcuts. Create `stop.txt` in that folder to finish
capture and close the disposable process. Neither marker contains commands or
paths to execute. Do not edit or publish drafts during a rendering diagnosis.

Captures cover a settled baseline, opening the menu, flight, menu closure,
settling, speed adjustment, returning to spawn, resuming walking, and teleporting
to Sunmeadow March and back to Bastion. Zone travel uses the same server commands
directly; the automated fixture does not claim pointer coverage of zone buttons.
Each JSON
capture records live renderer variables, viewport show flags, camera position
and grading, active zone, light/post-process component state, post-process
volumes and level visibility. Each stage captures both the final image with Slate
UI and a `-scene.png` image without Slate overlays, so a lingering UI tint cannot
be mistaken for a lighting change. Compare closed-panel stages with the baseline;
the open menu intentionally dims the world.

`report.json` confirms only that the diagnostic sequence completed. The Python
comparison uses scene images, reports camera matching, state differences and
fixed-region RGB measurements; neither
receipt claims visual acceptance. Compare matching camera positions and inspect
the screenshots. The full command/transition regression matrix and reproduction
of the persistent failure remain required before closing the bug.

## Verification status

Windows rendering evidence from 2026-09-29 uses the configured map
`/Game/WorldRebuild/DutchBastion_d105951f4aab/Bastion_Campaign_v3`. Run folders are
under `unreal/AegisWar/Saved/GmRenderingProof/` and are intentionally untracked:

| Run | Exercised path | Observed result |
| --- | --- | --- |
| `0acdf84918b34d0bab6ac34374d0af33` | Standalone routed pointer: flight, maximum speed, close, spawn return | Commands executed; settled world appearance and captured renderer state preserved. This early run has scene-only images. |
| `2c8026f7a25a4c9e829b18559a94d66e` | Embedded PIE held Slate mouse input, flight/speed, zone round trip | Completed with exit 0; authored capital lights restored on return. Remaining component differences are disabled runtime environment values. |
| `5f1b5f7387634cda8097cb9b337cda1f` | Standalone desktop mouse through Escape menu: flight and speed dragging to 6x | No persistent color change observed after closing. |
| `23ccf99b233549b0bd3b5c20d2d6b658` | Desktop PIE: flight both ways, speed 0.25x/6x, spawn return, Restore, cooldown reset, Builder/Workshop handoffs | 32 captured states had no changes to renderer, lighting, camera or streaming state. Closed-panel images retained the baseline appearance. Play was started/stopped manually for this run. |
| `81d15eafb3e54f5593f99cfff03ae4b0` | Idle embedded PIE control, same stage timing with no gameplay/menu actions | Completed with exit 0 using the final Python startup/shutdown path. All captured renderer, environment, camera and streaming values remained unchanged. |
| `408ae6fe77db47b5ba034493ed58774b` | Standalone direct-command control: flight, speed, spawn return, Sunmeadow/capital round trip | Completed with exit 0. Settled capital frames preserved renderer settings and authored lighting; only disabled runtime environment values differed after travel. |

These runs **did not reproduce the reported persistent failure**. They do not
establish Slate throttling as its cause, and no production rendering guard,
lighting patch or graphics reset has been applied. Open-menu dimming is expected
and disappeared on closure. A failing session capture is still needed to identify
the first incorrect transition and write a meaningful root-cause regression test.

Validation: Windows Editor and Game builds passed; 69 native foundation tests,
709 repository tests (including five diagnostic launcher tests), and 144 Unreal
tooling tests passed. All three typechecks, migration audit, world validation (33
maps), and model validation (906 records) passed. Release readiness remains false
with four existing blockers. Linux/macOS rendering and Steam acceptance remain
unverified.

All rendering runs started fresh processes with the newly built module. The
owner's pre-existing editor remained open with its previously loaded module;
these results do not inspect or attest its in-memory state. The automated PIE
driver ends Play before quitting, avoiding the shutdown crash seen when an early
fixture requested process exit directly during PIE. That fixture crash is not
evidence of the reported in-session rendering failure.

Still required: failing-before/fixed-after rendered evidence; exact editor-launched
Standalone launch parity; character teleport and pointer-driven zone travel;
level changes, coordinate copying, performance stats, rejected/cancelled commands;
and repeated focus-loss/interrupted-pointer/lifecycle stress checks. Diagnostic
success is not completion of that acceptance matrix or of the bug fix.
