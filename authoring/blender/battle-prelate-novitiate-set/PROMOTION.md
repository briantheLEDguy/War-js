# Additive Novitiate armor publication

This helper stages and applies the nine additional male Battle Prelate armor
modules. It does not publish the existing body, hammer, ornate armor, or starter
loadout. Publication requires a passed full-assembly validation and a separate,
hash-matched local visual review. No approval is fabricated by the helper.

The staged validation bundle contains 33 GLBs: 27 new armor files and six exact
shared body/weapon files. The shared files must also match the explicitly named
target repository before and after publication. Only the new 27 GLBs, their 27 QC
sidecars, nine approved manifests, compiled registry, and evidence/source archives
may be written. The entire remaining registry is compared unchanged. Prior files
are archived before replacement, and interrupted publication rolls back its own
changes without overwriting concurrent edits.

Identifiers use these forms for the nine slots `head`, `shoulders`, `chest`,
`hands`, `waist`, `legs`, `feet`, `back`, and `tabard`:

- Item: `novitiate_civic_battle_prelate_<slot>_m`.
- Asset: `arm.civic.battle_prelate.<slot>.novitiate.m`.
- LOD0: `arm_civic_battle_prelate_<slot>_novitiate_m.glb`.
- Lower LODs append `_lod1` or `_lod2` before `.glb`.

The runtime catalog is `src/data/novitiateArmor.ts`. Character selection offers
**Current armor / Novitiate armor** under **Armor preview**, once all nine models
resolve as approved compatible assets. It clones the preview character, preserves
the body and hammer, and changes no character equipment, inventory, gold, or
starter defaults. **Enter World uses the character's actual equipped armor.**
No shop, item grant, acquisition, bag expansion, rarity, or level system is added.

Run from this authoring directory after the actual exports and review are ready:

```powershell
$assetPython = 'C:/Users/bschm/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$targetRepository = 'C:/Users/bschm/Desktop/GitPulls/War-js/authoring/work/reference-rebuild'
& $assetPython -B tools/promote_runtime.py --target-repo $targetRepository --node 'C:/Program Files/nodejs/node.exe'
```

Inspect the returned `promotion/<transaction>/promotion_plan.json`. Apply that
exact plan with the same `--target-repo` and `--apply <plan path>` only after its
validated visual review is complete. Preparation alone leaves runtime assets
unchanged. Then run the existing registry and model checks in the target repo:

```powershell
node scripts/blender-character-pipeline/tools/compile-runtime-registry.mjs --check
npm run models:validate
```

Focused checks are `tests/novitiateArmor.test.ts` in the repository and
`tests/test_promote_runtime.py` here. Shared body/weapon source records are archived
under `shared_source/source/` and retain their original hashes; new armor records
remain under `source/`. The new variant and folded-hem authoring tools, literal
paint record, paint/refinement players, paint manifest, and all source PNG maps
are included in provenance. The paint manifest must match its record and all
four channels. `source_ledger.json` hashes every exact archived input; each new
QC/approved manifest binds that ledger. This ledger captures authoring inputs;
runtime binary validation and visual review remain separate evidence.
LOD1/2 remain deliverable assets without automatic distance switching. Nothing
in this workflow deploys the site.
