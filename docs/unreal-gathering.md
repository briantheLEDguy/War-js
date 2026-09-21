# Native resource gathering

The native catalog resolver reads each resource node from its original campaign
map, preserving zone/node/visual-prop identities, profession, loot, quantities,
probabilities, radius, XP and cooldown. It does not manufacture resources from
client parameters. All 284 current definitions have native transaction coverage.

`AWarResourceNode` represents a trusted imported world placement. Its visual must
be an existing visible imported static mesh; there is no generated fallback.
Interaction requires the same world, a matching visual-prop identity and source
range. Height participates for crater-city nodes with explicit source Y, as in
the browser. Character capsule height is removed when comparing feet to node
height. World import must still supply the correct suitable mesh and placement;
the imported-path guard alone is not visual/provenance approval.

`AWarPlayerState::ServerGatherResource` accepts only a node reference and expected
inventory revision. The server checks the living pawn, actor, catalog and range,
then supplies UTC time and randomness. `WarGathering::Gather` commits loot,
profession XP, owner-only per-character cooldown and inventory revision together.
A full bag retains the node's availability and awards no XP or partial/deferred
gathering loot. Previously pending rewards fill only remaining space. When all
loot probability rolls miss, the first loot entry's base quantity is guaranteed,
preserving the browser behavior. Expired cooldowns are pruned; other characters
and identically named nodes in other zones are independent.

`E` selects a nearby available native resource before station interaction.
Client time only helps select an apparently ready node; the server rechecks its
own cooldown. This state is session-only. No native campaign resource placements
are claimed ready: complex model import/bindings, complete world placement,
interaction prompts/maps/onboarding, durable recovery and multiplayer in-world
resource acceptance remain pending. Scavenging/butchering enemy corpses also
remain separate unfinished work.

The native transaction test executes every current resource definition and
checks guaranteed loot, exact cooldown expiry, retry rejection, per-character
and per-zone isolation, full-bag rollback, fallback quantity, invalid probability
and timestamp overflow. This is rules/catalog evidence, not a rendered 284-node
world playtest.

Verification: 14 native foundation groups passed, including all 284 node rule
cases; 72 migration tooling tests and tools TypeScript checking passed. Windows
Development BuildCookRun passed. The existing rendered packaged multiplayer
regression passed at
`artifacts/unreal/network/1789974055801-32060/report.json`; that sequence covers
movement/combat/inventory/crafting/salvage/cultivation, not in-world gathering.
The audit and strict release check still report `readyForRelease: false`.
