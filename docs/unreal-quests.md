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
Authenticated callers must still validate NPC identity/range, current zone and
kill ownership; the actual world/NPC/enemy integration is not yet implemented. These methods are deliberately not exposed to clients or Blueprints.
Native quest NPCs, interactions, quest log/markers/navigation, notifications and
real enemy attribution remain unfinished. Snapshot/receipt state is session-local;
durable reconnect/transfer settlement remains required. This is tested rules and
character-state integration, not a claim of playable quest parity.

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
