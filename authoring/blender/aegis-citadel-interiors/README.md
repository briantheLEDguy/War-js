# Crownwatch citadel furnishings

Fourteen original detailed furnishings support the citadel's household and siege
layout: throne, oath sentinel statue, relief campaign table, arms rack, provision
rack, double bunk, hearth, feast table, archive, counting desk, treasury, reliquary,
chandelier and Aegis tapestry. Heraldry combines original mountain, hearth and leaf
marks for the three allied peoples; no external artwork or borrowed insignia.

`sources/` retains editable Blender masters with separate carved feathers, armour
plates, book bindings, staves, cloth folds, individual table settings and small
props. `runtime/` contains joined delivery meshes and two actually decimated LODs
(52% and 24% targets). Every LOD has UVs, normals and tangents, at most eight
materials, 30,000 triangles and 4MB of mesh data. Five retained 2048px PBR master
surfaces supply wood grain, metal wear, stone grain and woven cloth. Delivery uses
three shared 2048px atlases with per-material UV transforms, so all fourteen kinds
reuse the same GPU images. Runtime GLBs reference those atlases under
`public/assets/textures/aegis_citadel_interiors/`.

All delivery roots are ground level. Models face Blender-Y / glTF+Z. Width, depth
and height envelopes are recorded in `build-report.json`; hanging objects are
grounded at the base of their fixture and placement supplies the mounting height.

Rebuild using Blender5.0 and Python3:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python authoring/blender/aegis-citadel-interiors/tools/build_interiors.py
python authoring/blender/aegis-citadel-interiors/tools/share_textures.py
python authoring/blender/aegis-citadel-interiors/tools/repair_tangents.py
node authoring/blender/aegis-citadel-interiors/tools/publish_interiors.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python authoring/blender/aegis-citadel-interiors/tools/review_interiors.py
```

Inspect the actual-export contact sheet and hero renders before writing
`review/review.json` with matching build/preview hashes. Publish with
`node authoring/blender/aegis-citadel-interiors/tools/publish_interiors.mjs --publish`.
Finally regenerate the model registry and GM catalog from the repository root.
The isolated publisher only writes this kit's GLBs, textures, blueprints and
approved entries. It does not rebuild or replace the existing city architecture.
