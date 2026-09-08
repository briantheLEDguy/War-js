# Cinderfen landscape

Draft, not runtime approved. Sixteen 300 m sectors cover the 1200 m region.
The survey is authored in `scripts/campaign/cinderfen-landscape.mjs`; shared
Float32 heights define both footing and exported explicit surface topology.
The existing curved campaign roads and logistics destinations remain stable.

The new landscape contains three shallow peat basins, basalt watersheds and
raised scouting banks. Surveyed zero-height causeways, keep pads, the enlarged
settlement pad and four supply pads preserve measured architecture placement.
Water is clipped to the survey at -0.35 m and carries `noGroundSupport` metadata;
GM footing follows the bottom, not the decorative water surface.

`build_terrain.py` and `road_junctions.py` derive from the project's reviewed
Sunmeadow surface authoring tools. The original tools remain unchanged. All
topology is explicit, with metre-based UVs, normal detail, alpha-blended road
verges and shared sector boundaries. Blender primitive operators are not used.
Albedos are new image-generated peat and basalt-fines sources retained in
`textures/source`; microrelief and shallow-water normals are analytical material
detail, not high-poly transfer bakes. Original generated images remain retained
under the user's Codex generated-images directory.

Run from the repository root:

```powershell
npx tsx authoring/blender/cinderfen-terrain/export-source.ts
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b -t 3 --python authoring/blender/cinderfen-terrain/build_terrain.py
node authoring/blender/cinderfen-terrain/validate.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b -t 3 --python authoring/blender/cinderfen-terrain/review_terrain.py
```

Masters, exact model/texture hashes and actual-GLB render receipts are retained.
Publication requires explicit internal visual acceptance of those exact bytes;
technical validation alone does not activate the terrain or mark the zone complete.
