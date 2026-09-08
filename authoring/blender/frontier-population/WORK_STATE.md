# Inhabitant work state

2026-09-07: `/root/orvr_simulation` owns this package's morphology, animation and
review tools and generated drafts. No derivative is published or approved.

The dwarf's exposed forearms were complete but flattened by global stature
compression. `build_inhabitants.py::morphology` now transports the retained arm
cross-section along the morphed forearm, preserving topology, weights and joint
centers. The same mapping fits skin, cuffs and hand joints. Mid-forearm thickness
increased from approximately 5.4 cm to 8.6 cm; distal thickness from 3.7 to 6.1 cm.

Close clean-GLB inspection then found a separate cuff defect: centroid-based
skin removal cut through visible triangles. `tailored_clothing.py` now keeps
the entire distal face and a hidden overlap beneath the cuff. The original
anatomical surface supplies that overlap; no cap geometry is added.

`inspect_arm_volume.py` can inspect the source or `--lod=0/1/2`. It samples the
literal exported idle/walk/run timestamps and midpoints, slices only anatomical
skin in bone-local planes, and rejects missing circumference, less than 5 cm
dwarf forearm thickness, or more than 20% section-area change. Reports and
source hashes are saved to `review/arm-volume-lod*.json`. First corrected LOD0
before the cuff overlap passed 224 samples with area ratio 0.999997–1.000002.
Current final-overlap exports are undergoing the same three-LOD checks.

`review_inhabitants.py` now poses by exact seconds and frames only meshes bound
to the character rig, excluding Blender's unrendered bone widgets. It includes
front/side forearm and walk/run close views. Current three-LOD rebuild finished;
the current clean-import review and numeric audits are still running. Existing
head-only and side images are older and must be rerendered before final approval.

Remaining: inspect the final cuff/arm views and all-LOD audit reports, then obtain
the root agent's visual decision before extending the same retained pipeline to
the remaining Empire farmer/herbalist, High Elf scout, Greenskin peat worker and
Dark Elf supply officer. Those roles need their own fitted equipment, grooming,
body proportions and movement review. They must not inherit dwarf-only offsets.
