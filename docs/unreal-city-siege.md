# Bastion of Aegis siege

This increment adds native siege rules, replicated state, a development game
mode, bots, encounter logic and a HUD. **It is not a verified playable siege.**
The isolated map now includes bound blockades, objective props and checked
navigation. Complete equipped rosters, encounter visuals, traversal review and
multiplayer acceptance remain outstanding. No release gate is approved.

## Scenario and balance

Riftbound attacks; Aegis defends. Fixed capacities are 6, 12 or 18 per realm,
including bots. Encounter NPCs never occupy slots or contribute capture weight.

1. Lower city: capture supplies, escort engineers through two checkpoints and
   protect the gate breach. Kill the emplacement crew and sabotage its position
   to permanently remove that defense.
2. Courtyard: disable two mechanisms sequentially and protect engineers at gate
   controls. Capturing the reinforcement post halves later defending waves.
3. Inner citadel: kill the commander. Frontal and ground attacks telegraph for
   three seconds; stagger/silence interrupts rally. Sabotaging the beacon halves
   rally summons. Defenders cannot heal the commander. Fifteen seconds without
   an eligible attacker in chamber range and sight resets health and summons.

Stages last 14 minutes with 60-second transitions. Aegis wins by holding any
stage. Final-objective activity grants at most two minutes of overtime, ending
after ten seconds without activity. Commander activity requires recent damage.

- Major NPC health scales 1x/2x/3x. Individual attacks stay constant. Guard waves
  contain 2/4/6 soldiers with two waves living at most; sabotage halves them.
- Capture takes 90 seconds alone. Rate is `min(2.5, 1 + .25 * (count - 1))`.
  One defender pauses it; ten seconds without attackers starts 5%/second decay.
  Completed milestones persist. Escort speed caps at 1.5x, pauses when contested
  and requires the physical crew to arrive. Dead crews return after 30 seconds
  at the last checkpoint, resetting unfinished work.
- Twenty-second respawn waves replace bots with arriving humans and backfill
  departures. Capacity never changes midmatch.
- Temporary combat normalization uses level 40, strength 100, health 2000 and
  mana 1000. Persistent rewards, equipment changes, consumables and saved GM
  level changes are blocked while normalized. Reset restores ordinary attributes.
- Reference damage is initially 50/second: commander health 36,000 and crew
  health 2,000 in 6v6. These are tuning defaults, not measured encounter durations.
- Bots fill toward one tank, one healer and four damage roles per six players.
  Squads contain at most six; excess bots operate without a human. Hazard
  avoidance and defensive/healing actions precede nearby combat, then objectives.
  Retreat starts below 25% health and ends at 60%. Pursuit is limited to 25m from
  the leader/task. Enemy participants take priority over encounter NPCs.
- Siege healing can target an allied participant within 20m and line of sight.
  Campaign healing retains its previous behavior. Siege target cycling includes
  allies; hostile ability validation still rejects friendly targets.
- Capture participation requires objective line of sight as well as radius and
  floor-height proximity. Encounter spawns project onto navigation before
  spawning; missing reachable ground fails recoverably.

## Native architecture and authoring

`WarSiegeRules` owns progression and bot decision rules. `WarSiegeGameMode`
samples server actors, fills slots, runs encounters and publishes
`WarSiegeGameState`. `WarSiegeBotController` uses native character abilities and
navigation. `WarSiegeBattlefield` is the version-1 map definition; `WarSiegeHud`
shows objectives, overtime, wave timing, roster and attack telegraphs.

Run `scripts/unreal/stage-aegis-siege.py` through UnrealEditor-Cmd's Python
commandlet to duplicate the selected Crownward map into
`/Game/Capitals/Siege/AegisCapital_Siege`. The script refuses to overwrite an
existing draft, leaves startup map settings unchanged and writes
`artifacts/unreal/siege/authoring.json`. Generated assets remain private/ignored.

The draft has eight objective anchors, three optional anchors and six team
spawns. The local authoring pass now binds two supply-crate blockades, two chain
controls and three optional props from existing authored assets. Four braziers
light the inner hall. These are provisional encounter dressing, not visual
acceptance of the finished siege.

The authoring sequence is `stage-aegis-siege.py`, `inspect-aegis-siege.py`,
`isolate-aegis-siege.py`, `build-siege-navigation.py`,
`author-siege-objectives.py`, `light-siege-hall.py`, then another navigation
build and `render-siege-map.py`. Map and objective creation scripts refuse to
overwrite existing authoring; hall lighting can reapply its owned clearance and
light settings. The editor-only `WarSiegeAuthoringLibrary` builds navigation and
assembles existing meshes. Its navigation helper removes inherited empty
campaign streaming records, which actor-only inspection cannot detect, and
builds only in the exact isolated siege map. The saved world contains the
persistent siege level and its private city geometry copy. Source campaign
packages remain untouched. Receipts and offscreen renders live under
`artifacts/unreal/siege/`; generated Content remains private and ignored.

All 17 required anchors have passed native navigation projection and connectivity
queries. The inner defender spawn was moved from a disconnected surface to the
reachable eastern court. Static navigation includes the through-route at each
blockade; physical collision closes it until the server opens that stage.
Navigation connectivity does not establish jump-proof gates, squad crowd flow,
combat clearance or visual approval. Bind approved realm/role and encounter
visuals and finish those checks before setting the review flags.

With this map using `AWarSiegeGameMode`, authorized local development GMs use
`WarSiegeStart 6 1` (capacity, roster-selection seed) and `WarSiegeReset`.
Existing standalone GM restrictions remain; remote roles and production
admission are not enabled. Missing content and critical spawn failures block
launch or return a recoverable error. The seed does not control all combat RNG.

Logs use `WAR_SIEGE_START`, `WAR_SIEGE_STAGE`, `WAR_SIEGE_PROGRESS`,
`WAR_SIEGE_DEATH`, `WAR_SIEGE_COMMANDER_RESET`, `WAR_SIEGE_RESULT` and
`WAR_SIEGE_BLOCKED`; bot decisions use verbose `WAR_SIEGE_BOT`.

## Verification and unfinished acceptance

Native automation covers `AegisWar.Foundation.SiegeRules`, `SiegeBotRules` and
`SiegeAuthorityAndNormalization`. Run the Editor build, `unreal:test-native`,
`npm test`, `test:unreal`, all three typechecks, `unreal:audit`, `world:validate`
and `models:validate`.

Verified on Windows on 2026-09-24: Editor build succeeded; all 47 native tests,
598 general tests and 112 Unreal-tool tests passed. All three typechecks,
migration audit, 33-zone world validation and 906 model validation records
passed. Native report: `artifacts/unreal/editor/test-1790239214356-25860`.
The first native run exposed a double-initialized test world; the corrected
fixture passed the full rerun. The isolated map was actually generated, with
its unresolved authoring requirements recorded in `artifacts/unreal/siege/authoring.json`.
These checks do not verify full siege gameplay, network operation or visuals.

The animation replacement provides equipped Battle Prelate, Sunfire Templar,
Warbrute and Ember Arcanist profiles, with player and participant-bot execution
checks. It does not establish complete balanced rosters for both realms or
commander/crew/garrison readiness. See `unreal-animation-import.md` for the
per-profile motion, equipment and gameplay verification.

Still required: complete approved class/NPC equipment; finished gate and defense
presentation; route/arena and crowd-flow review; native 6v6/12v12/18v18 play; network
join/reconnect/slot handoff/late-replication tests; spawn-protection and healer
playtests; commander balance; richer emplacement presentation; Steam and three
platforms. Normalized stats are not approved visual equipment loadouts for all
classes. Long-term bots, rewards and campaign outcome integration remain deferred.
