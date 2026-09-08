# Riftspire delivery review

Implemented locally on `codex/riftspire-crater-capital`; no public deployment or
backend activation. The normal game uses `riftspire_capital`. The local tour is
`http://127.0.0.1:5178/authoring/blender/riftspire-city/city-review.html`.

## Delivered content

- 1,024 m zone, approximately 800 m crater opening and 300 m basin depth.
- Five wall terraces and two suspended commons levels; six named districts.
- 248 inward-facing residences/workshops, eight varied architectural profiles and 24 hanging huts.
- Four 18 m transit arms, three central decks, four wall lifts, a settlement lift,
  redundant stairs, four rim gates and the existing three campaign connections.
- Eight furnished public rooms and connected palace admission, vault and throne halls.
- Seven preserved named service NPCs, 142 reviewed ambient inhabitants and three
  training effigies; Chaos, Greenskin and Dark Elf population models.
- 58 static module masters and three population masters; 183 runtime GLBs across
  three reviewed LODs, 47 shared 2048px texture images and 2,392 scenery placements.
- Height-aware floors, camera ground queries, map routes, interactions and siege
  checks; fixed-floor fall recovery and obsolete-save/layout recovery.
- Ordered Bridgehead, Vault and Throne siege, clear two-team formations and
  regenerated campaign, registry, Builder catalog and seed artifacts.

## Verification results

| Check | Result |
|---|---|
| Full regression suite, `npx vitest run --maxWorkers=2` | 97 files, 839 tests passed |
| Production build | Passed, 209 modules; existing large-bundle warning remains |
| World validation | 33 maps passed |
| Model/manifest validation | 660 records passed |
| Builder validation | 231 catalog definitions passed |
| Static GLB validation | 174 files, zero errors; maximum 29,000 triangles per module |
| Population GLB validation | Nine files, zero errors; every LOD below 30,000 triangles |
| Texture, model and review hashes | Verified; shared textures all 2048px |
| Aegis map preservation | Layout and geometry unchanged; only six generated punctuation corrections differ from HEAD |
| Normal Riftspire runtime | Zero asset fallbacks observed |

Automated checks sample every authored terrace/bridge/stair route for floor
support, every stair route for collider clearance, all public entrances and service
positions, population patrol loops, siege formations, objective prerequisites,
stacked-floor capture range, rotated floor indexing, moving lift collision,
disembarkation and missing/invalid approved LOD recovery. Builder tests retain the
spare room's model-space doorway and floor. Map tests mute remote stair segments.

In the actual Game runtime, the wall lift was boarded at -105 m, ridden to -245 m,
disembarked and sent away without moving the player. The central lift carried the
player to -150 m and allowed disembarkation. Stair descent and ascent were checked
at the terrace seam. The recessed Ashen Cup doorway and palace throne entrance
were walked through at -105 m. The fall check returned to the previous supported
position. Representative residence, bridge/hut and palace pieces were reviewed in
the game before expanding the collection; every exported LOD has an inspection
record and preview hash. This is technical review, not user aesthetic approval.

## Residential variety revision (2026-09-07)

The five residential bands contain 55, 75, 46, 38 and 34 homes. Seeded occupancy
creates clusters, paired cottages and 104 solid rock stretches. Footprints and
heights vary within excavation bounds; district-specific model pools emphasize
workshops, tenements or cottages. Dimensions are shared between the Blender
builder and layout collision through `riftspire-residence-profiles.json`.
All residential thresholds are now included in support and clearance tests.
The runtime review includes Paired cottages, Workshop cluster and Tall tenement
locations; all three were inspected with zero asset fallbacks. Updated exported
LODs were visually inspected and hash-reviewed before local publication.
Layout version v2 invalidates incompatible GM layouts; unsupported saved house
positions use the existing safe-arrival recovery.

The full suite passed 97 files / 834 tests. The production build passed after
rerunning outside the Windows sandbox, which initially blocked esbuild config
access. The existing bundle-size warning remains.

## District dressing revision (2026-09-07)

Eighteen new editable assemblies supply 692 district placements: military stores,
inspection stations and braziers at Ashgate; stocked stalls in Blackvein; washing
lines and cooking areas in Hollowwall; haulage and communal hearths in Chainwake;
pumps, ore carts and winches in Drowned Works; and oath monuments, ritual needles,
standards and council furnishings in the Crown. All three LODs were rendered,
inspected and hash-reviewed before local publication. Layout version v3 recovers
incompatible old GM placements through the existing safe-arrival mechanism.

Placement tests check the full footprints against authored floors and preserve an
8.2 m terrace lane, permanent bridge widths, door access, stairs, service positions,
lifts and siege formations. Added inhabitants use approved Chaos, Greenskin and
Dark Elf profiles on sampled clear routes. Crater zones register up to 160 actors,
with only the nearest 48 within 100 m visible and animated. Other zones retain the
48-actor registration limit. Small street assemblies use 220 m detail culling.

Seven district tour stops expose the new content. Blackvein Night Bazaar, Drowned
Pumpworks, Crown Oathguard and Chainwake Cookfire were inspected in the Game
runtime with zero asset fallbacks. Six new district close views join the seven
existing exported-model city renders. The screenshot gallery is available locally
at `http://192.168.68.55:8088/` while its server is running.

A ten-second district-pass sample at Chainwake Cookfire, 741 x 1270, measured
33.50 ms median smoothed game frames (about 30 FPS), with 277 draws, 722,123
triangles and zero fallbacks. No Blender, build or test job ran during the sample.
This view still has performance headroom to improve; it does not establish the
requested matched-Aegis target. Raw values are in `district-performance.json`.

## Matched performance (initial layout baseline)

These measurements predate the residential variety and district dressing revisions;
no new matched Aegis/Riftspire benchmark was performed for these art passes.

Same local browser and host, 1280x720 native resolution, 60 FPS cap, 1,000 m view
distance, ten seconds per view, no Blender/test job running during samples.

| View | Aegis median game frame | Riftspire median game frame | Riftspire / Aegis |
|---|---:|---:|---:|
| Street / transit bridge | 16.603 ms | 16.569 ms | 0.998 |
| Capital overview | 16.572 ms | 16.584 ms | 1.001 |

The measured game-frame target is met at the tested cap. These are medians of the
game's smoothed scheduled frame intervals, not isolated GPU render timings or an
uncapped headroom comparison. Raw browser callback intervals, draw counts and
triangle counts are retained in `performance.json`; browser callbacks also include
idle display frames between capped game updates. Aegis reported one existing
fallback in this comparison; Riftspire reported zero.

Spatial floor indexing removed the distant camera's full-city floor scans. Static
instances are grouped by city quadrant, distant furnishings are culled, local
lights reuse two slots, and moving cages are excluded from static batches.

## Visual evidence and limits

`city-rim.png`, `city-terrace.png`, `city-bridge.png`, `city-commons.png`,
`city-works.png`, `city-neighborhood.png`, `city-palace.png` and the six
`city-district-*.png` close views render the actual exported models at map
transforms. Contact sheets cover all three LODs. The scene is modular game art;
the reference's photographic finish and a hand-sculpted high-poly bake pipeline
are not claimed. Normal detail is generated from material height fields.

The regression suites and manual checks cover representative live traversal plus
all authored route samples. They do not substitute for an exhaustive multiplayer
siege playtest or a benchmark across other GPUs. No new fall-damage system was
introduced.
