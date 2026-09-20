# Field apothecary station

Published and integrated, 2026-09-20. Root completed game/GM publication and
placement in both Sunmeadow and Cinderfen supply shelters. Frozen source release
is `839beb3b995788c0ccb2`. Three LODs and all 19 measured colliders are delivered.
Both actual-game collision presses stop the player at the table front while
retaining .086m / .35m floor height. The runtime integration receipt records
the exact map/model/harness hashes and limits. Six dedicated integration tests
also verify actual host meshes, supported feet, working fronts and route access.

## Final technical and visual handoff

All three final GLBs pass `validate_station.mjs` and its read-only `--check` mode:
zero Khronos errors/warnings; finite unit orthogonal tangents; embedded PBR; exact
source, packed-master, texture, model and image-receipt hashes. All six actual
masters and all three reimported GLBs have zero positional boundary, multi-face
or loose edges. Four flat feet and 19 geometry-derived colliders are verified.

Final actual GLB renders were personally inspected: LOD0 neutral/detail/joinery/
rear/4 m, LOD1 neutral/12 m and LOD2 neutral/28 m. The corrected timber texture
continues across board repeats; the fitted rack, restrained vials, mortar/trays
and three herb bundles remain legible. Distant levels simplify leaf density and
small fittings while preserving the full station silhouette. No paint-over or
image editing was used. Amber vessels are opaque, not transmission glass.

GLB SHA256 values:
- LOD0: `ad505319ec15cb6612268de76e096a64c0397dc196e2ee7f1600e4c4e599b48d`
- LOD1: `74d711eed3c3bec87bf22a410d71bcb10659478768f7f5b2c7763e0de77fc50b`
- LOD2: `7fe1d8c3518ef48ba8d9965dd56601baa52c07dbee7a58ce181a58227b005cff`

The 0.5 m actor corridor from local Z2.5 to Z1.1 is unobstructed by the station.
This does not claim complete village placement or game navigation verification.
All package Blender processes have completed. No art/geometry changes remain
pending. Earlier failure logs and audit JSON are diagnostic history only;
validation.json and current-hash reimport receipts are authoritative.

## 17:46 checkpoint

Asset key is `frontier_field_apothecary`; asset ID `prop.frontier.field_apothecary`.
All three literal GLBs exported with embedded nine-material PBR. Triangle counts
are 38,574 / 19,512 / 8,694. Six packed editable source/finished Blender masters
passed actual-file topology inspection, including four flat ground feet. Exact
construction/source/image hashes are retained in the consolidated build receipt.

Actual footprint is 2.292 by 1.020 m, overall height 1.850 m. Receiving mortises
include the four leg rail joints and two cut worktop sockets for the rack posts.
The source measures collision from named visible structural masses. The intended
host-center standing point has 0.59 m clearance before actor radius, but village
placement and traversal remain root's integration work.

First actual exported neutral/detail images were inspected. The table/rack/tools
read well; a timber repeat seam was corrected with periodic source texture noise.
The far-LOD bundle's coincident capped stem ends were separated inside their
binding, and all three batched masters now pass closed positional topology.

Final current-byte renders are running with two threads per Blender process:
LOD0 neutral/detail/joinery/rear/gameplay and LOD1/2 neutral/gameplay. Their old
images must not be used for acceptance until final reimport hashes match.
`tools/validate_station.mjs --check` is a read-only gate; first run without
`--check` writes validation.json after all final evidence passes. The current
gate correctly rejects old render evidence while those renders finish.

One original joined worktable with an integrated rear drying/vial rack. Target
runtime footprint 2.30 m wide by 1.06 m deep, worktop 0.94 m, rack about 1.82 m.
Front is +Z in runtime (+Y up); authoring uses Z up and front -Y. Reserve a
2.20 m wide by 1.10 m deep working space beyond the front edge. Exact dimensions
and separate visible-mass colliders will be measured from the finished geometry.

The existing published repair bench neutral/detail exports were inspected as the
craftsmanship reference. No model geometry or texture pixels will be copied.
Every visible part starts as an authored polygon boundary, shaped section loft,
profile of revolution or curved leaf surface; no primitive operators.

Planned: fitted mortise/tenon frame, individually worn top boards, rear pegged
supports, clamped rack, strapped stoppered vials, hollow preparation trays, mortar
and pestle, bound drying herbs. Three deliberate LODs retain the useful silhouette.
Source-backed PBR textures and a packed editable Blender master are required.

Ownership: this package only. Root owns publication, game/GM placement and any
future interaction behavior. No gameplay interaction is claimed by the artwork.
