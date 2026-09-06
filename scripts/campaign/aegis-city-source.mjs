import { addAegisPeople } from './aegis-people.mjs';
import { buildAegisMountainside } from './aegis-mountainside.mjs';
import { addBattleCitadel } from './aegis-battle-citadel.mjs';
import { addAegisCivicDecorations } from './aegis-civic-decorations.mjs';
import { addAegisMountainRedoubt } from './aegis-mountain-redoubt.mjs';
import { furnishAegisCitadel } from './aegis-citadel-interiors.mjs';
import { addAegisCityInfill } from './aegis-city-infill.mjs';
import { replaceAegisPrimitiveScenery } from './aegis-reviewed-scenery.mjs';
// Original Aegis city: all geometry, circulation and destinations share one plan.
export const AEGIS_CITY_VERSION = 'gothic-canals-v1';
const P = (x, z) => ({ x, z });
const path = (name, width, coords) => ({ id: `aegis_city_${name}`, style: 'brick_walkway', autoConnect: false, width, points: coords.map(([x, z]) => P(x, z)) });
export const CITY_PATHS = [
  path('gateward', 9, [[0, -158], [0, -116], [-10, -90], [0, -65], [0, -10], [0, 28], [0, 48], [-48, 58], [-52, 77], [7, 86], [12, 101], [-12, 111], [0, 119]]),
  path('citadel_ascent', 18, [[0, 119], [0, 136], [0, 152], [0, 174], [0, 202]]),
  path('citadel_west_flank', 12, [[-51, 120], [-62, 130], [-62, 150], [-62, 164], [-42, 164], [0, 164]]),
  path('citadel_east_flank', 12, [[59, 113], [62, 130], [62, 150], [62, 164], [42, 164], [0, 164]]),
  path('west_approach', 8, [[-158, 0], [-117, 0], [-96, -14], [-65, -14], [-38, -6], [0, -10]]),
  path('east_approach', 8, [[0, -10], [32, -16], [54, -8], [60, 0], [70, 0], [95, 0], [119, -9], [136, 0], [158, 0]]),
  path('market_loop', 5, [[0, -116], [-34, -119], [-55, -101], [-48, -73], [0, -65], [34, -79], [44, -113], [0, -116]]),
  path('cinderbank', 5, [[-48, -73], [-84, -79], [-116, -62], [-113, -31], [-96, -14]]),
  path('west_quay', 5, [[-137, 14], [-117, 14], [-111, 2], [-100, 2], [-91, 2], [-65, 2], [-42, 2], [-26, 2], [-26, 17], [0, 17]]),
  path('west_bridge', 6, [[-117, 0], [-117, 24], [-117, 40], [-107, 65], [-120, 92], [-99, 120], [-51, 120]]),
  path('craft_bridge', 6, [[-65, -14], [-65, 12], [-65, 33], [-80, 54], [-68, 80], [-51, 120], [0, 127]]),
  path('bellfound', 7, [[0, 48], [-28, 55], [-45, 49], [-65, 33]]),
  path('crownwatch', 6, [[0, 48], [27, 55], [46, 76], [73, 87], [105, 79], [122, 57], [118, 32], [119, -9]]),
  path('north_lane', 5, [[0, 127], [0, 119], [9, 113], [28, 113], [59, 113], [94, 123], [119, 103], [105, 79]]),
  path('lantern_quays', 5, [[95, 0], [104, -23], [125, -38], [127, -79], [118, -111], [101, -124], [80, -119]]),
  path('south_bridge', 6, [[34, -79], [46, -94], [70, -94], [88, -94], [101, -124]]),
  path('southwest', 4, [[-55, -101], [-87, -117], [-123, -113], [-125, -89], [-116, -62]]),
  path('east_court', 4, [[32, -16], [43, -39], [31, -58], [34, -79]]),
];
// Rectangles form a watertight orthogonal channel with doglegs and a quay basin.
export const CITY_CANALS = [
  { id: 'west', x: -122.5, z: 24, width: 45, depth: 8 },
  { id: 'west_bend', x: -100, z: 18, width: 8, depth: 20 },
  { id: 'craft', x: -68, z: 12, width: 64, depth: 8 },
  { id: 'central_bend', x: -36, z: 20, width: 8, depth: 24 },
  { id: 'central', x: 1, z: 28, width: 74, depth: 8 },
  { id: 'east_bend', x: 38, z: 23, width: 8, depth: 18 },
  { id: 'east', x: 69, z: 18, width: 62, depth: 8 },
  { id: 'quay_bend', x: 100, z: 25, width: 8, depth: 22 },
  { id: 'outfall', x: 122.5, z: 32, width: 45, depth: 8 },
  { id: 'south_branch', x: 70, z: -65.5, width: 8, depth: 167 },
  { id: 'basin_link', x: 85, z: -65, width: 30, depth: 8 },
  { id: 'basin', x: 104, z: -65, width: 18, depth: 24 },
].map(c => ({ ...c, bedY: -3, waterY: -1.1 }));
export const CITY_BRIDGES = [
  { x: -117, z: 24, width: 6, rotY: 0 }, { x: -65, z: 12, width: 6, rotY: 0 },
  { x: 0, z: 28, width: 8, rotY: 0 }, { x: 118, z: 32, width: 6, rotY: 0 },
  { x: 70, z: 0, width: 8, rotY: Math.PI / 2 }, { x: 70, z: -94, width: 6, rotY: Math.PI / 2 },
];
export const CITY_DISTRICTS = [
  { id: 'gateward', name: 'Gateward Market', x: 0, z: -105 },
  { id: 'cinderbank', name: 'Cinderbank', x: -82, z: -55 },
  { id: 'lantern_quays', name: 'Lantern Quays', x: 110, z: -40 },
  { id: 'bellfound', name: 'Bellfound Court', x: -25, z: 60 },
  { id: 'crownwatch', name: 'Crownwatch', x: 45, z: 108 },
];
export const CITY_PLACES = [
  { name: 'The Sable Lantern', x: -29, z: -95, kind: 'tavern_1', interior: 'tavern' },
  { name: 'The Lockkeeper', x: 118, z: -18, kind: 'tavern_2', interior: 'tavern' },
  { name: 'Cinderleaf Apothecary', x: -85, z: -56, kind: 'apothecary', interior: 'shop' },
  { name: 'Three Seals Exchange', x: 24, z: -99, kind: 'shop', interior: 'shop' },
  { name: 'Chapel of the Vigil', x: -27, z: 73, kind: 'chapel', interior: 'chapel' },
  { name: 'Bellfound Hall', x: 24, z: 73, kind: 'civic_hall', interior: 'civic' },
];
export const CITY_DISCOVERIES = [
  { name: 'Candlemaker Yard', x: -67, z: -95 }, { name: 'Ashen Rose Court', x: -98, z: -94 },
  { name: 'Bellfound Cloister', x: -44, z: 70 }, { name: 'Lockkeeper Landing', x: 119, z: -51 },
  { name: 'Vigil Shrine', x: -89, z: 92 }, { name: 'Covered Exchange', x: 17, z: -78 },
  { name: 'Crownwatch Garden', x: 67, z: 127 }, { name: 'Weavers Court', x: 91, z: -106 },
];
function distance(point, a, b) {
  const dx = b.x - a.x, dz = b.z - a.z;
  const t = Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.z - a.z) * dz) / (dx * dx + dz * dz || 1)));
  return Math.hypot(point.x - a.x - t * dx, point.z - a.z - t * dz);
}
export function inCityWater(x, z, pad = 0) {
  return CITY_CANALS.some(c => Math.abs(x - c.x) < c.width / 2 + pad && Math.abs(z - c.z) < c.depth / 2 + pad);
}
function onBridge(x, z, pad = 0) {
  return CITY_BRIDGES.some(b => Math.abs(x - b.x) < (b.rotY ? 6 : b.width / 2) - pad && Math.abs(z - b.z) < (b.rotY ? b.width / 2 : 6) - pad);
}
function prop(id, kind, x, z, extra = {}) {
  return { id: `aegis_city_${id}`, kind: `aegis_${kind}`, assetKey: `aegis_${kind}`, model: `prop_aegis_${kind}.glb`, lodModels: [`prop_aegis_${kind}_lod1.glb`, `prop_aegis_${kind}_lod2.glb`], x, z, rotY: 0, scale: 1, ...extra };
}
function solid(id, kind, x, z, width, depth, extra = {}) {
  return prop(id, kind, x, z, { colliders: [{ width, depth, minY: -.3, maxY: 30 }], ...extra });
}
export function rebuildAegisCity(zone) {
  if (zone.id !== 'aegis_capital')
    return;
  zone.cityLayoutVersion = AEGIS_CITY_VERSION;
  zone.size = 800;
  zone.terrainTexture = 'aegis_city/flagstone_baseColor.png';
  zone.paths = structuredClone(CITY_PATHS);
  zone.canals = structuredClone(CITY_CANALS);
  zone.cityDistricts = structuredClone(CITY_DISTRICTS);
  zone.explorationPlaces = structuredClone(CITY_DISCOVERIES);
  zone.atmosphere = { fogColor: '#626f76', sunColor: '#ccd7dd', sunIntensity: 1.5 };
  zone.biomeKits = [];
  const oldProps = zone.props;
  // Keep gameplay-bearing props; replace the old street-grid architecture.
  zone.props = oldProps.filter(p => zone.resourceNodes.some(n => n.visualPropId === p.id) || p.id?.includes('station_visual'));
  const props = zone.props;
  const protectedPoints = [{ ...zone.spawnPoint, radius: 10 }, ...CITY_DISCOVERIES.map(p => ({ ...p, radius: 7 }))];
  // Keep both stair flights and their approaches clear during denser infill.
  for (const x of [-140, 140]) for (const z of [86, 98, 110, 122, 134]) protectedPoints.push({ x, z, radius: 3 });
  // Existing city services remain on generous, accessible southern streets.
  zone.npcs.forEach((npc, i) => {
    const side = i % 2 ? -1 : 1;
    const row = Math.floor(i / 2);
    npc.x = side * (12 + (row % 2) * 2);
    npc.z = -112 + row * 7;
    npc.y = 0;
    protectedPoints.push({ ...npc, radius: 4 });
  });
  zone.craftingStations.forEach((s, i) => {
    s.x = -91 + i * 9;
    s.z = -39;
    s.y = 0;
    protectedPoints.push({ ...s, radius: 5 });
    const p = props.find(p => p.id === `${zone.id}_${s.kind}_station_visual`);
    if (p) {
      p.x = s.x;
      p.z = s.z;
    }
  });
  zone.resourceNodes.forEach((n, i) => {
    n.x = -122 + i * 10;
    n.z = -132;
    n.y = 0;
    protectedPoints.push({ ...n, radius: 4 });
    const p = props.find(p => p.id === n.visualPropId);
    if (p) {
      p.x = n.x;
      p.z = n.z;
    }
  });
  zone.enemies.forEach((e, i) => { e.x = 38 + i * 9; e.z = -124; e.y = 0; protectedPoints.push({ ...e, radius: 5 }); });
  zone.rvrObjectives.forEach((o, i) => { o.x = 0; o.z = i === 0 ? -137 : -40; protectedPoints.push({ ...o, radius: o.captureRadius + 1 }); });
  for (const place of CITY_PLACES) {
    const civic = place.interior === 'chapel' || place.interior === 'civic';
    const p = solid(place.kind, place.kind, place.x, place.z, civic ? 12 : 10, civic ? 12 : 10);
    props.push(p);
    props.push(prop(`${place.kind}_door`, 'sign', place.x, place.z + (civic ? 5.7 : 4.7), { interaction: { id: `aegis_city_enter_${place.kind}`, type: 'house_portal', label: place.name, interiorVariant: place.interior, maxDistance: 5 } }));
    protectedPoints.push({ x: place.x, z: place.z + 9, radius: 4 });
    zone.paths.push(path(`${place.kind}_entrance`, 4, [[place.x, place.z + 7], [place.x, place.z + 10]]));
  }
  addBattleCitadel(zone);
  // Defenses follow one boundary; each road and water opening is explicit.
  const openings = { south: [[-5, 5, 'road'], [66, 74, 'water']], north: [[-9, 9, 'citadel']], west: [[-5, 5, 'road'], [20, 28, 'water']], east: [[-5, 5, 'road'], [28, 36, 'water']] };
  zone.cityPerimeter = { minX: -145, maxX: 145, minZ: -145, maxZ: 250, openings };
  const wallEntrances = {};
  for (const [side, gaps] of Object.entries(openings)) {
    const vertical = side === 'west' || side === 'east';
    const fixed = side === 'north' ? 250 : side === 'south' || side === 'west' ? -145 : 145;
    const spans = [];
    let start = -145;
    const end = vertical ? 250 : 145;
    for (const [a, b, type] of [...gaps, [end, end, 'end']]) {
      if (a > start)
        spans.push([start, a]);
      // The enclosed mountain passage supplies its own gate and roof here.
      if (type !== 'end' && type !== 'citadel') {
        const mid = (a + b) / 2;
        const x = vertical ? fixed : mid, z = vertical ? mid : fixed;
        const rotY = vertical ? Math.PI / 2 : 0;
        props.push(prop(`${side}_${type}_gatehouse`, type === 'road' ? 'gatehouse' : 'water_gate', x, z, { rotY, colliders: type === 'road' ? [] : [{ width: 8, depth: 3, minY: -3, maxY: 11.9 }], walkableSurfaces: [{ width: type === 'road' ? 14 : 11, depth: 2, fromY: 12, toY: 12 }] }));
        if (type === 'road') {
          const propId = side === 'south' ? 'aegis_capital_city_gate_gate' : `aegis_capital_city_wall_${side}_gate`;
          const id = `${propId}_interaction`;
          props.push(prop(`${side}_gate`, 'portcullis', x, z, { id: propId, rotY, interaction: { id, type: 'gate', label: `${side[0].toUpperCase() + side.slice(1)} Gate`, maxDistance: 18, startsOpen: true }, colliders: [{ width: 10, depth: .5, minY: 0, maxY: 10, blocksWhen: 'closed', interactionId: id }] }));
        }
      }
      start = b;
    }
    let count = 0;
    for (const [a, b] of spans) {
      const n = Math.ceil((b - a) / 12), length = (b - a) / n;
      for (let i = 0; i < n; i++) {
        const mid = a + (i + .5) * length;
        const entry = vertical && Math.abs(mid - 82) < length / 2;
        if (entry) wallEntrances[side] = mid;
        // Collider offsets use the existing clockwise authoring convention.
        const parapets = [{ width: 12, depth: .5, z: 1.25, minY: 12, maxY: 15 }];
        if (entry) for (const x of [-4, 4]) parapets.push({ x, width: 4, depth: .5, z: -1.25, minY: 12, maxY: 15 });
        else parapets.push({ width: 12, depth: .5, z: -1.25, minY: 12, maxY: 15 });
        props.push(prop(`${side}_wall_${count++}`, entry ? 'wall_entry' : 'wall', vertical ? fixed : mid, vertical ? mid : fixed, {
          rotY: vertical ? (side === 'east' ? -Math.PI / 2 : Math.PI / 2) : 0,
          scaleX: length / 12,
          colliders: [{ width: 12, depth: 3, minY: 0, maxY: 11.9 }, ...parapets],
          walkableSurfaces: [{ width: 12, depth: 2, fromY: 12, toY: 12 }],
        }));
      }
    }
  }
  for (const [i, [x, z]] of [[-145, -145], [145, -145], [-145, 250], [145, 250], [-145, 60], [145, -90], [24, 250], [-80, -145]].entries())
    props.push(solid(`tower_${i}`, 'tower', x, z, 9, 9, { colliders: [{ width: 9, depth: 9, minY: 0, maxY: 11.9 }], walkableSurfaces: [{ width: 8, depth: 8, fromY: 12, toY: 12 }] }));
  // Stair model rises six metres; two consecutive flights reach the wall walk.
  for (const x of [-140, 140]) {
    const landingZ = wallEntrances[x < 0 ? 'west' : 'east'];
    props.push(prop(`stairs_lower_${x}`, 'stairs', x, landingZ + 36, { walkableSurfaces: [{ width: 3, depth: 24, fromY: 6, toY: 0 }] }));
    props.push(prop(`stairs_upper_${x}`, 'stairs', x, landingZ + 12, { y: 6, walkableSurfaces: [{ width: 3, depth: 24, fromY: 6, toY: 0 }] }));
    props.push(prop(`wall_landing_${x}`, 'paving', x < 0 ? -142 : 142, landingZ, { y: 12, scaleX: 1.75, walkableSurfaces: [{ width: 4, depth: 4, fromY: 0, toY: 0 }] }));
  }
  CITY_BRIDGES.forEach((b, i) => props.push(prop(`bridge_${i}`, b.width === 8 ? 'bridge_wide' : 'bridge_narrow', b.x, b.z, { rotY: b.rotY, scaleX: b.width === 8 ? 1 : b.width / 4, colliders: [{ x: -(b.width === 8 ? 4 : 2), width: .5, depth: 12, minY: 0, maxY: 2 }, { x: b.width === 8 ? 4 : 2, width: .5, depth: 12, minY: 0, maxY: 2 }], walkableSurfaces: [{ width: b.width === 8 ? 7.5 : 3.5, depth: 12, fromY: 0, toY: 0 }] })));
  // Water occupancy cells share exact boundaries with the terrain cutouts.
  for (let z = -145; z < 145; z += 2) {
    let start = null;
    for (let x = -145; x <= 145; x += 2) {
      const wet = x < 145 && inCityWater(x + 1, z + 1) && !onBridge(x + 1, z + 1);
      if (wet && start === null)
        start = x;
      if (!wet && start !== null) {
        props.push({ id: `aegis_city_water_block_${start}_${z}`, kind: 'city_water_collision', visible: false, x: (start + x) / 2, z: z + 1, rotY: 0, scale: 1, colliders: [{ width: x - start, depth: 2, minY: -4, maxY: 8 }] });
        start = null;
      }
    }
  }
  // Only union boundary edges receive masonry; internal channel joins stay open.
  const edges = [];
  for (const c of CITY_CANALS)
    for (const side of [-1, 1]) {
      for (const axis of ['x', 'z']) {
        const along = axis === 'x' ? c.width : c.depth;
        const across = axis === 'x' ? c.depth : c.width;
        const count = Math.ceil(along / 4), len = along / count;
        for (let i = 0; i < count; i++) {
          const t = -along / 2 + (i + .5) * len;
          const x = c.x + (axis === 'x' ? t : side * across / 2), z = c.z + (axis === 'x' ? side * across / 2 : t);
          if (inCityWater(x + (axis === 'z' ? side * .1 : 0), z + (axis === 'x' ? side * .1 : 0)) || onBridge(x, z, -.7))
            continue;
          edges.push({ x, z, len, rotY: axis === 'x' ? 0 : Math.PI / 2 });
        }
      }
    }
  edges.forEach((e, i) => { props.push(prop(`quay_${i}`, 'embankment', e.x, e.z, { rotY: e.rotY, scaleX: e.len / 8 })); props.push(prop(`rail_${i}`, 'railing', e.x, e.z, { rotY: e.rotY, scaleX: e.len / 8 })); });
  function available(point, radius) {
    if (point.z + radius > 128 && Math.abs(point.x) < 98 + radius) return false;
    if (inCityWater(point.x, point.z, radius))
      return false;
    if (protectedPoints.some(p => Math.hypot(p.x - point.x, p.z - point.z) < radius + p.radius))
      return false;
    if (zone.paths.some(p => p.points.slice(1).some((b, i) => distance(point, p.points[i], b) < p.width / 2 + radius + .8)))
      return false;
    return !props.some(p => (p.colliders ?? []).some(c => {
      if (p.visible === false || c.blocksWhen === 'closed')
        return false;
      const dx = Math.abs(point.x - p.x), dz = Math.abs(point.z - p.z);
      const w = (c.width * (p.scaleX ?? 1)) / 2, d = c.depth / 2;
      return dx < (p.rotY ? d : w) + radius + 1 && dz < (p.rotY ? w : d) + radius + 1;
    }));
  }
  let houseIndex = 0;
  for (let z = -126; z <= 128; z += 13)
    for (let x = -129; x <= 131; x += 13) {
      const point = { x: x + Math.sin(z * .3) * 2, z: z + Math.cos(x * .3) * 2 };
      if (!available(point, 5.7))
        continue;
      const kind = `house_${houseIndex % 6 + 1}`;
      const nearest = zone.paths.flatMap(p => p.points).sort((a, b) => Math.hypot(a.x - point.x, a.z - point.z) - Math.hypot(b.x - point.x, b.z - point.z))[0];
      const rotY = Math.round(Math.atan2(nearest.x - point.x, nearest.z - point.z) / (Math.PI / 2)) * Math.PI / 2;
      props.push(solid(`house_${houseIndex++}`, kind, point.x, point.z, 10, 10, { rotY }));
    }
  CITY_DISCOVERIES.forEach((p, i) => {
    props.push(prop(`discovery_${i}`, i === 5 ? 'arch' : i % 3 === 0 ? 'altar' : 'table', p.x + 3, p.z));
    props.push(prop(`discovery_lantern_${i}`, 'lantern', p.x - 3, p.z));
  });
  // Keep existing cosmetic kit variety, but relocate it around the new routes.
  const oldLife = oldProps.filter(p => p.id?.startsWith('aegis_capital_life_'));
  let cursor = 0;
  for (let z = -130; z < 135 && cursor < oldLife.length; z += 8)
    for (let x = -132; x < 136 && cursor < oldLife.length; x += 8) {
      if (!available({ x, z }, 3.5))
        continue;
      const p = { ...oldLife[cursor++], x, z };
      props.push(p);
      protectedPoints.push({ x, z, radius: 3.5 });
    }
  for (const [i, p] of zone.paths.filter(p => p.points.length > 2).slice(0, 7).entries()) {
    props.push(prop(`street_lantern_${i}`, 'lantern', p.points[0].x + p.width / 2 + 1, p.points[0].z));
  }
  // Interleave shuffled district plots so density does not accumulate at one edge.
  function cityPlots(step, salt) {
    const districts = CITY_DISTRICTS.map(() => []);
    for (let z = -126; z < 131; z += step) for (let x = -129; x < 133; x += step) {
      const point = { x, z };
      const nearest = CITY_DISTRICTS.map((d, i) => ({ i, distance: Math.hypot(d.x-x, d.z-z) })).sort((a,b) => a.distance-b.distance)[0].i;
      districts[nearest].push(point);
    }
    const key = p => (Math.imul(p.x+180, 73856093) ^ Math.imul(p.z+180,19349663) ^ salt) >>> 0;
    for (const list of districts) list.sort((a,b) => key(a)-key(b));
    const result = [];
    for (let i = 0; districts.some(list => i < list.length); i++) for (const list of districts) if (list[i]) result.push(list[i]);
    return result;
  }
  // Narrow houses and low workshops fill leftover plots without closing lanes.
  let infill = 0;
  for (const { x, z } of cityPlots(5, 8173)) {
    if (infill >= 36) break;
    if (!available({ x, z }, 3.8)) continue;
    const kind = ['rowhouse_1', 'lean_to', 'rowhouse_2'][infill % 3];
    props.push(solid(`infill_${infill++}`, kind, x, z, 7, 7, { rotY: (infill % 4) * Math.PI / 2 }));
  }
  // These are real ground-level objects, with footprints reserved from routes.
  const dressing = [
    { kind: 'awning_1', width: 3.8, depth: 2.6, height: 3.4 },
    { kind: 'barrel_cluster', width: 2.3, depth: 2.2, height: 1.4 },
    { kind: 'planter', width: 2.4, depth: 1.5, height: 1.4 },
    { kind: 'crate_stack', width: 2.6, depth: 2.2, height: 2.3 },
    { kind: 'courtyard_tree', width: 2.3, depth: 1.2, height: 3 },
    { kind: 'handcart', width: 2.2, depth: 3.4, height: 1.6 },
    { kind: 'awning_2', width: 3.8, depth: 2.6, height: 3.4 },
    { kind: 'noticeboard', width: 2.8, depth: 1, height: 3.2 },
    { kind: 'washing_line', width: 5, depth: .4, height: 3.2 },
  ];
  let detail = 0;
  const placeDetail = (x, z, item, rotation = 0) => {
    props.push(prop(`street_detail_${detail++}`, item.kind, x, z, {
      rotY: rotation, colliders: [{ width: item.width, depth: item.depth, minY: 0, maxY: item.height }],
    }));
    protectedPoints.push({ x, z, radius: Math.max(item.width, item.depth) / 2 + .4 });
  };
  for (const { x, z } of cityPlots(6, 1957)) {
    if (detail >= 135) break;
    const item = dressing[detail % dressing.length];
    const radius = item.kind === 'courtyard_tree' ? 2.8 : Math.max(item.width, item.depth) / 2;
    if (available({ x, z }, radius)) placeDetail(x, z, item, detail % 2 ? Math.PI / 2 : 0);
  }
  // Courts get a deliberate focal point with a clear central approach.
  CITY_DISCOVERIES.forEach((court, index) => {
    const kind = index % 3 === 0 ? 'fountain' : index % 3 === 1 ? 'courtyard_tree' : 'awning_1';
    props.push(prop(`court_feature_${index}`, kind, court.x, court.z - 4.2, {
      colliders: [{ width: kind === 'fountain' ? 4.2 : 3.8, depth: 3, minY: 0, maxY: 3.5 }],
    }));
  });
  zone.cityDetailCounts = { infillBuildings: infill, streetFurnishings: detail, courtFeatures: CITY_DISCOVERIES.length };
  zone.ambientLife = { actors: zone.paths.slice(0, 8).flatMap((p, i) => {
      // Out-and-back routes avoid a closing diagonal through buildings.
      // Ambient patrols stop before the siege gates; they cannot open closed gates.
      const points = p.points.filter(v => Math.abs(v.x) < 139 && Math.abs(v.z) < 139)
        .map(v => ({ ...v, z: Math.min(v.z, 130) }));
      const route = [...points, ...points.slice(1, -1).reverse()];
      return [0, 1].map(j => ({ id: `aegis_city_actor_${i}_${j}`, kind: j ? 'guard' : 'citizen', ...route[j], route: j ? [...route.slice(1), route[0]] : route, speed: j ? 1.2 : 1.0, pauseSeconds: 1, variant: i % 4 }));
    }), emitters: [] };
  for (let i = 0; i < 3; i++)
    zone.ambientLife.actors.push({ id: `aegis_city_bird_${i}`, kind: 'bird', x: -30 + i * 30, z: -40, route: [{ x: -30 + i * 30, z: -40 }, { x: -10 + i * 30, z: -20 }], speed: 4 });
  for (const p of props.filter(p => p.kind === 'life_campfire'))
    for (const kind of ['smoke', 'embers'])
      zone.ambientLife.emitters.push({ id: `${p.id}_${kind}`, kind, x: p.x, z: p.z, count: 5, radius: 1 });
  addAegisMountainRedoubt(zone);
  furnishAegisCitadel(zone);
  buildAegisMountainside(zone);
  // Reserve residents' standing space before placing street furniture.
  addAegisPeople(zone);
  addAegisCivicDecorations(zone);
  replaceAegisPrimitiveScenery(zone);
  addAegisCityInfill(zone);
}
