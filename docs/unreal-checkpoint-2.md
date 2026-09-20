# Unreal implementation checkpoint 2

This is a verified development increment, not a completed conversion or release.
The owner resumed work after checkpoint 1. No requirement was retired to make
this increment pass.

## Implemented

- Actual Unreal imports for the complex Empire herbalist, Dark Elf supply
  officer, Warbrute body and authored command table. Materials reconstruct source
  PBR/alpha channels. Raw and compressed animation samples match source joint
  positions and skinning transforms within 0.1 cm.
- Fixed mismatched FBX bind poses, retained atomic-reimport settings, material
  slot naming and source animation provenance. Generated asset replacement checks
  ownership before changing files.
- A development map with allowed terrain geometry, authored prop meshes and
  explicit character visual DataAssets. Imported movement, jump, attack and death
  clips are available to the native character state logic. Network smoothing
  retains imported mesh offsets.
- A dedicated-process/two-client harness verifies replicated movement, movement
  and strike animation, server damage/mana and rejection of a cooldown retry.
  Windows Development packaging works; the harness also passes using packaged
  clients with offscreen real rendering at 60 FPS.
- Native inventory rules preserve 24 slots, 99-item stacks, individual gear,
  deferred reward quantities/affixes and equipment references to bag items.
  Seven fixtures captured from the browser implementation match native outputs.
  Invalid slots and dangling equipment references are rejected.

## Visual findings and replacement

The legacy male Prelate and male Arcanist source models failed direct Blender
visual review: high polygon counts concealed segmented placeholder bodies.
Their exact source hashes are rejected in `migration/visual-reviews.json`; the
audit and conversion/import tools enforce those decisions. The generated Prelate
FBX and Unreal assets were removed and are absent from the latest cooked content.
Their browser source replacements remain part of the unfinished asset stage.

The female Prelate development identity explicitly reuses the existing complex
female Empire herbalist source via `SourceProfileKey`. Its class/body identity
remains the exported female Prelate profile. Class-specific equipment fit and
final visual approval are still pending. The Warbrute is a substantive authored
body, with clothing/equipment and material review still required. No primitive
substitute was added for either missing source.

## Verified evidence

- Windows Editor compilation and Windows Development BuildCookRun succeeded.
- Eight `AegisWar.Foundation` groups passed. Latest report:
  `artifacts/unreal/editor/test-1789938437231-33420/`.
- 46 Vitest migration tests passed; tools TypeScript checks passed.
- Eight Python import-preflight, three pose-regression and seven Blender
  conversion tests passed.
- Final packaged/rendered multiplayer report and screenshots:
  `artifacts/unreal/network/1789938470497-35636/`.
- Development package: `artifacts/unreal/packages/Win64/`.
- `npm run unreal:release-check` exited 1 with `readyForRelease: false`, as
  required while the remaining acceptance gates are unmet.

Generated evidence, imported packages and binaries are ignored and reproducible;
they are not a replacement for source-controlled scripts and acceptance tests.

## Outstanding work

Stage 1 remains incomplete: the installed engine lacks Linux target files, a
packaged dedicated Linux server is unverified, and native macOS builds require
Mac hardware/tooling. Equipment and moving-mechanism proof also remain open.
The uncapped NullRHI packaged-client movement timing failure remains a hardening
investigation; the passing harness uses 60 FPS.

The full RPG, replicated inventory UI, durable economy/idempotency, crafting,
quests, campaign, all zones/travel/interiors, runtime GM editor, comprehensive
model replacement/primitive deletion, platform QA and Steam integration/release
are unfinished. Pure inventory rules and exported catalogs do not implement
those systems. Production admission remains closed. No Steam account, store,
deployment or external publication action was performed.
