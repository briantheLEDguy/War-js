# Herbalist work state

## Published September 20

Root published frozen L release `63072b851393b42f4329` as existing Serra Brightfield
and in the GM builder. Actual Game/NpcSpawner checks verified all three visible
LODs at 6.2/45.2/100.2m and grounded placement on the 86mm shelter floor. Nine
technical gates pass, including zero all-clip belt/cloth crossings. The runtime
integration receipt retains exact hashes and limits. Full campaign/performance
acceptance remains open. Entries below preserve the authoring history.

**Current: revision l is technically verified and frozen for root publication.**
All nine export gates pass after lossless compaction of 24 current reports.
All 18 current-import views are inspected. Editable master and exact source
ledger are retained; runtime/public/GM/map changes remain owned by root.
Use `review/technical-readiness.json` and `publication-contract.json`; older
entries below record superseded iterations and must not be treated as current.

2026-09-20: isolated authoring started. Not runtime-ready. Female civic anatomy
and farmer revision f fitted garment/contact workflow retained by exact hashes.
Design: cream linen shirt, sage divided working oversmock, practical trousers
and boots, gathered hair, properly suspended satchel and herb/vial equipment.
Original published packages remain immutable. Root owns all publication.

Next: adapt original female head/groom and garment cut, build packed master and
three GLBs, inspect exports and run full arm/motion/garment/tool/contact gates.

First authoring pass saved: original fitted sage torso/shoulder bridges and four
divided smock lappets, gusseted satchel, supported medicine cups, ceramic vials,
corks, shaped herb leaves/stems, fitted female scalp and gathered braid. The
first complete build is baking actual leg/arm/sole contact before export.
Mandatory added reports: master-continuity, garment_clearance, tool_clearance.
No readiness claim before actual GLB inspection and all gates.

Revision a exported three valid GLBs (154342 / 89517 / 41671 triangles), zero
Khronos errors/warnings. Actual front/head/side/rear/run/prone images inspected.
It failed outfit checks: up to 125 mm edge extension at armhole bindings,
13.5 mm prone smock floor penetration, and actual smock/underlayer crossings.
This is not a publishable result.

Revision b is building: exact projection fields for oversmock panels, bound
edges inherited from their own supporting panels, lower armholes and a torso
field for shoulder bridges; belt hull wraps completed smock before equipment
is fitted; prone support measures the real smock torso and dressed knee hems.
Panel winding is corrected. Eyebrows and a compact connected braid complete
the retained female face. The arm thickness gate compares actual sections with
the female quad foundation, with unchanged pose-area/closed-section criteria.

Revision b passed all nine LOD0 motion/contact checks: floor +2.97 mm,
terminal hands/soles/torso +4 mm, maximum material p99 stretch 1.723 and edge
extension 28.45 mm. It remained blocked by real side-smock/shirt crossings,
and actual imported rear/run views showed unsupported shoulder-bridge ends
and a floating groom knot. No readiness claim was made.

Revision c is rebuilding from the corrected source: radial 25 mm smock ease,
longer bridge ends joined into the smock, brows located from the actual female
eye meshes, and braid/tie points fitted to the actual head surface. Nearest
edge normals in the clearance inspector are ambiguous at thick garment hems;
those edge cases now use closed-cloth ray parity for sign. Actual crossing
checks and the 2 mm penetration threshold are unchanged. Current-byte audits
and imported views will determine readiness.

Revision c's current imported front/head/side/rear views confirm supported
brows and groom, joined bridge ends and full limbs. Its two-clip clearance
probe still found upper sleeves entering the smock during run/fall. Material
and bone-weight witnesses identified the sleeve, rather than the hidden torso.
Carried gear had zero crossings and at least 28.9 mm clearance. A diagnostic
pose probe removed the run intersections with an outward elbow pole and the
fall intersections with a wider intermediate bracing reach. Revision d bakes
these targeted motion changes; final hand supports remain unchanged. Other
seven clips are being checked concurrently. The package is still not ready.

The seven-clip audit found additional upper-sleeve contact with the outer
shoulder straps/bib during melee, throwing and casting. Revision e recuts the
armholes deeper and brings the shoulder straps onto the clavicles, with a
14 mm radial smock allowance. The run/walk outward elbow pole and intermediate
fall bracing adjustment remain. Five stressful clips are now being audited.

The equipment attachment probe found all four suspension loops connected to
both belt and payload, with exact triangle crossing witnesses, and both vials
supported by their holders. New per-LOD equipment_attachment evidence checks
closed loops, fifteen load-path contacts and all actual posed assembly vertices
against their shared rigid hips transform (10 micrometre residual limit).
Revision f extends each herb stem down to the actual inner satchel floor;
previous roots stopped at the opening. This is the only f geometry change.
All work is checkpointed locally; readiness remains false until all gates pass.

Revision g moves the shoulder strips clear of the collar opening and gives
those strips their exact supporting-shirt skin fields. Imported front/rear
views show attached straps and groom; the new positive cloth clearance in
ranged/cast/idle is about 4.3 mm. A remaining melee sleeve graze occurs only at
the inward punch peak. A current-export pose probe eliminated it with 40 mm
outward wrist travel. Revision h reduces the inward punch term by 75 mm at its
peak, with the same smooth envelope. Geometry is unchanged from g. Full matrix
checks and exact-byte views follow; this is still not a freeze/readiness claim.

The coarse LOD probe additionally passed female section preservation (reference
span ratio 0.9974-1.0058, animated area ratio 0.9936-1.0019), zero boot-hem
penetrations/crossings and two closed welts (maximum distance 3.24 mm).
These probe receipts will be replaced by exact final-GLB reports before handoff.

The full g outfit audit finished: only melee (the already diagnosed punch)
and one strip edge in run/walk still crossed. The strip's directional-ray
switch had produced a 69 mm chord between distant supporting shirt patches.
The h bake was interrupted before its master/export stage. Revision i replaces
that switch with continuous nearest-surface strip fitting and exact underlying
shirt fields, and includes the corrected punch. No contact tolerance changed.

Full g motion remained sound: floor +2.969 mm, maximum p99 stretch 1.723,
maximum edge extension 28.45 mm, and terminal hands/soles/torso all +4 mm.
The coarse g LOD2 attachment probe also passed all fifteen contacts, four closed
loops, and a maximum actual-pose rigid residual of 0.235 micrometres. Final
revision i reports and current-byte rendered views are still required.

Revision i exported valid GLBs, but the early actual-LOD audits found that
nearest-surface fitting could still choose the open neckline rather than the
clavicle; the offending strip vertices moved inward to x=81 mm. The unfinished
full-matrix jobs were stopped after recording this failure. Revision j restricts
strip support to the actual shoulder patch outside the neckline, preserves the
original supporting triangle indices for exact weights, uses denser stations,
and a 9 mm cloth offset. The strip remains a real fitted garment, not an exempt
contact region. All prior clearance and volume limits remain unchanged.

Revision j passed sparse preflight but full key/midpoint sampling exposed brief
melee sleeve crossings at peak reach; it is not ready. The complete 61-pose
actual-import diagnostic removes all crossings with a 90% anatomical arm-reach
cap and outward elbow pole (1.6). No extra wrist translation is required.
Revision k applies that bounded action-arm change; geometry is unchanged.

The coarse fall negative face-normal sign was independently disproved by
three exact closed-cloth parity rays (4,4,0 intersections, all outside), with
zero BVH overlap pairs. Cloth signed distance now uses majority containment
for every negative nearest-face sign. The 2 mm penetration allowance and zero
actual surface-crossing requirement remain unchanged. Final current-byte full
reports and inspected views are still required before freezing.

Revision k is the current saved master/export set. All three GLBs have zero
Khronos errors/warnings and all nine clips. Complete 849-key/midpoint garment
and tool matrices now have zero actual surface crossings at every LOD.
Minimum garment gaps: LOD0 5.189 mm, LOD1 4.410 mm, LOD2 2.661 mm.
Coarse LOD has completed all numerical reports and actual-import inspection
of front/head/side/rear/run_side/death:2. Higher-LOD remaining boot checks and
views are finishing; runtimeReady remains false until the complete final gate.

Current k GLB SHA-256:
- LOD0 34d9bb9ba86084b36b2dd0fa8bd1c7750d2e2518efe82302c4a06c0ab277ae75
- LOD1 4de277bf97c877216a8b9d5325898504fad2c01755bca7eb517c5ecc743808fa
- LOD2 1e448f82a62ba1b7986a2c74fbff239ea70711e17290d6ed770abd5a6fd8c217
Master: 7f4ae17b0d1cf4ffdc7bd6bfd4871fb5139f079dff51eecec2541b95588a7267

K remains withheld despite passing the eight existing gates. Root spotted rear
cream slivers at the belt. Actual ray witnesses identify smock edge binding
up to 3.76 mm in front of the belt, not an exposed shirt gap. The belt sampled
only five horizontal sections and omitted narrow top bindings between those
levels; panel-top leg/spine weights also lacked a firm waist attachment.
Revision l gives the tucked garment band a common hips anchor with a smooth
65 mm blend into free cloth, and fits the belt to the entire 46 mm vertical
slab including its bound edges. Leather retains 6 mm thickness and a 6 mm
cloth gap. An additional exact-export belt-layer gate is required before freeze.

Revision l exported cleanly with zero glTF errors/warnings. All three new
belt-layer reports pass 849 actual keys/midpoints, zero triangle crossings
and minimum inner clearances 3.865/3.864/4.067 mm. All 18 exact-current L
front/head/side/rear/run_side/death:2 views were inspected and their image/model
hashes verified. Root inspected the L rear and requested no more cosmetic
changes. Separate ray classification identifies the cream triangles below the
belt as underlying shirt in the rear working-slit opening, not penetration.
K failure image, ray witnesses and failing belt gate remain saved. Superseded
preview sets were removed; final L previews are retained.

Current l SHA-256: LOD0 59af5a498f94fb87c359e6bf1e3bbc90e16fa73f32a145abc6af65b66767507d;
LOD1 d9236e264cb0861ff7aafce695c0c6f95a53ac72e5f90ceac54e4d7c47ad2928;
LOD2 8f750f1e399d0cf86081677cb1b1fbd7aa43385611699c1bd43f65c0ae77e0cf.
Remaining before freeze: complete legacy numerical chains, lossless audit
minification, the complete nine-test gate and final technical-readiness receipt.

Final freeze: no known failed checks remain within the documented scope.
Root may publish with `--package=sunmeadow-herbalist --review-suffix=_l`.
The K waist-layer failure and L correction witnesses remain retained.
