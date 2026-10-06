# Fluid combat

The initial tuning pass keeps targeting, damage, healing and class kits intact.
Baseline abilities use a 1.0-second shared cooldown (stances retain 0.5 seconds),
and ordinary spell preparations use 80% of their previous duration. Ultimate,
channel tick/duration and authored movement timings retain their existing values.
Saved GM-authored timings take precedence over baseline preparation scaling.

## Gameplay and presentation boundaries

`UWarAbilityRuntime` owns release, channel ticks, costs, cooldowns, cancellation
and a single 200 ms input buffer. Animation recovery is cosmetic. Movement or
jump input cancels stationary casts/channels, clears buffered input and remains
responsive locally. Turning does not cancel. A stationary cast cannot begin
while movement input is held. Ordinary weapon attacks continue while moving.
Roots, stagger, death and validated charge/leap travel keep their gameplay rules.

Before an effect commits, movement cancellation reverses the activation's actual
career-resource delta and mana debit and removes its individual cooldown.
It does not rewind unrelated changes or the shared cooldown. Once a projectile,
movement effect, cleanse or channel tick commits, cancellation keeps the cost
and completed effects. Explicit enemy interrupts retain committed costs.
Launched projectiles retain their own definition and launch context; they cannot
be replaced by the next ability. Impact still validates the recipient, realm,
zone, range and line of sight.

Shared definitions and the native GM composer expose `movementPolicy` (`free`
or `stationary`). Channels require stationary casting. Old documents without a
policy use shape/school/movement-effect compatibility rules; no timing values
are silently rewritten. `preparationScale` affects unauthored baseline timing
only. Changing workshop timing marks it authored, including instant timing.
Baseline seed overrides explicitly keep magical weapon cleaves and Moonshot
mobile, while Blood Rite, Razor Prayer and Feast of the Shrine require stationary
casting despite their poison damage school.

`AWarCharacter` replicates presentation start, playback rate, instant-contact
offset and channel hold. `UWarAnimationInstance` blends locomotion below each
visual definition's `CombatUpperBodyBone`; current imported rigs use `spine`.
Missing split bones reject the visual definition. Equipment follows finalized
bones using existing profile-specific grips. No root-motion extraction or
animation notify can apply damage.

Ordinary damage never interrupts an ability. Cosmetic hit reactions cannot
replace an active action. Confirmed hit notices drive an original synthesized
impact sound, brief hit marker and camera impulse. Options contains a persisted
combat-shake slider: zero disables it, 0.25 is the light default. There is no
hit-stop. `CriticalHit` feedback accepts explicitly identified critical outcomes
without modifying their amounts; this pass does not invent a critical-damage
mechanic for a runtime that does not currently have one.

## Floating damage and healing

`WarCombatFeedback::Emit` forwards the authoritative recipient only to the effect
source's controller. `WarPlayerControllerCombatFeedback` passes that identity,
actor and head position in the existing sequenced, unreliable owner RPC.
Only confirmed positive health damage or effective healing produces a number;
overheal, interrupts, mitigation and another player's outgoing effects do not.
Self-healing produces one number. The existing combat log, sound and camera
feedback remain available. The owner notice budget is 128 events per second;
over-budget or lost cosmetic packets never affect gameplay or build a queue.

`WarFloatingCombatText` owns the client-only animation and bounded storage.
An isolated effect lasts one second. Each additional recent effect on the same
recipient (within 350 ms) increases scroll speed, capped at five times normal;
existing numbers accelerate too. Three short horizontal lanes separate procs,
with earlier text pushed upward when a lane is reused. The oldest numbers are
evicted at six per recipient or 32 overall. Effects on other targets do not
accelerate an isolated number. Each event retains its actual amount.

`WarCombatHud` projects each recipient's body-mesh head bounds, independent of
the selected target. Normal damage is pale gold, critical feedback orange and
healing green with a plus sign. Numbers rise 64 UI pixels and fade over the final
30% of the path. Text width is fitted to 56 pixels; the complete number and shadow
must fit a 160 x 112 pixel region above the head. These dimensions use the existing
HUD scale. Offscreen/behind-camera numbers are never pinned to screen edges.
Live recipients obey line of sight. An unmapped or destroyed actor briefly uses
its supplied/last known position. Weak references avoid retaining actors, and
controller ticking expires entries even while UI is hidden.

Native `AegisWar.Foundation.FloatingCombatText` tests cover isolated lifetime,
twenty procs within one second, simultaneous bursts, independent recipients,
bounded motion/count, quiet-period reset, source-only player/NPC routing,
self-healing, moving targets and despawn cleanup. Run it through
`npm run unreal:test-native` after an Editor build. Interactive visual/feel review
and actual multiplayer transport remain separate verification steps.

Verified on Windows on 2026-09-30: Editor compilation and all 74 native tests
passed (`artifacts/unreal/editor/test-1790774554074-5656/index.json`), including
the floating-number test. The shared suite passed 722 tests and Unreal tooling
passed 157 tests; all three typechecks, world/model validation and the migration
audit completed successfully. The audit retains its four release blockers.

## Default overhead health bars

Combat overlays can be customized in [Edit UI](unreal-combat-ui.md), including
independent friendly/enemy number motion, health bars, reticles and target panels.
Defaults below remain the initial settings; number streams share recipient
lanes and count limits even when their individual styles differ.

`WarOverheadHealth` reads replicated health/max-health attributes for players and
siege characters, or replicated health plus catalog max-health for `AWarEnemy`.
`WarOverheadHealthHud` renders an 84 x 10 UI-pixel bar above each eligible head,
scaled with the HUD, using the existing blue ally/red enemy colors, a dark border
and an empty-health background. Full-health and unselected characters show bars.
The fill follows current health directly each frame, including other characters'
damage, healing and maximum-health changes; it never subtracts floating-number
events or waits for a local attack. Floating numbers sit 12 pixels higher to keep
their bounded stream clear of the bar.

Eligibility reuses combat targeting: living characters with ready visuals, in the
same zone and within 50 metres. The local player's existing vitals remain in the
HUD. Dead, hidden, obstructed, offscreen or partly clipped bars do not render;
modal/GM/interface-edit screens suppress them. Noncombat city service NPCs have
no combat health and do not receive invented health bars. Rendering tests sight
only after range/zone and projection checks. No new health replication is needed.

`OverheadHealth` tests cover screen bounds, HUD scaling and clearance from damage
numbers. `TargetSelection` additionally checks default allied/enemy bars, immediate
health/heal/max-health updates, actual damage to an authored NPC, and rejection of
dead, hidden, out-of-range, other-zone and unloaded characters.

Verified on Windows on 2026-09-30: Editor build and all 75 native tests passed
(`artifacts/unreal/editor/test-1790778973035-20284/index.json`). The NPC check uses
the exact installed mesh/material/collision binding and applies real damage.
All 722 shared tests, 157 Unreal-tooling tests, three typechecks, world/model
validation and the migration audit also passed. Interactive visual and network
acceptance remain outstanding; the audit retains its four release blockers.

## Staging and verification

Use `npm run unreal:stage` for a fully reconciled content export. When unrelated
map edits are pending, `npm run unreal:stage-combat` updates baseline abilities
and their wiki pages, preserves the installed maps and other catalogs, and runs the existing
world-visual source/package guards. It refuses roster changes, backs up both
installed manifests and records the composite source provenance under
`artifacts/unreal/combat-stage/`. Persisted GM workspaces are not modified.
The installed baseline's source hash may therefore differ from a complete
current-worktree export. This is development staging, never world or release
approval.

- Build: `npm run unreal:build -- --target Editor` (also runs the repository's frontend refresh).
- Native gameplay: `npm run unreal:test-native`, including `CombatFluidity` and `CombatLocomotion`.
- Network input: `npm run unreal:combat-network-proof`, using real owner RPCs and predicted CharacterMovement with 80 ms lag, 20 ms variance and 2% packet loss.
- Presentation replication: `npm run unreal:animation-network-proof`, including late joins and playback-rate-aware pose sampling.
- Equipped captures: run `AegisWar.Foundation.CombatLocomotion` in Unreal automation with `-WarCaptureSuppliedAnimation -AllowCommandletRendering`; inspect `Saved/CombatFluidityCapture` for forward, strafe and backward attacks on all six admitted profiles.
- Full-cycle captures: also add `-WarCaptureCombatCycle`. This records forward/strafe/backward transitions, an animation restart, jump, and recovery at 12 frames per second from two views. Run `python scripts/unreal/combat-review.py` (Pillow required) to produce timed GIF previews and phase sheets under `artifacts/unreal/combat-playtest/review/`; generation requires a passing native capture receipt.
- Feedback review: run `AegisWar.Foundation.CombatFeedback` with `-WarCaptureCombatFeedback` to export the exact production-generated normal/critical PCM as WAV files under `Saved/CombatFeedbackReview/`. Tests verify headroom, decay, camera impulse bounds, immediate off, preserved view location/FOV, and shake-setting persistence in an isolated test settings file. These dry samples exclude game/master gain and the audio-device mixer.
- Shared/native tooling: `npm test`, `npm run test:unreal`, all three typechecks, `npm run unreal:audit`, `npm run world:validate`, and `npm run models:validate`.

Automation receipts establish only what was exercised. Rendered captures do not
replace an interactive feel/sound playtest, and Windows loopback checks do not
close Linux, macOS, Steam or release acceptance gates.

## Recorded development checks (2026-09-30)

- Editor build succeeded. Full native automation passed 73 tests:
  `artifacts/unreal/editor/test-1790768464545-22164/index.json`.
- Shared suite passed 722 tests; Unreal tooling passed 157 tests. All three
  typechecks, the Unreal audit, world validation (33 maps), and model validation
  (906 records) completed successfully. The audit still reports four release blockers.
- Rendered `CombatLocomotion` passed and produced 36 equipped captures across
  six admitted profiles, three directions and two views:
  `artifacts/unreal/combat-fluidity/rendered-final/index.json` and
  `unreal/AegisWar/Saved/CombatFluidityCapture/`. Forward, strafe and backward
  samples were visually reviewed on every profile. Still frames do not establish
  absence of foot sliding throughout a complete animation cycle.
- Delayed owner/server movement and cancellation passed:
  `artifacts/unreal/combat-network/1790768196925-24504/proof.json`.
  Presentation replication, including late join, passed all 41 variants:
  `artifacts/unreal/animation-replacement/network/1790767781337-5880/report.json`.
- Baseline abilities and wiki pages were staged with installed maps preserved:
  `artifacts/unreal/combat-stage/1790768430401/receipt.json`.

Interactive feel, sound, full-cycle clearance and camera-shake preference review
remain required before accepting this tuning pass. These results do not change
the existing platform, Steam or release gates.

### Extended playtest evidence

The final Editor build succeeded and all 73 native tests passed again:
`artifacts/unreal/editor/test-1790771598461-2412/index.json`.
Python compilation and preview frame-count/timestamp checks also passed.

The follow-up native `CombatLocomotion` check exercises complete actions through
forward/strafe/backward transitions, a second action, jumping and recovery on all
six admitted profiles. It checks finite poses, equipment bindings every frame,
airborne movement, return to locomotion and continued capsule velocity. The
passing capture receipt contains 720 images (684 cycle frames plus the 36 contact
views). `artifacts/unreal/combat-playtest/review/review.json` indexes 12 timed GIFs
and matching phase sheets; both views retain native elapsed timing. Phase sheets
were visually reviewed for each profile. An animation restart here tests visual
blending; authoritative ability chaining is covered by `CombatFluidity`.

The extended `CombatFeedback` check verifies production PCM amplitude/headroom,
fade-out and distinct critical samples; camera impulse decay, intensity scaling,
off and preserved view location/FOV; and controller preference persistence read
back from a separate test file. Its initial fixture issues (double world setup
and an unregistered config branch) were corrected; they did not require changing
production preference handling. Normal/critical WAV files contain dry production
samples, not a recording of the in-game audio mix.

These checks improve repeatable coverage but do not constitute subjective combat
feel, sound-mix or frame-by-frame clearance approval. Those acceptance gates stay
open alongside the existing platform, Steam and release gates.
