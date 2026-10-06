# AegisWar

[Fluid combat](docs/unreal-combat-fluidity.md) separates gameplay timing from
animation recovery: movement cancels stationary spells, melee continues while
moving, and baseline combat uses a 1-second shared cooldown. The guide covers
GM timing compatibility, cancellation/refunds, equipped locomotion, impact
feedback, combat-only staging and native/network verification. It also documents
full-cycle equipped captures and production impact-audio review exports.

Confirmed outgoing damage and effective healing now float above each receiving
player or NPC, following them independently of target selection. Isolated numbers
rise for one second; rapid procs accelerate the stream up to five times faster.
Each head has a bounded 160 x 112 UI-pixel region (scaled with the HUD), six visible
numbers at most, and a 32-number total limit. See the
[floating-number behavior and verification](docs/unreal-combat-fluidity.md#floating-damage-and-healing).

All visible nearby allied and enemy combat characters also have compact overhead
health bars by default, including damageable NPCs. Blue ally and red enemy bars
read current replicated health every frame, so damage from any source and healing
update them immediately. Bars sit below the floating numbers and follow the same
zone, range and visibility rules as combat targeting.

[Combat UI editing](docs/unreal-combat-ui.md) adds local friendly/enemy styling
to Edit UI: reticles, overhead bars, damage/critical/healing streams, target-panel
children, hit marker and combat messages. Slate body outlines and isolated mock
events preview edits; drag release and committed controls autosave separately
from action-bar layouts. `WarCombatUiSettings` owns validation/persistence,
`WarCombatUiDrawing` supplies shared Canvas/Slate layout, and
`SWarCombatUiEditor` provides runtime controls. See the guide for rendered and
owner/client verification commands and remaining acceptance evidence. The
combat UI network/live proof runners share `combat-ui-process.ts` to report
launch failures and confirm owned-process shutdown before releasing resources.

[Shared capital scenery](docs/unreal-shared-cities.md) gives campaign cities,
siege and the loading/menu presentation the same native scenery levels, meshes
and materials. With Unreal closed, `npm run unreal:city-sync` migrates or updates
bindings; `-- --check` verifies current sources. City changes invalidate affected
siege navigation/visual reviews instead of allowing an older city to launch.
Local lower-city admission now uses fresh crowd, convoy, gate and rendered
evidence for the current shared city. Full-siege and release acceptance remain separate.

The [reference citadel replacement](docs/unreal-aegis-citadel.md) adds a signed
architectural sheet and bidirectional route ledger, surveys actual native
geometry and stages Gothic scenery in private candidate packages. The version 2
siege progresses through the lower city, independent permanent side captures,
the locked central plaza and commander. Its encounter actor separates enrollment
from stat normalization; scenario and live campaign adapters share the rules.
The Node bridge owns readiness and durable settlement, validates the owning
native host and suspends legacy city combat during its lease. Critical inventory,
progression, quest and reward mutations flush a full private character document
before reporting success, then replay through the owning host's revision and
sequence checks. Interrupted native recovery, transient combat effects and
physical character returns still need complete acceptance evidence. Fresh geometry, full 18v18 scenario/live
capital, evacuation, recovery and rendered evidence are required before admission.
Participant and visitor evacuation documents have separate per-realm durable
budgets, so remote enrollment cannot consume the capital's evacuation capacity.
Use `npm run unreal:citadel-proof -- --blueprint <file> --map <candidate>
--city-revision <revision>` for exact-revision physical routes and gate sweeps.
Native import explicitly converts source triangle winding while retaining outward
normals. Route checks cover five lanes across each signed corridor width, and
architectural captures temporarily hide and restore local HUDs. The current
private captures are rejected for reference fidelity; older route diagnostics retain their failures,
they do not authorize publication or full-siege admission.
The older recipe 5 diagnostic retains 70 failures across 27,460 width samples. Exact
game-world overlap/sweep and direct-body diagnostics investigate those contacts
without changing corridor admission. Recipe 6 source binds the lower spawn's
surveyed ramp gradient and corrects gate, gallery, foundation and bounded approach
wall geometry. Private revision `8bb3168368e3` includes the gallery tangent
correction, a fresh read-only native survey and 139 connected native waypoints.
Its final schema 4 traversal passed, as recorded below. Live cooked contact
diagnostics use exact affine transforms and retain both failed movement and
destination contacts. Their candidate-face distance statistics never grant admission.
Versioned winning-plane diagnostics export full capsule/triangle intervals for
an independent Decimal projection audit; saved certificates never authorize movement.
Width proof schema 3 confines fresh typed live separation checks to route
placements, retaining raw gate admission and native floor/StepUp/movement vetoes.
Each sample records query accounting and independently audited full-capsule
certificates. The later schema 4 run supplies complete traversal for that revision.
Schema 4 requires the unchanged native character's full 64-channel collision
policy and continuous checks of capsule dimensions, scale, axis, gravity and
walking limits. Its first rehearsal passed 27,680 width samples but was stopped
after 24 walks to add the geometry guard; it remains diagnostic history.
The final guard accounts for Unreal's one-ULP slope rounding at spawn, then pins
the actual runtime and class-default limits exactly. All 100 native Foundation
tests passed. Fresh schema 4 run `1791300014775-28176` completed all 92 actual
walks and 27,680 width samples with zero route or physical failures; both
independent width auditors passed. These receipts bind only revision `8bb3168368e3`.
Recipe 7 `eb00703a2a63` adds articulated upper spires and supported dormers;
its 70 architecture controls, native staging and 139-waypoint navigation passed.
Fresh run `1791302524498-26280` passed all 92 walks, 27,680 width samples,
288 gate checks, 88 objective checks and 150 spawn checks, with eight game-camera
  captures. Both width auditors passed. Each receipt remains bound to its own geometry.
  Recipe 8 `d7936ad95609` adds the supported taller central standard; its asset
  build, 71 architecture controls, native staging and 139-waypoint navigation
  passed. Fresh complete native proof `1791305174868-5128` passed all 92 walks,
  27,680 width samples and all gate, objective and spawn checks, with eight views.
  Both independent width auditors passed. Visual and full siege approval remain open.
Recipe 9 `4069b99e5f8d` repairs bounded wing footings and strengthens the stepped
façade hierarchy while preserving objective, route, gate, spawn and room data.
Its asset build, 73 architecture controls, 68-package private staging and all
139 navigation waypoints passed. Native replay matched all 144 signed ground
samples exactly. Fresh native proof `1791308126754-24160` passed all 92 walks,
27,680 width samples and all gate, objective and spawn checks; both independent
width audits passed. Private campaign preparation and strict content validation
passed, with canonical packages preserved. The tooling suite passed 295 tests.
Crash recovery and cinematic visual review remain open for this revision.
Live campaign startup exposed streamed navigation being discarded in game.
The private campaign now owns both baked profiles and their bounds; a separate
native reload preserved all 5,765 character and 2,523 convoy tiles byte for byte,
and strict content validation passed. Runtime convoy and recovery checks remain
pending. Canonical campaign packages and the isolated scenario remain intact.
The local campaign journal now retries brief Windows sharing violations during
atomic replacement, retaining the durable checkpoint and flushed pending file.
Persistent or unrelated storage failures still pause authority without an ACK.
The preceding schema 3 run completed all 92 walks with zero physical failures.
Full siege acceptance, visual fidelity and cinematic lighting remain unapproved.
Seven source-bound lighting fixtures, shadowed architectural lights and native
clouds are being checked in isolated game-camera studies. New stair supports,
sculpted sentinels and a bounded native mountain carve require fresh evidence.
The carve checks every stored native corner, including unused attributes, and
binds original mesh policy to a separate read-only survey. Character return
requires a durable full current document; a restore acknowledgement cannot
release return custody. Native reconnect and crash verification remain pending.
Version 2 character recovery records supported effects and cooldowns with absolute
expiry times and their applied definitions. Elapsed downtime reduces remaining
duration; offline damage and healing ticks are skipped. Native regression tests
cover this codec, while actual process-crash acceptance remains separate.

Version 2 encounter navigation uses a bounded 8,192-node query filter; ordinary
players and recorded version 1 rounds retain the engine default. The new private
recipe records full-width spawn approaches and requires actual capsule checks
across every pad. Recipe 6 binds the retained ramp footprint to a fresh native
support survey without changing its anchor or clearance limits. Source checks
and the earlier 95-test native Foundation suite have passed. The older recipe 5 candidate
completed 92 center walks but still fails width and gate/spawn checks; fresh
complete traversal and cinematic approval remain pending. Diagnostic-only runs
cannot grant admission.


[GM rendering diagnostics](docs/unreal-gm-rendering.md) compare pointer-driven GM
controls, direct commands and an idle session using isolated preferences and
drafts. The persistent muted-color report remains under investigation until a
rendered before/after reproduction establishes its cause and verifies the fix.

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
equipped-frame reviewed; the current shared city still needs new siege route
acceptance before admission. Once accepted, start `npm run scenario:host`, launch the main game and enter your
character. Keep the host running while playing. If the Scenario panel reports a
connection failure, start the host and select **Connect / retry** in that panel.
Open **Escape → Scenario**, ready your party, queue and accept the
match. Your existing realm, class and equipment carry into a separate scenario
instance. The recorded lower-city rules retain 6v6; the replacement full siege
uses 18v18 after its fresh admission checks pass. **Leave scenario and return** restores your campaign character and
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
loads the same shared scenery levels into isolated presentation worlds, with
campaign lighting profiles and equipped character previews. After saving city
edits, close the Editor/game and run `npm run unreal:city-sync` before reopening.
Use `npm run unreal:frontend-refresh -- --check` to check presentation bindings.
This tracks saved native content. Run `npm run unreal:frontend-proof` for offscreen
login, selection and transition evidence; `-- --width 1280 --height 720` and
`-- --width 2560 --height 1080` exercise small and ultrawide layouts. Presentation
binding updates never rewrite source city maps or copy their materials.
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
