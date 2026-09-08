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

Current inspection:

```powershell
node authoring/blender/frontier-population/tools/retain_foundations.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --threads 2 --python-exit-code 1 --python authoring/blender/frontier-population/tools/inspect_foundation.py
```
