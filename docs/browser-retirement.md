# Browser retirement and recovery disposition

The browser application has been removed after shared dependency extraction.
`migration/browser-retirement.json` lists extracted and removed files. Source maps,
assets, authoring tools, database schema, backend authority and native code remain.
The Pages deployment workflow is removed. Disabling the previously published
GitHub Pages site through the repository API was rejected with HTTP 422
("Deactivating GitHub pages for this repository is not allowed"). Site takedown
therefore remains an owner/settings blocker; removal of the workflow alone does
not establish that the old public site is offline.

## Behavior preservation

The immutable browser reference is `browser-reference-before-retirement-20260922`
at `80d26c9445e3e2d7ea01f107e6ed0f2c82a93b00`. Historical source/test hashes and the
original complete export digest are in `migration/browser-reference.json`. The
retained export must match that gameplay-data digest. Source-provenance hashes
change with relocated files; IDs, map payloads, definitions and coordinates do not.
The inventory, salvage, progression and quest fixtures remain byte-for-byte
behavior references. Native automation exercises the implementation against them.
All 39 native acceptance contracts remain pending until actual acceptance exists.

## Branches and unfinished local work

`migration/branch-disposition.json` records every original branch tip and its
disposition. The six Unreal branch names shared the same 45 commits beyond main;
those commits are integrated once. All other feature-branch tips are ancestors of
the cleanup history. The pre-LFS backup has two separate commits containing
quarantined external binaries; retain it through a local recovery tag and do not
publish or merge those packages into the public tree.

The private snapshot in `artifacts/retirement-recovery/` contains a SHA-256 object
store, inventory for all ten worktrees, saved indexes and a per-file disposition.
Copies were verified against the source hash. Recovery tags preserve original
branch tips. These are local safeguards, not an off-device backup.

Across older worktrees, **1681 differing/unreviewed candidate files** remain in
private recovery and the original worktrees. They include paused armor/model
experiments, draft art and historical tests. They were not promoted over current
reviewed assets or described as integrated gameplay. Matching files are classified
separately. Worktrees stay in place because unrelated ignored local material may
still be present; branch-tip ancestry alone is not permission to delete it.

After verifying recovery tags and fast-forward integration into main, 31
unattached local branch names were removed. Eleven local branches remain,
including main, the cleanup branch and nine attached worktree branches. All ten
worktrees remain. No remote feature branches were deleted and no recovery tags
were published. The quarantined pre-LFS history exists only under its local
recovery tag; it was not merged.

## Verified checks

- Retained TypeScript/backend/database/tooling suite: 81 files, 586 tests passed.
- Native Windows Editor build succeeded; 43 foundation automation tests passed.
- Python import/layout/world tests and eight Blender conversion tests passed.
- Typechecks, 33-map world validation, 906-model validation and builder validation passed.
- Gameplay export remains equivalent to the browser reference; migration audit
  passes while the native release gate still rejects incomplete acceptance.
- Eight broad host Unreal firewall rules were backed up and disabled. This is
  limited hardening, not completed VM or host isolation acceptance.

## Collaboration blockers

- Windows guest license/media are unavailable; no VM or collaboration service is running.
- Hyper-V administration and encryption verification need an administrator session.
- Actual guest graphics, enforced network isolation and two-machine acceptance are pending.
- A Linux guest avoids Windows guest licensing, but the full Editor VM has no
  supported Hyper-V GPU route on this Windows 11 Pro/Radeon desktop. A server-only
  guest does not meet the owner's Editor isolation requirement.
- Native content distribution/source rights are unreviewed; the private repository
  currently publishes only its closed inventory and instructions.
- The host's existing work Tailscale account is forbidden. The new separate project
  account may be used only inside the guest. No collaborators have been invited.

See `docs/unreal-collaboration.md` for the deployment/acceptance runbook. These
blockers are not waived by passing code tests or creating a private repository.
