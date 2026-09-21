# FinalAppearance capital population

The official capital loads `/Game/Capitals/crownward/Population/AegisCapital_Population`
as an Always Loaded sublevel. It contains 17 new native `WarCityNpc` actors and
eight purchased-kit furnishings. Existing quest NPC Mara Vell remains in the
persistent city, for 18 people total. The population attachment was saved only
after the owner closed the editor; 8,754 persistent actor states were compared
before/after and preserved. Lighting, materials, architecture and terrain were
not edited by this increment.

## District and model assignments

`scripts/unreal/capital_population.py` is the identity/placement ledger. Each row
has a stable NPC ID, district, role, profile and facing. The generated private
`artifacts/unreal/population/population-build.json` records exact imported mesh,
idle animation and grounded transform for every added person.

| District | People | Imported appearances |
| --- | --- | --- |
| Gateward Market | Mara, Elira, Tovin, two shoppers | Existing Mara; herbalist Elira; field officer Tovin; farmer/herbalist shoppers |
| Cinderbank | Serra, smith assistant, two workers | Herbalist Serra/courier; farmer assistant/worker |
| Lantern Quays | Neris Reed, two dockworkers | Herbalist Neris; farmer dockworkers |
| Bellfound Court | Alden, Mira, civic scribe | Farmer Alden/scribe; herbalist Mira |
| Crownwatch | Corren, two guards | Existing imported field-officer profile |

The field-officer import reuses an existing herbalist-derived appearance. This
pass adds no new clothing or character sources, and does not certify final
wardrobe, equipment, LOD, production identity or complete model coverage.
NPC meshes have no blocking collision; furnishings use their imported collision.
Stable IDs and managed-layer hash checks prevent silent duplicate additions or
overwriting owner edits when regeneration is requested.

## Interaction and services

Approach a named service NPC and press **E**. The nearest eligible quest/service
NPC wins; Mara retains her quest dialogue. Merchant panels buy/sell one item per
click and show gold and rejection feedback. **E**, the Close button or Escape
closes the panel. Movement/look input is restored on closing or leaving range.

| Merchant | Goods | Purchase price | Buyback |
| --- | --- | --- | --- |
| Elira Dawnmarch | Bread; health potion; mana potion | 2; 10; 10 gold | 1; 5; 5 gold |
| Neris Reed | Scrap iron; torn cloth; clear water | 4; 4; 2 gold | 2; 2; 1 gold |

Only these listed goods can be sold. `WarCityServices` performs candidate-snapshot
trades; `WarCityTrading` validates server authority, identity, proximity, life/load
state, transaction ID, revision, quantity, gold and capacity before committing.
The existing reward receipt set rejects repeated transactions within a session.
This does **not** establish durable online economy acceptance or reconnect-safe
trade receipts.

Alden reads class resources and ability unlock levels from the exported catalog.
Serra reads professions, recipes, ranks and station requirements from it. These
are guidance panels, without paid unlocks or progression changes. Mira explicitly
reports that banking is unavailable. Guards and residents have no service actions.

## Editor follow-along and repeatable checks

Open the main `unreal/AegisWar/AegisWar.uproject` project and FinalAppearance.
In the Levels panel, select the Population sublevel to edit these actors. Actor
folders are `Population/<district>`, with readable labels. Reload only that
sublevel after background population changes; loaded assets do not hot-refresh.

`scripts/unreal/attach-capital-population.py` can be run once through Tools >
Execute Python Script when a current unsaved editor world does not yet have the
layer. It checks for an existing attachment and neither reloads nor saves the city.
The separate background save helper must only be used with the editor closed.

Checks:

- `python tests/unrealCapitalPopulation.test.py`
- `npm run unreal:test-native` includes `AegisWar.Foundation.CityServices`.
- `npm run unreal:population-proof -- --rendered` checks live identities, idle
  playback, materials, grounding, authoritative trade rejections and catalog
  guidance, then captures the merchant panel.
- `scripts/unreal/verify-capital-population.py` checks feet and standing clearance
  in the saved world through Unreal Python.
- `npm run unreal:crownward-proof` reruns walking, quest/station/gathering and GM
  draft/reload checks in separate game processes.

District inspection images use a temporary unsaved fill light, declared in
`artifacts/unreal/population/render.json`. They review placement and models, not
the saved city lighting. The game proof screenshot uses the saved lighting.
The population map and purchased content remain private local assets, outside
the public repository. Full migration release admission stays closed.

## Verification evidence (2026-09-21)

- First rendered service proof: `artifacts/unreal/population/proof-1790018617927`.
- Refined merchant panel and advancing-animation proof:
  `artifacts/unreal/population/proof-1790019118142`. All 17 new actors had
  assigned materials, a changing idle playback time and ground support; Mara
  appeared exactly once. Six purchase/sale pairs and duplicate, stale revision,
  distant, hidden and unknown-goods requests passed. Teacher text was checked
  against class/profession catalog entries.
- Native foundation suite: 24 passing groups in the shared checkout, including
  CityServices (insufficient gold, full bags, invalid quantities/slots and
  equipped-item rejection): `artifacts/unreal/editor/test-1790019032400-43188`.
- 87 tooling tests, tooling TypeScript check, two population-manifest tests and
  Python syntax checks passed. Migration audit still reports four blocker
  categories; release checking intentionally fails.
- Windows Editor and Game Development targets compiled successfully. Saved-world
  standing-clearance probes passed for all 17 new NPCs with zero measured foot
  height error. Five district inspection views were rendered and reviewed.
- Capital integration and fresh-process GM draft reload passed:
  `artifacts/unreal/capital-proof/crownward-1790019351991`. This includes the
  grounded uphill ascent, Mara/station interaction and all six current gathering
  nodes. This run does not repeat the separate castle-interior route proof.

The rendered proof is a Windows editor-game session with server authority. It
is not a packaged-platform, real network trade round-trip, persistence, or full
capital population acceptance result.
