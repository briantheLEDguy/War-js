# Field command table frozen authoring handoff

2026-09-20. Technically verified and ready for root publication. No aesthetic approval is pending.

`frontier_field_command_table` / `prop.frontier.field_command_table`

Run `node authoring/blender/field-command-table/tools/validate_table.mjs --check` from the repository root.

| LOD | Triangles | GLB bytes | SHA-256 |
|---|---:|---:|---|
| 0 | 27534 | 8343904 | `45690f7f8752e3dcf7265e60f3977e3a513915595e7d640a476f9cd43a49d6aa` |
| 1 | 13366 | 3117428 | `8e75aa87a5c2d1d8f6ef20d0697ba1c8ec4ebcf008d514ab35fb2c8c93b751be` |
| 2 | 5274 | 968028 | `b353175111bf942b8777280fb15c7e3f28ffe0d312e15aa7413952e12e36040d` |

Six packed masters (each contains 18 packed PBR images):

- `masters/frontier_field_command_table_lod0.source.blend` — `43fd77b6ad4c21c2436483aa45db6c5652d230e728bdd084aeb694f45ffeb218`
- `masters/frontier_field_command_table_lod0.blend` — `915d2074869ebcdeaa857c03a8ce40a3098f8797f555d139d64e67d4033e190f`
- `masters/frontier_field_command_table_lod1.source.blend` — `2df6b6cc1bb1d74acaf6126c9eab070d8dfbfd0518aca8416759391d41fffbd8`
- `masters/frontier_field_command_table_lod1.blend` — `877531de7b3831466ab247e44d0e377d87affaf99e292d2b29104d6c5f5634f7`
- `masters/frontier_field_command_table_lod2.source.blend` — `13069bfa4bbc7ce5a49ead6f3e8626ea452a4256be27e9652cb9eb9db24c6022`
- `masters/frontier_field_command_table_lod2.blend` — `337f651b3ba3e1191c29ba995a65ea0a0b830b05dd49a15dcfe6e311810761da`

Other frozen evidence:

- `tools/build_table.py` — `39d301ba34660b44fc591edf4d5fbbfdb846de4cd34a76b33e4654a47089cbbe`
- `tools/make_textures.py` — `2e7c5e634f654701db76444ad42c99bc5553776ff221b1c53aeecd0e0b2aa28f`
- `tools/validate_table.mjs` — `3d089d2c4ff2a8e64e34ff3dadf5184555ee0eb8b5b2c71a11a71d6b6c32f058`
- `builder-contract.json` — `2e356e84f4b560c9b4f1d2d981cec3ad2be459fb4d4c8372c41aca626eac27b3`
- `review/frontier_field_command_table_build.json` — `7fb859366e824d0b6b58c84defb7b257d43f249f4317df311e27d1317082c8dd`
- `review/construction-contacts.json` — `1b4abf3ddebefb07199284c877d711f69592b492443891ec1c72aa4edd6c1257`
- `review/master-audit.json` — `efeded68935dc03b856a2b42ff4c3f9c02ee1eabf14f782415a5753a0c7d1ef8`
- `validation.json` — `e203804e660a376d700f2608b815e86f07e4847e974581679bcc518e9693113b`

All source/final masters and literal imports have zero boundary, non-manifold and loose edges. All 300 fitting contacts pass after actual imported surface verification (0 m maximum vertex deviation; worst measured support gap 0.452 mm). Six measured collision masses cover every visible component exactly once. Both skids have eight source contact vertices at height zero. The +Z standing point at 1.08 m is accessible to the 0.5 m actor.

All nine required actual-import views were inspected: LOD0 neutral, rear, detail, joinery and gameplay; LOD1/2 neutral and gameplay. The final table has continuous board grain, fitted load paths, closed thin parchment, seated weights and connected tool/wallet fittings. Distant LODs preserve the table silhouette; tiny map labels are naturally not readable at 12/24 m.

The current-byte gate passes three genuine LOD reductions, finite unit orthogonal normals/tangents, authored UVs, six embedded PBR sets, exact source/export/image hashes, six packed masters, construction contacts, ground probes, full collision coverage and front approach clearance. Khronos reports zero errors and zero warnings at all LODs. It emits one informational NPOT-image note per LOD for the map image, whose aspect preserves its typography.

Limits: static scenery only; the chart is schematic and has no map interaction. No tool pickup, tabletop walking or world-placement/gameplay acceptance is claimed. Root owns publication, manifests, GM/map placement and live collision checks. The generation receipt says technical_review_pending and builder runtimeReady is false only because publication is owned by root; validation.json is passed. No authoring defects are known from the scoped checks.

Ownership: only authoring/blender/field-command-table/ was written. Existing rack, farmer and herbalist packages were not edited. Keep this package immutable during publication.
