# Purchased modular kits in the GM builder

The owner has authorized using already purchased Unreal store modular kits for
city environments and the native GM building catalog. This is a narrow addition
to the repository-source policy, not authorization to purchase more assets.
The owner approved launcher inspection. Three relevant owned entries were
identified on 2026-09-21; their listing metadata is summarized below. Actual
purchase-license evidence and dependency inspection remain outstanding. No kit
has been installed, converted, imported or accepted by this migration work.

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
