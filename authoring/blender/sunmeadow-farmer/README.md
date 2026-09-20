# Sunmeadow Empire farmer

Revision f is published in the game and GM builder as Edric Hayward in
Sunmeadow. Actual local gameplay verified all three visible LODs; the receipt
is `review/runtime-integration-20260920.json`. Five export
gates pass, with zero glTF errors/warnings across all three LODs. The exact
hashes, measured limits, inspected views and remaining integration scope are in
`review/technical-readiness.json`. Publication review suffix: `_f`.

An original full-height regional farmer, using the retained civic male anatomy,
canonical joints and continuous fitted garment construction as foundations. The
farmer has a distinct narrow weathered face, cropped dark groom, ochre linen
shirt, olive woven suspenders, dark trousers, laced work boots, a gusseted seed
pouch and a sheathed pruning knife. All added meshes are authored fitted
surfaces, garment patterns and shaped cross-sections; no primitive replacements.

The published dwarf and its generating package are immutable inputs. Local
derivative helpers are retained here. `foundations/input-provenance.json` records
their original versions, and build receipts record the exact derivative tools,
referenced anatomical foundation, packed image data and editable master.

Runtime publication is owned by the root task. Existence of an editable master
or a render alone does not establish export readiness. Three GLB LODs, nine
literal runtime clips, current-byte import inspection, deformation/contact and
garment checks are required before a technical handoff.

## Package and reproduction

- `sources/frontier_sunmeadow_empire_farmer.blend`: editable full-resolution
  garment, anatomy, head, groom, equipment, skeleton and animation source.
- `runtime/`: three self-contained GLBs with embedded PBR maps and nine clips.
- `tools/build_inhabitants.py`: authoring, tailored animation and atomic export.
  `farmer_details.py` owns the distinct suspenders, pouch, knife and hangers;
  retained fitted-surface helpers build the continuous shirt and dressed limbs.
- `review/*_build.json`: exact generating input hashes, packed image hashes,
  master hash, triangle counts and exported-byte hashes. Inspector hashes are
  recorded separately when those tools change after generation.
- `review/*_motion.json`, `arm-volume-lod*.json`, `*_boot_clearance.json` and
  `*_welt.json`: measurements of actual reimported exports across all nine clips.
- `review/*_review_f.json`: final revision f views, with source and image hashes.
  Older suffixed views are historical diagnostics, not evidence for current bytes.
- `publication-contract.json`: runtime identifiers and ownership. The package
  does not mutate asset indexes, manifests, GM entries or zone placements.

From the repository root in PowerShell:

```powershell
$farmerBlender = 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe'
$farmerTools = 'authoring/blender/sunmeadow-farmer/tools'
& $farmerBlender --background --threads 2 --python-exit-code 1 --python "$farmerTools/build_inhabitants.py" -- --assets=empire_farmer
node "$farmerTools/validate_inhabitants.mjs"
foreach ($farmerLod in 0..2) {
  & $farmerBlender --background --threads 2 --python-exit-code 1 --python "$farmerTools/inspect_export_motion.py" -- "--lod=$farmerLod"
  & $farmerBlender --background --threads 2 --python-exit-code 1 --python "$farmerTools/inspect_arm_volume.py" -- "--lod=$farmerLod" "--report=arm-volume-lod$farmerLod.json"
  & $farmerBlender --background --threads 2 --python-exit-code 1 --python "$farmerTools/inspect_boot_clearance.py" -- "--lod=$farmerLod"
  & $farmerBlender --background --threads 2 --python-exit-code 1 --python "$farmerTools/inspect_boot_welt.py" -- "--lod=$farmerLod"
  & $farmerBlender --background --threads 2 --python-exit-code 1 --python "$farmerTools/review_inhabitants.py" -- "--lod=$farmerLod" --views=front,head,side,rear,run,death:2 --suffix=_recheck
}
python "$farmerTools/test_exports.py"
```

Each command must finish successfully before continuing. Rebuilt bytes invalidate
earlier reports and readiness; regenerate and inspect the complete evidence set.
The render script uses two CPU threads and 16 Cycles samples. Visual inspection
and measured deformation/contact are separate checks.

## Scope of verification

The checks cover the exported civilian outfit and its own nine clips, arm
cross-section volume, floor and final prone support, material-edge deformation,
trouser hems inside boots, and closed sole welts. The boot check follows the
deforming exported boot ring and checks actual hem-edge/boot intersections.
It does not substitute a rigid shin axis for the deformed garment.

This is a complete civilian body with static carried equipment, not a modular
armor or interactive harvesting system. No combat equipment retargeting,
ragdoll, arbitrary animation blending, runtime cloth simulation or unseen
outfit combinations are certified. Game placement, GM registration and actual
browser gameplay verification belong to the root integration task.
