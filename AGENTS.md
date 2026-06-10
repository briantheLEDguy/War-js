# War-js — Codex Guide

This file is read by Codex (and similar AI coding assistants) to understand
the project layout, conventions, and commands before doing any work.

## What this project is

A browser-based recreation of **Warhammer Online: Age of Reckoning** (WAR), built
with **Three.js + React + Vite + TypeScript**, architected around local services
now and Supabase-ready service interfaces later.

The goal is a faithful carbon copy of WAR's gameplay, systems, and world running
entirely in the browser. Runtime assets are manifest-generated or direct `.glb`
files when present, with procedural Three.js primitive fallbacks for anything
missing or blocked from runtime review.

> [ProjectWAR](https://github.com/Shmerrick/ProjectWAR) is used as the authoritative
> reference for zone layouts, NPC data, and game mechanics. No code, assets, or
> branding from that project are vendored here.

---

## Reference Fidelity Rules

**These rules override everything else. All code and content must conform to them.**

### Races & Classes
Use the player-facing class names from `ability-system.md`. Legacy WAR career
names may appear only in compatibility aliases, historical changelog entries,
or source-reference notes.

| Realm       | Race       | Classes |
|-------------|------------|---------|
| Order       | Empire     | Ember Arcanist, Hex Inquisitor, Sunfire Templar, Battle Prelate |
| Order       | Dwarf      | Stoneguard, Doomseeker, Glyphbinder, Siegewright |
| Order       | High Elf   | Blade Savant, Pride Warden, Aether Sage, Veil Ranger |
| Destruction | Chaos      | Dreadsworn, Warped Reaver, Void Magister, Ruin Oracle |
| Destruction | Greenskin  | Warbrute, Fang Herder, Bog Hexer, Cleaver |
| Destruction | Dark Elf   | Blood Dancer, Dread Guard, Dusk Weaver, Crimson Acolyte |

### Capital Cities
- **Order capital**: `altdorf` — Altdorf, City of the Empire
- **Destruction capital**: `inevitable_city` — The Inevitable City
- Order characters (empire, dwarf, high_elf) default to `altdorf` on creation
- Destruction characters (chaos, greenskin, dark_elf) default to `inevitable_city`

### Zone Names & IDs
Zone IDs use WAR's naming convention (lowercase, underscored):
`altdorf`, `inevitable_city`, `nordland`, `norsca`, `troll_country`, `high_pass`,
`praag`, `thunder_mountain`, `kadrin_valley`, `mount_gunbad`, `black_crag`, etc.

### District & NPC Names
All district names, NPC names, and titles must match the original WAR game exactly.
Never invent names for content that existed in WAR.
Class trainer titles use the renamed player-facing class roster above.

### Mechanics
- No invented mechanics. Every system must correspond to something in WAR.
- RvR (Realm vs Realm) pairing structure: Nordland/Norsca → Ostland/Troll Country →
  Talabecland/High Pass → Reikland → Altdorf/Inevitable City
- City siege mechanics: cities are attackable when the realm holds all T4 RvR zones
- Scenarios (instanced PvP), Public Quests, and Open RvR zones follow WAR's layout

### Asset Pipeline
Prefer manifest-backed assets under `scripts/blender-character-pipeline/data/asset-blueprints/`
with runtime resolver entries in `public/assets/models/asset-index.json`. Direct
zone `model` filenames remain valid for legacy terrain/building/prop assets.
**Never hard-fail on a missing asset.**

---

## Quick-start commands

```bash
npm install          # install deps
npm run dev          # Vite dev server → http://localhost:5173
npm run build        # TypeScript check + production bundle → dist/
npm run preview      # serve the production bundle locally
npm run typecheck    # TypeScript check only (no emit)
npm run world:validate
npm run models:validate
npm run models:sync-playables
```

---

## Repository layout

```
.github/
  workflows/
    deploy-pages.yml    # builds + deploys to gh-pages branch on push to main
AGENTS.md               # this file
README.md               # human-oriented project overview
index.html              # Vite entry (references /src/main.tsx; Vite rewrites on build)
vite.config.ts          # Vite config — no base set here; pass --base=/War-js/ in CI
tsconfig.json
package.json

public/
  .nojekyll             # disables Jekyll on the gh-pages deployment
  assets/
    README.md           # explains asset layout
    maps/
      zone1.json        # Nordland Outskirts zone definition (legacy test zone)
      altdorf.json      # Altdorf — Order capital city
      reikland.json     # Reikland outdoor test/RvR-adjacent zone
    models/             # generated/direct .glb files, asset-index.json, QC sidecars
    textures/           # runtime terrain/building textures
    hdri/               # optional environment maps

scripts/
  validate-world-edits.mjs
  blender-character-pipeline/
    README.md           # manifest-first Blender model pipeline
    blender/            # Blender generator/exporter backends
    data/               # asset blueprints, schema, roster, style policy
    tools/              # Node list/validate/sync/generate commands
    mcp-server/         # Codex MCP wrapper

src/
  main.tsx              # React app entry point
  vite-env.d.ts         # Vite env type declarations

  data/
    careers.ts          # player-facing race/class roster and legacy aliases
    crafting.ts         # gathering/crafting professions and recipes
    items.ts            # item catalog and equipment metadata
    playableAssets.generated.ts
    quests.ts

  config/
    env.ts              # reads VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY

  services/             # backend abstraction layer
    types.ts            # AuthService, CharacterService, ChatService,
                        #   InventoryService, WorldService interfaces + shared types
    index.ts            # factory: returns local or supabase services based on env
    local/              # in-memory + localStorage implementations (fully working)
      authLocal.ts
      characterLocal.ts
      chatLocal.ts
      craftingLocal.ts
      inventoryLocal.ts
      questLocal.ts
      worldEditLocal.ts
      worldLocal.ts
    supabase/           # typed stubs — each throws NotImplementedError until wired
      authSupabase.ts
      characterSupabase.ts
      chatSupabase.ts
      craftingSupabase.ts
      inventorySupabase.ts
      questSupabase.ts
      worldEditSupabase.ts
      worldSupabase.ts

  state/
    gameStore.ts        # Zustand store: screen, user, character, enemies,
                        #   chat, inventory, HUD state, FPS, debug flag

  game/                 # Three.js runtime (no React inside)
    Game.ts             # WebGLRenderer setup, game loop, mount/unmount
    AssetLoader.ts      # GLTFLoader + TextureLoader + RGBELoader with
                        #   primitive fallbacks; uses import.meta.env.BASE_URL
    Player.ts           # player mesh, movement, jump physics
    Enemy.ts            # enemy mesh, respawn logic
    Combat.ts           # targeting, autoattack, floating damage numbers
    CraftingLogic.ts
    QuestLogic.ts
    Camera.ts           # FollowCamera (orbit + zoom)
    Input.ts            # keyboard + mouse state tracker
    abilities/          # data-driven class kits, runtime, VFX, types
    animation/          # shared procedural/GLB animation helpers

  world/
    ZoneLoader.ts       # fetches assets/maps/<id>.json; built-in default if missing
                        #   ZoneDefinition includes flatTerrain, zoneTriggers, npcs
    BiomeKit.ts
    PathKit.ts
    Terrain.ts          # procedural heightmap terrain mesh; flatTerrain=true for cities
    Skybox.ts           # HDR environment + directional light + ambient
    Props.ts            # spawns props from zone JSON (supports WAR city prop kinds)
    NpcSpawner.ts       # spawns NPC meshes from zone.npcs[]; pushes NpcState to store
    editor/             # GM voxel/prefab/transform/collision authoring runtime

  wiki/
    wikiContent.ts      # guide pages generated from gameplay catalogs
    wikiMetadata.ts     # overview copy, section order, and roadmap metadata

  ui/                   # React overlay (renders on top of the Three.js canvas)
    App.tsx             # root component — routes between login / char-select / world
    styles.css          # all CSS (dark fantasy theme; CSS custom properties)
    screens/
      LoginScreen.tsx
      CharacterSelectScreen.tsx
      CharacterPreviewStage.tsx
      GameScreen.tsx    # mounts Game, shows HUD
    hud/
      Hud.tsx
      PlayerFrame.tsx
      TargetFrame.tsx
      Hotbar.tsx
      AbilityIcon.tsx
      ChatPanel.tsx
      CharacterSheetPanel.tsx
      CraftingPanel.tsx
      InventoryPanel.tsx
      Minimap.tsx
      QuestDialog.tsx
      QuestLogPanel.tsx
      QuestMarkerLayer.tsx
      SettingsPanel.tsx
      TouchControls.tsx
      WikiPanel.tsx
      WorldEditorModeStrip.tsx
      WorldEditorPanel.tsx
      DebugOverlay.tsx
      NameplateLayer.tsx
      FloatingDamageLayer.tsx
```

---

## Key conventions

- **TypeScript everywhere** — no plain `.js` in `src/`. Use strict mode (see
  `tsconfig.json`).
- **Zustand for game state** — all shared state lives in `src/state/gameStore.ts`.
  The Three.js game loop reads it with `useGameStore.getState()` (not hooks).
- **Services are injected at module load** — `src/services/index.ts` creates one
  shared `services` object. Do not import service classes directly elsewhere.
- **Asset paths** — always prefix with `import.meta.env.BASE_URL` so they work
  both in dev (`/`) and in the GitHub Pages deployment (`/War-js/`).
- **Primitive fallbacks** — `AssetLoader` catches file-not-found or invalid-model
  errors and returns a Three.js primitive. A counter in `gameStore` tracks
  fallback count; the debug overlay shows it. **Never hard-fail on a missing asset.**
- **Zone definitions** — all world content (props, enemies, spawn point) lives in
  `public/assets/maps/<zoneId>.json`. The TypeScript code does not need changes
  when adding zones or tweaking layouts.
- **No CSS-in-JS** — all styles are in `src/ui/styles.css` using CSS custom
  properties. Do not add inline styles or CSS modules unless necessary.

---

## GitHub Pages deployment

The live URL is **https://briantheLEDguy.github.io/War-js/**.

### How it works

1. `.github/workflows/deploy-pages.yml` runs on every push to `main`.
2. It builds with `npx vite build --base=/War-js/` so all asset URLs are rooted
   at `/War-js/`.
3. The workflow deploys via **two** strategies so it works regardless of
   the Pages source setting:
   - **Pages API** (`actions/deploy-pages@v4`) — for source = "GitHub Actions".
   - **gh-pages branch push** (`JamesIves/github-pages-deploy-action`) —
     for source = "Deploy from a branch".
4. Either one is sufficient; both run every build.

### One-time setup (repository owner)

If you see a black screen or the deploy workflow fails:

1. **Make the repo public** (required for GitHub Pages on a free plan):
   Settings → General → Danger Zone → Change visibility → Public.
2. **Set Pages source** (pick **one**):
   - **Recommended:** Settings → Pages → Source → **GitHub Actions**.
   - **Alternative:** Settings → Pages → Source → Deploy from a branch →
     Branch: `gh-pages` / root.
3. **Re-run the workflow** (if needed):
   Actions → Deploy to GitHub Pages → Run workflow on `main`.

### Making `main` the default branch

Settings → General → Default branch → change from
`Codex/web-game-conversion-7yzlN` to `main`.

---

## Supabase activation (when ready)

1. Create a Supabase project.
2. Add the browser client dependency when implementing the stubs:
   ```bash
   npm install @supabase/supabase-js
   ```
3. Copy `.env.example` → `.env` and fill in:
   ```
   VITE_SUPABASE_URL=https://xxxx.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJ...
   ```
4. Implement the stubs in `src/services/supabase/*.ts` — each file has a `TODO`
   comment pointing at the exact Supabase call to make.
5. Create the database tables from the SQL in `README.md`.

---

## Phase 2 roadmap

See `README.md` for the full list. Key items:

| Phase | Description |
|-------|-------------|
| 2a | Manifest-first Blender asset pipeline (`scripts/blender-character-pipeline/`) - active |
| 2b | Supabase activation (implement service stubs) |
| 2c | Real multiplayer (Supabase realtime, remote player interpolation) |
| 2d | Abilities system (data-driven, cast bars) - active runtime; cast bars still future |
| 2e | Quests / NPCs / vendors - local vertical slice active |
| 2f | Multi-zone world |
| 2g | PvP / RvR |
| 2h | Auth hardening (Supabase Auth + RLS) |

---

## Common AI coding tasks

### Add a new zone
1. Create `public/assets/maps/<zoneId>.json` following the shape in existing zone files.
2. Use WAR-accurate `id`, `name`, district layout, and NPC placement.
3. Set `"flatTerrain": true` for capital cities and indoor zones.
4. Add `"zoneTriggers"` for exits to adjacent zones.
5. Add `"npcs"` for vendors, trainers, bankers, guards.
6. No TypeScript changes needed — `ZoneLoader` discovers it by `id`.

### Add a new service method
1. Add the signature to the appropriate interface in `src/services/types.ts`.
2. Implement in `src/services/local/<service>Local.ts` (in-memory).
3. Add a `NotImplementedError` stub in `src/services/supabase/<service>Supabase.ts`.

### Add a new HUD element
1. Create a component in `src/ui/hud/`.
2. Add its styles to `src/ui/styles.css`.
3. Mount it inside `src/ui/hud/Hud.tsx`.

### Add a game state field
1. Add to the `GameStore` interface in `src/state/gameStore.ts`.
2. Add the default value and setter in the `create(...)` call below it.
