# Sunmeadow High Elf patrol scout

## Published September 20

Root published frozen K/corrected-LOD2 release `d12b92a97fb9806ee882` as existing
Mira Stonewake and in the GM builder. Actual Game/NpcSpawner checks verified
all three visible LODs at 6.2/45.2/100.2m. Thirteen technical gates pass; full-width
shoulder seams attach through all clips and the reduced boot surface is retained
without the shaft split. The runtime integration receipt records hashes and
limits. Full campaign/performance acceptance remains open. Entries below preserve
the authoring history; draft readiness statements are superseded by this delivery.

2026-09-20: bounded character authoring complete. Final K source plus retained
LOD1 boots in LOD2 passed all 13 final package gates. All 18 current export views
were inspected; all three GLBs have zero glTF errors/warnings. Ready for root
publication. Package ownership is this folder only; root owns public manifests,
maps, catalog, publication and runtime work. Contract identity remains immutable.
See `review/technical-readiness.json` for final hashes and explicit limitations.

Initial source milestone: root confirmed Mira Stonewake / Forward Scout,
`sunmeadow_march_scout`, adult female High Elf. Exact runtime contract is saved in
`publication-contract.json`. Literal female anatomical GLB, editable master, QC
and quad surface are retained in `foundations/` with hashes in provenance.
`review/female-foundation.json` measures the normalized, coherently proportioned
1.9623 m female baseline. Ankle and cuff fitting uses these female dimensions.

Final source revision K was built with Blender background and two threads.
Continuous fitted shirt/trousers, sewn suede jerkin and shoulder yokes, braided
ash-blond groom, retained ear surface morph, suspended quiver, original recurve
stave/arrows and high belt map case have been constructed. All added geometry is
surface panels, explicit section lofts or authored swept paths. Nine named clips
are fitted to actual limb/sole/hand contact. Actual GLB view, arm, garment, boot,
equipment and motion reviews are complete. Later notes below retain the earlier
iteration history and do not override this final readiness statement.

Revision B evidence (superseded geometry, not publication evidence): actual three
exports and packed editable masters exist. First revision glTF validation was
zero errors/warnings at all LODs. Close front/head/side/rear views exposed a hidden
diagonal harness and loose braid root; B corrected them and fitted brows to actual
eye geometry instead of misplaced retained eye bones. Female LOD0 arm volume was
0.99468–1.00001 of rest through 224 samples; rest thickness was 1.0000–1.0063 of
the retained female sections. Corrected run has 51° minimum elbow flex and
420–434 mm wrist swings. Early idle/run/death boot checks had zero penetrations
or hem intersections. Death contacts both hands/soles/torso at approximately 4 mm.

The old nearest-normal contact sign was invalid around an open collar: it called
an exterior arrow −138 mm inside. `surface_contact.py` now proves actual cloth
shell closure and checks parity on separate closed volumes, together with the
closed 13,380-vertex retained full anatomical body beneath clothing. All actual
exported triangle intersections remain checked. B's idle diagnostic has zero
crossings, 7.64 mm garment / 7.29 mm gear minimum gaps and a retained real body
crossing control. Separately thickened shirt/collar share seam coordinates; their
complete closed shells are resolved through their unambiguous remaining edges.

C tightens 20 semantic attachment links (harness, quiver, bow keepers, map-case
loops) to measured supporting geometry with matching root weights. Its three
finished tagged exports passed glTF with zero errors/warnings and exact integral
part IDs. Actual LOD0 imports cover all 110,415 referenced vertices with no
mixed-part triangles; LOD2 also retains all required semantic parts. Idle link
contacts were mostly below 1.2 mm, but two thick quiver-loop contacts failed the
strict 6 mm limit at 6.45 mm. D flattens their round sections into actual 3–4 mm
leather, retaining strap width and anchor fitting. This remains draft evidence.
On completion
run `tools/export_tagged.py`: it retains the authored master, adds `_SCOUT_PART`
geometry IDs and exports three finished LODs, checking that IDs remain integral
and cover every exported vertex. `inspect_equipment_attachment.py` must then
track actual identified triangles at every key/midpoint in all nine clips, with
6 mm maximum contact gap. The other topology/contact/volume gates remain separate.
All final reports and exact-current front/head/side/rear/run_side/death:2 views,
including every LOD's GLB views, remain pending. No global files were edited.

The complete C run/idle/death diagnostic found real shirt/jerkin intersections
at the side panels and a recurve/trouser intersection during the fall. E increases
the jerkin's fitted panel density and side allowance, and hangs the complete bow
200 mm higher above the hip fold. Those changes still require the complete sweep.
The retained underlying body's float32 BVH also repeated grazing hits of the same
triangle within one micrometre. The saved diagnostic isolates those false signs;
the parity ray now advances by a face-normal-safe amount capped at 0.1 mm. It
correctly classifies the exterior probes while retaining the actual buried bow
failure. All exported edge crossings remain an independent strict zero gate.

E's actual LOD0 attachment gate passed all 20 links through all nine clips with
maximum bidirectional separation 0.984 mm. All three E GLBs had zero glTF errors
or warnings. The raised bow cleared the diagnosed leg contact. Actual GLB
candidate-pose experiments showed the inherited running elbow pole folded its
sleeve through the jerkin: a wider outward elbow pole removed all intersections
at both tested run phases while preserving the hand path. Widening fall bracing
by 60 mm removed both diagnosed fall garment/body contacts. F applies those
motion changes and repeats the full fit. The geometric contact gates are unchanged.

Wider exported-pose samples also caught walking and attack/cast contacts. The
exact-triangle containment control resolved the BVH's remaining false positives
without removing real intersections. Measured candidate poses show that limiting
walking/action reach to 90% of the actual female two-bone arm length leaves room
for a natural outward elbow bend and clears those contacts. The melee stance
also moves each wrist 80 mm outward; other action targets keep their original
positions. G includes these arm-route changes. Sampled jump/combat-idle already
clear; their motion is retained. Full current all-LOD reports remain pending.

First milestone: inspect the existing Sunmeadow scout population assignment and
retained anatomical foundation; send exact proposed identity/profile/body family/
skeleton/bind contract to root before relying on it. Then retain literal source
hashes and construct an original complete fitted scout outfit and equipment.

Required handoff: three real LODs; packed editable source/final masters; embedded
PBR; nine fitted locomotion/combat clips; actual exported front/head/side/run/death
views; independent arm-volume, garment, boot, suspended-equipment and full-motion
death/ground-contact gates. Arm references must use the retained race/sex-appropriate
anatomy, never a dwarf/Greenskin minimum. No primitive model construction or proxy
publication. Standing user approval does not bypass technical acceptance.


G's current LOD0 nine-clip motion gate passed: lowest surface 2.566 mm; run elbow flex at least 51.47 degrees; wrist spans 420.4/433.9 mm; final hands/soles/torso approximately 4 mm. All three LODs passed retained female arm-volume measurements and completed the 20-link nine-clip attachment sweep. G close head review exposed shoulder-yoke guides catching the cut neck opening; H routes the yokes and over-shoulder harness farther outside that boundary. This changes actual geometry and requires fresh exports/reviews/gates. The G full outfit check continues as a motion diagnostic.

Complete G LOD0 outfit sweep: all equipment clears all nine clips; all garment clips except death have zero crossings and >=7.15 mm gaps. Death still has shallow sleeve/jerkin crossings during 0.83–1.07 s, under 2 mm. Actual imported-pose tests show +90 mm temporary outward bracing clears the entire diagnosed interval with >=6.8 mm gaps. After H source/render checks, add a smooth brief extra brace envelope around that fall interval (preserve the existing final prone pose), then rebuild/re-export and rerun complete gates. No final acceptance yet.

H's actual head reimport showed the shoulder strip still kinked at its projection-direction switch. I uses a continuous radial shoulder projection, with the guide outside the neck opening, removing that discontinuous front/down/rear sampling. I also adds a 90 mm sin-squared bracing envelope only during source frames 20–38 of the fall; the final settled pose is preserved. Source changes were made after H export completed, preserving literal generation provenance.

The retained H source control confirms the projection defect (172 degree turns, 42–65 mm row jumps). I prefit actual strips measure 23–35 degree maximum turns, 16–17 mm maximum steps, and 32–40 mm widths. New inspect_shoulder_routing.py measures paired-edge authored geometry; the final read-only test now requires its current-master report in addition to actual GLB contact and views. Final report must be regenerated after tagged export; the current normal report is still the H negative control.

I completed and was tagged/exported. Current LOD0/1/2 hashes: b316eb47014c171323f503626ccda65c6fee7c7f71b10559b4b288dfa67807de / f9437b25bf521e981860fa05731b35dea3961f0528ad6f4aa1eb96f0b79e0d66 / b0954eb87d9576b352ae2522ade0448296699774614742dcb912fd80ad581d3b. All three glTF validations are zero errors/warnings. The eight sampled fall times now have zero crossings and positive clearance (minimum 1.598 mm). Full LOD0 outfit check, sequential LOD1/2 outfit checks, all-LOD attachment/motion/arm/boot/welt queue, and LOD0 six final renders are running. Final source continuity/master reports were regenerated. All source/checker code must remain stable during these checks. Do not promote until full reports pass and all three LOD renders are inspected.

Root's I rear/side review found the green jerkin shoulder bridges ended above
the rear panel. Actual retained-source measurements confirm 40.64/40.70 mm gaps;
smooth routing alone did not establish attachment. J extends both front/rear
guides onto the jerkin and binds four actual terminal seam links to its finished
surface and weights (24 attachment chains total). Denser authored bridge rows
preserve the existing continuity limit. No unrelated cosmetic changes. Existing
I inspections are allowed to finish before J overwrites input models/anchors;
all J acceptance reports and six views per LOD must then be regenerated.

J's full-width source check found one rear corner on each bridge still 10–11 mm
above the sloped rim despite the center joining. J was not tagged or accepted.
K extends the rear ends another 30 mm in the nominal guide and independently
fits both terminal corners to the jerkin with its local skinning weights. Eight
explicit corner contacts augment the four seam centers (32 total attachment
links). The retained K geometry proposal measures all eight corners at 1.000 mm
support separation, maximum row step 17.99 mm and maximum turn 25.93 degrees.
These remain preliminary source measurements; current-export all-LOD/all-clip
attachment, clearance and visual evidence is required after K finishes.

K tagged exports are complete: LOD0 a0d2983891f6fb3433d875362a29b563b46d846efe6c1875f98c4fd75ff0fdca
(168246 triangles), LOD1 6c0e68618edfd8bf50c7da6c1f413828fab2c8a3ff458e2cc3e7f87497b91ed8
(97542), LOD2 181603c6c98c944cff848774578a421645016272e52ae12ce94048447a3c847a
(45356). All three glTF validations have zero errors/warnings. All six current
LOD0 reimport views were inspected; root also confirmed rear/side bridge joins
with no further cosmetic changes. LOD0's 32-contact nine-clip attachment check
passes, maximum bidirectional gap 0.983 mm. Full outfit and remaining LOD numeric
checks/render sets are still running. Do not freeze acceptance until complete.

The complete 18-view review caught a real LOD2 run-pose boot-shaft split created
by aggressive reduction. K LOD0/1 are clean and remain byte-identical. The bounded
`retain_lod2_boots.py` finishing operation retains the literal pre-repair LOD2
master and imports only the two reviewed LOD1 boot parts into the editable LOD2
master, preserving its rig, nine clips and all other reduced parts. Build receipt
`bootRetention` records both source masters and this exact tool hash. Final LOD2
is now f821a8b3ae07c3d3d368fbe12eafbc1f0e500a510d0232d21f3700fba15c452f,
49336 triangles, with zero glTF errors/warnings. A new read-only gate compares
actual GLB boot triangles, winding and skinning exactly against LOD1 and passes.
The previous LOD2 views/reports are invalid for this new hash; all six views and
attachment/motion/volume/boot/welt/outfit gates are rerunning for LOD2 only.
