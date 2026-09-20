# Field apothecary worktable

Original universal town/workshop asset `frontier_field_apothecary`, asset ID
`prop.frontier.field_apothecary`. One joined worktable incorporates a drying rack,
three herb bundles, five individually shaped stoppered vials with restraints,
two hollow preparation trays and a stoneware mortar/pestle. It has no realm
insignia or associated preparation/harvesting interaction.

The 2.292 × 1.020 m footprint reaches 1.850 m high. Ground is model Y0; runtime
front is +Z. `builder-contract.json` contains actual structural bounds and separate
colliders, with a 2.20 × 1.10 m working-front reservation. The artwork does not
claim that any particular village placement has passed navigation review.

- `tools/mesh_authoring.py`: original polygon plates, station lofts, vessel
  profiles and thick folded leaf surfaces; no mesh primitive construction.
- `tools/build_station.py`: fitted construction, actual receiving mortises,
  three authored LODs, tangent checks, material batching and literal GLB export.
- `tools/make_textures.py`: deterministic periodic PBR fields; 81 source images
  and their receipt live in `textures/`. No copied art pixels.
- `masters/`: six packed editable source/finished Blender files. Finished masters
  retain hidden original per-part cages and receiving cutters alongside the
  exported surface. Source files preserve unbatched construction.
- `tools/audit_masters.py`: actual saved-master topology, packed images, ground
  contact and named structural collision measurements.
- `tools/review_station.py`: exact GLB reimport, closed positional topology and
  unretouched neutral/detail/game-distance renders in `review/`.
- `tools/consolidate_build.py`: generation/source hash inventory and all three
  per-LOD receipts in `review/frontier_field_apothecary_build.json`.
- `tools/validate_station.mjs`: source/master/image/review hashes, embedded PBR,
  unit orthogonal tangents, true LOD reductions, Khronos validation and accessible
  collision front. `--check` is strictly read-only.

LOD triangles: **38,574 / 19,512 / 8,694**. Nine deliberate PBR material batches
remain at every LOD; this is more complex than the three-material siege bench.
Textures are embedded in every runtime GLB at 1024 / 512 / 256 pixels per set.
Leaf and small fitting geometry reduces with distance; table/rack/vial/tray
silhouettes remain. All present art uses opaque surfaces, including amber vessels.

Build and verify with Python/Pillow/NumPy, Blender 5.0 and the repo's Node tools:

```powershell
python authoring/blender/field-apothecary/tools/make_textures.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --threads 2 --python authoring/blender/field-apothecary/tools/build_station.py -- --lods 0,1,2
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --threads 2 --python authoring/blender/field-apothecary/tools/audit_masters.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --threads 2 --python authoring/blender/field-apothecary/tools/review_station.py -- --lods 0 --views neutral,detail,joinery,rear,gameplay
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --threads 2 --python authoring/blender/field-apothecary/tools/review_station.py -- --lods 1,2 --views neutral,gameplay
python authoring/blender/field-apothecary/tools/consolidate_build.py
node authoring/blender/field-apothecary/tools/validate_station.mjs
node authoring/blender/field-apothecary/tools/validate_station.mjs --check
```

Inspect the current reimport PNGs before publishing. Changing a generator after
export invalidates its generation receipt; rebuild rather than rewriting its
saved hash. Logs of superseded early failures are diagnostic history, not current
acceptance evidence. Root owns public model promotion, maps and GM registration.
