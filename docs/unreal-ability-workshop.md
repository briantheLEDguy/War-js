# GM Ability Workshop

The native authoring UI, conditional executor and personal GM deployment are
implemented. **The full shared workshop plan is not complete.** Shared
publication/deployment stay closed pending native admission and GM authorization.
This document does not grant asset, release or remote-access approval.

## Authoring workflow

Open **Escape > GM Tools > Ability Workshop** under the existing authorized local
development GM gate. Shared/Shipping sessions retain their existing GM denial.

- Class Abilities shows one row per assignment, with frozen Class/Ability columns,
  virtualized rows, seven presets, header filters, sorting and removable chips.
  All 24 classes are grouped by realm/race. Small viewports collapse the class
  browser into the Classes menu instead of shrinking the text with HUD scaling.
- Filters combine columns with AND and `|` alternatives with OR. Numeric filters
  support `=20`, `>=20`, `<20` and `10..30`. Named personal views save search,
  filters, selected classes, sorting, widths, column order/visibility and compact
  mode in the game's user settings.
- Expand abilities into effects and rules. F2/double-click edits a numeric
  component; aggregates open the inspector. Shift-click selects a rectangle.
  Clipboard paste, fill-down (Ctrl+D), Set/Add/Multiply and reset-to-base preview
  visible cells and validate the whole transaction before committing. Undo/redo
  retain 100 edits. Damage/Healing presets expose minimum and maximum separately.
  A diamond marks overrides; a dash means not applicable, distinct from zero.
- Ability Library includes unassigned and archived bases. The structured inspector
  supports create, duplicate, archive, targeting/effects/conditions, costs/timing,
  class assignment/unlock/display order and profile recipe bindings. Inspector
  changes remain uncommitted until Apply validates the shared base and overrides.
- Test Arena includes a **calculated event snapshot** panel for stats, resources,
  defenses, recipients, starting statuses, ownership, expiry and casting state.
  It shows predicate traces, unconditional/conditional amounts and stale-result
  status. This fixed-state estimate is not measured arena evidence. Additional
  effect scheduling, travel, immunities and different recipient states still
  require the actual executor.
- Review compares the session's active definitions with the draft, including
  effective values for every affected class assignment, stable effect/rule
  identity, reordering and conditional dependencies. Changes are paged with
  before/after columns. It explicitly identifies missing measured test evidence;
  this comparison is not confirmation of another environment's active version.

Committed changes autosave to `Saved/AbilityWorkshop/draft.json`. Recovery keeps
the common shared baseline and uncertain requests' original idempotency keys.
An exclusive writer lock and compare-before-replace avoid overwriting a different
local session's draft. Save shared draft requires the configured account gateway
and environment grant; after its first acknowledgement, edits autosave there too.
Connection failure retains local changes. Retry reconciles the original request.
History's Load latest compares base/current/yours; overlapping edits and conflicting
reorderings require explicit choices before merge.
Recovery preserves the chosen environment. Once a workspace has been saved
shared, its environment cannot be changed through the local selector.

`WarAbilityWorkshopDocument` provides native transactions, compilation and merge;
`SWarAbilityWorkshop*`, its widget and subsystem own UI, calculated previews,
local recovery and the authenticated draft-gateway client.

## Use edited abilities in your personal game

1. Launch your existing local development game with `-WarDevelopmentGM` (or the
   configured local GM setting), enter an admitted character, then open
   **Escape > GM Tools > Ability Workshop**.
2. Edit a class row or create an ability in Ability Library. Apply composer
   changes, assign the ability to your class with an unlock level, and choose
   a compatible approved presentation recipe for each admitted profile.
3. Open **Review & Publish / Version History**. Review the affected assignments
   and select **Validate personal deployment**, then **Deploy draft to this game**.
4. Wait for **Active in this game**. New casts now use that complete version.
   Assign a newly created ability to a hotbar slot separately through UI Settings.
5. Use **Deploy this version** beside a saved history entry to roll back, or
   **Restore shipped abilities** to restore the migration baseline for future casts.

Deployments require the existing authorized, authoritative local GM session and
are disabled in Shipping and network sessions. They do not require the account
gateway. Every changed assignment is checked against every configured admitted
character profile of its class; unchanged shipped assignments retain their
existing admission. Missing assets, incompatible bindings, broken references or
a different code/content compatibility identity block deployment.

`WarAbilityDeploymentJournal` saves immutable UUID version files and a journal in
`Saved/AbilityWorkshop/deployments/`. Its exclusive writer lock prevents another
game process from overwriting this session's deployments. `WarAbilityWorkshopDeployment`
stages the complete validated catalog, observes activation at the next simulation
tick, then atomically records the confirmed active version. Interrupted staging
is marked failed on restart; the last confirmed version remains selected.
The next authorized GM launch automatically validates and restores that version.
If compatibility or asset validation fails, the shipped catalog remains active
and the UI reports the failure; the saved version is retained for recovery.

Existing activations, periodic effects, resources and cooldown deadlines retain
their captured state. Removed assignments block future casts while their hotbar
slots remain visibly unavailable. Rolling back changes future casts only and
does not replace your editable draft. Deployment history records operations;
the status above it identifies the version currently active in this game.

## Contract and conditional rules

`shared/game/abilities/workshop/` owns the authoring document, stable class
assignments and effect IDs, numeric overrides, validation, grid queries, atomic
edit history, and pure conditional evaluator. Definitions retain existing IDs;
the baseline migrates 24 classes and 240 abilities without moving hotbar bindings.

Rules use ALL/ANY groups, optional predicate negation, and explicit caster,
selected-target, or effect-recipient subjects. They query an active effect from
an ability, a specific effect, any HoT/DoT, or current casting/channeling. Status
ownership is explicit: this caster, allied casters, or anyone. Expired/depleted
effects and dead/missing subjects do not qualify. Cooldown/recovery is not casting.
Specific-effect references include conditionally added effects. Renaming or
reordering keeps those references; removing the referenced bonus blocks validation.

Evaluation events are cast start, application, and periodic tick. All predicates
at one event read the same pre-effect state. Flat bonuses are summed before
percentage bonuses: `(base + flat) * (1 + percent)`, rounded and clamped to zero.
Periodic ticks start from their application-adjusted baseline; tick bonuses never
accumulate into the next tick. Bonus effects do not recursively invoke rules.
Tick rules cannot create another periodic scheduler. Limits are 16 rules, 16
predicates per rule, two group levels, and 32 base effects per ability.

The native equivalents are `WarAbilityConditions`, `WarAbilityExecution`, the
immutable activation held by `WarAbilityRuntime`, and provenance-bearing periodic
state in `WarCombatStatus`. Existing effects keep their source behavior until
their targeting is deliberately changed. Presentation recipes remain tied to
approved character profiles and equipment; new ability identity is independent
of a reused presentation recipe.

## Shared persistence

The development gateway accepts `ability.save`, `ability.publish`, `ability.test`
and `ability.deploy` through its existing operations envelope. Read collections
at `/abilities/<environment>/workspaces|versions|deployments|tests[/<uuid>]`.
Database-side capability checks precede idempotent receipt replay. Draft saves
check expected revisions; versions, receipts, and test records are immutable.
The gateway computes canonical document hashes. Client-submitted test results
are calculated estimates, never accepted as native evidence.

The local migration adds explicit viewer/editor/publisher grants scoped to an
environment, with owner access inherited from trusted membership. RLS is enabled;
anon/authenticated have no direct table or RPC grants. Only the isolated gateway
uses service credentials. This migration has not been deployed remotely.

The gateway rejects both `ability.publish` and `ability.deploy` while admission
is closed, including for owners. The SQL protocol tests do not authorize enabling
them. No privileged credentials belong in client code. See
[Supabase RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security).

Deployment servers register/poll through the loopback-only `/ability-server`
endpoint, bound to a run, server ID, and writer epoch. A version is staged on all
servers before activation. UI must distinguish preparing, activating, active,
and failed; an acknowledged SQL write is not evidence of native adoption.

## Verification and remaining implementation

```powershell
npx vitest run tests/abilityWorkshop.test.ts tests/abilityWorkshopConformance.test.ts tests/abilityWorkshopGrid.test.ts tests/abilityWorkshopDatabase.test.ts tests/developmentHttp.test.ts
npm run unreal:build -- --target Editor
npm run unreal:build -- --target Game
npm run unreal:test-native
npm run unreal:workshop-ui-proof -- --width 1280 --height 800
npm run unreal:workshop-ui-proof -- --width 1920 --height 1080
npm run unreal:workshop-combat-proof
npm run unreal:workshop-deployment-proof
```

The UI harness uses isolated drafts/settings, renders actual native widgets,
loads 5,000 assignments, exercises filtering/edit preview/undo/redo, previews
conditions and checks input release. The combat harness runs a loopback-only
server/client with approved existing Prelate assets. It verifies an eleventh
assignment, conditional timing, same-event self-trigger prevention, version
changes during casts/statuses, resource/cooldown preservation, rollback and
client catalog synchronization. It grants no client GM privilege. Receipts under
`artifacts/unreal/ability-workshop*` are not Steam or two-machine acceptance.
The personal deployment harness uses ordinary local GM authorization and the
same deployment APIs as the UI, casts a newly assigned conditional heal, deploys
during a cast, checks rollback and cooldown/resource preservation, then launches
a second process against its isolated save directory to check automatic restoration.
It does not change your personal draft or deployed version.

Also run `npm test`, all three typechecks, `test:unreal`, `unreal:audit`,
`world:validate` and `models:validate`. Native tests include `AbilityConditions`,
`AbilityConditionValidation`, `AbilityConditionConformance` and
`AbilityWorkshopDocument` and `AbilityDeploymentJournal`. Both runtimes consume the same 23 golden cases from
`tests/fixtures/ability-conditions.json`. Preserve all release
gates and do not open collaborator access to run these fixtures.

Remaining plan requirements:

- Complete native shared admission and server-verified GM capabilities, the
  gateway-to-native deployment bridge and revision-aware transfers/reconnects.
  Existing OAuth, VM/network isolation and content-distribution prerequisites in
  `development-environment.md` remain unresolved.
- Implement the interactive isolated online arena, repeatable scenario sequences
  and server-owned measurements for the exact tested revision. The combat harness
  and calculated panel are not that arena. Complete measured action/amount traces,
  lagged periodic scheduling coverage and multi-recipient scenario execution there.
- Finish remote test-evidence retrieval, per-server deployment/rollback and
  opening arbitrary shared workspaces. Current History supports local active/draft
  comparison, dependency review, metadata and conflict review.
- Complete shared presentation admission across the full character/equipment roster,
  broader cross-language validation fixtures and comprehensive multiplayer/UI coverage.
  Missing approved assets must block affected assignments; no fallback models are
  admitted. Existing casts/statuses retain captured definitions, but native staging
  is not yet connected to the closed deployment gateway.

Arbitrary scripts, node graphs, automatic balancing, analytics and new
pet/summon/deployable authoring remain deferred.

## Verification recorded on 2026-09-24

- `npm test`: 88 files, 637 tests passed, including 23 shared conditional fixtures.
- `typecheck`, `typecheck:server`, `typecheck:unreal-tools`: passed.
- Windows Unreal 5.8.2 Editor and Game targets: built successfully.
- `unreal:test-native -- --capture-animations`: **54 of 54 passed**. This includes
  condition semantics, reference validation, review/merge, durable deployment
  history, interrupted staging, exclusive ownership and corrupt-history recovery.
  The combined animation checks also passed. Final report:
  `artifacts/unreal/editor/test-1790257762132-29348`.
- `test:unreal`: 17 files, 112 tests passed. World validation passed 33 maps;
  model validation passed 906 records.
- `unreal:audit` completed with four blockers and `readyForRelease: false`.
  `unreal:release-check` failed as required. No release gate was relaxed.
- Rendered and inspected native grid, composer, analysis and review at both
  target sizes. The harness exercises 5,000 assignments, hidden-column numeric
  filters, atomic edits, undo/redo, stale scenarios and input release. These are
  focused UI checks, not exhaustive keyboard, accessibility or collaboration tests.
  Screenshots/receipts:
  `artifacts/unreal/ability-workshop/1280x800-5d9478a0-4b32-40a9-ac82-f2fc9893a09e`
  and `artifacts/unreal/ability-workshop/1920x1080-a1ba0372-fd74-4a54-906d-6041b7139956`.
- The authoritative loopback server/client combat proof passed:
  `artifacts/unreal/ability-workshop-combat/fa613083-075e-48e7-9da0-c697db8f862a/report.json`.
  This covers cast/application/tick snapshots, publication boundaries, rollback,
  cooldown/resource retention and client catalog delivery. It is not shared
  admission, Steam, two-machine or three-platform acceptance.
- Personal GM deployment and a fresh-process restart passed:
  `artifacts/unreal/ability-deployment/ad1e9aa6-302d-45b9-a52b-d4a759e28e61`.
  This uses the ordinary deployment APIs to create an eleventh class ability,
  cast conditional heals, deploy during a cast, preserve mana/cooldowns, roll
  back, restore shipped definitions, reject a removed assignment, and restore
  the final confirmed version in a second process. Personal save files remain
  isolated from the user's real draft and deployment journal.
- Scoped whitespace/credential review found no issues. Existing concurrent
  animation, siege, asset and development-environment changes were preserved.

Command logs are retained in `artifacts/ability-workshop/`. The database migration
was tested locally and has not been applied to a hosted environment by this task.
