# Aegis city guard set

Four equipped NPC variants based on the supplied city guard guide: spear and
heater shield, halberd, crossbow sentry, and plumed captain with cloak and sword.
They share fitted steel armor, a pierced visor, blue/ivory livery, tower-and-star
charges, leather pouches, layered shoulders and articulated boots.

## Authoring and runtime

- `source/`: explicit editable vertices, faces, UVs, rig assignments and modifiers.
- `anatomy/`: fitted natural head/neck extracted from the repository's existing
  `blends/male_base.blend`, with source hashes and an uncovered anatomy review.
  The distorted inherited head cage is replaced. Skin UVs and packed texture
  pixels are retained; eye UVs are fitted to a natural iris footprint.
- `references/guard-guide.png`: supplied visual reference; its text is not an
  executable instruction source.
- `tools/author_guards.py`: adapted Battle Prelate anatomical/armor cages plus
  new civic helmets, heraldry, weapons, belt kit and captain accessories.
- `tools/guard_pose.py`: two-bone arm holds, finger closure and bind-space weapon
  placement. Canonical torso/leg motion remains active.
- `textures/`: deterministic shared equipment textures, plus packed skin/eye
  textures from the existing human base (maximum dimension 2048).
- `aegis_city_guards_master.blend`: editable source cages and ten armor/body
  modules per variant, plus three evaluated detail levels. The shared source
  rig is for authoring; use the individual export rigs for animation review.
- `aegis_city_guards_export_review.blend`: clean imports of delivered GLBs with
  independent rigs and each variant's actual idle action.
- `runtime/`: twelve self-contained GLBs, build hashes and Khronos validation.
- `review/`: actual exported-model views; `exported_idle_lineup.png` is the
  authoritative final lineup, rather than earlier source-space comparison views.

NPC exports combine the editable armor modules into one skinned mesh with nine
material primitives. The canonical `humanoid_game_v2` rig and clips are reused.
The runtime registry selects LOD0; LOD1 and LOD2 are supplied for later distance
selection. No automatic LOD switch is added by this change.

## Rebuild and verify

From the repository root, with Python/Pillow, Blender 5.x and Node dependencies:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --python-exit-code 1 --python authoring/blender/aegis-city-guards/tools/extract_natural_head.py
python authoring/blender/aegis-city-guards/tools/author_guards.py
python authoring/blender/aegis-city-guards/tools/paint_materials.py
python -m unittest discover -s authoring/blender/aegis-city-guards/tests -v
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 6 --python-exit-code 1 --python authoring/blender/aegis-city-guards/tools/build_guards.py -- --export --lods 0,1,2
node authoring/blender/aegis-city-guards/tools/validate_guards.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 4 --python-exit-code 1 --python authoring/blender/aegis-city-guards/tools/review_exports.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --python-exit-code 1 --python authoring/blender/aegis-city-guards/tools/review_anatomy.py
# Inspect the rendered exports and record review/visual-review.json with the validation hash.
python authoring/blender/aegis-city-guards/tools/install_guards.py
npm run test -- tests/aegisCityGuards.test.ts
```

`GLTF_VALIDATOR_PATH` can identify an existing local `gltf-validator` package.
The build imports the established loader, rig binder and tangent preparation
from the sibling Ember Arcanist tools. Keep both source packages available.

## Fidelity and animation limits

This is a game interpretation of the illustrated guide. Cloth folds, fur,
feather barbs, distressed heraldic paint and fine engraving remain simplified.
Cloth and fur are skinned meshes without simulation. Weapon holds are corrected
for patrol/idle use; dedicated crossbow reload and specialist combat gestures
are not authored. The captain carries a sheathed sword.

Weapon grip positions use palm contact points, with two separate holds on the
halberd shaft and crossbow stock/fore-end. `review/exported-grip-audit.json`
requires 90 contact samples per armed variant across all nine imported clips and
checks their relative positions. The audit
binds the result to each delivered GLB hash. Front/side and walking renders
provide the visual check in addition to these numerical contact measurements.

Local technical/visual review is a Codex assessment, not user aesthetic approval.
Missing models retain the game's existing fallback behavior.
