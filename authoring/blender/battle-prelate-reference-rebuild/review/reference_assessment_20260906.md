# Full-figure reference assessment

Read-only geometry assessment of `rig_full_front_material.png` and
`rig_full_three_quarter_material.png` against the supplied Battle Prelate design
sheet. These renders precede the latest skin and chainmail maps. Material
appearance in them is therefore not a review of the final baked asset. No mesh,
texture, camera, or rig changes were made for this assessment.

The tall gorget, broad shoulder silhouette, chest medallion, red central garment,
hip book, censer and large sanctified hammer identify the intended design. They
do not yet establish the requested photographic likeness. The model is visibly
cleaner, simpler and less densely constructed than the illustration.

| Priority | Visible difference | Targeted correction within the existing workflow |
| --- | --- | --- |
| High | The broad brown waist band is almost uninterrupted. The reference has a large central reliquary buckle, layered straps, chains and small metal fittings that make the waist a major focal point. | Add the central buckle first, then a few explicitly placed chain/medallion and strap fittings. Preserve current belt attachment and slot. This addresses a conspicuous blank region without changing the rig. |
| High | The face remains stylized: a smooth full forehead, thin arched brow shapes, fine eye slits, and simplified cheek, nose, mouth and jowl transitions. The reference has a heavy bony brow, deep-set eyes with aged lids, a broader blunt nose, pronounced cheek/jaw planes and a tightly compressed stern mouth. | Refine the existing authored head cage locally at brow overhang, upper/lower lids, nose wings, cheek-to-mouth fold and jaw/jowl. Skin color and crease paint can support those forms but cannot replace them. Review a neutral face crop before treating this as resolved. |
| Medium | The tabard emblem reads as a long thin staff with a short crossbar. The reference has a much broader, branched ornamental cross. | Widen the horizontal arms and add the authored stepped/flared terminals and a central boss while retaining garment folds and attachment. |
| Medium | Large armor regions are smooth single shells with sparse borders. The reference has more overlapping seams, small construction breaks, fasteners and layered brass edges, especially around the forearms, upper arms, waist and greaves. | Prioritize a second visible cuff/edge band at the wrist and elbow, then selected plate seams and fasteners. Keep large silhouette features in geometry; bake shallow engraving. Adding scratches alone will not supply plate construction. |
| Medium | The knee motifs read as large angular masks with triangular sockets and tooth stripes. The reference uses smaller skull reliefs nested in additional circular/shield borders. | Reduce the visual dominance of the skull face and add an inner border/boss around it; soften the authored skull's cheek and jaw contour without flattening the raised relief. |
| Medium | The pauldron crowns are very smooth broad domes, with exposed inner supports and simple lower lames. The reference's shoulder is denser, with a more definite raised inner defense and overlapping outer shell/trim. | Inspect the shoulder in the aligned comparison pose. If the support remains conspicuous, deepen the existing shell return and improve the overlap locally rather than enlarging the entire shoulder. Preserve the broad outer silhouette, which is already recognizable. |

## Pose and reference uncertainties

- The current front render has open hands and outward arms. The reference holds
  the hammer in a closed gauntlet with the opposite arm closer to the body. Hand
  gaps and the arm-to-torso silhouette are not reliable geometry errors until
  compared in the matching pose. The gauntlet plate bulk still warrants checking
  once the fingers are closed.
- The render has a more upright, narrow leg stance. The illustration spreads and
  rotates the feet, and its nominal front view has some torso turn. Match the
  comparison pose before changing bind-pose leg spacing or calling knee/ankle
  offsets a proportion failure.
- The main hammer head and shaft have a comparable overall scale relationship to
  the body. Its simpler collars, face hardware and relief ornament are more
  defensible correction targets than a wholesale size change.
- The book and censer occupy the intended lateral hip region. Their exact tilt,
  chain drape and hanging height vary between the sheet's views; use the chosen
  primary front appearance and verify joint clearance rather than averaging
  incompatible illustrated poses.
- The four illustrations are not exact orthographic projections. This assessment
  is qualitative and does not claim the 2% landmark tolerance has passed. Use the
  frozen comparison cameras and named landmarks for the quantitative diagnostic.

## Pending final material review

Inspect the actual baked/reimported renders for visible small chainmail links,
skin warmth and crease restraint, dark weathered steel versus brass separation,
roughness variation, and preservation of normal detail. The source review above
must not be mistaken for acceptance of the final runtime export.
