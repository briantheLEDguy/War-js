> Historical record: the animation payloads and recovery scripts described below
> were removed by the supplied-set replacement. Use [the current workflow](unreal-animation-import.md).

# Native combat animation studies

**Paused:** the owner replaced this authoring work with supplied FBX animations.
Use [the animation import workflow](unreal-animation-import.md) for the current
Battle Prelate implementation. The latest procedural heavy-hammer revision was
not accepted or installed in gameplay; historical results below describe the
earlier isolated study and do not validate that unfinished revision.

The first set prioritizes the **Battle Prelate**, followed by the **Ember Arcanist**.
It contains a two-handed hammer strike, a gold ward, a rising gold blessing,
a fire release, a fire invocation, and a separate violet casting study. Violet
is a presentation study, not an added Ember Arcanist gameplay ability.

The existing authored class bodies, nine clothing/armor modules per character,
and Prelate hammer are assembled on their matching canonical rigs. These are
isolated review imports; existing gameplay character bindings and startup maps
are not replaced. No character or weapon primitive fallback is used.

## Motion and effect boundaries

- `scripts/unreal/combat-motions.json` owns timings, themes and wrist targets.
- `build-combat-animations.py` bakes the evaluated complete skeleton at 120 Hz.
  Rear-leg loading precedes the pelvis turn, followed by torso/arm acceleration,
  knee compression and recovery. The revised heavy strike uses a staggered stance,
  a rear shoulder wind-up, an overhead downswing and a slower recovery.
  Feet stay planted, and IK cannot stretch limbs.
  Both hands share one rigid hammer transform during the strike. Casting releases
  the supporting hand; the other hand retains the hammer.
- `combat_motion_audit.py` checks foot drift, unchanged limb lengths, pelvis
  support bounds and lower-body response to large hand gestures. The support
  envelope is a geometric check, **not a center-of-mass or human biomechanics
  simulation**. Clothing intersections and naturalness require visual review.
- `audit-combat-clearance.py` checks the entire hammer against evaluated body
  and outfit triangles at 120 Hz. A grip exemption requires both hand/finger
  skin weights and proximity within 13 cm of a wrist (the equipped gripping
  knuckles reach 12.35 cm); torso, armor and forearm intersections
  fail the import gate. The gate checks the exact FBX hash. Palm grip calibration
  and forearm-aligned wrist solving avoid the inherited socket's hyperextension.
  Discrete checks still need visual review between samples and on other outfits.
- `two_handed_motion.py` interpolates shaft pitch as an angle. Interpolating
  nearly opposite direction vectors can create an unintended sideways sweep.
  Heavy strike imports require measured rear-to-front head travel. Future
  two-handed attacks must choose an intentional swing plane, load the body and
  weapon together, preserve both grips, and pass clearance through the whole
  arc. Do not solve clipping by flattening a heavy strike into a frontal circle.
- `import-combat-animations.py` reconstructs source PBR materials and checks both
  raw and compressed Unreal poses against source samples at the existing 1 mm
  tolerance. New assets live under versioned `/Game/Imported/ThematicCombat/` paths.
- `WarCombatPresentation` evaluates actual skeletal poses. Short ribbons sample
  the real hammer head; cast filaments follow the actual wrist. The release
  marker captures a fixed world origin for projectiles and afterglow. Effects use
  translucent tapered strokes and sparks, not orbiting weapon props or solid
  spheres. The gallery is presentation only and cannot apply damage.
- `review-combat-animations.py` creates a separate native gallery, uses
  `WarCombatReviewGameMode` with no gameplay pawn, and renders load/release/
  follow-through/recovery frames. The current map path is recorded in
  `artifacts/unreal/combat-animation/review.json`.
- `create-combat-preview.py` presents the native front/side captures in sync at
  30 fps, with scrubbing and half/quarter speed. It regenerates `preview.html`
  and `preview-heavy-hammer.html` without modifying the rendered frames.

## Verified review set — 22 September 2026

All six clips passed raw and compressed native pose parity and the whole-body
checks. The equipped Prelate's three clips passed 543 hammer/body surface samples
at 120 Hz with zero non-grip intersections. Isolated native front and side frames
were inspected; the side camera excludes neighboring gallery actors. The gold
weapon trail follows the head continuously, with a soft profile across its width.

The Windows native build and 33 native tests passed, alongside 94 Unreal tooling
tests, six motion-audit tests and the Unreal-tools typecheck. The migration audit
completed with four existing release blockers; release-check correctly failed.
These results cover this review set, not final artistic or gameplay acceptance.

## Reproduce

From the repository root in PowerShell (Unreal 5.8.2 and Blender 5.0 installed):

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/unreal/build-combat-animations.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/unreal/audit-combat-clearance.py
npm run unreal:build
$combatEditor = 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$combatProject = "$PWD/unreal/AegisWar/AegisWar.uproject"
& $combatEditor $combatProject -unattended -nop4 -nosound -nullrhi -run=pythonscript "-script=$PWD/scripts/unreal/import-combat-animations.py"
& $combatEditor $combatProject -unattended -nop4 -nosound -AllowCommandletRendering -run=pythonscript "-script=$PWD/scripts/unreal/review-combat-animations.py"
python scripts/unreal/create-combat-preview.py
python tests/unrealCombatMotion.test.py
npm run unreal:test-native
npm run unreal:audit
npm run test:unreal
npm run typecheck:unreal-tools
```

Open the map named in `review.json` in Unreal to inspect the six actors and their
editable cue properties. Play runs the loops in the isolated gallery. The source
Blender scenes, GLB/FBX files, import evidence and review frames are regenerated
under ignored `artifacts/unreal/combat-animation/`; the recipes are tracked.

## Acceptance remains separate

These assets do not establish animation approval for other body variants,
weapon sets, moving attacks, remote players or all class abilities. The current
native development strike still uses its original imported animation and damage
path; it does not consume this review set. Runtime ability mapping, authoritative
contact events, interruption/blending and multiplayer timing must be integrated
and tested before promoting these studies into live combat. The legacy browser
primitive paths and migration release gates remain outstanding.
