# Cinderfen architecture handoff

All eight modules are internally accepted and published. The main and corner receipts bind 59 required images, and merged GM metadata exposes all eight approved entries. Global registry and map activation remain with root.

## Frozen exports

| Asset | LOD triangles | LOD0 SHA-256 |
|---|---|---|
| frontier_cinderfen_dwelling | 108924 / 34140 / 11744 | e623c3fd7b6f5388d4cca781957e284a270bd82333c9e69633ac2aedffc4b1fd |
| frontier_cinderfen_workshop | 134704 / 39250 / 12108 | 81067dcb441ce106583c46160649b46646500e473567bda809c47ff994d79ab9 |
| frontier_cinderfen_supply_shelter | 73904 / 22142 / 7424 | 829317741fda3dc33d3df83209165650c399314af5176064c0de685b98639394 |
| frontier_cinderfen_curtain_walk | 30968 / 14784 / 4084 | d1afc68d62c053ee987dabeef8909a0c219d5a299a499e12d8989ca792c56008 |
| frontier_cinderfen_gatehouse | 356272 / 143994 / 44068 | 6404b8c4f42c7cceff961e996b09860be3a140b7dd2d04d71110ef0d957efe90 |
| frontier_cinderfen_gate_leaves | 16840 / 7592 / 1880 | 1bb62c5f20416e1f8903e891d84a30710fbc6b1aa28fbb95e408386383e899b1 |
| frontier_cinderfen_wall_stair | 28708 / 10396 / 3916 | 24b2e1b25941f4c55084c9e1136b45c9f81a605acd6673a16b8ece379338ec65 |
| frontier_cinderfen_corner_access | 59188 / 29762 / 8028 | 5efebeabdc7989da8779db3875bec44e493a7140df9ab944c6762a594573facc |

All filenames are `<asset>_lod0.glb`, `_lod1.glb`, `_lod2.glb`. Main exports live in `runtime/`; the corner exports live in `junction/runtime/`. Each approved publication provides the same filename under `public/assets/models/` with signed QC and shared textures.

## Evidence and integration

- Main `build-report.json`, `validation.json` and `review/review.json`: 21 GLBs, zero errors/warnings, 52 required actual-export images.
- Companion `junction/build-report.json`, `validation.json`, neutral/gameplay sheet and `corner_stair_assembly.png`: three GLBs, zero errors/warnings, seven required images.
- `review/keep-assembly.json`: 65 actual placed modules, continuous outer/inner perimeter and gangways, zero missing support or head-clearance samples.
- `review/placement-navigation.json`: shared runtime/authority movement functions reach all 13 keep targets and all 13 village targets. Model footprint heights match the current landscape v2 grid within 0.000061m.
- `navigation-contract.json` and `junction/navigation-contract.json`: measured Y-up bounds, metre-scale floors, doorways, gate and stair sockets, colliders and supports.
- After companion publication, run `node authoring/blender/cinderfen-architecture/tools/merge_builder_metadata.mjs` so all eight approved entries appear in the scanned package GM metadata.
- Activate from the shared generator with `composeCinderfenEnvironment(zone, { architecture: true })`; keep this frozen composer unchanged so its reviewed placement hash remains valid.
- Root owns realm standards and final landscape/registry activation. No generic architecture fallbacks are introduced by this package.

## Realm cloth attachments

`review/banner-sockets.json` measures the frozen gatehouse facade directly. Model-space attachments: X=-6.7,Y=3.8,Z=6.05716 and X=6.7,Y=3.8,Z=6.04226; outward +Z. Apply keep gatehouse yawPI and centreZ -24/-7.5. These are hanging-cloth attachments, not pole bases. Keep cloth clear of the six-metre central passage.

## Gameplay identities

Commander(keepX,4), delivery(keepX,-78), quartermaster(keepX-13,-60) and both original gate IDs are retained. Owner entrance passage pairs have radius2/span6 and labels Outer gate passage / Inner gate passage. The actual leaves retain local hinge pivots; their closed collider centre is localZ-.3. Root authority now derives the matching transformed collider centre.

## Next bounded package

Cinderfen ecology: original marsh alder, reed clump, sedge/horsetail ground cover and irregular basalt outcrop under `authoring/blender/cinderfen-nature/`. Preserve this frozen architecture.
