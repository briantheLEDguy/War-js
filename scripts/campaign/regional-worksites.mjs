import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { sharedKeepItemMetadata } from './shared-keep-items.mjs';
import { reviewedSceneryModelBounds } from './aegis-reviewed-scenery.mjs';

// These bays were measured against the delivered architecture, including built-in
// shelves and floors. A changed host needs a fresh fit instead of stale placement.
export const REGIONAL_WORKSITES = {
  sunmeadow_march: {
    hostKey: 'frontier_sunmeadow_supply_post',
    hostSha256: '241fc3646674f1279f4cc8dcc85dcd36ffbcc14894f0aecad33425b9dce45357',
    floorY: .086,
    bay: { x: 0, z: 0, width: 5.6, depth: 4.1 },
    builtIns: [-3.45, 3.45].map(x => ({ x, z: 0, width: 1.1, depth: 2.9 })),
    entrance: [[0, 3.5], [0, 1.7]],
    items: [
      { role: 'repair_bench', key: 'frontier_siege_repair_bench', x: -1.35, z: -.95 },
      { role: 'supply_cradle', key: 'frontier_siege_ammunition_cradle', x: 1.55, z: -.4 },
    ],
  },
  cinderfen_outskirts: {
    hostKey: 'frontier_cinderfen_workshop',
    hostSha256: '81067dcb441ce106583c46160649b46646500e473567bda809c47ff994d79ab9',
    floorY: .6,
    bay: { x: 2.5, z: 0, width: 4.4, depth: 7.4 },
    builtIns: [], // The authored bench already has measured host collision.
    entrance: [[0, 7.2], [0, 2.6]],
    items: [
      { role: 'repair_bench', key: 'frontier_siege_repair_bench', x: 2.5, z: -1.5, via: [[0, .4]] },
      { role: 'supply_cradle', key: 'frontier_siege_ammunition_cradle', x: 2.5, z: 1.5 },
    ],
  },
};

const localPoint = (prop, x, z) => {
  const yaw = -(prop.rotY ?? 0), c = Math.cos(yaw), s = Math.sin(yaw);
  return { x: prop.x + x * c - z * s, z: prop.z + x * s + z * c };
};

export const REGIONAL_APOTHECARIES = {
  sunmeadow_march: {
    hostKey: 'frontier_sunmeadow_supply_post',
    hostSha256: '241fc3646674f1279f4cc8dcc85dcd36ffbcc14894f0aecad33425b9dce45357',
    floorY: .086, bay: { x: 0, z: 0, width: 4.8, depth: 4.1 },
    builtIns: [-3.45, 3.45].map(x => ({ x, z: 0, width: 1.1, depth: 2.9 })),
    entrance: [[0, 3.5], [0, 1.7]],
    items: [{ role: 'table', key: 'frontier_field_apothecary', x: 0, z: -1.5 }],
  },
  cinderfen_outskirts: {
    hostKey: 'frontier_cinderfen_supply_shelter',
    hostSha256: '829317741fda3dc33d3df83209165650c399314af5176064c0de685b98639394',
    floorY: .35, bay: { x: 0, z: 0, width: 4.8, depth: 5.1 },
    builtIns: [],
    entrance: [[1.4, 5.3], [1.4, 3.4], [0, 1.7]],
    items: [{ role: 'table', key: 'frontier_field_apothecary', x: 0, z: -1.1 }],
  },
};

function apothecaryMetadata() {
  try { return JSON.parse(fs.readFileSync(new URL('../../authoring/blender/field-apothecary/builder-metadata.json', import.meta.url), 'utf8')).assets; }
  catch (error) { if (error.code === 'ENOENT') return {}; throw error; }
}
const rectangle = (prop, box) => {
  const scale = prop.scale ?? 1, sx = scale * (prop.scaleX ?? 1), sz = scale * (prop.scaleZ ?? 1);
  const sign = prop.colliderSpace === 'model' ? -1 : 1;
  const yaw = sign * (prop.rotY ?? 0), c = Math.cos(yaw), s = Math.sin(yaw);
  return { x: prop.x + (box.x ?? 0) * sx * c - (box.z ?? 0) * sz * s,
    z: prop.z + (box.x ?? 0) * sx * s + (box.z ?? 0) * sz * c,
    width: box.width * sx, depth: box.depth * sz, yaw: yaw + sign * (box.rotY ?? 0) };
};

/** Oriented bounds avoid false conflicts with Sunmeadow's angled side walls. */
export function worksiteRectanglesOverlap(a, b, gap = 0) {
  for (const angle of [a.yaw, a.yaw + Math.PI / 2, b.yaw, b.yaw + Math.PI / 2]) {
    const radius = box => Math.abs(Math.cos(box.yaw - angle)) * box.width / 2
      + Math.abs(Math.sin(box.yaw - angle)) * box.depth / 2;
    if (Math.abs((a.x - b.x) * Math.cos(angle) + (a.z - b.z) * Math.sin(angle))
      >= radius(a) + radius(b) + gap) return false;
  }
  return true;
}

export function regionalWorksiteReservations(prop, contract) {
  const { minimum: lo, maximum: hi } = contract.boundsYUp, front = contract.approachSource;
  return [
    { x: (lo[0] + hi[0]) / 2, z: (lo[2] + hi[2]) / 2, width: hi[0] - lo[0], depth: hi[2] - lo[2] },
    { x: (front.minimum[0] + front.maximum[0]) / 2, z: -(front.minimum[1] + front.maximum[1]) / 2,
      width: front.maximum[0] - front.minimum[0], depth: front.maximum[1] - front.minimum[1] },
  ].map(box => rectangle(prop, box));
}

const circleTouches = (point, box, radius) => {
  const c = Math.cos(box.yaw), s = Math.sin(box.yaw), dx = point.x - box.x, dz = point.z - box.z;
  const x = Math.max(0, Math.abs(dx * c + dz * s) - box.width / 2);
  const z = Math.max(0, Math.abs(-dx * s + dz * c) - box.depth / 2);
  return x * x + z * z <= radius * radius;
};
const routeClear = (points, obstacles) => points.every((b, index) => {
  if (!index) return true;
  const a = points[index - 1], count = Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) / .1);
  for (let i = 0; i <= count; i++) {
    const t = count ? i / count : 0, point = { x: a.x + (b.x - a.x) * t, z: a.z + (b.z - a.z) * t };
    if (obstacles.some(box => circleTouches(point, box, .45))) return false;
  }
  return true;
});
const bodyColliders = (prop, floorY = 0) => (prop.colliders ?? [])
  .filter(box => (box.maxY ?? Infinity) > floorY + .01 && (box.minY ?? -Infinity) < floorY + 1.8)
  .map(box => rectangle(prop, box));
const pointBox = point => ({ ...point, width: 1.4, depth: 1.4, yaw: 0 });
const delivered = asset => {
  if (!asset?.runtimeReady || !asset.model || !asset.modelSha256) return false;
  try {
    const bytes = fs.readFileSync(new URL(`../../public/assets/models/${asset.model}`, import.meta.url));
    return createHash('sha256').update(bytes).digest('hex') === asset.modelSha256;
  } catch { return false; }
};

/** Four useful service furnishings, only after measured geometry is published. */
export function integrateRegionalWorksites(zone, assets, metadata = sharedKeepItemMetadata()) {
  return integrateWorksite(zone, assets, metadata, REGIONAL_WORKSITES[zone.id], 'salvage_station', `${zone.id}_worksite_`);
}

/** Shared preparation equipment sits inside each climate's existing shelter. */
export function integrateRegionalApothecaries(zone, assets, metadata = apothecaryMetadata()) {
  return integrateWorksite(zone, assets, metadata, REGIONAL_APOTHECARIES[zone.id], 'apothecary_station', `${zone.id}_delivered_apothecary_`);
}

function integrateWorksite(zone, assets, metadata, site, stationSuffix, prefix) {
  if (!site) return zone;
  zone.props = zone.props.filter(prop => !prop.id?.startsWith(prefix));
  const host = zone.props.find(prop => prop.id === `${zone.id}_${stationSuffix}_visual`);
  const hostAsset = assets.staticProps?.[site.hostKey];
  if (!host || host.assetKey !== site.hostKey || !delivered(hostAsset)
    || hostAsset.modelSha256 !== site.hostSha256 || (host.model && host.model !== hostAsset.model)
    || host.visible === false || [host.scale, host.scaleX, host.scaleY, host.scaleZ].some(v => v !== undefined && v !== 1)
    || !host.colliders?.length) return zone;
  const service = zone.craftingStations?.find(station => station.id === `${zone.id}_${stationSuffix}`);
  if (!service) return zone;
  const occupied = bodyColliders(host, site.floorY).concat(site.builtIns.map(box => rectangle(host, box)));
  const externalObstacles = [...occupied];
  for (const prop of zone.props) {
    if (prop === host || Math.hypot(prop.x - host.x, prop.z - host.z) > 30) continue;
    const solids = bodyColliders(prop);
    occupied.push(...solids);
    externalObstacles.push(...solids);
    const model = prop.model ?? assets.staticProps?.[prop.assetKey ?? prop.kind]?.model;
    const bounds = prop.visible === false || !model ? null : reviewedSceneryModelBounds(model);
    if (bounds) {
      const visible = rectangle({ ...prop, colliderSpace: 'model' }, {
      x: (bounds.min.x + bounds.max.x) / 2, z: (bounds.min.z + bounds.max.z) / 2,
      width: bounds.max.x - bounds.min.x, depth: bounds.max.z - bounds.min.z,
      });
      occupied.push(visible);
      // Existing buildings have measured walls/doors: their roof overhang is
      // reserved against new objects, but is not a ground-level route blocker.
      if (!prop.colliders?.length) externalObstacles.push(visible);
    }
  }
  const actors = [...zone.npcs ?? [], ...zone.enemies ?? [], ...zone.ambientLife?.actors ?? []].map(pointBox);
  occupied.push(...actors);
  externalObstacles.push(...actors);
  const paths = [...zone.paths ?? [], ...zone.ambientLife?.actors ?? []].map(path => ({
    points: path.points ?? path.route ?? [], width: path.width ?? 1.4,
  }));
  const bay = rectangle(host, site.bay), pending = [];
  for (const item of site.items) {
    const asset = assets.staticProps?.[item.key], contract = metadata[item.key];
    if (!delivered(asset) || !contract?.runtimeReady
      || asset.modelSha256 !== contract.modelSha256 || !contract.boundsYUp || !contract.approachSource
      || !contract.colliders?.length) continue;
    const prop = { id: `${prefix}${item.role}`, kind: item.key, assetKey: item.key, model: asset.model,
      ...localPoint(host, item.x, item.z), y: (host.y ?? 0) + site.floorY,
      ...(host.heightMode === 'absolute' ? { heightMode: 'absolute' } : {}),
      rotY: host.rotY ?? 0, scale: 1, colliderSpace: 'model', cameraSolid: contract.cameraSolid ?? true,
      colliders: structuredClone(contract.colliders), walkableSurfaces: structuredClone(contract.walkableSurfaces ?? []) };
    const envelopes = regionalWorksiteReservations(prop, contract), front = envelopes[1];
    if (bodyColliders(prop).some(box => circleTouches(service, box, .5))) continue;
    // The fit uses identical bay/item yaw, so local projected extents are exact.
    const fits = envelopes.every(box => {
      const dx = box.x - bay.x, dz = box.z - bay.z;
      return Math.abs(dx * Math.cos(bay.yaw) + dz * Math.sin(bay.yaw)) + box.width / 2 < bay.width / 2
        && Math.abs(-dx * Math.sin(bay.yaw) + dz * Math.cos(bay.yaw)) + box.depth / 2 < bay.depth / 2;
    });
    if (!fits || Math.hypot(front.x - service.x, front.z - service.z) > service.radius
      || envelopes.some(box => occupied.some(other => worksiteRectanglesOverlap(box, other, .08)))) continue;
    if (paths.some(path => path.points.some((b, i) => {
      if (!i) return false;
      const a = path.points[i - 1], corridor = { x: (a.x + b.x) / 2, z: (a.z + b.z) / 2,
        width: Math.hypot(b.x - a.x, b.z - a.z), depth: path.width, yaw: Math.atan2(b.z - a.z, b.x - a.x) };
      return envelopes.some(box => worksiteRectanglesOverlap(box, corridor, .25));
    }))) continue;
    const route = [...site.entrance, ...item.via ?? []].map(([x, z]) => localPoint(host, x, z));
    route.push({ x: front.x, z: front.z });
    pending.push({ prop, envelopes, route });
    occupied.push(...envelopes);
  }
  // Test the whole composition: the second furnishing cannot trap the first.
  const navigation = [...externalObstacles,
    ...pending.flatMap(item => bodyColliders(item.prop))];
  for (const item of pending) if (routeClear(item.route, navigation)) zone.props.push(item.prop);
  if (zone.id === 'cinderfen_outskirts') zone.props.sort((a, b) => (a.id ?? '').localeCompare(b.id ?? ''));
  return zone;
}
