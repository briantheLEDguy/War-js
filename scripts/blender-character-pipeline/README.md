# Blender Character Pipeline

Manifest-first Blender pipeline for War-js runtime assets. The research report
in `deep-research-report.md` is the source of truth for this pipeline:
blueprints and metadata drive generation, Blender object names are labels, and
generated asset IDs/filenames/GLTF extras stay neutral and IP-safe.

## Prerequisites

- Blender 5.0 or compatible 3.6+ install.
- Node.js 18+.
- MCP server dependencies in `mcp-server/` when using Codex tools.

The local Blender path lives in `config.json`:

```json
{
  "blenderPath": "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe",
  "outputDir": "../../public/assets/models",
  "animScale": 1.0
}
```

## Manifest Contract

Blueprints live in `data/asset-blueprints/*.asset.json`. Each blueprint defines:

- `assetId`, `category`, `version`, neutral display/output names.
- Runtime mapping keys such as `profileKey`, `itemKey`, or `staticKey`.
- Output model path and artifact directory.
- Generator kind: `characterPreset`, `staticPreset`, `bodyModule`, `armorModule`, `weaponModule`, `jewelModule`, or `copyExisting`.
- Geometry, slots/anchors, materials, rigging, collider policy, compatibility, QC thresholds, and AI provenance.

The local schema is `data/asset-blueprint.schema.json`; style constraints are
documented in `data/style-policy.md`.

## Commands

Run from the repository root:

```bash
npm run models:list
npm run models:sync-playables
npm run models:sync-npcs
npm run models:validate
npm run models:generate -- chr.human.devout_guardian.t1.m
npm run models:all -- smoke
npm run models:all -- playable_smoke
npm run models:all -- playable_characters
npm run models:all -- playable_armor
npm run models:all -- playable_all
npm run models:all -- npc_characters
npm run models:all -- enemy_characters
npm run models:all -- enemy_creatures
npm run models:all -- destruction_preview
npm run models:all -- equipment
npm run models:all -- characters
npm run models:all -- weapons
npm run models:all -- jewels
```

`models:generate` accepts an `assetId`, manifest filename, output filename,
profile key, item key, or static key.

`models:sync-playables` expands
`data/playable-character-roster.json` into 48 playable character manifests,
432 starter armor-module manifests, `asset-index.json` entries, and
`src/data/playableAssets.generated.ts`. It is deterministic and should be run
after any playable race, class, body-variant, or armor-slot theme change.

`models:sync-npcs` scans `public/assets/maps/*.json`, applies the shared rules
from `scripts/npc-profile-rules.mjs`, and emits deterministic NPC/enemy
character manifests, creature static prop manifests, `asset-index.json`
entries, and `data/npc-character-roster.json`. Static NPCs and humanoid enemies
use `characterProfileKey`; training dummies and creature enemies use indexed
static `assetKey` values.

Generated artifacts:

- Runtime GLB: `public/assets/models/<neutral_name>.glb`
- QC sidecar with `qcPassed: true`: `public/assets/models/<neutral_name>.qc.json`
- Human preview/QC artifacts: `artifacts/blender/manifest/<asset_key>/`
- Runtime resolver: `public/assets/models/asset-index.json`

The `artifacts/` tree is ignored and disposable. Delete it during repo cleanup
when screenshot/QC renders are no longer needed; rerunning the relevant
manifest generation command recreates those files.

`models:validate` fails if an existing generated GLB has no QC sidecar, if the
sidecar does not report `qcPassed: true`, if preview-required character output
lacks preview images, or if a blocked runtime index entry lacks `reviewStatus`.

## MCP Tools

Install dependencies:

```bash
cd scripts/blender-character-pipeline/mcp-server
npm install
```

Codex config:

```toml
[mcp_servers."blender-character"]
command = 'node'
args = ['mcp-server/server.mjs']
cwd = 'C:\Users\bschm\Desktop\GitPulls\War-js\scripts\blender-character-pipeline'
startup_timeout_sec = 120
```

Available tools:

| Tool | Description |
| --- | --- |
| `list_asset_blueprints` | Show manifest blueprints and generated output status. |
| `generate_asset` | Generate one manifest-backed asset. |
| `generate_asset_set` | Generate a manifest set such as `smoke`, `equipment`, or `characters`. |
| `validate_asset` | Validate all blueprints plus `asset-index.json` references. |
| `list_generated_assets` | Show GLB and QC sidecar presence. |

## Blender Entry Points

The supported generator entrypoint is:

```text
blender/generate_asset_from_manifest.py
```

It dispatches to retained builder modules behind neutral presets:

- `generate_manifest_character.py` for rigged manifest character profiles.
- `generate_manifest_accessory.py` for weapon and jewel accessories.
- `generate_static_asset.py` for generated props.
- `generate_base_male_armor_showcase.py` functions for the reusable body and armor modules.

Direct legacy scripts are kept only as implementation backends or specialized
exporters. Do not add new public generation flows that bypass manifests.

## Runtime Contract

`AssetLoader` reads `public/assets/models/asset-index.json` and resolves:

- character profile keys to neutral character GLBs,
- equipment item keys to neutral armor GLBs and optional body overrides,
- static prop keys to neutral prop GLBs.

If any indexed file is missing or fails to load, the runtime still uses the
existing primitive fallback path and increments the debug fallback counter.
If indexed equipment is marked `runtimeReady: false`, the runtime intentionally
skips the generated file. This keeps unskinned same-origin modules and unsocketed
accessories out of gameplay until a later manifest-backed skinning/socket pass.

Playable characters use one profile per race, player-facing class, and body
variant (`m` or `f`). Runtime armor for `head`, `shoulders`, `chest`, `hands`,
`waist`, `legs`, `feet`, `back`, and `tabard` must be skinned to the same
`skeletonId` and `bodyFamily` as its matching character body. Compatible armor is
loaded as a skinned overlay and rebound to the player skeleton; `coveredRegions`
metadata masks only the body regions hidden by the equipped slot.

## Export Rules

- Runtime axes: X right, `+Y` up, `+Z` forward.
- Units: meters.
- Character/body origin: root grounded at the neutral pose.
- GLTF extras use `assetId`, `assetKit`, `assetCategory`, `assetSlot`, `bodyFamily`, and `skeletonId`.
- Do not add legacy protected naming fields or protected branded-world names to generated extras.

## Active Source Assets

Keep source files only when referenced by a manifest-backed builder or exporter:

- `blends/male_base.blend` for human body and fitted armor modules.
- `blends/altdorf_land.blend` for the current terrain exporter.
- `blends/guard_order.blend` for guard export fallback.

The removed legacy showcase/mannequin scripts and old generated GLBs are
superseded by manifest blueprints and neutral outputs.
