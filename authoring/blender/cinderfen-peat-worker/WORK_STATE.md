# Peat worker production state

2026-09-20: final revision F is technically ready for parent publication. All
three current GLBs passed Khronos validation with zero errors and warnings,
then all eleven focused export regression gates passed. The editable master
continuity audit also passed. Standing user approval covers aesthetics.
No public models, registry, campaign maps, GM data or shared sources were edited
by this package's authoring task.

The original Greenskin worker has a sculpted broad jaw and brow, shaped ears,
rooted curved tusks, continuous waxed-linen shirt/collar, wool trousers, tall
closed marsh boots, a fitted leather work bib and breast pocket, and a curved
belt-supported sheathed peat knife. Added visible surfaces use authored mesh
profiles or garment surfaces. No primitive models or rig-display helpers are
present in the export. The actual retained foundation and generating inputs are
recorded in foundation-provenance.json and the build receipt's sourceFiles;
validationSourceFiles separately records current inspection and viewer sources.

Final evidence:
- Three LODs: 133,208 / 77,251 / 35,849 triangles, each with all nine runtime clips.
- Each LOD's arm inspection measures 224 posed sections. Minimum area ratio is
  0.9999938; the largest angular opening is 23.48 degrees.
- Literal export keys and midpoints have no measured tool/clothing crossings,
  belt/bib intersections, boot/hem penetration, or bib/knee penetration.
- Worst measured ground height across all clips and LODs is +2.49mm. Stationary
  soles remain within the 12mm contact gate; terminal death hands settle at +5mm.
- Closed sole welts remain within 3.17mm of the actual animated boot surface.
- Worst material p99 edge stretch is 2.139; maximum individual edge extension
  is 57.50mm at LOD2, within the unchanged 60mm gate. Reduction deforms small
  detail edges more than LOD0, so the reduced models are for distance use.
- master-continuity.json confirms nine independently editable, connected, closed,
  UV-mapped, fully weighted outfit/tusk surfaces in the saved master.
- Final _f views cover close front/head/rear, run/front and side, terminal fall,
  and gameplay distance; LOD1 and LOD2 each have front and gameplay views.

The final correction changed an inward belt mount normal to an outward planar
normal and added measured outward sheath-tip curvature. Earlier C-E diagnostics
are superseded. Their failures were corrected in geometry/animation; no physical
clearance or deformation tolerance was relaxed.

Compatibility is frontier_mire_worker / variant m, skeleton
frontier_mire_worker_v1, bind pose frontier_mire_worker_a_v1. This is a complete
fitted civilian outfit using its own embedded clips, not modular armor or a siege
crew compatibility claim. The sheathed knife is carried visual equipment; no
harvesting interaction or facial/lip-sync animation is claimed. Audits sample
export keys and midpoints rather than proving every possible interpolated time.
Three.js in-game placement and GM integration remain the parent's responsibility.

Reproduction and current reports:
- tools/build_inhabitants.py writes the master, atomic three-LOD export and build
  receipt after verifying its exact generating inputs did not change.
- tools/inspect_master.py refreshes review/master-continuity.json after a rebuild.
- tools/run_quality.py checks all current exported LODs, validates glTF, and runs
  tools/test_exports.py. Final complete result: review/quality-f.log (11/11).
- review/frontier_cinderfen_greenskin_peat_worker_build.json contains exact hashes.
- review/inhabitant.html is an independent Three.js byte-verifying clip/LOD viewer.

Frozen F identifiers:
- Master: 4bca8d68d410232b6f439f3d1ac5a452f8095a43a035c09ef3b87266980011f8
- LOD0: b64aae36dfeabba7c256c78f7ae112ea8388eb6bcebc675d082f4cfabacd19a9
- LOD1: d4a5b4844bcfc4c70c9d90d5ec42bb4f687ab771530bc95a406ef0e58c8f5f1d
- LOD2: d187f41c4c3df12bdf65bd6780687031c62528af7d7de4c1eb4dadc0428fe4ec

## Root integration — September 20

Published exact F exports with standing approval, activated the registry and GM
catalog, and placed Barrek Reedhauler in the Cinderfen workyard. Actual production
gameplay rendering loaded all three LODs at 6.2/45.2/100.2m (133208/77251/35849
triangles), with no character fallback. Four publication regressions verify the
retained sources, runtime/QC hashes, clips, GM entry and actual map identity.
See review/runtime-integration-20260920.json for scoped evidence and limits.
