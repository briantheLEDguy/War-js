# Class-body authoring checkpoint — 2026-10-10

Run `anatomy-v10` contains 48 rigged draft bodies: all 24 canonical classes,
male and female, across six races. All 48 pass raw anatomy/export checks,
the derived atlas/static-bend checks, and six supplied-motion diagnostic clips
at 17 samples each. The derived bodies use 36,994–40,052 triangles, three
material draws, the 56-bone canonical skeleton and at most four normalized
influences. None is native accepted or runtime eligible.

The local deliverables are in
`artifacts/unreal/class-characters/anatomy-v10/`. Open `review.html` for all
class/body and face views, five static bends, supplied-pose midpoint and worst
frames, GLBs, rigged Blender files and live fitting sources. `race-lineup.png`
compares six representative male bodies at the same metre scale. Binaries stay
ignored; `checkpoint.json` here retains measured results and evidence hashes.

The complete fitting masters preserve MPFB's 19,158-vertex live fitting mesh.
Runtime candidates strip helpers and use welded-source weight transfer so UV
seams receive identical weights. The four male Dwarf bodies use source-bound
fixed weight corrections on 16–29 vertices; their largest individual change is
under 2.4 percentage points. Bones, rest surfaces and proportions stay fixed.
Earlier failed iterations remain local for comparison.

Use the [authoring workflow](../../../docs/unreal-class-characters.md) for build,
refinement, pose-review and gallery commands. Sources and recipes are public;
the generated binaries are local draft outputs. A changed source requires a
new run and fresh source-bound Dwarf corrections.

Final facial/hair/material appearance, twist and facial deformation, fitted
armor/body masks, equipped clearance, native retargeting and foot locking,
LOD1/LOD2, performance and Windows/Linux/macOS/Steam acceptance remain open.
The fit envelope reserves space; it does not prove armor clearance. Source-pose
diagnostics hold the pelvis fixed and do not approve locomotion or native clips.
No active native roster, registry or private Content package was changed.

Greenskin dentition correction and review checkpoint:

All eight Greenskin bodies now select `dentition-v1/`. The earlier canines began
below the mouth and appeared attached to the chin. Roots now sit inside the
retained lower canine sockets; curved enamel crowns emerge through the lip.
The CC0 source jaw-descendant mask restores lower-face movement. Lower crowns,
gums, tongue and tusks follow the canonical jaw; unchanged dental UV islands
identify the arches independently of fitted tooth heights. Body surfaces, bone
positions, triangles and three draws are preserved.

Actual re-imported exports pass 24 jaw openings, 40 static bends and 816 supplied
pose samples. Maximum dental skinning error is below one micrometre; roots stay
at least 23 mm behind the body surface in the diagnostic openings. Inspect each
body's front/three-quarter/profile views at 0, 12 and 24 degrees in the gallery.
`greenskin-dentition-review.png` compares all eight closed mouths. This proves
attachment in those diagnostics, not finished facial acting or native animation.

The owner requested a stopping point for in-game inspection through the T1 chat.
Character iteration is stopped at this saved local checkpoint. No draft was
installed into native Content or the active roster; no native binary build or
game launch was performed here. The T1 chat coordinates its separate launcher.

Verification (dentition refinement):

- Five TypeScript cases and 12 Python fixtures pass.
- All three typechecks, Unreal audit, 33-zone and 906-record model validation pass.
- The hash-checked gallery passes with 48 bodies and eight corrected dentitions.
- Full repository/Unreal suites were not repeated at the requested stopping point;
  their preceding foundation results below remain recorded with that scope.

Foundation verification before dentition refinement:

- Character regression tests: 4 TypeScript cases and 7 Python fixtures pass.
- Repository suite: 1,219 pass; the existing citadel topology wrapper exceeds
  its unchanged 75-second limit. Its isolated retry also timed out. Do not
  report the final complete repository run as green.
- Unreal suite: 588 tests across 114 files pass.
- Application, server and Unreal-tools type checks pass.
- Unreal audit passes with release readiness false and four blockers retained.
- World validation passes for 33 zones; model validation passes 906 records.
- Strict release check exits 1 as required while acceptance remains incomplete.
- Diff/whitespace review passes; generated assets remain ignored.

Local verification logs are under `artifacts/unreal/class-characters/`.
The full-suite timeout is recorded in `tests-complete.log`; character fixtures
are in `tests-final-focused.log`. Model evidence is bound separately in the
tracked checkpoint and the local gallery.
