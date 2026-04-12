# WAR Asset Pipeline (Phase 2)

This directory is a placeholder for the local-only asset conversion pipeline
that turns a WAR client installation into web-friendly `.glb` / `.png` / `.hdr`
files under `public/assets/`.

**This pipeline is NOT implemented yet.** The runtime works without it via
primitive fallbacks. When you're ready, scripts live here and you run them
locally; **nothing about the pipeline uploads your client files anywhere**.

## Prerequisites

You must supply these yourself:

- A legitimate WAR client install on your machine. Set `WAR_CLIENT_DIR` in `.env`.
- A `.myp` archive extractor (for example, the community "MythicPackage" tool).
- A `.nif -> .gltf` converter. Common paths:
  - Blender 3.x + the Niftools add-on, driven headless (`blender --background --python convert.py`).
  - A CLI converter such as `nifskope` or community-maintained nif-to-gltf tools.
- `.dds` -> `.png` conversion: `magick` (ImageMagick) or `texconv` works well.
- Node.js 20+.

## Intended commands

Add to `package.json` once implemented:

```jsonc
{
  "scripts": {
    "assets:extract":   "node scripts/war-asset-pipeline/extract-myp.mjs",
    "assets:convert":   "node scripts/war-asset-pipeline/convert-meshes.mjs",
    "assets:textures":  "node scripts/war-asset-pipeline/convert-textures.mjs",
    "assets:map-zones": "node scripts/war-asset-pipeline/map-zones.mjs",
    "assets:all":       "npm run assets:extract && npm run assets:convert && npm run assets:textures && npm run assets:map-zones"
  }
}
```

## Intended flow

1. `assets:extract` walks `WAR_CLIENT_DIR`, unpacks `.myp` archives into
   `tmp/war-raw/` (gitignored).
2. `assets:convert` batch-converts `.nif` meshes to `.glb`, writes into
   `public/assets/models/` using a stable naming scheme:
   - `character_<race>.glb`
   - `dummy.glb`
   - `tree_<N>.glb`, `rock_<N>.glb`, `building_<N>.glb`, ...
3. `assets:textures` converts `.dds` -> `.png` into `public/assets/textures/`.
   Terrain diffuse should be named `grass.png` (referenced by zone1).
4. `assets:map-zones` parses WAR terrain/prop placement data and emits
   `public/assets/maps/zoneN.json` compatible with `src/world/ZoneLoader.ts`.

Because the zone JSON format is already the game's source of truth, real
zones drop in without game-code changes.

## Legal / repo hygiene

- `tmp/` is in `.gitignore`. Keep raw extracted client data there; do not
  commit it.
- Only commit `public/assets/` output that you are authorized to distribute.
- This repository ships with **no** third-party game assets.
