# AegisWar

Native Unreal Engine **5.8.2** fantasy RPG: Aegis Accord versus Riftbound Host.
The browser application is retired. Node/TypeScript remains for shared content,
asset tooling and campaign/account/persistence infrastructure still awaiting
native integration. Production Steam admission and release remain gated.

## Architecture

| Location | Responsibility |
|---|---|
| `unreal/AegisWar/` | Native C++ gameplay, Editor tools, configuration and build targets |
| `shared/` | Browser-independent catalogs, rules, protocols, geometry and guide data |
| `server/` | Retained trusted Node campaign authority, authentication and persistence |
| `supabase/` | Database migrations, RLS and campaign seed data |
| `scripts/unreal/` | Content export, asset audit, imports, build/proof tools and collaboration checks |
| `scripts/campaign/`, `scripts/blender-character-pipeline/` | World generation and asset authoring/validation |
| `public/assets/`, `authoring/` | Retained source maps, models, textures and provenance; the path does not imply a website |
| `migration/` | Native policies, frozen reference fixtures, retirement and content manifests |
| `tests/` | Retained shared/backend/database/tooling tests and native Python tooling checks |

Unreal owns native live gameplay. The retained Node authority is a separate
reference/backend process; it has not been connected to native production play.
Each persistent datum must have one trusted owner at a future cutover. Do not
silently discard campaign, inventory, economy or runtime GM requirements.

## Setup and verification

Install Node 22.19+ and run `npm ci`. Install exact Unreal 5.8.2 and its supported
C++ toolchain, then set `UNREAL_ENGINE_ROOT` if outside the standard Windows path.
Fetch full Git history including `browser-reference-before-retirement-20260922`;
historical source hashes are verified through Git without retaining a runnable
browser application in this checkout.

```powershell
npm run typecheck
npm run typecheck:server
npm run typecheck:unreal-tools
npm test
npm run world:validate
npm run models:validate
npm run builder:validate
npm run unreal:audit
npm run unreal:build -- --target Editor
npm run unreal:test-native
```

`unreal:release-check` must still fail until complete gameplay, model, platform,
Steam and operational acceptance is recorded. Passing tooling or native rule
tests does not certify visual or production readiness. The retired browser's
fixtures are immutable; the fixture commands now verify them. Native automation
tests the implementation against those references.

## Native content and collaboration

Native content is local/private, outside the public code repository. The private
companion is `briantheLEDguy/War-js-content`, pinned by
`migration/native-content.lock.json`. Its initial inventory is **not distributable**:
source/license review is pending, so fresh-machine setup is not yet complete.
Do not force-add Content, purchased kits or supplied animation sources here.

See [collaboration setup and blockers](docs/unreal-collaboration.md). Collaboration
is closed pending a licensed Windows VM, suitable guest graphics, verified content
and remote isolation tests. The host's existing **work Tailscale account is
forbidden** for this project. A separate project account belongs inside the guest
only. No collaborator receives host login, filesystem, desktop or LAN access.

## Project requirements and history

- [Migration requirements and acceptance](docs/unreal-migration.md)
- [Browser retirement and branch dispositions](docs/browser-retirement.md)
- [Original class and ability system](ability-system.md)
- [Native abilities](docs/unreal-abilities.md), [interface](docs/unreal-interface.md),
  [world buildout](docs/unreal-world-buildout.md), [runtime GM tools](docs/unreal-gm-workbench.md)
- [Supplied animation handling](docs/unreal-animation-import.md)
- [Purchased modular kit review](docs/unreal-modular-kits.md)

Browser source and retired tests remain in the tagged Git history. Recovery
snapshots and unfinished asset-worktree candidates remain private under ignored
`artifacts/retirement-recovery/`; keep the original worktrees until their remaining
local material is reviewed. These same-disk snapshots do not protect against disk
loss and should be copied to encrypted off-device storage.
