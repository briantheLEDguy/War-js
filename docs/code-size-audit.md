# Repository size audit — 2026-09-08

Across two passes, the cleanup removes approximately **2.81 million text lines
(43.7%)** and **218 MB of working-tree files**, while preserving live map content
and approved asset evidence. These counts include JSON data, not just executable
code. The first pass (`67cbc72`) removed 2.54 million lines and 143 MB; the
follow-up below removes another approximately 268,000 lines and 75 MB.

## Baseline and scope

Measured clean commit `5eb9ed1` in the isolated `codex/code-size-cleanup` worktree:
6,427,259 text lines in 196,048,111 bytes. The concurrently edited original
checkout had approximately 6.59 million lines; those edits were left with the
world task. The screenshot shows a branch comparison; `5eb9ed1` itself added
3,350,378 lines. Most volume comes from generated maps and Blender source/review
JSON. No history rewrite or deployment is part of this cleanup.

Run `npm run audit:size` to repeat the read-only inventory, or
`npm run audit:size -- --json` for structured counts, large files and exact-byte
duplicate candidates. It counts tracked and unignored text files, skips missing
files, and reports application TypeScript separately. Duplicate bytes alone do
not establish that a file is unused.

## First-pass removals and dependency evidence

| Change | Text lines removed | Evidence |
| --- | ---: | --- |
| Obsolete Cinderfen kit snapshot `f6d472…` | 250,304 | No references; current provenance names the newer source. |
| Six pre-final Battle Prelate revision snapshots | 437,510 | Generated historical scratch; current builders read `source/` and active review files. |
| Isolated tabard surface probe outputs | 75,348 | Reproducible diagnostic scratch, with no active approval consumers. |
| Duplicate current Cinderfen kit snapshot `91af22…` | 355,650 | Byte-identical companion source was already independently required by the validator. |
| Published biome placement plans | 808,692 | Used only during authoring; no game, server or Blender consumer reads the published copies. |
| Repeated Aegis elevation values | 606,481 | Lossless runs preserve every one of the 641,601 samples. |
| Runtime/catalog and generator cleanup | About 5,350 net | Unreachable functions/components and duplicated catalog records. |

The artifact cleanup deletes 149 files / 115,526,333 bytes. The six obsolete
revision IDs are `20260905T213826Z`, `20260905T214352Z`, `20260905T215209Z`,
`20260905T223502Z`, `20260905T224313Z`, and `20260905T224844Z`. Historical
installation receipts can still mention those files; they are records, not
current build inputs. Git retains their history.

The current Cinderfen kit reference now points to `../source/architecture.json`.
Both provenance and the independent source contract retain the exact SHA256
check. Only the changed provenance writer's hash was refreshed. The older
utility references were preserved. New scratch revision/probe outputs are
ignored so ordinary builds do not grow another tracked history tree.

## Data and code improvements

The 32 campaign maps shrink from **35,194,520 to 9,438,436 bytes (73.18%)**, and
from **1,868,491 to 453,318 lines (75.74%)**. Authoring still computes vegetation
clearances before publication; only the unused `orvrLayout.biome.placements`
field is omitted. Active props, roads, terrain, NPCs, objectives and travel links
are unchanged. Map hashes, the TypeScript campaign catalog and SQL seed are
regenerated together.

`scripts/campaign/compact-city-elevation.mjs` stores repeated heights as
`[exclusiveSampleEnd, height]` runs. The browser uses binary search directly on
these runs rather than allocating a dense replacement array. Dense fields remain
supported. Authoring placement and runtime movement share the same triangle
interpolation through `src/world/CityElevation.ts`; three separate samplers no
longer need to stay in sync. Aegis's serialized elevation field uses about 8.05%
of the original height-array bytes, without reducing resolution or precision.

The 432 starter armor catalog records are derived from existing character
profiles instead of repeated in a 4,754-line literal. All serialized entries and
48 starter loadouts are checked. The source generator emits the same derivation.
The old map panel, unused combat/editor/animation helpers and unused exports were
removed. Crafting's unused parent subscription was removed; child views retain
their own subscriptions. TypeScript's `noUnusedLocals` check now prevents new
unused imports, local variables and private fields from accumulating.

## Retained content and limits

All runtime/server modules were reachable from the application or server entry
points; there was no evidence for deleting entire live modules. Referenced
promotion archives, active authored geometry, required final Battle Prelate
revision evidence, Sunmeadow's active canopy revision and ongoing draft art diagnostics
remain. Size alone is not grounds to delete them. This audit removes identified
unused content; it does not claim every possible unused parameter or asset has
been eliminated.

Existing Cinderfen road idempotence and scene-clearance test failures also occur
on the baseline. They belong to the concurrent world work. Existing retained
Cinderfen utility hashes can fail strict authoring validation after Windows
CRLF checkout conversion; this cleanup does not replace or relax those hashes.

## First-pass verification

- Old and cleaned generator outputs matched for all 34 emitted artifacts before
  publication changes. Afterwards all 32 maps matched every original field when
  decoding elevation and excluding only draft placements and content hashes.
- Repeated campaign generation changed none of its outputs.
- The original full Aegis sample digest and fractional/edge interpolation are
  regression-tested, alongside authoring placement and rendered terrain tests.
- Production build, frontend/server typechecks, world validation, 843 model
  validation records and the 374-entry builder catalog passed.
- Full suite (`npm test -- --maxWorkers=2`): **1,146 passed, four existing
  Cinderfen failures** in `orvrRoadNetwork.test.ts` and `worldLifeContent.test.ts`.
  All 137 suites loaded after the scoped Windows LF fix. Two focused provenance
  tests and the three existing Python source checks also passed.

## Second pass: duplicate source copies and unused diagnostics

Measured against `67cbc72`, this pass removes **122 files** containing 262,750
text lines and 74,927,130 bytes. Profile construction removes another 5,102 net
lines; documentation and retention tests add a small amount back.

| Change | Files removed | Text lines removed | Evidence |
| --- | ---: | ---: | --- |
| Horse trial/gait reports, old motion reports, export smoke and novitiate probes | 8 | 123,478 | Path and SHA256 searches found only writers or historical copy receipts, with no active readers or approval dependencies. |
| LOD surface-transfer probe outputs | 55 | 683 | Retained `probe.py` recreates them; accepted models embed their textures and do not require these standalone copies. |
| Unused Ember inherited tools and three unused component copies | 24 | 31,611 | Replaying `author_ember.py` and `refine_ember.py` with and without them produced 20 byte-identical outputs. |
| Remaining redundant final Battle Prelate revision copies | 35 | 106,978 | Every file has a SHA256-identical retained source/review copy; source records also remain in the approved archive. |

The inherited component copies are `gorget.json`, `repeated_reliquaries.json`
and `warhammer.json`. All 14 consumed inherited records remain. The final
`20260906T004719Z` revision retains `tools/build_proof.py` and
`full_three_quarter_material.png`, which still have active evidence/reference
consumers. Historical installation inventories remain unchanged.

The 48 playable profiles now use class, body-variant and armor-slot seeds. The
generated module falls from 5,505 to 373 lines. Full serialized profile, catalog
and loadout digests match the old values; all 432 armor records and coverage
arrays retain separate mutable ownership. The generator emits the same seeds
without adding a runtime dependency on Node tooling or manifests.

The production main JavaScript bundle falls from 1,781.24 to 1,674.77 KB
(gzip: 463.41 to 454.70 KB). This is a bundle-size measurement, not an FPS claim.

`tests/authoringEvidenceRetention.test.ts` checks ten archived report/ledger
hashes, 42 referenced source-file hashes, all 69 source-ledger inputs, and seven
supplemental reports plus 34 review images required by accepted visual reviews.
Hydrated image bytes or unhydrated Git LFS object IDs must match their recorded
SHA256 values. Both exported-motion
audit reports remain. No approval hashes were replaced or relaxed. A separate
baseline comparison verified all 1,706 protected text files in maps, manifests,
active source/runtime/texture records and promotion archives stayed byte-identical.
Editable geometry was neither reformatted nor minified.

Exact ignore rules keep the removed diagnostics and unused inherited copies
local if a tool recreates them. Their generators, required evidence and the
surface-transfer probe source remain tracked.

Second-pass verification: production build, frontend/server typechecks, world
validation, 843 model records and the 374-entry builder catalog passed. The full
suite loaded all 138 files: **1,151 tests passed, with the same four baseline
Cinderfen failures** listed above. The new profile-equivalence, mutable ownership
and approval-evidence retention checks all passed.

## Integration with ongoing world work

The cleanup is merged with `e1f5490`, retaining the reviewed caravans and newer
Cinderfen clearance changes. All 32 regenerated maps match that commit's live
fields after decoding elevation and excluding only draft placement metadata and
publication hashes. The merged Cinderfen hash is `d22eea91c8979adc`.

The regional road test rebuilds authoring exclusions before composing Cinderfen,
so it still checks deterministic roads and every vegetation exclusion without
requiring draft data in published maps. Its 37 tests pass. Production build,
frontend/server typechecks, 33-map validation, 843 model records and the 374-entry
builder catalog pass on the merged committed content. Unfinished world and art
drafts in the original checkout remain separate from this merge.

The final full run passes **all 1,160 tests in 139 files**. The newer world
clearance changes resolve the four failures recorded in the earlier baseline.
