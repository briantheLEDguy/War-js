# Purchased modular kits in the GM builder

The owner has authorized using already purchased Unreal store modular kits for
city environments, outdoor zones, dungeons and the native GM building catalog. This is an addition
to the repository-source policy, not authorization to purchase more assets.
The owner approved launcher inspection. Three relevant owned entries were
identified on 2026-09-21; their listing metadata is summarized below. Actual
purchase-license evidence and dependency inspection remain outstanding. No kit
was installed during that initial inspection. On 2026-09-21 the owner subsequently
installed Medieval Houses Modular Vol 2 and RPG environment effects into the
private `artifacts/unreal/licensed-kits/CityKitStaging` project. Medieval Modular
Town was still downloading and Paragon was queued when checked. These downloads
must not be interrupted. Kit runtime, visual and license acceptance remain open.

## Owned candidates inspected in Epic Launcher

These are publisher claims read from the signed-in Fab library and product
Formats tabs, not runtime measurements or acceptance evidence.

| Kit | Publisher | Listed Unreal versions | Relevant listing information |
|---|---|---|---|
| Medieval Modular Town (With Interiors) | Jemini Studio | 4.21–4.27, 5.0–5.8 | 393 static meshes plus two cloth flags; collision and LODs advertised; explorable interiors; Win32/Windows listed |
| Medieval Houses Modular Vol 2 | GameAssetFactory | 4.22–4.27, 5.0–5.8 | 209 modular assets, 16 assembled buildings and 73 nature assets; Windows/Mac plus console platforms listed |
| Castle Modular Pack | ArzaonGames 3D | 4.23–4.27, 5.0–5.4 | 164 meshes; custom collision and LODs advertised; Windows listed; launcher flags incompatibility with installed 5.8.2 |

Start compatibility evaluation with the two 5.8-listed kits. The castle kit
requires a forward-conversion trial. Linux is not listed for any of these three;
its absence is an unverified platform requirement, not proof of incompatibility.
Mac listing support likewise does not replace this project's packaging and
runtime tests. The castle product page displays a current Standard License and
an AI-usage restriction indicator; inspect the actual license terms applicable
to the purchase before adaptation or distribution. A library entry is not a
completed provenance review.

The inspection changed no library downloads, installed plugins or project assets.
Other library entries were not exhaustively audited. Their names or presence do
not imply admission to the GM catalog.

## Background inspection workflow

The owner requested no keyboard/mouse or foreground-window control while they
use the computer. Use background commandlets for remaining inspection and tests.
`scripts/unreal/inspect-city-kit.py` reads house-kit meshes, materials, bounds,
LODs and authored collision in CityKitStaging without executing kit Blueprints.
`scripts/unreal/stage-city-kit.py` selects a bounded house/floor/wall/doorway/stair
pilot, resolves package dependencies, rejects dependencies outside the kit's
environment root, and verifies source/destination hashes. Neither script grants
runtime or release approval. Generated receipts stay under ignored `artifacts/`.

The pilot preserves `/Game/Medieval_Environment/` package paths so existing
material references remain intact. Its corresponding native Content directory
is explicitly ignored by Git, in addition to `Content/LicensedKits/`. Never force
add either directory. Active downloads and original staging packages remain
unmodified by these scripts.

The main project is registered in Epic Launcher's `CreatedProjectPaths` using
the repository's `unreal` parent directory. AegisWar uses association `5.8`, which
resolves to the installed 5.8.2 build. The running launcher may need restarting
after downloads finish before its project list refreshes.

## First house-kit pilot

The separate map `/Game/Capitals/kit_pilot/AegisCapital_Workbench` starts a local
replacement trial: one residential placement uses the kit's assembled House 02,
with four nearby floor/wall/doorway/stair samples. Its GM catalog includes all
five pieces as searchable `Town kit` entries (14 models total, 306 editable
placements). The original capital map is retained. This is a pilot, not a
completed district or an interior traversal approval.

The read-only inventory found 230 meshes under the house-kit root. The selected
pilot uses 23 original dependency packages. House 02, the wall and stairs lacked
simple collision and had default collision settings. Separate meshes under
`/Game/LicensedKits/MH2/` enable triangle collision for those three; the floor and
doorway retain their authored simple collision. Originals are untouched. Native
GM construction now preserves mesh collision and material slots as well as the
existing attached box volumes. It never fills a doorway with a bounding box.

Reproduce with the inspection and staging scripts in CityKitStaging, followed
by `prepare-city-kit-pilot.py` in AegisWar. `render-city-kit-pilot.py` uses
offscreen commandlet rendering; use `-NoTextureStreaming` for inspection images.
Run `npm run unreal:capital-proof -- --kit-pilot` for actual gameplay checks.
The native checks passed blocking traces for all five pieces, created-floor
capsule support, model/material retention, picking, undo/redo and a separate
process loading the construction draft. Source-only and import receipts are not
counted as these runtime checks. `unreal:package-proof -- --include-capital
--include-kit-pilot` includes the pilot in a local Development package; it does
not authorize distribution or open the release gate.

Complete interior/stair traversal, visual review, modular seams/pivots, wider
city replacement, kit license review, performance and all shipping platforms
remain unfinished. The pilot currently uses the same development draft location
as the original workbench; conflicting map baselines are rejected, so do not
treat a draft from one as a draft for the other.

## Integration path

1. Inventory each installed kit: product identity, purchase/license evidence,
   supported engine versions, mesh/material dependencies and required plugins.
   Keep originals intact and convert a separate staging project to Unreal 5.8.2.
2. Migrate selected assets with their dependencies. Resolve shader, Blueprint and
   plugin failures before admitting any pieces. Asset conversion alone does not
   establish suitability for the game or any shipping platform.
3. Review meshes, textures/materials, pivots, scale, collision, walkable stairs,
   door openings, LODs and lighting. Verify the actual pieces in a rendered game
   and cooked builds. Use conventional LODs/scalable materials where required by
   the Windows/Linux/macOS baseline; do not assume Nanite-only content is suitable.
4. Register reviewed pieces using stable catalog IDs, source/version fingerprints,
   categories, bounds, grid dimensions, pivot offsets, rotation increments and
   approved collision. Rooms or assemblies need explicit component definitions.
   The current house-template catalog does not yet provide this generic adapter.
5. Adapt builder placement to kit-specific pivots, sockets, orientation and previews.
   Basic world XY grid and yaw snapping are implemented for existing authored
   buildings; that alone does not establish modular seam/pivot compatibility.
   Preserve selection, transforms, collision, undo/redo, draft save/load and
   additive-import compatibility. Test a room assembled from walls, floors,
   stairs, roof and door openings, then reload it in a fresh game process.
6. Test trusted server resolution and packaged clients. Saved drafts reference
   catalog IDs, never arbitrary asset paths or executable kit Blueprints.
   Interactive doors/lifts require explicit authoritative gameplay adapters;
   importing their appearance does not implement their behavior.

Older static mesh kits are candidates for conversion, not guaranteed compatible.
Blueprint-heavy kits and code plugins require separate dependency review. If a
kit cannot work on the target version/platforms, retain its rejection reason and
continue using accepted authored assets. Never replace failed pieces with visible
primitives or declare the capital complete from a successful import alone.

## Source handling and acceptance

Keep raw purchased assets and conversion projects outside the public repository.
The designated local content mount `unreal/AegisWar/Content/LicensedKits/` is
ignored by Git. This ignore rule only covers that location; inspect the complete
diff and dependency destinations after every migration. Share source assets only
as permitted by the specific purchase license. Track non-sensitive catalog
metadata and reproducible import instructions separately from licensed binaries.

Review the actual license attached to each older purchase; do not assume a legacy
Marketplace purchase has the current Fab license. Cooked distribution, private
collaborator access and raw redistribution are distinct uses. Final release
acceptance still requires all gameplay, model, platform and Steam gates.

Epic references: [migrating dependencies](https://dev.epicgames.com/documentation/unreal-engine/migrating-assets-in-unreal-engine),
[upgrading a copy of a project](https://dev.epicgames.com/documentation/unreal-engine/updating-projects-to-newer-versions-of-unreal-engine),
and [current Fab license summary](https://www.fab.com/eula).

Verification on 2026-09-21: editor pilot receipt
`artifacts/unreal/capital-proof/1790000112845-37796/report.json`; packaged Windows
pilot receipt `artifacts/unreal/capital-proof/1790000673607-35016/report.json`.
The local Development package built successfully with both capital maps. All 21
native foundation groups and 85 tooling tests passed, plus tooling typecheck.
The first house render shows the textured authored model, but complete visual
and interior acceptance remain open. Release readiness still reports four
blocking categories.

The doorway clearance probe measures its 15 cm timber threshold, checks it
against the character movement step-height limit, then sweeps the actual 42 cm
radius / 96 cm half-height capsule through the opening at that standing height.
This passes in editor and packaged Windows runtimes; it is a bounded clearance check, not a claim
that every interior or staircase has been walked end to end. Inspection images
show the authored stone, timber and thatch materials at full texture resolution.

Next integration work is the Medieval Modular Town building assemblies. Its
files appeared in staging after the initial download check. Confirm a stable,
complete source inventory first; assembled Blueprint buildings require explicit
static component, material and collision extraction plus authoritative adapters
for any doors or other behavior. Do not spawn arbitrary purchased Blueprints
from GM draft requests. The current five-piece pilot uses static meshes only.

Final packaged doorway/GM proof: `artifacts/unreal/capital-proof/1790001209987-31332/report.json`.

## Town assembly adaptation

`scripts/unreal/inspect-town-kit.py` inspects Blueprint component templates in
CityKitStaging without spawning the Blueprint. The installed Medieval Modular
Town inventory contains 393 static meshes and 56 Blueprints. The first building
has 354 static components beneath one identity-transform scene root, using 63
distinct meshes and 18 materials. Other hierarchies or component behaviors need
an explicit adapter; this is not blanket approval of the pack.

`scripts/unreal/adapt-town-kit.py` creates an isolated inspection world and
merges those templates into a private static mesh, preserving component
transforms, material overrides, vertex data and all four source LOD levels.
Run it using UnrealEditor-Cmd with `-run=pythonscript`, `-RenderOffscreen`,
`-AllowCommandletRendering` and `-unattended`. Do not use `-NullRHI` for the merge:
Unreal substitutes its default material when render material resources are
unavailable. The tool rejects differing material coverage, fingerprints the
source pack before and after, and gives each adaptation a unique asset path.
Original purchased assets and previous adaptations are never overwritten.

The verified merge contains 357,648 / 188,507 / 113,557 / 77,932 triangles and
all 18 materials. This is substantial geometry; district-scale performance is
not established. `scripts/unreal/verify-town-kit.py` performs fresh-process
structural reload checks, including triangle collision configuration, and may
run with `-NullRHI`. Local receipts live in
`artifacts/unreal/licensed-kits/town-kit-adaptation.json` and `town-kit-reload.json`.

This adaptation remains outside the current GM catalog. A bounded dependency
closure is copied into ignored game content for inspection using
`scripts/unreal/stage-town-kit.py`; it refuses changed destination bytes or
dependencies outside the reviewed pack. The 87 packages retain their original
material paths. `render-town-kit.py` makes isolated front/rear offscreen images
without opening an editor window or changing the capital maps or drafts.

Visual inspection caught an incorrect Python positional Rotator conversion in
the first merge. Unreal uses roll/pitch/yaw positional ordering, whereas the
inventory records pitch/yaw/roll. The adapter now uses named fields and checks
all 354 rotations using basis vectors before merging. The corrected front/rear
renders show a coherent textured exterior; this does not establish complete
interior, LOD or runtime approval. Corrected receipts and images supersede the
initial malformed assembly, which was never admitted to the GM catalog.

`scripts/unreal/probe-town-kit.py` records diagnostic 42 cm radius / 96 cm
half-height capsule sweeps across the front entrance candidate at local x=600.
All five heights (120–160 cm) hit geometry near y=43 cm. The current static merge
therefore has no entrance traversal approval. Resolve door/component behavior
and verify the actual walking route before registering it as a usable building.
The receipt explicitly keeps `traversalApproved` false.

Its construction script and interactive door behavior are not ported. Triangle
collision configuration alone is not evidence of traversable doors or stairs;
visual review, traversal, runtime GM integration, performance, licensing and
platform checks remain required before city deployment.
