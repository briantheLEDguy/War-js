# Model storage cleanup — September 24, 2026

The cleanup increased C: free space from **157.25 GiB to 247.77 GiB**, a measured
net gain of **90.52 GiB** before the final verification logs. These are filesystem
free-space readings, not a sum of file sizes that would double-count junctions.
Concurrent tasks can change the final free-space reading slightly.

## Removed

- Nine inactive, merged worktrees: the two temporary integration checkouts,
  four authoring worktrees and three Codex model/campaign worktrees. Their branch
  history remains in Git. Unique uncommitted non-model work and non-animation
  review evidence were inventoried and retained before removing the checkouts.
- Superseded model releases, trial/checkpoint models, previous accepted models,
  model-job payloads, regenerated preview scenes and Blender `.blend1` backups.
- Extensionless model payloads, old model textures and exact duplicate files
  from `artifacts/retirement-recovery/objects`. The archive's inventories and
  unique non-animation evidence remain; deleted models do not remain there.
- Retired browser distribution, old validation-project binaries, old packaged,
  staged and cooked outputs, and native map/catalog backup copies. A validation
  project's Content junction was unlinked before its directory was removed;
  the current Content target was preserved.
- Orphan Git LFS temporary transfer/filter files after Git/LFS processes stopped.
  The actual Git and LFS object stores were not pruned or rewritten.

`migration/model-storage-removal.json` records individual paths, hashes and
reasons. Private worktree inventories, preservation/disposition records, storage
measurements and deletion receipts are under `artifacts/storage-cleanup/`.
Earlier batch receipts are `artifacts/storage-*-removal.json`.

## Required data retained

Current authoring masters, frozen source-ledger inputs, current LODs, baked
textures and native imports serve different steps of the pipeline. Approved
recipes still use selected `releases/` directories and `revisions/canopy-v2`;
these current dependencies were checked before obsolete releases were removed.
All 44 supplied FBXs, equipped playable/NPC assets, current gameplay captures,
environmental animations and unique purchased kit sources remain. Licensed kit
sources account for approximately 24.8 GiB and remain private. Unreal compiler
intermediates and current binaries are separate from obsolete model iterations.

Preserved unique non-model files from retired worktrees are addressed by SHA-256
in the recovery object store. `worktree-preservation.json` maps original paths to
those hashes; `recovery-disposition.json` identifies subsequently deduplicated
objects and their retained current paths or Git-history disposition. Old tracked
code is already retained in immutable Git history.

## Verification and prevention

- 906 model validation records and 33 zone definitions pass after deletion.
- 783 hashes match for the four equipped model/weapon source pairs, 213 native
  animation sequences and 548 recorded gameplay images.
- `verify-animation-removal.py` checks retired paths, supplied FBX inventory,
  embedded character tracks, Blender save backups and extensionless recovery
  models. Directory traversal excludes junctions, symlinks, Git and dependencies.
- Four focused storage regression tests cover hidden model payloads, path
  containment, Git preservation and Windows junction exclusion.
- 649 repository tests, 124 Unreal-tool tests, all three typechecks and the
  migration audit pass. The existing four release blockers remain. The original
  Blender source models have no Actions; an unused scratch scene and its backup
  were removed.

Run `python tests/unrealStorageInventory.test.py`,
`python scripts/unreal/publish-animation-removal.py`,
`python scripts/unreal/verify-animation-removal.py`, then
`python scripts/unreal/publish-animation-coverage.py` when updating deletion
evidence. The provenance publisher preserves previous hashes across subsequent
cleanups instead of treating the current Git HEAD as the pre-replacement source.
An identical native rerun can rewrite the gameplay receipt's modification time.
Existing captures remain usable only when the previously published gameplay,
capture manifest, presentation manifest and every image hash still match; changed
evidence needs a new capture run. The coverage regression test checks this rule.

Keep Blender save-version backups disabled for automated generation. Remove
temporary model scenes and superseded outputs after acceptance; retain the
current source recipe and textual provenance. Do not create full recovery copies
of merged worktrees or licensed source libraries. Delete only reviewed, inactive
outputs, and never recursively delete a directory junction's target.

This cleanup does not change the existing siege-playtest, Steam, platform or
release-acceptance gates. The separately recorded animation gameplay/network
proof remains the evidence for the supplied-animation implementation.
