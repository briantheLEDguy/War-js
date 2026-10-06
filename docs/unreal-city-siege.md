# Bastion of Aegis siege

City scenery is shared with the current campaign and loading/menu views through
`UWarCityDefinition`; the siege map contains only its gameplay overlay and navigation.
See [shared-city migration and verification](unreal-shared-cities.md). Historical
receipts below describe their original revisions and do not approve changed city content.

## Reference replacement and version 2 rules

The current implementation work is described in
[the reference citadel guide](unreal-aegis-citadel.md). New `lower_city` allocations
retain that public identifier, gathering/acceptance windows, reconnect reservations
and character-return behavior, but select **Siege of Bastion of Aegis**, 18 seats
per realm and the full siege. Allocation requires fresh full-siege evidence and
fails recoverably while that evidence is unfinished. Historical 6v6 rounds retain
their recorded version 1 definition.

Version 2 captures supplies, two convoy checkpoints and the outer breach, then
allows both side objectives to progress independently. Side claims persist;
unfinished progress retains contesting and absence decay. Both claims unlock a
player-only central plaza capture, which opens the keep and commander encounter.
Optional defenses never substitute for a required claim. The shared timers remain
90-second solo captures, 14-minute stages, 60-second transitions and bounded
overtime. `AWarSiegeEncounter` owns execution and replicated progress; the scenario
GameMode and live campaign bridge adapt that same runtime.

The live campaign bridge uses normal character stats and equipment, opt-in seats
capped at 18 humans per realm, and 180 seconds of preparation for enrollment and
evacuation. Trusted Node eligibility requires the enemy T4 front, inner T4 zone
and fortress. Only the owning native host with a current activation and content
revision can checkpoint or settle conquest; ordinary queued wins cannot do so.
The legacy Node city-combat branch is suspended while a native lease owns the
encounter. Expired ownership pauses recovery rather than letting legacy combat
invent a result.

`npm run server:dev -- --native-siege` provisions the private host configuration
under `Saved/CampaignSiege/host.json`. Launch the development campaign authority
with `-WarCampaignSiegeHostConfig=<absolute-file>` after fresh admission checks.
Keep host credentials private. Native lifecycle checkpoints save full character
documents atomically with siege claims/clocks, preserve dead/respawn intent and
require restoration acknowledgement. Critical inventory, equipment, progression,
quest and reward changes flush a full-document native write-ahead record before
reporting success. Only the owning host can replay its next sequence against the
saved character revision; conflicts retain protected recovery. Stable, explicitly
provisioned development identities are required for live enrollment. Actual
interrupted native recovery, transient combat-effect reconstruction and physical
returns still require acceptance evidence. Production Steam identity, cross-platform builds and release
acceptance remain separate.

The remainder of this document records earlier lower-city implementation and
proofs; those receipts do not approve the replacement or its later stages.


The isolated lower-city development scenario has native rules, replicated state,
six equipped class choices, bots, encounter logic and preparation/combat/results
UI. Local lower-city admission is restored using current city/map hashes,
twelve-character physical routes, the replicated convoy and gate-passage proof,
and reviewed client captures. Navigation projection alone does not grant review.
Full three-stage siege,
Steam, three-platform and release acceptance remain outstanding.

`scripts/unreal/repair-shared-city-siege.py` backs up the siege overlay and
reconciles its convoy staging and ramp checkpoint with the surveyed shared city.
Navigation authoring excludes complete multipart supply props with pedestrian
clearance; their narrow gaps must not produce paths through physical collision.
Gates remain physical obstacles until their authoritative milestone opens them.
The convoy proof starts at the same authored positions as runtime gameplay and
checks capsule collision at both gates on the server and rendered client.

Local admission through `admit-lower-city.py` requires fresh traversal, convoy,
client and rendered evidence in `artifacts/unreal/shared-cities/siege-review.json`.
Each physical report must match the current city revision and overlay hash; the
review also hashes its captures. Admission preserves historical caster evidence,
records the reviewed city on the native battlefield and publishes the updated
map hash after saving review flags. It never approves the full siege or release.

## Scenario and balance

### Lower-city development round

The separate `LowerCity` scenario ends immediately on the outer gate breach;
the original `FullSiege` scenario still advances through all three stages.
Lower-city development rounds use six slots per realm, the existing 14-minute
timer and bounded overtime. Results include elapsed time, objective completion
timestamps, contested time and deaths. No persistent rewards are awarded.

**Main game entry:** start `npm run scenario:host`, enter a character normally,
then open **Escape → Scenario**. Ready and queue alone or with a same-realm party.
Accept the offer to enter a separate 6v6 match with your current character; bots
fill unused seats. Leaving or completing the match restores campaign state and
return position. Scenario is no longer available from the login screen.

`WarScenarioSession` connects to the shared Node coordinator; it no longer starts
private servers. `WarScenarioInstance` validates single-use character tickets.
See [queue setup, recovery and verification](unreal-scenario-queues.md) for the
current implementation and development network restrictions. The older direct
lobby and two-client launchers remain isolated verification fixtures.

`npm run unreal:scenario-menu-proof` exercises current character entry, queue,
acceptance, instance travel, squad movement and return. `-- --party` adds an
invited same-realm party, and `-- --instances` checks simultaneous matches.
Receipts remain under `Saved/ScenarioMenuProof/` and
`artifacts/unreal/scenario-menu/`. The following older receipts describe the
previous login shortcut and do not establish acceptance of the new queue flow.

Menu integration verified on Windows on 2026-09-26: the Editor build and all 63
native tests passed (`artifacts/unreal/editor/test-1790447158180-26104`). The
rendered proof selected both realms, readied into live 6v6 rounds, used the field
menu's Leave scenario action, returned to entry and cleaned up both owned
servers. Its eleven screenshots were generated; the main menu, selection,
lobby, gameplay, leave panel and returned menu were visually inspected. Receipt:
`Saved/ScenarioMenuProof/f3c71c7d7e394b91ac419ad0700f73bb/report.json`.
The 668 general and 132 Unreal-tool tests, all three typechecks, migration audit
and world/model validation also passed. Release checking still reports four
outstanding acceptance categories.

After closing the Editor and building the Editor target, run
`npm run unreal:siege-playtest`. The launcher starts an Editor dedicated server
bound to `127.0.0.1` and two rendered clients, admitting Aegis first and Riftbound
second. Each player chooses tank/healer/damage and presses Ready. The server
revalidates content and requires both humans to be ready; bots fill empty slots.
After a result, Ready for rematch retains selections and resets round state.
Closing a client or interrupting the launcher cleans up its own processes.
`-- --width 2560 --height 1080` changes client dimensions; `-- --dry-run` launches
nothing. `-- --smoke` checks headless two-client admission and reports content
blockers; it cannot certify gameplay or visuals.

For the separate two-client fixture on this prepared Windows checkout:

1. Close Unreal Editor, then run `npm run unreal:siege-playtest` from the repository.
2. Choose a class and press **Ready in each of the two windows**. The first window
   is Aegis; the second is Riftbound. Bots fill the remaining ten participant slots.
   Use Alt+Tab to switch clients if their windows overlap.
3. Move with WASD, hold the right mouse button to look, jump with Space, select nearby combatants
   with Tab and use abilities with 1–0. V enables the action-bar cursor. Current
   saved bindings take precedence; Escape opens settings. Target an ally to heal.
4. Riftbound captures supplies, escorts the engineers through two checkpoints,
   then breaches the outer gate. Aegis contests those objectives until timeout.
   Deaths return on twenty-second waves. The result screen supports class changes
   and **Ready for rematch**. Close either game window to end the local session.

This uses the already built Editor target and private Content in this checkout.
A fresh source clone also needs the reviewed native Content; missing models are
reported instead of replaced. It does not require the account gateway or Steam.

`-- --automated` runs two rendered offscreen clients through three normal-timed
rounds and two rematches, selecting damage, tank and healer in order. Allow up to
55 minutes. In round two, the Aegis driver prioritizes defending the optional
emplacement; the other rounds prioritize the main objective. `WarSiegePlaytestProof` exists only with explicit development test
flags: the server supplies navigation hints; clients use normal movement and
ability RPCs. It never changes health, capture rules, timers or results. Reports
require real movement/actions and three replicated results. Screenshots and
client receipts are under `Saved/SiegePlaytestProof/<run>/`; launcher logs and
the combined receipt are under `artifacts/unreal/siege/playtests/<run>/`.
The server's `state.json` updates every ten seconds with objective and actor
movement/health diagnostics; each client refreshes a live capture every minute.
Automated completion does not claim a human playtest or balance approval.

`WarSiegeSession` owns this development lifecycle. Client ready and class-choice
requests include the observed round ID and cannot launch an active round, grant
GM privileges or supply results. Existing remote/Shipping admission denials stay
in force. `WarSiegeLobbyWidget` owns preparation/result input; `WarSiegeHud`
displays live objectives. New native tests cover lower-only wins, timeout,
overtime, repeated rules rounds, gate state and unauthorized lobby requests.

Local roster: Sunfire Templar/Battle Prelate/Ember Arcanist against
Warbrute/Ruin Oracle/Void Magister. Caster adaptations use retained Chaos sources
and use separately owned native assets. Summon Idol creates an authored, replicated
native deployable: one idol per owner, 30-second lifetime, one nearest-hostile
pulse every two seconds within 12 metres, and a 20-metre owner leash. Placement
checks ground, line of sight and actual model bounds before spending resources.
Feed the Idol modifies live pulse damage through the existing empower status.
Death, disconnect, zone changes and round reset remove it. Missing native content
fails recoverably. The retained Node simulator still explicitly rejects this
native actor ability; it does not simulate a fake pet.

Verified on Windows on 2026-09-26: the rebuilt Editor target and all 63 native
foundation tests passed (`artifacts/unreal/editor/test-1790443074107-8944`).
`SiegeSpawnClearance` covers occupied positions, adjacent clear positions, floor
clearance and static obstructions. `WarpIdol` covers targeting, placement, empowerment and
lifecycle; `SiegeCasterGameplay` executes both complete ten-ability kits for
player and bot controllers, including actual Hover Disc travel and idol pulses. The
earlier loopback smoke run admitted both clients and correctly refused launch
before traversal and equipped-roster review. The launcher also
requires each client to construct its replicated preparation UI before reporting
startup results; networking admission alone is insufficient.

The rendered two-client run completed three normal-timed rounds and two rematches:

| Classes | Result | Duration | Milestones | Deaths |
| --- | --- | --- | --- | --- |
| Ember Arcanist / Void Magister | Aegis held | 840.1 seconds | 1 of 4 | 67 |
| Sunfire Templar / Warbrute | Riftbound breached | 546.3 seconds | 4 of 4 | 19 |
| Battle Prelate / Ruin Oracle | Aegis held | 840.0 seconds | 1 of 4 | 28 |

Both clients received identical results, moved through normal input and issued
433/683 ability requests. The launcher validated both receipts and exited
successfully, cleaning up all three owned Unreal processes. No runtime match
blocks or spawn failures occurred. Receipt:
`artifacts/unreal/siege/playtests/1790443165008-17348/automated.json`.
The 720p preparation, combat and result captures were inspected. This verifies
the local network round lifecycle and both endings; human balance acceptance
remains separate.

The final HUD build also passed a short rendered 2560×1080 check. The objective
panel follows the radar's scale and world labels cannot paint over its text.
Closing the owned Aegis test client caused the launcher to stop the matching
server and Riftbound client. This deliberately interrupted visual/cleanup check
is separate from the completed three-round receipt above. Captures:
`Saved/SiegePlaytestProof/93614b3618214b27a54d0637ed6e439f/`.
The same final build passed the default 1280×720 visual and cleanup check in
`Saved/SiegePlaytestProof/21a3b094aec445aab34e4deffb70045d/`. The consolidated
local receipt is `artifacts/unreal/siege/local-playtest-verification.json`.

The six class entries are bound in the isolated map using
`scripts/unreal/stage-siege-roster.py`. That script refuses to overwrite a
different roster or a reviewed battlefield. It never sets either review flag.
Both caster imports passed structural pose checks, with 160 native equipped
review frames covering movement, preparation, contact and recovery. Intersecting
hanging cloth was removed in favor of the fitted source armor. Explicit source
adaptations supply a Riftbound breach engineer, equipped Aegis garrison and
hammer-equipped commander. Their staging and 25-frame native review receipts
live under `artifacts/unreal/siege/`. All 185 equipped frames were reviewed for
local development. `admit-lower-city.py` verifies that evidence, publishes the two
exact caster bindings and sets only `bLowerCityReviewed`. Both original full-siege
review flags remain false. The original source profiles and campaign maps remain
intact; no global release gate changed.

`WarSiegeNavigation` selects reachable approach positions with actual walkable
floor and capsule clearance. Siege bots use Unreal crowd following and wider
objective spacing; route-stall recovery never teleports actors. Run
`npm run unreal:siege-traversal-proof` after an Editor build to exercise twelve
visible, colliding siege characters: jump/landing, all four lower-city objectives,
sabotage and both directions between team spawns. The isolated loopback fixture
uses the same controller and approach selection as gameplay. It fails on stalls,
partial paths, missing visuals or disabled collision, and saves per-character
movement evidence. Passing this focused route check does not set review flags or
certify combat, later siege stages, network behavior or three-round acceptance.

The 2026-09-26 run passed all seven routes for all twelve characters, with actual
jump/landing, capsule collision and movement throughout. Receipt:
`artifacts/unreal/siege/traversal/1790436547282-3992/report.json`. Earlier failed
runs exposed tight crowd spacing and prop clearance issues; the final run uses
the same corrected crowd controller and slope-aware approach checks as bots.

Repository verification also passed: 668 general tests, 132 Unreal-tool tests,
seven Python animation checks, all three typechecks, world/model validation and
the migration audit. The updated launcher has five passing focused tests.
Release-check remains blocked by the four outstanding acceptance categories.

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
  and requires the physical convoy to arrive. Dead lower-city engineers return
  after 30 seconds at the stopped equipment, resetting unfinished work. Equipment
  stays in place; completed checkpoints and ownership remain claimed.
- Twenty-second respawn waves replace bots with arriving humans and backfill
  departures. Respawns search nearby walkable, capsule-clear positions, including
  occupancy by other characters. Participant positions stay inside the protected
  spawn area; a temporarily full area defers human respawn to the next wave.
  Capacity never changes midmatch.
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

Beyond the local lower-city scope, still required: full approved class/NPC
equipment; finished gate and defense presentation; later-stage route/arena and
crowd-flow review; full-siege 6v6/12v12/18v18 play; network
join/reconnect/slot handoff/late-replication tests; spawn-protection and healer
playtests; commander balance; richer emplacement presentation; Steam and three
platforms. Normalized stats are not approved visual equipment loadouts for all
classes. Long-term bots, rewards and campaign outcome integration remain deferred.

## Siege equipment and ownership

`WarSiegeEquipment` replicates the battering ram and field catapult, their
engineer bindings, travelled distance and ram strike time. Two Greenskin
engineers push each engine. Authored wheel motion follows actual travel; the ram
uses its retained strike and suspension tracks at the outer gate. Vehicles use
navigation paths, ground sampling and a swept collision hull. Missing models or
unreviewed equipment produce a recoverable content error.

`WarSiegeConvoy` integrates the engines into the existing lower-city escort.
Attacker presence moves them at the ordinary participation rate. A defender,
missing escort, dead engineer or obstruction stops movement. The support engine
follows the ram, which waits if they become separated. Four engineers share the
previous 2,000-health crew budget in 6v6; replacements return to their engine after
30 seconds. The catapult is an escorted support engine; this change does not add
a player-operated artillery attack.

The convoy uses its own `SiegeConvoy` navigation agent (320 cm radius, 330 cm
height). The `Default` pedestrian dimensions now match character capsules at 42/192 cm. Run
`scripts/unreal/build-siege-navigation.py` through the Unreal Python commandlet
after changing the route or navigation settings; it builds both meshes in the
isolated Scenario map. Missing convoy navigation blocks Scenario admission.
The catapult follows the ram's travelled path through turns, and ground alignment
samples the full rotated chassis footprint before sweeping for obstacles.
The navigation radius includes the flat hull diagonal. Waypoints are reached
before turning, preserving the baked clearance; terrain-aligned hull sweeps still
reject collision beyond that flat footprint. The first admission path starts at
the authored ram staging position, matching actual runtime movement.

`WarSiegeBattlefield` replicates completed main and optional claims independently
of gate visibility. Eleven authored Riftbound war standards mark attacker control;
partial or contested progress does not raise a standard. Claims persist through
stage changes and results, and clear for a new round.

Run `python scripts/unreal/animation-pipeline.py siege-equipment --review` to
prepare/import private models and fit the retained supplied walk to the Greenskin
rig. Per-engine grip and posture corrections live in
`animation-recipes/corrections/engineer-push.json`; they do not change other
characters or restart procedural animation studies. Review the native frames,
record their hashes in the private `review/acceptance.json`, then run
`install-siege-equipment.py` through Unreal's Python commandlet. Installation
backs up the isolated map and preserves unrelated content. Generated Content
packages and review artifacts remain private.

`npm run unreal:siege-equipment-proof` exercises the actual equipment actors and
four engineers along both checkpoints and the breach approach, including missing
escort and crew-death stops. `SiegeOwnership` covers partial capture, contesting,
physical checkpoint requirements, results, rematch reset and optional ownership.
`npm run unreal:siege-equipment-network-proof` adds a rendered network client,
checks four replicated engineers and four completed ownership standards, and saves
convoy, checkpoint, ramp and gate captures under the equipment artifacts directory.
It also checks that repeated escort commands allow the ram strike to advance.
The native test also checks that slope alignment preserves steering yaw and keeps
all four chassis support points on a plane with both uphill and sideways grades.
These checks do not grant Steam, full three-stage or cross-platform acceptance.

The 2026-09-27 equipment network run passed:
`artifacts/unreal/siege/equipment/network/1790520059901-26644/`.
The ram travelled 260.16 m and the catapult 259.43 m through both checkpoints,
the ramp and the gate approach. The connected rendered client retained all four
engineers and showed four claimed standards. Server checks verified missing-escort
and crew-death stops, plus strike continuity at the gate. All 67 native tests and
136 Unreal-tool tests passed; the general suite passed 672 tests. The asset review
contains 20 equipped/mechanical frames and does not approve other character rigs.
The final Scenario menu run also passed for both realms, Ready-to-combat entry,
return to the menu and owned-server cleanup:
`Saved/ScenarioMenuProof/115f4514eb53429ab853f44c9f9d9dbb/report.json`.
