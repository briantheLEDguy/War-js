# Novitiate Field Harness

A secondary, modest armor set for the accepted male Battle Prelate. Nine separate
armor modules share the existing body, face, hammer and all nine animation clips.
The accepted ornate equipment remains available separately.

The refinement adds rolled steel edges, shaped plate returns, fitted hinge tabs
and rivets, leather binding straps, a leather toe rand, stitched boot welts, and
turned cloth hems. Painted material inputs add subtle steel roughness, leather
grain and cloth weave. This remains a stylized game character; it is not a
photographic reconstruction.

The compact shoulder cap, lower lame and hardware use one rigid shoulder
attachment to preserve their overlap during hammer swings. The leather toe rand
retains the accepted boot contact footprint for the shared death animation.

## Files

- `battle_prelate_novitiate_reference_master.blend`: editable source cages,
  finishing modifiers, materials and fixed comparison cameras.
- `battle_prelate_novitiate_game_master.blend`: canonical rig and three runtime
  LOD assemblies with packed textures.
- `source/`: explicit vertex IDs, coordinates, faces, UV corners, material
  assignments, transforms and derivation records.
- `textures/`: literal paint records, source image maps and their manifest.
- `runtime/`: 27 new armor GLBs, six byte-identical shared body/hammer GLBs,
  evaluated mesh archive, texture atlases and binary validation report.
- `review/`: source and clean GLB reimport renders, nine-clip motion evidence,
  numerical audits and the separate local visual assessment.
- `tools/`: explicit record authoring, loading, baking, rigging, validation,
  comparison and additive installation tools. `tests/` covers these workflows.
- `PROMOTION.md`: installation contract and preview behavior.

The sibling `battle-prelate-reference-rebuild` package is required to rebuild:
it supplies the accepted cages and immutable shared rig/body/weapon provenance.
Neither package should be deleted while regenerating this variant.

## Rebuild and verify

Run the following from this directory with Python/Pillow, then Blender 5.0 in a
disposable background process. The authoring tools serialize explicit records;
they do not generate anatomy or assemble primitive substitutes.

```text
python tools/author_novitiate_upper.py
python tools/author_novitiate_limbs.py
python tools/author_novitiate_core.py
python tools/refine_novitiate_cloth.py
python tools/refine_novitiate_paint.py
python tools/paint_materials.py
blender --background --factory-startup --python-exit-code 1 --python tools/build_proof.py -- --views full_front,full_three_quarter,full_side,full_back --modes material,neutral
blender --background --factory-startup --python-exit-code 1 --python tools/rig_character.py -- --lods 0,1,2 --bake --export
python tools/validate_runtime.py
blender --background --factory-startup --python-exit-code 1 --python tools/reimport_review.py -- --lods 0,1,2
python tools/reimport_review.py --compose review/reimport_report.json
blender --background --factory-startup --python-exit-code 1 --python tools/audit_exported_motion.py
python -m unittest discover -s tests -v
```

Review actual renders before preparing installation. Numeric checks do not
establish visual acceptance. The fixed cameras remain unchanged; diagnostic
closeups are supplementary. The final game uses LOD0; LOD1 and LOD2 are supplied
without adding automatic distance switching.

## Local game use

On a male Empire Battle Prelate, choose **Novitiate armor** under **Armor preview**
in character selection. This compares all nine installed modules using the
existing character renderer. It does not grant items or change saved equipment;
**Enter World uses the character's actual equipped armor**. Catalog IDs are
`novitiate_civic_battle_prelate_<slot>_m`. No shop, inventory expansion, item stats,
default loadout replacement or site deployment is included.

`DELIVERY.json` records final counts, hashes and installation evidence. The
authoritative final checks are `runtime/validation_report.json`,
`review/exported_motion_audit.json` and `review/runtime_visual_review.json`.
Other probe/design records document intermediate work and retain their own
source hashes; they must not be treated as approval of a later revision.
