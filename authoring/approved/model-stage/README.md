# Model-stage-approved authoring bundles

This directory is written only by the local full-roster review workflow.
Each `<kind>/<key>/` bundle is hash-bound to one generated run/revision and
contains `model-stage-approved.json`, LOD0 GLBs, QC reports, and review evidence.

These files are **not runtime assets**. Approval keeps `runtimeEligible: false`
and `animationStage: pending`; it does not update
`public/assets/models/asset-index.json`. GLBs under this directory are tracked
with Git LFS. Reapproval replaces the canonical item bundle and records compact
review/hash history under `history/`.
