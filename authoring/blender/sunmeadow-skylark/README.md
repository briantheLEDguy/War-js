# Sunmeadow skylark revision

Paused, unapproved work in progress. September 9 user priority puts character
models, equipment and town/siege items first, with animals last. Do not resume
this package ahead of those priorities.

Root owns this isolated continuation of the original
skylark prototype; the other fauna remain in `sunmeadow-fauna`.

`source/prototype-snapshot.json` binds the retained prototype GLBs and copied
authoring helpers. `source/anatomy.json` contains only the original bird's
authored sections, colors and landmarks. The copied helpers are local sources,
so work on the buck cannot alter this revision. No runtime publication or GM
entry is implied by these files.

First inspect the actual baseline at an appropriate close camera. Then repair
folded-wing skin transport, leg/foot contacts and the complete airborne cycle,
retaining deliberately authored feather thickness, layered wings, original
plumage, explicit UVs and all three LODs. Any altered anatomy/material needs a
new exact-export review before publication.

The new `build_skylark.py`, `skylark_anatomy.py` and `skylark_materials.py` retain
a separate v2 candidate, with an original passerine skeleton, shaped closed
feathers, fitted eyes, bill and toes. Only LOD0 has been exported. Its source,
master and model hashes are in `review/skylark_v2_build.json`. Current neutral
idle/flight renders are inspection evidence only; anatomy, folded-wing overlap,
deformation, contact, all LODs and material quality remain unapproved. Some older
runtime render receipts describe superseded candidates. Rebuild/review explicitly
when resumed; do not publish from mere file presence.

Anatomy/plumage reference notes: [Cornell identification](https://www.allaboutbirds.org/guide/Eurasian_Skylark/id)
informed the 17.5-19 cm length, short crest and bill, brown flight feathers,
streaked buff breast, pale belly and white outer tail feathers.
[RSPB identification](https://web-cdn.rspb.org.uk/birds-and-wildlife/skylark)
supports the grassland bird's crest and contrasting wing/tail edges. No reference
photograph or third-party mesh was copied into this package.
