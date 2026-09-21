# Native recipe execution

All five browser recipes now parse from the staged catalog into native rules:
two minor draughts, rejuvenation, Minor Might Talisman and Soldier's Seal.
Recipe input/output identities, quantities, station kind, minimum rank, XP and
strength-roll ranges remain catalog-owned. Unknown/duplicate definitions and
invalid quantities or ranges fail closed.

PlayerState receives only a recipe ID, expected inventory revision and optional
world-station reference. The server checks character availability, recipe/rank,
ingredients and output capacity. It selects ingredients in inventory order,
rolls affixes on the server, commits through the atomic inventory exchange, then
awards profession XP in the same server operation. Repeated stale requests do
not produce another output or XP award. Profession state replicates only to its
owner alongside inventory. Rank remains `floor(max(0, XP) / 100) + 1`.

The browser's `craftRecipe` permits portable crafting when no station is selected;
a general station accepts all recipes, and a specialist station rejects recipes
for another kind. Native portable recipe buttons preserve that implemented
behavior. A supplied native station must be in the same world, visible, backed
by an imported static mesh and within its configured interaction radius (default
500 cm). This runtime check does not establish commercial provenance or visual
approval. Imported-model validation and release gates remain separate.

The initial inventory panel includes portable recipe buttons with required and
current profession rank/XP. It reports server errors for missing ingredients,
rank, capacity or stale requests. Development proofs grant test ingredients;
this does not implement acquiring those ingredients in the native world.

Evidence so far:

- Ten native foundation groups passed. The crafting group parses all five
  recipes from the staged browser catalog and tests ingredient selection,
  portable/general/specialist eligibility, missing inputs and rank thresholds.
- Rendered two-client proof `artifacts/unreal/network/1789959667463-30440/`
  passed crafting both minor draughts after potion consumption. It checks output
  quantities, 10 XP per client, private profession state, fabricated recipe
  rejection and stale duplicate rejection.
- Atomic exchange tests separately cover full-bag rollback, equipped-item
  protection, duplicate receipts and deferred already-rolled reward delivery.

One packaged attempt failed the existing movement threshold before crafting:
the fixed 0.35-second input window yielded only about 20 cm during startup.
The proof driver now advances toward a measured 100 cm target (with a bounded
timeout); server and observer checks still require more than 50 cm of movement.
This changes test orchestration, not player movement code or acceptance limits.

Windows Development BuildCookRun succeeded after this change. The packaged
rendered proof passed at `artifacts/unreal/network/1789960099880-33424/`; its
inventory/crafting screenshot was inspected. Ten native groups, 46 tooling tests
and tools TypeScript checks passed. The full release gate remains closed.
A second packaged run using NullRHI also passed:
`artifacts/unreal/network/1789960228899-33920/report.json`.

Not yet accepted: in-world station placement/interaction UI across all 76
stations, end-to-end execution of higher-rank recipes/talisman affixes, all six
profession workflows, gathering, cultivation, durable progression,
complete crafting UI/help/onboarding, equipment stat effects and equipment art.
These remain migration work; recipe execution is not full crafting parity.

## Salvaging increment

Native inventory now offers a salvage action with an output preview. Equipped
gear must first be unequipped. The server validates the catalog item, computes
materials from the stored strength affix, and commits destruction/output delivery
through the atomic exchange. If outputs do not fit, the original item remains;
no partial materials, deferred salvage output or XP are awarded. Successful
salvaging awards exactly 8 salvaging XP. Stale requests and non-gear are rejected.
This state remains session-local; durable recovery is still required.

`npm run unreal:salvage-fixtures` captures 25 cases directly from the browser
implementation: weapons, chest/shoulder/leg armor and other armor at strength
0, 1, 2, 3 and 7. Tooling checks the source hash and fixtures; native tests compare
each material identity and quantity. A native regression covers full bags that
can fit only one of three salvage outputs.

The development multiplayer proof uses a catalog Iron Sword with a controlled
strength affix. It rejects salvaging while equipped, unequips it, rejects a
consumable, salvages once and retries the stale request. Acceptance requires
four scrap iron, one fragment, one essence, no sword, no equipped reference,
exactly 8 salvage XP, unchanged potions/apothecary XP and private owner state.
This is inventory metadata; equipment meshes/art are still unfinished.

Salvage verification passed 11 native foundation groups, 72 migration tooling
tests and tools TypeScript checking. Windows Development BuildCookRun succeeded;
two packaged clients passed the rendered sequence at
`artifacts/unreal/network/1789970303565-30772/report.json`. The resulting material
inventory was inspected. The release gate still rejects release. Cultivation is
the next profession dependency: preserve three plots, both seed timers, optional
soil, server-controlled readiness, capacity-safe harvest and duplicate protection.
