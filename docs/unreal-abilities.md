# Native class abilities

The exported catalog now drives native combat instead of remaining guide-only.
All 24 class kits (240 definitions) are available to the action-bar UI. The 238
abilities with implemented source effects use the shared native executor. The
two source-unimplemented summons remain visibly unavailable: Deploy Gunlet and
Summon Idol. Icon of Wrath now places its authored ten-second relic. This does not establish Steam, three-platform or
production acceptance, or graphical approval for every character's animations.

## Playing and configuring

The untouched Basic Strike/potion bar becomes the selected class's ten-button
kit. Customized legacy bars are preserved; assignments subsequently save per
class. Escape > Abilities lists the kit and can assign each ability to the first
bar. Escape > UI Settings > Configure button assigns abilities, Basic Strike or
potions to any button. Three starter skills unlock at level 1; the remainder
unlock through level 8, following the exported progression table. Locked entries
show their level rather than disappearing. The default keys remain 1 through 0.
Tab selects a hostile; V enables clicking the action bar.

The HUD displays the class resource, current action and active statuses.
Tooltips explain mana, resource, range, cooldown and rejection reasons. The
existing authorized development-GM restore/reset commands also restore class
resources and reset class cooldowns. They do not bypass level requirements.

## Boundaries and implementation

- `WarAbilityCatalog` parses the exported kits/progression once per game instance.
  Duplicate identities/slots, incomplete kits and unsupported effect kinds fail
  the catalog closed. No client supplies amounts, costs or animation timing.
- `WarAbilityRuntime`, owned by PlayerState, replicates resource and cooldown
  state to its owner. Pawn replacement cancels pending actions while retaining
  cooldowns/resource. Activation validates class, unlock level, life, controls,
  mana/resource, range, realm, zone, sight, animation and safe movement path.
- `WarCombatStatus` is pawn-local and replicated. It handles strongest-effect
  guard/empower/haste/slow, a single shield pool, control, cleanse, damage modifiers
  and periodic burn/bleed. GAS remains responsible for player vitals and death;
  its pre-execution damage hook applies guard/shield before health clamps.
  Enemy damage uses the existing death, reward and persistent respawn service.
- Effects resolve at animation contact, with additional catalog projectile flight
  time. Targets are checked again at impact. Death, pawn replacement, zone changes
  and control interruptions cancel pending effects. Costs/cooldowns are committed
  at activation and are not refunded by interruption or a missed target.
- Movement abilities validate capsule clearance and walkable ground throughout
  their path, then sweep the capsule over time. Penance uses the supplied sliding attack with capsule-owned travel and authored
  contact timing. Full-body actions block normal input
  and locomotion; hips/legs remain part of the supplied animation.

## Supplied presentation recipes

Four equipped profiles now use explicit recipes for all forty abilities. Battle
Prelate uses two-handed motion, Templar and Warbrute use sword-and-shield motion,
and Ember Arcanist uses Spellcast. Hybrid magical abilities use Spellcast while
weapon attacks retain weapon choreography. Solar Edict uses the supplied
one-handed invocation. Penance uses the full slide; Reliquary Smash alternates
between supplied jump and high-spin attacks with identical gameplay timing.

Preparations, combinations, channel holds and recoveries distinguish abilities.
The server selects variants, owns release/contact events and replicates start
times. See the [animation replacement workflow](unreal-animation-import.md) and
`shared/game/animation/suppliedPresentationCatalog.json` for all source bindings.

Icon of Wrath retains its 14-second cooldown, 15-mana cost and five-metre radius.
For ten seconds, eligible living allies in range and line of sight heal for 10%
of actual hostile health damage they deal. Participant bots qualify; encounter
NPCs do not. Overlaps do not stack. Replacement, death, disconnect and zone exit
remove the caster's relic. Overheal and recursive healing are excluded.

## Verification

Run `npm run unreal:build -- --target Editor`, `npm run unreal:test-native`,
`npm run unreal:audit`, `npm run test:unreal`, and
`npm run typecheck:unreal-tools`. The native foundation suite includes
`ClassAbilityCatalog`, `ClassCombatStatus`, `SuppliedAnimationGameplay` and
`IconOfWrath`. Run `npm run unreal:animation-network-proof` for all 41 variants
and a mid-action late join.

Launch `UnrealEditor-Cmd.exe <absolute-project-path> -game -nullrhi -unattended
-nosound -WarAbilityProof -GameUserSettingsINI=<absolute-temporary-ini>` for the
opt-in development live regression. Use a fresh preferences file so the default
bar check does not interfere with customized user layouts. It checks
all ten default Prelate hotbar entries, level/foreign-class/zone rejection,
resource and mana accounting, duplicate activation, delayed effects and all
ten abilities against the saved capital dummies, then verifies periodic
damage refresh/expiry and interruption without a cooldown refund. Its receipt is
`unreal/AegisWar/Saved/AbilityProof/report.json`; process exit alone is not proof.
It grants progression/resources only inside that disposable test session.
The command-line proof is unavailable in Shipping and does not save a character.

Verified on 2026-09-22: Windows Editor build, all 43 native foundation groups,
97 tooling tests, tooling typecheck and the required migration audit completed.
The final live Prelate proof passed all nine usable abilities plus the rejection,
timing, periodic-damage and interruption checks. The migration audit still reports
four existing release blockers; these checks do not confer graphical or release
acceptance on all 24 characters.
The final six-dummy regression also passed in both capitals, including delayed
Basic Strike, duplicate/cooldown rejection, death, no rewards and respawn.


Verified combat variety on 2026-09-24: Windows Editor build, 47 native foundation
tests, all nine live usable Prelate abilities (including release timing, periodic
damage and interruption), five Python admission tests, 598 general tests and 112
Unreal tooling tests passed. All three typechecks, 33 world maps and 906 model
records passed. The migration audit retains four release blockers. This is historical evidence. The superseded animation payloads and reviews were
deleted during supplied-set replacement; current evidence lives under
`artifacts/unreal/animation-replacement/`.
