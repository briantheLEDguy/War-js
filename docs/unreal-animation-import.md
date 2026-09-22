# Supplied animation import workflow

The procedural animation studies are paused. The current implementation uses
the owner's local FBXs in `unreal/AegisWar/AnimationImport/Two-handed`.
Source FBXs and generated Unreal packages remain local/ignored.

## Battle Prelate result

Eleven Mixamo two-handed clips are imported and retargeted onto the equipped
Prelate's own skeleton. The live `Visual_civic_battle_prelate_m` uses the new
idle, combat idle, walk and `Great Sword Slash (1)` for the basic strike. The
other slash is a longer combination whose ground clearance fails on this hammer;
it remains a library entry. All eleven are also registered under
`two_handed_<clip>` names. The original run, jump, death, ranged and cast roles
remain assigned: the supplied set has no run/death/cast, and jump/special attacks
need movement and ability timing integration before activation.

The same body, armor, materials and hammer are retained. The hammer's rigid
binding moves 72 cm along its shaft to put the hands below its head and shorten
the pommel behind them. The support arm is fitted to the shaft without stretching
its bones; the supplied pelvis, torso and leg rotations are preserved. Linear
horizontal travel is removed from movement/basic attack library clips because
the current pawn uses CharacterMovement and single-node animation playback.

The saved native visual and runtime admission registry are updated together.
`BeforeTwoHanded` and `original-binding.json` retain the previous visual and
registry entry. The installer changes only the Prelate entry, preserving other
characters and unrelated animation roles. Re-run installation after the older
`recover-battle-prelate.py` or `prepare-proof.py` resets this visual.

## Repeatable command

```powershell
python scripts/unreal/animation-pipeline.py battle-prelate-two-handed --review
python scripts/unreal/animation-pipeline.py battle-prelate-two-handed --from-stage verify
python tests/unrealPrelateTwoHanded.test.py
```

`--unreal` and `--blender` override executable locations; `WAR_UNREAL_EDITOR`
also overrides Unreal. Stages stop on failure and write separate logs under
`artifacts/unreal/two-handed`. Rendering is optional. `--from-stage` resumes
at a known stage. **Re-run retarget before fit**: grip fitting intentionally
rejects fitting an already-fitted animation. Source imports are reused by
source/body hash; changing FBX bytes creates a separate import directory.

Stages are declared in `scripts/unreal/animation-recipes/`. Source filenames,
bone-chain mapping and live role decisions are in `prelate_two_handed.py`.
The Blender preparation measures the original authored grip locations and
adapts only the weapon binding. Unreal performs the actual animation import,
IK retarget, compression, native validation and rendering.

## Notes for subsequent characters

1. Inventory FBX skeleton, frame rate, duration and travel before importing.
   Reuse one source skeleton for clips with the same hierarchy. Never make the
   Mixamo mannequin the character's gameplay mesh.
2. Add an explicit character recipe and anatomical chain mapping. Reuse the
   source-rig pattern and runner; keep class-specific weapon/grip, source paths,
   live roles and backup destinations separate. Do not apply the Prelate's
   72 cm hammer offset or 100x bind correction to another rig automatically.
3. Establish a bind pose and scale baseline before touching poses. This rig has
   a `humanoid_game_v2` armature at 100x above meter-space bones. UE 5.8 retarget
   processing strips scale. Restore that top-bone bind scale and divide the
   retargeted pelvis translation by 100; other FK local translations already
   use the target bone units. The root-motion operation must not copy Mixamo's
   pelvis height into the ground root.
4. Align chain poses, then inspect the equipped character from front and side.
   Weapon skinning can bias automatic hand alignment. Fit contact after body
   retargeting, retain original elbow planes, slide the support grip only along
   the shaft, and reject unreachable contacts for live roles. Check the head,
   torso, armor and legs through the complete swing, including recovery.
5. Decide movement ownership per clip. Forward-moving attacks and jumps cannot
   simply play at full root travel on a capsule-driven pawn. Do not fabricate a
   run from a walk, or bind a slide/spin to a basic strike merely because it exists.
6. Use scale-aware ACL compression and sample raw/compressed native poses.
   Verify every limb length and every saved animation/skeleton association.
   Register paths in both the visual DataAsset and `visual-imports.json` or the
   native admission gate correctly rejects the character.
7. Keep all source assets local, maintain backup bindings, and record which clips
   are active versus library-only. Repeat technical validation and visual review
   for each character; successful retargeting is not animation/art approval.

### Verified Unreal 5.8 Python API details

- Use absolute `.uproject` paths in unattended commands; prefer legacy FBX
  import here (`Interchange.FeatureFlags.Import.FBX 0`). Source namespaces are
  stripped (`mixamorig:Hips` becomes `Hips`).
- `IKRigController.add_retarget_chain(name, start, end, "None")`,
  `set_retarget_root`, `IKRetargeterController.add_default_ops`,
  `auto_map_chains(EXACT, True)` and `auto_align_all_bones(TARGET)` are supported.
- Use `IKRetargetBatchOperation.run_batch_retarget(inputs)` in 5.8.
- Read `AnimSequence` skeleton with `get_editor_property("skeleton")`.
  Write tracks via `animation.controller.set_bone_track_keys`; there is no
  Python `get_controller()` method on AnimSequence.
- Mesh materials are edited through the `materials` struct array. FBX slot
  sanitization replaces dots with underscores; match names, not slot ordering.
- This `validate_for_spawn` binding returns the error string on success (empty)
  or `None` on failure, not a `(bool, string)` tuple.
- Never reuse `new_level` at an existing asset path. Review levels are isolated
  and uniquely named; the owner's city map is not saved by these tools.

## Verification and remaining work

`verify-prelate-two-handed.py` reloads saved assets, checks native spawn readiness
and registry agreement, then compares raw/compressed poses at 60 Hz with a
0.1 cm position tolerance and 0.01 cm limb-length tolerance. It checks the full
rigid weapon bounding box against the ground and rejects live roles that cross
it. This conservative ground check does not replace body/armor collision review.
The role tests cover
preservation of existing clips, distinct source clips and rejection of missing,
nonfinite or unreachable live grips.

Some library-only clips still have up to approximately 2 cm of unreachable
support-hand contact with this body. They are not active gameplay roles.
Final armor/weapon clearance, animation blending, movement-speed matching,
contact-timed damage and jump/special action integration remain review work.
No production, Steam, Linux/macOS or final visual approval is implied.

Current Windows/UE 5.8.2 evidence: 11 native clips, 1,251 raw/compressed pose
samples at 60 Hz, native spawn and saved-registry validation, three focused
role tests, 94 Unreal tooling tests and tooling typecheck passed. Migration audit
retains four release blockers. `verification.json`, `installed.json`,
`grip-fit.json` and native review frames record the local result. A standalone
native pawn activation probe could not set the protected visual property from
Python; it is not counted as an end-to-end gameplay test.
