# Sunmeadow canopy revision

Three revised originals: pasture oak, hedgerow oak and common ash. Connected interior shoots, varied leaf inclination and asymmetric crown infill improve ground-level foliage coverage. Individual opaque shaped leaves remain geometry; no cards, hulls or primitive foliage substitutes are used. The other four accepted nature assets are unchanged.

All three real LODs have editable packed Blender masters, explicit botanical source, embedded base color/normal/ORM textures, and actual GLB reimport views. LOD2 uses larger leaves to retain distant canopy coverage and is intended for approximately 90m viewing. It should not be selected at close range. Static wind-free vegetation remains a limitation; runtime performance still requires measured scene testing.

| Asset | LOD0 triangles | LOD1 | LOD2 |
|---|---:|---:|---:|
| Pasture oak | 94,774 | 50,784 | 13,008 |
| Hedgerow oak | 70,008 | 37,496 | 9,632 |
| Ash | 95,516 | 51,682 | 19,820 |

Run from the repository root:

```powershell
node --test authoring/blender/sunmeadow-nature/revisions/canopy-v2/tools/review_evidence.test.mjs
node authoring/blender/sunmeadow-nature/revisions/canopy-v2/tools/publish_nature.mjs --prepare-review
node authoring/blender/sunmeadow-nature/revisions/canopy-v2/tools/publish_nature.mjs --publish
```

The publisher requires explicit internal approval in `review/visual_review.json`, bound to current build records, all six images per tree, both group images and the equal-scale contact sheet. Preparation never infers approval. Publication archives previous public GLBs, QC, blueprints and approved records by content hash before replacement. Original accepted Blender sources and review receipts remain in the parent package. Registry compilation remains a separate integration step.
