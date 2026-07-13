# Blender Character Pipeline

Manifest-first Blender pipeline for War-js runtime assets. The research report
in `deep-research-report.md` is the source of truth for this pipeline:
blueprints and metadata drive generation, Blender object names are labels, and
generated asset IDs/filenames/GLTF extras stay neutral and IP-safe.

## Free Real-Character Pilot

The Battle Prelate and Warbrute pilot is a separate, zero-cost path for natural
humanoid bodies. It uses Blender and MPFB locally. It does not configure Meshy,
does not require an API key, and does not make paid or remote generation calls.
The checked-in policy fixes the currency budget at zero and prohibits generation
in CI.

The pilot specification lives under `data/body-families/`:

- `civic_humanoid_v2.body-family.json` defines deterministic male and female
  Battle Prelate MPFB presets.
- `mire_brutish_v1.body-family.json` defines deterministic male and female
  Warbrute presets backed by hashed, original ear, brow, jaw, and tusk targets.
- `humanoid_game_v2.skeleton.json` defines the 56-bone canonical skeleton,
  `a_pose_v2`, and root, hand, and back sockets.
- `pilot-policy.json` defines the nine armor slots, four-body/36-module
  deliverable, animation list, review sheets, and QC budgets.
- `free-toolchain.json` pins the local dependencies, official asset-pack URLs,
  licenses, and SHA-256 values.
- `templates/*.provenance.template.json` records local inputs, exact revisions,
  prompts/references when applicable, source hashes, licenses, QC, and review
  state. A template is never approval evidence.

Every body recipe remains `promotionEligible: false`. A local Battle Prelate
male body and nine-slot equipped candidate can now be reproduced under the
ignored `artifacts/model-jobs/` tree, but it is still a draft rather than an
approved runtime asset. Generated output stays outside the runtime index until
its content hashes match its QC and review artifacts and a reviewer explicitly
approves it. Missing or rejected bodies continue through the game's existing
Three.js fallback path.

### Free toolchain setup

The real-character path requires:

- Blender 4.2 or newer.
- MPFB exactly 2.0.16, installed from Blender's extension platform.
- The CC0 MakeHuman system, Skins 03, Ears 01, Hands 01, Nose 01, Cheek 01,
  and Faceunits 01 packs from the official MakeHuman Community asset-pack page.
- Node.js 18 or newer for the local orchestration and validation tools.

Install these manually through Blender/MPFB. The repository never downloads or
installs them. MPFB's recommended user-data location is configurable; on a
default Blender 5.0 Windows installation it is commonly:

```text
%APPDATA%\Blender Foundation\Blender\5.0\extensions\.user\blender_org\mpfb\data
```

Run the doctor from the repository root:

```bash
node scripts/blender-character-pipeline/tools/model-doctor.mjs
node scripts/blender-character-pipeline/tools/model-doctor.mjs --strict
node scripts/blender-character-pipeline/tools/model-doctor.mjs --definitions-only
node scripts/blender-character-pipeline/tools/model-doctor.mjs --json
```

The full check discovers Blender from `--blender`, `BLENDER_PATH`, the existing
pipeline config, or `PATH`. It discovers MPFB from `--mpfb`/`MPFB_PATH` and its
standard extension locations. Use `--assets` or `MPFB_ASSET_ROOT` for a custom
MPFB user-data `data` directory. Use `--pack-archives` or
`MPFB_PACK_ARCHIVE_DIR` to retain and re-hash the original pack ZIP files. A
missing retained ZIP is a warning; an installed pack is still checked through
MPFB's `packs/*.json` registration and required pilot-content markers. `--strict`
keeps such unverifiable archives from reporting ready.

`--definitions-only` is the safe CI check: it validates the zero-cost policy,
family recipes, canonical skeleton/sockets, armor slots, budgets, and provenance
templates without requiring Blender or creating an asset. The full doctor also
fails safely for missing original Mire targets or missing/mismatched target
hashes.

Stable Fast 3D is an optional local CPU handoff, disabled by default. Enabling
it requires an explicit local repository path, exact Git revision, checkpoint
path/hash, input hashes, and acceptance of its own license. Its output is only a
candidate; it still needs retopology, modular fitting, canonical rigging, QC,
and explicit review. The pipeline neither downloads its checkpoint nor calls a
hosted endpoint.

## Legacy Manifest Pipeline Prerequisites

- Blender 5.0 or a compatible 3.6+ install for retained non-pilot generators.
  The MPFB real-character pilot above requires Blender 4.2+.
- Node.js 18+.
- MCP server dependencies in `mcp-server/` when using Codex tools.

`config.json` keeps a portable default. Set `BLENDER_PATH` (or pass the tool's
`--blender` option) when Blender is not available on `PATH`:

```json
{
  "blenderPath": "blender",
  "outputDir": "../../public/assets/models",
  "animScale": 1.0
}
```

## Manifest Contract

Blueprints live in `data/asset-blueprints/*.asset.json`. Each blueprint defines:

- `assetId`, `category`, `version`, neutral display/output names.
- Runtime mapping keys such as `profileKey`, `itemKey`, or `staticKey`.
- Output model path and artifact directory.
- Generator kind. Strict mode supports `staticPreset`, `weaponModule`,
  `jewelModule`, `copyExisting`, provenance-verified `externalImport`,
  `mpfbBody`, and `localModularSet`. Primitive `characterPreset`, `bodyModule`,
  and `armorModule` kinds are retired and fail strict validation.
- Geometry, slots/anchors, materials, rigging, collider policy, compatibility, QC thresholds, and AI provenance.

The local schema is `data/asset-blueprint.schema.json`; style constraints are
documented in `data/style-policy.md`.

## Commands

Run from the repository root:

```bash
npm run models:list
npm run models:validate
npm run models:validate:strict
npm run models:doctor
npm run models:cleanup-proxies:check
npm run models:registry
npm run models:assemble-battle-prelate
npm run models:audit-clearance
npm run models:generate -- <retained-non-character-asset-id>
npm run models:all -- smoke
npm run models:all -- destruction_preview
npm run models:all -- equipment
npm run models:all -- weapons
npm run models:all -- jewels
```

`models:generate` accepts an identifier for an active compatibility-allowlisted
non-character manifest. The old playable/NPC character sync commands are
deliberately retired and exit with an error so they cannot recreate proxy
bodies or armor. `models:assemble-battle-prelate` performs the zero-cost clean
body + nine modules + hammer assembly and independently validates its draft GLB,
hash-bound QC report, bind/idle review sheets, one skin, 56 bones, and nine
clips.

Generated artifacts:

- Approved runtime GLB: `public/assets/models/<neutral_name>.glb`
- Approved QC sidecar with matching hash: `public/assets/models/<neutral_name>.qc.json`
- Draft source, preview, and QC artifacts: `artifacts/model-jobs/<job>/`
- Approved-only runtime resolver: `public/assets/models/asset-index.json`

The `artifacts/` tree is ignored and disposable. Delete it during repo cleanup
when screenshot/QC renders are no longer needed; rerunning the relevant
manifest generation command recreates those files.

Strict validation fails for missing indexed GLBs, stale QC hashes, absent
required previews/PBR channels/clips, unsupported or retired generator kinds,
invalid skeleton compatibility, or draft/blocked/unapproved runtime entries.

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
cwd = '/absolute/path/to/War-js/scripts/blender-character-pipeline'
startup_timeout_sec = 120
```

Available tools:

| Tool | Description |
| --- | --- |
| `create_body_family` | Start a local MPFB body-family job. |
| `ingest_generated_candidate` | Quarantine and record a candidate with provider/source provenance. |
| `build_modular_set` | Start fitting and exporting a nine-slot modular set. |
| `validate_model_asset` | Run structured QC for a candidate or assembled asset. |
| `render_model_review` | Produce deterministic local review views and hash-bound animation evidence. |
| `get_model_job` / `cancel_model_job` | Inspect or cancel a long-running local job. |
| `record_model_review` | Record explicit review decisions and evidence hashes. |
| `promote_model_set` | Atomically promote only hash-matching approved assets. |

For focused locomotion and melee review, call `render_model_review` with
`includeAnimations: true` and
`animationEvidenceProfile: "locomotion_melee_key_phases"`. The manifest keeps
the legacy midpoint promotion key for each clip while adding side/back walk and
run phases plus front/side melee ready, windup, impact, follow-through, and
recovery frames. Every emitted PNG receives a SHA-256 hash in the completed job
manifest; the default `midpoint` profile remains available for faster checks.

## Blender Entry Points

The free character pilot uses these review-gated entrypoints:

- `generate_mpfb_body.py` for topology-stable anatomical bodies and canonical rigging.
- `generate_mpfb_modular_armor.py` for the fitted nine-slot local armor set.
- `generate_weapon_attachment_pilot.py` for socketed melee attachments.
- `assemble_runtime_equipped_review.py` for clean-body runtime assembly and bind/idle round-trip evidence.

### Reusable animation profiles

The free canonical animation path has two explicit layers:

- `canonical_mpfb_animation_library.py` owns MPFB-rest-axis locomotion shared by
  every humanoid. Rotations and translations are authored in armature space,
  then converted to each bone's rest basis by `canonical_animation_pack.py`.
- Equipment/class motion is opt-in through `--animation-profile`. The current
  `battle_prelate_hammer` profile holds its right arm steady during locomotion
  and supplies hammer-ready and melee poses without changing generic gait data.

Runtime assembly applies any equipment-specific direction constraints from
`EQUIPMENT_ANIMATION_PROFILES`. A weapon can expose a `weapon_strike_head`
marker; until one exists, assembly records a grip-to-farthest-geometry-cluster
axis in QC. This keeps profile directions semantic (grip toward striking head)
instead of assuming every weapon uses local `+Z`. Wrist keys are bounded by the
profile and the serialized result is sampled again rather than trusting the
authoring scene.

`audit_canonical_animation_motion.py` samples 101 poses per clip. Generic gait
gates cover foot centerlines, lateral foot/hip deviation, knee flex, and hip
bob. The Battle Prelate policy additionally gates socket error, wrist range,
hammer-head arc, windup-to-impact drop, and low/forward impact placement. The
secondary left-hand grip remains advisory until the weapon contract gains a
real secondary-grip node; this draft must not be presented as two-handed.

`generate_asset_from_manifest.py` remains only for compatibility-allowlisted
non-character assets. Primitive character and armor backends are retired; do
not add generation or roster-sync paths that recreate them.

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
- `blends/guard_order.blend` for guard export fallback.

The removed legacy showcase/mannequin scripts and old generated GLBs are
superseded by manifest blueprints and neutral outputs.
