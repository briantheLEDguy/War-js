# Farmer work state

Current: revision f is published as Edric Hayward in Sunmeadow and in the GM
builder. Actual local gameplay confirmed visible LOD0/1/2 at 6.2/45.2/100.2m;
see `review/runtime-integration-20260920.json`. Frozen publication release:
`releases/frontier_sunmeadow_empire_farmer/623facce78792ef7cab7`.
The five current-byte gates passed on 2026-09-20. All three GLBs have zero Khronos
errors/warnings, nine clips, 849 full-motion samples per LOD, positive minimum
floor height (+1.286 mm), closed/full-volume arms, no trouser/boot penetrations
or edge crossings, and closed sole welts. All 48 generating input hashes match;
the editable master and 22 packed images are retained.

Thirteen actual-export views are inspected, including front/run/death across
all LODs and LOD0 head/side/rear/run_side. Use `_review_f.json` receipts or the
canonical copies. `review/technical-readiness.json` records exact final hashes,
metrics, scope and limitations. The corrected boot inspector sections actual
exported triangles so sparse LOD2 vertices cannot bias its reference ring;
post-build inspector hashes are separate from the unchanged generating inputs.

Root completed publication, game/GM integration and bounded local browser
checks. Full network campaign acceptance remains open. No geometry or optional
cosmetic changes remain in this handoff.

## Historical diagnostic notes (superseded by revision f)

2026-09-20 — Active original farmer derivative. The initial editable master and
three complete nine-clip GLBs are saved (132450 / 76820 / 35760 triangles), all
with zero Khronos errors and warnings. The actual LOD0 arm audit measured 224
poses, 0.9939–1.00001 section-area ratio and complete circumference. The first
literal all-clip motion report has no floor penetration, but terminal hands
remain 25–26 cm above the ground; this is a failed contact result, not readiness.

Actual GLB front, side, head, run and death renders exposed the upper braces
being attracted to the shirt lining. Revision b now uses the exterior cloth and
direct front/back/top projection, measured belt contact for equipment hangers,
human fall height and wrist targets relative to actual shoulders. It also fits
the sclera to the complete eyelid opening and relaxes the farmer's brows.
The second complete source/export build is running. Existing audit receipts
describe the first bytes and must be regenerated after it completes.

The package remains draft and must not be published until the actual exported
contact, deformation, garment and three-LOD checks pass.

Revision c fixed torso, hand and actual sole support, all +4 mm in the terminal
death pose, but the full actual-mesh audit rejected a knee at -66 mm during the
fall. The source solver now extends the prone leg until the actual trouser knee
clears the ground, preserving the downward anatomical knee pole. Revision d is
building; it remains draft until the new exports pass every contact check.

The run boot check also exposed a checker limitation on unchanged c bytes: a
rigid shin-axis ray origin can sit outside the blended boot shaft, so its first
hit is an entry wall. The checker now derives each ray origin from the actual
exported boot ring at that hem height, requiring a complete ring. The unchanged
run then measured 159/159 covered hem probes with a minimum +2.80 mm clearance.
The existing 2 mm penetration limit is unchanged; complete all-clip evidence
must still be regenerated against d.
