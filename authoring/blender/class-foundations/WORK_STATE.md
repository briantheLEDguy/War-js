# Class-body authoring checkpoint — 2026-10-10

Run `anatomy-v10` contains 48 rigged draft bodies: all 24 canonical classes,
male and female, across six races. All 48 pass raw anatomy/export checks,
the derived atlas/static-bend checks, and six supplied-motion diagnostic clips
at 17 samples each. The derived bodies use 36,994–40,052 triangles, three
material draws, the 56-bone canonical skeleton and at most four normalized
influences. This source checkpoint precedes the native development installation
recorded below; final art and production acceptance remain open.

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
armor/body masks, moving equipped combat, foot locking,
LOD1/LOD2, performance and Windows/Linux/macOS/Steam acceptance remain open.
The fit envelope reserves space; it does not prove armor clearance. Source-pose
diagnostics hold the pelvis fixed and do not approve locomotion or native clips.
The source-authoring checkpoint itself changed no native roster or Content.

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

The earlier stopping point preserved source drafts for the T1 chat. The owner's
subsequent request to push the characters to the main build authorizes the
separate native installation below.

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

## Native main-build follow-up — 2026-10-10

The owner requested activation in the main build. All 48 selected bodies now
have separate native meshes, skeletons, supplied animation sets and stable
playable identities. The roster uses all 48 hash-bound revisions. All thirteen
previous import entries, NPCs, capitals, terrain and startup-world settings are
preserved. Generated packages remain ignored/private; reproducible tooling,
roster configuration and [native evidence hashes](native-checkpoint.json) are
tracked separately from the original source checkpoint.

All 48 pass FBX roundtrip, 56-source-joint bind parity and native raw/compressed
pose checks. Native skeletons additionally retain four attachment nodes and the
armature ancestor. Equipment checks pass at 30 Hz; both Prelate palm/support-arm
fits preserve segment lengths. Agent inspection covers 304 native body/mouth
frames. Mouth closeups hide equipment for visibility; body frames retain it.

Ordinary development login passes for every class/body in two temporary
realm-fixed PIE sessions: correct own mesh, native animation instance, possession,
login closure and no arrival-floor fall. No map or persistent character is saved.
This entry proof does not approve movement quality, combat or production play.

The six retained equipped careers have separate per-body recipes; the remaining
eighteen careers currently use basic supplied states without equipment. Armor
fitting/body masks, remaining equipment and choreography, moving equipped combat,
foot locking, final facial/hair/material polish, LODs, performance and platform/
Steam acceptance remain open. Agent development admission is not human art approval.

Current verification:

- Six focused TypeScript cases / seventeen Python fixtures pass.
- Unreal tooling suite: 599 tests across 120 files pass.
- Full repository suite: 1,229 pass; the existing citadel topology wrapper times
  out at its unchanged 75-second limit. The later Unreal suite includes a passing
  citadel run, but does not make the full repository run green.
- All three typechecks, 33-zone and 906-record model validation pass.
- Installed-content audit passes; strict release check exits 1 with four blockers.
- Editor/runtime modules build successfully; all 48 ordinary entry selections pass.
- All 153 native Foundation tests pass, including revised source identity,
  female ability resolution and unloaded equipment-path reset coverage.

Local native receipts are under
`artifacts/unreal/class-character-native/anatomy-v10/`; build/test logs are under
`artifacts/unreal/class-characters/`.
