# Sunmeadow Empire herbalist

Revision **l** is technically verified and frozen for root publication. Nine
current-export gates pass; three LODs retain all nine clips and 18 inspected
views. See `review/technical-readiness.json` for hashes, metrics and scope.

Original practical herbalist using the retained female civic anatomy and rig.
The female anatomy is normalized consistently to the common 1.86 m authoring
height, retaining its own proportions, face, exposed limbs and skin data.
This is a separate character package; published farmer/dwarf packages are read-only.

The cream linen shirt has a connected torso, axillae and sleeves, real fabric
thickness, sewn cuffs, laced placket and turned collar. The sage oversmock has
separate armholes and four divided hem panels for leg travel. A gathered chestnut
groom ends in a coiled braid. The belt carries a gusseted gathering satchel,
authored herb stems/leaves and two stoppered ceramic medicine vials seated in
leather holders. Fitted flat hangers wrap their individual belt sections.

All additional meshes are authored garment patterns, fitted surfaces and shaped
profile sweeps. No primitive model operators are used.

## Package files

- `sources/`: packed editable Blender master.
- `runtime/`: three actual GLB LODs with the nine named runtime clips.
- `tools/build_inhabitants.py`: retained fitted-clothing pipeline adapted to
  the female foundation; `herbalist_head.py` and `herbalist_details.py` own the
  original groom, oversmock and tools.
- `foundations/input-provenance.json`: hashes of inherited helper origins.
- `foundation-provenance.json`: retained anatomy/texture policy and source inputs.
- `review/*_build.json`: exact generating dependencies, master, embedded images
  and exports. Post-build inspectors have separate validation hashes.
- `review/master-continuity.json`: continuous shirt topology, divided source
  panels, packed images and modifier order.
- `review/*_motion.json`, `arm-volume-lod*.json`, `*_boot_clearance.json`,
  `*_welt.json`, `*_garment_clearance.json`, `*_tool_clearance.json`,
  `*_equipment_attachment.json`, `*_belt_clearance.json`: measurements
  of the actual reimported GLBs.
- `publication-contract.json`: profile, female body family, skeleton and bind
  pose identifiers. Root owns publication, GM integration and zone placements.

## Verification

Run Blender with `--background --threads 2 --python-exit-code 1 --python` and the
package tool path. Build with `build_inhabitants.py -- --assets=empire_herbalist`.
Run `node authoring/blender/sunmeadow-herbalist/tools/validate_inhabitants.mjs`.

Run `inspect_master.py` once; for each `--lod=0`, `--lod=1`, and `--lod=2`, run
`inspect_export_motion.py`, `inspect_arm_volume.py --report=arm-volume-lodN.json`,
`inspect_boot_clearance.py`, `inspect_boot_welt.py`, and
`inspect_outfit_clearance.py`, `inspect_equipment_attachment.py`, and
`inspect_belt_clearance.py`. All nine clips are sampled at exported keys and
midpoints. The boot reference ring is an exact triangle/height section, so
decimation does not depend on retaining a row of vertices at the hem height.
Forearm size is measured against the retained female foundation at matching
bone sections, preserving its anatomical span within ten percent; animation
area variation remains limited to twenty percent, with complete circumferences.
This avoids applying a dwarf wrist-size floor to the female anatomy.
Equipment contacts use exact imported triangle witnesses, four closed load
loops and shared rigid hips weights. Every actual posed assembly is checked
against the common rigid transform; a residual above 10 micrometres fails.
Thus the contact geometry is preserved across all sampled clips without
pretending that source-only attachment is sufficient. The belt has a separate
layer audit with no excluded waist band: tucked cloth and bindings must stay
inside its actual inner surface, and triangle edges may not cross the leather.
The belt follows the complete vertical cloth envelope, and the tucked layers
share its hips attachment with a smooth transition into freely moving cloth.

Use `review_inhabitants.py -- --lod=N --views=front,head,side,rear,run_side,death:2
--suffix=_l` for actual-export views. The renderer caps CPU work at two threads.
After inspecting the views, run:

```powershell
python authoring/blender/sunmeadow-herbalist/tools/test_exports.py
```

Building new bytes invalidates earlier readiness and reports. Technical gates
measure the complete fitted outfit with its own clips, not arbitrary modular
armor, animation blends, runtime cloth or interactive harvesting. The smock's
waist tuck and holder/content overlap are intentional and explicitly scoped in
the outfit contact report. Frozen release `63072b851393b42f4329` is published as
Serra Brightfield and in the GM builder. The production Game/NpcSpawner verified
visible LOD0/1/2 at 6.2/45.2/100.2m and grounded placement on the shelter floor.
Exact map/model/harness hashes and bounded verification limits are retained in
`review/runtime-integration-20260920.json`.
