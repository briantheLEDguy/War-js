// Asset keys in this catalog are production requirements, not approvals.
// Never promote a planned key to the runtime registry merely because it is listed here.
const regions = {
  sunmeadow_march: ['temperate_farmland', 'summer', 'Empire farmsteads; Dwarf workshops; High Elf scouts', ['oak', 'ash', 'hawthorn', 'wheat', 'meadow_grass'], ['deer', 'barrow_wolf', 'field_bird'], ['#88935b', '#bea471', '#65695c'], 'Limestone hamlet and stream crossing', 12],
  greybrook_crossing: ['temperate_floodplain', 'autumn', 'Empire river traders; Dwarf bridgewrights', ['willow', 'alder', 'reed', 'sedge', 'river_grass'], ['otter', 'marsh_wolf', 'water_bird'], ['#71847a', '#ad9b76', '#687b82'], 'Weathered bridge market and flood terraces', 9],
  ironwood_redoubt: ['cool_old_growth', 'autumn', 'Empire foresters; Dwarf charcoal crews; High Elf sentries', ['oak', 'hornbeam', 'fern', 'moss', 'fallen_log'], ['forest_deer', 'grey_wolf', 'woodland_bird'], ['#455f49', '#857455', '#777771'], 'Root-lined timber redoubt and charcoal clearing', 22],
  brightfen_approach: ['freshwater_fen', 'summer', 'High Elf reed workers; Empire marsh farmers', ['alder', 'willow', 'reed', 'iris', 'sedge'], ['water_deer', 'mire_hound', 'wading_bird'], ['#7b9562', '#a0b39d', '#c3ac7a'], 'Raised reed village and limestone causeway', 7],
  glassriver_ford: ['clear_river_valley', 'summer', 'High Elf ferrymen and herbalists; Dwarf masons', ['birch', 'willow', 'river_grass', 'lily', 'wildflower'], ['river_deer', 'river_stalker', 'kingfisher'], ['#699595', '#93a676', '#bcbab0'], 'Pale stone ferry steps and clear-water gorge', 20],
  highvale_rampart: ['alpine_foothills', 'winter', 'Dwarf upland crews; High Elf cold-weather scouts', ['mountain_pine', 'juniper', 'heather', 'snow_grass', 'lichen'], ['ibex', 'snow_wolf', 'alpine_bird'], ['#83928c', '#c7d0cf', '#747b81'], 'Sheltered mining terraces below snowfields', 36],
  cinderfen_outskirts: ['geothermal_marsh', 'autumn', 'Greenskin fen settlements; Dark Elf supply officers', ['dead_alder', 'reed', 'rust_sedge', 'fungus', 'moss'], ['marsh_boar', 'cinder_wolf', 'marsh_bird'], ['#696c47', '#9a7752', '#515859'], 'Peat causeway settlement and mineral vents', 11],
  bleakroot_causeway: ['drowned_forest', 'autumn', 'Greenskin loggers; Dark Elf watchposts', ['dead_oak', 'alder', 'reed', 'fungus', 'root_mass'], ['swamp_boar', 'root_hound', 'carrion_bird'], ['#4a5b50', '#776c58', '#6c7979'], 'Root-tangled dyke and sunken woodland shrine', 9],
  vilemere_heights: ['wet_moorland', 'autumn', 'Dark Elf ridge outposts; Greenskin peat cutters', ['heather', 'gorse', 'sedge', 'stunted_birch', 'peat_grass'], ['moor_deer', 'moor_wolf', 'moor_bird'], ['#687174', '#8d8174', '#555957'], 'Wind-worn slate redoubts and peat gullies', 28],
  ashen_steppe: ['semiarid_steppe', 'summer', 'Chaos war settlements; Greenskin wagon crews', ['dry_grass', 'thorn_scrub', 'acacia', 'sage', 'deadwood'], ['steppe_antelope', 'ash_hound', 'steppe_bird'], ['#ae936b', '#897052', '#716b61'], 'Dry wash caravan settlement and ochre ridges', 17],
  gorepine_pass: ['cold_conifer_pass', 'winter', 'Chaos mountain garrisons; Dark Elf scouts', ['pine', 'spruce', 'juniper', 'snow_grass', 'lichen'], ['mountain_goat', 'pine_wolf', 'raven'], ['#496157', '#9aa4a1', '#666d73'], 'Snow-drift pass and heavy timber supply lodge', 33],
  obsidian_scar: ['volcanic_badlands', 'summer', 'Chaos forge crews; Greenskin haulers', ['ash_scrub', 'dry_grass', 'lichen', 'charred_trunk', 'basalt_scree'], ['scar_lizard', 'glass_hound', 'cliff_bird'], ['#585358', '#8f5845', '#a89c8f'], 'Basalt quarry, cooled lava shelves, and forge road', 27],
  aegis_crownworks: ['fortified_highlands', 'autumn', 'Mixed Aegis armies; Dwarf engineers; Empire suppliers', ['oak', 'juniper', 'heather', 'upland_grass', 'lichen'], ['highland_deer', 'upland_wolf', 'hawk'], ['#7a876e', '#a79d85', '#828587'], 'Terraced pale-stone works and army workshops', 26],
  dawnline_expanse: ['temperate_frontier', 'summer', 'Mixed Aegis armies and displaced farm communities', ['oak', 'hawthorn', 'meadow_grass', 'wildflower', 'fallen_log'], ['deer', 'frontier_wolf', 'field_bird'], ['#8b9269', '#ab9872', '#777c75'], 'Broken field boundaries and fortified road junction', 17],
  shatterline_expanse: ['dry_war_frontier', 'autumn', 'Mixed Riftbound armies and mobile supply crews', ['thorn_scrub', 'dry_grass', 'deadwood', 'heather', 'lichen'], ['steppe_antelope', 'scar_hound', 'raven'], ['#9b896e', '#777365', '#81776f'], 'Shattered escarpment and occupied trade road', 22],
  rift_crownworks: ['volcanic_highlands', 'autumn', 'Chaos war smiths; Greenskin engineers; Dark Elf watch', ['pine', 'ash_scrub', 'lichen', 'charred_trunk', 'scree'], ['mountain_goat', 'cinder_hound', 'cliff_bird'], ['#6a686a', '#98634f', '#8b8373'], 'Basalt ramparts above hot mineral valleys', 31],
  aegis_gate_fortress: ['alpine_fortress', 'winter', 'Mixed Aegis fortress troops and civilian supply train', ['mountain_pine', 'juniper', 'snow_grass', 'lichen', 'scree'], ['ibex', 'snow_wolf', 'alpine_bird'], ['#8b9896', '#c8ceca', '#7e817b'], 'High stone gate over a defensible mountain saddle', 38],
  rift_gate_fortress: ['volcanic_fortress', 'autumn', 'Mixed Riftbound fortress troops and forge laborers', ['ash_scrub', 'charred_trunk', 'lichen', 'dry_grass', 'basalt_scree'], ['scar_lizard', 'glass_hound', 'raven'], ['#5b5459', '#9c654f', '#85796b'], 'Obsidian gate between cooled lava cliffs', 38],
};

const regionalPopulations = {
  sunmeadow_march: ['aegis', 'empire', 'dwarf', 'high_elf'],
  greybrook_crossing: ['aegis', 'empire', 'dwarf', 'high_elf'],
  ironwood_redoubt: ['aegis', 'empire', 'dwarf', 'high_elf'],
  brightfen_approach: ['aegis', 'high_elf', 'empire', 'dwarf'],
  glassriver_ford: ['aegis', 'high_elf', 'dwarf', 'empire'],
  highvale_rampart: ['aegis', 'dwarf', 'high_elf', 'empire'],
  cinderfen_outskirts: ['riftbound', 'greenskin', 'dark_elf', 'chaos'],
  bleakroot_causeway: ['riftbound', 'greenskin', 'dark_elf', 'chaos'],
  vilemere_heights: ['riftbound', 'dark_elf', 'greenskin', 'chaos'],
  ashen_steppe: ['riftbound', 'chaos', 'greenskin', 'dark_elf'],
  gorepine_pass: ['riftbound', 'chaos', 'dark_elf', 'greenskin'],
  obsidian_scar: ['riftbound', 'chaos', 'greenskin', 'dark_elf'],
  aegis_crownworks: ['aegis', 'dwarf', 'empire', 'high_elf'],
  dawnline_expanse: ['aegis', 'empire', 'high_elf', 'dwarf'],
  shatterline_expanse: ['riftbound', 'chaos', 'greenskin', 'dark_elf'],
  rift_crownworks: ['riftbound', 'chaos', 'greenskin', 'dark_elf'],
  aegis_gate_fortress: ['aegis', 'empire', 'dwarf', 'high_elf'],
  rift_gate_fortress: ['riftbound', 'chaos', 'dark_elf', 'greenskin'],
};

const lairs = {
  wardens_hollow: ['sunmeadow_march', 'Veteran barrow sentinel and woodland pack', 'Root-covered limestone barrow beneath an old oak'],
  briarwatch_den: ['greybrook_crossing', 'River ambushers and thorn-bound den guardian', 'Flood-cut bank with thorn canopy and ruined ferry pier'],
  stormbarrow_lair: ['ironwood_redoubt', 'Forest sentinels and storm-scarred overlord', 'Lightning-split trees around a weathered burial terrace'],
  mireglass_den: ['brightfen_approach', 'Fen stalkers and mire guardian', 'Reflective fen pool with reed-island nesting grounds'],
  glassriver_depths: ['glassriver_ford', 'River predators and drowned-vault guardian', 'Water-cut limestone chamber below the river shelf'],
  highvale_sanctum: ['highvale_rampart', 'Cold-weather sentinels and mountain guardian', 'Snow-sheltered ritual terraces beneath an ice cornice'],
  cindermaw_pit: ['cinderfen_outskirts', 'Vent predators and cindermaw guardian', 'Mineral-crusted sinkhole and steaming reed margins'],
  rotwreath_nest: ['bleakroot_causeway', 'Root ambushers and nest overlord', 'Interlocked root vault above drowned forest floor'],
  nightglass_hollow: ['vilemere_heights', 'Moor hunters and slate-hollow guardian', 'Water-polished slate cleft with wind-torn heather'],
  ashfang_pit: ['ashen_steppe', 'Steppe scavengers and ashfang pack leader', 'Ochre dry wash opening into a layered sandstone pit'],
  gorepine_warrens: ['gorepine_pass', 'Mountain packs and cold-den guardian', 'Pine-root burrows between frost-shattered rock faces'],
  obsidian_maw: ['obsidian_scar', 'Scar predators and glass-maw guardian', 'Cooled lava throat with fractured obsidian ribs'],
};

export const ORVR_ART_DIRECTIONS = Object.freeze(Object.fromEntries(Object.entries(regions).map(([zoneId, value]) => {
  const [biomeId, season, cultures, vegetation, fauna, palette, landmark, reliefMetres] = value;
  const [realm, ...races] = regionalPopulations[zoneId];
  return [zoneId, Object.freeze({
    zoneId, realm, races, biomeId, season, cultures, vegetation, fauna, palette, landmark, reliefMetres,
    vegetationAssetKeys: vegetation.map((species) => `frontier_${biomeId}_${species}`),
    creatureProfileKeys: fauna.map((species) => `frontier_creature_${species}`),
    materialSetKey: `frontier_${biomeId}_materials`,
    architectureAssetKey: `frontier_${biomeId}_settlement`,
    status: 'planned',
  })];
})));

export const ORVR_LAIR_ART_DIRECTIONS = Object.freeze(Object.fromEntries(Object.entries(lairs).map(([zoneId, [parentZoneId, population, landmark]]) => [zoneId, Object.freeze({
  ...ORVR_ART_DIRECTIONS[parentZoneId], zoneId, parentZoneId, population, landmark,
  bossProfileKey: `frontier_boss_${zoneId}`, optionalCampaignBranch: true,
})])));

export const WORLD_ART_DIRECTIONS = Object.freeze({ ...ORVR_ART_DIRECTIONS, ...ORVR_LAIR_ART_DIRECTIONS });

export const FRONTIER_SIEGE_ASSET_KEYS = Object.freeze({
  caravan: 'frontier_supply_wagon', ram: 'frontier_battering_ram',
  oil: 'frontier_oil_cauldron', catapult: 'frontier_field_catapult', gate: 'frontier_keep_gate',
});
