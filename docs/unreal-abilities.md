# Native class abilities

The exported catalog now drives native combat instead of remaining guide-only.
All 24 class kits (240 definitions) are available to the action-bar UI. The 237
abilities with implemented source effects use the shared native executor. The
three source-unimplemented summons remain visibly unavailable: Icon of Wrath,
Deploy Gunlet and Summon Idol. This does not establish Steam, three-platform or
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
  their path, then sweep the capsule over time. Penance approaches at running
  speed before starting its planted swing. Full-body actions block normal input
  and locomotion; hips/legs remain part of the supplied animation.

## Battle Prelate motion decisions

The equipped mesh and imported clips are unchanged. The recipe is explicitly
scoped to `civic_battle_prelate_m`; its grip/motion/contact decisions are not
copied to unreviewed character variants. The supplied 1.8-second
`Great Sword Slash (1)` is the verified `attack_melee` role. Side-view review
frames 42–45 at 30 Hz put forward contact around 1.44 seconds (80%). Basic Strike
and class weapon effects use that contact, not the old procedural contact time.

| Ability | Motion |
| --- | --- |
| Litany of Strikes | Full supplied hammer slash |
| Sanctified Blow | Full supplied hammer slash; damage and heal at contact |
| Martyr's Ward | Full hammer-led invocation; shield at forward release |
| Penance Step | Swept running approach, then full hammer slash |
| Hymn of Resolve | Full hammer-led invocation; empower at forward release |
| Reliquary Smash | Full hammer slash; area impact at contact |
| Judgment of Ash | Hammer-led release using the full slash |
| Redemption Surge | Full hammer-led invocation; heal at forward release |
| Icon of Wrath | Hammer-led role reserved; unavailable summon cannot activate |
| Last Homily | Full hammer slash; area damage and heal at contact |

Holy invocations reuse the verified full hammer motion so every usable ability
has a visible action, rather than playing ordinary idle as a cast. The supplied
set has no dedicated prayer/casting gesture. No unverified jump, slide, spin or long
combination clip is activated. No upper-body-only overlay or manual limb posing
is introduced. Future class-specific motions should extend the mapping only
after the [import workflow](unreal-animation-import.md) verifies their equipped
grip, clearance, motion ownership and contact timing. Other classes currently
use their own admitted cast/melee/ranged roles, not the Prelate's rig.

## Verification

Run `npm run unreal:build -- --target Editor`, `npm run unreal:test-native`,
`npm run unreal:audit`, `npm run test:unreal`, and
`npm run typecheck:unreal-tools`. The native foundation suite includes
`ClassAbilityCatalog` and `ClassCombatStatus`.

Launch `UnrealEditor-Cmd.exe <absolute-project-path> -game -nullrhi -unattended
-nosound -WarAbilityProof -GameUserSettingsINI=<absolute-temporary-ini>` for the
opt-in development live regression. Use a fresh preferences file so the default
bar check does not interfere with customized user layouts. It checks
all ten default Prelate hotbar entries, level/foreign-class/zone rejection,
resource and mana accounting, duplicate activation, delayed effects and all
nine usable abilities against the saved capital dummies, then verifies periodic
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
