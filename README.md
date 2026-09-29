# AegisWar

[Portal travel and model candidates](docs/unreal-portal-models.md) covers the
capsule-entry fix, Interact retry, saved-world survey and reference-based Blender
authoring. Both model variants are installed at all 70 local campaign entrances;
reference-fidelity, sculpted collision and release acceptance remain unfinished.
The same guide documents the portal-visual installer and saved-world verifier;
the campaign must be closed in Unreal before its routing map can be updated.

The [Dutch Bastion revision](docs/unreal-dutch-bastion.md) rebuilds all five
districts with adjoining gabled brick houses, winding streets, enclosed courts,
fifteen public venues and deliberate gathering/combat spaces. Shared wall planes
replace isolated-house spacing. Guarded native revisions preserve services,
other zones and GM drafts. Revision `d105951f4aab` is active in the default game
and editor campaign, correcting overlapping floors and exterior corner trim.
Native review includes 157 city views, 42 supplemental corner views and 139 passed capsule routes.
Commands, measured performance costs and independent release gates are in the
revision notes.

The [imported population workflow](docs/unreal-imported-population.md) assigns 18
supplied character models to both capitals and four starter-zone PvE camps.
Its shared assignment ledger, private native animation recipes and guarded
placement survey preserve existing services. Native material, equipped-motion
and placement review are required before activating new appearances.

Native gameplay keeps the cursor visible: click allies or enemies to select,
**middle-click** selects the nearest visible enemy, and **Tab** cycles enemies.
Selected characters have bold blue (friendly) or red (enemy) corner reticles.
Camera dragging and clickable action bars remain available. See the
[control and targeting notes](docs/unreal-interface.md#configurable-action-bars-and-edit-ui).

The [lower-city siege playtest](docs/unreal-city-siege.md#lower-city-development-round)
adds a loopback server/two-client launcher, preparation and rematch UI, separate
lower-city victory rules, player squad orders and combat feedback. This work
includes native Summon Idol, fitted caster armor, authored encounter models and
crowd-aware objective navigation. The six-class roster and encounter assets are
admitted for local lower-city development after equipped-frame and traversal
review. Start `npm run scenario:host`, launch the main game and enter your
character. Keep the host running while playing. If the Scenario panel reports a
connection failure, start the host and select **Connect / retry** in that panel.
Open **Escape → Scenario**, ready your party, queue and accept the
match. Your existing realm, class and equipment carry into a separate 6v6
instance. **Leave scenario and return** restores your campaign character and
position. The shared coordinator owns instance allocation and recovery; see
[scenario queue setup](docs/unreal-scenario-queues.md).
The lower-city escort includes an authored battering ram and field catapult,
pushed by four Greenskin engineers. Claimed objectives raise Riftbound standards.
Equipment models, fitted push poses and ownership bindings are maintained through
the [siege equipment recipe and route proof](docs/unreal-city-siege.md#siege-equipment-and-ownership).
For the separate two-client fixture, run `npm run unreal:siege-playtest` and press
**Ready in both windows**.
`-- --automated` runs three normal-timed network rounds and rematches;
`-- --dry-run` inspects the launcher without starting Unreal. Full three-stage
siege, Steam and release acceptance remain separate and unapproved.

The GM City Builder includes [Remote world sync](docs/unreal-world-sync.md):
authenticated snapshot publishing and pulls with recovery, undo and revision
conflict checks. `npm run dev:check` diagnoses the connection. Local Auth is
configured, but the gateway address, owner login and hosted sync deployment are
still outstanding; this does not deploy an active game server.

The native [cinematic frontend](docs/unreal-character-entry.md#cinematic-frontend)
renders isolated capital snapshots and equipped character previews. Editor builds
and frontend proofs refresh stale private snapshots from every active capital
layer, including architecture and population. After saving city edits, close the
Editor/game and run `npm run unreal:frontend-refresh` before reopening; use
`-- --check` to check freshness without rebuilding. This tracks saved native
content, not unsaved edits or live server state. Run
`npm run unreal:frontend-proof` for offscreen login, selection and transition
evidence; `-- --width 1280 --height 720` and `-- --width 2560 --height 1080`
exercise small and ultrawide layouts. Source city maps are never rewritten.
Import the owner's login logo, button and window PNGs from `graphics-new` with
`scripts/unreal/import-frontend-artwork.py` through the same Python commandlet.
Private UI materials apply bronze coloring and transparent-margin cropping;
the supplied files remain unchanged.

The [Bastion siege runtime](docs/unreal-city-siege.md) adds three-stage rules,
population scaling, bot squads and local GM controls. Its isolated capital map
has stage blockades, objective props and navigation through all 17 required
anchors. The lower-city test uses a separate development admission flag; the
courtyard, commander and larger-population siege remain unapproved.

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

The native world builder (**G**) keeps movement and right-drag camera orbit active.
Choose a model to preview it in green, point at ground or a wall, then click to
place it. **Cancel placement** returns to selection. **Publish draft to local
game** persists the current layout and restores it on the next authorized local
GM launch; **Save draft / Load draft** remain separate recovery controls. Remote
authoring snapshots have their own sync controls; active shared-world deployment
remains unavailable. See [builder controls](docs/unreal-gm-workbench.md).
Run `npm run unreal:builder-proof` for the isolated rendered placement/publication
check and fresh-process restoration.

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
| `.mcp.json` | Project-local Blender character MCP configuration; uses the retained authoring server |

Unreal owns native live gameplay. The retained Node authority is a separate
reference/backend process; it has not been connected to native production play.
Each persistent datum must have one trusted owner at a future cutover. Do not
silently discard campaign, inventory, economy or runtime GM requirements.

The [model storage cleanup](docs/model-storage-cleanup-2026-09-24.md) removes
obsolete model iterations, recovery payloads and nine inactive checkouts. Current
authoring sources and imported runtime assets remain separate required inputs.
Run `python scripts/unreal/verify-animation-removal.py` to check retired paths,
Blender version backups, hidden recovery models and embedded character tracks.

## Setup and verification

Choose **Quit Game** below **Graphics** on the login screen to close the game
without signing in.

Choose **Local development login** on the entry screen for session character
testing; it does not require the optional developer-account companion. Once in
game, open **Escape > GM Tools > Set level** and choose
**1-45**. This updates stats and ability unlocks, resets current XP, and restores
health/mana for the session. See [GM controls](docs/unreal-gm-workbench.md).

`npm run unreal:stage` keeps installed world visual bindings synchronized with
gameplay exports after verifying unchanged source maps, models and native packages.
Changed or already stale bindings stop staging for review. Restart the play session
after staging; see [character-entry diagnostics](docs/unreal-character-entry.md).

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
- [Capital expansion authoring and verification](docs/unreal-capital-expansion.md)

Browser source and retired tests remain in the tagged Git history. Recovery
snapshots and unfinished asset-worktree candidates remain private under ignored
`artifacts/retirement-recovery/`; keep the original worktrees until their remaining
local material is reviewed. These same-disk snapshots do not protect against disk
loss and should be copied to encrypted off-device storage.

Scenario queue architecture, local-host setup and acceptance guidance: [In-game scenario queues](docs/unreal-scenario-queues.md).
