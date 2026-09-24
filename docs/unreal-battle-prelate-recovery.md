> Historical record: the animation payloads and recovery scripts described below
> were removed by the supplied-set replacement. Use [the current workflow](unreal-animation-import.md).

# Battle Prelate recovery

The native development selection is **Empire / Battle Prelate / Male**.
Restart the editor/game after rebuilding to refresh the entry default and loaded
configuration. Female and other unconfigured selections retain a recoverable
missing-model error; they cannot substitute an NPC.

The former proof setup mapped `civic_battle_prelate_f` to the Sunmeadow herbalist
and deleted the male native import. The original male character was not lost:
its body, nine armor modules and hammer remain under `public/assets/models/`.
The historical rejection in `migration/visual-reviews.json` concerns the isolated
body source, which is not the complete equipped character. That rejection remains
recorded; this recovery uses a separate complete assembly and does not grant
release approval.

## Rebuild

Run from the repository root with Blender 5.0 and Unreal 5.8.2 installed:

```powershell
$blender = 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe'
$editor = 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$project = Join-Path $PWD 'unreal/AegisWar/AegisWar.uproject'
& $blender --background --factory-startup --python-exit-code 1 --python scripts/unreal/assemble-battle-prelate.py
& $blender --background --factory-startup --python-exit-code 1 --python scripts/unreal/convert-model.py -- --profile civic_battle_prelate_m
npm run unreal:build -- --target Editor
npm run unreal:import -- --profile civic_battle_prelate_m
$recovery = Join-Path $PWD 'scripts/unreal/recover-battle-prelate.py'
& $editor $project -unattended -nop4 -nosplash -nosound -nullrhi -run=pythonscript "-script=$recovery"
```

`assemble-battle-prelate.py` uses the original clean-reimport assembly helper,
including bone/rest-transform and vertex-position checks. The exported weapon's
socket binding becomes rigid skin weights on the same hand bone. It creates
`artifacts/unreal/equipped/civic_battle_prelate_m/equipped.glb` and an assembly
receipt listing all eleven source hashes. `equipped_source.py` checks that receipt
and the current registry before conversion or native import. Browser models and
registrations are unchanged. This is a fixed recovered outfit; dynamic native
equipment swapping is still pending.

The regular converter verifies the GLB-to-FBX roundtrip. It now preserves a final
NLA frame whose float32 endpoint falls just below an integer. The Unreal pose
check clamps only sub-microsecond endpoint overshoot, avoiding Unreal's out-of-range
reference pose without weakening pose tolerances. Import reconstructs the eleven
materials and verifies all nine raw/compressed animation clips.

`recover-battle-prelate.py` saves only the owned male visual DataAsset. It does
not rebuild or save the owner's capital. `prepare-proof.py` now uses that same
male identity and no longer deletes it. Runtime playable validation rejects a
different `SourceProfileKey`, while existing NPC source reuse remains available.

## Verification on Windows, 2026-09-22

- Unreal Editor build passed; native import saved one skeletal mesh, one skeleton,
  eleven materials, 33 textures and nine animations.
- All nine raw and compressed clip checks passed. Maximum sampled joint error:
  0.00339 cm; skin-transform error: 0.09396 cm (existing limit: 0.1 cm).
- Unreal front/back/side idle renders were inspected in
  `artifacts/unreal/visual-proof/civic_battle_prelate_m/`; the recovered armor,
  hammer, book and tabard are present.
- The rendered capital gameplay check passed with the recovered Prelate pawn:
  `artifacts/unreal/population/proof-1790077969824/report.json` and `merchant.png`.
  This verifies native spawn and city interactions through the development fixture;
  it does not claim interactive Steam login acceptance.
- Four assembly tests, ten import preflight tests, six pose-parity tests and the
  eight Blender conversion tests passed. `npm run test:unreal` passed all 94 tests;
  tooling typecheck and migration audit passed. Strict release-check still fails
  with four blockers, as required.
- Final native foundation run: all 32 passed, including
  `AegisWar.Foundation.CharacterFrontend` and its NPC/class-substitution checks.
  An earlier run failed the GM-default assertion; the shared workspace's GM
  setting was corrected before the successful rerun. Final report:
  `artifacts/unreal/editor/test-1790078075475-27988/index.json`.

Steam authentication, platform packaging and full gameplay/art acceptance remain
separate migration gates.
