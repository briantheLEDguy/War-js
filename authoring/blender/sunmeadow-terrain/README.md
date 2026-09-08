# Sunmeadow authored landscape

Sixteen 300 m sectors cover the 1,200 m zone. Each sector has an editable Blender
master and three exported GLB levels. Geometry is built from explicit survey
topology, never Blender primitive operators. The shared authoritative Float32
height grid remains the movement surface. LOD0 samples it at 1.5625 m; coarser
levels retain every sector border sample to prevent cracks.

`scripts/campaign/sunmeadow-road-network.mjs` is the physical road graph and the
source for caravan itineraries. The winding march road connects the three
objectives. Branches serve the keeps, farms, staging camps and travel exits.
Routes reuse these roads; overlapping full-width routes are not rendered six
times. Road ribbons have fitted joins, terrain grounding, metre-scaled UVs and
feathered edges. Broad terrain shoulders avoid abrupt grass cliffs beside roads.

`road_junctions.py` adds explicit radial mesh patches only where an authored road
endpoint touches multiple distinct alignments, including endpoint-on-interior
joins. The widest touching road sets the transition radius. The opaque core ends
at half-width minus up to 0.35 m; the transparent rim ends at half-width plus up to
0.6 m. Radial bands are at most 2 m and circumference edges about 1 m. Patches use
the same world UV coordinates, survey elevation, corner RGBA feather and sector
clipping as the road ribbons. A submillimetre layer offset prevents coplanar
flicker. The original road coordinates, widths and authoritative terrain survey
are unchanged by this surface refinement.

The meshes use shared external base-color and normal textures. The original
diffuse sources were generated with the built-in image-generation tool in this
task and are preserved in `textures/source`. Runtime diffuse textures are packed
at 1024 px; analytical microrelief normals are 512 px. These normals describe
sub-millimetre material detail, not a claimed high-poly transfer bake.

## Source prompts

- `sunmeadow_meadow_albedo_v1`: seamless square, top-down flat diffuse albedo of
  a two-metre late-summer meadow; short olive/sage grass, dry tips, tiny clover,
  muted loam, fine medieval fantasy ground detail, no cast shadows, highlights,
  perspective, focal objects, text or borders.
- `sunmeadow_road_albedo_v1`: seamless square, top-down flat diffuse albedo of
  two metres of compact warm grey-beige limestone dust and brown loam; fine grit,
  tiny flakes, subtle scuffs and fissures, low contrast, no wheel tracks, shadows,
  grass, large objects, text or borders.

## Rebuild and review

From the repository root:

```powershell
npx tsx authoring/blender/sunmeadow-terrain/export-source.ts
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python authoring/blender/sunmeadow-terrain/build_terrain.py
node authoring/blender/sunmeadow-terrain/validate.mjs
python authoring/blender/sunmeadow-terrain/test_road_junctions.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python authoring/blender/sunmeadow-terrain/review_terrain.py
node authoring/blender/sunmeadow-terrain/publish.mjs --prepare-review
npx vitest run tests/sunmeadowTerrain.test.ts tests/sunmeadowEnvironment.test.ts
```

Inspect all three actual-export overview images, the close road material
image and `road_junction_lod0.png`, which shows the Aegis keep delivery junction.
Approval is recorded against exact binaries, source, external textures
and render receipts; rebuilding invalidates old evidence. The publisher requires
that review before `--publish`. Run `npm run models:registry` afterward. Enable
the terrain release in the Sunmeadow composer only after approved registry and
runtime checks succeed. Missing or altered assets never install partial terrain.

For a road-surface-only revision, capture the previous land mesh with
`node authoring/blender/sunmeadow-terrain/audit_junction_exports.mjs --capture-baseline`
before rebuilding, then run the same command without the flag afterward. It
requires identical source-file bytes and exact position, normal, UV, color and
index bytes for all 48 terrain surfaces. The original tangent buffers are
retained compressed with verified hashes; recomputed tangents may differ by one
0.0001 exporter quantization step, and the audit records their actual maximum
drift. For a fresh baseline, run `--retain-original-tangents` while the preceding
published models are still available. The audit also checks world UVs,
normalized color channels and sector clipping on the rebuilt roads. Preserve
the existing baseline when reproducing this revision. Prior accepted build and
review receipts are retained under `review/history/`.

With Vite running, open `authoring/blender/sunmeadow-terrain/runtime-review.html`
for the actual local game renderer, seven ground-level inspection locations and
a road overview. The overview disables fog for layout inspection; returning to
a ground location restores gameplay fog. This authoring page disables
character/position persistence.
Its optional foreground timing measurement describes only the current view and
machine, not the campaign's reference-hardware performance target.

Collision is evaluated from the shared survey grid. The original layout's
separate collision asset keys remain planned; these visual GLBs are not filled
box colliders. Terrain approval does not certify finished ecology, wildlife,
NPC variety, siege art or GPU performance for the whole zone.
