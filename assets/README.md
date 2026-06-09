# /public/assets

Runtime asset root. The app must render even when model files are missing; all
loaders keep primitive fallbacks in `src/game/AssetLoader.ts`.

## Folders

- `models/` - runtime `.glb` files plus `asset-index.json` and `.qc.json` sidecars.
- `maps/` - zone JSON consumed by `src/world/ZoneLoader.ts`.
- `textures/` - `.png`, `.jpg`, or `.svg` textures referenced by zones or models.
- `hdri/` - `.hdr` environment maps.

## Model Index

`models/asset-index.json` is the runtime resolver for manifest-backed assets.
It maps neutral asset profiles to generated GLBs:

- `characterProfiles` for playable model profiles.
- `equipment` for item-key to armor-module model resolution.
- `baseBodies` for reusable body overrides.
- `staticProps` for indexed props such as the training dummy.

Equipment entries may include `runtimeReady: false` plus `reviewStatus`.
The runtime skips those generated files and keeps primitive fallbacks rather
than mounting unskinned bind-pose modules or unsocketed accessories.

Playable character entries are generated for every race, player-facing class,
and body variant (`m` or `f`). Runtime-ready armor entries include
`bodyFamily`, `skeletonId`, `skinned: true`, and `coveredRegions` so the player
renderer can rebind fitted overlays to the active character skeleton and hide
only the covered body regions.

The runtime still accepts direct zone `model` filenames for terrain, buildings,
doors, guards, and other legacy props. Missing or invalid files fall back to
procedural primitives.

## Manifest-Generated Outputs

Current manifest outputs include:

```text
asset-index.json
chr_<race_family>_<class_key>_t1_<m|f>.glb
arm_<race_family>_<class_key>_<slot>_t1_<m|f>.glb
chr_human_pyromancer_t1_m.glb
chr_human_tracker_t1_m.glb
chr_human_sun_vanguard_t1_m.glb
chr_human_devout_guardian_t1_m.glb
body_human_armor_fit_t1_m.glb
arm_human_chest_blackened_plate_t1_m.glb
arm_human_shoulders_blackened_plate_t1_m.glb
arm_human_hands_blackened_bracers_t1_m.glb
arm_human_waist_blackened_belt_t1_m.glb
arm_human_legs_blackened_plate_t1_m.glb
arm_human_feet_blackened_boots_t1_m.glb
arm_human_tabard_oathcloth_t1_m.glb
arm_human_back_crimson_cape_t1_m.glb
wep_hammer_2h_reliquary_steel_t1.glb
jwl_amulet_bloodglass_t1.glb
prop_training_dummy_t1.glb
```

The playable roster is generated from
`scripts/blender-character-pipeline/data/playable-character-roster.json` with
`npm run models:sync-playables`. A full generated pass covers 48 character GLBs
and 432 starter armor-module GLBs; the compact smoke set is
`npm run models:all -- playable_smoke`.

Each generated GLB should have a matching `.qc.json` sidecar with
`qcPassed: true` before it counts as validated output.

## Legacy Direct Models

Some zone-authored assets are still direct model references and are not yet
manifest-backed:

```text
altdorf_land.glb
altdorf_castle.glb
castle_gate.glb
castle_door.glb
castle_stairs.glb
gate.glb
banner_post.glb
vendor_stall.glb
guard_male.glb
```

These remain valid runtime assets. Future new model work should prefer a
manifest blueprint and an index entry.

## Biome Kits

Zone JSON can include `paths` and `biomeKits` entries. `paths` are expanded by
`src/world/PathKit.ts` into terrain-following path-strip chunks with generated
walkable surfaces. `biomeKits` are expanded by `src/world/BiomeKit.ts` into
deterministic props while avoiding path corridors and declared no-scatter
rectangles.

The current `evergreen_pnw` kit supports Douglas fir, western red cedar,
hemlock, sword fern, grass clumps, wildflowers, low shrubs, mossy boulders,
fallen logs, path-edge stones, dirt path strips, and cobblestone path strips.

## Runtime Rules

- Asset paths must work under both `/` and `/War-js/`; use `import.meta.env.BASE_URL`.
- Model-backed terrain can be declared with `terrainModel`; missing terrain falls back to generated terrain.
- Interactive props can declare `interaction`, `colliders`, and `walkableSurfaces` in zone JSON.
- Character GLBs should expose `idle`, `walk`, `run`, `jump`, `attack_melee`, `attack_ranged`, `cast`, `combat_idle`, and `death` when animated.
- The ability system emits generic action ids such as `light_attack_a`, `heavy_attack`, `shoot_standing`, `cast_short`, `cast_long`, `cast_heal`, and `ultimate_cast`; the runtime currently maps those to `attack_melee`, `attack_ranged`, or `cast` until specific authored clips exist.
- The indexed training dummy should expose `idle` and `hit_react`.
- Only commit assets that are original or licensed for this project.
