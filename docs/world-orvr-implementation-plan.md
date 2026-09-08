# Expanded world and shared ORvR implementation plan

## Outcome and current status

The approved outcome is a complete original Aegis Accord versus Riftbound Host campaign across eighteen large outdoor fronts, with high-quality regional environments and populations. Sunmeadow March and Cinderfen Outskirts are the first complete-zone review milestone, followed by the remaining pairing zones, optional lairs, central fronts, fortresses, and the city finale.

The [production board](orvr-production-board.md) tracks the active parallel work and integration dependencies.

The repository now contains expanded outdoor layout sources, explicit art direction for all thirty noncapital zones, generated travel-safe maps, shared terrain controls, and a local authoritative server/client playtest. **A layout is not a completed environment.** Replacement terrain, settlement, vegetation, population, wildlife, and siege assets remain subject to the production and visual-review requirements below. Production multiplayer activation, hosted infrastructure, complete city navigation integration, and measured 18-versus-18 performance are not established by these source changes.

| Milestone | Status and evidence |
|---|---|
| Eighteen 1,200-metre outdoor layouts | Implemented; each has three objective IDs, two opposed keeps, two uncapturable staging camps, six supply routes, and sixteen terrain production chunks |
| Original campaign/optional-boss travel | Implemented and validated; relocated return spawns preserve all original bidirectional connections, with capital content preserved |
| Explicit climate and cultural briefs | Implemented for eighteen outdoor fronts and twelve lairs; planned model/profile selections are not asset approvals |
| Shared terrain evaluation | Implemented; server/client grid-height agreement, route plateaus, and keep/staging grounding have focused tests |
| Shared authoritative campaign playtest | Local server, protocol, simulation, persistence adapters, and client presentation are implemented; use the recorded test results and operational guide to determine which scenarios have actually been verified |
| Sunmeadow/Cinderfen replacement art | Sunmeadow terrain, regional buildings and vegetation are integrated; see the [verification record](orvr-verification.md). Full populations, wildlife, logistics and Cinderfen remain in production |
| Frontier siege collection | Authored deliverables remain staged until binary, material, topology, animation, and visual review are complete; presence in an authoring directory never approves runtime use |
| Production multiplayer | Pending identity/database setup, durable deployment, recovery/load verification, and production activation |
| 1080p/60 FPS, 18 versus 18 | Target only; requires measurement on the stated reference hardware and representative completed assets |

## World scale and authored art

All sixteen battlefield zones and both fortress zones are 1,200 × 1,200 metres. Existing capitals remain city environments and twelve boss lairs remain optional side branches at their existing scale. Ordinary travel stays independent of whether the campaign front is active.

Outdoor keeps are approximately 700 metres apart. Three battlefield objectives form distinct contested locations, each with an explicit route to either keep. Supply roads are twelve metres wide, with reserved clearance for escorted wagons and ambush encounters. Uncapturable realm staging sits behind the keeps and supports fifteen-second respawns. Settlement and wildlife placement separates civilian activity from hostile encounters while maintaining accessible services and gathering nodes.

The road network follows a shared winding objective road and two keep branches.
Caravan itineraries reuse those exact alignments instead of creating six separate
overlapping roads. Measured deliveries range from approximately 364 to 647 metres;
validation allows 350–750 metres for natural alignment. Five-metre keep approaches
fit their passages, seven-to-eight-metre support roads serve camps and villages,
and narrower optional trails provide farm and lair access. Full lane widths,
connected junctions and portal approaches have geometry and collision tests.

Use the current Battle Prelate rebuild as the craftsmanship reference. Every new visible model requires deliberate mesh authorship, convincing thickness and construction, fitted components, readable materials, appropriate topology, UVs, PBR textures, and an editable Blender master. No primitive assemblies, disguised proxy geometry, or automatic approval based on successful export. Detailed source meshes and three inspected runtime LODs must preserve silhouette, materials, and animation character.

Inspect exported GLBs at close range and gameplay distance under neutral and game lighting. Reject stretched textures, conspicuous faceting, floating equipment, bad anatomy, broken deformation, repeated foliage silhouettes, and terrain seams. Assets must be original or have recorded provenance compatible with the project. Weathering should follow material construction and environmental exposure.

The full zone ecosystem includes terrain, roads, rocks, vegetation, architecture, defensive structures, gates, resource-node visuals, service NPCs, civilians, allied and hostile troops, animals, birds, tools, supplies, carts, siege equipment, and necessary animation. An attractive keep does not complete its surrounding zone. A rendered cart does not complete an animated animal-drawn caravan.

The climate progression is explicit:

- Aegis west: warm farmland → temperate floodplain → cool old-growth woodland.
- Aegis east: freshwater fen → clear river valley → alpine foothills and snowfields.
- Riftbound west: geothermal marsh → drowned forest → wet moorland.
- Riftbound east: semiarid steppe → cold conifer pass → volcanic badlands.
- Central campaign: fortified uplands and transitional battlefields, becoming volcanic toward Riftspire.

Use fixed regional seasons initially. Dynamic weather, annual seasons, civilian daily schedules, and an ecology simulation are outside this iteration. Climate transitions require believable elevation, drainage, soil, vegetation, and distant landforms. Local clothing, architecture, work, faction composition, and fauna must reflect those conditions. The full thirty-zone roster is in `docs/orvr-zone-art-briefs.md` and the executable catalog `scripts/campaign/orvr-art-direction.mjs`.

## Campaign rules

### Objectives, supplies, and keep development

Three battlefield objectives begin neutral. Defeat hostile guards and maintain thirty seconds of uncontested living allied presence to capture one. An opposing living player resets capture progress and pauses production.

An owned, uncontested objective produces a 100-supply shipment every three minutes, with at most one ready shipment and one active caravan. A player dispatches the caravan through its supply officer. The wagon follows its authored route at 3.5 metres/second while a connected living ally remains within 25 metres. It stops without an escort and is lost after four minutes unattended. Enemies destroy the wagon through combat; enemy proximity alone does not stop it. Destroyed cargo is not recoverable and awards attackers no supplies or logistics influence.

Delivery grants the receiving keep 100 cumulative upgrade progress and 100 spendable supplies, and grants its realm 100 influence within that zone. Keep stock caps at 1,000; overflow is discarded while the full delivery still contributes progress and influence. Objective ownership changes clear ready cargo and production progress; caravans already dispatched retain their original realm and destination. Battlefield captures and repeatable defense activities no longer manufacture logistics influence, while their existing XP rules may remain.

| Keep level | Delivered supplies in current activation | Unlocks |
|---|---:|---|
| 1 | 0 | Basic garrison and oil installation slot |
| 2 | 300 | Ram deployment |
| 3 | 600 | Defensive catapults |

Spending supplies does not reduce level. A ram costs 100 supplies, with one active per realm per zone. Oil costs 50, with one active installation per keep. Catapults cost 150, with two per keep. Repair costs 25 supplies for ten percent gate health through a ten-second interaction, unavailable while that gate has taken damage within the previous thirty seconds.

Allied players purchase equipment from the keep quartermaster at authored positions. One player can drive a ram, but two seated operators are required to strike a gate. Rams physically travel and can be destroyed; ordinary player attacks cannot substitute for a ram against a keep gate. Destroyed or abandoned rams release their slot and begin a three-minute replacement cooldown without refund. Oil and catapults are player-operated defenses.

Keep conquest requires outer gate breach, inner gate breach, commander defeat, and thirty seconds of uncontested objective occupation. Ownership of all three battlefield objectives is not required. Losing an objective does not erase equipment, cancel a siege, or restore gates.

### Front movement and city finale

The west pairing runs Ironwood ↔ Greybrook ↔ Sunmeadow ↔ Cinderfen ↔ Bleakroot ↔ Vilemere. The east pairing runs Highvale ↔ Glassriver ↔ Brightfen ↔ Ashen Steppe ↔ Gorepine ↔ Obsidian Scar. Aegis victories move toward the Riftbound end; Riftbound victories move toward the Aegis end. The initial fronts are Sunmeadow in the west and Ashen Steppe in the east.

The first authoritative result establishing both keeps under one realm wins the zone. Close its campaign interactions and open the adjacent front toward the losing realm after three minutes of staging. Defender victories counterpush. Secured zones remain travel-accessible. Reopening restores neutral battlefield objectives, one level-one keep per realm, repaired structures, and zero current-activation stock/progress. Historical contributions and territorial victories remain recorded; every activation has a fresh identifier that rejects stale commands and rewards.

Winning an enemy-end T3 zone in either pairing triggers one coordinator-controlled breakthrough, freezes both side pairings, and opens the shared central front. Aegis enters Shatterline; Riftbound enters Dawnline. The full central chain is Bastion of Aegis ← Starfall Gate ← Aegis Crownworks ← Dawnline ↔ Shatterline → Rift Crownworks → Voidgate Fortress → Riftspire Citadel. Counterpushes follow the same both-keeps rule. City access requires the enemy T4 front, inner T4 zone, and fortress.

Each shared front permits eighteen players per realm; overflow stays in safe staging with a realm-specific queue. A fortress victory creates three minutes of city preparation, followed by thirty minutes of siege combat. The Aegis sequence is Crownwatch Courtyard → Crownwatch Vault → Crownwatch Throne Room. The Riftspire sequence is Chainwake Bridgehead → Blackvein Vault → Riftspire Throne. Attackers must retain prerequisites when taking the final objective; defenders win at timeout. Both outcomes record results, end the campaign, and create five minutes of recovery before a fresh campaign. Keep characters, earned rewards, and history while resetting territorial state and siege stock. Empty instances pause simulation and production instead of farming unattended shipments or completing an empty siege.

## Authority, presentation, and recovery

Use a long-lived TypeScript game server with a twenty-Hz authoritative simulation and ten-Hz interest-filtered snapshots. Shared rules must remain independent of React, Three.js, browser storage, and Zustand. Clients request movement, abilities, interactions, and equipment operations; they cannot assert damage, ownership, stock, progress, rewards, or campaign victories.

Supabase Auth verifies identity, and Postgres stores durable characters, campaign state, supplies, rewards, and transactions. Exactly one owner simulates each zone, and one campaign coordinator commits breakthroughs and front changes. Deliveries, purchases, rewards, and campaign transitions must commit durably before success is broadcast. Sequence numbers, campaign/activation identifiers, and transactional deduplication reject retries or stale requests after reconnects and front changes.

Shared presentation uses spatial scenery residency, actual GLB LODs where reviewed levels exist, and animation-aware actor distance handling. Releasing a chunk must release its loader-owned GPU resources; removing actors must release clone-specific skeleton state without disposing shared materials. Async loads cannot resurrect despawned actors or old zones. New `frontier_*` models require explicit runtime/review approval plus matching QC/model hashes before display. Missing optional decoration stays absent. Essential missing terrain, traversal, or gameplay visuals need a recoverable state with Retry/Return and a preserved safe position before a zone can be declared complete.

The playtest transport pauses commands during zone handoff until a destination snapshot or a transfer rejection arrives. Reconnecting requires a fresh full snapshot, stale socket callbacks are ignored, and refreshed authentication tokens start a newly authenticated connection. Only obsolete movement rejections are suppressed; purchase and other action failures remain visible. Entry health checks time out with a retry control, and closed sessions return to sign-in. These recovery paths have focused transport tests; hosted Supabase session renewal still needs deployment verification.

Current transitional terrain uses the authored landform controls while detailed terrain/collision GLBs are produced. `src/shared/orvrTerrain.ts` owns pure height evaluation and Float32 grid sampling; `src/world/orvrTypes.ts` defines the layout contract. `scripts/campaign/orvr-zone-layouts.mjs` recomposes outdoor content without changing persistent IDs and relinks return spawns only after all destination layouts are complete.

## Delivery and verification checklist

1. Finish the authoritative foundation and verify opposing clients, identity boundaries, class abilities, contested captures, shipments, repairs, siege operations, queueing, reconnects, and durable recovery.
2. Finish Sunmeadow and Cinderfen completely, including their regional ecosystems and animated logistics. Review one real advance and counterpush using completed playable zones.
3. Complete both pairing routes and each attached boss lair, then central battlefields and fortresses. Integrate the existing capital objective sequences and actual city navigation with shared siege authority.
4. Complete the entire campaign in both directions, including defender counterpushes and both city outcomes. Promote only the assets and zones that have passed their acceptance gates.

Run focused tests plus the full suite, `npm run typecheck`, `npm run build`, `npm run campaign:generate`, `npm run world:validate`, and relevant model validation commands. Verify generated hashes, LOD references, QC/model/source hashes, textures, source provenance, rigging, animation, and absence of new primitive substitutions. Review diffs for unrelated user changes, accidental generated content changes, missing tests, stale documentation, and secrets.

Exercise duplicate deliveries and purchases, caravan destruction versus delivery, simultaneous keep captures, breakthrough races, stale commands across activations, reconnects, server restart, persistence failures, and queue overflow. Walk every route, ram approach, gate, service, gathering node, crossing, and bidirectional portal; inspect camera clearance, collision, grounding, actor/vegetation separation, and chunk seams.

Benchmark native 1080p on Ryzen 5 5600, RTX 3060, and 16 GB RAM. Measure representative hamlet, woodland, combat, travel, and full eighteen-versus-eighteen keep encounters, plus two pairing instances before convergence. The target is sixty FPS with 95th-percentile frame time at or below 16.7 milliseconds after loading. Publish measured hardware, population, asset readiness, frame-time distribution, server tick timing, memory, transfer times, and known limitations. Do not infer final performance from empty maps or draft assets.

Work on dedicated `codex/` branches, preserve ongoing capital work, and maintain README/changelog operational guidance. Hosted production deployment remains a separate operational action; its absence must not be described as a successful launch.
