# In-game scenario queues

This development increment moves Scenario into the possessed character's game menu.
It uses a shared Node coordinator and separately allocated Unreal dedicated servers.
Production Steam authentication, deployment and cross-platform acceptance remain gated.

## Running locally

Start `npm run scenario:host`, then launch the main Unreal game normally and enter a
character. Open the game menu, choose **Scenario**, mark yourself ready and queue for
**Breach the Lower City**. A 30-second gathering window fills unused 6v6 seats with
bots. Accept the match within 30 seconds. Members of a same-realm party (maximum six)
ready individually; the leader queues everyone together.

Keep the host process running while playing. Opening Scenario connects automatically;
the panel shows connection progress and any failure. If the host is missing or stopped,
start `npm run scenario:host` in the project folder and select **Connect / retry**.
A failed connection keeps the campaign character in place. Repeated clicks during
registration are coalesced, and reopening a connected panel preserves its session.

The coordinator defaults to loopback port 8788. Its private keys and recovery journal
live under ignored `unreal/AegisWar/Saved/ScenarioHost/`. `--allow-lan`, `--bind` and
`--advertise` are explicit development host settings; they do not grant collaborator
access or production authentication approval. Instance admission always requires a
character-bound ticket. A fresh source checkout also needs reviewed private Content.

For an explicitly approved private LAN test, the host operator starts
`npm run scenario:host -- --allow-lan --bind 0.0.0.0 --advertise <host-ip>`.
Provision each development character separately with
`npm run scenario:host -- --provision-peer <character-id> --realm aegis --url http://<host-ip>:8788`
(or `--realm riftbound`). Give that tester only their generated private peer config,
then launch their game with `-WarScenarioHostConfig=<absolute-config-path>`.
Use an existing character of the bound realm. The identity authenticates that local
development campaign authority and cannot restore another character. Never share
the host control key or journal. This opt-in transport does not open firewall rules,
configure remote access, approve private asset distribution or bypass the guest VM
collaboration gates. Production clients cannot submit campaign snapshots.

## Systems and state

`shared/scenarios/` holds the scenario catalog and transport-neutral types.
`server/scenarios/` owns parties, queue offers, instance allocation, admission leases
and atomic recovery journals. `UWarScenarioSession` is the native queue client;
`UWarScenarioInstance` consumes tickets and manages the instance roster. Trusted
campaign hosts capture the character again at departure, so time spent playing while
queued does not roll back inventory or progression. Clients cannot register snapshots
using their player credentials.
Departure briefly locks campaign movement, combat and inventory mutations while the
authoritative snapshot is saved. Instance admission remains closed until the trusted
campaign host confirms that it has destroyed the old pawn.

The first scenario uses the player's existing realm, appearance, equipment and class.
Combat is normalized to level 40 while the character retains earned ability unlocks.
Campaign rewards and persistent item consumption are disabled in the match. Leaving
restores the campaign snapshot. Disconnects reserve a seat for 120 seconds; missing
humans are temporarily replaced with bots. Coordinator restart cancels queue offers and
makes transferred campaign snapshots recoverable. Health, mana, class resource,
remaining cooldowns and reward/quest receipts are retained with the inventory.
Return storage is acknowledged only after a campaign pawn exists. The previous
scenario must release possession before restoration; orphaned instances stop after
15 seconds without the coordinator, and restart recovery waits 20 seconds.
Windows sharing violations retry atomic journal replacement; persistent storage
failure temporarily refuses requests while retaining the previous durable file.
Failed writes also roll back in-memory ticket and command changes, so a failed
admission request remains retryable. Earlier development journals retain recovery.
Only one coordinator may own a recovery directory.

Follow, Attack, Hold and the optional-objective target appear in the siege HUD. Each
human commands their assigned bots. Orders resume after nearby combat or hazard
avoidance. Engineers belong to the convoy and do not respond to squad orders.

## Private city scenery

`refresh-siege-capital.py` copies the capital's current authored, generated and
population layers, removes copied campaign gameplay actors and retains furnishings.
It backs up the siege overlay, leaves source packages untouched, and records their
hashes in `artifacts/unreal/scenario-queues/capital-scenery.json`. The navigation tool
must retain these private scenery layers. Source hashes, actual navigation and native
visual review are checked before instance allocation; copying assets alone is not
acceptance. Regeneration preserves older private revision packages for recovery.

The ram and catapult are prepared in separate staging positions before participants
spawn. Supplies unlock convoy movement. Full hull placement, movement and rotational
clearance protect participants; unexpected overlaps stop the engine and trigger
server-side recovery. Physical character capsules use a matching 42 cm radius / 192 cm
height pedestrian agent; convoy navigation remains 280 cm / 330 cm.
If every validated recovery position is temporarily occupied, the affected capsule
can move out through that engine while it remains stopped. Normal engine collision
resumes immediately after the capsule clears. World collision remains active.

## Verification

Focused Node tests cover queue timing, parties, acceptance/decline, capacity, duplicate
requests, authenticated transport, ticket replay, reconnect and journal recovery.
`unreal:test-native` includes occupied-hull and rotational-sweep collision tests.
`unreal:scenario-menu-proof` exercises normal character entry, the in-game queue,
instance admission, convoy visibility before supplies capture, squad movement and
return-state preservation for both realms. `unreal:siege-equipment-network-proof`
remains supporting route and rendering evidence, rather than a substitute for the
player flow.

The rendered `--party` mode verifies invitations, readiness and two current characters
entering one instance. `--instances` verifies two simultaneously occupied dedicated
instances across both realms. `--recovery` restarts the coordinator and removes its
match server while the player is connected, then verifies automatic campaign return.
`--reconnect --realm riftbound` exercises an actual network disconnect and reserved-seat
re-entry. These are local development tests; they do not approve Steam or remote access.

On 2026-09-28 the two-realm simultaneous-instance run passed in
`artifacts/unreal/scenario-menu/2977dd03-74ce-46ec-85cb-32e67cb42ab1`, and coordinator
restart recovery passed in `artifacts/unreal/scenario-menu/562d2cb7-154f-42df-a32a-5938478c39c4`.
The refreshed private capital contains 9,277 scenery actors and eight retained
furnishings; pedestrian and convoy navigation validated all 17 authored route anchors.
The rendered convoy run passed in
`artifacts/unreal/siege/equipment/network/1790611668014-18564`: ram travel 339.5 m,
catapult travel 336.2 m, all three route checkpoints, escort/crew stops, ram strike,
four replicated engineers and four claimed-objective standards. A forced participant
overlap inside the ram recovered without damage. Start, checkpoint, ramp and gate
captures were visually reviewed against the refreshed city.
The final native build and all 69 native tests passed, including occupied staging,
swept turns, capsule escape, campaign vitals/cooldowns and departure locking.
Repository verification passed 701 tests, 136 Unreal-tool tests, all three typechecks,
33 world maps, 906 model records and migration invariants. Release readiness remains
false with four existing platform/content/gameplay gates.
Reserved-seat reconnection passed in
`artifacts/unreal/scenario-menu/ec9ed1e7-0896-467c-9191-b831ed2f7908`, including
the server-observed 1 human / 5 bots → 0 humans / 6 bots → 1 human / 5 bots
transition, optional-objective HUD orders and restored campaign inventory/position.
The final Aegis party run passed in
`artifacts/unreal/scenario-menu/046cbe50-c33f-46a6-a138-0f3bb6314f69`, with the
member holding position while the leader independently commanded Attack and Optional.
Restart recovery passed again with the release-confirmation protocol in
`artifacts/unreal/scenario-menu/b3326a8b-d0bd-4c83-b654-fed442a9369f`.
The final build and 69-test native run are recorded in
`artifacts/unreal/scenario-queues/build-queue-native-17.log` and `native-final-4.log`.
The final Aegis flow passed in
`artifacts/unreal/scenario-menu/8b56f2cb-8356-4745-aac5-eb1a5a6b3cf8`, including
visually checked earned-level action-bar labels and campaign return.

Separate-machine LAN, production accounts, Steam and three-platform release acceptance
remain unverified. The rendered runs use multiple real Unreal processes on one Windows
host. They cover the main queue/travel/orders/return flows and the full convoy route;
they do not constitute exhaustive combat, interruption or long-session soak coverage.

### Connection feedback regression

`npm run unreal:scenario-menu-proof -- --connection-retry` opens Scenario with a
missing configuration, retries against a stopped host, then starts the host and
retries successfully. It checks visible error text, immediate progress, the restored
Ready/queue controls, and unchanged campaign inventory, with rendered captures.

Verified 2026-09-28 with the final rebuilt module: `artifacts/unreal/scenario-queues/connection-retry-proof-final.log`
and `Saved/ScenarioMenuProof/F68462E5D1AB4BB3AF970C640C53FE0F/` (private native
captures and report). The missing-host, unavailable-host and connected panels were
visually reviewed. The build is recorded in `build-connect-feedback-3.log`; repository
tests in `tests-connect.log` passed all 701 tests.
The native foundation suite passed all 69 tests (`native-connect-final.log`).
