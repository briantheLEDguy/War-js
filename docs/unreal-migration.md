# Unreal and Steam migration

## Delivery contract

The approved target is an online-only Unreal 5.8.2 game for Steam on native
Windows, Linux and macOS, with 18 players per realm per contested zone. Fresh
characters replace browser save import. Every implemented local and shared
gameplay/GM capability remains required. Merchant/banker/trainer transactions,
persistent summons, warbands and other unimplemented systems remain separately
identified; descriptions and NPC role labels are not evidence of implementation.

Only repository models and adaptations of their sources may be used. Every
playable body/class variant, NPC, enemy, resident, ambient creature, preview,
equipment set and siege crew needs a suitable complex model. Visible primitive
models, dummy substitutions for real enemies and invisible combatants are not
acceptable. Collision, navigation, terrain construction, editor guides and
intentional effects remain valid technical geometry. Preserve Git history.

`migration/unreal-policy.json` records these decisions and browser baseline
`4965996`. The branch is `codex/unreal-migration`. The browser game remains the
behavior reference while replacements are developed; its legacy primitive paths
are outstanding migration debt, not a completed cleanup.

The owner requested a pause after the first implementation checkpoint to change
models. See `docs/unreal-checkpoint-1.md` for verified results and the next work.

## Implementation and stage gates

| Stage | Required outcome | Current evidence |
|---|---|---|
| 0: inventory | Complete behavior/content/model ledgers and reproducible source fingerprints | Exporter, 39 detailed behavior contracts, asset resolver/GLB audit and readiness report implemented; art/rights review remains open |
| 1: engine proof | Native builds on three OSes, Linux server, representative imports and two-client movement/combat | Windows Editor target compiles; conversion samples and development tools are ready. Other native targets, actual imports and two-client playtests remain unverified |
| 2: assets | All character/species/environment replacements, rig/animation/equipment/LOD validation, primitive deletion | Incomplete; audit reports blocked/candidate rows, never fabricated approval |
| 3: RPG | All current combat, progression, inventory, gathering/crafting, quests and HUD behavior under server authority | Pending; exported catalogs do not implement gameplay |
| 4: online | Steam ownership, full characters/economy/chat, handoffs, supplies/siege/campaign, durable recovery | Pending; native production admission remains closed |
| 5: world/GM | All 32 campaign zones, 70 directed routes, interiors/lifts, atlas/wiki/settings and runtime GM editor | Pending; preserving raw map data is not importing a playable world |
| 6: hardening | WAN, simultaneous 18v18 fronts, crashes/retries/backup restore, platform and performance acceptance | Pending |
| 7: Steam | Playtest, native depots, clean install/update, disclosures/review and release | Pending; no store or deployment action performed |

The planned effort remains 26–47 person-months before contingency, approximately
35–60 including integration/learning risk. These are estimates, not achieved
work or elapsed schedules. No feature or model is dropped to meet them.

## Architecture and file ownership

- `unreal/AegisWar/` contains native C++ targets and engine configuration. Unreal
  owns live movement, collision, combat, abilities, AI and zone replication.
  PlayerState owns persistent-within-session ability state; no browser rendering
  or visible primitive meshes are imported as a fallback.
- The existing Node server is the reference for eventual campaign/account/
  persistence coordination. Its browser combat authority has not been silently
  replaced. Native development and browser authorities are separate processes;
  a later cutover must give each live datum exactly one owner.
- `scripts/unreal/export-content.ts` exports complete raw map definitions and
  catalogs, including current ability effects/unavailability, crafting rules,
  campaign data, guide pages, keybindings, settings and builder definitions.
  `content-contract.ts` defines stable JSON/hashes and coordinate conversion.
- `scripts/unreal/asset-ledger.ts` audits actual requests and resolver outcomes,
  binary GLB geometry/skins/clips, hashes, LODs, provenance and adaptation
  candidates. `primitive-audit.ts` classifies source findings without deleting
  technical geometry. Saved browser/remote content is not present in this audit.
- `scripts/unreal/feature-parity.ts` records current source/tests and required
  acceptance scenarios for every subsystem. All native gameplay contracts remain
  pending until actual engine tests and playtests establish parity.
- `scripts/unreal/migration.ts` emits all reports and rejects release while
  required acceptance is missing. It cannot be bypassed by changing an asset
  file's existence or labeling a generated catalog as native gameplay.

The canonical export retains source coordinates and every map field. For
positions only, source `(x,y,z)` meters maps to Unreal `(X=z*100,Y=x*100,Z=y*100)`
centimeters; source Y yaw maps to Unreal Z yaw degrees. Arbitrary mesh, skeleton,
scale and rotation conversion must be checked during import. Do not apply the
position multiplier twice to a mesh importer that already converts units.

## Reproduce the migration inventory

```powershell
npm run unreal:audit
npm run unreal:export -- --check
npm run unreal:assets -- --strict
npm run unreal:release-check
npm run test:unreal
npm run typecheck:unreal-tools
```

Reports are generated under ignored `artifacts/unreal/`: `content.json`,
`asset-ledger.json`, `feature-parity.json` and `readiness.json`. They include
source/content fingerprints and can be recreated. The complete export is large;
do not commit a second copy of the maps or generated reports.

Audit/export success means the inventory was generated/validated. The two strict
commands currently **must fail** because complete model, gameplay, platform and
Steam acceptance does not exist. These are useful failures, not tests to weaken.
Actual clip compatibility, visual quality and commercial rights need review;
GLB triangle counts or registry approval alone cannot provide it.

The model audit covers both canonical maps and the development map, ownership
variants, generated interior templates, approved registry entries and unused
public GLBs. Its assignment count is not a count of unique characters or missing
models. Explicit adaptation candidates are never assignments or approvals.

## Native development

```powershell
$env:UNREAL_ENGINE_ROOT = 'C:\Program Files\Epic Games\UE_5.8'
npm run unreal:doctor
npm run unreal:stage
npm run unreal:build -- --target Editor
npm run unreal:build -- --target Client --platform Win64
npm run unreal:build -- --target Server --platform Linux
```

Doctor checks the exact engine version and build/editor entry points. It does
not certify compiler/SDK availability; the native build supplies that evidence.
The launcher engine may not contain dedicated-server build support. A suitable
source/installed engine and Linux toolchain are required for that target. macOS
build/QA requires Mac hardware and the matching Xcode toolchain.

Staging is explicitly development-only and copies content into the ignored
`Content/Migration/` path. It does not assign unreviewed models, instantiate all
maps or permit production login. Native settings must point to validated imported
visual DataAssets before characters can spawn. No starter mannequin, cube,
sphere, capsule or training dummy substitutes for a missing character.

The build wrapper only accepts Development/DebugGame configurations. Production
packaging, native acceptance receipts and the trusted Steam admission gateway
are future implementation gates. Run `npm run unreal:test-native` after building
the Editor target to execute the seven `AegisWar.Foundation` automation groups.
The wrapper requires a fresh report containing all seven successful groups;
editor exit status alone is not a passing test result.

## Asset conversion experiments

`scripts/unreal/convert-model.py` runs in a disposable Blender scene. It reads a
registered GLB and QC whose hashes match the registry, exports FBX into ignored
`artifacts/unreal/converted/<profile>/`, and performs a Blender roundtrip check.
It never rewrites approved source files, changes profile assignments or grants
Unreal approval. For example:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/unreal/convert-model.py -- --profile npc_frontier_sunmeadow_empire_herbalist
```

Verify each clip, bind pose, centimeter scale, axes, material reconstruction,
LODs, equipment fit, collision and silhouette in Unreal before publication.
Any animation conversion failure is a failed experiment, not a reason to strip
the animations or replace the character with a primitive.

`scripts/unreal/import-models.py` consumes verified conversion receipts and
imports the command table and two NPC samples into `/Game/Imported/`. Run
`npm run unreal:import -- --profile frontier_field_command_table` after building
the Editor; the other supported sample keys are
`npc_frontier_sunmeadow_empire_herbalist` and
`npc_frontier_cinderfen_dark_elf_supply_officer`. This reconstructs materials from
source images and records actual imported mesh/animation paths. Native character
entry requires a matching `Content/Migration/visual-imports.json` binding in
addition to a visual DataAsset. An import receipt is development evidence, not
art approval, a playable-class assignment or proof of full animation parity.

## Completion and operating acceptance

Maintain a testable checklist for all 240 abilities (including three disabled
outcomes), both quest chains, all crafting/gathering, inventory capacity and
reward idempotency, the whole campaign cycle, all travel/interiors/lifts, all GM
draft/publish/restore actions, keybindings/touch/input isolation and visual maps.
Native acceptance must also cover realm queues, reconnects, stale commands,
single-character ownership, concurrent fronts, crash recovery, durable writes,
backup restore and patch/content compatibility.

Steam identity must be verified by trusted services; no client or native demo
parameter may self-assert paid ownership or GM privileges. Steam credentials,
database secrets and signing keys must never enter client assets or Git. Store
onboarding, application fees, native build review and release happen only after
the project satisfies the relevant stage gates.

Current platform references:
[Epic Steam integration](https://dev.epicgames.com/documentation/unreal-engine/online-subsystem-steam-interface-in-unreal-engine),
[FBX pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-content-pipeline),
[Steam authentication](https://partner.steamgames.com/doc/features/auth),
[Steam onboarding](https://partner.steamgames.com/doc/gettingstarted/onboarding).
