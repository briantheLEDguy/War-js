# Riftspire city authoring

The deterministic layout is `scripts/campaign/riftspire-city-source.mjs`. This
collection contains original Riftspire architecture, furnishings and character
derivatives, independent of the Aegis collection. The material generation and
publishing conventions reuse the existing project infrastructure.

Residential dimensions and roof styles are shared with Blender through
`scripts/campaign/riftspire-residence-profiles.json`. Seeded neighborhood occupancy
produces 55 rim, 75 market, 46 transit, 38 lower and 34 works residences. Paired
cottages and varied setbacks fit inside the existing excavations; 104 unoccupied
recesses receive an authored rock infill. Public-room addresses remain fixed.

## Files and review

- `sources/`: editable Blender masters, with separate named architectural parts.
- `runtime/`: 58 static modules and three inhabitants, each with LOD0/1/2.
- `textures/`: editable material images and shared content-addressed 2048px maps.
- `build-report.json` and population reports: model hashes, sizes and budgets.
- `review/`: actual exported-model renders, all-LOD contact sheets, per-asset
  hash-bound inspection records, thirteen complete-city and district views and verification logs.
- `validation.json` / `population-validation.json`: Khronos GLB validation results.
- `city-review.html`: actual `Game` runtime, normal registry/QC loading, isolated
  review character and disabled position persistence. WASD, drag orbit and zoom
  work normally. Location selection covers districts, interiors, stairs and lifts.
- `review.html`: orbit/LOD comparison of the representative residence, bridge/hut
  assembly and palace facade. `prototype.html` preserves the initial in-game
  representative review before the collection was expanded.

The review records document technical inspection by Codex, not user aesthetic
approval. Exports are modeled meshes, not runtime primitive substitutions. The
shared material normal maps are derived from generated stone/timber height fields;
there is no claim of hand-sculpted high-poly transfer baking. Architectural UVs
use a consistent four-metre tile density. Original skinned anatomy and animation
provenance is retained by the population builder; Chaos armor, Dark Elf features
and Greenskin features are authored derivatives. Existing Aegis buildings are not
recolored into Riftspire buildings.

## Rebuild (from repository root)

Use Blender 5.0 and Python with Pillow. Set `BLENDER` below to the local executable.
The generation is local and does not invoke a backend or deploy the game.

```powershell
$riftBlender = 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe'
& $riftBlender -b --python-exit-code 1 --python authoring/blender/riftspire-city/tools/build.py
python authoring/blender/riftspire-city/tools/share_textures.py
python authoring/blender/riftspire-city/tools/repair_tangents.py
& $riftBlender -b --python authoring/blender/riftspire-city/tools/render.py -- --lods=0,1,2
python authoring/blender/riftspire-city/tools/contact_sheets.py
node authoring/blender/riftspire-city/tools/publish.mjs
```

`build.py` and `render.py` accept `--assets=house_1,bridge,hut,palace` after `--`.
Do not regenerate all assets for an isolated edit. Inspect the exported renders
and the game, then update the corresponding review record with observed findings
and exact SHA-256 hashes. `publish.mjs --publish` refuses stale model or preview
hashes, invalid GLBs, non-2K textures and modules exceeding 30,000 triangles.
It installs files, QC sidecars, blueprints and approval records locally.

Population uses `tools/build_population.py -- --assets=chaos,dark_elf,greenskin`.
Process each `population_<kind>-report.json` using the texture-sharing and tangent
tools' `--report=` argument, render `population_<kind>` at all LODs, inspect it,
and use `tools/publish-population.mjs --publish` after updating review hashes.
Runtime population selects LOD1 first and falls back only to another approved LOD.

```powershell
node authoring/blender/riftspire-city/tools/publish.mjs --publish
node authoring/blender/riftspire-city/tools/publish-population.mjs --publish
npm run models:registry
npm run campaign:generate
npm run builder:generate
& $riftBlender -b --python authoring/blender/riftspire-city/tools/render_city.py
npx vite --config authoring/blender/riftspire-city/review-vite.config.mjs --port 5178 --strictPort
```

Open `http://127.0.0.1:5178/authoring/blender/riftspire-city/city-review.html`.
Append `?zone=aegis` for comparison. The stable review server disables HMR; restart
it after runtime source edits and reload after map or model publication.

## Traversal and compatibility

Scenery supplies explicit absolute heights and model-space collision. Only
loaded models contribute support surfaces. Floor selection chooses a reachable
surface beneath the player's current elevation, not the uppermost XZ surface.
Stair connections meet the inner terrace edges through open railing bays. Wall
lifts serve all five terraces; the central lift serves -105, -130 and -150 m.
Call controls appear near a landing or aboard a cage. Main siege approaches are
18 m wide. Rope paths are optional, narrower settlement connections.

The eight public rooms and three palace rooms are physical walk-in spaces.
NPC service IDs, quest IDs and the three campaign links are preserved. The fourth
gate is local. Obsolete flat positions and incompatible GM layout revisions are
ignored/recovered without deleting progression or unrelated saved data. Missing
approved scenery never introduces visible fallback shapes; invalid essential
support sends the player to a fixed recovery or the existing fortress zone.

## Verification

Run `npx vitest run --maxWorkers=2` to avoid CPU contention between geometry-heavy
layout suites, then the production build, world/model and Builder validators.
Focused tests cover stacked floors, undersides, lift carrying/calls/disembarkation,
recovery, old saves, complete route support, stair collision, population patrols,
public entries, formations, objective ordering, approved LOD fallback and hashes.

Performance comparison uses the same browser, 1280x720 native drawing buffer,
60 FPS cap and 1000 m view-distance setting, with no Blender render running.
Use the page's ten-second benchmark on corresponding street and overview views.
The page reports browser frame interval percentiles and the game's smoothed frame
interval; these are not isolated GPU timings. Results and remaining verification
limitations are recorded in `review/delivery-review.md`.

## LAN screenshot gallery

`node authoring/blender/riftspire-city/tools/serve_gallery.mjs --host=192.168.68.55 --port=8088`
serves the selected city and district review images on this workstation's current LAN address.
Change the host argument for another computer. It serves only whitelisted images,
with caching disabled so refreshed renders appear on reload.

## District dressing

`tools/district_details.py` builds 18 original street assemblies. Their footprints
come from `scripts/campaign/riftspire-district-props.json`, also used by
`scripts/campaign/riftspire-district-dressing.mjs` for deterministic placement.
Run `build.py -- --district-details` to rebuild only this collection, then follow
the shared texture, tangent repair, exported-LOD review and publication steps.

| District | Content |
|---|---|
| Ashgate Rim | Muster desks, pikes and trophy shields, standards, braziers, empty iron cages |
| Blackvein Market | Cloth traders, apothecary shelves, provision stalls, barrels and stores |
| Hollowwall Warrens | Patched washing lines, wash tubs, communal kettles and household storage |
| Chainwake Commons | Winches, loaded carts, cooking circles and deck-side stores |
| Drowned Works | Riveted pumps, cisterns, ore carts and haulage equipment |
| Riftspire Crown | Horned oath monuments, ritual needles, war tables and armed guard patrols |

The layout contains 692 additional assemblies and 142 ambient inhabitants.
Placement tests preserve an eight-metre central terrace lane, full permanent
bridge approaches, stair mouths, every residential threshold, services, lifts and
capture formations. Objects require support at all footprint corners and cannot
overlap protected routes or other modeled furnishings. The runtime keeps only the
nearest 48 district actors visible within 100 m; all other zones retain their
original population cap. New small props share instancing and 220 m detail culling.
Layout v3 ignores incompatible older GM placements; character progression is kept.

The runtime review includes seven named district stops. `render_city.py` adds six
`city-district-*.png` views, and the LAN gallery serves these alongside city views.
