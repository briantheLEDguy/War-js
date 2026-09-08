# Sunmeadow architecture

Six original, editable architecture modules for the Sunmeadow frontier. Limestone courses, timber joints, slate courses, dressed arches, splayed arrow slits, forged fittings and cloth pennants share a coherent Aegis regional vocabulary. The source was developed against the Aegis city material/construction references and the Battle Prelate reference rebuild's expectations for retained geometry, surface channels and actual export review.

This package supplies a regional construction kit. It does not represent Riftbound architectural identity or completion of every campaign zone. The review record establishes acceptance of the exact assets; technical validation alone does not assert art approval.

## Runtime placement contract

Runtime GLBs are metre-scaled, Y-up, grounded at the centre of the footprint. Front is **+Z**. Source cages and placement records use Blender Z-up, front **−Y**. Convert source `(x,y,z)` to runtime `(x,z,-y)`, including the wall-segment coordinates below. A southern keep entrance therefore uses `rotationY = Math.PI`.

| Static key / file stem | Wall footprint | Opening | Placement notes |
|---|---:|---:|---|
| `frontier_sunmeadow_farmhouse` | 8 × 10 m | 1.6 × 2.5 m | Roof envelope about 9.4 × 11.4 m; front entrance, interior floor, open leaves, shutters and chimney. |
| `frontier_sunmeadow_workshop` | 10 × 8 m | 2.6 × 3 m | Roof envelope about 11.4 × 9.4 m; upper timber/plaster grain loft with ladder opening. |
| `frontier_sunmeadow_supply_post` | 8 × 5 m | 5.6 × 3.1 m | Roof envelope about 9.2 × 6.2 m; open front bay, fitted knee braces, side benches. |
| `frontier_sunmeadow_gatehouse` | 28 × 12 m | 6 × 4.8 m minimum | Full-depth central passage, roofed sentry towers, central parapet and curtain wings. No blocker or gate leaf is baked into the passage. |
| `frontier_sunmeadow_curtain_wall` | 8 × 2.2 m | — | Repeat on an 8 m centre spacing. Nominal end planes ±4 m; small dressed-stone overlap covers the seam. Wall walk 6.3 m; crenellations about 8.3 m. |
| `frontier_sunmeadow_gate_leaves` | 6 × 0.65 m | 6 m closed span | Pair of 4.8 m timber leaves. Pivots `(−3,0,0)` and `(3,0,0)`; no masonry frame. |

Each stem has `_lod0.glb`, `_lod1.glb` and `_lod2.glb`. The exact measured bounds, rather than the nominal design envelope, are recorded per LOD in `build-report.json`. Collision uses the authored `contract.collision_walls` segments with `wall_thickness`; do not use a filled rectangle for an entrance-bearing building. These are placement data, not visible proxy geometry. Roof overhangs are excluded from ground movement blockers. The gatehouse's whole-footprint blocker must also remain split around the six-metre passage. Tower interiors are visual architectural shells; this package does not implement navigation to the upper wall walks.

The gatehouse curtain-wing sockets lie on local runtime **Z=+4.6 m**, ending at **X=±14 m**, rather than across its footprint centre. At rotation Y=π, put the gatehouse centre 4.6 m north of the joining curtain line. Sunmeadow's outer/inner curtain lines at Z=−24/−7.5 therefore use gatehouse centres Z=−19.4/−2.9 and leaf centres Z=−25.4/−8.9. The measured wing midline is Z=+4.623 m, providing a small fitted stone overlap with the adjoining curtain sections.

The gate leaves expose stable nodes `gate_leaf_left` and `gate_leaf_right`. `gate_open` and `gate_close` each contain both rigid rotation channels, lasting 1.2 seconds. Opening rotates the leaves inward by 90 degrees. The authoritative campaign gate controls the central blocker and damage state separately; remove the central blocker when the gate is open or destroyed. Do not animate the entire gatehouse as a leaf. Gate artwork supplies no separate broken-state debris model.

## File architecture

- `tools/author_source.py`: original literal shaped vertex/facet records, per-corner UVs and finite placement records for 19 construction components and six modules. No Blender primitive constructors or imported generic proxy meshes.
- `source/architecture.json`: serialized editable source geometry, UVs, material assignments, component descriptions and placement/collision contracts.
- `tools/paint_surfaces.py`: retained original grain, fissure, pit, cloth and localized wear strokes; 13 original 1024 px PBR material sets.
- `textures/source/`: base color, normal, packed occlusion/roughness/metallic, independent height and roughness source maps. `paint_records.json` retains stroke coordinates and image hashes.
- `tools/build_architecture.py`: Blender construction, fitted-edge finishing, protected opening/join geometry, three LODs, packed editable masters and hinge animation authoring.
- `masters/`: editable `.blend` files with the original cages, individually placed construction pieces and final mesh forms. Gate masters retain both animation clips.
- `runtime/`: staged final GLBs. `textures/sunmeadow_architecture/` contains the shared exported texture pixels, named by their full SHA-256.
- `tools/share_textures.py`: exact image deduplication. It retains the input/output GLB hashes and changes image storage only; geometry, material channels and animation accessors remain intact.
- `tools/audit_geometry.py`: positional topology and front-opening checks on fresh final GLB imports.
- `tools/review_exports.py`: fresh GLB reimport renders for every LOD, front gatehouse view, gate motion renders and measured clearance/animation records.
- `tools/validate_architecture.mjs`: hash, topology, passage, animation, LOD, material, image, source and Khronos validation; pending blueprint generation; optional reviewed publication.
- `review/`: build measurements, actual reimport PNGs, geometry audit, per-model Khronos reports, logs and the contact sheet. `build-report.json` aggregates the six source/build records and final LOD measurements.

Material UV overlap is intentional: repeated stone, slate, timber and hardware reuse their original material coordinates. This is tiled material sharing, not an accidental overlapping bake atlas. Tangent-space normal maps derive from independent physical relief fields, not luminance from a shaded beauty image. ORM red contains authored material cavity; it is not a scene-lighting bake. Base color contains localized dirt, soot and fabric/wood/stone coloration. Three.js and Blender supply the scene lighting.

All authored cages are closed shells. The final topology audit welds glTF material/UV/normal split positions at a one-micrometre tolerance and requires zero boundary edges. The distant wall-walk slabs touch at exactly fitted lower ends: seven coincident four-face edges in curtain-wall LOD2, and six in gatehouse LOD2, all at source Z=6.12 m. The validator checks the precise joint coordinates and rejects other multi-face edges. These separate closed slabs do not require a boolean union. UV sharing and those particular slab joins are the only allowed overlaps/topology exceptions.

LOD2 masonry, slate and coping use explicit coarse outer-boundary cages retained in `source/architecture.json`; they preserve thickness and fit. Distant mortar filler is omitted. Arch/opening pieces are protected and reduced components stay within their authored envelopes, so distant construction cannot protrude into the clear opening. The nearby LOD retains all original fitted detail.

## Rebuild and validate

Run from the repository root with Python including Pillow/NumPy, Node dependencies installed and Blender 5.0 available:

```powershell
python authoring/blender/sunmeadow-architecture/tools/author_source.py
python authoring/blender/sunmeadow-architecture/tools/paint_surfaces.py
python authoring/blender/sunmeadow-architecture/tools/test_source.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python authoring/blender/sunmeadow-architecture/tools/build_architecture.py
python authoring/blender/sunmeadow-architecture/tools/share_textures.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python authoring/blender/sunmeadow-architecture/tools/audit_geometry.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python authoring/blender/sunmeadow-architecture/tools/review_exports.py
node authoring/blender/sunmeadow-architecture/tools/validate_architecture.mjs
node authoring/blender/sunmeadow-architecture/tools/test_blueprints.mjs
python authoring/blender/sunmeadow-architecture/tools/contact_sheet.py
```

`--geometry-only` on the validator checks the binaries and generates pending blueprints before rendering is complete. It cannot publish. Re-run the complete validator after every final GLB reimport. Blender may return exit code zero after a Python exception; check the final `ARCHITECTURE_EXPORTED` / `ARCHITECTURE_REIMPORTED` records and validator output, not the process code alone.

## Internal visual acceptance and publication

Inspect all 18 actual reimport PNGs, the gatehouse front view and gate-leaf opened views. After acceptance, the integration reviewer writes `review/review.json`:

```json
{
  "approved": true,
  "reviewedBy": "reviewer name",
  "reviewedAt": "ISO-8601 timestamp",
  "buildSha256": "SHA-256 of build-report.json",
  "previewSha256": "SHA-256 of review/all-exports.png",
  "heroSha256": {
    "frontier_sunmeadow_farmhouse_lod0_reimport.png": "SHA-256 of that PNG"
  }
}
```

`heroSha256` must contain every LOD's reimport image, the gatehouse front view and all three opened-gate views: 22 images, not just the example entry. The exact filename/hash pairs are each LOD's `reviewImages` field in `build-report.json`. The publisher rejects a stale build or missing image coverage. This is an internal review mechanism; it does not require another user permission question. The authoring tool does not invent or automatically grant visual acceptance.

```powershell
node authoring/blender/sunmeadow-architecture/tools/validate_architecture.mjs --publish
```

Publication copies the models and shared textures, writes standard hash-bound QC sidecars, adds accepted blueprint lifecycle metadata and approved asset records. It **does not** compile the global runtime registry or change maps. The integrating task performs the established registry compilation and runtime verification afterward.

`tools/test_published.mjs` independently checks the six approved records, all 18 published model hashes, each QC signature and every shared texture byte. Texture lists are present in both `builtLods` and `lods`, and in each model's top-level QC. Multiple glTF image slots may reuse one signed image URI; the signature list contains each URI once.

## Composition verification

The package's read-only map audits are separate from asset acceptance. `audit_composition.mjs` snapshots the current source composition and checks placement contracts. `audit_traffic.mjs` tests complete measured LOD0 roof envelopes against every road segment and lane width, plus other building envelopes. `audit_service_clearance.py` samples actual imported LOD0 surfaces over a 0.5 m radius and 0.3–2.2 m standing height at NPC, service, keep-use and building entrance positions. The sampled headroom check supplements the application's collision and route tests; it does not replace them.

```powershell
node authoring/blender/sunmeadow-architecture/tools/test_published.mjs
node authoring/blender/sunmeadow-architecture/tools/audit_composition.mjs
node authoring/blender/sunmeadow-architecture/tools/audit_traffic.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python authoring/blender/sunmeadow-architecture/tools/audit_service_clearance.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python authoring/blender/sunmeadow-architecture/tools/audit_building_pair.py
```

Final composition findings are retained in `review/*_audit.json`. Gate-wing joins, all eight shelter wall colliders and the apothecary road placement were corrected in the campaign source by the integration task. The salvage shelter and workshop have overlapping conservative overhead envelopes but zero actual triangle intersections, so their positions remain unchanged. The final service check recorded 35 positions and 1,781 rays without an obstructed sample.

The acceptance record applies to these six Sunmeadow modules and their exact pixels/geometry. It does not claim every region, faction, architectural interior or future destruction state meets the Battle Prelate acceptance scope.
