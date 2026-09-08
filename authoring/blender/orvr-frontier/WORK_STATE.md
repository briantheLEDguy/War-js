# Frontier siege and logistics handoff

Updated 2026-09-07, 21:55 local. Branch `codex/map-readability`.

The current package is complete for main-task integration review and remains unpublished. All authoring/review Blender processes have finished. Do not resume old session IDs or run the obsolete pre-animation refinement scripts.

Eight original assets have three exported PBR LODs: wagon, ram, oil cauldron, catapult, gate, draft horse/harness, fitted reins/bit, and supply-officer pouch. One animation-only pack adds the fitted seated driver on the existing canonical humanoid. Every source/master and current hash is saved. No runtime, map, global registry or service file was changed by this asset pass.

Authoritative handoff files:
- `source/runtime_contract.json`: exact model basenames/hashes, metre scale, pivots, sockets, gaits, event times, driver offset, palms and belt fit.
- `review/package_validation.json`: all 25 current files, zero glTF errors; six identity-parent skinned-node warnings across the horse LODs.
- `review/final_inventory.json` and `review/final_lod_contact_sheet.png`: all 24 matching model/render hash sets.
- `review/visual_observations.json`: explicit completed construction review and remaining limits; not automatic benchmark approval.
- `review/frontier_caravan_assembly.json`, `frontier_supply_officer_fit.json`, `frontier_draft_horse_details.json`: actual published-body/equipment and anatomy review receipts.
- `README.md`: accurate rebuild order, file responsibilities, clip use and remaining runtime scope.

Focused verification: four test files, eleven tests passed. Actual binary tests cover pivots, clip start, normalized horse skin, stationary roots, canonical rest compatibility, published boot-to-footboard fit, all-LOD shaft/grip alignment and officer belt transforms. Horse key foot drift is below 1 mm; the worst sampled interpolated midpoint is 6.12 mm under the explicit 1 cm contact budget.

Live review pages: `review.html` for individual LODs/materials/clips; `caravan-review.html` for a hash-verified actual equipped assembly with independent animation mixers. Root can inspect in its browser. This child has no available CUA browser session, so Blender clean GLB reimports supplied the visual checks.

Root requested the next bounded task be dwarf limb volume/deformation in frontier-population. Do not edit those files until the root explicitly hands over ownership after this package handoff.
