# Browser retirement and recovery disposition

The browser application has been removed after shared dependency extraction.
`migration/browser-retirement.json` lists extracted and removed files. Source maps,
assets, authoring tools, database schema, backend authority and native code remain.

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

Unattached redundant feature branches can be removed after their recovery tags
are verified. Branches attached to retained worktrees stay available until the
remaining material is reviewed. No remote feature branches or recovery tags are
deleted/published automatically.

## Collaboration blockers

- Windows guest license/media are unavailable; no VM or collaboration service is running.
- Hyper-V administration and encryption verification need an administrator session.
- Actual guest graphics, enforced network isolation and two-machine acceptance are pending.
- Native content distribution/source rights are unreviewed; the private repository
  currently publishes only its closed inventory and instructions.
- The host's existing work Tailscale account is forbidden. The new separate project
  account may be used only inside the guest. No collaborators have been invited.

See `docs/unreal-collaboration.md` for the deployment/acceptance runbook. These
blockers are not waived by passing code tests or creating a private repository.
