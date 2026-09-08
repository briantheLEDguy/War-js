# Expanded ORvR world art briefs

This is the production contract for eighteen 1,200 × 1,200 metre outdoor fronts and their twelve optional boss branches. `scripts/campaign/orvr-art-direction.mjs` owns explicit climate and population selections. `scripts/campaign/orvr-zone-layouts.mjs` owns terrain controls, travel connections, supply roads, keep positions, staging camps, and production asset references.

These definitions are layout and art-direction work. They do **not** establish that the replacement environment, population, or terrain assets have been built or visually approved. Generated outdoor maps remain `layout-ready-art-pending`; planned keys cannot be promoted to approved assets by the generator. Existing assets retain their identifiers while replacements are made. The Sunmeadow terrain, architecture and initial nature release is integrated; further population and ecology work is tracked on the [production board](orvr-production-board.md).

## Modeling and completion standard

Use the current Battle Prelate rebuild as the craftsmanship reference: deliberate silhouette, shaped surfaces, convincing material thickness, purposeful construction, fitted components, UVs, PBR textures, and inspected deformation. Every new visible mesh must be authored; no primitive assemblies or subdivision of placeholder shapes. An invisible collision surface or landform-control region is not a visible model.

Keep editable Blender masters, detailed source meshes, three inspected runtime LODs, texture provenance, export hashes, and review views. Check every GLB under neutral and actual game lighting at close range and gameplay distance. Terrain must meet across chunk borders without cracks; foliage needs varied silhouettes and readable species; animals and people need climate-appropriate anatomy, clothing, equipment, and animation. All assets remain draft until those checks actually pass.

The frontier siege set uses `frontier_supply_wagon`, `frontier_battering_ram`, `frontier_oil_cauldron`, `frontier_field_catapult`, and `frontier_keep_gate`. Its staging directory is `authoring/blender/orvr-frontier`; that directory is not a runtime approval signal. Complete caravans additionally require authored draft animals and appropriate animation; a wagon shell alone is not a complete caravan.

## Playable space and composition

- Opposing keeps occupy `(-350, 0)` and `(350, 0)`. Each has two successive gates, a commander, supply officer/delivery approach, one oil slot, two catapult slots, and a ram assembly point. Keep source coordinates must match the authored collision and navigation records; collision enclosures describe reserved footprints, not solid filled boxes.
- The three existing battlefield-objective IDs occupy `(0, -260)`, `(0, 0)`, and `(0, 260)`. The west/central/east suffixes are persistent compatibility IDs; they no longer dictate compass position. Shared campaign initialization makes all three neutral.
- Six explicit supply itineraries link every objective to either realm's keep over shared, winding roads. Current lengths range from approximately 364 to 647 metres. Main supply roads are twelve metres wide; narrower approaches fit keep passages and support routes. Keep doors require a six-metre clear opening for the ram's approximately 3.5-metre width including hubs and turning margin. Routes have no instantaneous teleports.
- Uncapturable staging camps at `(-505, 80)` and `(505, 80)` provide fifteen-second respawns independently of keep ownership. Native settlements sit south of the home keep, away from hostile wildlife and combat objective radii.
- Travel triggers move to a 540-metre radius. Return spawns sit outside the matching trigger volume and its immediate re-entry margin. Every original campaign and optional boss connection is retained; campaign activation controls combat, separately from ordinary travel.
- Terrain consists of sixteen 300-metre production chunks. Authored ridge, terrace, basin, plateau, and corridor controls reserve traversable ground before detailed sculpting. The control source is not a completed terrain model or a guarantee of visual quality. Approved terrain/collision assets must replace the transitional terrain before declaring a zone finished.
- Preserve all quest, enemy, service-NPC, objective, harvest, crafting, and interaction IDs. Runtime biome generation is disabled for these draft layouts until approved regional asset selections exist; generic evergreen scatter must not stand in for every climate.

## Battlefield and fortress regions

| Zone | Climate and landmark | Vegetation | Local population and wildlife |
|---|---|---|---|
| Sunmeadow March | Late-summer farmland; limestone hamlet and stream crossing | Oak, ash, hawthorn, wheat, meadow grass | Empire farmers and traders, Dwarf craftspeople, High Elf scouts; deer, Barrow Wolves, field birds |
| Greybrook Crossing | Autumn floodplain; bridge market and flood terraces | Willow, alder, reeds, sedge | Empire river traders, Dwarf bridgewrights; otters, marsh wolves, water birds |
| Ironwood Redoubt | Cool old-growth forest; timber redoubt and charcoal clearing | Oak, hornbeam, ferns, moss, fallen wood | Empire foresters, Dwarf charcoal crews, High Elf sentries; deer, grey wolves, woodland birds |
| Brightfen Approach | Summer freshwater fen; raised reed village | Alder, willow, reeds, iris, sedge | High Elf reed workers, Empire marsh farmers; water deer, mire hounds, wading birds |
| Glassriver Ford | Clear river valley; ferry steps and water-cut gorge | Birch, willow, lilies, river grass | High Elf ferrymen and herbalists, Dwarf masons; river deer, river stalkers, kingfishers |
| Highvale Rampart | Winter alpine foothills; mining terraces below snowfields | Mountain pine, juniper, heather, snow grass, lichen | Dwarf upland crews, High Elf scouts in cold-weather clothing; ibex, snow wolves, alpine birds |
| Cinderfen Outskirts | Autumn geothermal marsh; peat causeway and mineral vents | Dead alder, reeds, rust sedge, fungi, moss | Greenskin fen workers, Dark Elf supply officers; marsh boar, cinder wolves, marsh birds |
| Bleakroot Causeway | Drowned autumn forest; root-tangled dyke | Dead oak, alder, reeds, fungi, roots | Greenskin loggers, Dark Elf watchposts; swamp boar, root hounds, carrion birds |
| Vilemere Heights | Wet autumn moorland; slate redoubts and peat gullies | Heather, gorse, sedge, stunted birch | Dark Elf ridge outposts, Greenskin peat cutters; moor deer, moor wolves, moor birds |
| Ashen Steppe | Summer semiarid steppe; dry-wash caravan settlement | Dry grasses, thorn scrub, acacia, sage | Chaos war settlements, Greenskin wagon crews; steppe antelope, ash hounds, steppe birds |
| Gorepine Pass | Winter conifer pass; drifted road and timber lodge | Pine, spruce, juniper, snow grass, lichen | Chaos mountain garrisons, Dark Elf scouts; mountain goats, pine wolves, ravens |
| Obsidian Scar | Volcanic badlands; quarry and cooled lava shelves | Ash scrub, dry grass, lichens, charred trunks, basalt scree | Chaos forge crews, Greenskin haulers; scar lizards, glass hounds, cliff birds |
| Aegis Crownworks | Autumn fortified uplands; pale-stone terraces | Oak, juniper, heather, upland grass | Mixed Aegis armies, Dwarf engineers, Empire suppliers; highland deer, upland wolves, hawks |
| Dawnline Expanse | Summer temperate frontier; fortified road junction | Oak, hawthorn, meadow grass, flowers, fallen wood | Mixed Aegis armies and displaced farm communities; deer, frontier wolves, field birds |
| Shatterline Expanse | Dry autumn front; broken escarpment and occupied road | Thorn scrub, dry grass, deadwood, heather | Mixed Riftbound armies and supply crews; antelope, scar hounds, ravens |
| Rift Crownworks | Autumn volcanic highlands; hot mineral valleys | Pine, ash scrub, lichen, charred wood, scree | Chaos smiths, Greenskin engineers, Dark Elf watch; mountain goats, cinder hounds, cliff birds |
| Starfall Gate | Winter alpine fortress; defensible mountain saddle | Mountain pine, juniper, snow grass, lichen | Mixed Aegis fortress troops and civilian supply train; ibex, snow wolves, alpine birds |
| Voidgate Fortress | Autumn volcanic fortress; gate between cooled lava cliffs | Ash scrub, charred trunks, lichen, dry grass | Mixed Riftbound fortress troops and forge laborers; scar lizards, glass hounds, ravens |

Each border approach must explain its climate change through elevation, drainage, vegetation density, soil, and distant landforms. Assets may share compatible construction modules, but landmarks, silhouettes, settlement patterns, and wildlife habitats must remain distinct. Do not recolor a single scene and call it a different region.

## Optional boss branches

| Lair | Parent climate | Distinct landform and population |
|---|---|---|
| Warden's Hollow | Sunmeadow | Root-covered limestone barrow beneath an old oak; barrow sentinel and woodland pack |
| Briarwatch Den | Greybrook | Flood-cut bank and thorn canopy above an old ferry pier; river ambushers and den guardian |
| Stormbarrow Lair | Ironwood | Lightning-split trees around a burial terrace; forest sentinels and storm-scarred overlord |
| Mireglass Den | Brightfen | Reflective fen pool and reed-island nesting grounds; fen stalkers and mire guardian |
| Glassriver Depths | Glassriver | Water-cut limestone vault below the river shelf; river predators and drowned-vault guardian |
| Highvale Sanctum | Highvale | Ritual terraces beneath an ice cornice; cold-weather sentinels and mountain guardian |
| Cindermaw Pit | Cinderfen | Mineral-crusted sinkhole and steaming reed margins; vent predators and cindermaw guardian |
| Rotwreath Nest | Bleakroot | Root vault above drowned forest floor; root ambushers and nest overlord |
| Nightglass Hollow | Vilemere | Water-polished slate cleft and wind-torn heather; moor hunters and hollow guardian |
| Ashfang Pit | Ashen Steppe | Dry wash opening into layered sandstone; scavengers and ashfang pack leader |
| Gorepine Warrens | Gorepine | Pine-root burrows among frost-shattered rock; mountain packs and cold-den guardian |
| Obsidian Maw | Obsidian Scar | Cooled lava throat with fractured glass ribs; scar predators and glass-maw guardian |

Lairs retain their original scale and travel identity. They do not become 1,200-metre battlefield copies, receive extra campaign keeps, or block front progression.

## Review and acceptance

Begin with complete Sunmeadow and Cinderfen zones so one advance and one counterpush can be reviewed. Verify neutral captures, supply escorts and ambushes, deliveries, keep upgrades, physical ram travel, sequential gate breaches, commander combat, objective possession, and staging access. Walk all service, crafting, harvest, portal, and boss approaches. Inspect collision, character grounding, camera clearance, vegetation corridors, and chunk seams.

The automated layout tests verify coverage, exact objective/keep counts, persistent identities, route endpoints/lengths/clearances, travel round-trips, determinism, explicit climates, and draft asset status. They cannot verify Battle Prelate-level craftsmanship, completed ecosystem coverage, animation quality, or 1080p/60 FPS. Those remain explicit visual and performance acceptance gates for every completed zone.
