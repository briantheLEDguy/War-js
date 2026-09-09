# Corrected buck candidate handoff

**Paused:** the user now prioritizes characters, equipment and town/siege assets;
animals are last. No more fauna model work or new review batches. Only the
already-running `buck_final_cycle_receipts.log` batch may finish safely. Pending
review preparation/publication is left to root after the stable checkpoint.

Root subsequently cancelled that remaining render batch; session69463 exited1.
Saved current profile receipts: all8 run phases and walk0/.125/.25. Missing final
profile receipts: walk.375/.5/.625/.75/.875, idle0/.5, graze0/.25/.5/.875. Existing
three-LOD rest/run/graze full views, head close views and peak-tuck views remain
saved. This is a stable accepted-for-now checkpoint with incomplete formal cycle
evidence, not a published release. Do not run more fauna work during the pause.

The user accepted the current buck for now and explicitly ended further rump
iteration. Root instructed freezing these exact models and moving to red fox.
No further buck shape edits or aesthetic approval loop are required. Publication
has not run; root owns the final registry/catalog/map integration. Current work
only completes fixed-byte cycle receipts required by the existing publisher.

The three literal models include idle, walk, run and graze with portable signed
morph corrections. `frontier_sunmeadow_roe_deer_buck.blend` is the editable morph
master. The current base under `runtime/` is an uncorrected authoring input and
must not be substituted for these reviewed candidate GLBs.

| LOD | Bytes | Morph modes | SHA-256 |
|---|---:|---:|---|
| 0 | 12,315,668 | 36 | `5ef5815a7eba661b2e61eecba12c41b1f3a13cbf1905d2da83540b8db37d0f76` |
| 1 | 4,704,292 | 32 | `9525ad6c0ec4d78329ba4d113bcda9c554859a6a96eec6e91677e3a9c679fd1d` |
| 2 | 2,022,780 | 32 | `39cb49e2692917c6f8a2aacf437050da1dfab9ffc0889c49d6c5330781e3e0ed` |

All unchanged technical gates pass for these bytes: three Khronos inspections
with zero errors/warnings,12 actual clip/LOD key-and-midpoint audits, run maximum
stretch3.355/p991.635 across LODs, planted-foot error4.47mm, root/loop displacement0.
The current base head positions, corner normals, tangents, UVs, colors and original
atlas islands0–6 remain exactly preserved.36 Python and10 Node regressions pass.

The new candidate-aware publisher binds `candidate.json`, both editable base and
corrective masters, base authoring inputs, the literal corrected GLBs, matching
technical/motion reports and actual-import image receipts. It requires all three
LOD rest/run/graze comparisons plus full LOD0 cycle and close-head coverage.

After the remaining actual visual review is complete, prepare its pending record:

```powershell
node authoring/blender/sunmeadow-fauna/tools/publish_fauna.mjs --assets=roe_deer_buck --candidate-dir=review/candidates/buck_differential --prepare-review
```

The record is local `visual_review.json` in this candidate directory. Only after
root records the final matching visual decision, the same command with `--publish`
instead of `--prepare-review` freezes the reviewed sources and copies the literal
corrected models. It does not regenerate geometry, rebake motion, replace base
runtime files, or compile the global registry/GM catalog. Publication has not run.

`checkpoints/buck-before-hamstring/` preserves the prior passing draft and its
rejected rectangular peak-tuck profile for comparison; it is not a release.
