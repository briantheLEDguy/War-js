# Cinderfen architecture

Original geothermal-marsh architecture for fen workers and Dark Elf supply staff:
raised alder dwellings and workshops, an open supply shelter, a basalt and timber
curtain, a six-metre gatehouse, paired animated leaves, a switchback wall stair
and an independently exported corner with a supported courtyard gangway.
All eight modules are internally accepted and locally published. Named review
receipts bind the exact model hashes and 59 required export/assembly images.
The global registry and campaign activation are handled separately by root.

## Source and construction

`tools/author_source.py` retains the original drawn construction cages and their
finite placements. `source/architecture.json` is the serialized editable source.
The pieces have real thickness: battered mineral footings, grown alder piles,
scarf shoulders, curved knees, comb-cut reed bundles, fitted roof bindings, open
rain troughs, overlapping ceramic caps, cambered vault stones and driven pins.
No Blender primitive constructors or Sunmeadow geometry are used.

`tools/paint_surfaces.py` authors fourteen material fields from retained grain,
cleft, mineral, weave and wear strokes. Height, roughness, normal and ORM channels
are distinct; occlusion represents material cavities, not baked illumination.
UVs tile at physical metre scale after each construction piece is fitted. Shared
UV space is intentional for reusable materials and repeated construction pieces.
It is not a unique lightmap atlas.

The revised roof has down-slope overlapping sheaves, irregular comb-cut ends,
dedicated cut-pith surfaces and hollow projecting reed tips. Five drawn basalt
cleavage patterns sit on recessed ash bedding; alder cladding uses separate
fitted boards and longitudinal grain. These visible surfaces received an internal
material review followed by complete module and assembled keep acceptance.

The finishing, export, texture-packing and publication utilities were adapted
from the accepted Sunmeadow architecture pipeline. Their geometry and painted
pixels were not reused. Source provenance records preserve exact tool hashes.
Each Blender master retains the individual finished placements and original
control cages. LOD1 simplifies edge finishes and roof courses. LOD2 retains the
curved silhouette, roof thickness, real passage and deck heights with explicit
coarse boundaries and fewer distant construction seams. Gate leaves remain
independent rigid meshes with `gate_open` and `gate_close` clips.

## Files

- `DESIGN.md`: regional art direction and intended placement rules.
- `source/`: original serialized cages, placements and provenance.
- `masters/`: seven editable `.blend` files with packed source materials.
- `textures/source/`: retained source channels and painted-stroke records.
- `textures/cinderfen_architecture/`: content-addressed shared export textures.
- `runtime/`: three GLBs per module, with shared texture references.
- `review/`: actual GLB imports, neutral and gameplay-distance PNGs, mechanical
  views, positional topology, doorway and support audits, validation receipts.
- `build-report.json`: exact model bounds, triangle counts, hashes and contracts.
- `navigation-contract.json`: integration-facing Y-up bounds, sockets, supports
  and colliders. `completeReimportReview` distinguishes a preliminary technical
  export from a complete measured review; `runtimeReady` requires publication.
- `junction/`: independent corner source, Blender master, three GLBs, material
  references and actual joined-corner/stair review.
- `builder-metadata.json`: approved model hashes with model-space collider,
  walking-surface and gate defaults for all entries exposed in the GM builder.
- `validation.json`: current technical result; not an art approval.

## Rebuild and review

Run from the repository root with Python, Pillow and NumPy installed. Blender
5.0 is available locally at the path below. Coordinate with other Blender jobs;
the package uses three threads rather than taking all CPU cores.

```powershell
python authoring/blender/cinderfen-architecture/tools/author_source.py
python authoring/blender/cinderfen-architecture/tools/paint_surfaces.py
python authoring/blender/cinderfen-architecture/tools/test_source.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/cinderfen-architecture/tools/build_architecture.py
python authoring/blender/cinderfen-architecture/tools/share_textures.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/cinderfen-architecture/tools/audit_geometry.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/cinderfen-architecture/tools/review_exports.py
node authoring/blender/cinderfen-architecture/tools/validate_architecture.mjs --geometry-only
python authoring/blender/cinderfen-architecture/junction/tools/author_junction.py
python authoring/blender/cinderfen-architecture/junction/tools/test_source.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/cinderfen-architecture/junction/tools/build_architecture.py
python authoring/blender/cinderfen-architecture/junction/tools/share_textures.py
node authoring/blender/cinderfen-architecture/junction/tools/validate_architecture.mjs --geometry-only
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/cinderfen-architecture/junction/tools/audit_geometry.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/cinderfen-architecture/junction/tools/review_exports.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/cinderfen-architecture/junction/tools/review_assembly.py
node authoring/blender/cinderfen-architecture/tools/test_placement.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --factory-startup --threads 3 --python-exit-code 1 --python authoring/blender/cinderfen-architecture/tools/review_keep_assembly.py
python authoring/blender/cinderfen-architecture/tools/write_provenance.py
python authoring/blender/cinderfen-architecture/junction/tools/write_provenance.py
node authoring/blender/cinderfen-architecture/tools/validate_architecture.mjs
node authoring/blender/cinderfen-architecture/junction/tools/validate_architecture.mjs
python authoring/blender/cinderfen-architecture/tools/contact_sheet.py
python authoring/blender/cinderfen-architecture/junction/tools/contact_sheet.py
node authoring/blender/cinderfen-architecture/tools/test_blueprints.mjs
```

`--geometry-only` runs Khronos/PBR/count checks before image review. It cannot
publish. Every final GLB needs a new hash-bound neutral view and a perspective
view at 40, 90 or 160 metres for its respective LOD. The gatehouse also needs its
front view and full-depth passage ray check; leaves need both imported clips and
opened views; the stair needs an unobscured side view and tread-support audit.
Required closeups show actual workshop grain, the reed edge and basalt. The
complete keep review imports LOD1 modules at the exact source transforms and
checks every perimeter, gangway, stair tread and preserved service approach.
The navigation test executes the shared authority support/collision functions
with a finite player footprint and both owner passage pairs through closed gates.

After a named internal reviewer accepts the exact exports, `review/review.json`
must bind the final build-report hash, contact-sheet hash and every review image.
Then publication is local and scoped to this package:

```powershell
node authoring/blender/cinderfen-architecture/tools/validate_architecture.mjs --publish
node authoring/blender/cinderfen-architecture/junction/tools/validate_architecture.mjs --publish
node authoring/blender/cinderfen-architecture/tools/merge_builder_metadata.mjs
node authoring/blender/cinderfen-architecture/tools/test_published.mjs
node authoring/blender/cinderfen-architecture/junction/tools/test_published.mjs
```

The publisher writes uniquely named blueprints, approved records, GLBs, QC and
shared textures. It does not compile the global registry or edit maps. Any model,
source, texture or required review-image change invalidates the matching receipt.
Do not mark a technical pass as a completed internal art review.
Re-run the metadata merge after republishing the main package: it deliberately
owns seven entries, while the independent companion publishes the eighth. The
campaign placement source remains `scripts/campaign/cinderfen-environment.mjs`;
root integration activates it only after the complete package is accepted.
