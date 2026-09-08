# Fauna work state

All fauna remains draft. No fauna blueprint, approval record, or runtime publication exists. The accepted canopy-v2 package is frozen and is confirmed in the game/GM builder.

Current priority is one roe deer buck through anatomy, actual exported pose, and material review. Other species proofs are not release candidates and must be rebuilt after the buck workflow is sound.

2026-09-08, active correction after visual rejection:

- Root rejected the full buck's running silhouette despite the technical pass: at phases .125-.375 the thigh pulls the belly into a bulge; at .625-.75 the front elbow folds too tightly. Head, directional coat, antler grafts and rounded cupped ears are accepted as the direction to preserve, but **the full animal is not approved**. No public fauna asset or approved record exists.
- The rejected exact GLB, source files and close side rest/worst-phase images are saved in `checkpoints/buck-rejected-gait/`. The current builder batch is `buck_range_build.log` followed by `buck_range_motion.log` and `buck_range_joint_review.log`; inspect the new close renders before a full review batch.
- Bounded active correction: front shoulder pivot Z .535→.58m (lengthens the short humerus); run hoof clearance135→81mm after scale; run body crouch reduced43→22mm before scale; continuous anterior upper-thigh support fades out so abdominal flank follows the pelvis. The head surface and original anatomical skin cage are otherwise unchanged.
- The package-local publisher and frozen release mechanism are implemented, with four evidence tests. Root raised the global prop atlas declaration ceiling to4096; humanoid2K policy remains intact. Sixteen pure atlas/texture/gait/sampling tests pass. The publisher still requires complete current visual acceptance.
- A publication integrity issue was fixed: Khronos `validatedAt` timestamps are omitted from the hash-bound deterministic diagnostic, and the actual GLB hash is included. Revalidation cannot silently invalidate an otherwise identical review because the clock changed.

2026-09-07, earlier numerical-pass checkpoint (not visual approval):

- Latest buck revision has rounded cupped ear contours, a restrained upper lid, shaped skull planes, continuous antler grafts and irregular overlapping summer-pelt strokes. Root accepted the preceding coat/skull/antler direction and requested only the ear/lid refinements, which are now built. Full current LOD/cycle visual review is rendering; do not reuse earlier image hashes.
- The new plant audit found an actual return-to-stance velocity discontinuity. Increasing bake density alone was insufficient. `gait_curves.py` now joins the constant-velocity stance with a compact C1 return; a whole-span Hermite trial was rejected for excessive airborne limb extension. Current actual-GLB plant errors pass the unchanged6 mm gate: run5.67 mm, walk0.744 mm. The rig bakes at60 fps. All three LODs again pass Khronos, strain, floor, root and loop checks.
- The derived1× playback speeds are0.345 m/s for the browsing walk and3.0 m/s for run. Old speculative speed fields were removed from the buck source. Runtime authority must use the build report's scaled stride contract.
- Sixteen focused pure regressions cover atlas boundaries, literal GLB timestamp sampling, texture normal orientation, repeatable non-lattice hair, local facial fields and continuous contact curves. Package source/module/texture/cage/master hashes and actual reimport receipts are in place. The package-local publisher/frozen source snapshots remain to be completed after visual acceptance.

- Buck LODs now contain 43,720 / 20,510 / 8,488 triangles, 37 bones, and idle/walk/run/graze. All three actual GLBs have zero Khronos errors and warnings and pass the current technical gate. They remain visually unapproved.
- Motion inspection now reads the literal exported animation timestamps and checks every key plus every midpoint, without rounding to Blender's import frame rate. All twelve clip/LOD audits pass. Worst run stretch is 2.884 maximum / 1.789 p99 across the LODs; graze 2.398 / 1.663; walk 1.823 / 1.292. Root movement and loop differences are zero. Nine pure atlas/sampling regressions pass.
- The mobile scapula and continuous anatomical skin removed the earlier recessed haunch socket and discontinuous shoulder. A shallow flexion crease remains for full-cycle visual review. These metrics do not prove joint-volume quality.
- The small gold-looking eye rim was a concrete UV defect: individual polygons interpolated between unrelated atlas islands. Eye strips and ear walls now stay within a single island; a cage-level gate and regression tests prevent that defect. The current buck eye is dark and fitted to the finished skin.
- Current rest/run/graze views still show an overly smooth coat and underdeveloped facial structure. Those are material acceptance gaps. Close anatomy/material views and full motion strips are next; no source proof is approval evidence.

Earlier experiments and implementation notes:

- The active buck revision uses a continuous fused skin from retained original anatomical cages. Several connected-quad hip openings were tested and rejected: the lower opening produced a long rump-to-knee membrane; the higher opening produced a false socket. `stitched_skin.py` remains an unpublished experiment, not the selected delivery topology.
- Three actual LODs are built; the previous continuous-skin counts were approximately 43.6k / 20.2k / 8.4k triangles. A smoother cage refinement pass is rebuilding, so counts remain provisional.
- Continuous body/limb weight fields use at most four influences without rank truncation. Distal forearm/shin influence is kept below the belly, and lower-limb fields are blended continuously.
- Wider lower-neck fields improved grazing to 2.39 maximum / 1.46 p99 stretch. Walk was 1.82 / 1.26 and run 2.73 / 1.84 on the prior continuous-skin export. The visible flexed haunch still requires review; metrics alone do not establish acceptance.
- Limb pivots now lie in the anatomical sagittal leg planes. The current build smooths the actual cage before fusion, removes the separate cream jaw strip in favor of continuous jaw-weighted skin, ray-fits a subtler orbital rim with a horizontal pupil, adds short coat relief and original antler burr/ridge detail, and shortens the excessive tail.
- The current export batch audits all three LODs and reimports rest/run/graze. Inspect its current receipts before rebuilding. A source-side Corrective Smooth experiment did not sufficiently improve the haunch and is not part of delivery.
- Remaining face/material work includes visual review of these changes, cheek and tear-duct structure if needed, and a close material view.
- Remaining technical work includes complete three-LOD pose audits, source-module/texture hashes, normal handedness tests, actual reimport contact/motion sheets, and a hash-bound package-local review/publisher. Do not approve from a passing exporter or deformation metric alone.

Commands use Blender 5.0 with three CPU threads. The build, inspection, and reimport scripts live in `tools/`; every rebuild replaces draft model bytes and invalidates prior image receipts. Root owns global registry/catalog/map integration. No questions or permission requests are needed for this authorized work.
