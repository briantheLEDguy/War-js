# /public/assets

Runtime asset root. The app renders without any files here thanks to
primitive fallbacks in `src/game/AssetLoader.ts`.

Drop converted assets into these folders to light the game up:

- `models/` — `.glb` models referenced in `maps/*.json` and by name in code:
  - `character_empire.glb`, `character_greenskin.glb`, `character_dwarf.glb`, `character_elf.glb`
  - `dummy.glb`
  - Any additional named props referenced by `props[].model` in zone JSON.
- `textures/` — `.png` / `.jpg` textures referenced by zone JSON
  (`terrainTexture`, etc.). `grass.png` is used by `zone1`.
- `hdri/` — `.hdr` environment maps referenced by zone JSON (`skybox`).
  `sky.hdr` is used by `zone1`.
- `maps/` — `zone<N>.json`. `zone1.json` is committed with a default layout.

See `scripts/war-asset-pipeline/README.md` for the intended conversion flow
from a local WAR client.
