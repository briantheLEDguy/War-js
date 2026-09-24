# Supplied animation replacement

The active source contract is all **44 FBXs** in `AnimationImport/Two-handed`,
`swordandshield` and `Spellcast`. `animation_replacement.py` records exact names,
style templates, four character recipes and forty ability presentations. FBXs and
native Content remain private, ignored assets.

| Profile | Equipped presentation | Movement |
|---|---|---|
| Battle Prelate | Established body, armor and two-handed hammer | Two-handed |
| Sunfire Templar | Male Empire body, articulated plate, blue tabard, sun heraldry, sword and shield | Sword and shield |
| Warbrute | Existing Greenskin body and armor, cleaver and scavenged shield | Sword and shield |
| Ember Arcanist | Existing body, robes and staff | Spellcast |

Hybrid abilities select weapon or Spellcast choreography individually. Equipment
moves between hand and back bindings for free-handed casts. The three spell
attacks provide projectile, focused/channelled and broad ritual families. Shield
idle derives from the new block pose; caster backward movement reverses the new
walk; caster jump and landing adapt the supplied two-handed jump. No missing
state falls back to an old character clip.

## Pipeline and ownership

```powershell
python scripts/unreal/animation-pipeline.py supplied-four --review
python scripts/unreal/animation-pipeline.py supplied-four --from-stage verify
python scripts/unreal/animation-pipeline.py sunfire-templar --from-stage retarget --review
```

`--unreal`, `--blender` and `WAR_UNREAL_EDITOR` override executable locations.
Recipes live in `scripts/unreal/animation-recipes/`; reusable locomotion templates
live in its `styles/` directory. The all-character recipe also migrates admitted
humanoid NPC rigs. Character recipes restrict retargeting, fitting and composition
to that profile. Logs and receipts live in `artifacts/unreal/animation-replacement`.
Run Unreal mutation stages sequentially with other Editor/proof processes closed.

1. Inventory every FBX's SHA-256, skeleton, duration, frame rate and hip travel.
2. Prepare animation-free bodies and separately imported equipment. Templar
   additions use the established human body/rig and baked material channels.
3. Retarget onto each body's own skeleton. Preserve rest scale and limb lengths.
   The current humanoid rig has a 100x root above metre-space bones; this
   correction must not be assumed for another rig.
4. Fit the Prelate support hand to the hammer shaft without stretching bones.
   Its 72 cm shaft correction belongs only to that character.
5. Compose preparations, combinations, holds and full recoveries. Both Smash
   variants share one authoritative contact time and recovery duration. Remove
   horizontal source travel; the capsule owns slide, charge and leap movement.
   The airborne sword-and-shield chains transfer their sampled vertical travel
   into the swept capsule. Landing adaptations keep the feet at physical ground.
   Contact markers are measured against the equipped hammer, sword and cleaver;
   the second hammer slash supplies Sanctified Blow's distinct finishing motion.
   The final descending shield-combo strike owns its damage event.
6. Install visual definitions and `Content/Migration/visual-imports.json` together.
   Each playable has ten ability bindings. Unknown active rigs fail installation.
7. Verify skeleton associations, raw/compressed poses, finite transforms, limb
   lengths and recovery; render equipped front/side views.

`SuppliedPoseCompressionV1` has a stable codec identity and scale-aware settings.
`WarImportLibrary.finalize_animation_sampling` synchronizes authored tracks and
platform compression rates. Body import is separate from animation: character
GLBs with embedded tracks are rejected. `convert-model.py --verify-existing`
checks retained, track-stripped FBXs without re-exporting their meshes. New body
import receipts verify reference poses and contain an empty animation array.

## Native runtime

`WarAnimationInstance` extracts and blends supplied poses. `WarCharacter`
selects directional locomotion, turn-in-place, jump/landing, directional reactions,
actions and death. Locomotion phase follows measured speed. The server chooses
the variant and replicates its identity, serial, start, duration and equipment
state. Clients evaluate poses against the server clock, including late joins.
Drawn and stowed equipment use native bone sockets. Supplied preparation and
recovery poses carry the equipment by its grip around the torso, with fixed-length
arm fitting before the back attachment takes over. Equipment updates after bone
finalization using the evaluated pose's time, including parallel evaluation;
death releases it beside the corpse above ground. Structural checks also compare
the hand and back transforms at each attachment handoff.

`WarAbilityRuntime` owns contact/release events, interruption and capsule motion.
Sweeps reject obstructed travel before spending resources; new obstructions cancel
pending contact. Smash shares one capsule trajectory across both variants,
rejects insufficient overhead clearance and removes duplicate pose lift.
The ten-slot bar and existing controls remain.

`WarWrathRelic` implements Icon of Wrath: 14-second cooldown, 15 mana, five-metre
radius and ten-second lifetime. Its authored relic heals allied living players
and participant bots for 10% of actual hostile health damage while in range and
line of sight. Overlaps do not stack; encounter NPCs, overheal and recursive
healing are excluded. Replacement, death, disconnect and zone exit remove it.

## Removal and verification

`migration/animation-removal.json` preserves textual provenance and before/after
hashes. GLB, Blender and binary FBX cleanup verifies that meshes, materials,
skinning, corrective shapes and rest rigs survive. Animation-only sources,
obsolete native sequences/graphs, duplicate imports, backups and obsolete
generators are deleted. The standalone `AnimationImport/Spell Cast.fbx` is
deleted. Environmental door/gate/mechanism animation and Git history remain.

The [storage cleanup](model-storage-cleanup-2026-09-24.md) additionally removes
obsolete model iterations and inactive checkouts. The removal check scans
extensionless recovery objects and Blender version backups without following
junctions. Current approved authoring releases remain required inputs.

```powershell
python scripts/unreal/publish-animation-removal.py
python scripts/unreal/verify-animation-removal.py
npm run unreal:test-native
npm run unreal:test-native -- --capture-animations
npm run unreal:animation-network-proof
python scripts/unreal/publish-animation-coverage.py
```

Run `verify-complete-animation-replacement.py` through the Unreal Python commandlet
for the complete installed playable/NPC check, equipped ground measurements and
fresh asset-registry, redirector-dependency and populated-map checks.
`measure-equipped-motion.py` samples every LOD0 equipment vertex at 30 Hz, including
stow transitions and capsule-owned leaps, and rejects ground penetration. This
ground check does not replace body/armor clearance review.

`SuppliedAnimationGameplay` executes forty abilities and both Smash variants for
player and participant-bot fixtures, then movement, turns, jump/landing, reactions
and death. It checks contact timing, recovery, interruption, obstacles, released
equipment and production respawn for all four selected profiles.
The optional capture pass waits for actual mesh and shader compilation, then
records the production actors at preparation, contact and recovery from two
views, plus movement/reaction/death/respawn. Its images and execution times are
in `Saved/AnimationGameplayCapture/frames.json`; snapshots do not independently
grant production art approval.
`IconOfWrath` tests actual-damage eligibility, occlusion, overlap and cleanup.
The loopback proof requires both clients to evaluate all 41 variants and a
delayed client to observe an action in progress. Received identities and
start/duration values are compared with the authority. Pose receipts are published
after Unreal completes evaluation and include the server time sampled by that
evaluation. The proof checks phase against that timestamp and rejects poses older
than one frame plus 50 ms; asset-loading hitches cannot be mistaken for clock drift.
State selection runs at pose preparation, so movement-triggered mesh updates do
not reuse the previous pawn tick's action time.

`publish-animation-coverage.py` requires every source to have recorded player
and bot execution, all forty abilities to execute, structural checks to pass and
late-join synchronization to be verified. Its public manifest links source
hashes to private receipts and exact scenario indices. Importing a clip or
placing it in a preview never counts as gameplay coverage.

Review equipped renders and complete movement/contact/clearance evidence before
visual acceptance. Windows development proofs do not approve Steam admission,
Linux/macOS packages or three-platform release gates.
