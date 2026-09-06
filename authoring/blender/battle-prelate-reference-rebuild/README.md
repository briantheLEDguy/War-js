# Reference-built Battle Prelate

This workspace contains the full male character, nine armor modules and separate
warhammer built from explicitly authored mesh records. The user accepted the
upper-body direction and requested full completion and local game integration.
Final runtime acceptance is recorded separately from source validation.

The complete set was installed locally on 2026-09-06. LOD0/1/2 contain
98,274 / 56,628 / 29,484 equipped triangles, eleven materials per LOD, and
66,191,728 bytes across the 33 self-contained GLBs. The final export passed both
binary validation and Khronos validation (zero errors). The visual decision and
remaining likeness/LOD/death-pose limitations are recorded in
`review/runtime_visual_review.json`; this is not a photographic reconstruction.

`review/authoring_installation.json` records the initial verified package copy.
Build and review reports retain the original isolated build-directory paths as
provenance. Rebuild/revalidate from the new location to create a new revision;
do not edit historical report paths or hashes to make them appear current.

## Architecture

- `source/*.json`: stable vertex IDs, literal XYZ coordinates, faces, corner UVs,
  named landmarks, materials, instance transforms and permitted modifiers.
- `tools/author_*.py`: literal coordinate/topology tables and serialization.
  Repeated ornaments copy these newly authored patches at recorded placements.
- `references/`: pixel-identical reference crops, landmarks, uncertainty ranges,
  traced silhouettes and documented disagreements between illustrated views.
- `source/scene.json`: fixed comparison cameras, poses, scale and coordinate rules.
- `tools/build_proof.py`: idempotent source importer, retained control cages,
  neutral/material/wireframe renders and fully evaluated geometry archives.
- `textures/*paint*.json`, `tools/paint_*.py`: literal paint strokes and UV
  associations. Material images contain no reference lighting or randomized noise.
- `source/chainmail_detail.dat`, `tools/bake_chainmail.py`: inspectable authored
  links and explicit placements baked into the joint-underlayer material.
- `source/humanoid_game_v2_animation_contract.blend`: canonical armature, four
  attachment empties and nine compatible actions only. Previous character meshes
  are discarded before this snapshot is made.
- `tools/rig_character.py`: module assembly, shared rest matrices, skin weights,
  three LODs, atlas baking, staged GLBs and actual mesh/UV/weight inspection data.
- `tools/correct_animation.py`: measured arm/finger corrections around the actual
  hammer grip and hips translation to keep evaluated boots above the ground.
  Preserves the original skeleton, root tracks and leg rotations; grounding is
  checked with root/scale tracks muted to match the game animation sanitizer.
- `tools/bake_atlas.py`: authored material and high-source normal transfer into
  one atlas material per module. Cloth appliques and lower-LOD armor also receive
  high-source color, roughness and metallic transfer. AO records joined-module
  self-occlusion and authored occlusion maps where present.
- `tools/tessellate_runtime.py`: runtime n-gon tessellation for explicit normal-map
  tangents; preserves vertex positions, skin weights and authored UV corners.
- `tools/validate_source.py`, `tools/validate_runtime.py`, `tests/`: geometry,
  source provenance, binary GLB, skeleton, texture, animation and budget checks.
- `tools/reimport_review.py`: clean import of exported assets and motion renders.
- `tools/promote_runtime.py`, [PROMOTION.md](PROMOTION.md): hash-bound staging,
  targeted runtime publication, archives and rollback of overwritten files.

`battle_prelate_upper_body_proof.blend` preserves the first milestone.
`battle_prelate_reference_master.blend` contains the editable comparison source.
`battle_prelate_game_master.blend` is produced by the complete baked/exported run;
its source cages remain separate from the rigged runtime modules and LODs.
Packed image maps travel with the master. `runtime/evaluated_lods.json.gz` records
all actual runtime vertices, faces, corner UVs, materials and named weights.

The tabard cross and gilded hem remain modeled in the editable source. Their
thin surface detail is baked onto runtime cloth so it follows the cloth's exact
deformation. Silhouette fringe stays modeled in LOD0/1. Lower-LOD armor bakes also
transfer the retained high-source material channels, preserving the brass color
of details whose separate geometry is reduced or omitted.

## Rebuild and verify

Use Python 3 with Pillow and Blender 5.0. Run from this directory. The author
scripts are independent except that repeated reliquaries copy `medallion.json`.
Regenerate only the changed component, then validate before building.

```powershell
python tools/validate_source.py
python -m unittest discover -s tests -v
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 8 --python-exit-code 1 --python tools/build_proof.py -- --views full_front,full_side,full_back,full_three_quarter --modes neutral,material,wire
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 8 --python-exit-code 1 --python tools/rig_character.py -- --lods 0,1,2 --bake --export --render
python tools/validate_runtime.py
```

Geometry budgets are checked before baking. Atlas caches are keyed to the exact
source, paint, UV/group inputs and implementation; stale entries are not reused.
Partial LOD runs are diagnostic and cannot pass the promotion gate. Final review
requires the actual GLBs, four equipped views and motion evidence. A successful
script or validator does not by itself establish visual likeness.

Full validation requires the staged build report and its exact hashed
`runtime/evaluated_lods.json.gz` inspection archive. The promotion package retains
that archive, and each LOD's QC records its own retained parts and finishing.
Explicit partial binary audits may run without build provenance, with warnings;
they cannot authorize runtime promotion.

## Runtime contract and limitations

Coordinates use meters, Blender Z-up, front -Y; glTF converts `(x,y,z)` to
`(x,z,-y)`. Height is 1.86 m. The 56-bone `humanoid_game_v2` skeleton and all four
socket empties retain the canonical rest matrices. Skinning uses at most four
influences. Rigid armor follows its assigned bones, while joint cloth and the
split-weight tabard deform independently. Body owns the animation clips.

LOD0 targets 110k triangles, with a 120k ceiling; armor modules are limited to
14k each, LOD1 to 60k and LOD2 to 30k. Equipped rendering uses eleven atlas
materials; textures are at most 2048 square. GLBs embed base color, tangent normal
and packed occlusion/roughness/metallic maps. Separate channel PNGs remain in the
source package. The combined GLB bundle is limited to 80 MB.

The existing game resolver selects LOD0. LOD1/2 are separately validated runtime
assets, with their paths recorded in QC, for a future distance-selection policy;
this change does not alter gameplay APIs. Local promotion changes only the male
Battle Prelate assets and approved manifest entries. It does not deploy the site.

The reference is an illustrated concept sheet, not calibrated photography.
Hidden construction is documented interpretation. Likeness measurements remain
diagnostics; the final visual report records remaining differences candidly.
