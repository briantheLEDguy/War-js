# Regional inhabitants

This package is in authoring. Its anatomical inputs and draft exports are not
runtime-approved characters.

The first cast covers an Empire farm worker and herbalist, a Dwarf workshop
craftsperson, a High Elf field scout, a Greenskin peat worker and a Dark Elf
supply officer. Clothing, tools, body proportions and animation must fit each
role and climate. Population IDs and services remain owned by campaign content.

`tools/retain_foundations.mjs` retains the existing local MPFB anatomy, embedded
MakeHuman textures, original Blender masters and QC bytes under `foundations/`.
It rejects a changed input instead of silently replacing retained provenance.
The original masters refer to unavailable external texture paths; the companion
GLBs retain those image bytes, and new editable masters must pack them. This
does not require reinstalling MPFB or downloading new content.

New garments use fitted authored surfaces with real hems, collars, closures,
layering and work equipment. Racial morphology changes anatomical meshes and
rest joints together. No primitive models or visible proxy fallbacks are allowed.
Every derivative needs neutral and game-lighting export review, three real LODs,
grounded deformation, texture and source hashes, and an explicit approval receipt.

The dwarf's forearm and cuff correction has passed its bounded visual review.
The complete character remains a draft while all nine clips, clothing and ground
contact are checked. Its canonical core skeleton has one additional internal
`apron_lower` joint for the leather panel's waist fold; its clip names stay
`idle`, `walk`, `run`, `combat_idle`, `attack_melee`, `attack_ranged`, `cast`,
`death`, and `jump`.

`tools/inspect_arm_volume.py` measures complete skin sections at actual GLB keys
and their midpoints. `tools/inspect_export_motion.py` measures each material's
edge deformation, fitted arm travel and ground contact across all nine clips.
`tools/inspect_garment_clearance.py` checks the separate apron surface against
raised knees, the trouser hems against their boot interiors, and actual belt
edge/triangle intersections against the apron in every clip. Matching a
technical gate does not confer visual acceptance. The review renderer
and `tools/make_motion_sheets.py` retain image/model hashes; the package-local
`review/inhabitants.html` viewer verifies its GLB before offering clip, time and
LOD controls. These tools do not write game placements.

The build preserves continuous retained surface weights while relaxing them
with tailored fabric. Editable subdivision/thickness precedes armature
deformation, matching the exported result. Undefined LOD tangents are repaired
only from neighboring UV derivatives, with the exact affected vertices recorded
in the build report.

The current motion revision gives the dwarf fitted bent-arm counter-swing and
relaxed idle hands. The apron belt follows its exterior contour and cloth
weights; the working hammer is fitted behind the hip for motion review.
Boot laces follow their curved supporting leather, and tucked wool follows the
same ankle deformation field as the boots. The complete character remains draft
until current export renders, contact evidence and material review are accepted.
`apron_details.py` constructs the continuous neck loop and the closed binding
from the finished panel boundary. `surface_bindings.py` samples the supporting
cloth's actual skinning weights for those details and the belt. The lower apron
keeps its torso ease when the shirt hem is tucked beneath it.
The belt profile comes from exact garment cross-sections. During the prone fall,
the actual buckle/panel surface supports the torso before limb contact is fitted;
untouched parent animation interpolation is preserved throughout that bake.

`workwear_finish.py` binds cuff and shoulder stitches to the shirt surface and
maps apron wear to its perimeter and pocket use areas. The linen weave and
directional hair maps remain embedded in every export, with editable source
construction retained in the master. All finishes still require close visual
review at all three LODs; a successful technical report is not publication.
Shoulder seams use the exterior cloth surface, excluding the thickness lining.
`probe_hair_finish.py` creates a separate GLB for bounded head-material review
from the current master without replacing the master or runtime exports.

Current inspection:

```powershell
node authoring/blender/frontier-population/tools/retain_foundations.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --threads 2 --python-exit-code 1 --python authoring/blender/frontier-population/tools/inspect_foundation.py
node authoring/blender/frontier-population/tools/validate_inhabitants.mjs
python authoring/blender/frontier-population/tools/test_inhabitant_exports.py
```

The export regression test requires current three-LOD arm and full-motion audit
reports. A stale report or failed geometry/contact check fails the test; it must
be regenerated and inspected against the new binary before approval.
Its seven gates cover binary/clip validity, arm volume, full-motion contact and
deformation, apron clearance, boot/hem clearance, alternating bent run arms and
belt/apron separation. The final death hand contact is measured per hand, so one
grounded body point cannot conceal a floating opposite hand.
