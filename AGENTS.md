# War-js — Codex Guide

This file is read by Codex (and similar AI coding assistants) to understand
the project layout, conventions, and commands before doing any work.

## Active Unreal migration requirements

The approved target is Unreal 5.8.2, online-only Steam play on Windows, Linux
and macOS, with 18 players per realm per contested zone. Preserve every working
local/shared gameplay and runtime GM capability; only offline play and browser
save import are retired. See `docs/unreal-migration.md` and
`migration/unreal-policy.json` for the stage gates.

New native code lives under `unreal/AegisWar/`; migration tooling lives under
`scripts/unreal/`. Use repository model sources/adaptations by default. The owner
also authorized already purchased Unreal modular kits for city environments,
outdoor zones, dungeons and the GM catalog, subject to per-kit license, compatibility and runtime review;
see `docs/unreal-modular-kits.md`. No new purchases are authorized, and raw
purchased assets must stay out of the public repository. Visible
primitive character, creature, equipment, prop, scenery and fallback models are
forbidden in the target. Retain collision/navigation/terrain/editor/effect
geometry. Replace dependencies before deleting legacy browser primitive paths,
and report those paths as unfinished until they are actually removed. Missing
required native models block packaging or return a recoverable loading error;
never spawn invisible combatants or substitute another species/training dummy.

For supplied character animations, read `docs/unreal-animation-import.md` and
reuse `scripts/unreal/animation-pipeline.py` recipes. The procedural animation
studies are paused. Keep character-specific rig units, grip corrections and live
role decisions separate; verify equipped motion and clearance before activating
clips on another character.

Run `npm run unreal:audit`, `npm run test:unreal` and
`npm run typecheck:unreal-tools`. `unreal:release-check` must fail until all native
gameplay, model, three-platform and Steam acceptance is verified. Do not treat
exported JSON, source-only C++ or an FBX conversion as native implementation or
visual approval. The browser application is retired; historical behavior evidence is retained in Git.

## Original Campaign Rules

**These rules override everything else. All code and content must conform to them.**

### Races & Classes
Use the player-facing class names from `ability-system.md`. Legacy class
names may appear only in compatibility aliases, historical changelog entries,
or source-reference notes.

| Realm       | Race       | Classes |
|-------------|------------|---------|
| Aegis Accord | Empire     | Ember Arcanist, Hex Inquisitor, Sunfire Templar, Battle Prelate |
| Aegis Accord | Dwarf      | Stoneguard, Doomseeker, Glyphbinder, Siegewright |
| Aegis Accord | High Elf   | Blade Savant, Pride Warden, Aether Sage, Veil Ranger |
| Riftbound Host | Chaos      | Dreadsworn, Warped Reaver, Void Magister, Ruin Oracle |
| Riftbound Host | Greenskin  | Warbrute, Fang Herder, Bog Hexer, Cleaver |
| Riftbound Host | Dark Elf   | Blood Dancer, Dread Guard, Dusk Weaver, Crimson Acolyte |

### Capital Cities
- **Aegis capital**: `aegis_capital` - Bastion of Aegis
- **Riftbound capital**: `riftspire_capital` - Riftspire Citadel
- Aegis-aligned characters (empire, dwarf, high_elf) default to `aegis_capital`
- Riftbound-aligned characters (chaos, greenskin, dark_elf) default to `riftspire_capital`

### Zone Names & IDs
Zone IDs use original lowercase, underscored names from
`scripts/campaign/static-campaign-source.mjs`, such as `dawnline_expanse`,
`shatterline_expanse`, `aegis_gate_fortress`, and `rift_gate_fortress`.

### District & NPC Names
New districts, NPC names, and titles must be original Aegis/Riftbound content.
Do not add protected IP names to new campaign-facing surfaces.
Class trainer titles use the player-facing class roster above.

### Mechanics
- The static campaign graph follows the attached Aegis/Riftbound sketch:
  side T1-T3 lanes feed into inner T4 zones, central T4 fronts push toward
  fortresses, and fortresses open city siege pressure.
- City siege readiness: a realm must control the enemy T4 front, enemy inner
  T4 zone, and enemy fortress.
- Boss/lair branches are optional side objectives and do not block travel.
- Every campaign arrow is represented by bidirectional `zoneTriggers`.

## Native repository conventions

- Native gameplay and Editor modules live under `unreal/AegisWar/`.
- Shared catalogs, trusted rules and serialization live under `shared/`; do not
  introduce React, Zustand, browser globals or runtime rendering dependencies.
- Node backend and Supabase schema remain critical retained infrastructure.
- `public/assets/` holds shared source assets, not a deployable browser app.
- Preserve historical fixtures and source hashes. Read archived browser evidence
  with `scripts/unreal/browser-reference.ts`; fetch the reference tag/full history.
- Preserve all outstanding native acceptance gates and runtime GM requirements.
- Work on a dedicated branch, preserve unrelated changes, add focused behavior
  tests, update README/changelog, and review the final diff for secrets and regressions.
- Run `npm test`, `npm run typecheck`, `npm run typecheck:server`,
  `npm run typecheck:unreal-tools`, `npm run unreal:audit`, `npm run world:validate`
  and `npm run models:validate` for relevant shared/native migration work.
- Native Content and licensed packages belong to the private companion repository
  only after distribution-rights review. Never force-add them to this public repo.
- Collaboration runs inside a dedicated VM. The host's existing work Tailscale
  installation/account is forbidden: do not read, switch, modify or reuse it.
  Use the separate project account in the guest only. Keep collaborator access
  closed until actual content, VM, networking and remote isolation checks pass.
