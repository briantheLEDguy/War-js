# Repository size audit — 2026-09-08

The cleanup removes approximately **2.54 million text lines (39.5%)** and
**143 MB of working-tree files**, while preserving live map content and approved
asset evidence. These counts include JSON data, not just executable code.

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

## Removed content and dependency evidence

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
promotion archives, active authored geometry, the final accepted Battle Prelate
revision, Sunmeadow's active canopy revision and ongoing draft art diagnostics
remain. Size alone is not grounds to delete them. This audit removes identified
unused content; it does not claim every possible unused parameter or asset has
been eliminated.

Existing Cinderfen road idempotence and scene-clearance test failures also occur
on the baseline. They belong to the concurrent world work. Existing retained
Cinderfen utility hashes can fail strict authoring validation after Windows
CRLF checkout conversion; this cleanup does not replace or relax those hashes.

## Verification

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

Further reductions should target demonstrated duplicate source structures and
unreferenced diagnostic outputs. Avoid minifying editable geometry merely to
lower line counts or deleting evidence required by current asset approvals.
