# Aegis/Riftbound world buildout

The approved scope is 32 existing zones and 70 directed portals in the main
AegisWar project. Implementation has begun with shared foundations and
Sunmeadow March/Cinderfen Outskirts. **No zone or batch is complete.**

## Saved world and ownership

The owner's FinalAppearance capital retains its startup map, architecture,
population, lighting, detail and existing GM baseline. The former combined
campaign was copied into a routing level and 32 pairs of Generated/Authored zone
levels. Routing retains all 32 anchors and 70 portals. The 16,369 original
campaign actors were compared before/after copying for identity, transforms,
tags, mesh/material assignments and collision. The original combined level and
pre-attachment main-map backup remain local.

Managed edits check package/source fingerprints, back up generated levels, and
refuse conflicts instead of overwriting owner edits. Regeneration does not write
an Authored level. `partition-capital.py` copies the complete saved capital into
its authored level, preserving private brush data, 9,150 actors and all compared
component state. Its unchanged 25-actor population level also streams with Bastion.
The original startup map path is retained as a lightweight persistent container.
The extraction receipt records backups and before/after package fingerprints.

GM history retains stable IDs and source fingerprints while actors unload.
Soft model/material references avoid retaining capital assets through the catalog;
level reload rebinds authored actors and reapplies the current draft. Created
objects return in their template's level. Missing or changed originals produce a
conflict without replacing the draft, undo/redo or markers. Broader zone-aware
GM construction/catalog support remains unfinished.

`artifacts/unreal/world-portals/zone-manifest.json` records identities, source
hashes, level references, dependencies, routes, counts, native mesh/material/
collision inventories, pending content and separate environment, gameplay,
traversal, visual, network and release states. `coverage.json` inspects the saved
world and lists NPCs, resources, missing enemies, mechanisms and objectives by
source identity. Inventories do not grant visual or gameplay acceptance.

The nine placed combat NPCs have exact [equipment bindings](unreal-npc-equipment.md),
including bone-attached spears, shields and sidearms and the scout's embedded bow.
Missing required equipment blocks native combat readiness and zone admission.
The catalog uses soft asset references, and generated attachments do not modify
the saved capital or zone packages. Unbuilt combatants remain explicit coverage gaps.

## Travel and asset admission

`UWarZoneStreamingSubsystem` loads the server's occupied/requested zones and
requests only each remote player's occupied/requested levels on that client.
Travel waits for server collision and the client's engine visibility
acknowledgement, then reruns reciprocal-route, range, cooldown, ground, slope and
capsule-clearance checks. Only the entering pawn moves. Walking out, death, pawn
changes, lost visual readiness or a 30-second deadline cancel pending travel.
Missing destination references fail without moving the player. GM travel and
respawn also wait for content. Unoccupied campaign levels, including the capital,
unload after the brief travel hold. In the editor, Unreal loads referenced sublevels
for world authoring; seeing the whole layout there does not establish runtime
residency. For focused editing, open a zone level from its manifest.

All loaded zones incur memory and scene-management costs even when out of view;
visible meshes, lights and shadows may add GPU cost. Runtime isolation therefore
matters. Actor/level residency checks do not measure FPS or production memory.

These are development-session level loads within one server. Durable online
handoffs, Steam ownership, admission queues, reconnect recovery, 18 players per
realm per contested zone and production GM roles remain closed.

Resource interaction resolves an exact `world-visuals.json` binding for purpose,
zone, node, source visual, mesh, ordered material slots and collision profile.
An imported folder name alone no longer admits a model. The catalog is tied to
the staged gameplay source revision and records source/native package hashes;
missing or changed bindings return a recoverable error. The initial catalog
preserves six working Aegis and eight Riftspire nodes and adds two Sunmeadow and
four Cinderfen herb patches. `migration/world-resource-sources.json` reviews exact
source replacements and model fingerprints; complete multi-material source
surfaces are retained. `record-world-visuals.py`
checks prior placement receipts and writes changes to a conflict file instead
of replacing existing bindings. These bindings are Development only. Skeletal
imports retain separate exact mesh/animation/source validation. General
scenery/GM admission and per-kit release/license review remain open.

## First batch

Sunmeadow and Cinderfen now use complete 4x4 sets of source terrain sectors:
32 ground surfaces, 19 road overlays and 9 water surfaces. Conversion retains
vertex colors and source alpha behavior. Road/water overlays do not support
collision. Footprints and locations remain unchanged. Native LODs, biome detail,
shoreline/interior walking, navigation and final visual review still need work.

Six exact source characters are placed with imported idle animations:

- Sunmeadow: farmer, herbalist, High Elf scout and Dwarf artisan.
- Cinderfen: Dark Elf supply officer and Greenskin peat worker.

The three added characters passed Blender roundtrip and native raw/compressed
animation checks for all nine source clips. The importer can retry compression
with full-precision rotations while retaining the 1 mm deformation tolerance.
Placement does not implement guard AI or trainer/service transactions. All six
pass saved-scene height, source-facing and foot-clearance checks. Inspected
aerial and character-height captures exposed dark inherited lighting, sparse
scenery and editor nameplate placeholders. The new lighting profiles address the
inherited environment; visual acceptance remains pending.

The six herb patches retain source locations, profession requirements, loot and
cooldowns. The live proof checks full inventory atomically, stale revisions,
successful gathering and repeated requests across all 20 installed sites.
Wood, ore, water and many other required gathering models remain missing.

## Zone lighting

`UWarZoneLightingSubsystem` applies one local-view environment from the current
player's zone. The 32 profiles in `WarZoneLightingProfiles.cpp` specify distinct
sun direction/color/intensity, fill, fog and exposure/grading: warm limestone
farmland, amber geothermal marsh, cool gorge, snowy pass, slate moor, volcanic
gate and separate lair themes. Bastion uses its preserved authored environment.
Transient lights do not replicate, change saved maps or follow other players on
the shared server. Dedicated servers do not create these cosmetic actors.
Authored local lamps remain part of their zone. Editor previews use the same
profiles explicitly; native automation verifies restoration and bounded actor
counts. `inspect-world-lighting.py` captures all 32 approaches and checks saved
hashes and restoration. Profiles/captures alone do not grant art acceptance.

Sunmeadow now has its three source Campaign Raiders using an exact imported
visual. Native development behavior includes server-owned chasing, ordinary
melee, leash reset, atomic XP/loot/quest attribution, death and safe respawn.
Enemy state outlives zone unloading. The source Hamstring special, navigation,
equipment/visual acceptance and network combat checks remain open. See
[native enemy implementation and checks](unreal-enemies.md).

Cinderfen's expedition remains assigned to Cinderfen. Its dispatch model,
native enemies and live kill attribution still need implementation. The Aegis
expedition stays in Brightfen for batch two. Sunmeadow receives no replacement
quest chain. Warden's Hollow and Cindermaw Pit remain unfinished and must
complete alongside the first pair before advancing.

## Remaining sequence and gates

`world_zones.py` fixes the approved order, including optional lairs in the first
six batches: Sunmeadow/Cinderfen; Brightfen/Ashen; Greybrook/Bleakroot;
Glassriver/Gorepine; Ironwood/Vilemere; Highvale/Obsidian; Crownworks;
Dawnline/Shatterline; Starfall/Voidgate; final capitals. Capital services and
adjoining approaches accompany early batches.

Each zone still needs its full grounded environment/navigation, materials and
vegetation, settlements/interiors, mechanisms, NPCs/encounters, resources,
atmosphere and atlas presentation. Lairs require bosses, supporting encounters,
rewards and return travel. Require live walking/combat/quest/resource/reward
tests, full-inventory/retry failures, repeat-build preservation, player-view art
review and measured frame, memory and travel performance before completion.

Broader native enemy AI, patrols, navigation, shared kill attribution, keep encounters,
capture/defense, caravans, siege, campaign progression, authoritative world
publication, wider GM catalog expansion and full performance
acceptance remain substantial work. The RPG pairs precede wider warfare.
Steam, Windows/Linux/macOS clients and Linux servers remain mandatory release
gates. No new assets were purchased and no release approval was granted.

## Reproduction and evidence

Close saved editor/game processes before changing maps or native modules. Run
all commandlets in the main AegisWar project. Python exceptions can accompany
a successful process exit; require a fresh success marker and receipt.

1. On an unpartitioned build, run `partition-world.py`, inspect its candidate
   and actor snapshots, then `attach-partition.py`. Run `partition-capital.py`
   to extract the preserved capital and its population. `attach-world.py` refuses to
   replace an attached partition with the old layer.
2. Export sectors with `python scripts/unreal/world_landscapes.py`, then run
   `apply-world-landscapes.py` in Unreal. Matching reruns do not edit maps;
   changed inputs/packages require reconciliation.
3. Convert/import exact profiles through `convert-model.py` and
   `npm run unreal:import -- --profile <key>`, then run `populate-world.py`.
4. Run `populate-world-resources.py`, `record-world-visuals.py`,
   `inspect-world-coverage.py`, `render-world-portals.py` and
   `inspect-world-lighting.py`. Rendering requires
   `-AllowCommandletRendering -RenderOffscreen`; lighting previews are transient.
5. Run the main map with `-game -WarDevelopmentGM -WarPortalProof -nullrhi`;
   save its log as `artifacts/unreal/world-portals/traversal-main.log`, then run
   `python scripts/unreal/verify-world.py`. It requires all 70 routes, deferred
   loading, failure/cancellation, all 20 resource identities and final respawn.
   It also saves a disposable GM edit before travel and checks actor state,
   unload, undo/redo and draft reload after respawn. Proof drafts use a unique directory
   under `Saved/WorldEditPortalProof`; the owner's normal draft is untouched.
6. `npm run unreal:zone-network-proof` starts a background dedicated server and
   two loopback clients. It checks per-client loading, other-player isolation,
   inventory/pawn retention, vacant-capital unload and actual-client residency
   with saved-package hashes. Clients report only their current zone's content,
   zero persistent static meshes and their own active lighting profile.
   This does not establish Steam or rendering performance acceptance.
7. Run `npm run unreal:test-native`, `npm run test:unreal`,
   `npm run typecheck:unreal-tools`, `npm run unreal:audit`, and focused Python
   tests `unrealWorldZones`, `unrealWorldStatic`, `unrealWorldLandscapes`,
   `unrealWorldResources`, `unrealModelImport` and `unrealPoseParity`.
   `npm run unreal:release-check` must still fail.

Native assets, backups and purchased dependencies remain private/ignored.
`build.json`, `zone-manifest.json`, `coverage.json`, `verification.json`,
`render-verification.json`, network reports and each profile's
`editor-import.json` describe distinct evidence; none substitutes for another.

## Verified development checkpoint, 2026-09-22

`continuation-receipt.json` records the current evidence and explicit incomplete
gates. Editor and Game builds passed, along with 33 native automation groups,
94 tooling tests, 33 focused Python tests, tooling typechecking and the Unreal
audit. Strict release checking returned exit 1 as required.

The final 70-route run retained inventory, gathered all 20 installed sites and
restored GM draft/undo/redo after actual capital unload, reload and respawn.
The two-client loopback proof recorded only Sunmeadow's two levels (2,593 actors)
on its client and Riftspire's two levels (7,473 actors) on the other, with zero
persistent static-mesh actors on either client. The vacant capital unloaded on
the server. These are scene-residency observations, not measured FPS gains.

A fresh process compared all 9,150 capital actors to the preserved source state,
confirmed the unchanged music setup, and checked extraction rerun idempotence.
All 32 lighting profiles were captured from grounded approach views without
changing saved maps or authored environment settings. Saved-scene checks cover
70 portal labels, six source NPCs and six frontier herb patches. Later zones
remain sparse and some shaded views need further tuning; visual acceptance and
all zone/batch completion remain pending.
