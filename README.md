# War-js

Browser-based MMO/RPG vertical slice built with **Three.js + React + Vite +
TypeScript** and Supabase-ready service interfaces. Local mode works without
backend configuration by using in-memory, localStorage, and IndexedDB services.

The runtime renders with generated or licensed `.glb` files when present and
falls back to procedural Three.js primitives when assets are missing.

## Quick Start

```bash
npm install
npm run dev
```

Dev server: `http://localhost:5173`

Useful checks:

```bash
npm run test
npm run campaign:generate
npm run typecheck
npm run world:validate
npm run models:doctor
npm run models:cleanup-proxies:check
npm run models:cleanup-roster
npm run models:roster -- --all --run-id full-roster-v2 --resume
npm run build
npm run models:validate
```

## Controls

| Key/Input | Action |
| --- | --- |
| `W` `A` `S` `D` | Move |
| `Space` | Jump |
| Right mouse drag | Turn camera and character facing |
| Left mouse drag | Orbit camera |
| Left + right mouse | Move forward |
| Mouse wheel | Zoom |
| Left click | Target enemy |
| Middle mouse press | Target nearest living enemy |
| Right click | Open/close interactive gates and doors; equip gear in inventory |
| `Tab` / `Shift` + `Tab` | Cycle forward / backward through nearby enemies |
| `NumLock` | Toggle autorun (any movement key stops it) |
| `1`-`0` | Class ability hotbar |
| `E` | Interact with quest givers, crafting stations, harvestable corpses, and nearby gates |
| `I` | Toggle inventory |
| `C` | Toggle character sheet |
| `L` | Toggle quest log |
| `M` | Open/close the unified campaign atlas at the current zone tier |
| `H` | Toggle in-game guide / wiki |
| HUD Campaign icon | Open/close the unified campaign atlas at the full campaign tier |
| Map window left click | Zoom from campaign to route, or route to zone detail |
| Map window right click | Zoom out from zone to route, or route to campaign |
| Map window wheel | Continuously zoom the current map tier |
| `Esc` | Close the active window; opens Settings when no window is open |
| `Enter` | Focus chat |
| `` ` `` | Toggle debug overlay |
| HUD window headers/title bars | Drag windows around the viewport |
| Settings → Gameplay / Key binds | Adjust camera gameplay options or rebind controls; bindings persist locally |
| `/gm build` | Enable GM world-edit mode when `VITE_GM_ENABLED=true` and your email is allowlisted |
| `/gm build off` | Leave GM world-edit mode |

## Architecture

```text
.github/workflows/
  deploy-pages.yml       GitHub Pages build/deploy
public/
  assets/
    maps/                Zone JSON data
    models/              Runtime GLBs, asset-index.json, QC sidecars
    textures/            Runtime textures
    hdri/                Environment maps
scripts/
  campaign/             Static Aegis/Riftbound graph and map generator
  blender-character-pipeline/
    data/asset-blueprints/ Manifest-first model blueprints
    data/body-families/  Free MPFB body/skeleton/pilot definitions
    data/full-roster-policy.json Playable/NPC/creature model-stage contract
    data/external-imports.json Quarantined external-source inventory
    data/asset-blueprint.schema.json
    data/npc-character-roster.json Generated NPC/enemy profile style data
    data/style-policy.md
    blender/             MPFB body, review, and retained static generators
    tools/               Atomic jobs, QC, registry, doctor, and validation
    mcp-server/          Local-only reviewed model MCP
src/
  config/                Environment flag parsing
  data/                  Campaign graph, class roster, item/crafting catalogs,
                         equipment visuals
  editor/                GM authorization helpers
  services/              Local/Supabase service abstraction
    local/               In-memory services and browser-compatible ID helpers
    supabase/            NotImplemented stubs that preserve the backend contract
  state/                 Zustand game store
  game/                  Three.js runtime, loader, player, combat, input,
                         data-driven ability runtime, resource regeneration
  game/abilities/        Class kits, ability schema, activation runtime,
                         projectile/impact VFX
  game/animation/        Shared procedural/GLB animation and VFX helpers
  game/WeaponAnimation.ts Procedural weapon gestures for equipped and fallback weapons
  world/                 Zone loading, terrain, props, NPCs, biome/path kits,
                         GM world-edit validation and runtime editor helpers
  world/editor/          Voxel terrain, prefab, transform, collider, and
                         walkable-surface authoring runtime
  wiki/                  React-agnostic guide/wiki content generation from
                         gameplay catalogs plus roadmap metadata
  ui/                    React screens and HUD overlay
```

Runtime terrain notes:

- `src/world/PathKit.ts` expands zone `paths` into connected visual road props, including endpoint connectors and junction caps for close path endpoints.
- Generated path props render through terrain-following ribbons in `src/world/Props.ts`; they do not create separate walkable shelves, so player grounding stays tied to the active terrain or authored walkable surfaces.
- `src/game/Camera.ts` resolves the third-person camera against prop colliders and terrain height so the viewport moves forward when terrain would occlude it.
- The Settings panel persists camera inversion, look sensitivity, zoom speed, and view distance in localStorage; view distance updates scene fog live without changing zone data.
- HUD windows share `src/ui/hud/useDraggableWindow.ts`, which keeps dragged panels inside the viewport while preserving each window's default CSS placement until moved.

Runtime animation notes:

- `src/game/Player.ts` resolves the manifest-backed playable character profile first so player bodies use authored locomotion and combat clips when available; external player overrides remain fallback assets.
- Modular armor entries with canonical skeleton metadata are emitted as
  `skinned: true` runtime overlays and carry their `coveredRegions` into the
  registry. The player rebinds those overlays to the loaded body skeleton so
  armor follows authored body animation and covered body surfaces are masked.
- `src/game/Enemy.ts` drives enemy `idle`/`walk`/`run` loops from AI movement and plays attack, cast, and hit reactions as one-shot clips.
- `src/game/animation/StaticModelAnimator.ts` layers procedural limb motion over imported or primitive characters that lack complete GLB animation clips.

## Quarantined External Sources

Raw external files no longer live under `public/`, so Vite cannot copy them
into production builds. Existing authoring sources are retained unchanged under
ignored `authoring/quarantine/external-sources/`. They are not eligible for
runtime character resolution until author, license, source URL, and source hash
records are complete. The eight active non-character legacy GLBs are isolated
by an explicit compatibility allowlist; Three.js fallbacks cover all removed or
unapproved character models.

## Capital Cities

`scripts/campaign/generate-static-campaign.mjs` is authoritative for Bastion of
Aegis and Riftspire Citadel. Both capitals use the original generated
dark-fantasy town family: varied timber-and-stone houses form dense medieval
blocks around open cobbled avenues, markets, crafting services, gates, and NPC
routes. A large generated stone-and-slate castle anchors each city center while
realm-specific monuments and a shared dark-fantasy fortress build pack preserve
each capital's identity. The capitals now use crenellated curtain walls,
corner towers, gatehouses surrounding interactive gates, wall stairs, ember
braziers, torn banners, and off-road siege barricades.

Generated and GM-placed town houses expose an `Enter House` interaction on
their exterior door. The runtime moves the player into a reusable footprint-
matched interior beyond the zone boundary, with solid room collision, a tighter
indoor follow-camera profile, warm lighting, residents, beds, tables, benches,
storage, shelving, rugs, and a working hearth. The interior exit returns the
player to the exact street position and facing they entered from; transient
interior coordinates are never persisted as the character's world location.
The same behavior is attached automatically to `Aegis House`, `Rift House`,
`Town House 1`, and `Town House 2` objects stamped through GM Build mode.

The retired imported Aegis city mesh and source pack are no longer registered
or used. Run `npm run models:all -- dark_fantasy_town`, then
`npm run models:registry` and `npm run campaign:generate` after changing the
architecture or layout so model QC, map hashes,
`src/data/campaign.generated.ts`, and `supabase/seed_campaign_static.sql` stay
aligned.

## GM Build Town Kit

The GM builder prefab list comes from
`src/world/editor/PrefabCatalog.ts`. The original dark-fantasy town family is
indexed as `town_*` prefabs with labels, preview models, footprints, default
colliders, camera-solid behavior, and asset-index static keys. Its two hero
houses, capital castle, and 17 modular pieces share weathered stone, framed plaster, warped oak,
staggered slate, forged iron, and leaded amber glass PBR materials. In the GM
Build panel, pick `Modular Town Kit` in the Kit selector, then choose the
individual house, wall, roof, door, window, beam, chimney, spire, or plank piece.
Existing grid snapping, angle snapping, wheel rotation, drag-chain placement,
transform controls, save, publish, and reload behavior continue through
`WorldEditorRuntime` because the town-kit prefabs are ordinary
`WorldPropObject` entries with `assetKey` and `model` metadata.

The pack is generated locally and does not depend on the retired external house
FBX. Rebuild it deterministically with:

```bash
npm run models:all -- dark_fantasy_town
npm run models:registry
```

`scripts/blender-character-pipeline/blender/generate_dark_fantasy_town.py`
contains the shared construction and material rules. Use the local MCP
`validate_model_asset` and `render_model_review` jobs after regeneration; the
review renderer scales its lights for building-sized subjects so dark surfaces
remain inspectable without changing their in-game palette.

## Fortress Build Pack

Pick `Fortress Build Pack` in the GM Build kit selector to place the reusable
dark-fantasy castle pieces: a crenellated curtain wall, corner tower, gatehouse,
animated fortress gate, wall stairs, ember brazier, torn banner, and siege
barricade. Gatehouses intentionally leave their center clear; pair one with the
animated `Fortress Gate` prefab to retain open/close interaction and closed-gate
collision. Curtain walls, gatehouses, and stairs include walkable surfaces for
future vertical city layouts.

The pack is generated locally alongside the town kit and is deployed through the
same manifest/runtime registry flow:

```bash
npm run models:all -- fortress_build_pack
npm run models:registry
npm run campaign:generate
```

## In-Game Wiki Guide

`src/wiki/wikiContent.ts` builds the reusable guide index from the same catalogs
used by gameplay: races/classes, ability kits, crafting professions/recipes,
cultivation seeds, quests, and referenced item names. Hand-authored metadata in
`src/wiki/wikiMetadata.ts` provides section order, overview text, race copy, and
planned roadmap pages.

`src/ui/hud/WikiPanel.tsx` renders that index as an in-game HUD guide with
section tabs, search, page navigation, detail rows, and data tables. The guide
opens from the HUD Guide icon or `H`; while open, movement, combat,
interaction, and chat shortcuts are blocked, and `Esc` closes the guide before
falling back to settings.

## Player QoL HUD

`src/ui/hud/ObjectiveTracker.tsx`, `src/ui/hud/Minimap.tsx`, and
`src/ui/hud/WorldMapPanel.tsx` improve orientation during play. The objective
tracker summarizes active and ready-to-turn-in quests with nearby enemy/NPC
distance context, while the minimap shows toggled marker categories for quests,
NPCs, crafting stations, resource nodes, enemies, exits, and off-range priority indicators. The
full map opens with `M` or the HUD Map icon and renders the active zone JSON
as terrain shading, roads, camps/objectives, landmarks, exits, and live markers.

`src/ui/hud/InventoryPanel.tsx` and `src/ui/hud/CraftingPanel.tsx` reduce menu
friction with inventory search, type/slot/material filters, sort controls,
capacity state, equipped-item comparison, recipe availability filters,
ingredient deficits, cultivation-ready counts, and preview-before-salvage.

`src/ui/hud/InteractionFeedback.tsx` surfaces local context prompts and ability
failure messages. Nearby quest givers, crafting stations, resource nodes,
harvestable corpses, objectives, gates, and targetable enemies advertise the expected action, and blocked
ability attempts explain cooldowns, resources, missing targets, range, defeated
player state, or UI focus.

`src/ui/hud/GuidedTasksPanel.tsx` adds optional first-session goals for core
player actions: movement, camera control, interaction, combat, corpse
harvesting, gear equip, guide use, and crafting. Progress is driven by local
gameplay events and persisted in localStorage, so it does not change service
contracts or require Supabase.

`src/ui/hud/CampaignMapPanel.tsx` combines the static Aegis Accord vs Riftbound
Host campaign graph with the detailed zone map. Its route model lives in
`src/ui/hud/campaignMapModel.ts`; campaign data lives in `src/data/campaign.ts`,
generated map hashes live in `src/data/campaign.generated.ts`, and static maps
live under `public/assets/maps/`. The unified atlas shows lane control,
active-zone objectives, realm influence, fortress pressure, city-siege
readiness, boss/lair branches, and static previews of every zone. Local mode
persists campaign control and influence in browser storage; Supabase activation
uses the `campaign_*` tables seeded from `supabase/seed_campaign_static.sql`.
`src/ui/hud/campaignMapViewport.ts` provides the shared logical scene sizing,
fit-to-pane scale, physical scroll surface, cursor-anchored wheel zoom, and
drag-pan behavior used by all three tiers. Terrain, backgrounds, connectors,
markers, labels, and effects stay inside that same scaled scene.
In-world `rvrObjectives` can also be claimed locally by standing inside their
capture radius for three seconds; battlefield objective captures grant 75 XP and
25 realm influence, with a 25 influence sweep bonus for controlling all three
BOs. A realm needs all three BOs and 100 local zone influence before the enemy
keep becomes capturable. The player realm is derived from race alignment, so
Aegis races claim for Aegis and Riftbound races claim for
Riftbound.

## Character Select Preview

`src/ui/screens/CharacterPreviewStage.tsx` renders the selected character beside
the character-select list with a compact Three.js scene. It creates a preview
`Player` with a zeroed position, so model loading, generated profile resolution,
idle animation playback, and compatible equipment overlays use the same runtime
path as the in-world player without mounting the full game loop.

Saved characters load their full `CharacterState` before previewing. While the
create form is open, the preview uses the unsaved race, class, and body variant
choices. Race-themed preview environments are procedural except for the
Riftbound foliage/stone accents, which are manifest-backed static props:
`preview_twisted_tree`, `preview_blight_shrub`, `preview_jagged_stone`, and
`preview_dreary_reeds`.

## Gathering And Crafting

Gathering and crafting are data-driven from `src/data/crafting.ts` and persisted
through `services.crafting`, with localStorage active by default and Supabase
stubs ready for Phase 2 backend wiring.

Supported v1 professions:

- **Scavenging**: humanoid enemy corpses can be harvested once before respawn.
- **Butchering**: beast enemy corpses use the same one-time corpse flow.
- **Salvaging**: armor and weapons can be broken into crafting materials.
- **Cultivation**: seeds grow in timed local plots and can use soil additives.
- **Apothecary**: reagents brew health, mana, and hybrid draughts.
- **Talisman Making**: fragments bind into equipable neck-slot talismans with
  rolled Strength bonuses.

Generated campaign zones now contain `craftingStations` and `resourceNodes`.
Stations open the crafting panel, while resource nodes are in-world gathering
points with stable IDs, minimap markers, local cooldowns, crafting XP, and loot
tables that feed the existing inventory/crafting recipes.

## Ability System

The combat hotbar is data-driven by `src/game/abilities/abilityData.ts`.
Every playable class has a ten-ability kit keyed to slots `1` through `0`.
Player-facing class names follow the renamed roster in `ability-system.md`,
with legacy WAR career names normalized as compatibility aliases for older
localStorage saves.

Ability definitions include:

- class family and class resource, such as Heat, Verdicts, Zeal, Rage,
  Grudge, Plan, Bloodlust, Hatred, Essence, and similar class-specific meters.
- mana cost, class-resource build/spend rules, cooldown, GCD intent, tags, and
  cancel-rule metadata.
- targeting shape: melee, projectile, beam, cone, area, self, dash, deployable,
  or pet.
- effect payloads for damage, healing, and tracked combat statuses.
- animation metadata with release/active notify windows and generic action ids.
- visual profile metadata for class/race palettes, thematic hotbar icons,
  class-family flair, cast windups, projectile silhouettes, trails, motion
  style, and target-contact impact effects.
- VFX socket intent for future authored assets.

`src/game/abilities/AbilityRuntime.ts` validates range and resources, starts
the matching player animation, spends/builds resources, schedules delayed
impact resolution from animation release windows and projectile travel time,
and hands off damage/healing/status application to `src/game/Combat.ts` so XP,
loot, respawn, enemy hit reactions, and quest kill credit stay on the existing
combat path.

`src/game/WeaponAnimation.ts` adds procedural weapon gestures on top of body
animations. Equipped main-hand/off-hand overlays and tagged fallback weapons
share the same controller: blades swing or thrust, staves and ranged weapons
point toward the attack direction, heavy weapons slam, and shields brace for
ward/block abilities. Ability visual motion metadata (`cleave`, `jab`, `shot`,
`slam`, `ward`, `ritual`, and similar) selects the gesture so weapon-implied
abilities read differently even before bespoke GLB clips exist.

`src/game/ResourceRegeneration.ts` applies the baseline player recovery loop.
All classes currently regenerate health and mana from empty to full in about
30 seconds, with the per-second rate scaled from each character's max health
and max mana.

`tests/abilityCatalog.test.ts` and `tests/abilityRuntime.test.ts` run under
Vitest and guard the ability catalog, legacy class aliases, resource rules,
targeting metadata, visual profiles, activation gating, resource spending,
cooldowns, animation calls, and VFX handoff.

`src/ui/hud/AbilityIcon.tsx` renders generated SVG icons from each ability's
visual profile, replacing text-glyph hotbar placeholders with class- and
school-themed frames, symbols, accents, and a shared palette used by the
hotbar and runtime VFX.

`src/game/abilities/abilityIconOverrides.ts` is the explicit art-direction
catalog for all 240 playable abilities. Each stable ability ID selects an
effect-oriented SVG motif such as an orb, meteor, shockwave, ward, summon,
snare, mark, bleed, or venom shape. Missing entries still use the safe generic
resolver, while `tests/abilityCatalog.test.ts` prevents playable abilities
from losing their explicit recipe.

`src/wiki/classGuides.ts` contains the role-aware PvE opener, single-target
loop, AoE sequence, resource rule, and utility priorities shown on every class
guide page. Rotations are practical catalog-based recommendations rather than
simulator-proven DPS rankings because the current combat slice has no encounter
simulation model.

`src/game/abilities/AbilityVfx.ts` provides runtime visuals for cast windups,
class-family flourishes, projectiles, beams, melee arcs, ground pulses, impact
bursts, and self auras. Projectile abilities now carry a shaped projectile,
trail, arcing/swaying travel motion, and delayed target-contact burst that
lines up with the scheduled impact window. Class families add their own
race-appropriate palettes, glyphs, orbit behavior, beam pulse rings, area
spokes, and impact fragments so careers share the same runtime system without
all looking like the same recolored spell.
Current generated character GLBs can keep exposing `attack_melee`,
`attack_ranged`, and `cast`; `src/game/Player.ts` maps the richer ability
action ids (`light_attack_a`, `heavy_attack`, `shoot_standing`, `cast_short`,
`cast_long`, `cast_heal`, `ultimate_cast`) onto those clips until more specific
combat animations are authored.

## Runtime Assets

`src/game/AssetLoader.ts` resolves model assets in this order:

1. `public/assets/models/asset-index.json` for manifest-backed characters,
   equipment, body overrides, and indexed props.
2. Direct `model` fields from zone JSON for legacy terrain/building/prop assets.
3. Procedural fallback primitives if a file is missing or invalid.

Indexed equipment can be present on disk but blocked from runtime with
`runtimeReady: false` and a `reviewStatus`. This is used for modules that have
valid manifest output but are not yet skinned/socketed well enough to mount in
gameplay.

Character entries must be approved and present on disk before the resolver will
return them. Body and equipment compatibility is checked by `bodyFamily`,
`bodyVariant`, `skeletonId`, and `bindPoseId`; equipment can expose `m`/`f`
variants under one logical item. Missing, draft, blocked, unapproved, or
incompatible models are skipped and use the existing Three.js fallback path.

The fallback counter is visible in the debug overlay. Missing assets must never
hard-fail the browser.

## Full Roster Model-Stage Pipeline

Character and creature generation is local-only with a currency budget of
zero. Blender 5.x plus MPFB 2.0.16 creates the six stable-topology humanoid
families; pinned CC0 MakeHuman packs supply fitted source clothing and anatomy.
Original project targets derive the Greenskin family. No paid provider, hosted
generator, remote model service, or CI generation path is allowed.

`scripts/blender-character-pipeline/data/full-roster-policy.json` and the
compiled roster contract define 48 resumable groups: 24 playable class pairs
(48 appearances and 432 nine-slot T1 modules), 12 race/body NPC foundations
covering 74 static NPC plus 32 humanoid-enemy combinations, and 12 rig-ready
creatures. Every humanoid uses `humanoid_game_v2`, both hand sockets, and the
shared review-only one-handed pair/two-handed weapon suite. Creatures declare a
body-plan skeleton plus root, ground-contact, attack-origin, and hit-center
markers. This phase produces LOD0 and model-stage evidence only.
The Battle Prelate and Warbrute pilot additionally runs the animation stage:
both body variants must embed the canonical nine-clip pack, and each equipped
variant receives deterministic locomotion/melee frame evidence. Animation
approval remains a separate human review gate.

Run the exact preflight and batch commands from the repository root:

```bash
npm run models:doctor -- --strict
npm run models:cleanup-roster                 # dry-run
npm run models:cleanup-roster -- --apply      # exact manifest targets only
npm run models:roster -- --smoke --run-id full-roster-smoke-v1 --resume
npm run models:roster -- --all --run-id full-roster-v2 --resume
npm run models:roster -- --kind playable --key battle_prelate --revision next
```

For a specifically authorized pilot exception, the direct promotion command
requires an explicit `--bypass-approval` flag, rechecks source hashes/QC, and
records the bypass in the revision and approved manifest metadata:

```bash
npm run models:promote-roster -- --run-id <id> --kind playable --key <key> --revision <n> --bypass-approval
```

The same explicitly authorized bypass can promote the NPC or creature pilot
outputs. NPC promotions register every generated live profile against its
equipped role model and preserve the nine embedded animation clips; creature
promotions register the generated static prop key. The command records the
bypass in each revision, approved manifest, and promotion transaction:

```bash
npm run models:promote-roster -- --run-id <id> --kind npc --key <body-foundation> --revision <n> --bypass-approval
npm run models:promote-roster -- --run-id <id> --kind creature --key <creature-key> --revision <n> --bypass-approval
```

The full command checks the strict doctor before creating revisions. A missing
MPFB installation, retained CC0 pack, source target, or matching source hash
creates a consolidated preflight-blocked report without partially starting the
batch. Once ready, groups run sequentially, failures are recorded as blocked,
and later groups continue. Revision seeds deterministically vary bounded fit,
wear, material, and silhouette details while preserving the class/species brief.
`ready_for_review` means the generated LOD0 bundle and its automated QC evidence
passed; it does not mean a reviewer approved the model. A clean resume of a
finished run reports all 48 groups as skipped and zero groups as blocked.

Start Vite and open the local authoring queue:

```bash
npm run dev
# open http://localhost:5173/?modelReview=roster
```

The Classes, NPCs, and Creatures tabs provide item/version navigation,
male/female class review, bare/equipped views, turntable and stress evidence,
all three humanoid weapon modes, QC status, and Approve/Disapprove/Regenerate.
Disapproval requires notes. Mutations require an ephemeral same-origin token;
artifacts are resolved only through selected manifest indexes and re-hashed
before streaming or approval.

Approval freezes the exact hash-bound model-stage bundle under
`authoring/approved/model-stage/` (GLBs use Git LFS), records lightweight audit
history, and removes only unselected revisions for that item in the same run.
It never changes `public/assets/models/asset-index.json`. `runtimeEligible`
remains false until later LOD and animation approval. The Battle Prelate and
Warbrute pilot is the first playable animation-stage slice; the later phase
will extend the same nine-clip contract to the remaining class pairs, class
plus role overlays for humanoid NPCs, and one unique pack per creature species.
Current stress poses and rendered animation frames are QA evidence and cannot
satisfy animation approval.

### Typed modular-character pilot

The model pipeline now classifies every wearable before choosing an operation:

- `rigid` equipment uses an explicit canonical socket and offset profile.
- `skinned` wearables use nearest-face weight transfer or Surface Deform, then
  normalized four-influence weights and reversible body-region masks.
- `loose` garments use an armature-first, pinned Cloth stack and remain a later
  tier until fitted wearables are stable.

The stable contracts live in
`scripts/blender-character-pipeline/pipeline-data/`: slot taxonomy, body
archetypes, semantic socket aliases, body masks, the nine-pose core pack, and
the runtime GLB export profile. The MCP server exposes these as resources and
also provides narrow stage tools (`assemble_base_character`, `fit_wearable`,
`apply_body_mask`, `attach_rigid_item`, `validate_pose_pack`,
`render_turntable`, and `export_asset`). `repair_fit_failure` and
`build_test_character` are reusable prompts. Filename similarity is never used
to choose a fit or attachment path.

Generate the local review fixtures and validate them without MPFB:

```bash
npm run models:generate:test-assets
npm run models:validate:character
```

This produces draft-only canonical GLBs under
`scripts/blender-character-pipeline/test-assets/`: a base skinned body, a
socketed rigid sabre, and a skinned chest wearable with transferred weights and
an under-chest body mask. They are test evidence, not runtime-approved assets;
promotion still requires the existing human review and hash gates. The fixture
validator performs local GLB 2.0 structure checks, canonical skeleton/socket
checks, animation presence checks, four-influence/QC checks, pose-pack metadata
checks, and rigid clearance checks. An external Khronos validator can be added
as a final deployment gate when its CLI is available.

Historical static creature GLBs, QC files, blueprints, compatibility entries,
and the hard-coded Battle Prelate development route have been removed. The 60
beast placements actually present in the canonical 32-map campaign source keep
their IDs, levels, and coordinates while being redistributed across the six
Aegis and six Riftbound species. Missing/unapproved assets continue through the
existing Three.js primitive fallback path.

## World Data

Zone JSON in `public/assets/maps/` drives terrain, props, NPCs, enemies,
colliders, walkable surfaces, paths, campaign objectives, resource nodes, and
biome kits.

The Aegis/Riftbound campaign maps are generated once from
`scripts/campaign/static-campaign-source.mjs` by `npm run campaign:generate`
and committed as static JSON. Each generated map has `staticMapVersion`,
`staticMapHash`, concrete prop transforms, `rvrObjectives`, `resourceNodes`,
crafting stations, and bidirectional `zoneTriggers`, so every player loads the
same scenery and portal graph. Portal `targetSpawn` positions are applied as
the character's entry point in the destination zone, then portal triggering is
held until the player clears the entry volume. Zone `spawnPoint` values are
kept as safe death/GM-return respawn positions outside enemy aggro, rather than
being overwritten by the character's last saved entry position.
Playable character routing is campaign-only: stale local saves or stale portal
targets for unknown map IDs normalize back onto
the Aegis/Riftbound campaign graph before loading. Missing future zone files
still load through the built-in fallback path; the runtime must never hard-fail
on absent content.

- `terrainModel` can load a visible GLB terrain and use it for height sampling.
- `props[].colliders` and `props[].walkableSurfaces` make multi-floor props navigable.
  Collider `minY` / `maxY` bounds are optional; when present they limit player
  blocking to that vertical band, which keeps upper castle walls from blocking
  lower floors.
- `props[].interaction` marks animated gate/door props; closed-only colliders
  reference the interaction id so `E` or right-click can visually open/close
  the gate and release the blocker.
- `props[].id` can provide a stable GM-editor id for static-object overrides;
  when omitted, the loader generates one from the expanded prop order.
- `paths` expand into visible, walkable path strips.
- `biomeKits` expand deterministic landscaping while avoiding path corridors.
- `rvrObjectives` define static battle objectives, faction keeps, city gates,
  and boss/lair targets used by the campaign service. Generated battlefield and
  fortress zones each have three BOs, one Aegis keep, and one Riftbound keep.
  Keeps are generated from the same editable prop pieces exposed in GM build
  mode: wall segments, towers, animated front gates, rear posterns, and inner
  keep doors.
  Capital cities use the same prop pipeline for dense hard-colliding house
  blocks, full street networks, outer city walls, portal-facing side gates, rear
  gates, realm-specific landmarks, and six-level walkable citadels so GMs can
  adjust those pieces in build mode. Riftspire uses Riftbound-only destructive
  prop kinds such as `rift_house`, `rift_wall_segment`, `rift_tower`,
  `rift_obelisk`, `rift_brazier`, and `rift_spike_cluster`.
- `enemies[].archetype` selects lightweight NPC combat behavior such as raider,
  guard, caster, beast, or captain. Archetypes drive chase/leash behavior,
  ranged stand-off spacing, cooldown abilities, and status effects.
- `npcs[].characterProfileKey` and `enemies[].characterProfileKey` select
  manifest-backed humanoid models. `enemies[].assetKey` selects indexed static
  enemy props for creatures and training targets.
- `resourceNodes` define gatherable world resources. Each node references a
  visible `props[].id` via `visualPropId`, has loot/XP/cooldown data, and is
  persisted through `CraftingState.resourceNodeCooldowns`.

## GM World Editor

GM build mode is an in-game authoring layer for sculpting and improving static
zones without replacing the generated campaign JSON baseline.

Enable it locally with:

```text
VITE_GM_ENABLED=true
VITE_GM_EMAILS=you@example.com
```

Then sign in as that email and submit `/gm` or `/gm menu` in chat to open the
GM tools menu. GM commands are intercepted locally and never sent to zone chat.
Unauthorized users receive a system message and cannot open the tools.

The GM tools menu currently includes:

- Campaign zone teleporting across the committed Aegis/Riftbound campaign
  zones from `CAMPAIGN_ZONES`.
- Go-to-character lookup by exact case-insensitive character name. The menu
  uses the online world presence first, then falls back to the saved character
  record and teleports to that stored zone/position.
- Current coordinate display and copy-to-clipboard.
- Return to the current zone spawn.
- Restore health, mana, and class resource, plus a separate ability-cooldown reset.
- Walking/flying speed multiplier slider.
- Flying mode toggle; while flying, use `Q` to descend and `E` to ascend.
- GM build mode toggle.

`/gm build`, `/gm build on`, `/gm build off`, `/gm off`, and `/gm exit` remain
available as direct chat shortcuts for the world editor.

The editor currently focuses on world geometry:

- Voxel terrain sculpting: add, subtract, smooth, flatten, roughen, erase, and
  material paint. Data is stored as sparse voxel chunks, while runtime rendering
  generates a smoothed terrain mesh rather than visible block art. In build
  mode, `Tab` cycles the top-center Add/Subtract/Erase/Scale mode strip, and
  material buttons switch directly into Add with a live translucent brush
  preview for the selected material. Paint can recolor existing voxel terrain
  and can seed a shallow material patch on static terrain.
- Prefab/object authoring: place reusable building, castle, wall, stair,
  bridge, dock, statue, fountain, tree, and rock primitives or matching GLB
  fallbacks. The Brush tool shows a green unplaced preview, places on left
  click, and chains additional pieces end-to-end while dragging without waiting
  for model loading. The preview includes the placement model/fallback plus a
  footprint guide for the chain spacing. Mouse wheel rotates around Y;
  `Shift` + wheel rotates X; `Alt` + wheel rotates Z.
  Selected props can be moved, rotated, scaled, and deleted with Three.js
  `TransformControls`; Select mode exposes a delete button and also accepts
  `Delete`/`Backspace`. Static zone props, including prebuilt castle pieces,
  are selectable too; moving or hiding one writes a draft override for that
  stable static object id rather than editing the source zone JSON directly.
- Static terrain editing: Select mode can target the loaded terrain mesh. Its
  transform is stored as a draft override and the runtime height sampler is
  refreshed when it moves, rotates, scales, or is hidden.
- Collision authoring: add standalone blocking colliders and walkable surfaces,
  plus default collider/walkable metadata for common authored prefabs. Stamped
  `castle_gate` and `castle_door` prefabs get animated GLB models, closed-only
  colliders, and interaction ids by default, matching generated campaign gates.
- Persistence: static zone JSON loads first, then the latest published world
  edit overlay. In GM mode, a draft overlay replaces the published overlay,
  autosaves to IndexedDB, and can be published as a named version. Use
  `Reset to Live` in the GM panel to discard the current draft and reload the
  latest published overlay; when no published overlay exists, it resets the
  draft to the static zone JSON baseline. Undo history is seeded from that
  live baseline and is not capped, so a GM editing session can undo from the
  current draft state back to Live.

Local world edits use IndexedDB (`war-js-world-edits`) because voxel chunks can
be too large for localStorage. `services.worldEdits` exposes the shared
local/Supabase-ready interface:

```ts
getPublished(zoneId)
getDraft(zoneId)
saveDraft(zoneId, patch)
publishDraft(zoneId, notes)
listVersions(zoneId)
restoreVersion(zoneId, versionId)
```

Run `npm run world:validate` to check static zone data for editor-compatible
models, colliders, walkable surfaces, paths, core map shape, campaign
objectives, static hashes, and bidirectional portals.

## Supabase Setup

Local mode is default. The Supabase service classes currently preserve the
backend contract as explicit `NotImplementedError` stubs. To route through
Supabase later:

1. Create a Supabase project.
2. Add the browser client dependency and a shared client helper:

   ```bash
   npm install @supabase/supabase-js
   ```

3. Copy `.env.example` to `.env`.
4. Set:

   ```text
   VITE_SUPABASE_URL=https://xxxx.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJ...
   ```

5. Apply `supabase/migrations/20260611120000_campaign_static_map.sql`.
6. Apply `supabase/seed_campaign_static.sql` after every campaign graph change.
7. Implement the stubs in `src/services/supabase/*`.

Suggested tables:

```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  created_at timestamptz default now()
);

create table characters (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  name text not null,
  class text not null,
  race text not null,
  level int default 1,
  xp int default 0,
  zone_id text not null,
  position jsonb default '{"x":0,"y":0,"z":0}',
  rotation_y real default 0,
  health int default 100,
  max_health int default 100,
  mana int default 100,
  max_mana int default 100,
  strength int default 10,
  gold int default 0,
  equipment jsonb default '{}'::jsonb,
  updated_at timestamptz default now()
);

create table inventory_items (
  id uuid primary key default gen_random_uuid(),
  character_id uuid references characters(id),
  slot int not null,
  item_key text not null,
  item_name text not null,
  qty int not null default 1,
  kind text,
  equip_slot text,
  icon text,
  affix jsonb default '{}'::jsonb,
  unique (character_id, slot)
);

create table chat_messages (
  id uuid primary key default gen_random_uuid(),
  channel text not null,
  user_id uuid,
  from_name text,
  body text not null,
  created_at timestamptz default now()
);

create table zone_players (
  zone_id text not null,
  user_id uuid not null,
  character_id uuid not null,
  name text not null,
  position jsonb not null,
  rotation_y real default 0,
  updated_at timestamptz default now(),
  primary key (zone_id, user_id)
);

create table world_edit_versions (
  version_id text primary key,
  zone_id text not null,
  status text not null check (status in ('draft', 'published')),
  parent_version_id text,
  notes text,
  author_user_id uuid,
  author_email text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  published_at timestamptz
);

create table world_edit_objects (
  version_id text references world_edit_versions(version_id) on delete cascade,
  object_id text not null,
  object jsonb not null,
  primary key (version_id, object_id)
);

create table world_edit_chunks (
  version_id text references world_edit_versions(version_id) on delete cascade,
  chunk_key text not null,
  chunk jsonb not null,
  primary key (version_id, chunk_key)
);

create table gm_user_roles (
  user_id uuid,
  email text,
  role text not null check (role in ('gm', 'admin')),
  created_at timestamptz default now()
);
```

The migration above includes the campaign tables:
`campaign_static_zones`, `campaign_edges`, `campaign_objectives`,
`campaign_zone_state`, and `campaign_objective_state`. The seed file is
generated from the same source as the committed map JSON and stores each
zone's `map_hash` for client-side mismatch warnings. A follow-up migration adds
`campaign_zone_influence` for per-zone Aegis/Riftbound keep-siege influence.

Character creation chooses starting `zone_id` in the service layer:
Aegis-aligned races start in `aegis_capital`, while Riftbound-aligned races
start in `riftspire_capital`.

Enable Row Level Security on all world-edit tables before exposing Supabase to
the browser. Published rows can be readable by players; draft, restore, and
publish writes should be limited to `gm`/`admin` users.

## Deployment

GitHub Pages is built by `.github/workflows/deploy-pages.yml`.

Expected URL:

```text
https://briantheLEDguy.github.io/War-js/
```

The workflow builds with `vite --base=/War-js/`; runtime asset paths must use
`import.meta.env.BASE_URL`.

## Scripts

| Command | What |
| --- | --- |
| `npm run dev` | Vite dev server |
| `npm run build` | TypeScript check plus production bundle |
| `npm run preview` | Preview production bundle |
| `npm run test` | Vitest unit tests for wiki/data consistency plus ability catalog and runtime behavior |
| `npm run test:watch` | Watch mode for the Vitest unit suite |
| `npm run typecheck` | TypeScript check only |
| `npm run world:validate` | Validate zone JSON for world-editor compatibility |
| `npm run models:list` | List model blueprints and generated status |
| `npm run models:doctor` | Verify Blender, MPFB, required packs, targets, and the zero-cost policy |
| `npm run models:validate` | Validate retained blueprints and runtime index |
| `npm run models:validate:strict` | Enforce approval, hashes, previews, PBR, rig, topology, and clip evidence |
| `npm run models:registry` | Compile the deterministic approved-only runtime registry |
| `npm run models:cleanup-proxies:check` | Confirm removed proxy assets cannot return |
| `npm run models:cleanup-roster` | Dry-run the exact manifest-driven historical roster cleanup; add `-- --apply` to execute |
| `npm run models:roster -- --all --run-id <id> --resume` | Run or resume all 48 model-stage generation groups after strict preflight |

## License

Source code: MIT when a license file is added.

Only commit assets that are original or licensed for this project.
