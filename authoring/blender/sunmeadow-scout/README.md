# Sunmeadow High Elf patrol scout

Original complete outfit for the existing **Mira Stonewake, Forward Scout** NPC
(`sunmeadow_march_scout`). The final K source and three reviewed exports pass
all 13 package gates and are ready for the root publication process. Exact
identity remains immutable in `publication-contract.json`; verified evidence is
in `review/technical-readiness.json`. Runtime readiness is set separately by the
publisher, and this package makes no in-game or network verification claim.

The retained `civic_humanoid_v2_f` anatomical foundation supplies rounded limbs,
articulated fingers, face and the original skeletal structure. The body and rig
share the same High Elf proportion map. The source GLB, editable foundation,
quad garment surface and QC bytes are retained locally and named by literal
hashes in `foundation-provenance.json`.

The original scout outfit uses a continuous forest-green woven shirt, trousers,
fitted boots, a sewn suede jerkin, narrow shoulder yokes, an ash-blond swept groom
and compact braid. A visible shoulder harness and leather keepers suspend a
quiver and recurve bow; a separate belt loop carries the map case. The equipment
is part of the complete skinned outfit. No new weapon or inventory behavior is
implied.

`tools/build_inhabitants.py` builds the editable fitted master and draft LODs;
`tools/export_tagged.py` retains that authored master and adds semantic geometry
IDs before producing the final three LOD masters/GLBs. IDs identify exact
equipment parts for the independent attachment audit after batching and reduction;
they do not add gameplay behavior. Construction uses explicit garment panels, section lofts and
swept paths; no Blender primitive mesh operators are used. The nine established
clips are fitted to the actual limbs, soles and prone contact surfaces.

The final LODs contain 168,246 / 97,542 / 49,336 triangles, 18 materials and nine
embedded clips each. `tools/retain_lod2_boots.py` is the final finishing step after
tagged export: it retains the reviewed LOD1 boot surfaces in LOD2 to prevent a
visible shaft split during running. The original LOD2 master, input hashes and
exact operation are retained in the build receipt. LOD0 and LOD1 stay unchanged.
The gate directly compares actual GLB boot topology, winding and skin weights.

`tools/inspect_foundation.py` records the retained female anatomical baseline.
The independent `inspect_*` scripts reimport the actual exports for arm volume,
garment and equipment clearance, boot tucking, welt attachment, motion and ground
contact. `review_inhabitants.py` renders actual GLB views. The read-only final
gate is `python authoring/blender/sunmeadow-scout/tools/test_exports.py` after all
required reports exist. Missing reports are failures, not implicit acceptance.
Run `tools/retain_validation_inputs.py` only after all current inspection reports
and six reimported views per LOD are complete; it records additional validation
inputs separately from the original generation inputs. The final gate itself is
read-only. Shoulder joins are checked at four seam centers and eight corners,
alongside twenty equipment contacts, through every clip and every LOD. All
garment and carried-item edge crossings must be zero; source smoothness does not
replace actual attachment checks.

The bow, arrows and map case remain stowed components of this complete outfit.
The package does not claim modular equipment interchange, bow-drawing behavior,
canonical-animation retargeting compatibility, or verified network gameplay.

Frozen release `d12b92a97fb9806ee882` is published as existing Mira Stonewake
and in the GM builder. Production Game/NpcSpawner checks verified visible
LOD0/1/2 at 6.2/45.2/100.2m, with 168,246/97,542/49,336 triangles and properly
located skin bounds. Exact map/model/harness hashes and bounded runtime limits
are retained in `review/runtime-integration-20260920.json`.
