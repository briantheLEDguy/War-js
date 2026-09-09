# Cinderfen woodland floor

This separate draft package supplies a low fallen alder limb and an irregular
fern/wood-sedge grouping for damp shaded woodland soil. The four published
assets in `cinderfen-nature` remain frozen. No woodland-floor runtime asset has
been approved or published yet.

`source/design.json` retains the crooked limb sections, unequal broken-end
offsets, non-radial heartwood fracture survey, seven fern rachis paths and thick
leaf outlines. `tools/author_floor.py` expands them to explicit mesh, material
and corner-UV records for three LODs in `source/floor.json`. It runs in Blender
because constrained triangulation preserves the irregular broken-wood boundary.
No primitive mesh operators or imported geometry participate in construction.

`tools/build_floor.py` currently finishes source geometry, preserves original
limb cages, joins the fork surfaces and checks closed positional topology. Its
`*.source-preview.blend` masters and source review images use flat colors only.
They are shape proofs, not final PBR/export evidence. `tools/paint_floor.py`
creates new shade-foliage base color, metric height, tangent normal and ORM maps;
none of the published nature texture pixels is copied.

`materials_floor.py` keeps branch-local fibre coordinates continuous into the
broken ends and uses shared object-space bark pigment, dampness and lichen.
`preview_floor_materials.py` retains editable material masters and close source
proofs. These material-direction images are also separate from final export
evidence. `test_floor_source.py` checks source closure, finite grain coordinates,
independent LOD budgets/ground contact and metric height-to-normal consistency.

The retained source in `source/references/review_nature.py` documents reused
camera/audit mechanics only. `tools/review_floor.py` is the separate local copy
being adapted for the smaller woodland-floor assets.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python-exit-code 1 --threads 3 --python authoring/blender/cinderfen-woodland-floor/tools/author_floor.py
python authoring/blender/cinderfen-woodland-floor/tools/paint_floor.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' --background --python-exit-code 1 --threads 3 --python authoring/blender/cinderfen-woodland-floor/tools/build_floor.py -- --preview
```

Check each exit status before running the next step. Source-only geometry
approval does not approve appearance, final export bytes, LOD transitions or GM
readiness. Root owns final internal review, publication and world placement.

The package is paused at the completed source/PBR checkpoint while character,
equipment and town/siege work takes priority. Draft `bake_floor_wood.py` and
`export_floor.py` compile but have not run. There are no runtime GLBs or final
technical/visual receipts. See `WORK_STATE.md` for the exact pending gates.
