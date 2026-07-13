import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import {
  CAMPAIGN_STATIC_VERSION,
  EDGES,
  LANE_LABELS,
  NODES,
  REALMS,
} from './static-campaign-source.mjs';
import { withEnemyVisual, withNpcVisual } from '../npc-profile-rules.mjs';

const root = process.cwd();
const mapsDir = path.join(root, 'public', 'assets', 'maps');
const dataDir = path.join(root, 'src', 'data');
const supabaseDir = path.join(root, 'supabase');

const ROLE_SIZE = {
  capital: 360,
  fortress: 340,
  battlefield: 300,
  boss_lair: 190,
};

const ROLE_SEGMENTS = {
  capital: 96,
  fortress: 96,
  battlefield: 96,
  boss_lair: 64,
};

const nodeById = new Map(NODES.map((node) => [node.id, node]));
const neighborsById = buildNeighbors();
const portalPoints = buildPortalPoints();
const IMPORTED_AEGIS_CAPITAL_ID = 'aegis_capital';
const AEGIS_CAPITAL_GUARD_VARIANT_PROFILES = [
  'npc_external_warrior_guard',
  'npc_external_warrior_guard',
  'npc_external_swordsman',
  'npc_external_medieval_character',
];

const IMPORTED_AEGIS_CAPITAL_TRIGGERS = {
  aegis_gate_fortress: { x: 0, z: -164, radius: 12 },
  sunmeadow_march: { x: -164, z: -18, radius: 12 },
  brightfen_approach: { x: 164, z: -18, radius: 12 },
};

const THEME_TEXTURE = {
  aegis_city: 'cobblestone.svg',
  aegis_fortress: 'stone_wall.svg',
  aegis_highlands: 'grass.png',
  frontier_grassland: 'grass.png',
  rift_frontier: 'grass.png',
  rift_highlands: 'grass.png',
  rift_fortress: 'stone_wall.svg',
  rift_city: 'stone_wall.svg',
};

const zones = [];
const mapHashes = {};

await mkdir(mapsDir, { recursive: true });
await mkdir(dataDir, { recursive: true });
await mkdir(supabaseDir, { recursive: true });

for (const node of NODES) {
  const zone = buildZone(node);
  const hash = hashZone(zone);
  zone.staticMapHash = hash;
  zones.push(zone);
  mapHashes[node.id] = hash;
  await writeFile(
    path.join(mapsDir, `${node.id}.json`),
    `${JSON.stringify(zone, null, 2)}\n`,
    'utf8',
  );
}

await writeGeneratedData();
await writeSupabaseSeed();

console.log(`[campaign] Generated ${zones.length} static campaign map(s).`);

function buildNeighbors() {
  const map = new Map(NODES.map((node) => [node.id, []]));
  for (const [a, b] of EDGES) {
    if (!nodeById.has(a)) throw new Error(`Unknown edge node "${a}"`);
    if (!nodeById.has(b)) throw new Error(`Unknown edge node "${b}"`);
    map.get(a).push(b);
    map.get(b).push(a);
  }
  for (const [id, neighbors] of map.entries()) {
    neighbors.sort((a, b) => edgeSortKey(a).localeCompare(edgeSortKey(b)));
    map.set(id, neighbors);
  }
  return map;
}

function edgeSortKey(id) {
  const node = nodeById.get(id);
  return `${node.lane}:${node.tier}:${node.id}`;
}

function buildPortalPoints() {
  const result = {};
  for (const node of NODES) {
    const size = ROLE_SIZE[node.nodeRole];
    const radius = size * 0.43;
    const spawnRadius = radius - 14;
    const neighbors = neighborsById.get(node.id) ?? [];
    result[node.id] = {};
    const baseAngles = neighbors.map((neighborId, index) =>
      baseAngleForConnection(node, neighborId, index, neighbors.length),
    );
    const angleCounts = countBy(baseAngles.map(angleGroupKey));
    const angleSeen = new Map();
    neighbors.forEach((neighborId, index) => {
      const baseAngle = baseAngles[index];
      const groupKey = angleGroupKey(baseAngle);
      const ordinal = angleSeen.get(groupKey) ?? 0;
      angleSeen.set(groupKey, ordinal + 1);
      const angle = fanPortalAngle(baseAngle, ordinal, angleCounts.get(groupKey) ?? 1);
      result[node.id][neighborId] = {
        trigger: pointAt(angle, radius),
        spawn: pointAt(angle, spawnRadius),
      };
    });
  }
  return result;
}

function baseAngleForConnection(node, neighborId, index, total) {
  const neighbor = nodeById.get(neighborId);
  if (node.lane === 'central' && neighbor.lane === 'central') {
    if (neighbor.realm === 'riftbound' && node.realm !== 'riftbound') return -Math.PI / 2;
    if (neighbor.realm === 'aegis' && node.realm !== 'aegis') return Math.PI / 2;
    return centralRank(neighbor) < centralRank(node) ? -Math.PI / 2 : Math.PI / 2;
  }
  if (neighbor.lane.endsWith('_west')) return Math.PI;
  if (neighbor.lane.endsWith('_east')) return 0;
  if (node.lane.endsWith('_west') && neighbor.lane === 'central') return 0;
  if (node.lane.endsWith('_east') && neighbor.lane === 'central') return Math.PI;
  if (neighbor.nodeRole === 'boss_lair') return neighbor.lane.endsWith('_west') ? -Math.PI * 0.72 : -Math.PI * 0.28;
  const start = -Math.PI / 2;
  return start + (index / Math.max(1, total)) * Math.PI * 2;
}

function countBy(values) {
  const result = new Map();
  for (const value of values) result.set(value, (result.get(value) ?? 0) + 1);
  return result;
}

function angleGroupKey(angle) {
  return angle.toFixed(4);
}

function fanPortalAngle(baseAngle, ordinal, count) {
  if (count <= 1) return baseAngle;
  const spacing = 0.34;
  return baseAngle + (ordinal - (count - 1) / 2) * spacing;
}

function centralRank(node) {
  const order = [
    'riftspire_capital',
    'rift_gate_fortress',
    'rift_crownworks',
    'shatterline_expanse',
    'dawnline_expanse',
    'aegis_crownworks',
    'aegis_gate_fortress',
    'aegis_capital',
  ];
  return order.indexOf(node.id);
}

function pointAt(angle, radius) {
  return {
    x: round(Math.cos(angle) * radius),
    z: round(Math.sin(angle) * radius),
    angle,
  };
}

function defaultSpawnPoint(node) {
  if (node.nodeRole === 'capital') return { x: 0, y: 0, z: -118 };
  if (node.nodeRole === 'fortress') return { x: 0, y: 0, z: -118 };
  if (node.nodeRole === 'boss_lair') return { x: 0, y: 0, z: -58 };
  return { x: 0, y: 0, z: -40 };
}

function buildZone(node) {
  const size = ROLE_SIZE[node.nodeRole];
  const zone = {
    id: node.id,
    name: node.name,
    size,
    segments: ROLE_SEGMENTS[node.nodeRole],
    terrainTexture: THEME_TEXTURE[node.theme] ?? 'grass.png',
    skybox: 'sky.hdr',
    flatTerrain: node.nodeRole === 'capital',
    staticMapVersion: CAMPAIGN_STATIC_VERSION,
    campaign: {
      realm: node.realm,
      tier: node.tier,
      lane: node.lane,
      laneLabel: LANE_LABELS[node.lane],
      nodeRole: node.nodeRole,
      levelBand: node.levelBand,
    },
    spawnPoint: defaultSpawnPoint(node),
    paths: buildPaths(node),
    props: [],
    npcs: buildNpcs(node).map((npc) => withNpcVisual(zoneContext(node), npc)),
    craftingStations: buildCraftingStations(node),
    enemies: [],
    resourceNodes: [],
    rvrObjectives: buildObjectives(node),
    zoneTriggers: buildTriggers(node),
    biomeKits: buildBiomeKits(node),
  };

  const resources = buildResourceNodes(node);
  zone.resourceNodes = resources.nodes;
  zone.props.push(...buildObjectiveProps(node, zone.rvrObjectives));
  zone.props.push(...buildPortalProps(node));
  zone.props.push(...buildCraftingStationProps(zone.craftingStations));
  zone.props.push(...buildCampProps(node));
  zone.props.push(...resources.props);
  zone.props.push(...buildEnvironmentProps(node));
  zone.enemies.push(...buildEnemies(node).map((enemy) => withEnemyVisual(zoneContext(node), enemy)));

  return zone;
}

function zoneContext(node) {
  return {
    id: node.id,
    campaign: {
      realm: node.realm,
      tier: node.tier,
      lane: node.lane,
      nodeRole: node.nodeRole,
      levelBand: node.levelBand,
    },
  };
}

function isImportedAegisCapital(_node) {
  // The legacy imported capital mesh is intentionally retired. Both capitals
  // now use the deterministic original town and castle asset family.
  return false;
}

function buildPaths(node) {
  if (isImportedAegisCapital(node)) return [];

  const mainRoadPoints = node.nodeRole === 'capital'
    ? [{ x: 0, z: -122 }, { x: 0, z: -70 }, { x: 0, z: 0 }, { x: 0, z: 58 }, { x: 0, z: 136 }]
    : [{ x: 0, z: -70 }, { x: 0, z: 0 }, { x: 0, z: 70 }];
  const paths = [
    {
      id: `${node.id}_main_road`,
      style: node.nodeRole === 'capital' || node.nodeRole === 'fortress'
        ? 'cobblestone_avenue'
        : 'dirt_trail',
      width: node.nodeRole === 'boss_lair' ? 7 : 11,
      points: mainRoadPoints,
    },
  ];

  const portals = Object.values(portalPoints[node.id] ?? {});
  for (const [index, entry] of portals.entries()) {
    paths.push({
      id: `${node.id}_portal_road_${index + 1}`,
      style: node.nodeRole === 'capital' || node.nodeRole === 'fortress'
        ? 'cobblestone_avenue'
        : 'dirt_trail',
      width: node.nodeRole === 'boss_lair' ? 6 : 8,
      points: [{ x: 0, z: 0 }, { x: entry.trigger.x, z: entry.trigger.z }],
    });
  }
  if (node.nodeRole === 'capital') {
    paths.push(...capitalStreetPaths(node));
  }

  return paths;
}

function capitalStreetPaths(node) {
  return [
    {
      id: `${node.id}_west_gate_road`,
      style: 'cobblestone_avenue',
      width: 9,
      points: [{ x: -126, z: 0 }, { x: -84, z: 0 }, { x: -36, z: 0 }, { x: 0, z: 0 }],
    },
    {
      id: `${node.id}_east_gate_road`,
      style: 'cobblestone_avenue',
      width: 9,
      points: [{ x: 0, z: 0 }, { x: 36, z: 0 }, { x: 84, z: 0 }, { x: 126, z: 0 }],
    },
    ...[-58, -30, 28, 70, 112].map((z, index) => ({
      id: `${node.id}_cross_street_${index + 1}`,
      style: 'cobblestone_avenue',
      width: index === 3 ? 8 : 7,
      points: [{ x: -108, z }, { x: -56, z }, { x: -18, z }, { x: 18, z }, { x: 56, z }, { x: 108, z }],
    })),
    {
      id: `${node.id}_west_inner_lane`,
      style: 'cobblestone_avenue',
      width: 6,
      points: [{ x: -92, z: -70 }, { x: -92, z: -24 }, { x: -92, z: 34 }, { x: -92, z: 92 }, { x: -92, z: 132 }],
    },
    {
      id: `${node.id}_east_inner_lane`,
      style: 'cobblestone_avenue',
      width: 6,
      points: [{ x: 92, z: -70 }, { x: 92, z: -24 }, { x: 92, z: 34 }, { x: 92, z: 92 }, { x: 92, z: 132 }],
    },
    {
      id: `${node.id}_castle_service_lane`,
      style: 'cobblestone_avenue',
      width: 6,
      points: [{ x: -44, z: 54 }, { x: -54, z: 88 }, { x: -44, z: 126 }, { x: 0, z: 136 }, { x: 44, z: 126 }, { x: 54, z: 88 }, { x: 44, z: 54 }],
    },
  ];
}

function buildBiomeKits(node) {
  if (isImportedAegisCapital(node)) return [];

  const size = ROLE_SIZE[node.nodeRole];
  const commonExcludes = [
    { x: 0, z: -40, radius: 24 },
    { x: 0, z: 0, radius: node.nodeRole === 'capital' ? 44 : 34 },
    { x: 0, z: 58, radius: node.nodeRole === 'battlefield' ? 42 : 24 },
  ];
  if (node.nodeRole === 'battlefield' || node.nodeRole === 'fortress') {
    const keepX = node.nodeRole === 'fortress' ? 58 : 52;
    const keepZ = node.nodeRole === 'fortress' ? 58 : 62;
    commonExcludes.push(
      { x: -keepX, z: keepZ, radius: node.nodeRole === 'fortress' ? 48 : 42 },
      { x: keepX, z: keepZ, radius: node.nodeRole === 'fortress' ? 48 : 42 },
    );
  }
  if (node.nodeRole === 'capital') {
    commonExcludes.push(
      { x: 0, z: 92, radius: 78 },
      { x: 0, z: -86, radius: 42 },
      { x: -116, z: 0, radius: 26 },
      { x: 116, z: 0, radius: 26 },
      { x: 0, z: 136, radius: 34 },
    );
  }
  if (node.nodeRole === 'capital') {
    return [
      biomeKit(node, 'west_garden', -104, 58, 46, 118, 24, commonExcludes, ['pnw_grass_clump', 'pnw_wildflower_clump', 'pnw_low_shrub']),
      biomeKit(node, 'east_garden', 104, 58, 46, 118, 24, commonExcludes, ['pnw_grass_clump', 'pnw_wildflower_clump', 'pnw_low_shrub']),
    ];
  }
  if (node.nodeRole === 'fortress') {
    return [
      biomeKit(node, 'west_scarp', -96, -8, 94, 170, 46, commonExcludes, themeAllowedKinds(node)),
      biomeKit(node, 'east_scarp', 96, -8, 94, 170, 46, commonExcludes, themeAllowedKinds(node)),
    ];
  }
  if (node.nodeRole === 'boss_lair') {
    return [
      biomeKit(node, 'lair_ring', 0, 8, size * 0.9, size * 0.75, 42, commonExcludes, themeAllowedKinds(node)),
    ];
  }
  return [
    biomeKit(node, 'west_wilds', -86, 12, 92, 176, 58, commonExcludes, themeAllowedKinds(node)),
    biomeKit(node, 'east_wilds', 86, 12, 92, 176, 58, commonExcludes, themeAllowedKinds(node)),
  ];
}

function biomeKit(node, suffix, x, z, width, depth, count, exclude, allowedKinds) {
  return {
    id: `${node.id}_${suffix}`,
    biomeId: 'evergreen_pnw',
    activeSeason: 'summer',
    x,
    z,
    width,
    depth,
    count,
    seed: hashNumber(`${node.id}:${suffix}`),
    shape: 'ellipse',
    exclude,
    allowedKinds,
  };
}

function themeAllowedKinds(node) {
  if (/fen|mire|bleakroot|glassriver/i.test(node.theme)) {
    return ['pnw_sword_fern', 'pnw_low_shrub', 'pnw_grass_clump', 'pnw_mossy_boulder', 'pnw_fallen_log'];
  }
  if (/forest|ironwood|gorepine|briar/i.test(node.theme)) {
    return ['pnw_douglas_fir', 'pnw_western_red_cedar', 'pnw_hemlock', 'pnw_sword_fern', 'pnw_fallen_log'];
  }
  if (/obsidian|ash|cinder|rift|scar/i.test(node.theme)) {
    return ['pnw_low_shrub', 'pnw_grass_clump', 'pnw_mossy_boulder', 'pnw_fallen_log'];
  }
  return ['pnw_douglas_fir', 'pnw_sword_fern', 'pnw_grass_clump', 'pnw_wildflower_clump', 'pnw_mossy_boulder'];
}

function buildCraftingStations(node) {
  if (isImportedAegisCapital(node)) {
    return [
      station(node, 'apothecary', 'Apothecary Table', -40, -72),
      station(node, 'talisman', 'Talisman Workbench', 40, -72, 'talisman_making'),
      station(node, 'cultivation', 'Cultivation Plots', -42, 72, 'cultivation', 7),
      station(node, 'salvage', 'Salvage Bench', 42, 72, 'salvage'),
      station(node, 'general', 'Campaign Supply Table', 0, -104, 'general'),
    ];
  }
  if (node.nodeRole === 'capital') {
    return [
      station(node, 'apothecary', 'Apothecary Table', -42, -18),
      station(node, 'talisman', 'Talisman Workbench', 42, -18, 'talisman_making'),
      station(node, 'cultivation', 'Cultivation Plots', -42, 22, 'cultivation', 7),
      station(node, 'salvage', 'Salvage Bench', 42, 22, 'salvage'),
      station(node, 'general', 'Campaign Supply Table', 0, -12, 'general'),
    ];
  }
  if (node.nodeRole === 'fortress') {
    return [
      station(node, 'salvage', 'Siege Salvage Bench', -42, -44, 'salvage'),
      station(node, 'apothecary', 'Field Apothecary Table', 42, -44, 'apothecary'),
      station(node, 'general', 'Fortress Supply Table', 0, -52, 'general'),
    ];
  }
  if (node.nodeRole === 'boss_lair') {
    return [
      station(node, 'general', 'Expedition Supply Cache', 0, -26, 'general', 6),
    ];
  }
  return [
    station(node, 'cultivation', 'Field Cultivation Patch', -34, -48, 'cultivation', 7),
    station(node, 'salvage', 'War Salvage Bench', 34, -48, 'salvage'),
    station(node, 'apothecary', 'Field Apothecary Table', 0, -56, 'apothecary'),
  ];
}

function station(node, suffix, label, x, z, kind = suffix, radius = 6) {
  return {
    id: `${node.id}_${suffix}_station`,
    label,
    kind,
    x,
    z,
    radius,
  };
}

function buildCraftingStationProps(stations) {
  return stations.map((entry, index) => {
    const kind = entry.kind === 'cultivation'
      ? 'pnw_grass_clump'
      : entry.kind === 'salvage'
        ? 'vendor_stall'
        : entry.kind === 'talisman_making'
          ? 'statue'
          : 'vendor_stall';
    return prop(`${entry.id}_visual`, kind, entry.x, entry.z, index * 0.35, entry.kind === 'cultivation' ? 1.35 : 0.9);
  });
}

function buildCampProps(node) {
  if (isImportedAegisCapital(node)) {
    return importedAegisCapitalProps(node);
  }
  if (node.nodeRole === 'capital') {
    return [
      ...capitalCityProps(node),
      prop(`${node.id}_market_stall_west`, 'vendor_stall', -64, -12, 0.4, 0.95),
      prop(`${node.id}_market_stall_east`, 'vendor_stall', 64, -12, -0.4, 0.95),
      ...(node.realm === 'riftbound'
        ? [
            prop(`${node.id}_central_brazier_west`, 'rift_brazier', -10, 18, 0, 1.0),
            prop(`${node.id}_central_brazier_east`, 'rift_brazier', 10, 18, 0, 1.0),
            prop(`${node.id}_marshal_obelisk`, 'rift_obelisk', 0, 40, 0, 1.0),
          ]
        : [
            prop(`${node.id}_central_fountain`, 'fountain', 0, 18, 0, 1.2),
            prop(`${node.id}_marshal_statue`, 'statue', 0, 40, 0, 1.35),
          ]),
    ];
  }
  if (node.nodeRole === 'fortress') {
    return [
      prop(`${node.id}_outer_yard_barricade_left`, 'wall_segment', -64, -40, 0.25, 0.8),
      prop(`${node.id}_outer_yard_barricade_right`, 'wall_segment', 64, -40, -0.25, 0.8),
      prop(`${node.id}_siege_workshop`, 'vendor_stall', 54, -38, -0.6, 1.05),
      prop(`${node.id}_field_hospital`, 'vendor_stall', -54, -38, 0.6, 1.05),
      prop(`${node.id}_fortress_watchtower_west`, 'tower', -88, 8, 0, 0.85),
      prop(`${node.id}_fortress_watchtower_east`, 'tower', 88, 8, 0, 0.85),
    ];
  }
  if (node.nodeRole === 'boss_lair') {
    return [
      prop(`${node.id}_lair_cache_left`, 'vendor_stall', -20, -18, 0.7, 0.75),
      prop(`${node.id}_lair_cache_right`, 'vendor_stall', 20, -18, -0.7, 0.75),
      prop(`${node.id}_lair_warning_totem`, 'banner_post', 0, 18, 0, 1.2),
    ];
  }
  return [
    prop(`${node.id}_west_camp_tent`, 'vendor_stall', -46, 12, 0.55, 0.95),
    prop(`${node.id}_west_camp_banner`, 'banner_post', -58, 6, 0, 1.05),
    prop(`${node.id}_east_camp_tent`, 'vendor_stall', 46, 12, -0.55, 0.95),
    prop(`${node.id}_east_camp_banner`, 'banner_post', 58, 6, 0, 1.05),
    prop(`${node.id}_keep_supply_cart`, 'vendor_stall', 0, 26, 0, 0.85),
    prop(`${node.id}_field_bridge`, 'bridge', 0, -8, 0, 0.75),
  ];
}

function capitalCityProps(node) {
  return [
    ...capitalOuterWallProps(node),
    ...capitalHousingProps(node),
    ...capitalDistrictProps(node),
    ...capitalCitadelProps(node),
    ...capitalRealmLandmarks(node),
  ];
}

function importedAegisCapitalProps(node) {
  return [
    prop(`${node.id}_imported_city_collision_proxy`, 'aegis_capital_collision_proxy', 0, 0, 0, 1, {
      visible: false,
      colliders: importedAegisCapitalColliders(node.id),
    }),
  ];
}

function importedAegisCapitalColliders(zoneId) {
  return [
    // Outer wall ring. Gaps remain at the front, side, and rear gates.
    importedCollider(zoneId, 'front_wall_west', -103, -164, 118, 12),
    importedCollider(zoneId, 'front_wall_east', 103, -164, 118, 12),
    importedCollider(zoneId, 'west_wall_south', -164, -88, 12, 92),
    importedCollider(zoneId, 'west_wall_north', -164, 76, 12, 144),
    importedCollider(zoneId, 'east_wall_south', 164, -88, 12, 92),
    importedCollider(zoneId, 'east_wall_north', 164, 76, 12, 144),
    importedCollider(zoneId, 'rear_wall_west', -96, 164, 122, 12),
    importedCollider(zoneId, 'rear_wall_east', 96, 164, 122, 12),

    // Dense house blocks, leaving the central avenue, side streets, and plazas open.
    importedCollider(zoneId, 'lower_houses_west', -88, -86, 82, 56),
    importedCollider(zoneId, 'lower_houses_east', 88, -86, 82, 56),
    importedCollider(zoneId, 'market_block_west', -86, -40, 72, 28),
    importedCollider(zoneId, 'market_block_east', 86, -40, 72, 28),
    importedCollider(zoneId, 'middle_houses_west', -104, 22, 60, 64),
    importedCollider(zoneId, 'middle_houses_east', 104, 22, 60, 64),
    importedCollider(zoneId, 'upper_houses_west', -94, 84, 76, 58),
    importedCollider(zoneId, 'upper_houses_east', 94, 84, 76, 58),
    importedCollider(zoneId, 'rear_houses_west', -68, 132, 58, 38),
    importedCollider(zoneId, 'rear_houses_east', 68, 132, 58, 38),

    // Landmark clusters inside the imported city mesh.
    importedCollider(zoneId, 'north_court_cluster', 0, 100, 48, 54),
    importedCollider(zoneId, 'south_market_cluster_west', -40, -106, 30, 34),
    importedCollider(zoneId, 'south_market_cluster_east', 40, -106, 30, 34),
  ];
}

function importedCollider(zoneId, suffix, x, z, width, depth, rotY = 0) {
  return {
    id: `${zoneId}_imported_${suffix}_collider`,
    x,
    z,
    width,
    depth,
    rotY,
  };
}

function capitalOuterWallProps(node) {
  const id = `${node.id}_city_wall`;
  const wallKind = node.realm === 'riftbound' ? 'rift_wall_segment' : 'wall_segment';
  const towerKind = node.realm === 'riftbound' ? 'rift_tower' : 'tower';
  return [
    wallPropKind(`${id}_front_left`, wallKind, -74, -86, 0, 1.16, 52),
    wallPropKind(`${id}_front_right`, wallKind, 74, -86, 0, 1.16, 52),
    wallPropKind(`${id}_west_lower`, wallKind, -126, -51, Math.PI / 2, 1.1, 70),
    wallPropKind(`${id}_west_upper`, wallKind, -126, 76, Math.PI / 2, 1.1, 120),
    wallPropKind(`${id}_east_lower`, wallKind, 126, -51, Math.PI / 2, 1.1, 70),
    wallPropKind(`${id}_east_upper`, wallKind, 126, 76, Math.PI / 2, 1.1, 120),
    wallPropKind(`${id}_rear_left`, wallKind, -64, 136, 0, 1.12, 76),
    wallPropKind(`${id}_rear_right`, wallKind, 64, 136, 0, 1.12, 76),
    cityGateProp(`${id}_west_gate`, `${node.name} West Gate`, -126, 0, -Math.PI / 2, 1.18),
    cityGateProp(`${id}_east_gate`, `${node.name} East Gate`, 126, 0, Math.PI / 2, 1.18),
    cityGateProp(`${id}_rear_gate`, `${node.name} Rear Gate`, 0, 136, Math.PI, 1.3),
    towerProp(`${id}_tower_front_west`, -126, -86, 1.35, 0, towerKind),
    towerProp(`${id}_tower_front_east`, 126, -86, 1.35, 0, towerKind),
    towerProp(`${id}_tower_rear_west`, -126, 136, 1.45, 0, towerKind),
    towerProp(`${id}_tower_rear_east`, 126, 136, 1.45, 0, towerKind),
    towerProp(`${id}_west_gate_tower_south`, -126, -22, 1.08, 0, towerKind),
    towerProp(`${id}_west_gate_tower_north`, -126, 22, 1.08, 0, towerKind),
    towerProp(`${id}_east_gate_tower_south`, 126, -22, 1.08, 0, towerKind),
    towerProp(`${id}_east_gate_tower_north`, 126, 22, 1.08, 0, towerKind),
    towerProp(`${id}_rear_gate_tower_west`, -34, 136, 1.12, 0, towerKind),
    towerProp(`${id}_rear_gate_tower_east`, 34, 136, 1.12, 0, towerKind),
  ];
}

function capitalHousingProps(node) {
  const coords = [
    [-112, -72], [-90, -72], [-68, -72], [-44, -72], [-24, -72], [24, -72], [44, -72], [68, -72], [90, -72], [112, -72],
    [-106, -43], [-80, -43], [-54, -43], [-29, -43], [29, -43], [54, -43], [80, -43], [106, -43],
    [-106, -14], [-80, -14], [-54, -14], [-28, -14], [28, -14], [54, -14], [80, -14], [106, -14],
    [-108, 44], [-82, 44], [-55, 44], [-29, 44], [29, 44], [55, 44], [82, 44], [108, 44],
    [-109, 91], [-84, 91], [84, 91], [109, 91],
    [-108, 124], [-83, 124], [-58, 124], [58, 124], [83, 124], [108, 124],
  ];
  return coords.map(([x, z], index) => townBuildingProp(
    `${node.id}_capital_house_${String(index + 1).padStart(2, '0')}`,
    x,
    z,
    ((index % 7) - 3) * 0.045 + (x < 0 ? 0.03 : -0.03),
    0.78 + (index % 4) * 0.045,
    index % 4 === 0 ? 2 : 1,
  ));
}

function capitalDistrictProps(node) {
  const prefix = `${node.id}_capital_district`;
  return [
    townBuildingProp(`${prefix}_market_hall_west`, -43, -18, 0.12, 1.02, 2),
    townBuildingProp(`${prefix}_market_hall_east`, 43, -18, -0.12, 1.02, 2),
    townBuildingProp(`${prefix}_craft_hall_west`, -43, 17, -0.12, 0.94, 2),
    townBuildingProp(`${prefix}_training_hall_east`, 43, 17, 0.12, 0.94, 2),
    townBuildingProp(`${prefix}_barracks_west`, -63, 74, 0.06, 1.02, 2),
    townBuildingProp(`${prefix}_barracks_east`, 63, 74, -0.06, 1.02, 2),
    townBuildingProp(`${prefix}_upper_residence_west`, -42, 122, -0.08, 0.9, 1),
    townBuildingProp(`${prefix}_upper_residence_east`, 42, 122, 0.08, 0.9, 1),
    prop(`${prefix}_avenue_banner_west`, 'banner_post', -22, 54, 0, 1.12),
    prop(`${prefix}_avenue_banner_east`, 'banner_post', 22, 54, 0, 1.12),
    prop(`${prefix}_rear_banner_west`, 'banner_post', -24, 124, 0, 1.1),
    prop(`${prefix}_rear_banner_east`, 'banner_post', 24, 124, 0, 1.1),
  ];
}

function capitalCitadelProps(node) {
  const id = `${node.id}_capital_citadel`;
  const props = [solidProp(id, 'castle', 0, 86, 0, 1.22, 38, 34, {
    assetKey: 'town_castle',
    model: 'prop_town_castle.glb',
    collider: { minY: -0.4, maxY: 34 },
  })];
  props.push(prop(`${id}_banner_west`, 'banner_post', -24, 66, 0, 1.14));
  props.push(prop(`${id}_banner_east`, 'banner_post', 24, 66, 0, 1.14));
  if (node.realm === 'riftbound') {
    props.push(prop(`${id}_brazier_west`, 'rift_brazier', -19, 66, 0, 1.0));
    props.push(prop(`${id}_brazier_east`, 'rift_brazier', 19, 66, 0, 1.0));
  } else {
    props.push(prop(`${id}_forecourt_statue`, 'statue', 0, 60, 0, 1.1));
  }
  return props;
}

function capitalCitadelLevelWalls(id, levelNumber, level, wallKind, towerKind) {
  const props = [];
  const halfW = level.width / 2;
  const halfD = level.depth / 2;
  const frontZ = level.z - halfD;
  const rearZ = level.z + halfD;
  const leftX = -halfW;
  const rightX = halfW;
  const gap = levelNumber === 1 ? 22 : 10;
  const frontLen = (level.width - gap) / 2;
  const rearLen = levelNumber === 1 ? (level.width - 18) / 2 : level.width;
  props.push(levelWallProp(`${id}_level_${levelNumber}_front_left_wall`, wallKind, -(gap / 2 + frontLen / 2), frontZ, 0, frontLen, level.y));
  props.push(levelWallProp(`${id}_level_${levelNumber}_front_right_wall`, wallKind, gap / 2 + frontLen / 2, frontZ, 0, frontLen, level.y));
  if (levelNumber === 1) {
    props.push(levelWallProp(`${id}_level_${levelNumber}_rear_left_wall`, wallKind, -(9 + rearLen / 2), rearZ, 0, rearLen, level.y));
    props.push(levelWallProp(`${id}_level_${levelNumber}_rear_right_wall`, wallKind, 9 + rearLen / 2, rearZ, 0, rearLen, level.y));
  } else {
    props.push(levelWallProp(`${id}_level_${levelNumber}_rear_wall`, wallKind, 0, rearZ, 0, rearLen, level.y));
  }
  props.push(levelWallProp(`${id}_level_${levelNumber}_west_wall`, wallKind, leftX, level.z, Math.PI / 2, level.depth, level.y));
  props.push(levelWallProp(`${id}_level_${levelNumber}_east_wall`, wallKind, rightX, level.z, Math.PI / 2, level.depth, level.y));
  props.push(levelTowerProp(`${id}_level_${levelNumber}_tower_nw`, towerKind, leftX, frontZ, level.y, levelNumber));
  props.push(levelTowerProp(`${id}_level_${levelNumber}_tower_ne`, towerKind, rightX, frontZ, level.y, levelNumber));
  props.push(levelTowerProp(`${id}_level_${levelNumber}_tower_sw`, towerKind, leftX, rearZ, level.y, levelNumber));
  props.push(levelTowerProp(`${id}_level_${levelNumber}_tower_se`, towerKind, rightX, rearZ, level.y, levelNumber));
  return props;
}

function capitalRealmLandmarks(node) {
  if (node.realm === 'aegis') {
    return [
      solidProp(`${node.id}_sun_court_temple`, 'temple', -58, 92, 0.28, 1.05, 11, 14),
      towerProp(`${node.id}_sun_court_bell_tower`, 58, 96, 1.22),
      prop(`${node.id}_sun_court_fountain`, 'fountain', -58, 72, 0, 1.05),
      prop(`${node.id}_sun_court_statue`, 'statue', 58, 116, 0, 1.18),
      prop(`${node.id}_sun_court_banner_west`, 'banner_post', -44, 74, 0, 1.16),
      prop(`${node.id}_sun_court_banner_east`, 'banner_post', 44, 74, 0, 1.16),
    ];
  }
  return [
    towerProp(`${node.id}_rift_spire_west`, -58, 94, 1.4, 0, 'rift_tower'),
    towerProp(`${node.id}_rift_spire_east`, 58, 94, 1.34, 0, 'rift_tower'),
    prop(`${node.id}_rift_court_obelisk`, 'rift_obelisk', 0, 18, 0.2, 1.2),
    prop(`${node.id}_rift_court_brazier_west`, 'rift_brazier', -18, 18, 0, 1.0),
    prop(`${node.id}_rift_court_brazier_east`, 'rift_brazier', 18, 18, 0, 1.0),
    prop(`${node.id}_rift_court_shard_west`, 'rift_spike_cluster', -42, 112, 0.7, 1.8),
    prop(`${node.id}_rift_court_shard_east`, 'rift_spike_cluster', 42, 112, -0.7, 1.8),
    prop(`${node.id}_rift_court_spikes_south_west`, 'rift_spike_cluster', -34, 48, 0.4, 1.25),
    prop(`${node.id}_rift_court_spikes_south_east`, 'rift_spike_cluster', 34, 48, -0.4, 1.25),
    prop(`${node.id}_rift_court_banner_west`, 'banner_post', -44, 74, 0, 1.18),
    prop(`${node.id}_rift_court_banner_east`, 'banner_post', 44, 74, 0, 1.18),
  ];
}

function buildResourceNodes(node) {
  const count = node.nodeRole === 'capital'
    ? 8
    : node.nodeRole === 'battlefield'
      ? 12
      : node.nodeRole === 'fortress'
        ? 8
        : 5;
  const anchors = isImportedAegisCapital(node)
    ? importedAegisCapitalResourceAnchors()
    : resourceAnchors(node.nodeRole);
  const profile = resourceProfile(node);
  const nodes = [];
  const props = [];

  for (let i = 0; i < count; i += 1) {
    const anchor = anchors[i % anchors.length];
    const kind = profile[i % profile.length];
    const id = `${node.id}_${kind}_node_${String(i + 1).padStart(2, '0')}`;
    const visualPropId = `${id}_visual`;
    const jitter = deterministicJitter(node.id, i);
    const x = round(anchor.x + jitter.x);
    const z = round(anchor.z + jitter.z);
    nodes.push({
      id,
      label: resourceLabel(kind, node),
      kind,
      professionId: resourceProfession(kind),
      x,
      z,
      radius: 5,
      xp: resourceXp(kind, node),
      respawnSeconds: node.nodeRole === 'capital' ? 75 : node.nodeRole === 'boss_lair' ? 120 : 90,
      visualPropId,
      loot: resourceLoot(kind),
    });
    props.push(prop(
      visualPropId,
      resourceVisualKind(kind, i),
      x,
      z,
      jitter.rotY,
      resourceVisualScale(kind, i),
    ));
  }

  return { nodes, props };
}

function resourceAnchors(nodeRole) {
  if (nodeRole === 'capital') {
    return [
      { x: -102, z: 34 },
      { x: -98, z: 92 },
      { x: 102, z: 34 },
      { x: 98, z: 92 },
      { x: -82, z: -58 },
      { x: 82, z: -58 },
      { x: -56, z: 122 },
      { x: 56, z: 122 },
    ];
  }
  if (nodeRole === 'fortress') {
    return [
      { x: -96, z: -58 },
      { x: -112, z: 4 },
      { x: -74, z: 64 },
      { x: 96, z: -58 },
      { x: 112, z: 4 },
      { x: 74, z: 64 },
      { x: -28, z: -76 },
      { x: 28, z: -76 },
    ];
  }
  if (nodeRole === 'boss_lair') {
    return [
      { x: -48, z: -20 },
      { x: 48, z: -20 },
      { x: -42, z: 34 },
      { x: 42, z: 34 },
      { x: 0, z: 76 },
    ];
  }
  return [
    { x: -104, z: -62 },
    { x: -110, z: -4 },
    { x: -96, z: 52 },
    { x: -38, z: 86 },
    { x: 104, z: -62 },
    { x: 110, z: -4 },
    { x: 96, z: 52 },
    { x: 38, z: 86 },
    { x: -18, z: -92 },
    { x: 18, z: -92 },
    { x: -72, z: -104 },
    { x: 72, z: -104 },
  ];
}

function importedAegisCapitalResourceAnchors() {
  return [
    { x: -140, z: -128 },
    { x: 140, z: -128 },
    { x: -148, z: 34 },
    { x: 148, z: 34 },
    { x: -34, z: 148 },
    { x: 34, z: 148 },
    { x: -38, z: 68 },
    { x: 38, z: 68 },
  ];
}

function resourceProfile(node) {
  if (/fen|mire|bleakroot|glassriver/i.test(node.theme)) {
    return ['herb', 'water', 'soil', 'herb', 'wood', 'water'];
  }
  if (/forest|ironwood|gorepine|briar/i.test(node.theme)) {
    return ['wood', 'herb', 'wood', 'soil', 'herb', 'relic'];
  }
  if (/obsidian|ash|cinder|rift|scar|night|void/i.test(node.theme)) {
    return ['ore', 'scrap', 'relic', 'ore', 'soil', 'scrap'];
  }
  if (/city|fortress|crownworks|highlands|rampart/i.test(node.theme)) {
    return ['scrap', 'ore', 'herb', 'soil', 'relic', 'water'];
  }
  return ['herb', 'wood', 'ore', 'soil', 'water', 'scrap'];
}

function resourceLabel(kind, node) {
  const prefix = node.realm === 'aegis' ? 'Aegis' : 'Riftbound';
  switch (kind) {
    case 'herb': return `${prefix} Herb Patch`;
    case 'ore': return `${prefix} Ore Vein`;
    case 'wood': return `${prefix} Fallen Timber`;
    case 'water': return `${prefix} Springwater`;
    case 'soil': return `${prefix} Fertile Soil`;
    case 'scrap': return `${prefix} War Scrap`;
    case 'relic': return `${prefix} Relic Shards`;
    default: return `${prefix} Resource`;
  }
}

function resourceProfession(kind) {
  if (kind === 'ore' || kind === 'scrap' || kind === 'relic') return 'salvaging';
  return 'cultivation';
}

function resourceXp(kind, node) {
  const base = node.nodeRole === 'boss_lair' ? 11 : node.nodeRole === 'fortress' ? 10 : 8;
  return kind === 'relic' || kind === 'ore' ? base + 2 : base;
}

function resourceLoot(kind) {
  switch (kind) {
    case 'herb':
      return [
        { key: 'craft_mandrake_root', qty: 1, chance: 0.85, minQty: 1, maxQty: 2 },
        { key: 'craft_goldweed', qty: 1, chance: 0.65, minQty: 1, maxQty: 2 },
        { key: 'seed_mandrake', qty: 1, chance: 0.18 },
      ];
    case 'water':
      return [
        { key: 'craft_clear_water', qty: 1, chance: 0.9, minQty: 1, maxQty: 3 },
        { key: 'craft_vial_cloudy', qty: 1, chance: 0.28 },
      ];
    case 'soil':
      return [
        { key: 'craft_fertile_soil', qty: 1, chance: 0.85, minQty: 1, maxQty: 2 },
        { key: 'seed_goldweed', qty: 1, chance: 0.18 },
        { key: 'craft_stabilizing_salt', qty: 1, chance: 0.16 },
      ];
    case 'wood':
      return [
        { key: 'craft_fertile_soil', qty: 1, chance: 0.62 },
        { key: 'seed_mandrake', qty: 1, chance: 0.24 },
        { key: 'craft_torn_cloth', qty: 1, chance: 0.22 },
      ];
    case 'ore':
      return [
        { key: 'craft_scrap_iron', qty: 1, chance: 0.9, minQty: 1, maxQty: 3 },
        { key: 'craft_talisman_fragment', qty: 1, chance: 0.26 },
      ];
    case 'scrap':
      return [
        { key: 'craft_scrap_iron', qty: 1, chance: 0.8, minQty: 1, maxQty: 2 },
        { key: 'craft_torn_cloth', qty: 1, chance: 0.55, minQty: 1, maxQty: 2 },
        { key: 'craft_talisman_fragment', qty: 1, chance: 0.18 },
      ];
    case 'relic':
    default:
      return [
        { key: 'craft_arcane_dust', qty: 1, chance: 0.75, minQty: 1, maxQty: 2 },
        { key: 'craft_talisman_fragment', qty: 1, chance: 0.44 },
        { key: 'craft_essence_minor', qty: 1, chance: 0.14 },
      ];
  }
}

function resourceVisualKind(kind, index) {
  switch (kind) {
    case 'herb': return index % 2 === 0 ? 'pnw_wildflower_clump' : 'pnw_sword_fern';
    case 'ore': return 'pnw_mossy_boulder';
    case 'wood': return 'pnw_fallen_log';
    case 'water': return 'pnw_low_shrub';
    case 'soil': return 'pnw_grass_clump';
    case 'scrap': return 'rock';
    case 'relic': return 'statue';
    default: return 'rock';
  }
}

function resourceVisualScale(kind, index) {
  if (kind === 'relic') return 0.55 + (index % 2) * 0.1;
  if (kind === 'ore' || kind === 'scrap') return 0.75 + (index % 3) * 0.16;
  return 0.85 + (index % 3) * 0.12;
}

function deterministicJitter(zoneId, index) {
  const rng = createRng(hashNumber(`${zoneId}:resource:${index}`));
  return {
    x: round((rng() - 0.5) * 10),
    z: round((rng() - 0.5) * 10),
    rotY: roundAngle(rng() * Math.PI * 2),
  };
}

function buildTriggers(node) {
  if (isImportedAegisCapital(node)) {
    return (neighborsById.get(node.id) ?? []).map((targetId) => {
      const target = nodeById.get(targetId);
      const here = IMPORTED_AEGIS_CAPITAL_TRIGGERS[targetId] ?? portalPoints[node.id][targetId].trigger;
      const there = portalPoints[targetId][node.id];
      return {
        id: `${node.id}_to_${targetId}`,
        label: `Travel to ${target.name}`,
        x: here.x,
        z: here.z,
        radius: here.radius ?? 9,
        targetZoneId: targetId,
        targetSpawn: { x: there.spawn.x, y: 0, z: there.spawn.z },
      };
    });
  }

  return (neighborsById.get(node.id) ?? []).map((targetId) => {
    const target = nodeById.get(targetId);
    const here = portalPoints[node.id][targetId];
    const there = portalPoints[targetId][node.id];
    return {
      id: `${node.id}_to_${targetId}`,
      label: `Travel to ${target.name}`,
      x: here.trigger.x,
      z: here.trigger.z,
      radius: 9,
      targetZoneId: targetId,
      targetSpawn: { x: there.spawn.x, y: 0, z: there.spawn.z },
    };
  });
}

function buildObjectives(node) {
  if (isImportedAegisCapital(node)) {
    return [
      objective('city_gate', `${node.id}_city_gate`, `${node.name} Main Gate`, 0, -136, node.realm, 16),
      objective('battle_objective', `${node.id}_plaza`, 'Market Plaza', 0, -18, node.realm, 14),
    ];
  }
  if (node.nodeRole === 'capital') {
    return [
      objective('city_gate', `${node.id}_city_gate`, `${node.name} Gate`, 0, -86, node.realm, 16),
      objective('battle_objective', `${node.id}_plaza`, 'Central Plaza', 0, 0, node.realm, 14),
    ];
  }
  if (node.nodeRole === 'fortress') {
    return [
      objective('battle_objective', `${node.id}_west_objective`, 'West Siege Standard', -72, -24, node.realm, 14),
      objective('battle_objective', `${node.id}_central_objective`, 'Central Siege Standard', 0, -6, node.realm, 14),
      objective('battle_objective', `${node.id}_east_objective`, 'East Siege Standard', 72, -24, node.realm, 14),
      objective('keep', `${node.id}_aegis_keep`, 'Aegis War Keep', -58, 58, 'aegis', 18),
      objective('keep', `${node.id}_riftbound_keep`, 'Riftbound War Keep', 58, 58, 'riftbound', 18),
    ];
  }
  if (node.nodeRole === 'boss_lair') {
    return [
      objective('boss', `${node.id}_boss`, `${node.name} Overlord`, 0, 48, node.realm, 18),
    ];
  }
  return [
    objective('battle_objective', `${node.id}_west_objective`, 'West Field Standard', -64, -18, node.realm, 13),
    objective('battle_objective', `${node.id}_central_objective`, 'Central Field Standard', 0, 6, node.realm, 13),
    objective('battle_objective', `${node.id}_east_objective`, 'East Field Standard', 64, -18, node.realm, 13),
    objective('keep', `${node.id}_aegis_keep`, 'Aegis War Keep', -52, 62, 'aegis', 18),
    objective('keep', `${node.id}_riftbound_keep`, 'Riftbound War Keep', 52, 62, 'riftbound', 18),
  ];
}

function objective(type, id, label, x, z, defaultRealm, radius) {
  return {
    id,
    type,
    label,
    x,
    z,
    captureRadius: radius,
    defaultRealm,
  };
}

function buildObjectiveProps(node, objectives) {
  if (isImportedAegisCapital(node)) return [];

  const props = [];
  for (const obj of objectives) {
    if (obj.type === 'battle_objective') {
      props.push(prop(`${obj.id}_banner`, 'banner_post', obj.x, obj.z, 0, 1.15));
      props.push(prop(`${obj.id}_stone_left`, 'rock', obj.x - 7, obj.z + 4, 0.3, 1.1));
      props.push(prop(`${obj.id}_stone_right`, 'rock', obj.x + 7, obj.z + 4, -0.4, 1.05));
    }
    if (obj.type === 'keep') {
      props.push(...keepProps(`${obj.id}_keep`, obj.x, obj.z, obj.defaultRealm, node.nodeRole === 'fortress' ? 1.12 : 1));
      props.push(prop(`${obj.id}_banner_left`, 'banner_post', obj.x - 22, obj.z - 20, 0, 1.2));
      props.push(prop(`${obj.id}_banner_right`, 'banner_post', obj.x + 22, obj.z - 20, 0, 1.2));
    }
    if (obj.type === 'fortress') {
      props.push(...fortressProps(`${obj.id}_fortress`, obj.x, obj.z, node.realm));
    }
    if (obj.type === 'city_gate') {
      props.push(cityGateProp(`${obj.id}_gate`, obj.label, obj.x, obj.z, 0, 1.55));
      const towerKind = node.realm === 'riftbound' ? 'rift_tower' : 'tower';
      props.push(towerProp(`${obj.id}_tower_left`, obj.x - 34, obj.z, 1.3, 0, towerKind));
      props.push(towerProp(`${obj.id}_tower_right`, obj.x + 34, obj.z, 1.3, 0, towerKind));
    }
    if (obj.type === 'boss') {
      props.push(prop(`${obj.id}_altar`, 'statue', obj.x, obj.z + 5, 0, 1.7));
      props.push(prop(`${obj.id}_banner_left`, 'banner_post', obj.x - 12, obj.z - 10, 0.2, 1.1));
      props.push(prop(`${obj.id}_banner_right`, 'banner_post', obj.x + 12, obj.z - 10, -0.2, 1.1));
    }
  }
  return props;
}

function keepProps(id, x, z, realm, scaleMultiplier = 1) {
  const scale = (realm === 'aegis' ? 0.95 : 1.05) * scaleMultiplier;
  const props = [];
  const labelPrefix = realm === 'aegis' ? 'Aegis' : 'Riftbound';
  const at = (localX, localZ) => ({ x: x + localX * scale, z: z + localZ * scale });
  const addWall = (suffix, localX, localZ, length, rotY = 0, wallScale = 1) => {
    const point = at(localX, localZ);
    props.push(wallProp(`${id}_${suffix}`, point.x, point.z, rotY, scale * wallScale, length));
  };
  const addTower = (suffix, localX, localZ, towerScale = 1) => {
    const point = at(localX, localZ);
    props.push(prop(`${id}_${suffix}`, 'tower', point.x, point.z, 0, scale * towerScale, {
      colliders: [
        { id: `${id}_${suffix}_collider`, width: 7, depth: 7 },
      ],
    }));
  };
  const addDoor = (suffix, localX, localZ, rotY, doorScale, label, maxDistance = 14) => {
    const point = at(localX, localZ);
    props.push(interactiveDoorProp(`${id}_${suffix}`, label, point.x, point.z, rotY, scale * doorScale, maxDistance));
  };
  const addGate = (suffix, localX, localZ, rotY, gateScale, label, maxDistance = 20) => {
    const point = at(localX, localZ);
    props.push(interactiveDoorProp(`${id}_${suffix}`, label, point.x, point.z, rotY, scale * gateScale, maxDistance, 'castle_gate', 18, 2.5));
  };

  addWall('outer_front_left_wall', -18, -24, 18);
  addWall('outer_front_right_wall', 18, -24, 18);
  addWall('outer_rear_left_wall', -16.5, 24, 21);
  addWall('outer_rear_right_wall', 16.5, 24, 21);
  addWall('outer_west_wall', -27, 0, 48, Math.PI / 2);
  addWall('outer_east_wall', 27, 0, 48, Math.PI / 2);
  addTower('outer_tower_nw', -27, -24, 1.05);
  addTower('outer_tower_ne', 27, -24, 1.05);
  addTower('outer_tower_sw', -27, 24, 1.05);
  addTower('outer_tower_se', 27, 24, 1.05);
  addGate('front_gate', 0, -24, 0, 0.82, `${labelPrefix} Keep Gate`, 20);
  addDoor('rear_postern', 0, 24, Math.PI, 0.72, `${labelPrefix} Keep Postern`, 13);

  addWall('inner_front_left_wall', -9.5, -7.5, 11, 0, 0.86);
  addWall('inner_front_right_wall', 9.5, -7.5, 11, 0, 0.86);
  addWall('inner_rear_left_wall', -9.5, 15, 11, 0, 0.86);
  addWall('inner_rear_right_wall', 9.5, 15, 11, 0, 0.86);
  addWall('inner_west_wall', -15, 4, 23, Math.PI / 2, 0.86);
  addWall('inner_east_wall', 15, 4, 23, Math.PI / 2, 0.86);
  addTower('inner_tower_nw', -15, -7.5, 0.82);
  addTower('inner_tower_ne', 15, -7.5, 0.82);
  addTower('inner_tower_sw', -15, 15, 0.82);
  addTower('inner_tower_se', 15, 15, 0.82);
  addDoor('inner_front_door', 0, -7.5, 0, 0.66, `${labelPrefix} Keep Door`, 12);
  addDoor('inner_rear_door', 0, 15, Math.PI, 0.62, `${labelPrefix} Keep Rear Door`, 12);
  return props;
}

function fortressProps(id, x, z, realm) {
  return keepProps(id, x, z, realm, realm === 'aegis' ? 1.35 : 1.45);
}

function buildingProp(id, x, z, rotY, scale, width = 8, depth = 8, kind = 'building') {
  return solidProp(id, kind, x, z, rotY, scale, width, depth);
}

function townBuildingProp(id, x, z, rotY, scale, variant = 1) {
  const isLarge = variant === 2;
  return solidProp(id, 'building', x, z, rotY, scale, isLarge ? 12.2 : 9.8, isLarge ? 9 : 7.4, {
    assetKey: isLarge ? 'town_house_2' : 'town_house_1',
    model: isLarge ? 'prop_town_house_2.glb' : 'prop_town_house_1.glb',
    collider: { minY: -0.25, maxY: isLarge ? 12 : 10 },
    interaction: {
      id: `${id}_house_door`,
      type: 'house_portal',
      label: 'Enter House',
      maxDistance: isLarge ? 11 : 9,
      interiorVariant: isLarge ? 'large' : 'small',
    },
  });
}

function towerProp(id, x, z, scale, rotY = 0, kind = 'tower') {
  return solidProp(id, kind, x, z, rotY, scale, kind === 'rift_tower' ? 7.5 : 7, kind === 'rift_tower' ? 7.5 : 7);
}

function solidProp(id, kind, x, z, rotY, scale, width, depth, extra = {}) {
  const { collider, ...propExtra } = extra;
  return prop(id, kind, x, z, rotY, scale, {
    ...propExtra,
    colliders: [
      { id: `${id}_collider`, width, depth, ...(collider ?? {}) },
    ],
  });
}

function wallProp(id, x, z, rotY, scale, length) {
  return wallPropKind(id, 'wall_segment', x, z, rotY, scale, length);
}

function wallPropKind(id, kind, x, z, rotY, scale, length, extra = {}) {
  const { collider, ...propExtra } = extra;
  return prop(id, kind, x, z, rotY, scale, {
    ...propExtra,
    scaleX: roundScale(length / 10),
    colliders: [
      { id: `${id}_collider`, width: 10, depth: 1.8, ...(collider ?? {}) },
    ],
  });
}

function castleFloorProp(id, x, z, y, width, depth) {
  return prop(id, 'castle_floor', x, z, 0, 1, {
    y,
    scaleX: roundScale(width / 24),
    scaleZ: roundScale(depth / 24),
    walkableSurfaces: [
      { id: `${id}_walkable`, width: 24, depth: 24, fromY: 0, toY: 0 },
    ],
  });
}

function castleStairsProp(id, x, z, y, rotY) {
  return prop(id, 'castle_stairs', x, z, rotY, 1, {
    y,
    walkableSurfaces: [
      { id: `${id}_ramp`, width: 8, depth: 12, fromY: 0, toY: 4, axis: 'z' },
      { id: `${id}_landing`, z: 7, width: 10, depth: 6, fromY: 4, toY: 4 },
    ],
  });
}

function levelWallProp(id, kind, x, z, rotY, length, y) {
  return wallPropKind(id, kind, x, z, rotY, 1, length, {
    y,
    collider: { minY: -0.35, maxY: 3.85 },
  });
}

function levelTowerProp(id, kind, x, z, y, levelNumber) {
  const scale = Math.max(0.58, 0.95 - levelNumber * 0.06);
  return solidProp(id, kind, x, z, 0, scale, kind === 'rift_tower' ? 7.5 : 7, kind === 'rift_tower' ? 7.5 : 7, {
    y,
    collider: { minY: -0.35, maxY: 3.85 },
  });
}

function cityGateProp(id, label, x, z, rotY, scale) {
  return interactiveDoorProp(id, label, x, z, rotY, scale, 28, 'castle_gate', 18, 2.5);
}

function interactiveDoorProp(
  id,
  label,
  x,
  z,
  rotY,
  scale,
  maxDistance,
  kind = 'castle_door',
  colliderWidth = 5.4,
  colliderDepth = 1.2,
) {
  const interactionId = `${id}_interaction`;
  return prop(id, kind, x, z, rotY, scale, {
    model: kind === 'castle_gate' ? 'castle_gate.glb' : 'castle_door.glb',
    colliders: [
      {
        id: `${id}_closed_collider`,
        width: colliderWidth,
        depth: colliderDepth,
        blocksWhen: 'closed',
        interactionId,
      },
    ],
    interaction: {
      id: interactionId,
      type: 'gate',
      label,
      maxDistance,
      openClip: 'open',
      closeClip: 'close',
    },
  });
}

function buildPortalProps(node) {
  if (isImportedAegisCapital(node)) return [];

  return (neighborsById.get(node.id) ?? []).map((targetId) => {
    const point = portalPoints[node.id][targetId].trigger;
    return prop(`${node.id}_portal_${targetId}`, 'gate', point.x, point.z, point.angle + Math.PI / 2, 0.85, {
      colliders: [
        { id: `${node.id}_portal_${targetId}_marker`, width: 9, depth: 2 },
      ],
    });
  });
}

function buildEnvironmentProps(node) {
  if (isImportedAegisCapital(node)) return [];

  const rng = createRng(hashNumber(node.id));
  const props = [];
  const size = ROLE_SIZE[node.nodeRole];
  const treeCount = node.nodeRole === 'boss_lair' ? 20 : node.nodeRole === 'capital' ? 28 : 42;
  const rockCount = node.nodeRole === 'boss_lair' ? 18 : 30;
  const edgeRadius = size * 0.46;

  for (let i = 0; i < treeCount; i += 1) {
    const point = randomRingPoint(rng, size * 0.22, size * 0.44);
    if (tooCloseToCenter(point)) continue;
    if (node.nodeRole === 'capital' && insideCapitalCityFootprint(point)) continue;
    const kind = node.realm === 'riftbound' && i % 3 === 0 ? 'pnw_low_shrub' : 'tree';
    props.push(prop(`${node.id}_tree_${String(i + 1).padStart(2, '0')}`, kind, point.x, point.z, rng() * Math.PI * 2, 0.75 + rng() * 0.75));
  }

  for (let i = 0; i < rockCount; i += 1) {
    const point = randomRingPoint(rng, size * 0.28, edgeRadius);
    if (node.nodeRole === 'capital' && insideCapitalCityFootprint(point)) continue;
    props.push(prop(`${node.id}_rock_${String(i + 1).padStart(2, '0')}`, 'rock', point.x, point.z, rng() * Math.PI * 2, 0.7 + rng() * 1.8));
  }

  for (let i = 0; i < 18; i += 1) {
    const angle = (i / 18) * Math.PI * 2;
    const radius = edgeRadius + (i % 2) * 8;
    props.push(prop(`${node.id}_ridge_${String(i + 1).padStart(2, '0')}`, 'rock', Math.cos(angle) * radius, Math.sin(angle) * radius, angle, 1.9 + (i % 4) * 0.45));
  }

  return props;
}

function tooCloseToCenter(point) {
  return Math.hypot(point.x, point.z) < 42;
}

function insideCapitalCityFootprint(point) {
  return Math.abs(point.x) < 132 && point.z > -104 && point.z < 146;
}

function randomRingPoint(rng, minRadius, maxRadius) {
  const angle = rng() * Math.PI * 2;
  const radius = minRadius + rng() * (maxRadius - minRadius);
  return { x: round(Math.cos(angle) * radius), z: round(Math.sin(angle) * radius) };
}

function buildEnemies(node) {
  if (node.nodeRole === 'capital') {
    return [
      trainingDummy(node, 'training_dummy_1', 'Training Dummy', 58, 16, 1, 60),
      trainingDummy(node, 'training_dummy_2', 'Heavy Training Dummy', 70, 16, 3, 120),
      trainingDummy(node, 'training_dummy_3', 'Dueling Target', 82, 16, 2, 90),
    ];
  }
  if (node.nodeRole === 'boss_lair') {
    return [
      {
        id: `${node.id}_overlord`,
        name: `${node.name} Overlord`,
        level: bossLevel(node),
        x: 0,
        z: 48,
        maxHealth: 920,
        archetype: 'captain',
        aggroRange: 18,
        attackRange: 3.5,
        attackDamage: 34,
        moveSpeed: 3,
      },
      enemy(node, 'sentinel_1', 'Lair Sentinel', -18, 30, bossLevel(node) - 1, 260, { archetype: 'guard' }),
      enemy(node, 'sentinel_2', 'Lair Sentinel', 18, 30, bossLevel(node) - 1, 260, { archetype: 'guard' }),
      enemy(node, 'beast_1', lairBeastName(node), -38, -2, bossLevel(node) - 2, 190, { archetype: 'beast' }),
      enemy(node, 'beast_2', lairBeastName(node), 38, -2, bossLevel(node) - 2, 190, { archetype: 'beast' }),
      enemy(node, 'adept_1', 'Lair Cultist', -24, 58, bossLevel(node) - 1, 220, { archetype: 'caster' }),
      enemy(node, 'adept_2', 'Lair Cultist', 24, 58, bossLevel(node) - 1, 220, { archetype: 'caster' }),
    ];
  }
  if (node.nodeRole === 'fortress') {
    return [
      enemy(node, 'west_guard_1', 'Objective Guard', -72, -24, tierLevel(node), 220, { archetype: 'guard' }),
      enemy(node, 'west_caster_1', 'Siege Hexer', -82, -14, tierLevel(node), 180, { archetype: 'caster' }),
      enemy(node, 'central_guard_1', 'Objective Guard', -10, -4, tierLevel(node), 220, { archetype: 'guard' }),
      enemy(node, 'central_raider_1', 'Campaign Raider', 10, -4, tierLevel(node), 180, { archetype: 'raider' }),
      enemy(node, 'east_guard_1', 'Objective Guard', 72, -24, tierLevel(node), 220, { archetype: 'guard' }),
      enemy(node, 'east_caster_1', 'Siege Hexer', 82, -14, tierLevel(node), 180, { archetype: 'caster' }),
      enemy(node, 'aegis_keep_guard_1', 'Aegis Keep Guard', -72, 42, tierLevel(node) + 1, 260, { archetype: 'guard' }),
      enemy(node, 'aegis_keep_guard_2', 'Aegis Keep Guard', -44, 42, tierLevel(node) + 1, 260, { archetype: 'guard' }),
      enemy(node, 'riftbound_keep_guard_1', 'Riftbound Keep Guard', 44, 42, tierLevel(node) + 1, 260, { archetype: 'guard' }),
      enemy(node, 'riftbound_keep_guard_2', 'Riftbound Keep Guard', 72, 42, tierLevel(node) + 1, 260, { archetype: 'guard' }),
      enemy(node, 'beast_1', fieldBeastName(node), -102, -52, tierLevel(node), 190, { archetype: 'beast' }),
      enemy(node, 'beast_2', fieldBeastName(node), 102, -52, tierLevel(node), 190, { archetype: 'beast' }),
      enemy(node, 'captain', 'Keep Captain', 0, 72, tierLevel(node) + 2, 340, { archetype: 'captain' }),
    ];
  }
  return [
    enemy(node, 'west_raider_1', 'Campaign Raider', -46, 2, tierLevel(node), 150, { archetype: 'raider' }),
    enemy(node, 'west_guard_1', 'Objective Guard', -64, -18, tierLevel(node), 190, { archetype: 'guard' }),
    enemy(node, 'central_caster_1', 'Battlefield Hexer', -10, 14, tierLevel(node), 165, { archetype: 'caster' }),
    enemy(node, 'central_raider_1', 'Campaign Raider', 10, 14, tierLevel(node), 150, { archetype: 'raider' }),
    enemy(node, 'east_raider_1', 'Campaign Raider', 46, 2, tierLevel(node), 150, { archetype: 'raider' }),
    enemy(node, 'east_guard_1', 'Objective Guard', 64, -18, tierLevel(node), 190, { archetype: 'guard' }),
    enemy(node, 'aegis_keep_guard_1', 'Aegis Keep Guard', -66, 42, tierLevel(node) + 1, 210, { archetype: 'guard' }),
    enemy(node, 'aegis_keep_caster_1', 'Aegis Keep Sage', -38, 44, tierLevel(node) + 1, 190, { archetype: 'caster' }),
    enemy(node, 'riftbound_keep_guard_1', 'Riftbound Keep Guard', 38, 44, tierLevel(node) + 1, 210, { archetype: 'guard' }),
    enemy(node, 'riftbound_keep_caster_1', 'Riftbound Keep Magister', 66, 42, tierLevel(node) + 1, 190, { archetype: 'caster' }),
    enemy(node, 'field_captain', 'Keep Captain', 0, 78, tierLevel(node) + 2, 300, { archetype: 'captain' }),
    enemy(node, 'beast_1', fieldBeastName(node), -96, -74, tierLevel(node), 160, { archetype: 'beast' }),
    enemy(node, 'beast_2', fieldBeastName(node), 96, -74, tierLevel(node), 160, { archetype: 'beast' }),
  ];
}

function trainingDummy(node, suffix, name, x, z, level, maxHealth) {
  return {
    id: `${node.id}_${suffix}`,
    name,
    level,
    x,
    z,
    maxHealth,
    aggroRange: 0,
    assetKey: 'dummy',
  };
}

function fieldBeastName(node) {
  if (/fen|mire|bleakroot|glassriver/i.test(node.theme)) return 'Mire Hound';
  if (/forest|ironwood|gorepine|briar/i.test(node.theme)) return 'Wild Stag';
  if (/obsidian|ash|cinder|rift|scar/i.test(node.theme)) return 'Ash Hound';
  return 'War Boar';
}

function lairBeastName(node) {
  if (/nest|rot|mire|fen/i.test(node.theme)) return 'Lair Spider';
  if (/ash|cinder|obsidian|rift|night/i.test(node.theme)) return 'Rift Hound';
  return 'Barrow Wolf';
}

function enemy(node, suffix, name, x, z, level, maxHealth, extra = {}) {
  const archetype = extra.archetype ?? inferEnemyArchetype(suffix, name);
  const tuning = enemyTuning(archetype, level);
  return {
    id: `${node.id}_${suffix}`,
    name,
    level,
    x,
    z,
    maxHealth,
    archetype,
    ...tuning,
    ...extra,
  };
}

function inferEnemyArchetype(suffix, name) {
  if (/beast|hound|stag|boar|spider|wolf/i.test(`${suffix} ${name}`)) return 'beast';
  if (/caster|hexer|cultist|sage|magister|adept/i.test(`${suffix} ${name}`)) return 'caster';
  if (/captain|overlord/i.test(`${suffix} ${name}`)) return 'captain';
  if (/guard|sentinel/i.test(`${suffix} ${name}`)) return 'guard';
  return 'raider';
}

function enemyTuning(archetype, level) {
  switch (archetype) {
    case 'caster':
      return {
        aggroRange: 18,
        attackRange: 14,
        preferredRange: 12,
        attackDamage: 5 + level,
        moveSpeed: 2.55,
      };
    case 'guard':
      return {
        aggroRange: 14,
        attackRange: 3,
        preferredRange: 2.4,
        attackDamage: 9 + level * 2,
        moveSpeed: 2.75,
      };
    case 'beast':
      return {
        aggroRange: 16,
        attackRange: 2.4,
        preferredRange: 1.9,
        attackDamage: 8 + level * 2,
        moveSpeed: 3.85,
      };
    case 'captain':
      return {
        aggroRange: 18,
        attackRange: 3.2,
        preferredRange: 2.7,
        attackDamage: 12 + level * 2,
        moveSpeed: 3.05,
      };
    case 'raider':
    default:
      return {
        aggroRange: 15,
        attackRange: 2.8,
        preferredRange: 2.2,
        attackDamage: 7 + level * 2,
        moveSpeed: 3.25,
      };
  }
}

function tierLevel(node) {
  if (node.tier === 'T1') return 3;
  if (node.tier === 'T2') return 9;
  if (node.tier === 'T3') return 18;
  if (node.tier === 'T4') return 32;
  return 40;
}

function bossLevel(node) {
  if (node.levelBand.includes('Tier 1')) return 8;
  if (node.levelBand.includes('Tier 2')) return 16;
  return 28;
}

function buildNpcs(node) {
  const prefix = node.realm === 'aegis' ? 'Aegis' : 'Riftbound';
  const names = node.realm === 'aegis'
    ? ['Elira Dawnmarch', 'Corren Vale', 'Mira Stonewake', 'Alden Voss', 'Serra Brightfield', 'Tovin Greyford']
    : ['Vask Rauth', 'Nyra Vex', 'Gorvak Mirehand', 'Selk Dreadspire', 'Kara Ashvein', 'Drog Thornjaw'];
  if (isImportedAegisCapital(node)) {
    return importedAegisCapitalNpcs(node, prefix, names);
  }
  const npcs = [
    {
      id: `${node.id}_quartermaster`,
      name: names[0],
      title: `${prefix} Quartermaster`,
      role: 'vendor',
      x: -16,
      z: -34,
      rotY: 0,
    },
    {
      id: `${node.id}_marshal`,
      name: names[1],
      title: `${node.levelBand} Campaign Marshal`,
      role: 'guard',
      x: 16,
      z: -34,
      rotY: 0,
    },
  ];

  if (node.nodeRole === 'capital') {
    npcs.push(
      {
        id: `${node.id}_banker`,
        name: names[2],
        title: 'Vault Keeper',
        role: 'banker',
        x: -24,
        z: 12,
        rotY: 1.5708,
      },
      {
        id: `${node.id}_class_trainer`,
        name: names[3],
        title: `${prefix} Class Trainer`,
        role: 'trainer',
        x: 24,
        z: 12,
        rotY: -1.5708,
      },
      {
        id: `${node.id}_craft_trainer`,
        name: names[4],
        title: 'Crafting Mentor',
        role: 'trainer',
        x: 0,
        z: -24,
        rotY: 0,
      },
      {
        id: `${node.id}_portal_guard`,
        name: names[5],
        title: 'Portal Guard',
        role: 'guard',
        x: 0,
        z: -72,
        rotY: 0,
      },
    );
    if (node.id === 'aegis_capital') {
      npcs.push({
        id: 'quest-1',
        name: 'Mara Vell',
        title: 'Dawnline Dispatch Officer',
        role: 'questgiver',
        x: 0,
        z: 38,
        rotY: 3.1416,
      });
    }
    return npcs;
  }

  if (node.nodeRole === 'fortress') {
    npcs.push(
      {
        id: `${node.id}_siege_engineer`,
        name: names[2],
        title: 'Siege Engineer',
        role: 'vendor',
        x: 46,
        z: -54,
        rotY: -0.4,
      },
      {
        id: `${node.id}_field_medic`,
        name: names[3],
        title: 'Field Medic',
        role: 'ambient',
        x: -46,
        z: -54,
        rotY: 0.4,
      },
      {
        id: `${node.id}_gate_captain`,
        name: names[4],
        title: 'Gate Captain',
        role: 'guard',
        x: 0,
        z: -4,
        rotY: 3.1416,
      },
    );
    return npcs;
  }

  if (node.nodeRole === 'battlefield') {
    npcs.push(
      {
        id: `${node.id}_scout`,
        name: names[2],
        title: 'Forward Scout',
        role: 'guard',
        x: -22,
        z: -52,
        rotY: 0,
      },
      {
        id: `${node.id}_craft_mentor`,
        name: names[3],
        title: 'Field Crafting Mentor',
        role: 'trainer',
        x: 22,
        z: -52,
        rotY: 0,
      },
      {
        id: `${node.id}_forager`,
        name: names[4],
        title: 'Resource Warden',
        role: 'ambient',
        x: 0,
        z: -62,
        rotY: 0,
      },
    );
    return npcs;
  }

  npcs.push({
    id: `${node.id}_expedition_guide`,
    name: names[2],
    title: 'Expedition Guide',
    role: 'ambient',
    x: 0,
    z: -34,
    rotY: 0,
  });
  return npcs;
}

function importedAegisCapitalNpcs(node, prefix, names) {
  return [
    {
      id: `${node.id}_quartermaster`,
      name: names[0],
      title: `${prefix} Quartermaster`,
      role: 'vendor',
      x: -30,
      z: -76,
      rotY: 0.65,
    },
    {
      id: `${node.id}_marshal`,
      name: names[1],
      title: `${node.levelBand} Campaign Marshal`,
      role: 'guard',
      x: 0,
      z: -24,
      rotY: -0.45,
    },
    {
      id: `${node.id}_banker`,
      name: names[2],
      title: 'Vault Keeper',
      role: 'banker',
      x: -42,
      z: 18,
      rotY: 1.5708,
    },
    {
      id: `${node.id}_class_trainer`,
      name: names[3],
      title: `${prefix} Class Trainer`,
      role: 'trainer',
      x: 42,
      z: 18,
      rotY: -1.5708,
    },
    {
      id: `${node.id}_craft_trainer`,
      name: names[4],
      title: 'Crafting Mentor',
      role: 'trainer',
      x: -42,
      z: 58,
      rotY: 1.1,
    },
    {
      id: `${node.id}_portal_guard`,
      name: names[5],
      title: 'Portal Guard',
      role: 'guard',
      x: 0,
      z: -128,
      rotY: 0,
    },
    {
      id: 'quest-1',
      name: 'Mara Vell',
      title: 'Dawnline Dispatch Officer',
      role: 'questgiver',
      x: 10,
      z: -94,
      rotY: 2.85,
    },
    guardNpc(node, 'front_gate_west', 'Brann Hartwell', 'Main Gate Guard', -15, -148, 0.2),
    guardNpc(node, 'front_gate_east', 'Orrin Valecross', 'Main Gate Guard', 15, -148, -0.2),
    guardNpc(node, 'west_gate_south', 'Cedric Wold', 'West Gate Guard', -148, -28, 1.5708),
    guardNpc(node, 'west_gate_north', 'Hale Durn', 'West Gate Guard', -148, -4, 1.5708),
    guardNpc(node, 'east_gate_south', 'Tamsin Reed', 'East Gate Guard', 148, -28, -1.5708),
    guardNpc(node, 'east_gate_north', 'Veyra Sunholt', 'East Gate Guard', 148, -4, -1.5708),
    guardNpc(node, 'market_west', 'Garron Pike', 'Market Watch', -48, -42, 0.8),
    guardNpc(node, 'market_east', 'Lysa Bright', 'Market Watch', 48, -42, -0.8),
    guardNpc(node, 'plaza_west', 'Merek Flint', 'Plaza Watch', -22, -4, 1.2),
    guardNpc(node, 'plaza_east', 'Rowan Hale', 'Plaza Watch', 22, -4, -1.2),
    guardNpc(node, 'side_street_west', 'Iven Stonebrook', 'Street Patrol', -52, 62, 0.45),
    guardNpc(node, 'side_street_east', 'Kara Voss', 'Street Patrol', 52, 62, -0.45),
    guardNpc(node, 'rear_district_west', 'Brenna Vale', 'Rear District Guard', -32, 118, 2.7),
    guardNpc(node, 'rear_district_east', 'Tor Caldus', 'Rear District Guard', 32, 118, -2.7),
  ];
}

function guardNpc(node, suffix, name, title, x, z, rotY) {
  const id = `${node.id}_${suffix}`;
  return {
    id,
    name,
    title,
    role: 'guard',
    x,
    z,
    rotY,
    characterProfileKey: aegisCapitalGuardVariantProfile(id),
  };
}

function aegisCapitalGuardVariantProfile(seed) {
  const hash = hashNumber(seed);
  return AEGIS_CAPITAL_GUARD_VARIANT_PROFILES[hash % AEGIS_CAPITAL_GUARD_VARIANT_PROFILES.length];
}

function prop(id, kind, x, z, rotY, scale, extra = {}) {
  return {
    id,
    kind,
    x: round(x),
    z: round(z),
    rotY: roundAngle(rotY),
    scale: roundScale(scale),
    ...extra,
  };
}

function hashZone(zone) {
  const normalized = { ...zone };
  delete normalized.staticMapHash;
  return createHash('sha256').update(JSON.stringify(normalized)).digest('hex').slice(0, 16);
}

function createRng(seed) {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashNumber(value) {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function round(value) {
  return Math.round(value * 10) / 10;
}

function roundAngle(value) {
  return Math.round(value * 10000) / 10000;
}

function roundScale(value) {
  return Math.round(value * 100) / 100;
}

async function writeGeneratedData() {
  const generatedNodes = NODES.map((node) => ({
    ...node,
    staticMapHash: mapHashes[node.id],
  }));
  const generatedObjectives = Object.fromEntries(
    zones.map((zone) => [
      zone.id,
      zone.rvrObjectives.map((objective) => ({ ...objective })),
    ]),
  );
  const content = `// Generated by scripts/campaign/generate-static-campaign.mjs. Do not edit by hand.
export const CAMPAIGN_STATIC_VERSION = ${JSON.stringify(CAMPAIGN_STATIC_VERSION)} as const;

export const CAMPAIGN_REALMS = ${JSON.stringify(REALMS, null, 2)} as const;

export const CAMPAIGN_LANE_LABELS = ${JSON.stringify(LANE_LABELS, null, 2)} as const;

export const CAMPAIGN_NODES = ${JSON.stringify(generatedNodes, null, 2)} as const;

export const CAMPAIGN_EDGES = ${JSON.stringify(EDGES, null, 2)} as const;

export const CAMPAIGN_OBJECTIVES = ${JSON.stringify(generatedObjectives, null, 2)} as const;

export const CAMPAIGN_MAP_HASHES = ${JSON.stringify(mapHashes, null, 2)} as const;
`;
  await writeFile(path.join(dataDir, 'campaign.generated.ts'), content, 'utf8');
}

async function writeSupabaseSeed() {
  const staticZoneRows = zones.map((zone) => `  (${sql(zone.id)}, ${sql(zone.name)}, ${sql(zone.campaign.realm)}, ${sql(zone.campaign.tier)}, ${sql(zone.campaign.lane)}, ${sql(zone.campaign.nodeRole)}, ${sql(CAMPAIGN_STATIC_VERSION)}, ${sql(zone.staticMapHash)})`).join(',\n');
  const edgeRows = EDGES.map(([from, to]) => `  (${sql(from)}, ${sql(to)}),\n  (${sql(to)}, ${sql(from)})`).join(',\n');
  const objectiveRows = zones.flatMap((zone) => zone.rvrObjectives.map((objective) => `  (${sql(zone.id)}, ${sql(objective.id)}, ${sql(objective.type)}, ${sql(objective.label)}, ${objective.x}, ${objective.z}, ${objective.captureRadius}, ${sql(objective.defaultRealm)})`)).join(',\n');
  const content = `-- Generated by scripts/campaign/generate-static-campaign.mjs.
-- Re-run npm run campaign:generate after changing scripts/campaign/static-campaign-source.mjs.

insert into campaign_static_zones
  (zone_id, name, realm, tier, lane, node_role, static_map_version, map_hash)
values
${staticZoneRows}
on conflict (zone_id) do update set
  name = excluded.name,
  realm = excluded.realm,
  tier = excluded.tier,
  lane = excluded.lane,
  node_role = excluded.node_role,
  static_map_version = excluded.static_map_version,
  map_hash = excluded.map_hash;

insert into campaign_edges (from_zone_id, to_zone_id)
values
${edgeRows}
on conflict (from_zone_id, to_zone_id) do nothing;

insert into campaign_objectives
  (zone_id, objective_id, objective_type, label, x, z, capture_radius, default_realm)
values
${objectiveRows}
on conflict (zone_id, objective_id) do update set
  objective_type = excluded.objective_type,
  label = excluded.label,
  x = excluded.x,
  z = excluded.z,
  capture_radius = excluded.capture_radius,
  default_realm = excluded.default_realm;
`;
  await writeFile(path.join(supabaseDir, 'seed_campaign_static.sql'), content, 'utf8');
}

function sql(value) {
  if (value === null || value === undefined) return 'null';
  return `'${String(value).replaceAll("'", "''")}'`;
}
