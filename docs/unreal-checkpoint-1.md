# Unreal migration checkpoint 1

The owner requested pausing at the first checkpoint to switch models. No work
should resume until the owner continues this task. This checkpoint implements
the migration foundation; it does not complete Stage 0 or Stage 1 acceptance,
the full engine port, Steam integration or primitive-model removal.

## Repository state

- Branch: `codex/unreal-migration`; browser baseline: `4965996`.
- Scope and required stages: `docs/unreal-migration.md` and
  `migration/unreal-policy.json`.
- Native project: `unreal/AegisWar/AegisWar.uproject`, pinned to Unreal 5.8.2.
- Installed engine: `C:/Program Files/Epic Games/UE_5.8`.
- Installed C++ tools: Visual Studio 2022 Build Tools, MSVC 14.44, Windows SDK
  10.0.22621.0 and .NET Framework 4.8 SDK. `.vsconfig` records components.
- Blender: `C:/Program Files/Blender Foundation/Blender 5.0/blender.exe`.
- Generated reports, converted FBXs, build products and imported experiment
  assets are ignored artifacts. Keep authored source, scripts and tests in Git.

## Implemented foundation

- Deterministic content export preserves raw maps/catalogs and source hashes:
  32 campaign maps, one development map, 48 playable variants, 240 abilities,
  482 items, eight quests and 457 builder prefabs.
- The parity ledger records 39 behavior contracts with source references and
  acceptance scenarios. Native parity remains pending for all contracts.
- The asset ledger enumerates 15,895 assignment rows: 6,464 blocked, 9,431
  candidates and zero art-approved Unreal mappings. Rows include placements,
  generated paths, equipment, previews and shared/local variants; they are not
  unique model counts. Of 48 playable variants, 43 lack direct current coverage.
- Native C++ foundation includes GAS ownership on PlayerState, replicated
  movement, a server-only sample strike, health/mana, cooldowns and respawn,
  Enhanced Input, an entry-error UI and import-bound character visual validation.
  This implements one demonstration ability, not the 240-ability catalog.
- Production admission is closed. Explicit nonshipping development networking
  uses `-WarDevelopmentNetworking`; it does not verify Steam ownership.
- Converter and importer preserve source provenance and refuse primitive
  substitutes. The two NPC FBXs contain one authored mesh, 56 joints and nine
  animations each. Blender's generated bone-display Icosphere is excluded by
  disabling its creation and enforcing exact source mesh identities/counts.

## Verification

- Browser/full Vitest regression: 1,473 tests across 176 files passed before
  two additional automation-report tests were added.
- Current migration Vitest suite: 35 tests passed. The revised automation-report
  validator also passed its focused rerun.
- Migration tooling and server TypeScript checks passed; browser production
  build passed with the existing large-chunk warning.
- Seven Blender conversion tests and seven importer preflight tests passed.
- Both NPC conversion roundtrips passed all nine clips, 17 pose samples per clip,
  source mesh identity/triangle counts, joint motion and evaluated bounds checks.
  The static command table conversion contains six meshes and 27,534 triangles.
- Strict release check exited 1 as required: model, gameplay, platform and Steam
  acceptance are incomplete. Audit generation itself passed.
- Native Windows Editor target compiled successfully with Unreal 5.8.2 and MSVC
  14.44. Build log: `artifacts/unreal/checkpoint-1-native-build.log`.
- All seven `AegisWar.Foundation` native automation groups passed in the actual
  Unreal Editor with NullRHI. Report:
  `artifacts/unreal/editor/test-1789933343279-22576/index.json`.
  The first run exposed a test-world lifecycle omission; the fixture now uses
  normal component initialization and asserts GAS attribute registration before
  the unchanged health, mana and cooldown checks. This is headless foundation
  validation, not graphical, network or complete gameplay acceptance.
- Actual Unreal model imports and graphical/two-client playtests have not run.

## Resume sequence

1. Read this checkpoint and inspect Git state. Preserve all scope and model
   requirements; do not infer approval from metadata or polygon counts.
2. Rebuild and rerun native foundation checks after changing native code. Commands:
   `npm run unreal:build -- --target Editor`, then `npm run unreal:test-native`.
   Engine build/test caches can require access outside the repository.
3. Run `npm run unreal:stage` if the content export is stale. Import the three
   converted samples through `npm run unreal:import -- --profile <key>`; see
   `docs/unreal-migration.md` for exact keys. Import scripts have passed preflight
   only; their Unreal Python execution and actual imported outputs need testing.
4. Validate materials, animations, scale, axes, collision and equipment visually.
   Existing sample NPCs are not assigned to playable classes. Choose suitable
   repository playable sources and establish reviewed DataAssets before spawn.
5. Prove two clients, predicted movement and the sample ability. Then establish
   native Windows/Linux/macOS builds and Linux dedicated-server support. The
   launcher engine may need replacement with a suitable source/installed build
   for server targets; Mac hardware/toolchain is still required.
6. Continue the full approved stage plan. All implemented gameplay/GM capability
   remains required. Complete suitable replacements before deleting dependent
   browser primitives; the old primitives are still present and explicitly owed.

Do not publish, claim platform support, promote candidate models to approved,
weaken release gates, or declare the migration complete from this checkpoint.
