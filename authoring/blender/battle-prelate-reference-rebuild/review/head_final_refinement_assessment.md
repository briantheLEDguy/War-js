# Focused head refinement

The retained revision strengthens the inner brow and changes the fine arched
eyebrow ribbon into a heavier, lower inner brow. A slightly more open eyelid
contour and smaller iris/pupil surfaces reduce the previous narrow, sleepy eye
reading. The nasal bridge, tip and wings have more forward projection and breadth;
the lower cheek, jaw and chin are fuller in the oblique view.

The first pass made the eyebrow too neutral and the eye opening too large. The
second restored a firmer inner angle, reduced the iris/pupil proportions and
moderated the lid opening. An overly sharp cheek adjustment was backed off in the
retained source. These are local improvements to the existing cage, not a claim
of photographic likeness: the face remains smooth and stylized, and the
illustration's complex aged facial planes are only partially represented.

`head_final_before_after.png` compares the original and retained material renders.
The unchanged front comparison camera was used for both neutral and material
views. A separate oblique diagnostic camera was recorded once in
`head_oblique_diagnostic_camera.json` and used unchanged for both versions; the
master scene cameras were not modified. Current skin maps and lighting are the
same throughout.

`head_before_final_refinement.json` and
`author_head_before_final_refinement.py` retain the original source. The retained
source changes 106 literal coordinate records, with maximum individual
displacement approximately 17.6 mm. Vertex IDs/counts, face connectivity and
materials, face-corner UVs, modifier settings, creases, seams, transforms and
landmarks are unchanged. Source validation passed. Hashes and the complete
coordinate diff are recorded in `head_final_refinement_report.json` and
`head_final_refinement_coordinate_changes.json`.

No skin maps, other component sources, masters or runtime exports were modified.
The body atlas must be rebaked from the retained head before runtime integration.
