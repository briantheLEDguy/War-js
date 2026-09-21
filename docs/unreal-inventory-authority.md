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
equipment visuals, user-facing error feedback, inventory UI, sorting, filtering,
consumables, crafting and deferred-delivery retry remain unfinished.

The opt-in development network proof supplies one synthetic inventory test item
per player (no mesh or visual substitute). Each client submits an invalid slot,
a valid equip, then a stale unequip. Passing requires revision 2, the equipped
item and original affix, and absence of the other player's private inventory.
The server also verifies duplicate reward rejection. This harness is disabled
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
