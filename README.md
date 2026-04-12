# War-js

Web-based vertical slice inspired by [ProjectWAR](https://github.com/Shmerrick/ProjectWAR) (a Warhammer Online server emulator).

Built with **Three.js + React + Vite + TypeScript**, architected for a **Supabase** backend.

> Note: ProjectWAR is referenced for domain inspiration only. No code, assets, or branding from that repository are vendored here, and this project never writes to it.

## Live URL

Every push to `main` auto-deploys to **GitHub Pages** via `.github/workflows/deploy-pages.yml`.

- Expected public URL: **https://briantheLEDguy.github.io/War-js/**
- One-time setup (required before the first deploy succeeds):
  1. **Settings** → **General** → **Danger Zone** → **Change visibility** → **Public** (GitHub Pages on a free plan requires a public repo)
  2. **Settings** → **Pages** → **Build and deployment** → **Source** → **Deploy from a branch** → Branch: **`gh-pages`** / root
  3. **Actions** tab → **Deploy to GitHub Pages** → **Run workflow** on branch `main`
- Deploy status: see the **Actions** tab.

## Quick start (local)

```bash
npm install
npm run dev         # dev server at http://localhost:5173
# or
npm run build && npm run preview   # prod build at http://localhost:4173
```

1. Any email/password works on the login screen (local mode).
2. Pick one of two prebuilt characters (or create your own).
3. You spawn into a procedural zone with scattered props and a few training dummies.

### Controls

| Key | Action |
| --- | --- |
| `W` `A` `S` `D` | Move |
| `Space` | Jump |
| Right mouse drag | Orbit camera |
| Mouse wheel | Zoom |
| Left click | Target enemy |
| `1` | Autoattack (slot 1) |
| `I` | Toggle inventory |
| `Enter` | Focus chat |
| `` ` `` | Toggle debug overlay |

## Architecture overview

```
src/
  main.tsx              # React entry
  config/env.ts         # reads VITE_SUPABASE_* flags
  services/             # backend abstraction (local | supabase)
    types.ts            # AuthService, CharacterService, ChatService,
                        # InventoryService, WorldService interfaces
    local/              # in-memory + localStorage implementations
    supabase/           # typed stubs; throw NotImplementedError
  state/gameStore.ts    # Zustand store (screen, player, enemies, chat, ...)
  game/                 # Three.js-side runtime
    Game.ts             # renderer + loop + mount/unmount
    AssetLoader.ts      # .glb/.png/.hdr loader with primitive fallbacks
    Player.ts, Enemy.ts, Combat.ts
    Camera.ts, Input.ts
  world/                # Terrain, Skybox, Props, ZoneLoader
  ui/                   # React overlay
    screens/            # LoginScreen, CharacterSelectScreen, GameScreen
    hud/                # PlayerFrame, TargetFrame, Hotbar, ChatPanel,
                        # InventoryPanel, Minimap, DebugOverlay,
                        # NameplateLayer, FloatingDamageLayer
public/
  assets/
    maps/zone1.json     # hand-written zone description
    models/             # .glb (empty until Phase 2)
    textures/           # .png (empty until Phase 2)
    hdri/               # .hdr (empty until Phase 2)
scripts/
  war-asset-pipeline/   # Phase 2 workflow docs
```

### Asset fallbacks

Everything renders today with **zero external asset files**. `AssetLoader` tries the file first, and on failure returns a primitive fallback (capsule humanoid, cylinder dummy, cone trees, etc.). The debug overlay shows a fallback counter so you can see when real assets haven't been dropped in yet.

### Supabase setup (when you're ready)

1. Create a Supabase project.
2. Copy `.env.example` to `.env` and set:

   ```
   VITE_SUPABASE_URL=https://xxxx.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJ...
   ```

3. Create the tables below (SQL editor):

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
     zone_id text default 'zone1',
     position jsonb default '{"x":0,"y":0,"z":0}',
     rotation_y real default 0,
     health int default 100,
     max_health int default 100,
     mana int default 100,
     max_mana int default 100,
     updated_at timestamptz default now()
   );

   create table inventory_items (
     id uuid primary key default gen_random_uuid(),
     character_id uuid references characters(id),
     slot int not null,
     item_key text not null,
     qty int not null default 1,
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
   ```

4. Enable Realtime on `chat_messages` and `zone_players` (or use broadcast channels named `chat:zone`, `zone:<id>`).
5. Implement the stubbed methods in `src/services/supabase/*`. Each file's TODO comment tells you exactly what to call.

When the env vars are set, the app will route through the Supabase services. Until you implement the stubs, the first method call shows a clear `NotImplementedError` pointing at the exact file.

## Phase 2 roadmap

1. **WAR asset pipeline** — see [`scripts/war-asset-pipeline/README.md`](scripts/war-asset-pipeline/README.md).
2. **Supabase activation** — implement the stubs in `src/services/supabase/*`.
3. **Real multiplayer** — Supabase realtime for player transforms; interpolation for remotes.
4. **Abilities system** — data-driven ability table, resource costs, cast bars.
5. **Quests, NPCs, vendors** — dialogue trees, quest log.
6. **Multi-zone world** — zone transitions, loading screens.
7. **PvP / RvR** — realm vs realm zones, objectives, scoring.
8. **Auth hardening** — Supabase Auth + RLS.

## Scripts

| Command | What |
| --- | --- |
| `npm run dev` | Vite dev server |
| `npm run build` | `tsc --noEmit` + production bundle |
| `npm run preview` | Preview the production build |
| `npm run typecheck` | TypeScript check only |

## License

Source code: MIT (see LICENSE if/when added).

Any art assets placed in `public/assets/` must be licensed for your use. This
repository ships with **no third-party assets**; it renders using procedurally
generated Three.js primitives until you drop assets in.
