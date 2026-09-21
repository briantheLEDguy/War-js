# Native expedition quest rules

`WarQuestRules` ports acceptance, realm/level/prerequisite checks, zone-specific
kill counters, ready/completed transitions and all-or-nothing quest rewards.
`WarQuests.cpp` connects these rules to the owner-only character snapshot through
trusted C++ server methods. There are no client quest-reward or kill-report RPCs.
Acceptance and completion check the expected inventory revision; unique kill
receipts prevent repeated or pre-acceptance events from advancing progress.
Completion updates quest status, bag contents, XP, gold, stat growth and revision
atomically. Full bags leave the ready quest and every reward unchanged. Completed
quests cannot award again, even with a fresh revision. Unrelated pending campaign
gear remains separate from quest reward capacity checks.

`npm run unreal:quest-fixtures` executes the actual browser quest functions and
captures both complete four-quest expedition chains. Ordinary tests compare the
recorded results without rewriting them. Native automation replays the same
accept/kill/turn-in sequence against the exported definitions, comparing counters,
status, item placement/affixes, XP/gold and growth at each step. Rejection scenarios
cover other realms, missing prerequisites, wrong giver/kill/turn-in zones, repeated
acceptance/completion and full bags. The deterministic reward roll is 0.5.

The content subsystem now validates and caches the runtime quest catalog on
startup. Invalid identities, objective counts, zones, item references, affix ranges
and prerequisite chains fail content readiness. Catalog-based trusted commands
resolve quest definitions and rewards on the server, preflight turn-in capacity
and eligibility before rolling affixes, and retain atomic completion/retry checks.
The lower-level rule methods remain available for trusted tests/integration.
The trusted catalog methods are deliberately not exposed to clients or Blueprints.
`ServerInteractQuest` accepts only an NPC reference, quest ID, action and expected
revision. The server checks a living loaded pawn, NPC catalog identity, model
provenance, visibility, world, range and giver/turn-in identity before resolving
the existing atomic transaction. Clients cannot supply zones, rewards or kills.
Full campaign NPC placement, navigation, complete notifications and real enemy
attribution remain unfinished. Snapshot/receipt state is session-local;
durable reconnect/transfer settlement remains required. This is tested rules and
character-state integration, not a claim of playable quest parity.

`L` opens the native `WarQuestLogWidget`, a read-only view of the owning player's
replicated snapshot. It groups active/ready and completed quests and displays the
authored descriptions, current objective counts, XP/gold/item rewards and affix
ranges. It refreshes when the character or inventory revision changes and removes
stale rows when character ownership disappears. Unknown definitions produce an
unavailable message rather than silently hiding saved progress. Opening the log
closes inventory, and closing it restores gameplay input. Dragging, navigation
and full quest presentation remain unfinished.

`E` opens the closest valid quest NPC's dialogue before gathering/station actions.
The dialogue lists eligible offers, in-progress quests and ready turn-ins, with
revision-bound accept/complete buttons and quest-specific server feedback. Reward
capacity is previewed without changing inventory or rolling affixes; blocked
turn-ins explain the problem and disable completion until the snapshot changes.
Source range behavior is retained: strictly less than four metres, horizontal distance normally, and
foot-to-NPC height included for authored Riftspire crater-city floors.

The development scene explicitly maps Mara Vell and Ari Vell to the imported
female Empire herbalist source. Their distinct NPC/profile/zone IDs remain
unchanged. `prepare-proof.py` records these two development assignments in
`proof-map.json`; they are reuse candidates, not final wardrobe/art approvals.
These two placements share a proof scene and do not implement travel between
the capital and Brightfen. Riftbound NPC model coverage remains unfinished;
the Chaos dispatch officer is not replaced with a Dark Elf or Greenskin.
Entry validation rejects a placed quest NPC with missing/mismatched visual data.

The network proof now drives Aegis acceptance and completion through the owning
client's reliable RPCs. It sends missing/wrong NPCs, stale revisions and duplicate
requests, while the server checks exact catalog identity, source-compatible range,
alive/ready state and atomic rewards. The server still supplies scripted kill
events and moves the test pawn between the two development placements; this is
not real enemy attribution or zone travel. Riftbound still uses trusted catalog
commands because its quest NPC models are not imported.

`WarQuestHud` projects native `!` offer and `?` turn-in markers 2.6 metres above
authored quest NPC positions. `WarQuestMarkerRules` uses only the owning player's
snapshot and validated catalog, preserves realm/level/prerequisite eligibility,
and gives ready turn-ins priority. Accepted offers disappear; completion unlocks
the next eligible offer. Behind-camera/offscreen/hidden NPC markers are omitted.
Queries never change progress or publish another player's quest state. This
restores the world markers; minimap markers and route guidance remain open.

NPC transaction verification (2026-09-21): all 16 native groups passed in
`artifacts/unreal/editor/test-1789981764842-10700/`, including ambiguous/malformed
NPC catalog rejection. Windows packaging and the owning-client RPC proof passed
in `artifacts/unreal/network/1789981880477-28076/report.json`. The earlier
server-command proof's two screenshots (`1789981404172-33180`) were inspected for
readable completed quest details and visible authored NPCs. These are development
fixtures, not complete quest/world/visual acceptance.

Marker rule verification: 17 native groups passed in
`artifacts/unreal/editor/test-1789982005559-9536/`. The additional group checks
both realms, unknown identities, level/prerequisite/zone restrictions, accepted
offer removal, ready turn-in priority, next-offer unlocking and query immutability.
Interactive Editor review confirmed `E` dialogue, the Accept button, the accepted
message/in-progress state, offer-marker removal, and `L` showing the active quest.
Mara was moved closer only in the temporary Play-in-Editor world for this manual
check; stopping play discarded that transform. No authored map edit was saved.
Marker and message sizes were increased after that review. Ready/full-bag dialogue
screens and long-log scrolling still need graphical review.

The final marker/dialogue Windows package and multiplayer regression passed in
`artifacts/unreal/network/1789982458314-16964/report.json`. Both screenshots were
inspected: the Aegis client shows Ari's newly unlocked offer marker and completed
quest, while the Riftbound client does not see that private offer. NPCs can
overlap the proof camera; production camera/world-layout acceptance remains open.
The 74 tooling tests and tools typecheck passed. Release admission stays closed.

Use `npm run unreal:network-proof -- --packaged-root artifacts/unreal/packages/Win64
--rendered --quest-ui` to capture the quest log after both realms' catalog quest
transactions. It cannot be combined with `--inventory-ui`. Screenshots require
actual inspection; their existence alone is not graphical acceptance.

Quest log verification (2026-09-21): all 16 native groups passed in
`artifacts/unreal/editor/test-1789979574316-35696/`. Windows packaging passed and
the final two-client proof passed in
`artifacts/unreal/network/1789979658248-33152/report.json`. Both client screenshots
were inspected for title, objective text, 4/4 progress, rewards and readable close
control. Repeated inventory/log switching restores movement, camera and cursor
state on both clients. Local jump/strike requests now honor the modal input block.
Active/ready states, scrolling through long logs and interactive keyboard testing
still need visual acceptance. The 74 tooling tests and tools typecheck passed;
release admission remains closed with four blocker categories.

Verification on 2026-09-21: 74 migration tooling tests and tools typechecking
passed. All 16 native Foundation groups passed, including 76 browser-reference
quest snapshots and authority/retry/overflow tests, in
`artifacts/unreal/editor/test-1789976604249-29304/`. Windows Development packaging
also passed. A separate development network fixture checks that an accepted
synthetic quest replicates only to its owner; it does not exercise quest NPCs
or real enemy kills.

The packaged Windows two-client privacy/regression proof passed in
`artifacts/unreal/network/1789976836275-25396/report.json`. An earlier run
(`1789976621730-28668`) exposed overlapping respawn/quest observation phases;
the proof now allows the respawn phase to replicate before adding quest state.
The successful run verifies owner-only quest counters alongside movement, combat,
crafting, cultivation, progression and respawn. It uses a local Unreal Editor
dedicated server, not a packaged Linux server or production service.

Catalog integration update (2026-09-21): the same 76 snapshots now execute the
production catalog parser and affix resolver. Native tests also reject duplicate
quests/objectives, unknown items/zones, fractional counts, missing/cyclic/cross-realm
prerequisites, malformed optional fields and reversed affix ranges. All 16 native
groups passed in `artifacts/unreal/editor/test-1789977450617-5460/`; 74 tooling tests
and tools typechecking passed. Windows packaging and the real-catalog two-client
quest transaction proof passed in
`artifacts/unreal/network/1789978458889-34160/report.json`. Both realms accept their
first expedition quest, record four trusted kills, receive 150 XP, eight gold and
three healing potions, and reject a repeated completion. The proof preserves the
Riftbound character's three previously crafted healing potions and verifies that
quest state remains private. This still uses scripted trusted commands and an
Editor dedicated server; NPC interaction and real enemy attribution remain open.
