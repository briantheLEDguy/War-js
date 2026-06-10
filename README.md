# War-js

Browser-based MMO/RPG vertical slice built with **Three.js + React + Vite +
TypeScript** and Supabase-ready service interfaces. Local mode works without
backend configuration by using in-memory, localStorage, and IndexedDB services.

The runtime renders with generated or licensed `.glb` files when present and
falls back to procedural Three.js primitives when assets are missing.

## Quick Start

```bash
npm install
npm run dev
```

Dev server: `http://localhost:5173`

Useful checks:

```bash
npm run test
npm run typecheck
npm run world:validate
npm run models:sync-playables
npm run build
npm run models:validate
```

## Controls

| Key/Input | Action |
| --- | --- |
| `W` `A` `S` `D` | Move |
| `Space` | Jump |
| Right mouse drag | Turn camera and character facing |
| Left mouse drag | Orbit camera |
| Left + right mouse | Move forward |
| Mouse wheel | Zoom |
| Left click | Target enemy |
| Right click | Open/close interactive gates and doors; equip gear in inventory |
| `1`-`0` | Class ability hotbar |
| `E` | Interact with quest givers, crafting stations, and harvestable corpses |
| `I` | Toggle inventory |
| `C` | Toggle character sheet |
| `H` | Toggle in-game guide / wiki |
| `Esc` | Toggle settings |
| `Enter` | Focus chat |
| `` ` `` | Toggle debug overlay |
| `/gm build` | Enable GM world-edit mode when `VITE_GM_ENABLED=true` and your email is allowlisted |
| `/gm build off` | Leave GM world-edit mode |

## Architecture

```text
.github/workflows/
  deploy-pages.yml       GitHub Pages build/deploy
public/
  assets/
    maps/                Zone JSON data
    models/              Runtime GLBs, asset-index.json, QC sidecars
    textures/            Runtime textures
    hdri/                Environment maps
scripts/
  blender-character-pipeline/
    data/asset-blueprints/ Manifest-first model blueprints
    data/asset-blueprint.schema.json
    data/style-policy.md
    blender/             Blender generator backends and manifest entrypoint
    tools/               Node list/validate/generate commands
    mcp-server/          Codex MCP wrapper
src/
  config/                Environment flag parsing
  data/                  Class roster, item/crafting catalogs, equipment visuals
  editor/                GM authorization helpers
  services/              Local/Supabase service abstraction
    local/               In-memory services and browser-compatible ID helpers
    supabase/            NotImplemented stubs that preserve the backend contract
  state/                 Zustand game store
  game/                  Three.js runtime, loader, player, combat, input,
                         data-driven ability runtime
  game/abilities/        Class kits, ability schema, activation runtime,
                         projectile/impact VFX
  game/animation/        Shared procedural/GLB animation and VFX helpers
  world/                 Zone loading, terrain, props, NPCs, biome/path kits,
                         GM world-edit validation and runtime editor helpers
  world/editor/          Voxel terrain, prefab, transform, collider, and
                         walkable-surface authoring runtime
  wiki/                  React-agnostic guide/wiki content generation from
                         gameplay catalogs plus roadmap metadata
  ui/                    React screens and HUD overlay
```

## In-Game Wiki Guide

`src/wiki/wikiContent.ts` builds the reusable guide index from the same catalogs
used by gameplay: races/classes, ability kits, crafting professions/recipes,
cultivation seeds, quests, and referenced item names. Hand-authored metadata in
`src/wiki/wikiMetadata.ts` provides section order, overview text, race copy, and
planned roadmap pages.

`src/ui/hud/WikiPanel.tsx` renders that index as an in-game HUD guide with
section tabs, search, page navigation, detail rows, and data tables. The guide
opens from the HUD `Guide` button or `H`; while open, movement, combat,
interaction, and chat shortcuts are blocked, and `Esc` closes the guide before
falling back to settings.

## Character Select Preview

`src/ui/screens/CharacterPreviewStage.tsx` renders the selected character beside
the character-select list with a compact Three.js scene. It creates a preview
`Player` with a zeroed position, so model loading, generated profile resolution,
idle animation playback, and compatible equipment overlays use the same runtime
path as the in-world player without mounting the full game loop.

Saved characters load their full `CharacterState` before previewing. While the
create form is open, the preview uses the unsaved race, class, and body variant
choices. Race-themed preview environments are procedural except for the
Destruction foliage/stone accents, which are manifest-backed static props:
`preview_twisted_tree`, `preview_blight_shrub`, `preview_jagged_stone`, and
`preview_dreary_reeds`.

## Gathering And Crafting

Gathering and crafting are data-driven from `src/data/crafting.ts` and persisted
through `services.crafting`, with localStorage active by default and Supabase
stubs ready for Phase 2 backend wiring.

Supported v1 professions:

- **Scavenging**: humanoid enemy corpses can be harvested once before respawn.
- **Butchering**: beast enemy corpses use the same one-time corpse flow.
- **Salvaging**: armor and weapons can be broken into crafting materials.
- **Cultivation**: seeds grow in timed local plots and can use soil additives.
- **Apothecary**: reagents brew health, mana, and hybrid draughts.
- **Talisman Making**: fragments bind into equipable neck-slot talismans with
  rolled Strength bonuses.

Altdorf contains the first crafting hub in `public/assets/maps/altdorf.json` via
`craftingStations`. Stations are interaction points, so real models can replace
their primitive/vendor-stall props later without TypeScript changes.

## Ability System

The combat hotbar is data-driven by `src/game/abilities/abilityData.ts`.
Every playable class has a ten-ability kit keyed to slots `1` through `0`.
Player-facing class names follow the renamed roster in `ability-system.md`,
with legacy WAR career names normalized as compatibility aliases for older
localStorage saves.

Ability definitions include:

- class family and class resource, such as Heat, Verdicts, Zeal, Rage,
  Grudge, Plan, Bloodlust, Hatred, Essence, and similar class-specific meters.
- mana cost, class-resource build/spend rules, cooldown, GCD intent, tags, and
  cancel-rule metadata.
- targeting shape: melee, projectile, beam, cone, area, self, dash, deployable,
  or pet.
- effect payloads for damage, healing, and tracked combat statuses.
- animation metadata with release/active notify windows and generic action ids.
- visual profile metadata for class/race palettes, thematic hotbar icons,
  class-family flair, cast windups, projectile silhouettes, trails, motion
  style, and target-contact impact effects.
- VFX socket intent for future authored assets.

`src/game/abilities/AbilityRuntime.ts` validates range and resources, starts
the matching player animation, spends/builds resources, schedules delayed
impact resolution from animation release windows and projectile travel time,
and hands off damage/healing/status application to `src/game/Combat.ts` so XP,
loot, respawn, enemy hit reactions, and quest kill credit stay on the existing
combat path.

`tests/abilityCatalog.test.ts` and `tests/abilityRuntime.test.ts` run under
Vitest and guard the ability catalog, legacy class aliases, resource rules,
targeting metadata, visual profiles, activation gating, resource spending,
cooldowns, animation calls, and VFX handoff.

`src/ui/hud/AbilityIcon.tsx` renders generated SVG icons from each ability's
visual profile, replacing text-glyph hotbar placeholders with class- and
school-themed frames, symbols, accents, and a shared palette used by the
hotbar and runtime VFX.

`src/game/abilities/AbilityVfx.ts` provides runtime visuals for cast windups,
class-family flourishes, projectiles, beams, melee arcs, ground pulses, impact
bursts, and self auras. Projectile abilities now carry a shaped projectile,
trail, arcing/swaying travel motion, and delayed target-contact burst that
lines up with the scheduled impact window. Class families add their own
race-appropriate palettes, glyphs, orbit behavior, beam pulse rings, area
spokes, and impact fragments so careers share the same runtime system without
all looking like the same recolored spell.
Current generated character GLBs can keep exposing `attack_melee`,
`attack_ranged`, and `cast`; `src/game/Player.ts` maps the richer ability
action ids (`light_attack_a`, `heavy_attack`, `shoot_standing`, `cast_short`,
`cast_long`, `cast_heal`, `ultimate_cast`) onto those clips until more specific
combat animations are authored.

## Runtime Assets

`src/game/AssetLoader.ts` resolves model assets in this order:

1. `public/assets/models/asset-index.json` for manifest-backed characters,
   equipment, body overrides, and indexed props.
2. Direct `model` fields from zone JSON for legacy terrain/building/prop assets.
3. Procedural fallback primitives if a file is missing or invalid.

Indexed equipment can be present on disk but blocked from runtime with
`runtimeReady: false` and a `reviewStatus`. This is used for modules that have
valid manifest output but are not yet skinned/socketed well enough to mount in
gameplay.

Playable character models are resolved from `race`, player-facing `className`,
and `bodyVariant` (`m` or `f`). The generated playable roster currently expands
the 6 races and 24 classes into 48 neutral character profiles. Each profile has
starter armor for `head`, `shoulders`, `chest`, `hands`, `waist`, `legs`,
`feet`, `back`, and `tabard`, for 432 generated modular armor item definitions.
`neck`, `mainHand`, and `offHand` remain separate equipment pipelines.

Runtime-ready armor modules must declare matching `bodyFamily`, `skeletonId`,
`skinned: true`, and `coveredRegions` in `asset-index.json`. The player renderer
loads those modules as skinned overlays, rebinds compatible armor to the loaded
player skeleton, and masks only the body regions covered by the equipped slots.
Incompatible or review-blocked modules are skipped instead of mounted in
bind-pose.

The fallback counter is visible in the debug overlay. Missing assets must never
hard-fail the browser.

## Manifest-First Model Pipeline

The model creation pipeline is driven by manifests under:

```text
scripts/blender-character-pipeline/data/asset-blueprints/
```

The research report in `deep-research-report.md` is the technical source of
truth for the pipeline: manifests own slots, anchors, LOD intent, material
channels, collider policy, QC thresholds, and AI provenance. Generated asset
IDs, filenames, GLTF extras, and manifest metadata use neutral IP-safe names.

Commands:

```bash
npm run models:list
npm run models:sync-playables
npm run models:validate
npm run models:generate -- chr.human.devout_guardian.t1.m
npm run models:all -- smoke
npm run models:all -- playable_smoke
npm run models:all -- playable_characters
npm run models:all -- playable_armor
npm run models:all -- playable_all
npm run models:all -- destruction_preview
npm run models:all -- equipment
npm run models:all -- characters
npm run models:all -- weapons
npm run models:all -- jewels
```

Generated output contract:

- `.asset.json` blueprint in `scripts/blender-character-pipeline/data/asset-blueprints/`
- `.glb` runtime asset in `public/assets/models/`
- `.qc.json` sidecar beside the generated GLB with `qcPassed: true`
- preview/QC artifacts under `artifacts/blender/manifest/` (ignored, safe to
  delete, and regenerated by Blender)
- runtime resolver entry in `public/assets/models/asset-index.json`

`npm run models:validate` checks manifests, neutral generated semantics,
asset-index references, blocked runtime-review statuses, and generated QC
sidecars for existing outputs.

`npm run models:sync-playables` reads
`scripts/blender-character-pipeline/data/playable-character-roster.json` and
deterministically emits the playable `.asset.json` blueprints, asset-index
entries, and `src/data/playableAssets.generated.ts` starter item catalog. Run it
after changing any race/class/body-variant theme data, then validate before
generating GLBs.

Codex MCP tools are exposed by `scripts/blender-character-pipeline/mcp-server/server.mjs`:

| Tool | Purpose |
| --- | --- |
| `list_asset_blueprints` | Show manifests and generated status |
| `generate_asset` | Generate one manifest-backed asset |
| `generate_asset_set` | Generate a manifest set |
| `validate_asset` | Validate manifests and asset-index references |
| `list_generated_assets` | Show GLB and QC sidecar status |

## World Data

Zone JSON in `public/assets/maps/` drives terrain, props, NPCs, enemies,
colliders, walkable surfaces, paths, and biome kits.

Current committed maps are `altdorf`, `reikland`, and the legacy `zone1`
test map. Missing future zone files still load through the built-in fallback
path; the runtime must never hard-fail on absent content.

- `terrainModel` can load a visible GLB terrain and use it for height sampling.
- `props[].colliders` and `props[].walkableSurfaces` make multi-floor props navigable.
- `props[].id` can provide a stable GM-editor id for static-object overrides;
  when omitted, the loader generates one from the expanded prop order.
- `paths` expand into visible, walkable path strips.
- `biomeKits` expand deterministic landscaping while avoiding path corridors.

## GM World Editor

GM build mode is an in-game authoring layer for sculpting and improving Altdorf
and future zones without replacing the static zone JSON pipeline.

Enable it locally with:

```text
VITE_GM_ENABLED=true
VITE_GM_EMAILS=you@example.com
```

Then sign in as that email and submit `/gm build` in chat. The command is
intercepted locally and never sent to zone chat. Unauthorized users receive a
system message and cannot open the tools.

The editor currently focuses on world geometry:

- Voxel terrain sculpting: add, subtract, smooth, flatten, roughen, erase, and
  material paint. Data is stored as sparse voxel chunks, while runtime rendering
  generates a smoothed terrain mesh rather than visible block art. In build
  mode, `Tab` cycles the top-center Add/Subtract/Erase/Scale mode strip, and
  material buttons switch directly into Add with a live translucent brush
  preview for the selected material. Paint can recolor existing voxel terrain
  and can seed a shallow material patch on static terrain.
- Prefab/object authoring: place reusable building, castle, wall, stair,
  bridge, dock, statue, fountain, tree, and rock primitives or matching GLB
  fallbacks. The Brush tool shows a green unplaced preview, places on left
  click, and chains additional pieces end-to-end while dragging without waiting
  for model loading. The preview includes the placement model/fallback plus a
  footprint guide for the chain spacing. Mouse wheel rotates around Y;
  `Shift` + wheel rotates X; `Alt` + wheel rotates Z.
  Selected props can be moved, rotated, scaled, and deleted with Three.js
  `TransformControls`; Select mode exposes a delete button and also accepts
  `Delete`/`Backspace`. Static zone props, including prebuilt castle pieces,
  are selectable too; moving or hiding one writes a draft override for that
  stable static object id rather than editing the source zone JSON directly.
- Static terrain editing: Select mode can target the loaded terrain mesh. Its
  transform is stored as a draft override and the runtime height sampler is
  refreshed when it moves, rotates, scales, or is hidden.
- Collision authoring: add standalone blocking colliders and walkable surfaces,
  plus default collider/walkable metadata for common authored prefabs.
- Persistence: static zone JSON loads first, then the latest published world
  edit overlay. In GM mode, a draft overlay replaces the published overlay,
  autosaves to IndexedDB, and can be published as a named version. Use
  `Reset to Live` in the GM panel to discard the current draft and reload the
  latest published overlay; when no published overlay exists, it resets the
  draft to the static zone JSON baseline. Undo history is seeded from that
  live baseline and is not capped, so a GM editing session can undo from the
  current draft state back to Live.

Local world edits use IndexedDB (`war-js-world-edits`) because voxel chunks can
be too large for localStorage. `services.worldEdits` exposes the shared
local/Supabase-ready interface:

```ts
getPublished(zoneId)
getDraft(zoneId)
saveDraft(zoneId, patch)
publishDraft(zoneId, notes)
listVersions(zoneId)
restoreVersion(zoneId, versionId)
```

Run `npm run world:validate` to check static zone data for editor-compatible
models, colliders, walkable surfaces, paths, and core map shape.

## Supabase Setup

Local mode is default. The Supabase service classes currently preserve the
backend contract as explicit `NotImplementedError` stubs. To route through
Supabase later:

1. Create a Supabase project.
2. Add the browser client dependency and a shared client helper:

   ```bash
   npm install @supabase/supabase-js
   ```

3. Copy `.env.example` to `.env`.
4. Set:

   ```text
   VITE_SUPABASE_URL=https://xxxx.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJ...
   ```

5. Implement the stubs in `src/services/supabase/*`.

Suggested tables:

```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  created_at timestamptz default now()
);

create table characters (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  name text not null,
  class text not null,
  race text not null,
  level int default 1,
  xp int default 0,
  zone_id text not null,
  position jsonb default '{"x":0,"y":0,"z":0}',
  rotation_y real default 0,
  health int default 100,
  max_health int default 100,
  mana int default 100,
  max_mana int default 100,
  strength int default 10,
  gold int default 0,
  equipment jsonb default '{}'::jsonb,
  updated_at timestamptz default now()
);

create table inventory_items (
  id uuid primary key default gen_random_uuid(),
  character_id uuid references characters(id),
  slot int not null,
  item_key text not null,
  item_name text not null,
  qty int not null default 1,
  kind text,
  equip_slot text,
  icon text,
  affix jsonb default '{}'::jsonb,
  unique (character_id, slot)
);

create table chat_messages (
  id uuid primary key default gen_random_uuid(),
  channel text not null,
  user_id uuid,
  from_name text,
  body text not null,
  created_at timestamptz default now()
);

create table zone_players (
  zone_id text not null,
  user_id uuid not null,
  character_id uuid not null,
  name text not null,
  position jsonb not null,
  rotation_y real default 0,
  updated_at timestamptz default now(),
  primary key (zone_id, user_id)
);

create table world_edit_versions (
  version_id text primary key,
  zone_id text not null,
  status text not null check (status in ('draft', 'published')),
  parent_version_id text,
  notes text,
  author_user_id uuid,
  author_email text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  published_at timestamptz
);

create table world_edit_objects (
  version_id text references world_edit_versions(version_id) on delete cascade,
  object_id text not null,
  object jsonb not null,
  primary key (version_id, object_id)
);

create table world_edit_chunks (
  version_id text references world_edit_versions(version_id) on delete cascade,
  chunk_key text not null,
  chunk jsonb not null,
  primary key (version_id, chunk_key)
);

create table gm_user_roles (
  user_id uuid,
  email text,
  role text not null check (role in ('gm', 'admin')),
  created_at timestamptz default now()
);
```

Character creation chooses starting `zone_id` in the service layer: Order races
start in `altdorf`, while Destruction races start in `inevitable_city`.

Enable Row Level Security on all world-edit tables before exposing Supabase to
the browser. Published rows can be readable by players; draft, restore, and
publish writes should be limited to `gm`/`admin` users.

## Deployment

GitHub Pages is built by `.github/workflows/deploy-pages.yml`.

Expected URL:

```text
https://briantheLEDguy.github.io/War-js/
```

The workflow builds with `vite --base=/War-js/`; runtime asset paths must use
`import.meta.env.BASE_URL`.

## Scripts

| Command | What |
| --- | --- |
| `npm run dev` | Vite dev server |
| `npm run build` | TypeScript check plus production bundle |
| `npm run preview` | Preview production bundle |
| `npm run test` | Vitest unit tests for wiki/data consistency plus ability catalog and runtime behavior |
| `npm run test:watch` | Watch mode for the Vitest unit suite |
| `npm run typecheck` | TypeScript check only |
| `npm run world:validate` | Validate zone JSON for world-editor compatibility |
| `npm run models:list` | List model blueprints and generated status |
| `npm run models:sync-playables` | Regenerate the 48-profile playable roster manifests and starter armor catalog |
| `npm run models:validate` | Validate manifests and asset index |
| `npm run models:generate -- <ref>` | Generate one manifest-backed model |
| `npm run models:all -- <set>` | Generate a manifest set |

## License

Source code: MIT when a license file is added.

Only commit assets that are original or licensed for this project.
