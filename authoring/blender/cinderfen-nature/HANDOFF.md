# Cinderfen nature handoff

Status: technical pass; final actual-export visual acceptance pending.

| Runtime key | LOD0 / LOD1 / LOD2 triangles | LOD0 SHA-256 |
|---|---|---|
| frontier_cinderfen_marsh_alder | 102450 / 38616 / 5672 | 53a409a11d64ebf2ad32a737b887abfc23b26454f4078227a177942510e3832c |
| frontier_cinderfen_reed_clump | 105672 / 20960 / 5944 | bfe7d14840216e1e3ab4d28ec540f2c01a4adbbf741239b29f3ca8d7308227ca |
| frontier_cinderfen_sedge_horsetail | 29028 / 14556 / 4260 | 3792876915e7aeeddeb3e9563389e562afbd3210681af1fe84aed7e38a065416 |
| frontier_cinderfen_basalt_outcrop | 12474 / 2356 / 208 | 73a4024da48d7ae8af88e0ce175e8eef29cc214f2832b8c32c7071a48088e6d5 |

Runtime filenames are each key followed by _lod0.glb, _lod1.glb and _lod2.glb. All 12 staged GLBs pass Khronos with zero errors/warnings. Five original-source tests and four strict repository blueprint checks pass.

Actual bounds and model-space colliders are in builder-metadata.json. Reed/sedge are nonblocking; alder has its trunk collider and basalt four mass colliders. All are static and planted at local Y0, with natural roots/toes intentionally below datum. No walkable platforms or gate interactions are claimed.

All 45 primary alder root/limb socket tests pass against the actual GLBs. Each LOD has one connected primary bark shell; every primary terminal reaches that same component. All 12 actual reimports have zero positional boundary, multiface and loose edges. review/alder-joins.json retains the measurements. Minor directional bark UV joins remain visible at original cage boundaries in the lower close view; no floating collars remain.

The final evidence includes 29 actual-export images: 12 neutral, 12 measured gameplay-distance, four material details and the lower alder join view. The two contact sheets are review/all-exports.png and review/gameplay-exports.png. Build-report SHA-256: 2b89330f7030b753f9bb54cb4ca481824b1dfff08e2c5f4595a5c8a509bbfa2b. Source provenance SHA-256: 294270243fc48cd8fec2ac71dc245faaa86cb098d6c7c29b38de6ee151cd48bd.

No global registry, campaign map, landscape composer or shared app source was edited. Parent owns activation and landscape placement. The accepted Cinderfen architecture package remains frozen.
