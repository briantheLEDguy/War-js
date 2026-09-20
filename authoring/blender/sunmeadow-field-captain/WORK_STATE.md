# Sunmeadow Empire field captain

2026-09-20 — Active bounded authoring package. Own this directory only. Root
owns publication, game/GM registration and the existing NPC's placement. The
scout package has transferred to root and must remain immutable.

Target: existing Corren Vale, Tier 1 Campaign Marshal,
`sunmeadow_march_marshal`, adult male Empire / Aegis guard at (-419,-239), rotY 0.
Identity, role and location remain unchanged. Exact asset identity is saved in
`character-contract.json`.

Use the reviewed male `civic_humanoid_v2_m` anatomy/rig foundation retained by the
published Empire farmer pipeline, with literal GLB, QC, editable master and quad
surface hashes copied into this package. Keep adult male limb volumes and the
same coherent anatomical mapping for cloth, hands, feet and skeleton.

Design: an original navy field shirt, fitted russet brigandine with restrained
steel articulation, practical dark boots, readable pale-gold Aegis field
insignia, and a purpose-built belt dispatch case/tool sheath on actual hangers.
Construct explicit garment panels, section lofts and shaped sweeps, with no
primitive replacement models. Preserve the working front of every seam and
physical support of equipment throughout the fitted nine-clip pack.

First milestone: retain and measure the exact male foundation and scaffold the
source/export/contact pipeline. Then save the editable uniform and inspect early
rest/run exports before committing to all-LOD acceptance. Protect reduced boot
topology from the outset; a clean sole/hem check alone cannot prove a closed shaft.

Required final gates: current-byte source and export evidence, three real LODs,
packed editable source/final masters, embedded PBR, all nine fitted clips, actual
garment/layer/boot/arm/deformation/contact/attachment checks, six actual GLB views
per LOD and gameplay-scale views. No modular armor, draw gameplay, runtime
collision/navigation or network verification claim is implied by authoring.

Foundation milestone: the retained GLB SHA is
`2e8d9d2f93abafc48218f6aa9fac7a61f451822f4805d635b8375a7e0fbfd7af`;
quad cage SHA is `9e36be7bb14d94e0f71cf6754644aa4e57e4f0177c0f3f28123986a64dd806fc`.
`review/male-foundation.json` measures 1.859999 m height without scaling and
retains all bone dimensions. The editable foundation/QC and 26 source-helper
origins are recorded separately in `foundation-provenance.json`.

Revision A full build is running (Blender background, two threads). Its prefit
master is saved and both 81-row shoulder bridges pass the source route check:
maximum step 18.94 mm, width 45.09–54.12 mm, maximum turn 13.82 degrees. The
original fitted russet brigandine, three small separated steel shoulder lames on
a fitted pad, Aegis shield/rising-ray badge, dispatch case and tool sheath have
31 explicit source contacts (bridge corners, case-hanger corners, pad and lames).
All final actual-GLB contact/deformation gates remain pending.

`export_tagged.py` now protects the exact LOD1 boot topology/weights in LOD2
before export; its per-LOD receipt records that source master and exporter hash.
The direct actual-GLB boot comparison test protects this policy. The captain
uses `_CAPTAIN_PART` semantic IDs. Layer checks are explicit separate
`layer_clearance` reports alongside garment/tool clearance. Final review requires
head/front/side/rear/run_side/death:2 plus a perspective gameplay-scale view for
every LOD. The copied checks have been adapted to male scale 1 and the captain's
actual pieces, but cannot pass until actual exports/reports exist.

Revision A build and tagged export completed. Actual three-LOD counts are
149,882 / 86,930 / 44,915 triangles; all nine clips are embedded in each. Khronos
validation reports zero errors and warnings in all three models. The direct
actual-GLB test confirms LOD2 retains the exact LOD1 boot triangles, winding and
skin weights. These checks do not establish visual or deformation acceptance.

LOD0 actual import views, full motion sweep and early outfit/contact diagnostics
are in progress. Status remains draft pending all current-model gates and visual
inspection. Do not mutate generating sources while those receipts are measured.

Revision A inspection: all seven LOD0 actual GLB views were inspected. Continuous
shirt, rounded limbs, joined brigandine bridges, shoulder lames and boots read
coherently; no cosmetic iteration requested. Nine-clip motion has no below-floor
geometry; run wrist swings are 451 / 439 mm, minimum elbow flex 51.7 degrees.
Settled death hands, soles and torso support measure about 4 mm above the floor.
All 31 physical attachment contacts remain within 4.111 mm in the full sweep.
The 224-sample arm volume gate gives area ratios 0.99390–1.00001 and actual male
reference span ratios 0.999998–1.000660. Boot surfaces are independently closed
two-manifold meshes in every LOD, now asserted by the direct binary test.

One real draft issue is open: the dispatch case grazes the animated rear thigh
during run. Early diagnostic samples measured 11 crossing edges and 0.428 mm
penetration. The full layer/garment/equipment sweep is collecting the worst pose
before a narrow suspension-clearance correction. Do not treat A as approved.

## Paused for the user's checkpoint

Root requested the current part be wrapped and all work committed so the user
can change focus. No new model iteration was started. The remaining full outfit
sweep was interrupted through its own exec session after completing melee,
ranged, cast, combat-idle and death work; it did not write a final complete report.
No captain process remains running. All current editable masters, three GLBs,
partial diagnostics, seven LOD0 views and checker sources are saved. No shared
maps, registry or other packages were edited by this captain task.

`character-contract.json` remains `runtimeReady: false` and the separate technical
readiness file explicitly records an incomplete WIP. Do not publish this draft.
The four focused source/foundation/shoulder/boot topology tests pass. The complete
13-test gate has not run because several final reports and lower-LOD reviews are
missing. The test tool gained the stronger all-LOD closed-boot assertion after
the export; the original generation snapshot is retained unchanged. A future
export and validation-input snapshot must record the then-current checker bytes.

Exact saved SHA-256 values:

- Contract: `9f512065b861f2e53d8f68079548772b5eae322a49e850fdeacfbcb842d4d9cd`
- Editable tagged master: `484ed6e3f27514f3d685d1ab3f4df63a5e0be83e294e038c97d1785edf8f3eec`
- Editable authored master: `bb1ad20be71a419b713972896038d3b7915e267e3735cb20aa37d90f65fa7e04`
- LOD0: `eae89f5b537468b052a3ed68b9928baee2ad9d014dd4454a4baf9ca58558e29a`
- LOD1: `661a4dc6be7eab27735a5018d25f51594146ff0237517393680faf6287f8ed8c`
- LOD2: `e31f74f1ad46284ec53c3c2eaed03f4df90ac76617b72408e8a0835073cf3b42`

Resume only when requested:

1. Measure the full case/body sweep; fit the dispatch case clear of the moving
   thigh by a small physical placement/suspension correction. Preserve all four
   hangers' measured belt/case endpoints. No correction has yet been applied.
2. Rebuild and re-export after a source change; do not reuse old-hash reviews.
3. Run every per-LOD arm, motion, boot, welt, garment, layer, tool and attachment
   check. Run current master/shoulder checks and zero-error GLB validation.
4. Render and inspect all seven required actual import views for all three LODs.
   Retain exact validation inputs, then run the full read-only technical gate.
5. Hand the proven package to root for publication and actual game/GM placement
   checks. No runtime, collision/navigation or network verification is claimed.
