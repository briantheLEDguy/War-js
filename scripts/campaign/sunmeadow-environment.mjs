/** Sunmeadow's authored landscape source. Gameplay identities remain stable. */
import { composeSunmeadowRoads } from './sunmeadow-road-network.mjs';
export const SUNMEADOW_RELEASE = Object.freeze({ terrain: true, architecture: true, nature: true });

const NATURE = ['oak_pasture', 'oak_hedgerow', 'ash', 'hawthorn', 'wheat', 'meadow', 'limestone'].map(kind => `frontier_sunmeadow_${kind}`);
const ARCHITECTURE = ['farmhouse', 'workshop', 'supply_post', 'gatehouse', 'curtain_wall', 'gate_leaves'].map(kind => `frontier_sunmeadow_${kind}`);
const round = n => Math.round(n * 1000) / 1000;
const prop = (id, key, x, z, extra = {}) => ({ id: `sunmeadow_march_${id}`, kind: key, assetKey: key, x: round(x), z: round(z), rotY: 0, scale: 1, colliderSpace: 'model', ...extra });
const solid = (width, depth, maxY, x = 0, z = 0) => ({ width, depth, maxY, minY: 0, x, z });
const replaceAuthoredProps = (zone, entries) => {
  const ids = new Set(entries.map(entry => entry.id));
  zone.props = zone.props.filter(entry => !ids.has(entry.id)).concat(entries);
};

function distanceToSegment(p, a, b) {
  const dx = b.x - a.x, dz = b.z - a.z, length = dx * dx + dz * dz;
  const t = length ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.z - a.z) * dz) / length)) : 0;
  return Math.hypot(p.x - a.x - dx * t, p.z - a.z - dz * t);
}

export function sunmeadowPlacementClear(zone, point, radius = 3) {
  const layout = zone.orvrLayout;
  if (layout.terrain.flattenAreas.some(area => Math.hypot(point.x - area.x, point.z - area.z) < area.radius + radius)) return false;
  if (zone.zoneTriggers.some(exit => Math.hypot(point.x - exit.x, point.z - exit.z) < exit.radius + radius + 3)) return false;
  if (layout.terrain.clearCorridors.some(road => road.points.slice(1).some((end, i) => distanceToSegment(point, road.points[i], end) < road.radius + radius))) return false;
  return Math.abs(point.x) + radius < 580 && Math.abs(point.z) + radius < 580;
}

function dressNature(zone) {
  // Replace existing low-detail ecology before adding composed groves and field margins.
  const natureKinds = /^(tree|rock|pnw_)/;
  const resourceVisuals = new Set((zone.resourceNodes ?? []).map(node => node.visualPropId));
  zone.props = zone.props.filter(p => resourceVisuals.has(p.id) || !natureKinds.test(p.kind));
  const entries = [], occupied = [];
  let seed = 72841;
  const random = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296);
  const place = (id, kind, x, z, radius, scale = 1, angle = random() * Math.PI * 2) => {
    const point = { x, z };
    if (!sunmeadowPlacementClear(zone, point, radius * scale)) return;
    if (radius >= 4 && occupied.some(other => Math.hypot(x - other.x, z - other.z) < radius * scale + other.radius)) return;
    if (radius >= 4) occupied.push({ ...point, radius: radius * scale });
    const colliders = /oak|ash/.test(kind) ? [solid(1.25, 1.25, 4)] : kind === 'limestone' ? [solid(4.9, 3.3, 2.1)] : undefined;
    entries.push(prop(id, `frontier_sunmeadow_${kind}`, x, z, { rotY: round(angle), scale: round(scale), ...(colliders ? { colliders } : {}) }));
  };
  const groves = [
    { id: 'north_wood', x: -220, z: 455, width: 550, depth: 140, count: 55 },
    { id: 'west_pasture', x: -305, z: 260, width: 230, depth: 205, count: 22 },
    { id: 'east_oaks', x: 165, z: 360, width: 300, depth: 240, count: 30 },
    { id: 'southern_ash', x: 135, z: -430, width: 530, depth: 150, count: 24 },
  ];
  for (const grove of groves) for (let i = 0; i < grove.count; i += 1) {
    const x = grove.x + (random() - .5) * grove.width, z = grove.z + (random() - .5) * grove.depth;
    place(`${grove.id}_${i}`, ['oak_pasture', 'oak_hedgerow', 'ash'][i % 3], x, z, 5.5, .88 + random() * .26);
  }
  // Narrow strips read as cultivated crops; broken hawthorn margins preserve flanking gaps.
  const fields = [
    { id: 'homefield', x: -345, z: -310, rows: 14, columns: 22 },
    { id: 'northfield', x: -145, z: 345, rows: 12, columns: 20 },
    { id: 'eastfield', x: 325, z: 180, rows: 12, columns: 20 },
  ];
  for (const field of fields) {
    for (let row = 0; row < field.rows; row += 1) for (let column = 0; column < field.columns; column += 1) {
      const x = field.x + (column - field.columns / 2) * 2.1, z = field.z + (row - field.rows / 2) * 2.1;
      place(`${field.id}_crop_${row}_${column}`, 'wheat', x, z, 1, .94 + random() * .12, (row % 2) * Math.PI);
    }
    for (let i = 0; i < field.columns; i += 1) {
      if (i % 8 === 4) continue;
      place(`${field.id}_hedge_${i}`, 'hawthorn', field.x + (i - field.columns / 2) * 4.5, field.z + field.rows * 1.05 + 5, 2.6, 1, 0);
    }
  }
  for (let i = 0; i < 600; i += 1) {
    const x = (random() - .5) * 1100, z = (random() - .5) * 1100;
    place(`meadow_scatter_${i}`, 'meadow', x, z, 1.4, .9 + random() * .3);
  }
  for (let i = 0; i < 32; i += 1) {
    const x = 470 + (random() - .5) * 80, z = -420 + random() * 330;
    place(`limestone_exposure_${i}`, 'limestone', x, z, 4, .7 + random() * .45);
  }
  replaceAuthoredProps(zone, entries);
  zone.orvrLayout.biome.vegetationAssetKeys = NATURE;
  zone.orvrLayout.assetPolicy.optionalAssetKeys = [...new Set([...zone.orvrLayout.assetPolicy.optionalAssetKeys, ...NATURE])];
}

function dressArchitecture(zone) {
  const entries = [];
  const previousGates = new Map(zone.props.filter(p => p.interaction?.type === 'gate').map(p => [p.id, p]));
  zone.props = zone.props.filter(p => !/_keep_keep_/.test(p.id ?? ''));
  for (const keep of zone.orvrLayout.keeps) {
    const prefix = `${keep.realm}_keep`;
    const wall = (id, x, z, rotY = 0) => entries.push(prop(`${prefix}_${id}`, 'frontier_sunmeadow_curtain_wall', keep.x + x, z, { rotY, colliders: [solid(8, 2.2, 8.3)] }));
    for (const x of [-26, -18, 18, 26]) wall(`front_wall_${x}`, x, -24);
    for (let i = 0; i < 7; i += 1) for (const x of [-31, 31]) wall(`side_wall_${x}_${i}`, x, -20 + i * 8, Math.PI / 2);
    for (let i = 0; i < 8; i += 1) wall(`rear_wall_${i}`, -28 + i * 8, 32);
    for (let i = 0; i < 4; i += 1) for (const x of [-15, 15]) wall(`inner_side_${x}_${i}`, x, -3.5 + i * 8, Math.PI / 2);
    for (let i = 0; i < 4; i += 1) wall(`inner_rear_${i}`, -12 + i * 8, 24.5);
    for (const gate of keep.gates) {
      // Wing sockets lie 4.6m along local +Z, which faces toward world -Z after the authored half turn.
      const centerZ = gate.stage === 'outer' ? -19.4 : -2.9;
      entries.push(prop(`${prefix}_${gate.stage}_gatehouse`, 'frontier_sunmeadow_gatehouse', keep.x, centerZ, {
        rotY: Math.PI, colliders: [solid(11, 12, 12, -8.5), solid(11, 12, 12, 8.5)],
      }));
      gate.z = centerZ - 6; gate.height = 4.8; gate.depth = .45; gate.assetKey = 'frontier_sunmeadow_gate_leaves';
      const previous = previousGates.get(gate.propId);
      const interaction = { ...previous?.interaction, id: previous?.interaction?.id ?? `${gate.propId}_interaction`, type: 'gate', label: `${keep.realm === 'aegis' ? 'Aegis' : 'Riftbound'} ${gate.stage} gate`, maxDistance: 12, startsOpen: false, openClip: 'gate_open', closeClip: 'gate_close' };
      entries.push({ ...prop(`${prefix}_${gate.stage}_leaves`, gate.assetKey, gate.x, gate.z), id: gate.propId, rotY: Math.PI, interaction,
        colliders: [{ ...solid(6, .45, 4.8), blocksWhen: 'closed', interactionId: interaction.id }],
      });
    }
    entries.push(prop(`${prefix}_quartermaster_shelter`, 'frontier_sunmeadow_supply_post', keep.x - 13, -64, { rotY: 0 }));
    const outsidePostern = prop(`${prefix}_postern_outside`, 'frontier_sunmeadow_gate_leaves', keep.x + 24, 33.15, { scale: .5 });
    const insidePostern = prop(`${prefix}_postern_inside`, 'frontier_sunmeadow_gate_leaves', keep.x + 24, 30.85, { scale: .5, rotY: Math.PI });
    entries.push(outsidePostern, insidePostern);
    keep.postern = { propId: outsidePostern.id, outside: { x: keep.x + 24, y: 0, z: 35 }, inside: { x: keep.x + 24, y: 0, z: 28 }, interactionRadius: 3 };
    for (const slot of keep.siegeSlots.filter(slot => slot.kind === 'oil')) slot.operatorPosition = { x: keep.x + 8, y: 0, z: -11.9 };
    // Reviewed winch bounds are 4.4 x 3.04 x 3.3m; half scale fits the 4.5m courtyard gap.
    entries.push(prop(`${prefix}_oil_console`, 'riftspire_chain_winch', keep.x + 10, -11.9, { scale: .5, colliders: [solid(4.4, 3.3, 3.04)] }));
    const standard = keep.realm === 'aegis' ? 'aegis_citadel_tapestry' : 'riftspire_war_standard';
    entries.push(prop(`${prefix}_realm_standard`, standard, keep.x + 9, -25.6, { y: 3.8, scale: .7, rotY: Math.PI }));
  }
  const details = {
    life_signpost: 'aegis_civic_waymarker', life_lantern: 'aegis_civic_streetlight', life_planter: 'aegis_planter',
    life_bench: 'aegis_civic_bench', life_barrels: 'aegis_barrel_cluster', life_crate_stack: 'aegis_crate_stack',
    life_handcart: 'aegis_handcart', life_clothesline: 'aegis_washing_line', life_campfire: 'aegis_citadel_hearth',
    life_supply_tent: 'frontier_sunmeadow_supply_post', vendor_stall: 'frontier_sunmeadow_supply_post',
    gate: 'aegis_civic_waymarker', banner_post: 'aegis_civic_waymarker', bridge: 'aegis_bridge_narrow',
  };
  zone.props = zone.props.map(entry => {
    const key = details[entry.kind];
    if (!key) return entry;
    const { model, lodModels, scaleX, scaleY, scaleZ, ...rest } = entry;
    return { ...rest, kind: key, assetKey: key, scale: entry.kind === 'life_campfire' ? .42 : 1, colliderSpace: 'model' };
  });
  for (const objective of zone.orvrLayout.battlefieldObjectives) {
    const marker = zone.props.find(entry => entry.id === `${objective.objectiveId}_banner`);
    if (marker) Object.assign(marker, { x: objective.x + 12, z: objective.z + 10, scale: 1, colliders: [solid(.76, .76, 3.625)], colliderSpace: 'model' });
  }
  for (const trigger of zone.zoneTriggers) {
    const marker = zone.props.find(entry => entry.id === `${zone.id}_portal_${trigger.targetZoneId}`);
    const path = zone.paths.find(path => path.points.at(-1)?.x === trigger.x && path.points.at(-1)?.z === trigger.z);
    if (!marker || !path) continue;
    const previous = path.points.at(-2), dx = trigger.x - previous.x, dz = trigger.z - previous.z, length = Math.hypot(dx, dz);
    const offset = path.width / 2 + 2;
    let nx = -dz / length, nz = dx / length;
    // Keep the signpost on the inward verge while the travel trigger stays centered on the road.
    if (trigger.x * nx + trigger.z * nz > 0) { nx = -nx; nz = -nz; }
    Object.assign(marker, { x: round(trigger.x + nx * offset), z: round(trigger.z + nz * offset), rotY: round(Math.atan2(-nx, -nz)),
      scale: 1, colliders: [solid(.76, .76, 3.625)], colliderSpace: 'model' });
  }
  const farmTrackCart = zone.props.find(entry => entry.id === `${zone.id}_life_roadside_caravan_4`);
  if (farmTrackCart) { farmTrackCart.x = -352; farmTrackCart.z = -185; }
  // The reviewed shelter is wider than the retired tent. Keep its walls and
  // roof clear of the surrounding delivery furniture at their actual scale.
  for (const [suffix, x, z] of [
    ['outfitter_2', -423, -281], ['outfitter_3', -406, -282],
    ['outfitter_5', -406, -269], ['outfitter_6', -415, -269],
    ['roadside_caravan_2', -346, -193],
  ]) {
    const furniture = zone.props.find(entry => entry.id === `${zone.id}_life_${suffix}`);
    if (furniture) { furniture.x = x; furniture.z = z; }
  }
  const buildings = [
    ['west_farmhouse', 'farmhouse', -473, -266, Math.PI / 2],
    ['north_farmhouse', 'farmhouse', -459, -211, Math.PI],
    ['east_farmhouse', 'farmhouse', -391, -273, -Math.PI / 2],
    ['croft_farmhouse', 'farmhouse', -485, -295, 0],
    ['craft_workshop', 'workshop', -397, -244, -Math.PI / 2],
  ];
  for (const [id,kind,x,z,rotY] of buildings) {
    const width = kind === 'workshop' ? 10 : 8, depth = kind === 'workshop' ? 8 : 10, door = kind === 'workshop' ? 2.6 : 1.6;
    entries.push(prop(id, `frontier_sunmeadow_${kind}`, x, z, { rotY,
      colliders: [solid(.5,depth,7,-width/2),solid(.5,depth,7,width/2),solid(width,.5,7,0,-depth/2),solid((width-door)/2,.5,7,-(width+door)/4,depth/2),solid((width-door)/2,.5,7,(width+door)/4,depth/2)],
    }));
  }
  replaceAuthoredProps(zone, entries);
  const apothecary = zone.craftingStations?.find(station => station.id === `${zone.id}_apothecary_station`);
  const apothecaryShelter = zone.props.find(entry => entry.id === `${zone.id}_apothecary_station_visual`);
  if (apothecary && apothecaryShelter) {
    Object.assign(apothecary, { x: -448, z: -266 });
    Object.assign(apothecaryShelter, { x: -448, z: -266, rotY: 0 });
  }
  for (const entry of zone.props.filter(entry => entry.assetKey === 'frontier_sunmeadow_supply_post')) {
    entry.colliderSpace = 'model';
    entry.colliders = [
      { id: `${entry.id}_left_wall`, ...solid(.5, 5, 1.5, -4) },
      { id: `${entry.id}_right_wall`, ...solid(.5, 5, 1.5, 4) },
      { id: `${entry.id}_rear_wall`, ...solid(8, .5, 1.5, 0, -2.5) },
    ];
  }
  zone.orvrLayout.assetPolicy.requiredAssetKeys = [...new Set([
    ...zone.orvrLayout.assetPolicy.requiredAssetKeys.filter(key => key !== 'frontier_keep_gate'), ...ARCHITECTURE,
  ])];
}

export function composeSunmeadowEnvironment(zone, release = SUNMEADOW_RELEASE) {
  if (zone.id !== 'sunmeadow_march' || !zone.orvrLayout) return zone;
  composeSunmeadowRoads(zone);
  const terrain = zone.orvrLayout.terrain;
  terrain.sourceVersion = 'sunmeadow-pastures-v1';
  // Broad shoulders carry roads through pasture rises without vertical grass cuts.
  terrain.clearCorridors.forEach(corridor => { corridor.feather = 28; });
  terrain.landforms = [
    { id: 'north_woodland_spine', kind: 'ridge', x: -210, z: 470, radiusX: 310, radiusZ: 100, height: 22 },
    { id: 'eastern_limestone_ridge', kind: 'ridge', x: 485, z: -260, radiusX: 70, radiusZ: 260, height: 32 },
    { id: 'southern_lime_bluff', kind: 'ridge', x: 120, z: -500, radiusX: 230, radiusZ: 90, height: 26 },
    { id: 'western_pasture_roll', kind: 'terrace', x: -300, z: 260, radiusX: 175, radiusZ: 150, height: 12 },
    { id: 'oak_scout_rise', kind: 'terrace', x: 180, z: 180, radiusX: 110, radiusZ: 200, height: 16 },
    { id: 'southern_stream_basin', kind: 'basin', x: 55, z: -360, radiusX: 280, radiusZ: 55, height: -4 },
  ];
  for (const chunk of terrain.chunks) {
    chunk.status = release.terrain ? 'approved' : 'planned';
    chunk.lodDistances = [0, 390, 630];
  }
  if (release.nature) dressNature(zone);
  if (release.architecture) dressArchitecture(zone);
  return zone;
}
