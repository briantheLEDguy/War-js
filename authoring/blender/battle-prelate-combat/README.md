# Battle Prelate combat animation pack

Original hammer combat on the existing `humanoid_game_v2` / `a_pose_v2` skeleton. Character geometry, textures, weights, rest matrices and sockets are unchanged. The rigid Dawn Maul also has an explicit female compatibility record.

## Authoring and runtime

- `battle_prelate_combat_master.blend`: editable reference body/hammer, wrist/foot controls and four IK chains. Select `AUTHOR_<clip>` on the armature and `<clip>_CTL_<limb>` on each matching control to edit a motion together.
- `tools/build_animation_pack.py`: deterministic choreography and quaternion bake. It reads `src/game/animation/battlePrelateMotions.json`, the same durations/contact times used by gameplay.
- `tools/install_animation_pack.mjs`: verifies the bake digest/contact errors, then updates the Battle Prelate manifest/index entries while preserving unrelated entries.
- `review/`: bake audit, equipped runtime screenshots, comparison GIFs and review sheets. `runtime_review.json` records verification, limitations and evidence hashes. `tools/compose_review.py` composes screenshots using Pillow.
- `public/assets/models/anim_battle_prelate_combat.glb`: fourteen clips: twelve ability variants, combat guard and landing recovery. Embedded idle/walk/run/jump/death remain available.

Litany rotates through three strikes once per successful activation and resets after three seconds without Litany. The opening strike samples the character's embedded `attack_melee` windup, expands its wrist travel by 35% and rotation by 22% before the shared grip/foot constraint solve, and bakes it as `prelate_litany_a`; the next strikes use the authored horizontal return sweep and descending blow. The unmodified embedded clip remains available in baseline comparison and as a missing-pack fallback. All other abilities have dedicated gestures. Icon of Wrath remains unavailable in gameplay until persistent summons are implemented; its motion is available in the review stage.

Authored strikes establish a loaded pose before accelerating and retain velocity through contact. The return sweep travels horizontally, Penance loads low, Judgment thrusts from chest height, Sanctified Blow coils across the shoulder, and Reliquary lifts overhead. Hips lead the torso, stationary feet remain planted and the long handle finishes outside the central torso. Wrist targets stay within anatomical reach. The supporting hand releases deliberately for ward, chant, healing, placement and sermon gestures.

## Rebuild and review

Run from the repository root with Blender 5.0:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --python-exit-code 1 --python authoring/blender/battle-prelate-combat/tools/build_animation_pack.py
node authoring/blender/battle-prelate-combat/tools/install_animation_pack.mjs
npm test -- tests/battlePrelateMotion.test.ts tests/battlePrelateImpactTiming.test.ts tests/combatAnimationController.test.ts
npm run dev
```

Open `/?modelReview=combat` on the local development server. It uses the real Player, equipment binding and VFX without editing saved characters. Controls cover all abilities, Litany variants, body/armor selection, embedded-motion comparison, scrubbing, slow playback, movement, airborne transitions, effects and side/gameplay views. The route is excluded from production builds.

Review at normal speed, then inspect anticipation/contact/recovery from multiple angles. Check both bodies, male ornate armor and the male Novitiate set. The embedded baseline uses current ability durations to compare choreography; it does not reproduce the old timing bug.

The 120 Hz offline bake limits interpolation error; it is not a runtime frame-rate requirement. Export tests use the actual GLB on both body hierarchies: at most 2 mm planted-foot drift and 5 mm supporting-palm error. An approximate central-torso shaft check supplements visual review; it is not a complete armor collision proof.

## Integration boundaries

`CombatAnimationController` uses disjoint upper/lower track masks. Stationary actions use full-body poses; moving and airborne actors retain lower-body locomotion. Repeated actions get independent crossfade instances, retired actions are uncached, and recovery returns to a breathing guard. Combat notifications retain that guard for four seconds.

`AbilityMotionSequence` resolves one variant after activation validation. Character playback, weapon/VFX and pending damage share the selected duration/contact marker. Interrupting visual recovery preserves already committed gameplay effects. Existing costs, damage, cooldowns, movement validation and utility-status application rules remain intact.

Optional animation-pack metadata provides content-hash URLs, SHA-256 verification and bone-binding checks. Missing/corrupt/incompatible packs retain embedded and procedural fallbacks. Other classes retain their profiles. No paid assets, character redesign, enemy animation overhaul or deployment is included.

The third pass expands shoulder loads, lateral sweeps and follow-through while increasing strike-only torso rotation. Source multipliers are authoring targets; arm-reach constraints limit the final wrist displacement. Spell gestures and contact markers are unchanged.
