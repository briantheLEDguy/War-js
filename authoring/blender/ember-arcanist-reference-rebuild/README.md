# Ember Arcanist reference build

Male Ember Arcanist with auburn hair and stubble, a wrapped ash-colored collar,
oxblood split robes, brass-edged dark shoulders, leather arms and boots, parchment
facings, seals, belt pouches, a spellbook and an emissive brazier staff.

This is a simplified game interpretation of the supplied illustrated reference.
It is not a photographic reconstruction. Hair, face, ornament density, fabric
tears and close-up surface detail remain less elaborate than the concept sheet.

## Files and workflow

- `ember_arcanist_reference_master.blend`: editable control cages and comparison cameras.
- `ember_arcanist_game_master.blend`: rigged modules, packed baked images and three LODs.
- `ember_arcanist_reimport_review.blend`: assembly of the actual exported GLBs.
- `source/`: explicit vertices, corner UVs, permitted modifiers and canonical rig.
- `inherited/`: retained Battle Prelate cage records and archived reference tooling.
- `tools/author_ember.py`, `tools/refine_ember.py`: repeatable fitting and literal new patches.
- `textures/`: paint records, source PNGs and paint inspection reports.
- `runtime/`: staged GLBs, evaluated geometry archive and binary/Khronos audits.
- `review/`: source views, exported views, motion frames and visual-review evidence.
- `manifest_templates/`: unapproved input templates; only promotion fills final hashes and review.

The body and some outfit topology derive from the accepted Battle Prelate source
cages. Hair, collar, robe facings, harness and staff use new explicit patches.
The helpers connect authored grid rows and serialize coordinates; Blender
primitives and random shape generators are not used. Read `derivation.json` for
the distinction between inherited and new components.

## Rebuild

Use Python with Pillow, Blender 5.0 and Node with `gltf-validator`. Run here:

```powershell
python tools/author_ember.py
python tools/refine_ember.py
python tools/paint_materials.py
python tools/paint_skin.py
python -m unittest discover -s tests -v
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 6 --python-exit-code 1 --python tools/build_proof.py -- --views full_front,full_three_quarter,full_side,full_back --modes material
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 6 --python-exit-code 1 --python tools/rig_character.py -- --lods 0,1,2 --bake --export
python tools/validate_runtime.py
node tools/check_gltf.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 6 --python-exit-code 1 --python tools/reimport_review.py -- --engine BLENDER_EEVEE
python tools/reimport_review.py --compose review/reimport_report.json
```

Run both authoring scripts in that order; `author_ember.py` resets the initial
adaptation and `refine_ember.py` applies the final fit and material refinements.
Do not execute the archived Battle Prelate authoring scripts against this package.

## Runtime contract

One body, nine armor slots and one rigid staff at three LODs: 33 self-contained
GLBs. The canonical `humanoid_game_v2` rig retains 56 bones, four attachment
sockets and nine body-owned actions. At most four weights per vertex.
The scarf is head equipment but does not mask the face. Staff emission is baked
into its own atlas channel. The staff uses the existing right-hand socket.

Equipped triangles: 62,900 / 29,468 / 15,636. Bundle: 48,993,960 bytes.
LOD0 is selected by the current resolver; LOD1/2 are supplied without adding
automatic distance switching. Skin and source materials are packed into the
Blender master. GLBs use at most 2K textures and eleven atlas materials per LOD.

The local integration adds the male profile and armor to the approved registry,
plus the Ashbound Brazier Staff item. New male characters receive the staff;
existing empty main-hand slots are backfilled while custom weapons and armor
remain intact. Female characters keep their existing defaults. No deployment.

Final installation and game verification are recorded in `DELIVERY.md`.
