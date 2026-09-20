# Frontier workshop items

Original siege repair bench and ammunition cradle for human-scale town/keep
workshops, shared by both campaign pairings. See `DESIGN.md` for construction
and placement direction and `WORK_STATE.md` for the current technical boundary.
Published September 20 under the user's standing asset approval. Both items
have three validated runtime LODs, full PBR textures and measured collision.
All 36 keeps contain one of each item; both are available in the GM builder's
Universal Siege Workshop collection. These are static props; repair and
ammunition-stock interactions remain future work.

`source/` retains explicit construction geometry and references for utility code.
`tools/` builds source cages, finishes joints and produces local review evidence.
`masters/`, `textures/`, `runtime/` and `review/` separate editable authoring,
painted/baked material channels, staged exports and exact visual/technical proofs.
`builder-metadata.json` binds the measured collision and clear working approaches
to the published model hashes. `scripts/campaign/shared-keep-items.mjs` places
the items in free inner-court bays while retaining the commander and gate routes.

`author_items.py` retains explicit timber/tool sections, shouldered tenons,
cutting cages, shaped plates, rope routes and individually dressed stone surveys.
`build_items.py` cuts actual receiving sockets, finishes edges, seats stone loads
against the finished supports and preserves every original construction cage.
`materials_items.py` supplies original piece-aligned wood grain and working
wear, forged/steel fields, hemp fibres and mineral detail. Source PBR proofs are
separate from runtime exports. `export_items.py` bakes exact finished batches;
`share_textures.py` externalizes unchanged PNG bytes into content-addressed
texture files. `review_exports.py` checks fresh GLBs at 4, 12 and 28 metres plus
neutral/detail views. `validate_items.mjs` binds hashes, complete PBR, technical
budgets, actual topology/images and Khronos validation without publishing.
`measure_builder.py` derives conservative collision boxes from real finished
parts and verifies clear working approaches. `test_source.py` checks closed
source cages, receiving sockets, frontage, grounded feet and load support.

Rebuild/reimport outputs before running `node tools/publish_items.mjs --publish`
from this package. That publisher requires exact model, material, source,
retained-exporter and image hashes, closed actual-export topology and zero
Khronos errors/warnings. Then regenerate the model registry, campaign and GM
catalog from the repository root. Local, shared-campaign and GM presentations
use the same 16m/42m LOD thresholds; campaign visibility ends at 160m.
