# Local Battle Prelate promotion

`tools/promote_runtime.py` prepares a reviewable publication package below this
authoring directory. Its apply command updates the explicitly named repository.
It does not generate geometry, commit, deploy, or change gameplay code.

The user already authorized local game integration when the model is complete.
The evidence requirement is a technical and visual completion check by the working
agent, not another user permission request. The helper never fabricates a visual
review or converts an unfinished review to an accepted one.

## Required completed inputs

- All 33 self-contained GLBs: 11 modules at each of LOD0, LOD1, and LOD2.
- A passed, full `runtime/validation_report.json`, matching the exact GLB,
  `runtime_report.json`, evaluated-mesh archive, and source hashes. Preparation and application rerun the
  binary validator; edited or stale files are rejected.
- `review/runtime_visual_review.json` written after inspecting the final exported
  assembly. It must identify the reviewer, exact model/report hashes, four final
  equipped views, and at least one animation stress image or contact sheet.
  A review must not mark checks passed merely because images were rendered.
- The existing male Battle Prelate manifests and registry compiler in the target
  repository. No female, other class, or unrelated registry entries are changed.

The visual review format is:

```json
{
  "status": "accepted_for_local_runtime",
  "reviewed_by": "Name of the agent/person who inspected the images",
  "reviewed_at": "UTC ISO timestamp",
  "validation_report_sha256": "Actual SHA256",
  "runtime_report_sha256": "Actual SHA256",
  "model_hashes": {
    "chr_civic_battle_prelate_t1_m.glb": "Actual SHA256; include all 33 filenames"
  },
  "checks": {
    "reference_design": "passed",
    "material_response": "passed",
    "module_fit": "passed",
    "animation_stress": "passed",
    "weapon_socket": "passed",
    "lod_silhouette": "passed"
  },
  "findings": [
    {"blocking": false, "detail": "Record any remaining limitation accurately"}
  ],
  "evidence": [
    {
      "id": "equipped_front",
      "scope": "equipped",
      "view": "front",
      "path": "review/final_export_front.png",
      "sha256": "Actual image SHA256"
    }
  ]
}
```

The example is incomplete and deliberately cannot pass. Supply equipped `front`,
`side`, `back`, and `isometric` entries, plus an `animation_stress` entry. Evidence
paths are relative to this authoring directory; IDs are unique lowercase names.
All images must exist and their recorded hashes must match. A full hash set may be
copied from the validator's module records, but review status/checks are an actual
review decision. This artifact does not assert exact photographic reconstruction.

## Commands

Run from this authoring directory in PowerShell. `node` resolves to the installed
Node executable; `--node` accepts an explicit executable path if needed.

```powershell
$assetPython = 'C:/Users/bschm/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$targetRepository = 'C:/Users/bschm/Desktop/GitPulls/War-js'
& $assetPython -B tools/validate_runtime.py
& $assetPython -B tools/promote_runtime.py --target-repo $targetRepository
```

Preparation prints the exact `promotion/.../promotion_plan.json` path and leaves
the target repository unchanged. Inspect its file list and staged manifests/QC,
then apply that exact plan after the task's local review is complete:

```powershell
& $assetPython -B tools/promote_runtime.py --target-repo $targetRepository --apply 'EXACT_PREPARED_PLAN_PATH'
```

Preparation uses the existing `compileRuntimeRegistry({additionalManifests})` to
write a staged `asset-index.json`. Application publishes that compiler output last.
It refuses stale target files or changed registry inputs; prepare a fresh plan if
another task changes them. It preserves unrelated dirty files and does not reset
or switch the target checkout.

After application, run these existing commands from the target repository:

```powershell
node scripts/blender-character-pipeline/tools/compile-runtime-registry.mjs --check
npm run models:validate
npm run models:validate:strict
npm run typecheck
```

Report pre-existing unrelated strict-validation failures separately. The parent
task also verifies the local game's actual equipped character and animation.

## Publication and archives

- Replaces the 11 LOD0 GLBs and their 11 approved manifests; preserves existing
  profile/item keys, compatibility, and covered-region mappings.
- Publishes the 22 LOD1/2 GLBs and QC sidecars for all 33 models. QC records use
  actual binary measurements and each LOD's own source/build provenance. Old MPFB/Equipment01
  provenance is replaced for these new meshes; rig/action reuse remains disclosed.
- Publishes the reviewed images under a hash-specific model review directory.
  Armor previews are explicitly labeled as shared equipped-character context.
- Archives source records, contracts, current authoring tools, and exact validation,
  runtime, and visual review reports under
  `authoring/archives/battle-prelate-reference-rebuild/<validation-hash-prefix>/`.
  This includes the exact validated `runtime/evaluated_lods.json.gz` archive.
  Required tool copies include `correct_animation.py` and `tessellate_runtime.py`,
  which implement the exported motion correction and tangent-ready tessellation.
  Preparation fails if either helper is missing.
  Tool copies document the promotion-time workspace; only the source-record/build
  hashes establish the geometry revision actually validated.
- Copies every overwritten file into
  `authoring/archives/battle-prelate-promotions/<transaction>/previous/` before any
  replacement. A write failure restores files already replaced where their new
  hashes still match. Concurrent edits are retained and reported as rollback
  conflicts. Archive content is never deleted automatically.

The current registry and game loader use LOD0 filenames only. LOD1/2 are published
and validated, with their paths/hashes in QC, but **the unchanged game does not
switch to those meshes by distance**. This workflow does not claim otherwise.

Verification:

```powershell
& $assetPython -B -m unittest discover -s tests -p 'test_promote_runtime.py'
```
