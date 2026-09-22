# Capital combat training dummies

Each capital contains its three existing source targets: Training Dummy (60 HP),
Heavy Training Dummy (120 HP) and Dueling Target (90 HP). Bastion's targets are
beside the training yard at source x=38/47/56, z=-124. Riftspire's targets use the
training terrace at x=-30/-21/-12, z=-32, y=-105. Source metres map to Unreal
centimetres as (z, x, y), plus the zone origin.

The exact models are `prop_training_dummy_t1.glb` for Bastion and
`prop_riftspire_training_dummy.glb` for Riftspire. Native static meshes retain
all source geometry and ordered materials. The Aegis object hierarchy is baked
at rest; its object-animation clips are not activated. Neither model substitutes
for missing humanoids or creatures. Missing or mismatched dummy bindings block
zone readiness through the existing recoverable content-loading path.

`AWarEnemy` admits these identities as passive targets. The existing server strike
checks range, zone, visibility, player state, mana and cooldown. Targets never
chase or retaliate, grant no XP/loot/quest credit, and respawn after 15 seconds.
Health, death and visibility replicate; session life state survives streaming.

`scripts/unreal/capital_training_dummies.py` extracts the source geometry.
`populate-capital-dummies.py` checks source/package ownership, backs up both
Generated capital levels, imports exact meshes and appends the six actors and
visual bindings. It leaves Authored levels intact. Matching reruns verify their
saved snapshots; mismatches fail instead of overwriting owner edits.
`render-capital-dummies.py` checks grounding, captures all six at player height
and verifies that rendering did not change saved maps.

Run these Python scripts using the main project's unattended Unreal Python
commandlet; rendering also needs `-AllowCommandletRendering -RenderOffscreen`.
Close the editor before native builds or saved-level changes.

Verification:

- `python tests/unrealCapitalDummies.test.py`
- `npm run unreal:build` and `npm run unreal:test-native`
- Launch the main project with `-game -nullrhi -WarDevelopmentGM -WarTrainingDummyProof`.
  Require `WAR_TRAINING_DUMMY_PROOF passed=1 targets=6` and the fresh
  `unreal/AegisWar/Saved/TrainingDummyProof/report.json`. This fixture loads each
  capital and validates a melee approach directly; it does not certify GM travel.
- `npm run unreal:audit`, `npm run test:unreal`, `npm run typecheck:unreal-tools`.

Local placement and visual receipts live in `artifacts/unreal/capital-dummies/`.
These are development fixtures; Steam, three-platform, multiplayer combat and
final art acceptance remain separate release gates. Bastion's existing yard
lighting leaves its targets dark in the captures; world lighting is unchanged.
