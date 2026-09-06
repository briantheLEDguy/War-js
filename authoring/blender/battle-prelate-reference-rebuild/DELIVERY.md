# Battle Prelate delivery

The full male Battle Prelate is installed locally in the main working copy and
the isolated `codex/reference-battle-prelate-rebuild` working copy. It follows the
accepted modeling direction, with a body, nine armor modules, and a separate
warhammer. It is a **stylized interpretation, not a photographic reconstruction**.
No site deployment was performed.

## Package and evidence

| Item | Final result |
| --- | --- |
| Runtime files | 33 self-contained GLBs: 11 modules at each of three LODs |
| Equipped triangles | LOD0 98,274; LOD1 56,628; LOD2 29,484 |
| Materials / draw calls | 11 per equipped LOD, one atlas material per module |
| Combined GLB size | 66,191,728 bytes (66.2 MB decimal) |
| Rig | 56 bones, four sockets, nine body-owned animation clips |
| Skin weights | At most four normalized influences per vertex |
| Textures | At most 2048 pixels; base color, normal, and packed occlusion/roughness/metallic |
| Clean export review | Four LOD0 material views, neutral front, LOD1/2 fronts, and 27 motion frames |

Open [battle_prelate_game_master.blend](battle_prelate_game_master.blend) for the
rigged character and packed materials. The editable literal mesh cages and source
comparison scene are in
[battle_prelate_reference_master.blend](battle_prelate_reference_master.blend).
[battle_prelate_reimport_review.blend](battle_prelate_reimport_review.blend) contains
the actual exported assembly. [source/](source/), [textures/](textures/), and
[references/](references/) retain the explicit coordinates, painted material
inputs, reference crops, and measurement uncertainty.

The staged GLBs and exact evaluated mesh/UV/weight archive are in
[runtime/](runtime/). Installed game assets are under each repository's
`public/assets/models/`, with the eleven male Battle Prelate approved manifests
under `scripts/blender-character-pipeline/data/approved-assets/`. Each local
promotion published 120 files and archived previous files under
`authoring/archives/battle-prelate-promotions/`:

- Main transaction: `reference-9d26a2eb0a6c-071bc05c`.
- Isolated transaction: `reference-9d26a2eb0a6c-dca8042a`; all publication hashes
  match the main transaction. See [isolated integration](review/isolated_integration.json).

Reports retain the original isolated build paths as provenance. The main package
mirror is `authoring/blender/battle-prelate-reference-rebuild/`; its initial
verified copy is recorded in [authoring installation](review/authoring_installation.json).

## Verification

| Check | Status |
| --- | --- |
| Authoring Python suite | [112 tests passed](review/test_results_final.txt) |
| Final four JavaScript test files | 32 tests passed in the main working copy |
| TypeScript after the reflection fix | Passed |
| Local Vite production build after the reflection fix | Passed: 172 modules; existing large-chunk warning only |
| Final live-game screenshots after the reflection fix | Passed: character selection, world view, and airborne jump |
| Full binary, source, rig, texture, and budget validation | All 33 GLBs passed |
| Khronos glTF validator | Zero errors; 30 expected skinned-parent warnings |
| Isolated registry and regular model validation | Passed; 197 validation records |
| Strict repository model validation | 79 unrelated baseline QC hash mismatches remain |

The final local checks include actual [character selection](review/local_game_character_selection.png),
[world](review/local_game_world.png), [airborne jump](review/local_game_jump.png),
and [Reliquary Smash activation](review/local_game_ability.png) captures after the
reflection correction. The main production build reports only
the existing warning for bundles larger than 500 KB.

The [local game review](review/local_game_review.json) records the observed
actions, clean-reload console output, installed asset hashes, and screenshot
hashes. The [final delivery supplement](review/final_delivery_sync.json) verifies
the final evidence copied into the main project. Watch exclusions are scoped to
each checkout's own authoring directories so runtime source updates remain active.

The strict audit found the same 79 mismatches against the preserved previous and
current registry expectations; all lie outside this promotion. All eleven
promoted entries pass their current hashes and approval checks. This is not a
claim that the repository-wide strict check is clean. See
[strict baseline audit](review/strict_baseline_audit.json) for its historical
evidence limits.

The [binary report](runtime/validation_report.json),
[Khronos report](runtime/gltf_validation_report.json), and
[clean reimport report](review/reimport_report.json) bind evidence to the final
files. [Runtime visual review](review/runtime_visual_review.json) records the
separate local acceptance decision and limitations. The later
[archive byte correction](review/archive_byte_write_correction.json) preserves
literal source/scene bytes; it changed no geometry or exports, and the builder
actually used for the retained source master remains archived.

The runtime fixes keep the authored hammer grip under its animation's control,
provide neutral room reflections in character preview, and include the complete
sky sphere in reflection capture when HDRI is absent. These lighting corrections
do not change the delivered GLBs or their material values.

## Limits

- Facial detail, ornament density, and weathering remain visibly simpler than
  the illustrated reference. Its views are not calibrated photographs; hidden
  construction and ambiguous landmarks are documented interpretations.
- The game currently selects LOD0. LOD1/2 are delivered and validated, with
  coarser small details, **without automatic distance switching**.
- The tabard cross and gilded hem remain modeled in the source and are baked
  onto runtime cloth to follow deformation. Geometric fringe remains in LOD0/1.
- Motion review samples all nine clips; it is not an exhaustive collision proof
  for every blended pose. The inherited death motion folds forward rather than
  ending fully prone; the fixed contact camera clips its far end, covered by a
  separate wider audit.
- Local installation and review do not constitute deployment.
