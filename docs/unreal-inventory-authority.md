# Native inventory authority increment

PlayerState now owns a replicated inventory snapshot containing bag items,
equipment references, already-rolled deferred rewards and a revision number.
Only its owning connection receives this data. Pawn replacement does not clear
the PlayerState inventory; reconnect and zone handoff persistence are not yet
implemented.

`GrantRewards` is a trusted C++ server API, not a client RPC. It accepts resolved
item metadata from trusted callers and refuses duplicate transaction GUIDs.
Invalid rewards do not consume the receipt. Receipts are session-local and
bounded to 65,536; reaching the limit rejects further grants instead of evicting
old receipts and allowing replay. Durable transactions remain required before
production. This API does not resolve catalog entries or roll affixes itself.

The only client mutation is an equip/unequip selection by bag slot and expected
revision. Server validation rejects nonexistent items, invalid equipment and
stale revisions. Equipment retains its occupied bag slot. Strength aggregation
is validated but is not yet applied to combat attributes. Full affix effects,
equipment visuals and full comparison/filter controls remain unfinished.
Native recipe execution is described in [the crafting increment](unreal-crafting.md).

The native panel opens with `I` and provides catalog names, quantities, strength
affixes, equipped state, deferred reward count, search and name/bag-slot ordering.
Selections show server success/error feedback. Search/order change only the view;
they never renumber authoritative slots. This is an initial panel, not complete
browser inventory/HUD parity. Dragging, complete filters, comparisons and input
remapping remain required. Keyboard/mouse interaction needs broader playtesting.

Consumable use resolves HP/mana effects from the server's staged catalog, consumes
one item, clamps resources to their maxima and rejects stale requests, missing
items, nonconsumables and dead characters. The client cannot supply effect values.
The current replicated resources are HP/mana; other class resources remain pending.

`ExchangeItems` is a trusted server-only boundary for future recipe/salvage callers.
It validates exact slot quantities and equipment protection, then requires every
output to fit before committing consumption. Previously rolled deferred rewards
fill remaining space without rerolls or another XP/gold award. Failed exchanges
leave inventory, revision and receipts unchanged. Recipe execution now uses this
boundary; complete profession/world workflows remain unfinished.

The opt-in development network proof supplies one synthetic inventory test item
per player (no mesh or visual substitute), plus two catalog potions. Each client submits an invalid slot,
a valid equip, then a stale unequip. Passing requires revision 2, the equipped
item and original affix, and absence of the other player's private inventory.
The server also verifies duplicate reward rejection. After observing damage and
mana expenditure, clients use their potions and retry with the stale revision.
Passing requires capped restored resources and one remaining potion each.
This harness is disabled
in Shipping and does not enable production admission.

Verification:

- Nine native foundation groups passed, including browser-derived inventory
  parity and authoritative full-bag/retry/equipment tests.
- Two Editor game clients passed the extended loopback proof:
  `artifacts/unreal/network/1789948652857-17564/report.json`.
- 46 migration tooling tests and the tooling TypeScript check passed.
- Windows Development BuildCookRun succeeded. Two packaged Windows clients
  passed the same loopback proof (NullRHI, 60 FPS):
  `artifacts/unreal/network/1789948788141-12188/report.json`.
- The content audit remains not ready for release; model and full functionality
  parity requirements are unchanged.

To capture the initial native inventory panel alongside the network proof:

```powershell
npm run unreal:network-proof -- --rendered --inventory-ui
```

Rendered proof `artifacts/unreal/network/1789958841570-20704/` passed the
consumable scenarios. The preceding panel render was inspected for readability;
the development map still reports unbuilt lighting. Neither these screenshots
nor the panel's equipment labels constitute equipment mesh or art approval.

The latest interaction increment passed nine native groups and 46 tooling tests.
Windows BuildCookRun succeeded after an automatic retry of a transient Zen
storage connection failure. Packaged clients passed the rendered consumable/UI
proof at `artifacts/unreal/network/1789959169149-30644/`; the panel screenshot
was inspected. The release check still rejects release, as required.
