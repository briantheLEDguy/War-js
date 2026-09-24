# AegisWar

The [Bastion siege runtime](docs/unreal-city-siege.md) adds three-stage rules,
population scaling, bot squads and local GM controls. Its isolated capital map
has stage blockades, objective props and navigation through all 17 required
anchors. Complete equipped rosters and native multiplayer playtest evidence
remain outstanding; it is not yet a verified playable siege.

Native Unreal Engine **5.8.2** fantasy RPG: Aegis Accord versus Riftbound Host.
The browser application is retired. Node/TypeScript remains for shared content,
asset tooling and campaign/account/persistence infrastructure still awaiting
native integration. Production Steam admission and release remain gated.

The native [GM Ability Workshop](docs/unreal-ability-workshop.md) adds a class
spreadsheet, shared-ability composer, conditional effects, numeric overrides,
local recovery and shared-draft persistence contracts. The native executor
captures immutable cast/periodic definitions and synchronizes catalog changes.
The workshop also includes calculated condition scenarios, affected-class
before/after review, and common TypeScript/Unreal conformance fixtures.
In your local GM development session, **Review & Publish > Deploy draft to this
game** activates edited abilities for new casts. Saved versions support rollback
and automatic restoration on the next GM launch. The journal lives alongside
draft recovery in `Saved/AbilityWorkshop/deployments/`.
The full workshop plan is **not yet complete**: the interactive online arena,
native shared admission/GM authority and gateway-to-server deployment bridge
remain outstanding. Shared publication and deployment stay closed.

The active [free development environment](docs/development-environment.md) adds
identity and persistence foundations. **It is not yet a usable shared server:**
OAuth setup, native saves/admission/shared GM, Linux server deployment, content
onboarding and two-machine acceptance remain outstanding. The VM is provisioned;
resume NetBird setup from the [checkpoint](docs/development-setup-checkpoint-2026-09-23.md). The
[dated strategy](docs/architecture/mmo-hosting-2026-09-23.md) preserves paid options.

The supplied-animation pipeline covers 44 clips and explicit presentations for
forty abilities across Battle Prelate, Sunfire Templar, Warbrute and Ember Arcanist.
It includes a native blended state machine, replicated action timing, equipped
casting transitions and Icon of Wrath. See the
[animation workflow](docs/unreal-animation-import.md) for generation, gameplay
proofs, deletion receipts and visual/release acceptance gates.
The [Windows verification record](docs/unreal-animation-verification-2026-09-24.md)
links the passing gameplay, multiplayer, capture and removal evidence.

## Architecture

| Location | Responsibility |
|---|---|
| `unreal/AegisWar/` | Native C++ gameplay, Editor tools, configuration and build targets |
| `shared/` | Browser-independent catalogs, rules, protocols, geometry and guide data |
| `shared/game/abilities/workshop/` | Ability workspaces, stable assignments/effect IDs, conditional rules, validation and spreadsheet transactions |
| `server/` | Retained trusted Node campaign authority, authentication and persistence |
| `server/development/` | Development PKCE companion, account gateway and owner administration |
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

Choose **Local development login** on the entry screen for session character
testing; it does not require the optional developer-account companion. Once in
game, open **Escape > GM Tools > Set level** and choose
**1-45**. This updates stats and ability unlocks, resets current XP, and restores
health/mana for the session. See [GM controls](docs/unreal-gm-workbench.md).

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
npm run test:development
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
