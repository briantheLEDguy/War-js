# Bastion of Aegis architecture

Original modular Gothic architecture kit: 56 assets, 168 GLBs across three LODs. Editable
Blender masters are in `sources/`; `aegis_city_review.blend` and
`review/all-exports.blend` inspect the exported models. Source masters and large
review images use Git LFS.

## Rich civic collection

An additional ten original civic models (30 GLBs, about 6.3 MB total) add cast
iron scrollwork, fluted brass posts, six-sided emissive lantern cages, enamel
trade signs with raised lettering, a canal bridge relief, benches, directory
posts and the Common Sky astronomical sculpture. Geometry and PBR material
factors are authored locally; there are no external images or heraldic references.
Lights use emissive glass and existing scene illumination, with no additional
per-lamp shadow lights. Static copies use the city's existing instancing and LODs.

The collection is built separately, preserving the architecture sources:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python authoring/blender/aegis-city/tools/build_civic.py
node authoring/blender/aegis-city/tools/publish_civic.mjs
```

Inspect `review/civic-exports.png` (actual LOD0 exports) and the individual
`sources/civic_*.blend` masters. Record the reviewed build and image SHA-256s,
reviewer, timestamp and observations in `review/civic-review.json`. Promotion
checks those hashes and technical validation before writing manifests/QC files:

```powershell
node authoring/blender/aegis-city/tools/publish_civic.mjs --publish
npm run models:registry
npm run campaign:generate
npm run world:validate
npm run models:validate
npm test -- tests/aegisCivicDecorations.test.ts tests/aegisCity.test.ts tests/worldLifeContent.test.ts
```

`scripts/campaign/aegis-civic-decorations.mjs` runs after elevation baking. It
keeps full road widths, water edges, existing world-life props and service
approaches clear. Freestanding pieces use level plots; mounted pieces compensate
for the difference between local terrain and the building's foundation height.
The four trade signs retain the existing shop/tavern portal IDs and labels.
`CityCivicFallback.ts` preserves decoration-scale silhouettes if a GLB is missing.
The shipped pass contains 69 street lamps, 104 facade lanterns, four named signs,
17 reliefs, five sculptures, ten benches and five directory posts.

The high-resolution workflow retains detailed beveled source geometry, explicit
UVs, painted PBR color/roughness maps, and a retained brick relief master used to
bake tangent-space normals. Brick, paving and flagstone maps are 2048 pixels; other tiled materials are
1024 pixels. Runtime exports share external textures instead of embedding the
same images in every building. Lower LODs reduce geometry to approximately 50%
and 20%. These are modular architecture assets, with intentionally repeated
facades and materials.

Rebuild from the repository root with Blender 5 and Python 3:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python authoring/blender/aegis-city/tools/build_city.py
python authoring/blender/aegis-city/tools/share_textures.py
python authoring/blender/aegis-city/tools/repair_tangents.py
node authoring/blender/aegis-city/tools/validate_city.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python authoring/blender/aegis-city/tools/review_all.py
```

Inspect `review/all-exports.png` and `review/exported-kit.png` before promotion.
The validator uses the repository's `gltf-validator` dependency; an isolated
installation under `.deps/` is also supported. The tangent repair only repairs
degenerate UV corners and records repairs in the build report.

```powershell
python authoring/blender/aegis-city/tools/publish_city.py
npm run models:registry
npm run models:validate
npm run campaign:generate
npm run world:validate
```

Promotion requires validation and model hashes to match. It creates blueprint,
QC and approved-asset records under the existing manifest-first pipeline. Keep
the shared `public/assets/textures/aegis_city/` directory beside the models when
deploying: GLBs resolve these relative texture references.

`scripts/campaign/aegis-city-source.mjs` owns the deterministic layout. It builds
five districts, a complete fortress perimeter with three road gates and barred
water gates, six bridges, 98 ordinary houses, six public entrances, a citadel,
eight exploration courts and two wall stairways. Six entrances share four
furnished interior variants; ordinary houses remain exterior scenery.

Runtime responsibilities:

- `CityWater.ts` partitions ground and water at canal boundaries.
- `CityArchitecture.ts` supplies LODs, shared materials and missing-asset fallbacks.
- `CityInstances.ts` batches static architecture and restores editable originals
  during GM mode. Collision and interaction IDs remain independent of rendering.
- `CityNavigation.ts` recovers saved positions obstructed by the new layout.
- `HouseInteriorRuntime.ts` loads public interiors only for Aegis.
- `cityMap.ts` draws the authored street, canal and wall geometry on the minimap.

Run `npm run dev`, then open
`http://127.0.0.1:5173/authoring/blender/aegis-city/review.html` for the isolated
runtime review. Select district, bridge, interior, discovery or gate viewpoints;
use WASD to walk and E to enter/leave. The review character does not save position
or equipment. This development page is excluded from the production entry point.

Verification: `npm run build`, `npm run world:validate`, `npm run models:validate`,
the GLB validator above, and `npm test`. Focused city coverage lives in
`tests/aegisCity.test.ts`, `tests/cityInstances.test.ts` and
`tests/houseInteriorRuntime.test.ts`.

## Density and material variety

The second pass adds 36 narrow buildings, 135 street furnishings and eight court
features, distributed across all five districts while reserving service and
portal approaches. Thirteen new assets include rowhouses, a lean-to workshop,
awnings, carts, crates, barrels, planters, trees, washing lines, noticeboards and
a fountain. `tools/city_details.py` builds these with the same three-LOD pipeline.

`tools/city_materials.py` creates irregular masonry, plaster, wood and roof PBR
fields. Brick, paving and flagstone use 2048 maps; other surfaces use 1024 maps.
Ochre/lime/sage plaster, limestone, terracotta and copper distinguish facades and
roofs. `src/world/CityWeathering.ts` adds broad world-space stains, including on
instanced copies, so adjacent objects do not repeat the same weathering patch.

## Mountainside layout

`aegis-mountainside.mjs` bakes a 560-segment height field into the campaign map.
Lower canals stay at their original level. Northern roads climb to the 42-metre
citadel terrace; a separate reviewed mountain massif supplies the natural skyline. Building pads and road
beds are graded independently, and the existing reviewed masonry kit supplies
deep wall foundations. `CityElevation.ts` samples the same triangle heights for
terrain, movement and terrain-relative objects. `flatTerrain` retains the city
surface treatment; authored elevation takes precedence over its zero-height
fallback. The local review page includes ascent and switchback viewpoints.

City brick paths use `CityRoad.ts` to clip their surfaces against the exact
height-field triangles. This avoids paving cutting through slopes when a rotated
street and the terrain would otherwise use different triangulations.

## Grand citadel and battle capacity

`citadel_assets.py` builds the enlarged keep, bastions, arcades, three-approach
gate module, stone cover and a broad eroded granite mountain with unequal peaks.
The keep reaches approximately 125 metres above the 42-metre terrace.
Its 72 by 62 metre hall extends toward the court while the rear doorway stays fixed.
`aegis-battle-citadel.mjs` authors a 128 by 34 metre combat forecourt, an 18-metre
central approach and two 12-metre flanks, with two separated 18-person staging
formations. The outer fortress extends north to Z=250 around the new precinct.

Tests check one-metre-radius clearance, all 36 starting positions, connected
approaches and the extended fortress boundary. The runtime review has a battle
overview and optional 36 avatar-sized markers. These markers demonstrate spacing;
networked combat, ability effects and real player load still require a live
36-player test. The keep is a hollow, walk-in hall with side chambers, stairs and
galleries; the battle court and arcades are walkable outdoor space. Flat upper
and lower terrain strips use fewer triangles.

### Gothic exterior rebuild

`tools/citadel_gothic.py` builds the central lantern and needle, staggered tower
spires, roof pinnacles, pointed window frames and high flying braces.
`citadel_assets.py` owns the hollow hall, extended galleries and fixed rear doorway.
UV layer names match the shared masonry primitives so joining preserves their
stone and slate textures. Detailed bevels remain in the editable master;
runtime bevels use one segment and the keep is capped below 30,000 triangles.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python-exit-code 1 --python authoring/blender/aegis-city/tools/build_city.py -- --assets=citadel --reuse-materials
python authoring/blender/aegis-city/tools/share_textures.py --assets=citadel
python authoring/blender/aegis-city/tools/repair_tangents.py --assets=citadel
node authoring/blender/aegis-city/tools/publish_citadel.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python-exit-code 1 --python authoring/blender/aegis-city/tools/review_citadel_exterior.py
```

Inspect `review/citadel-gothic.png`, `citadel-gothic-facade.png` and
`citadel-gothic-lod2.png`. Record their SHA-256s, the three model hashes, reviewer,
timestamp and observations in `review/citadel-gothic-review.json`. Then run
`node authoring/blender/aegis-city/tools/publish_citadel.mjs --publish` and
`npm run models:registry`. This publisher checks the actual exported triangle
counts, shared textures and review hashes, and updates only the keep's approval/QC.
`--reuse-materials` reads the retained citadel master rather than repainting other assets.

After footprint changes run `npm run campaign:generate`, `npm run builder:generate`,
`npm run world:validate`, `npm run models:validate` and `npm run build`.
Run `npm test -- tests/aegisCity.test.ts tests/citadelSiege.test.ts tests/citadelMountain.test.ts tests/citadelInteriorLayout.test.ts tests/citadelBuilderTransforms.test.ts`.
These check the shipped doorway, extended floor and side walls at every LOD,
collision, upper gallery access, all 36 staging slots and objective clearance.

## Mountain siege interiors

`citadel_assets.py` also authors the open mountain passage, divided redoubt,
treasury vault, and sealed future crypt threshold. The redoubt's front chamber
serves as a guarded forehall. Three broad portals at local Blender Y=-4 open
into the 52-metre-deep throne hall. The east side has a treasury entry and a
separate return route into the throne hall; the west side retains its crypt
approach.

The vault is a 48 by 84 metre walk-in shell with two side portals, a ribbed stone
ceiling, iron tension straps, perimeter relief panels and four load-bearing
piers. Its floor is at local height zero; the roof underside is at 20 metres.
Only the four 3 by 3 metre pier feet occupy interior floor space. The connected
shells share the existing tiled PBR materials and static architecture LODs.
Their Blender X coordinates reflect when placed with map `rotY: Math.PI`;
collider definitions follow the resulting world-space walls and openings.

Rebuild changed shells with the same reviewed high-resolution pipeline:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python authoring/blender/aegis-city/tools/build_city.py -- --assets=mountain_redoubt,mountain_vault,mountain_massif
python authoring/blender/aegis-city/tools/share_textures.py
python authoring/blender/aegis-city/tools/repair_tangents.py
node authoring/blender/aegis-city/tools/validate_city.mjs
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python authoring/blender/aegis-city/tools/review_mountain_interiors.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python authoring/blender/aegis-city/tools/review_monuments.py
& 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe' -b --python authoring/blender/aegis-city/tools/review_all.py
```

Inspect the exported-model images before running `tools/publish_city.py`.
`review/review.json` records the mountain interior image hashes, including both
vault views. The publisher promotes only technically validated, hash-matching
exports and records the shared review hash in each QC sidecar and approved asset.
