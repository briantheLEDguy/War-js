# Reimport visual review — before full surface-channel transfer

Reviewed 2026-09-06. This record covers the actual GLB reimport renders listed below, before the revised high-source base-color, roughness, and metallic transfer. It is an intermediate review, not final acceptance. No geometry, textures, or pipeline files were edited for this review.

## Findings

- LOD0 front, three-quarter, side, and back retain all visible major armor modules, the hammer, and accessories. No renewed chainmail penetration through the thigh cuisses or obvious inverted-normal patch is visible in these views. Steel, brass, crimson cloth, leather, parchment, and chainmail remain distinguishable.
- LOD1 and LOD2 lose important brass surface color while retaining broken gray relief: the breastplate diagonal V bands and the paired shoulder crosses. This is a visible material discontinuity between LODs and should be rechecked after the new transfer bake.
- LOD2 collar lettering becomes disconnected pitted relief. It needs color transfer from the authored source when the lettering geometry is omitted.
- Large character, plate, weapon, and accessory silhouettes remain substantially consistent across the three supplied front renders. LOD2 introduces visible facial facets and angular trim at this close comparison scale; its transition distance still needs evaluation in the game.
- These frames do not establish motion acceptance. Known tabard cross/hem intersections in run/jump are being addressed separately. The character remains stylized and does not achieve photographic likeness to the reference.

## Exact source associations

| Visible region | Authored source part | Observation |
|---|---|---|
| Brass chest V bands | `breastplate.json::breastplate_diagonal_reinforcement`; adjacent `breastplate_reinforcement_steel_inset` | V bands are retained in LOD1 but read as broken gray scars. A reduced shell may bury part of the original trim; normal-only source transfer does not restore brass color. |
| Both shoulder crosses | `pauldron.json::left_pauldron_sun_cross_emblem`, mirrored | Retained in LOD1; largely absent as brass and replaced by pale/dark surface flecks. |
| Collar creed | `gorget.json::gorget_creed_inlay` | Omitted from LOD2 geometry; gray relief survives without consistent dark inlay color. |

The diagnosis of burial versus material transfer is an inference from the rendered surface and source/runtime part lists. The revised bake should be inspected rather than assumed to solve it.

## Comparison evidence

- `reimport_lod_material_detail_comparison.png`: equal source-pixel crops of LOD0, LOD1, and LOD2, including the affected chest, shoulders, and collar.
- `reimport_lod_visual_comparison.png`: equally scaled full-figure front images for overall silhouette review.

## Reviewed image hashes (SHA-256)

| File | SHA-256 |
|---|---|
| `reimport_lod0_full_front_material.png` | `fcf9d34ad4ded148c5565d66b3a0ae798efba7aa6de777af510fdc077f716e5b` |
| `reimport_lod1_full_front_material.png` | `d73eecb3ef55d76a287004cb996930d1809d894ff29b1b50be4e0d1768eedd29` |
| `reimport_lod2_full_front_material.png` | `e6d3b5deaf01a7f8f99ce7d552360f03dbe4a8242c8c047adf407e5134e2e56b` |
| `reimport_lod0_full_three_quarter_material.png` | `42fff89f0c27cf566621cd0f3280dc46ecf29300c9d25384b5e14eee55398d97` |
| `reimport_lod0_full_side_material.png` | `d0b5140cc159d50f726d0fb37bf72ec4551aff6202ccb2283c1095f8103d6742` |
| `reimport_lod0_full_back_material.png` | `2d318ca7cb7bcb5c770d4054061b25560e0910c703ddf5bc8c0d2063cc8a39c4` |

Pending: inspect the replacement bake and reimport images, especially color continuity and residual relief artifacts in these same regions.
