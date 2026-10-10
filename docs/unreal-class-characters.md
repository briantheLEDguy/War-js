# Class character foundations

The class-body workflow builds 48 independent local candidates: the 24 original
classes, male and female, using the six retained MakeHuman/MPFB race recipes.
Class physique differences stay within conservative race ranges. Chaos retains
human skin detail; no alien bio-armor replaces its anatomy. Compact Dwarfs, tall
Elves and stronger Greenskins keep the same humanoid bone hierarchy and normal
limb structure. Grooming is short, detachable and tinted by race.

```powershell
npm run unreal:class-characters -- --run-id anatomy-v10
npm run unreal:class-character-review -- anatomy-v10
```

Use `--class stoneguard --variant f` for a focused build. Reusing a run resumes
only unchanged, hash-verified outputs. A changed recipe, generating script or
model requires a new run id; the generator refuses changed inputs. The strict
local toolchain doctor checks Blender, pinned MPFB and installed pack hashes.
Generation uses existing local CC0/project sources and no paid service.

## Files and ownership

`scripts/unreal/class-character-spec.mjs` derives class requests from the existing
roster and constrains physique/grooming. `build-class-characters.mjs` runs local
Blender jobs with two workers by default (`--jobs 1` through `--jobs 4`). Each
worker owns a different character directory. `build-class-character.py` reuses
the existing MPFB body generator, canonical adapter and export/round-trip helpers.
`class_character_audit.py` measures the actual mesh, weights and joint lengths.
`review-class-characters.mjs` verifies evidence and creates a searchable local
HTML review sheet. Binaries and renders live in the ignored
`artifacts/unreal/class-characters/<run-id>/` directory.

`atlas-class-characters.py` creates a derived `optimized-v2/` candidate after the
complete body run. It refines joint transitions on the welded source topology,
protects strongly weighted torso interiors with smooth falloff, and transfers
one source weight row to every UV seam duplicate. Region-specific passes
keep bone lengths fixed and normalize four influences. It also lifts
intersecting scalp/brow cards away from skin and packs the three grooming
textures and three face-part textures into separate 2048px
atlases with gutters, and preserves repeated source UVs. The resulting three
material draws fit the retained four-draw body budget. Original fitting masters
remain editable and separate. A second export/import checks triangles, bounds,
bone positions, normalized skin weights, alpha modes and texture dimensions;
body and face renders show that exact imported candidate.
The derived candidate also repeats the complete anatomy/static bend audit and
renders those bends from the re-imported GLB. Earlier `optimized/` candidates
and their movement failures remain available for comparison.
`class_character_skin.py` owns the joint refinement and the 10-micrometre
source-surface matching limit. `class-character-skin-recipes.json` records the
measured hip/shoulder settings per character: 96 iterations by default, 64 for
the female Siegewright, 128 for two male Empire/Chaos bodies, and 192 shoulder
iterations for broader male bodies. `--hip-iterations` (also `--skin-iterations`)
and `--shoulder-iterations` support focused diagnostics; their chosen values
are recorded in each candidate receipt. More
diffusion can worsen deformation, so it is never treated as an approval signal.

The four male Dwarf candidates additionally use small, fixed weight-paint
corrections in `scripts/unreal/class-character-skin-corrections/`.
`fit-class-character-skin.py` fits those weights against 102 supplied-pose
samples and five static bends. Its linear-blend prediction must match Blender's
evaluated modifier within 10 micrometres before solving. Corrections retain the
existing four bone influences and constrain each weight change to 0.2; the
recorded corrections use substantially smaller changes. A source model hash,
welded vertex/position hash and exact baseline recipe prevent applying them to
another body. Changed bodies require a fresh fit. These are ordinary fixed skin
weights, with no frame-dependent shape changes or altered bone pivots. Every
corrected export still repeats the independent Blender deformation review.

To refit a changed Dwarf source, run the fitter with `--run <run-directory>
--character stoneguard_m` (or the other Dwarf identity) through Blender. It
writes `skin-correction.json` beside that source and fails if the fit remains
outside the unchanged deformation limit. Inspect the result, replace that
identity's tracked correction, then rebuild and review its atlas candidate.
The previous correction deliberately refuses a different source binary.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --factory-startup --threads 2 --python-exit-code 1 --python scripts/unreal/atlas-class-characters.py -- --run artifacts/unreal/class-characters/anatomy-v10
```

Each character directory contains:

- `fitting-source.blend`: live anatomical targets and the stable 19,158-vertex
  MPFB fitting topology, including its hidden helpers.
- `character.blend`: stripped body, normalized skin, rig, detachable grooming
  and a hidden wireframe `ArmorFit_EditorOnly` envelope.
- `body.glb`: body/rig/materials/sockets without helper geometry, fitting cage or
  embedded animation. The four canonical sockets and 56-bone hierarchy remain.
- `anatomy.json`, `roundtrip.json`, `receipt.json`: measured results, source
  hashes and hash-bound binary/render evidence.
- Four body views, two neutral anatomy views, five static bend views, and body
  and face views rendered from the re-imported GLB.

The smooth calf/thigh correction changes the surface and hidden fitting helpers
together before MPFB fits the rig. It never scales animated bones. Surface-edge
weight diffusion softens joints, preserves shorter hand transitions, and then
normalizes to four influences. Eye pivots follow the fitted eyeballs. The pinned
eye atlas's transparent corneal shell is removed for opaque exports, retaining
the original iris/sclera geometry and UVs. Skin/hair tints are packed generated
images so the exported material does not depend on unsupported Blender mix nodes.
Grooming uses smooth surface normals and alpha cutouts. The initial Greenskin
canines still looked attached to the chin. The separate dentition pass below
corrects their roots, curvature and jaw attachment without rebuilding bodies.

The editor envelope reserves 18 mm around the body and up to 25 mm near joints;
6 mm is the intended soft-layer fit spacing. These are fitting targets, **not
measured clearance against armor**. Armor needs fitted modules, reversible body
masks and equipped motion inspection before admission.

## Greenskin dentition refinement

Derive all eight Greenskin variants from the verified atlas candidates:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --factory-startup --threads 2 --python-exit-code 1 --python scripts/unreal/fit-class-character-dentition.py -- --run artifacts/unreal/class-characters/anatomy-v10
```

The pass writes `dentition-v1/` beside each Greenskin source. Canine roots sit
inside the retained lower canine sockets, behind the lip; convex enamel crowns
curve forward through the mouth corners. Source dental UV islands identify the
16 lower crowns even when fitted molars rise above upper incisors. Lower teeth,
gums, tongue and tusks follow the canonical jaw. A retained CC0 MPFB jaw-descendant
weight mask transfers through the live fitting indices to every runtime seam.
The remaining skeleton and rest body surface stay fixed. Gum colour uses the
unused face-atlas tile; triangle counts and three material draws are preserved.

Validation re-imports the actual GLB, compares oriented body triangles within a
10-micrometre export tolerance, checks the original bone positions, and measures
rigid dental skinning and buried roots at jaw openings of 0, 12 and 24 degrees.
Each opening has front, three-quarter and profile renders. Five static bends and
the six supplied clips repeat on the corrected export. `--character warbrute_f`
limits the pass to one body; `--preview-only` skips source clips and deliberately
cannot produce a passing receipt. Jaw opening is diagnostic, not facial acting
or native animation acceptance.

Render the lineup and rebuild the gallery after this pass. Both select a passing
dentition candidate in preference to its atlas source, with current file/source
hashes checked. Earlier bodies remain available for comparison. Source regression
coverage includes `tests/unrealClassDentition.test.ts` and its Python fixtures.

## Deformation evidence and remaining gates

The anatomy audit checks real normalized finite weights, four influences, exact
canonical parents, positive uniform rig scale, stature/grounding, race shoulder
span, paired limb symmetry and forearm/upper-arm and calf/thigh balance.
Elbow, knee, overhead-arm, hip and finger bends measure the complete body edge
distribution and maximum physical extension. Maximum extension scales with body
height rather than judging a very dense short edge solely by its stretch ratio.
Every maximum remains in the report; numerical checks do not certify appearance.

Optional supplied-source pose diagnostics reuse the existing animation inventory
and anatomical chain contract:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --factory-startup --threads 2 --python-exit-code 1 --python scripts/unreal/review-class-character-motion.py -- --run artifacts/unreal/class-characters/anatomy-v10 --optimized
npm run unreal:class-character-review -- anatomy-v10
```

Render the six representative races at a shared metre scale before rebuilding
the gallery:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --factory-startup --threads 2 --python-exit-code 1 --python scripts/unreal/render-class-character-lineup.py -- --run artifacts/unreal/class-characters/anatomy-v10
```

These diagnostics apply 17 samples each of six supplied walking, running, weapon
and casting clips to fixed-length target limbs. Rest-direction alignment is
source-space preview only; the pelvis stays fixed and no clips are published.
Each clip includes midpoint and maximum-extension renders. `--optimized`
requires the derived atlas candidate; omit it to inspect the original body.
After a complete body run, either Blender pass can use disjoint `--shards 3
--shard 0`, `--shard 1`, and `--shard 2` workers. Finish every shard before
building the review sheet. On restricted Windows sessions set `TEMP` and `TMP`
to a writable local scratch directory for Blender's image-export scratch files.
Attack samples exposed shoulder/hip deformation beyond the diagnostic limits
on earlier candidates. Those failed iterations remain available for comparison;
the selected settings and bounded corrections must pass the same limits.

Native motion continues through `scripts/unreal/animation-pipeline.py` and the
[existing recipes](unreal-animation-import.md). Rig units, grips and live role
decisions remain character-specific. Equipped clearance, twist/corrective
quality, foot locking, facial deformation, final hair/anatomy/material polish,
LOD1/LOD2, performance and native/platform/Steam acceptance remain open.
No script in this workflow records human approval, publishes a runtime registry,
imports native Content or changes the active four-profile development roster.

Verification uses `tests/unrealClassCharacters.test.ts` and its Python numerical
fixtures, plus the normal repository/Unreal tooling checks. Actual local binary
and render validation is separate from those source-level regression tests.
