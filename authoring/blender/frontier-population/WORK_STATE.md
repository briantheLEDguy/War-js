# Inhabitant work state

## 2026-09-09 resumed bounded dwarf motion work

`/root/frontier_population` now owns this package. User resumed the world plan.
Saved forearm/cuff geometry remains intact. `fit_stride_arms` now fits alternating
bent-arm counter-swing for walk/run to the actual shortened skeleton. The complete
atomic three-LOD build is running from source, including sole and apron fitting.
Current review receipts are stale until regenerated from those completed bytes.
First rebuilt GLBs passed Khronos at all three LODs, but actual run front/side
review still rejected the high elbow plane, open hands, belt/apron intersection
and trouser/boot cuff notch. The floor audit isolated a terminal pinky tip at
-6.85 mm; the old toe defect is gone. A second complete build now fits lower
counter-swing wrists and relaxed fingers, matches belt weights to the apron,
tucks trouser hems inside their boot mouths, and fits actual hand skin to the
floor. `inspect_garment_clearance.py` now also measures nine-clip boot/hem contact.
Open visual checks remain the apron waist, run arm/shoulder shape, boot cuffs,
nine-clip ground contact and terminal death posture. No character is approved.

Root accepted the second revision's rounded shoulder/arm plane as a bounded
correction. Its run revealed a hammer/forearm intersection and unsupported lace
segments. The third source revision now places a flat-strapped hanger behind the
hip, projects complete lace curves onto the boot, matches tucked wool to the
boot's mixed ankle field, and wraps the belt around the true exterior hull.
Idle now uses fitted relaxed arms. Reachable asymmetric hand targets replace the
overextended death target; actual skin contact fitting remains active. The first
boot ray audit correctly remains failing until these new bytes are checked.
Apron audit component selection now separates the belt that shares its joint.

Revision c passed the LOD0 nine-clip floor/deformation limits (minimum surface
height +0.48 mm, worst material p99 1.78, maximum edge extension 44.9 mm).
Run hem/apron checks reported no penetration, with at least 5.1 mm boot/hem gap.
Root retained the fitted laces and rear-hip hanger, then identified discontinuous
neck straps, protruding side piping and the rear shirt hem. Revision d is now
building a continuous fitted neck loop, closed evaluated-panel binding and tucked
shirt hem. `surface_bindings.py` samples exact finished-cloth skinning weights
for the loop, binding and belt; no contact/deformation tolerances changed.

## Checkpoint boundary — 2026-09-09

Revision d completed its atomic source/three-LOD export. Package edits are frozen
for root checkpoint staging. No build or render remains in progress. Its current
binary review reports are stale and confer no approval. The completed build's
new run apron fit reached 75.9 degrees after the shirt tuck, so inspect and correct
the apron pattern's waist ease before accepting the continuity revision.

Next mandatory correction: `fit_prone_contact` currently selects hand vertices
with any nonzero hand-group weight. A retained 0.0006 cross-hand influence made
the left hand react to the unfitted opposite hand. The isolated probe in
`review/probe_hand_contact.py` confirms this. Use majority hand membership, settle
both actual hands on the floor, and review the terminal pose. The new exported
`handHeights` gate requires both terminal hands to settle; it is intentionally
not satisfied by merely keeping the character's overall lowest point above floor.
Continue with current GLB continuity renders and all-three-LOD/nine-clip audits.
All derivatives remain drafts; accepted bounded arm/cuff/hanger/lace corrections
do not constitute full-character acceptance.

2026-09-08: `/root/orvr_simulation` owns this package's morphology, animation and
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
The final-overlap exports passed those three-LOD checks. The root agent accepted
the bounded forearm/cuff correction, not the full dwarf character.

`review_inhabitants.py` now poses by exact seconds and frames only meshes bound
to the character rig, excluding Blender's unrendered bone widgets. It includes
front/side forearm and walk/run close views. `inspect_export_motion.py` checks
literal keys and midpoints across all nine clips. It exposed nearest-vertex
garment weight jumps and contact problems in the inherited human clips.
Garments now retain the source vertex weights, relaxed with their cloth surfaces.
`tailored_locomotion.py` fits stationary and airborne ankles, samples source poses
before inserting keys, lowers the pelvis when shortened legs cannot reach their
planted targets, and authors compact defense/throw/cast hand targets. A local
`apron_lower` bone folds the actual panel at its waist seam during the prone fall;
the canonical core rig and nine clip names remain unchanged. This revision is
still under active inspection.

`export_tangents.py` repairs only undefined zero exported tangents from adjacent
UV derivatives and records exact changed vertices and hashes. All three LODs
passed Khronos with no errors or warnings before this motion revision. Do not
publish a previous review report against changed GLB hashes. Existing head-only
and side images are older and must be rerendered before final approval.

Remaining: inspect the final cuff/arm views and all-LOD audit reports, then obtain
the root agent's visual decision before extending the same retained pipeline to
the remaining Empire farmer/herbalist, High Elf scout, Greenskin peat worker and
Dark Elf supply officer. Those roles need their own fitted equipment, grooming,
body proportions and movement review. They must not inherit dwarf-only offsets.
## 2026-09-08 motion review, in progress

The retained forearm/cuff correction remains accepted as a bounded change. The full dwarf is still draft and must not be published.

The a6557148f564 LOD0 export passed Khronos and every material's nine-clip p99 deformation gate (worst 1.78). The death boot cuff twist is resolved. Exact-key/midpoint floor inspection found a remaining 58 mm toe penetration at 0.68 s in death; actual evaluated sole fitting is now rebuilding. This is a transition defect, not the old terminal buckle/apron penetration.

Actual neutral-light LOD0 run image reveals the raised knee clipping through the lower apron. This was not detected by the edge-stretch audit. The lower apron hinge must lift forward with the gait, followed by a garment/leg intersection check and new actual motion renders. Do not approve the current run image or copy this flaw to other roles.

The cast render preserves sleeves and wrist volume; terminal death retains folded apron and continuous sleeves but reads like a prone brace. Review the final terminal posture and resting head/hands alongside the nine-clip sheet.

Next: complete current sole-fit build, fit apron clearance, rerun all-LOD actual GLB motion/contact and arm-volume audits, inspect current nine-clip sheets and live AnimationMixer page. Frozen frontier siege/caravan assets and all global runtime/catalog files remain untouched.
