# War-js — Claude Code Guide

This file is read by Claude Code (and similar AI coding assistants) to understand
the project layout, conventions, and commands before doing any work.

## What this project is

A browser-based recreation of **Warhammer Online: Age of Reckoning** (WAR), built
with **Three.js + React + Vite + TypeScript**, architected for a **Supabase** backend
(local in-memory fallback works out of the box with zero config).

The goal is a faithful carbon copy of WAR's gameplay, systems, and world — running
entirely in the browser. All geometry is procedural Three.js primitives until real
game assets are available via the Phase 2 asset pipeline.

> [ProjectWAR](https://github.com/Shmerrick/ProjectWAR) is used as the authoritative
> reference for zone layouts, NPC data, and game mechanics. No code, assets, or
> branding from that project are vendored here.

---

## WAR Fidelity Rules

**These rules override everything else. All code and content must conform to them.**

### Races & Careers
Use Warhammer Online's exact race and career names — no substitutions:

| Realm       | Race       | Careers |
|-------------|------------|---------|
| Order       | Empire     | Bright Wizard, Witch Hunter, Knight of the Blazing Sun, Warrior Priest |
| Order       | Dwarf      | Ironbreaker, Slayer, Rune Priest, Engineer |
| Order       | High Elf   | Swordmaster, White Lion, Archmage, Shadow Warrior |
| Destruction | Chaos      | Chosen, Marauder, Magus, Zealot |
| Destruction | Greenskin  | Black Orc, Squig Herder, Shaman, Choppa |
| Destruction | Dark Elf   | Witch Elf, Blackguard, Sorceress, Disciple of Khaine |

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

### Mechanics
- No invented mechanics. Every system must correspond to something in WAR.
- RvR (Realm vs Realm) pairing structure: Nordland/Norsca → Ostland/Troll Country →
  Talabecland/High Pass → Reikland → Altdorf/Inevitable City
- City siege mechanics: cities are attackable when the realm holds all T4 RvR zones
- Scenarios (instanced PvP), Public Quests, and Open RvR zones follow WAR's layout

### Asset Pipeline
When `.glb` model files land in `public/assets/models/`, they use the same filename
the zone JSON references — no code changes required. Until then all geometry uses
Three.js primitive fallbacks. **Never hard-fail on a missing asset.**

---

## Quick-start commands

```bash
npm install          # install deps
npm run dev          # Vite dev server → http://localhost:5173
npm run build        # TypeScript check + production bundle → dist/
npm run preview      # serve the production bundle locally
npm run typecheck    # TypeScript check only (no emit)
```

---

## Repository layout

```
.github/
  workflows/
    deploy-pages.yml    # builds + deploys to gh-pages branch on push to main
CLAUDE.md               # this file
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
    models/             # .glb files (empty — primitive fallbacks used until Phase 2)
    textures/           # .png/.jpg terrain textures (empty until Phase 2)
    hdri/               # .hdr environment maps (empty until Phase 2)

scripts/
  war-asset-pipeline/
    README.md           # Phase 2 local asset-conversion workflow (not implemented yet)

src/
  main.tsx              # React app entry point
  vite-env.d.ts         # Vite env type declarations

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
      inventoryLocal.ts
      worldLocal.ts
    supabase/           # typed stubs — each throws NotImplementedError until wired
      authSupabase.ts
      characterSupabase.ts
      chatSupabase.ts
      inventorySupabase.ts
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
    Camera.ts           # FollowCamera (orbit + zoom)
    Input.ts            # keyboard + mouse state tracker

  world/
    ZoneLoader.ts       # fetches assets/maps/<id>.json; built-in default if missing
                        #   ZoneDefinition includes flatTerrain, zoneTriggers, npcs
    Terrain.ts          # procedural heightmap terrain mesh; flatTerrain=true for cities
    Skybox.ts           # HDR environment + directional light + ambient
    Props.ts            # spawns props from zone JSON (supports WAR city prop kinds)
    NpcSpawner.ts       # spawns NPC meshes from zone.npcs[]; pushes NpcState to store

  ui/                   # React overlay (renders on top of the Three.js canvas)
    App.tsx             # root component — routes between login / char-select / world
    styles.css          # all CSS (dark fantasy theme; CSS custom properties)
    screens/
      LoginScreen.tsx
      CharacterSelectScreen.tsx
      GameScreen.tsx    # mounts Game, shows HUD
    hud/
      Hud.tsx
      PlayerFrame.tsx
      TargetFrame.tsx
      Hotbar.tsx
      ChatPanel.tsx
      InventoryPanel.tsx
      Minimap.tsx
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
- **Primitive fallbacks** — `AssetLoader` catches any file-not-found error and
  returns a Three.js primitive. A counter in `gameStore` tracks fallback count;
  the debug overlay shows it. **Never hard-fail on a missing asset.**
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
3. The `dist/` folder is pushed to the `gh-pages` branch via
   `JamesIves/github-pages-deploy-action`.
4. GitHub Pages serves the `gh-pages` branch.

### One-time setup (repository owner)

If you see a black screen or the deploy workflow fails:

1. **Make the repo public** (required for GitHub Pages on a free plan):
   Settings → General → Danger Zone → Change visibility → Public.
2. **Set Pages source to the `gh-pages` branch**:
   Settings → Pages → Build and deployment → Source → Deploy from a branch →
   Branch: `gh-pages` / root.
3. **Re-run the workflow** (if needed):
   Actions → Deploy to GitHub Pages → Run workflow on `main`.

### Making `main` the default branch

Settings → General → Default branch → change from
`claude/web-game-conversion-7yzlN` to `main`.

---

## Supabase activation (when ready)

1. Create a Supabase project.
2. Copy `.env.example` → `.env` and fill in:
   ```
   VITE_SUPABASE_URL=https://xxxx.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJ...
   ```
3. Implement the stubs in `src/services/supabase/*.ts` — each file has a `TODO`
   comment pointing at the exact Supabase call to make.
4. Create the database tables from the SQL in `README.md`.

---

## Phase 2 roadmap

See `README.md` for the full list. Key items:

| Phase | Description |
|-------|-------------|
| 2a | WAR asset pipeline (`scripts/war-asset-pipeline/`) |
| 2b | Supabase activation (implement service stubs) |
| 2c | Real multiplayer (Supabase realtime, remote player interpolation) |
| 2d | Abilities system (data-driven, cast bars) |
| 2e | Quests / NPCs / vendors |
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
