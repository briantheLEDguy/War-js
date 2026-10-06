# Shared city scenery

Campaign, the Aegis siege and the loading/menu presentation reference one
`UWarCityDefinition` per capital at `/Game/Cities/Shared/<zone>/City`. Each definition
contains the zone identity, origin, scenery levels and content revision. Scenery
levels retain their existing mesh/material references and authored placements.
Campaign services live in separate gameplay levels; siege objectives, encounters,
gates and navigation live in the siege overlay. There is no Riftspire siege.

The frontend streams these same levels into render-only preview worlds, with
the city's own exposure and the same native lighting subsystem as campaign. It does not build placement snapshots or
duplicate materials. Character previews retain their separate studio lighting.
Preview worlds have no campaign game instance, AI, navigation, audio or physics.

## Updating content

Save and close Unreal Editor and game windows, build the Editor module, then run
`npm run unreal:city-sync`. `npm run unreal:city-sync -- --check` validates the
published sources. `npm run unreal:frontend-refresh` updates camera bindings only.
The old siege isolation/refresh entry points delegate to shared-city migration.
New Dutch Bastion builds split scenery before recording review hashes and bind a
staged candidate definition for network testing. Activation publishes it through
the stable city definition and synchronizes both consumers. Historical receipts
stay unchanged; the current shared contract verifies migrated source packages.

`scripts/unreal/sync-shared-cities.py` preserves scenery packages and reparents
campaign gameplay into overlays. It verifies actor names, transforms, components,
collision and tags before saving. Models and materials are never copied. The
private receipt is `artifacts/unreal/shared-cities/current.json`; backups and
operation journals sit alongside it, outside packaged Content. An interrupted
run leaves `pending.json` and refuses a retry until its backups are reconciled.
Do not overwrite subsequently edited content when recovering a journal.

City revisions include scenery package bytes, visual dependencies and origin.
Scenario admission checks both current campaign routing and installed package
hashes. An old receipt cannot pass merely because its old files still exist.
Changing city geometry invalidates siege traversal and visual review. Synchronizing
content never grants those reviews, Steam admission or release acceptance.

GM identities and draft storage stay intact. Unpublished GM drafts remain
session edits; publish/save city changes and synchronize before reviewing a new
siege revision. Existing historical receipts describe their original content only.

## Verification

- Run `verify-shared-cities.py` in Unreal to inspect the actual saved campaign,
  siege and frontend definition references, and reject gameplay in scenery.
- Rebuild siege navigation, run `npm run unreal:siege-traversal-proof`, inspect
  matching views from `render-shared-city-review.py`, and run frontend/menu proofs.
- Run repository tests, all typechecks, migration audit and world/model validation,
  plus `npm run unreal:test-native`. Release checking remains independently blocked.
- Remove obsolete scenery/material copies only after native reference verification
  and a referencer scan. Preserve their historical evidence outside Content.

## Installed migration verification - September 29, 2026

Both capitals now share native references across consumers. Native inspection
counted 10,187 Aegis scenery actors and 7,602 Riftspire scenery actors. Cleanup
removed 684 obsolete siege-layer/material packages after checking references;
private backups and hashes remain under `artifacts/unreal/shared-cities`.

Repository tests, Unreal tooling tests, all three typechecks, world/model checks,
the migration audit and 71 native tests passed. The rendered frontend proof passed
for both capitals, transitions, reduced motion and four character profiles; its
Riftspire view uses the campaign lighting subsystem and rejects blank captures.
Two-client campaign streaming
passed, as did all 70 campaign routes, 20 resources, respawn, streaming recovery
and GM draft/undo history across city unloads. The release check remains blocked.

The siege overlay now stages its convoy clear of the current houses, aligns the
upper checkpoint with vehicle navigation, and excludes whole supply assemblies
from pedestrian paths. Convoy navigation covers the hull diagonal and its follower
reaches corners before turning; full terrain-aligned collision sweeps remain active.
Crowd destinations leave passing space and use the runtime bot detour recovery.

All twelve colliding characters passed seven routes, including sabotage and both
spawn crossings. Both vehicles travelled about 354 metres with four engineers;
unsupported movement, overlap recovery, ram strikes and replicated outer-gate
passage passed. The inner gate stayed closed. Four current client captures were
reviewed. `artifacts/unreal/shared-cities/siege-review.json` binds this local review
to the city revision, map hash and evidence hashes. Admission preserves its
pre-review map backup and records the saved map hash separately after review flags.
Full-siege, final art, Steam and release acceptance remain independent.

The current local admission also passed `unreal:scenario-menu-proof` for Aegis
and Riftbound: queue, offer, dedicated 6v6 entry, squad movement/orders and return
with campaign inventory and realm preserved. Evidence is under
`artifacts/unreal/scenario-menu/e3a3aa82-1b1d-48be-b11c-f59e588905c1`;
`artifacts/unreal/shared-cities/verification.json` links the final reports.
These menu captures are functional evidence: shader warm-up is visible, and an
Aegis hold-order frame has a close-camera obstruction. They do not grant final
presentation approval. The separate convoy captures support the scoped scenery review.
