# Native campaign world

The combined-layer construction below is the original bootstrap. The main world
now uses per-zone Generated/Authored levels and asynchronous development travel;
see [current buildout architecture, evidence and remaining work](unreal-world-buildout.md).

The campaign builder assembles 32 zones and all 70 directed routes from the
original campaign graph. Its generated CampaignTravel layer attaches to the
existing main capital; the startup map remains unchanged. Capital detail is
applied directly to the main city, not a separate preview project.

## Architecture

- `scripts/unreal/world-portals.ts` validates reciprocal routes, bounds and source
  arrivals, then exports 30 terrain surfaces and their road surfaces. Aegis keeps
  its existing authored city; Riftspire uses its source crater/deck meshes.
  Nonoverlapping zone origins are a development layout, not campaign geography.
- `world_static.py` checks source registry approval and fingerprints before
  converting static GLB surfaces, node transforms and materials. It records
  unsupported assets instead of substituting another model. Skeletal meshes,
  animations and interactive props require their own native implementations.
- `world_build_assets.py` and `build-world-portals.py` import source surfaces,
  scenery, admitted NPC visuals and supported crafting stations into a unique
  `/Game/WorldRebuild/Campaign_<timestamp>/CampaignTravel` package. Fingerprints
  prevent mixing inputs from different source revisions.
- `attach-world.py` backs up the main map, attaches the completed candidate, and
  preserves unrelated sublevels. A subsequent attachment replaces only the
  previously recorded campaign layer. Generated assets and purchased dependencies
  remain local, in ignored Content paths.
- `AWarZonePortal` performs authority-side development traversal with reciprocal
  destination, range, cooldown, blocking-ground, slope and capsule clearance
  checks. Travel retains the pawn, PlayerState, inventory and progression, stops
  autorun and updates the current zone. It does not perform whole-server travel.
- `AWarZoneAnchor` supplies zone bounds, map positioning and zone-local respawn.
  Realm entry chooses its home capital when no current zone exists.
  Campaign respawn bypasses Unreal's cached original PlayerStart so death after
  portal travel uses the current zone. Maps without a matching anchor retain
  normal engine start selection.
- `populate-world.py` adds exact imported source profiles using their source
  roles. Ambient residents and guards use population actors; only quest givers
  may enter the quest-NPC catalog. The current three characters are two Sunmeadow
  residents and Cinderfen's supply officer. Guard AI and interactions remain
  unfinished; these placements do not imply quest or combat implementation.
- `world_resources.py` validates original gathering/visual identities, source
  approval and crater floor coordinates. `populate-world-resources.py` upgrades
  eight existing Riftspire crate actors to `AWarResourceNode`, preserving their
  transforms, materials and other mesh parts. It does not create duplicate props
  or replace missing outdoor gathering models. Native gathering retains source
  loot, profession XP, range/height checks and server-side cooldowns.
- `UWarPortalProof` traverses every route, alternating explicit requests with real
  trigger overlap, checks pawn/inventory/zone continuity, then checks death and
  respawn in the final zone. A three-item health-potion stack verifies nonempty
  inventory continuity. This is a local development test, not Steam proof.

## Build and verify

Close the editor after saving changes before rebuilding native modules. Close
headless gameplay runs before saving map changes too: Windows holds loaded map
packages open while a game is running.

```powershell
npm run unreal:world-plan
python scripts/unreal/world_static.py
npm run unreal:build -- --target Editor
$editor = 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$project = "$PWD/unreal/AegisWar/AegisWar.uproject"
& $editor $project -unattended -nop4 -nosplash -nullrhi -run=pythonscript "-script=$PWD/scripts/unreal/build-world-portals.py"
# Require a fresh candidate.json and WAR_CAMPAIGN_LAYER_BUILT, then attach:
& $editor $project -unattended -nop4 -nosplash -nullrhi -run=pythonscript "-script=$PWD/scripts/unreal/attach-world.py"
& $editor $project -unattended -nop4 -nosplash -nullrhi -run=pythonscript "-script=$PWD/scripts/unreal/populate-world.py"
& $editor $project -unattended -nop4 -nosplash -nullrhi -run=pythonscript "-script=$PWD/scripts/unreal/populate-world-resources.py"
& $editor $project -game -WarDevelopmentGM -WarPortalProof -nullrhi -unattended -nosound
npm run unreal:test-native
npm run test:unreal
npm run unreal:audit
npm run typecheck:unreal-tools
python tests/unrealWorldStatic.test.py
python tests/unrealCapitalDetail.test.py
python tests/unrealWorldResources.test.py
```

Python commandlets can exit successfully after a script exception: inspect logs
and require fresh receipts. `artifacts/unreal/world-portals/candidate.json` records
construction; `build.json` records main-map attachment. Gameplay must produce a
fresh successful `unreal/AegisWar/Saved/PortalProof/report.json` with 70 routes.
Save the gameplay log as `artifacts/unreal/world-portals/traversal-main.log` and
run `python scripts/unreal/verify-world.py` to record package fingerprints and
require every route in that log. This invalidates older evidence after map edits.
The current gameplay proof harvests all twenty installed capital/frontier resource nodes, rejects
immediate repeats and checks cooldown records before traversing the network.
The verification receipt requires all twenty resource identities too, plus
GM draft/undo/redo survival through streamed travel and respawn.
Use `render-world-portals.py` with `-AllowCommandletRendering -RenderOffscreen`
for saved-scene inspection; it uses transient zone-lighting previews and saves no map changes.

## Remaining work

This is an incomplete native world reconstruction. Pending scenery and gameplay
are listed explicitly in the build receipt. Many zones still need source models,
population, enemies, resources, objectives and authored portal effects. Animated
gates, lifts, skeletal ambient creatures and unavailable NPC visuals are omitted.
New scenery is not yet admitted into the runtime GM catalog; existing capital GM
capabilities remain intact. Materials approximate source PBR settings; continuous
alpha blending and final lighting/art review remain unfinished.

The initial combined layer loaded all zones together; the current partition
loads occupied/requested campaign zones independently. Server ownership, durable cross-zone handoffs,
reconnects, 18-player-per-realm capacity, Steam and three-platform acceptance are
still separate gates. Source conversion, a saved map, or local traversal must not
be treated as production or visual acceptance. The release check must remain
blocked and legacy browser primitive paths remain migration debt.

## Historical bootstrap verification

Before the separate-level buildout on 2026-09-22, the Editor target compiled and 28 native automation groups passed,
including the regression for Unreal's cached original start. The 94 migration
tool tests and six focused Python tests passed; audit and tooling typechecking
passed. The strict release check still rejects release.

The main layer contains 5,739 scenery placements, 36 crafting stations and three
source population actors. Saved-scene checks verify all 70 portal labels plus
NPC identity, skeletal meshes, body height, source facing and foot clearance.
Offscreen images were inspected; sparse scenery, dark inherited commandlet
lighting and editor-only placeholder nameplates are not final art acceptance.
Runtime population nameplates are initialized on BeginPlay.

Read `artifacts/unreal/world-portals/verification.json` for the latest successful
full traversal/respawn receipt and exact map hashes. Construction and rendering
alone do not establish gameplay acceptance. The pending inventory lists 3,793
scenery placements and 157 unavailable NPC/station placements; guard AI and
services remain additional unfinished behaviour for the visible population.

### Riftspire resource pass (2026-09-22)

Eight source gathering sites are now active in the main layer. The native live
proof harvested all eight, rejected immediate repeats and retained inventory
revision 9 through all 70 portal routes and zone-local respawn. The four new
resource-binding Python tests, 28 native groups and 94 tooling tests passed;
audit/typechecking passed and strict release returned exit 1. A second resource
placement run preserved the verified map hash and did not add duplicate actors.

The resource receipt tracks 268 remaining non-Aegis sites that lack supported
native source visuals. Aegis's existing capital gathering sites are preserved
separately. These missing visuals are not replaced with generic scenery.
