# Native campaign enemies

The capitals also contain six [passive combat training targets](unreal-training-dummies.md)
with their existing static dummy models, no rewards and a 15-second respawn.

The main Sunmeadow March generated level contains its three original Campaign
Raiders, using `enemy_aegis_campaign_raider_raider`. These are development
encounters; source special attacks, navigation, grip/art review and network
combat acceptance remain open. No zone is complete. Cinderfen's raider and field
officer profiles are absent from the approved source registry and were not
substituted with another identity.

## Runtime

`AWarEnemy` reads exact zone/enemy identity and statistics through
`WarEnemyRules`, then validates its visual against the imported mesh, animations
and source fingerprint. Ordinary melee raiders and the exact passive capital
training targets are supported. Creatures,
casters, guards and keep commanders cannot silently use this behavior.
Incomplete visuals disable the actor and block server zone readiness; a client
with mismatched enemy content disconnects rather than displaying an invisible
attacker. This is a development content-error path, not durable online recovery.

The server selects a visible living player in the same zone, sweeps movement
through CharacterMovement, refuses ledges, checks line of sight/range for hits,
and resets enemies that lose their target, exceed the source 25 m leash or stop
making progress. This is direct collision-aware chasing, not completed navmesh
pathfinding or patrol authoring. Source health, damage, speed and ranges are
preserved; ordinary hits use the source 2–2.5 second interval and damage variance.
The source raider Hamstring special is still missing.

All three raiders now carry source-derived patrol spears through the exact
[combat NPC equipment catalog](unreal-npc-equipment.md). Missing required equipment
blocks their combat readiness. Attachments follow the imported hand bones through
idle, run, attack and death, and are rebuilt without duplicates after zone reload.

The player's existing development strike accepts enemy actors as well as player
characters. The server still validates targets before spending mana or starting
cooldowns. Enemy health, movement, death and attack animations replicate. The
HUD draws nearby visible enemy names, levels and health from replicated state.
Class-specific player abilities and final encounter balance remain separate work.

`WarEnemyRewards` awards source XP (`20 + level * 10`), source-table random loot
and matching active quest counters in one inventory revision. Each death has a
server-generated GUID. Duplicate events fail without changing rewards or quest
progress. A full bag retains loot in the existing pending-reward queue. Attribution
is to the living player delivering the lethal hit; party sharing is not implemented.

`UWarEnemyStateSubsystem` retains health, death GUID and the 15-second respawn
deadline across level unload/reload for the current server session. Respawn
validates floor slope and capsule clearance and creates a new death GUID only
after a safe landing succeeds. Reused streamed actors retain their original home.
This state is not durable across a server restart.

Zone readiness additionally waits for blocking physics state and traces the
authored portal arrival surfaces. Visible-level state alone is insufficient during
rapid unload/reload. The existing per-player streaming and final landing validation
remain in force.

## Reproduce and verify

Close the saved Unreal project before modifying native modules or saved levels.
Use the main AegisWar project throughout.

1. Convert the exact profile with `convert-model.py`, then run
   `npm run unreal:import -- --profile enemy_aegis_campaign_raider_raider`.
   Raw and compressed animation parity are required; import evidence is not art approval.
2. Run `populate-world-enemies.py` in the unattended Unreal Python commandlet.
   It checks source/package/import fingerprints, backs up the generated level,
   places the three source identities and records component snapshots.
   Matching reruns log `WAR_WORLD_ENEMIES_UNCHANGED=3`; changed actors cause a
   conflict instead of being overwritten. Authored capital content is untouched.
3. Run `render-world-enemies.py` with commandlet rendering, then inspect the
   three player-height captures. It checks saved identities, grounding and map
   fingerprint stability. The current captured model remains too dark on its
   shaded side and needs grip/material review; visual approval stays false.
   `verify-npc-equipment.py` separately captures and checks the equipped NPCs.
4. Launch the main map with `-game -WarDevelopmentGM -WarEnemyProof -nullrhi`.
   Require `WAR_ENEMY_PROOF passed=1` and the fresh
   `Saved/EnemyProof/report.json`; an engine exit code alone is insufficient.
   This opt-in proof uses elevated player health to observe a complete lifecycle,
   not to establish combat balance. It covers range/zone rejection, chasing,
   leash reset, repeated strike cooldown, actual damage, eight-hit death, full-bag
   reward handling, invalid/repeated rewards, unloading, reload cooldown and respawn.
5. Run native automation, the 70-route portal proof, two-client zone proof,
   `inspect-world-coverage.py`, `verify-world-character-imports.py`, tooling tests,
   typechecking and the Unreal audit. Keep strict release checking blocked.

Local receipts live under `artifacts/unreal/world-portals/`: `enemy-placement.json`,
`enemy-render-verification.json`, `enemy-live-proof.log` and the current coverage
and zone manifests. Production Steam, platform, performance and durable recovery
acceptance are not granted by these checks.
