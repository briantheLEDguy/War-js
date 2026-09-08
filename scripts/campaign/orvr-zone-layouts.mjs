import { FRONTIER_SIEGE_ASSET_KEYS, ORVR_ART_DIRECTIONS, WORLD_ART_DIRECTIONS } from './orvr-art-direction.mjs';
import { WORLD_LIFE_FOOTPRINTS } from './world-life-source.mjs';
import { composeOrvrRoads } from './orvr-road-network.mjs';

export const ORVR_LAYOUT_VERSION = 'expanded-orvr-v1';
export const ORVR_ZONE_SIZE = 1200;
const REALMS = ['aegis', 'riftbound'];
const BO_SUFFIXES = ['west_objective', 'central_objective', 'east_objective'];
const BO_POINTS = [{ x: 0, z: -260 }, { x: 0, z: 0 }, { x: 0, z: 260 }];
const round = (value) => Math.round(value * 100) / 100;
const point = (x, z) => ({ x: round(x), z: round(z) });

export function routeLength(points) {
  return round(points.slice(1).reduce((distance, entry, index) => distance + Math.hypot(entry.x - points[index].x, entry.z - points[index].z), 0));
}

function createKeep(zoneId, realm) {
  const x = realm === 'aegis' ? -350 : 350;
  const objectiveId = `${zoneId}_${realm}_keep`;
  return {
    objectiveId, realm, x, z: 0,
    quartermaster: point(x - 13, -60), deliveryPoint: point(x, -78),
    commander: { entityId: `${zoneId}_${realm}_keep_commander`, ...point(x, 4) },
    gates: [
      { id: `${objectiveId}_outer_gate`, stage: 'outer', propId: `${objectiveId}_keep_front_gate`, ...point(x, -24), width: 6, depth: 0.5, height: 6, assetKey: FRONTIER_SIEGE_ASSET_KEYS.gate },
      { id: `${objectiveId}_inner_gate`, stage: 'inner', propId: `${objectiveId}_keep_inner_front_door`, ...point(x, -7.5), width: 6, depth: 0.5, height: 6, assetKey: FRONTIER_SIEGE_ASSET_KEYS.gate },
    ],
    siegeSlots: [
      { id: `${objectiveId}_oil_1`, kind: 'oil', ...point(x, -22), y: 7.5, assetKey: FRONTIER_SIEGE_ASSET_KEYS.oil },
      { id: `${objectiveId}_catapult_1`, kind: 'catapult', ...point(x - 25, 25), y: 0, assetKey: FRONTIER_SIEGE_ASSET_KEYS.catapult },
      { id: `${objectiveId}_catapult_2`, kind: 'catapult', ...point(x + 25, 25), y: 0, assetKey: FRONTIER_SIEGE_ASSET_KEYS.catapult },
    ],
    ramSpawn: { ...point(x + 16, -60), assetKey: FRONTIER_SIEGE_ASSET_KEYS.ram },
    collisionSlots: [
      { id: `${objectiveId}_outer_enclosure`, ...point(x, 0), width: 64, depth: 64, height: 9 },
      { id: `${objectiveId}_inner_enclosure`, ...point(x, 4), width: 36, depth: 30, height: 10 },
    ],
  };
}

function createCaravanRoutes(zoneId, keeps) {
  return BO_POINTS.flatMap((position, index) => keeps.map((keep) => {
    const sign = keep.realm === 'aegis' ? -1 : 1;
    const waypoints = index === 0 ? [[100, -245], [220, -170]]
      : index === 1 ? [[100, -110], [240, -140]] : [[100, 205], [220, 80], [260, -90]];
    const points = [{ ...position }, ...waypoints.map(([x, z]) => point(x * sign, z)), { ...keep.deliveryPoint }];
    return {
      id: `${zoneId}_${BO_SUFFIXES[index]}_supply_${keep.realm}`,
      objectiveId: `${zoneId}_${BO_SUFFIXES[index]}`,
      realm: keep.realm, destinationKeepId: keep.objectiveId,
      points, width: 12, clearanceRadius: 9, lengthMetres: routeLength(points),
      assetKey: FRONTIER_SIEGE_ASSET_KEYS.caravan,
    };
  }));
}

function createTerrain(zoneId, art, keeps, stagingCamps, caravanRoutes) {
  const height = art.reliefMetres;
  return {
    sourceVersion: 'authored-landform-controls-v1', chunkSize: 300,
    chunks: Array.from({ length: 16 }, (_, index) => {
      const column = index % 4;
      const row = Math.floor(index / 4);
      return {
        id: `${zoneId}_terrain_${column}_${row}`, x: -450 + column * 300, z: -450 + row * 300,
        width: 300, depth: 300,
        assetKey: `frontier_${zoneId}_terrain_${column}_${row}`,
        collisionAssetKey: `frontier_${zoneId}_collision_${column}_${row}`,
        lodDistances: [0, 180, 420], status: 'planned',
      };
    }),
    // These are authored control surfaces for the Blender source, not visible primitives.
    landforms: [
      { id: 'north_watershed', kind: 'ridge', ...point(-180, 490), radiusX: 240, radiusZ: 90, height },
      { id: 'south_watershed', kind: 'ridge', ...point(200, -475), radiusX: 200, radiusZ: 100, height: round(height * 0.7) },
      { id: 'west_horizon', kind: 'ridge', ...point(-545, -180), radiusX: 60, radiusZ: 190, height: round(height * 0.8) },
      { id: 'east_horizon', kind: 'ridge', ...point(545, 200), radiusX: 60, radiusZ: 190, height: round(height * 0.9) },
      { id: 'stream_basin', kind: 'basin', ...point(70, -360), radiusX: 270, radiusZ: 45, height: -3 },
      { id: 'north_scout_rise', kind: 'terrace', ...point(160, 320), radiusX: 90, radiusZ: 70, height: round(height * 0.25) },
      { id: 'south_scout_rise', kind: 'terrace', ...point(-160, -320), radiusX: 90, radiusZ: 60, height: round(height * 0.2) },
    ],
    flattenAreas: [
      ...keeps.map((keep) => ({ id: keep.objectiveId, x: keep.x, z: keep.z, radius: 85, height: 0, feather: 20 })),
      ...stagingCamps.map((camp) => ({ id: camp.id, x: camp.x, z: camp.z, radius: 40, height: 0, feather: 16 })),
      ...BO_POINTS.map((position, index) => ({ id: `${zoneId}_${BO_SUFFIXES[index]}`, ...position, radius: 34, height: 0, feather: 14 })),
      { id: `${zoneId}_settlement`, x: art.realm === 'riftbound' ? 435 : -435, z: -245, radius: 70, height: 0, feather: 20 },
    ],
    clearCorridors: caravanRoutes.map((route) => ({ id: route.id, points: structuredClone(route.points), radius: route.clearanceRadius, height: 0, feather: 5 })),
  };
}

function buildLayout(zoneId, art) {
  const keeps = REALMS.map((realm) => createKeep(zoneId, realm));
  const stagingCamps = REALMS.map((realm) => ({
    id: `${zoneId}_${realm}_staging`, realm, x: realm === 'aegis' ? -505 : 505, y: 0, z: 80,
    radius: 30, capturable: false, respawnSeconds: 15,
  }));
  const caravanRoutes = createCaravanRoutes(zoneId, keeps);
  const terrain = createTerrain(zoneId, art, keeps, stagingCamps, caravanRoutes);
  return {
    version: ORVR_LAYOUT_VERSION, size: ORVR_ZONE_SIZE, status: 'layout-ready-art-pending',
    assetPolicy: {
      mode: 'legacy-transition', allowNewPrimitiveModels: false,
      requiredAssetKeys: [...Object.values(FRONTIER_SIEGE_ASSET_KEYS), ...terrain.chunks.flatMap((chunk) => [chunk.assetKey, chunk.collisionAssetKey]), art.architectureAssetKey],
      optionalAssetKeys: [...art.vegetationAssetKeys, ...art.creatureProfileKeys],
    },
    battlefieldObjectives: BO_POINTS.map((position, index) => ({ objectiveId: `${zoneId}_${BO_SUFFIXES[index]}`, ...position, initialRealm: 'neutral', captureRadius: 18 })),
    stagingCamps, keeps, caravanRoutes, terrain,
    biome: { id: art.biomeId, season: art.season, palette: art.palette, vegetationAssetKeys: art.vegetationAssetKeys, creatureProfileKeys: art.creatureProfileKeys },
    populationAssignments: [],
  };
}

export const ORVR_ZONE_LAYOUTS = Object.freeze(Object.fromEntries(Object.entries(ORVR_ART_DIRECTIONS).map(([id, art]) => [id, buildLayout(id, art)])));

/** Recompose generated outdoor content without changing persistent gameplay IDs. */
export function applyOrvrZoneLayout(zone, node) {
  const art = WORLD_ART_DIRECTIONS[node.id];
  if (art) zone.artDirection = structuredClone(art);
  const definition = ORVR_ZONE_LAYOUTS[node.id];
  if (!definition) return zone;
  if (zone.orvrLayout?.version === ORVR_LAYOUT_VERSION) {
    composeOrvrRoads(zone);
    if (zone.id !== 'sunmeadow_march') zone.orvrLayout.biome.placements = terrainScatterPlacements(node.id, zone.orvrLayout, zone);
    return zone;
  }
  const layout = structuredClone(definition);
  const oldSize = zone.size;
  const scale = ORVR_ZONE_SIZE / oldSize;
  const oldObjectives = structuredClone(zone.rvrObjectives ?? []);
  if (oldObjectives.filter((entry) => entry.type === 'battle_objective').length !== 3 || oldObjectives.filter((entry) => entry.type === 'keep').length !== 2) {
    throw new Error(`ORvR zone ${node.id} requires exactly three battlefield objectives and two keeps`);
  }
  const oldTriggers = structuredClone(zone.zoneTriggers ?? []);
  const realm = node.realm;
  const settlement = { x: realm === 'aegis' ? -435 : 435, z: -245 };
  const offsetCamp = (entry) => ({ ...entry, x: round(settlement.x + entry.x), z: round(settlement.z + entry.z + 40) });
  const spread = (entry) => ({ ...entry, x: round(entry.x * scale), z: round(entry.z * scale) });

  zone.size = ORVR_ZONE_SIZE;
  zone.segments = 192;
  zone.orvrLayout = layout;
  zone.spawnPoint = { x: settlement.x, y: 0, z: settlement.z - 40 };
  for (const objective of zone.rvrObjectives ?? []) {
    const target = layout.battlefieldObjectives.find((entry) => entry.objectiveId === objective.id)
      ?? layout.keeps.find((entry) => entry.objectiveId === objective.id);
    if (!target) throw new Error(`Unmapped ORvR objective ${objective.id}`);
    objective.x = target.x;
    objective.z = target.z;
    objective.captureRadius = objective.type === 'keep' ? 18 : target.captureRadius;
  }
  for (const trigger of zone.zoneTriggers ?? []) {
    const angle = Math.atan2(trigger.z, trigger.x);
    Object.assign(trigger, point(Math.cos(angle) * 540, Math.sin(angle) * 540));
    trigger.radius = 12;
  }

  const newObjectiveById = new Map((zone.rvrObjectives ?? []).map((entry) => [entry.id, entry]));
  const moved = (entry, old, next) => ({ ...entry, x: round(next.x + entry.x - old.x), z: round(next.z + entry.z - old.z) });
  const oldKeepByRealm = Object.fromEntries(REALMS.map((team) => [team, oldObjectives.find((entry) => entry.id === `${node.id}_${team}_keep`)]));
  const mapProps = new Map();

  zone.resourceNodes = (zone.resourceNodes ?? []).map((entry) => {
    const next = moveOffCorridors(spread(entry), layout, 5);
    if (entry.visualPropId) mapProps.set(entry.visualPropId, next);
    return next;
  });
  zone.craftingStations = (zone.craftingStations ?? []).map((entry) => {
    const next = offsetCamp(entry);
    mapProps.set(entry.id, next);
    return next;
  });
  zone.props = (zone.props ?? []).map((entry) => {
    const objective = oldObjectives.find((old) => entry.id?.startsWith(`${old.id}_`));
    if (objective) return moved(entry, objective, newObjectiveById.get(objective.id));
    const portal = oldTriggers.find((old) => entry.id === `${node.id}_portal_${old.targetZoneId}`);
    if (portal) return moved(entry, portal, zone.zoneTriggers.find((next) => next.id === portal.id));
    const resource = mapProps.get(entry.id);
    if (resource) return { ...entry, x: resource.x, z: resource.z };
    const station = (zone.craftingStations ?? []).find((candidate) => entry.id?.startsWith(`${candidate.id}_`));
    if (station) return offsetCamp(entry);
    if (entry.id?.startsWith(`${node.id}_life_`) || (Math.abs(entry.x) < 45 && entry.z < 2 && entry.z > -100)) return offsetCamp(entry);
    return moveOffCorridors(spread(entry), layout, 5);
  });
  zone.npcs = (zone.npcs ?? []).map(offsetCamp);
  zone.enemies = (zone.enemies ?? []).map((entry) => {
    const suffix = entry.id.slice(node.id.length + 1);
    const keepRealm = REALMS.find((team) => suffix.startsWith(`${team}_keep_`));
    if (keepRealm && oldKeepByRealm[keepRealm]) return moved(entry, oldKeepByRealm[keepRealm], layout.keeps.find((keep) => keep.realm === keepRealm));
    const boIndex = ['west_', 'central_', 'east_'].findIndex((prefix) => suffix.startsWith(prefix));
    if (boIndex >= 0) {
      const old = oldObjectives.find((objective) => objective.id === `${node.id}_${BO_SUFFIXES[boIndex]}`);
      if (old) return moved(entry, old, BO_POINTS[boIndex]);
    }
    if (entry.archetype === 'beast') return { ...entry, x: entry.x < 0 ? -210 : 220, z: 365 };
    return { ...entry, x: round(entry.x * 2), z: 335 };
  });
  if (zone.ambientLife) {
    zone.ambientLife.actors = zone.ambientLife.actors.map((actor) => ({
      ...offsetCamp(actor), route: actor.route?.map(offsetCamp),
    }));
    zone.ambientLife.emitters = zone.ambientLife.emitters.map(offsetCamp);
  }

  const roadStyle = node.nodeRole === 'fortress' ? 'cobblestone_avenue' : 'dirt_trail';
  zone.paths = [
    ...layout.caravanRoutes.map((route) => ({ id: route.id, style: roadStyle, width: route.width, points: structuredClone(route.points) })),
    ...layout.keeps.map((keep) => ({ id: `${keep.objectiveId}_approach`, style: roadStyle, width: 12, points: [{ ...keep.deliveryPoint }, point(keep.x, 0)] })),
    ...layout.stagingCamps.map((camp, index) => ({ id: `${camp.id}_road`, style: roadStyle, width: 10, points: [point(camp.x, camp.z), point(camp.x, -78), { ...layout.keeps[index].deliveryPoint }] })),
    { id: `${node.id}_settlement_road`, style: roadStyle, width: 10, points: [{ ...settlement }, point(settlement.x, -140), point(realm === 'aegis' ? -240 : 240, -140)] },
    ...(zone.zoneTriggers ?? []).map((trigger, index) => ({ id: `${node.id}_portal_road_${index + 1}`, style: roadStyle, width: 10, points: portalRoadPoints(trigger) })),
  ];
  layout.terrain.clearCorridors = zone.paths.map((path) => ({ id: path.id, points: structuredClone(path.points), radius: path.width / 2 + 3, height: 0, feather: 5 }));
  composeOrvrRoads(zone);
  // Planned palettes remain explicit. No unreviewed prop key gets instantiated.
  layout.biome.placements = terrainScatterPlacements(node.id, layout, zone);
  zone.biomeKits = [];
  layout.populationAssignments = populationAssignments(zone, realm, art);
  return zone;
}

/** Run after every map is built, including capitals and optional boss branches. */
export function linkOrvrZoneTravel(zones) {
  const byId = new Map(zones.map((zone) => [zone.id, zone]));
  for (const source of zones) for (const trigger of source.zoneTriggers ?? []) {
    const target = byId.get(trigger.targetZoneId);
    if (!target?.orvrLayout) continue;
    const reverse = target.zoneTriggers?.find((candidate) => candidate.targetZoneId === source.id);
    if (!reverse) throw new Error(`Missing return portal: ${target.id} -> ${source.id}`);
    const magnitude = Math.hypot(reverse.x, reverse.z);
    const spawnRadius = magnitude - reverse.radius - 10;
    trigger.targetSpawn = { x: round(reverse.x * spawnRadius / magnitude), y: 0, z: round(reverse.z * spawnRadius / magnitude) };
  }
  return zones;
}

function distanceToSegment(position, start, end) {
  const dx = end.x - start.x;
  const dz = end.z - start.z;
  const lengthSquared = dx * dx + dz * dz;
  const t = lengthSquared ? Math.min(1, Math.max(0, ((position.x - start.x) * dx + (position.z - start.z) * dz) / lengthSquared)) : 0;
  return Math.hypot(position.x - start.x - t * dx, position.z - start.z - t * dz);
}

function portalRoadPoints(trigger) {
  if (Math.abs(trigger.x) > 480 && Math.abs(trigger.z) < 220) {
    const sign = trigger.x < 0 ? -1 : 1;
    return [point(0, 0), point(sign * 240, -140), point(sign * 450, -160), point(trigger.x, trigger.z)];
  }
  return [point(0, 0), point(trigger.x * 0.78, trigger.z * 0.78), point(trigger.x, trigger.z)];
}

function moveOffCorridors(entry, layout, footprint) {
  for (let step = 0; step < 16; step += 1) {
    const candidate = { ...entry, x: round(Math.max(-570, Math.min(570, entry.x + (entry.x < 0 ? -1 : 1) * step * 9))), z: round(Math.max(-570, Math.min(570, entry.z))) };
    const blocked = layout.caravanRoutes.some((route) => route.points.slice(1).some((end, index) => distanceToSegment(candidate, route.points[index], end) < route.clearanceRadius + footprint))
      || layout.keeps.some((keep) => Math.hypot(candidate.x - keep.x, candidate.z - keep.z) < 75)
      || layout.stagingCamps.some((camp) => Math.hypot(candidate.x - camp.x, candidate.z - camp.z) < camp.radius + footprint)
      || layout.battlefieldObjectives.some((objective) => Math.hypot(candidate.x - objective.x, candidate.z - objective.z) < 30 + footprint);
    if (!blocked) return candidate;
  }
  return { ...entry, x: entry.x < 0 ? -555 : 555, z: round(Math.max(-480, Math.min(480, entry.z))) };
}

function terrainScatterPlacements(zoneId, layout, zone) {
  const lifeClearings = zone.props.filter((prop) => prop.id?.startsWith(`${zoneId}_life_`)).map((prop) => ({
    x: prop.x, z: prop.z, radius: (WORLD_LIFE_FOOTPRINTS[prop.kind] ?? 3) + 3,
  }));
  const lifeCorridors = (zone.ambientLife?.actors ?? []).filter((actor) => actor.kind !== 'bird').map((actor) => ({
    id: `${actor.id}_ground_route`, points: [point(actor.x, actor.z), ...(actor.route ?? []).map((position) => point(position.x, position.z)), point(actor.x, actor.z)],
    radius: actor.kind === 'deer' ? 4 : 3, height: 0, feather: 0,
  }));
  return layout.terrain.chunks.map((chunk, index) => ({
    id: `${zoneId}_climate_patch_${index + 1}`, biomeId: layout.biome.id,
    activeSeason: layout.biome.season, x: chunk.x, z: chunk.z, width: 285, depth: 285,
    count: 90, seed: index + 104729, shape: 'rectangle', status: 'planned',
    approvedAssetKeys: [], desiredAssetKeys: [...layout.biome.vegetationAssetKeys],
    exclude: [
      ...layout.keeps.map((keep) => ({ x: keep.x, z: keep.z, radius: 85 })),
      ...layout.stagingCamps.map((camp) => ({ x: camp.x, z: camp.z, radius: 40 })),
      ...layout.battlefieldObjectives.map((objective) => ({ x: objective.x, z: objective.z, radius: 34 })),
      ...layout.terrain.flattenAreas.filter((area) => area.id.endsWith('_settlement')).map((area) => ({ x: area.x, z: area.z, radius: area.radius })),
      ...lifeClearings,
    ],
    excludeCorridors: structuredClone([...layout.terrain.clearCorridors, ...lifeCorridors]),
  }));
}

function populationAssignments(zone, realm, art) {
  const races = art.races;
  return [
    ...(zone.npcs ?? []).map((npc, index) => ({ entityId: npc.id, race: races[index % races.length], role: npc.role, desiredProfileKey: `frontier_${art.biomeId}_${races[index % races.length]}_${npc.role}`, status: 'planned' })),
    ...(zone.enemies ?? []).map((enemy) => {
      const realmRole = REALMS.find((team) => enemy.id.startsWith(`${zone.id}_${team}_keep_`));
      const beast = enemy.archetype === 'beast';
      const race = beast ? 'wildlife' : realmRole === 'aegis' ? 'empire' : realmRole === 'riftbound' ? 'chaos' : races[0];
      return { entityId: enemy.id, race, role: enemy.archetype, desiredProfileKey: beast ? art.creatureProfileKeys[1] : `frontier_${art.biomeId}_${race}_${enemy.archetype}`, status: 'planned' };
    }),
  ];
}
