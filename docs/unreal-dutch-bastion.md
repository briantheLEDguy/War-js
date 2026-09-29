# Dutch Bastion city revision

Bastion of Aegis is the only revised capital. The active private revision contains
1,058 fitted houses in 42 closed blocks, 40 street/access links, and fifteen
furnished public venues. Revision `d105951f4aab` passed native architecture review
and is active in the default game and editor campaign map.
Riftspire, PvE camps, scenario maps and their gameplay remain outside this revision.
Reload the default campaign to see the correction; an already open editor or game
session retains its previously loaded map until reopened.

## Authoring and preservation

### Floor and corner overlap correction

The first activated revision's visual review missed coincident foundation/floor
faces, slab edges on exterior wall planes and projecting trim crossing angled
party walls. Walking routes alone did not detect these rendering defects.
The correction ends foundations beneath the timber slab, recesses slab edges
12 cm into masonry, and clips finished triangles to disjoint façade envelopes.
Shared structural wall coordinates stay unchanged. Triangle clipping preserves
texture coordinates and handles vertical faces and concave parcels.

The retained source road actor is replaced only in the copied revision: its
original triangles and material remain outside the rebuilt paving area and on
the six canal bridge decks, which depend on those triangles for collision. This
removes old road triangles intersecting the Vigil Cup floor without altering
terrain, bridges, the citadel or original source packages.

`audit-dutch-overlaps.py` checks all exported house vertices, face centres and
3,135 floor plates against their owned boundaries. Native configuration rejects
missing or stale overlap evidence. Visual proof now includes downward floor
views for all fifteen venues and a corner close-up in every block. Follow-up
activation verifies the previous revision, its dependencies and saved GM draft.
The native ground survey waits for mesh compilation and fails on discrepancies;
activation also requires every configured ground sample to pass. A preliminary
bridge-removal regression was caught by native walking and never activated.

`scripts/campaign/dutch-bastion-layout.json` defines distinct district streets,
protected services, named gathering spaces and the retained canal/bridge anchors.
`plan-dutch-city.py` derives enclosed blocks from those corridors, partitions each
street-facing ring into shared-boundary lots, and records intentional court
passages. Coordinate-based block identities and exact wall planes determine
frontage; roof overhangs and mesh bounds never determine house spacing.

The numerical audit rejects missing frontage, overlapping lots, broken corners,
one-centimetre seams, disconnected routes and inaccessible venue assignments.
Court passages retain their width at the rear wall as well as the street;
the audit checks two metres of clearance along the actual passage wall planes.
Near-collinear sites use explicit half-plane clipping when a Voronoi result would
overlap. Small residual regions are recorded as named paving or gathering spaces.
There are five larger district spaces for fighting, market activity and ambiance;
the existing Grand Court and citadel approaches remain open.

`dutch_city_ground.py` builds continuous raised paving above retained terrain,
with bounded grades. `dutch_polygon_architecture.py` produces fitted stone
basements, horizontal brick courses, tall windows, stepped/bell/triangular gables,
steep clipped roofs and chimneys. Adjacent houses share their boundary coordinates.
Public rooms have level floors and grounded thresholds; upper floors are exterior
architecture. Each district has an inn, cafe and shop. These rooms are atmospheric
venues and do not invent merchant, quest or lodging services.

`prepare-dutch-city-placement.py` records 224 owned old-house removals, one owned
road replacement, 254 scenery relocations and 85 grounding adjustments. Thirty-one existing service/interior
sites retain their identities. The source city, terrain, bridges and GM draft stay
unchanged. The owner's added barrel is reproduced in the revision. Purchased
furniture, materials, collision and three native LODs use the established importer.
Native packages and purchased sources remain private; this work grants no
additional distribution rights.

`native-dutch-city.py` checks source hashes and copies the three capital layers
before changing owned actors. It compares unrelated actor states, writes change
journals, and refuses changed or unreceipted outputs. Repeating a completed build
verifies its hashes without duplicating inhabitants or architecture. Each revision
uses a separate GM draft directory; the original draft is not overwritten.

`dutch_city_activation.py` constructs a separate complete campaign shell, changes
only Bastion's layer bindings and retains all other zones and portal identities.
Activation requires full native city evidence and a two-client streaming check.
Original maps, manifests and startup settings remain available for rollback.
Interrupted publication is journaled and resumes only when each file matches its
recorded before/after hash. Changed editor work stops the affected update.
Independent campaign review metadata is merged against the captured baseline;
competing edits to the same field stop activation. Concurrent review states are
backed up before publication, preserving portal checks from other tasks.

`migration/dutch-bastion-city.json` is the portable authoritative architecture
ledger: streets, blocks, openings, buildings, venues, native bindings, source
hashes, relocations and review status. `dutch_city_revision.py` validates and
exports it into private native migration content. Native GM catalog entries derive
from actual placed meshes and retain stable building identities.

## Commands

```powershell
python -m pip install --target artifacts/unreal/dutch-bastion/python -r scripts/unreal/requirements-dutch-bastion.txt
python scripts/unreal/dutch-bastion-pipeline.py city-survey
python scripts/unreal/prepare-dutch-city.py
python scripts/unreal/dutch_city_ground.py
python scripts/unreal/plan-dutch-city.py
python scripts/unreal/dutch_polygon_architecture.py
python scripts/unreal/prepare-dutch-city-placement.py
python scripts/unreal/audit-dutch-overlaps.py
python scripts/unreal/dutch-bastion-pipeline.py city-assets
python scripts/unreal/dutch-bastion-pipeline.py city-build
python scripts/unreal/dutch-bastion-pipeline.py city-route-survey
python scripts/unreal/dutch-bastion-pipeline.py city-world
npm run unreal:build -- --target Editor
python scripts/unreal/dutch-bastion-pipeline.py city-proof-config
python scripts/unreal/dutch-bastion-pipeline.py city-proof
python scripts/unreal/dutch-bastion-pipeline.py city-performance-config
python scripts/unreal/dutch-bastion-pipeline.py city-proof
python scripts/unreal/dutch-bastion-pipeline.py city-baseline-config
python scripts/unreal/dutch-bastion-pipeline.py city-proof
python scripts/unreal/dutch_city_revision.py
python tests/unrealDutchBastion.test.py
python tests/unrealDutchCity.test.py
python tests/unrealDutchRevision.test.py
```

`city-review-config` is a shorter diagnostic, not full city acceptance.
`npm run unreal:zone-network-proof -- --candidate <revision>/campaign.json` tests
the candidate before publishing it. `city-apply` requires the recorded native
review, exact package hashes and streaming evidence. Do not edit acceptance flags
to bypass failed evidence. The saved pilot remains available through current.json;
city-current.json identifies the city candidate.

After examining the saved views and reports, the reviewer records `review.json`
inside the private revision directory with its `revision`, `visual`, `traversal`,
`performance`, `networkEvidence` and `unfinished` fields. Activation verifies the
native reports and package hashes in addition to those attestations. Supplemental
camera captures use `city_details`; they cannot replace the full `game-proof`.

## Verification and remaining gates

The native proof captures gameplay lighting and walks the actual 84-by-192-cm
player capsule through every configured street, court passage and public room.
Failed routes remain explicit in the report. Performance comparison uses the same
six cameras and resolution in the previous dense city and corrected city with VSync and the
frame cap disabled; draw calls, primitives, physical memory and outstanding
streaming requests are recorded after settling. It is a local Windows comparison,
not three-platform, multiplayer-load or Steam acceptance.

Initial native review caught rotated masonry UVs, recessed gable windows and a
mismatch between roof and gable peak heights; the generator was corrected.
A sloped entrance diagnostic also spawned below its paving; outside route points
now use the actual graded surface. Paving triangles share the height field's
exact diagonal. Failed preliminary reports remain private and are not acceptance.

The final ground survey checks 3,000 route samples without discrepancies. Bridge
approaches retain their original deck elevations; graded paving extends to the
retained approach roads. Lantern Bank, Sailmakers' Cut and South Court avoid
preserved public interiors. A capital-owned overcast fill keeps shaded brick
facades readable. Mesh, material and texture dependency hashes accompany the
saved level hashes, so subsequent asset edits invalidate the reviewed revision.

Capsule walking additionally caught a tapered court exit and lanes crossing
preserved Cinderbank rooms. Shared rear-wall coordinates now keep passages wide,
and road validation includes the retained buildings' full bounds. The historical
citadel path endpoints also extended through solid native walls: retained route
records now end inside the actual great-hall entrance and at the two exterior
overlooks. No citadel wall, gate or floor is changed by this revision.

Current code verification: 33 Python geometry/ledger tests, 69 native foundation tests,
704 general tests and 139 Unreal tooling tests passed. Three TypeScript checks,
Unreal audit, world validation and model validation passed. The correction changes
Python authoring and saved geometry; no C++ rebuild was needed for these fixes.
The 157-view native run and 42 supplemental corner captures were reviewed;
supplemental cameras replace obstructed original corner views. All 139 actual
capsule routes passed with zero failures. The exact campaign passed two-client
local streaming on its isolated retry after a concurrent rendering run timed out. Repeated
build and activation runs passed without duplicates; original level, city export
and GM draft hashes remain unchanged.

The September 29 matched six-view measurements used 1600 x 1000, six seconds of settling, uncapped
frames and VSync off on Windows 11/D3D12, Ryzen 7 7700 and Radeon RX 7700 XT:

| Metric | Previous dense city (`61bc85751eac`) | Corrected city |
|---|---:|---:|
| Whole-city P95 frame time | 14.99 ms | 13.66 ms |
| Pooled P95 frame time | 11.51 ms | 10.79 ms |
| Pooled P95 draw calls | 22,125 | 22,128 |
| Pooled P95 primitives | 14,556,215 | 15,291,796 |
| Final process physical memory | 5,566 MiB | 5,573 MiB |
| Peak pending texture requests after settling | 0 | 0 |

All six revised views stayed below 16.7 ms at P95 on this development machine.
Draw calls and memory are broadly unchanged; clipping increases measured rendered
primitives by about five percent. These short development runs do not establish
a speedup, release readiness or 18-player performance acceptance. The earlier
September 28 comparison against the original sparse city remains historical evidence.

Private evidence and rollback snapshots are under
`artifacts/unreal/dutch-bastion/d105951f4aab/`: `game-proof`, `city_details`,
`visual-review.json`, `route-ground-survey.json`, `performance-comparison.json`,
`source-overlap-audit.json`, `review.json`, `fix-verification.json` and `activation-backup`.
The two-client report is
`artifacts/unreal/world-portals/network/1790682065290-23344/report.json`.
The active campaign package is
`/Game/WorldRebuild/DutchBastion_d105951f4aab/Bastion_Campaign_v3`.

The migration release gate remains blocked independently by existing gameplay,
model, Steam and Windows/Linux/macOS acceptance requirements. City architecture
never marks those gates complete.
