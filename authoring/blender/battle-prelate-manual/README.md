# Battle Prelate editing study

This is an incomplete Blender editing experiment, not a photo-accurate character or an approved runtime asset.

`battle_prelate_batch_study.blend` is the current result. The source was an existing armor master with inherited MPFB-derived anatomy, earlier armor geometry, and a hidden reference weapon. It is not a newly handcrafted character. `battle_prelate_before_batch.blend` preserves the scene before the Python batches; `battle_prelate_manual_study.blend` is the earlier saved copy.

## Work performed

The first batch assigned steel, crimson, mail, and leather materials to 17 explicitly named existing components, displayed one armor version, removed overlapping garment alternatives from view, and revealed the existing eyes/brows/lashes. No atlas was overwritten. The second batch tried five object transforms. Visual review rejected and reverted both shoulder transforms; three belt/cloth transforms were retained as a rough study.

The three batch scripts run inside Blender's Python Console using `runpy.run_path(...)`. They are records of specific edits, not character generators. The material and transform batches verified unchanged mesh position/topology hashes and object names. No new mesh, primitive, Geometry Nodes system, remeshing, or procedural texture was added. Earlier manual sculpt strokes on the inherited chest LOD remain in the file, hidden with that LOD.

## Files and verification

- `inspect_study.py` and `study_inventory.json`: live scene inventory before batch edits.
- `batch_01_materials.py` and `batch_01_report.json`: material/visibility edits and execution audit.
- `batch_02_transforms.py` and `batch_02_report.json`: trial transforms, previous matrices, and review outcomes.
- `batch_03_review_correction.py`: restores the two rejected shoulder matrices.

Both batches were executed in the open Blender 5.0.1 application, reviewed in its viewport, and saved. The first batch's material/visibility work executed in about 0.047 seconds, excluding preparation, visual review, and saves; this is not an end-to-end modeling speed measurement.

Known limitations: malformed plate surfaces, poor shoulder shape, generic young face, incomplete garment silhouette, and missing brass trim, insignia, chainmail detail, seals, tome, censer, and correct warhammer. This study has not passed render, animation, clipping, export, or runtime approval.
