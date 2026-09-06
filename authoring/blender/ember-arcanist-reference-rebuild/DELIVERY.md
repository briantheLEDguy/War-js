# Ember Arcanist delivery

Installed locally in the main project and isolated `codex/ember-arcanist-reference` worktree. No website deployment.

- Editable reference master: `ember_arcanist_reference_master.blend`.
- Rigged game master with packed maps: `ember_arcanist_game_master.blend`.
- Actual exported assembly: `ember_arcanist_reimport_review.blend`.
- 33 self-contained GLBs: body, nine armor modules and staff at three LODs.
- Equipped triangles: 62,900 / 29,468 / 15,636; eleven atlas materials per LOD.
- Bundle: 48,993,960 bytes; 56-bone rig, four sockets, nine clips, max four weights.
- Source and runtime masters were packed and assigned a full-figure opening view after validation. `review/delivery_master_preparation.json` records those master-only hash changes. Exported GLBs did not change.

## Verified

- 5 authoring unit tests passed.
- 19 focused TypeScript tests passed in the main project across Ember equipment, character service and weapon animation authority.
- Main TypeScript check and production build passed (existing large-chunk warning).
- 208 standard model/registry validation records passed.
- All 33 GLBs passed binary validation and Khronos validation: zero errors, 30 skinned-parent warnings.
- Clean reimport includes four equipped views, lower LOD views and 27 animation frames.
- Browser preview, production world entry, airborne jump and White Cautery activation were observed and captured in `review/local_game_review.json`.

## Limits

The model is a simplified game interpretation, not a full photographic likeness. Broad hair locks, facial detail, robe tears, cloth folds and ornament density remain simpler than the supplied concept. Existing skeletal animation is used, without cloth simulation. LOD0 is active; lower LODs are delivered without automatic switching. The full death motion extends beyond the fixed review camera.

The review is a Codex visual/technical decision under the user's explicit local-integration request; it is not represented as user aesthetic approval. No repository-wide strict-validation success is claimed.

## Installation evidence

Main transaction: `authoring/archives/ember-arcanist-promotions/reference-98428bc32a58-fd450203/`.
Isolated transaction: `authoring/archives/ember-arcanist-promotions/reference-98428bc32a58-a0b1f625/`.
Reports retain their original build paths as provenance. Rerunning validation in a copied package creates a new local report; do not rewrite historical paths or hashes.
