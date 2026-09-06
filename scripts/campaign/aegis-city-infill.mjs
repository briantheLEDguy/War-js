import { civicGroundHeight, distanceToCivicSegment } from './aegis-civic-decorations.mjs';
import { WORLD_LIFE_FOOTPRINTS } from './world-life-source.mjs';
import { AEGIS_REVIEWED_SCENERY, reviewedSceneryFootprint } from './aegis-reviewed-scenery.mjs';

// Full visible envelopes reserve roofs and tree crowns, not merely collision trunks.
export const INFILL_ASSETS = {
  house_1: [9.2, 9.4, 13], house_2: [8.2, 9.4, 14], house_3: [10.2, 10.4, 16],
  house_4: [9.2, 9.4, 13], house_5: [7.2, 9.4, 14], house_6: [10.2, 10.4, 16],
  rowhouse_1: [7.8, 6.8, 16], rowhouse_2: [7.8, 6.8, 18],
  garden_linden: [6.2, 6.2, 9], garden_cypress: [3, 3, 10],
  flowerbed_roses: [4, 2, 1.1], flowerbed_violets: [4, 2, 1.1],
};
const PREFIX = 'aegis_infill_';
const originalLifeKinds = new Map(Object.entries(AEGIS_REVIEWED_SCENERY)
  .filter(([kind]) => kind.startsWith('life_')).map(([kind, entry]) => [entry.kind, kind]));
const half = Math.PI / 2;
const hash = (x, z, salt = 0) => (Math.imul(Math.round(x * 100) + 18000, 73856093)
  ^ Math.imul(Math.round(z * 100) + 18000, 19349663) ^ salt) >>> 0;

export function infillFootprint(prop) {
  const kind = prop.kind.replace(/^aegis_/, ''), envelope = INFILL_ASSETS[kind];
  if (!envelope) return null;
  return { x: prop.x, z: prop.z, width: envelope[0] * (prop.scale ?? 1) * (prop.scaleX ?? 1),
    depth: envelope[1] * (prop.scale ?? 1) * (prop.scaleZ ?? 1), angle: -(prop.rotY ?? 0) };
}

function frontage(prop) {
  if (!/house/.test(prop.kind)) return null;
  const box = infillFootprint(prop), distance = box.depth / 2 + 1;
  return { x: box.x - Math.sin(box.angle) * distance, z: box.z + Math.cos(box.angle) * distance,
    width: 2.4, depth: 2, angle: box.angle };
}

function overlap(a, b, gap = .6) {
  if (b.clearanceRadius) {
    const dx = b.x - a.x, dz = b.z - a.z;
    const x = Math.max(0, Math.abs(dx * Math.cos(a.angle) + dz * Math.sin(a.angle)) - a.width / 2);
    const z = Math.max(0, Math.abs(-dx * Math.sin(a.angle) + dz * Math.cos(a.angle)) - a.depth / 2);
    return Math.hypot(x, z) < b.clearanceRadius;
  }
  const axes = [a.angle, a.angle + half, b.angle, b.angle + half];
  for (const axis of axes) {
    const ca = Math.abs(Math.cos(a.angle - axis)), sa = Math.abs(Math.sin(a.angle - axis));
    const cb = Math.abs(Math.cos(b.angle - axis)), sb = Math.abs(Math.sin(b.angle - axis));
    const distance = Math.abs((b.x - a.x) * Math.cos(axis) + (b.z - a.z) * Math.sin(axis));
    if (distance >= (a.width * ca + a.depth * sa + b.width * cb + b.depth * sb) / 2 + gap) return false;
  }
  return true;
}

function segmentNearBox(a, b, box, padding) {
  const cos = Math.cos(box.angle), sin = Math.sin(box.angle);
  const local = p => ({ x: (p.x - box.x) * cos + (p.z - box.z) * sin,
    z: -(p.x - box.x) * sin + (p.z - box.z) * cos });
  const p = local(a), q = local(b);
  let lo = 0, hi = 1;
  for (const [start, delta, extent] of [[p.x, q.x - p.x, box.width / 2 + padding],
    [p.z, q.z - p.z, box.depth / 2 + padding]]) {
    if (Math.abs(delta) < 1e-9) { if (Math.abs(start) > extent) return false; continue; }
    const u = (-extent - start) / delta, v = (extent - start) / delta;
    lo = Math.max(lo, Math.min(u, v)); hi = Math.min(hi, Math.max(u, v));
    if (lo > hi) return false;
  }
  return true;
}

function existingFootprints(zone, excludedId) {
  return zone.props.filter(p => p.id !== excludedId).flatMap(p => {
    if (p.id?.startsWith(PREFIX)) return [infillFootprint(p), frontage(p)].filter(Boolean);
    const visible = /^aegis_(house_|rowhouse_)/.test(p.kind) ? infillFootprint(p) : reviewedSceneryFootprint(p);
    const sx = (p.scale ?? 1) * (p.scaleX ?? 1), sz = (p.scale ?? 1) * (p.scaleZ ?? 1);
    const angle = (p.colliderSpace === 'model' ? -1 : 1) * (p.rotY ?? 0);
    if (p.kind === 'aegis_courtyard_tree') return [{ x: p.x, z: p.z, width: 5.2 * sx, depth: 4.5 * sz, angle }];
    const boxes = (p.colliders ?? []).filter(c => (c.minY ?? 0) < 2.2 && (c.maxY ?? 100) >= 0).map(c => ({
      x: p.x + (c.x ?? 0) * sx * Math.cos(angle) - (c.z ?? 0) * sz * Math.sin(angle),
      z: p.z + (c.x ?? 0) * sx * Math.sin(angle) + (c.z ?? 0) * sz * Math.cos(angle),
      width: c.width * sx, depth: c.depth * sz,
      angle: angle + (p.colliderSpace === 'model' ? -1 : 1) * (c.rotY ?? 0),
    }));
    // Converted models retain the original scenery's navigation reservation even
    // where the delivered mesh and collision occupy a smaller fitted envelope.
    const lifeKind = p.id?.startsWith(`${zone.id}_life_`) ? originalLifeKinds.get(p.kind) ?? p.kind : p.kind;
    const radius = WORLD_LIFE_FOOTPRINTS[lifeKind];
    const reserved = radius ? [{ x: p.x, z: p.z, clearanceRadius: radius }] : [];
    if (boxes.length || visible || reserved.length) return [...(visible ? [visible] : []), ...boxes, ...reserved];
    if (p.kind === 'aegis_lantern' || p.kind === 'banner_post') return [{ x: p.x, z: p.z, width: 1, depth: 1, angle: 0 }];
    return [];
  }).filter(Boolean);
}

function protectedPoints(zone) {
  return [{ ...zone.spawnPoint, radius: 8 },
    ...(zone.npcs ?? []).map(p => ({ ...p, radius: 3 })),
    ...(zone.enemies ?? []).map(p => ({ ...p, radius: 4 })),
    ...(zone.craftingStations ?? []).map(p => ({ ...p, radius: 3 })),
    ...(zone.resourceNodes ?? []).map(p => ({ ...p, radius: 3 })),
    ...(zone.explorationPlaces ?? []).filter(p => p.z < 140).map(p => ({ ...p, radius: 4.5 })),
    ...(zone.rvrObjectives ?? []).map(p => ({ ...p, radius: p.captureRadius + 1 })),
    ...(zone.zoneTriggers ?? []).map(p => ({ ...p, radius: (p.radius ?? 3) + 3 })),
    ...zone.props.filter(p => p.interaction).map(p => ({ ...p, radius: 3.5 }))];
}

export function infillPositionClear(zone, prop, options = {}) {
  const box = infillFootprint(prop), radius = Math.hypot(box.width, box.depth) / 2;
  if (Math.abs(box.x) + radius > 138 || box.z - radius < -137 || box.z + radius > 238) return false;
  // The military enclosure, siege approaches and mountain expansion are kept open.
  if (box.z + radius > 125 && Math.abs(box.x) - radius < 98) return false;
  if ((zone.canals ?? []).some(c => overlap(box, { ...c, angle: 0 }, .8))) return false;
  if ((options.protectedPoints ?? protectedPoints(zone)).some(p => overlap(box, { ...p, width: p.radius * 2, depth: p.radius * 2, angle: 0 }, .5))) return false;
  if (zone.paths.some(p => p.points.slice(1).some((b, i) => segmentNearBox(p.points[i], b, box, p.width / 2 + .7)))) return false;
  const footprints = options.footprints ?? existingFootprints(zone, prop.id), door = frontage(prop);
  if (footprints.some(p => overlap(box, p, .7) || (door && overlap(door,p,.5)))) return false;
  const tree = prop.kind.includes('garden_'), spanX = tree ? .45 : box.width / 2, spanZ = tree ? .45 : box.depth / 2;
  const base = civicGroundHeight(zone, box.x, box.z), cos = Math.cos(box.angle), sin = Math.sin(box.angle);
  for (const dx of [-1, -.5, 0, .5, 1]) for (const dz of [-1, -.5, 0, .5, 1]) {
    const ground = civicGroundHeight(zone, box.x + dx * spanX * cos - dz * spanZ * sin,
      box.z + dx * spanX * sin + dz * spanZ * cos);
    if (Math.abs(ground - base) > (tree ? .18 : .045)) return false;
  }
  return true;
}

function candidate(kind, x, z, index, scale = 1, rotY = 0) {
  const [width, depth, height] = INFILL_ASSETS[kind], tree = kind.startsWith('garden_');
  return { id: `${PREFIX}${kind}_${index}`, kind: `aegis_${kind}`, assetKey: `aegis_${kind}`,
    model: `prop_aegis_${kind}.glb`, lodModels: [1, 2].map(l => `prop_aegis_${kind}_lod${l}.glb`),
    x, z, scale, rotY, colliderSpace: 'model', colliders: tree ? [
      { width: kind === 'garden_linden' ? 1.44 : .7, depth: kind === 'garden_linden' ? 1.44 : .7, minY: -.03, maxY: .2 },
      { width: .7, depth: .7, minY: .15, maxY: 2.8 },
    ] : [{ width, depth, minY: 0, maxY: height }] };
}

function plots(zone, spacing, salt) {
  const lists = zone.cityDistricts.map(() => []);
  for (let z = -132; z < 234; z += spacing) for (let x = -133; x < 134; x += spacing) {
    const jitter = hash(x, z, salt), p = { x: x + (jitter % 101) / 100 * 1.7 - .85,
      z: z + ((jitter >>> 8) % 101) / 100 * 1.7 - .85 };
    const district = zone.cityDistricts.map((d, i) => ({ i, distance: Math.hypot(d.x - p.x, d.z - p.z) })).sort((a,b) => a.distance - b.distance)[0].i;
    lists[district].push(p);
  }
  for (const list of lists) list.sort((a,b) => hash(a.x,a.z,salt) - hash(b.x,b.z,salt));
  const result = [];
  for (let i = 0; lists.some(list => i < list.length); i++) for (const list of lists) if (list[i]) result.push(list[i]);
  return result;
}

/** Infill follows the final terrain, civic cast and decorations, so it cannot
 * displace existing destinations or introduce new foundations across street grades. */
export function addAegisCityInfill(zone) {
  if (zone.id !== 'aegis_capital') return;
  zone.props = zone.props.filter(p => !p.id?.startsWith(PREFIX));
  const clearance = { footprints: existingFootprints(zone), protectedPoints: protectedPoints(zone) };
  const counts = { houses: 0, trees: 0, flowerbeds: 0 };
  const houseUses = {};
  const districtCounts = Object.fromEntries(zone.cityDistricts.map(d => [d.id, { houses: 0, trees: 0, flowerbeds: 0 }]));
  const place = (p, type) => {
    zone.props.push(p); counts[type]++;
    if (type === 'houses') houseUses[p.kind.replace('aegis_','')] = (houseUses[p.kind.replace('aegis_','')] ?? 0) + 1;
    clearance.footprints.push(infillFootprint(p));
    const door = frontage(p); if (door) clearance.footprints.push(door);
    const nearest = [...zone.cityDistricts].sort((a,b) => Math.hypot(a.x-p.x,a.z-p.z) - Math.hypot(b.x-p.x,b.z-p.z))[0];
    districtCounts[nearest.id][type]++;
  };
  const houses = ['house_1','rowhouse_1','house_5','house_2','rowhouse_2','house_4','house_3','house_6'];
  for (const point of plots(zone, 2.5, 12591)) {
    if (counts.houses >= 28) break;
    const nearest = zone.paths.flatMap(p => p.points.slice(1).map((b,i) => ({ a:p.points[i], b,
      distance: distanceToCivicSegment(point, p.points[i], b) }))).sort((a,b) => a.distance-b.distance)[0];
    if (nearest.distance > 28) continue;
    const front = { x: (nearest.a.x + nearest.b.x) / 2, z: (nearest.a.z + nearest.b.z) / 2 };
    const yaw = Math.round(Math.atan2(front.x-point.x,front.z-point.z)/half)*half || 0;
    const variants = houses.map((_,i) => houses[(counts.houses+i)%houses.length])
      .sort((a,b) => (houseUses[a] ?? 0) - (houseUses[b] ?? 0));
    for (const kind of variants) {
      const scale = [.85,.9,.95,1][hash(point.x,point.z,1181)%4];
      const p = candidate(kind, point.x, point.z, counts.houses, scale, yaw);
      if (infillPositionClear(zone,p,clearance)) { place(p,'houses'); break; }
    }
  }
  for (const point of plots(zone, 3.5, 7757)) {
    if (counts.trees >= 52) break;
    const kind = counts.trees % 3 === 0 ? 'garden_linden' : 'garden_cypress';
    const value = hash(point.x,point.z,487), scale = [.84, .94, 1.04, 1.14][value % 4];
    const p = candidate(kind, point.x, point.z, counts.trees, scale, value % 628 / 100);
    if (infillPositionClear(zone,p,clearance)) place(p,'trees');
  }
  for (const point of plots(zone, 2.8, 4141)) {
    if (counts.flowerbeds >= 80) break;
    const value = hash(point.x,point.z,144), kind = counts.flowerbeds % 2 ? 'flowerbed_violets' : 'flowerbed_roses';
    const scale = [.8,.9,1,1.1][value % 4];
    const p = candidate(kind,point.x,point.z,counts.flowerbeds,scale,(value % 4)*half + ((value >>> 8)%9-4)*.018);
    if (infillPositionClear(zone,p,clearance)) place(p,'flowerbeds');
  }
  zone.cityExpansion = { version: 'garden-wards-v1', ...counts, districtCounts };
}
