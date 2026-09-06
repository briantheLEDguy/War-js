# Fixed reference comparison

This is a read-only review of actual Blender renders and the original reference
crop. The script writes only `review/comparison*`. It does not edit Blender,
source meshes, cameras, materials, or reference pixels, and does not fit images.

The frozen authoring convention is:

```text
x_reference = 254.282 + world_x / (1.86 / 633)
y_reference = 729 - world_z / (1.86 / 633)
```

For the declared front camera, Blender orthographic width is 1.01 m at 1100 x
1000 pixels with square pixels and the default horizontal fit. Image height is
1.01 * 1000 / 1100 m. The optical center uses width/2 and height/2. The script
rejects a changed front camera or a mismatched scene/build hash instead of
silently updating this convention. No matching algorithm is used.

The reference upper-body crop and aligned actual renders are displayed at the
same scale. Reference enlargement does not create new detail. The 50/50 overlay
blends existing pixels; no synthesized character or replacement reference is
used. A cyan landmark circle is the illustration estimate; a magenta cross is
a named source control vertex transformed by the matrix recorded in the build.

Distances are 2D authoring-plane discrepancies. They are not calibrated physical
errors, and control-cage points are not necessarily points on the final
subdivided surface. Reference occlusion, perspective, orientation, illustration
inconsistency, and pose remain unresolved. The nominal distance band is advisory;
even zero landmark error does not establish facial likeness or an acceptable
character. The pauldron-crown pairing is explicitly low confidence.

`comparison_report.json` records input hashes, named pairings, uncertainties,
source/render binding evidence, and source files newer than a render. Missing
source hashes in the build make the current-source/render pairing unverified.
Regenerate after rebuilding and rendering any changed source records.

Semantic pairing revision 002 replaces the earlier F11 breastplate-shell
waist-center surrogate with the actual belt upper-front center: the explicit
stable vertex v000 in heavy_relic_belt. This changes the diagnostic pairing only;
source vertices, camera calibration, and reference pixels remain unchanged.
F05 remains a low-confidence guard/main-shell crown correspondence.

Run with the bundled Python/Pillow interpreter:

```powershell
& 'C:/Users/bschm/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/compare_reference.py
```

This diagnostic does not establish visual acceptance or runtime promotion;
see runtime_visual_review.json for that separate decision.
