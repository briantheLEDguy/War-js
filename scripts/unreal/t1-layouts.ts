import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { orvrHeightAt, createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { containsSpatialPoint, distanceToSpatialSegment, resolveZoneSpatial, spatialSegmentInside, type SpatialPoint } from '../../shared/worldSpatial';
import { villagePlan } from './t1-modules';

type Point = SpatialPoint & { y: number };
type Region = {
  width: number; depth: number; outline: number[][]; village: number[]; main: number[][];
  upper: number[][]; lower: number[][]; lair: number[]; landforms: number[][];
  theme: string; landmark: string; architecture: string; palette: string[]
};
const point = ([x, z, y = 0]: number[]): Point => ({ x, z, y });
const suffixes = ['west_objective', 'central_objective', 'east_objective'];
/** Coordinates are source metres. Route vertices include grade targets, not arbitrary terrain samples. */
export const T1_REGIONS: Record<string, Region> = {
  sunmeadow_march: {
    width: 1500, depth: 1100,
    outline: [[-740, -380], [-620, -530], [-240, -500], [80, -535], [550, -470], [740, -260], [720, 260], [540, 510], [120, 530], [-160, 440], [-570, 520], [-735, 180]],
    village: [-585, -280, 5],
    main: [[-435, -110, 8], [-285, -70, 5], [-120, -45, 6], [-60, -15, 8], [5, 25, 10], [75, 35, 12], [145, 50, 14], [285, 15, 10], [430, -55, 9]],
    upper: [[-435, -110, 8], [-310, 130, 15], [-60, 180, 23], [75, 190, 23], [290, 150, 18], [430, -55, 9]],
    lower: [[-435, -110, 8], [-310, -205, 8], [-60, -190, 12], [75, -170, 15], [300, -180, 12], [430, -55, 9]],
    lair: [-475, 360, 18], landforms: [[-120, 370, 560, 175, 66], [230, -400, 570, 160, 54], [-570, 145, 220, 250, 34]],
    theme: 'Cultivated valley, requisitioned harvests and wooded barrow ridges', landmark: 'Ancient oak at the barrow track',
    architecture: 'Empire limestone and oak timber', palette: ['#858b59', '#bda578', '#646853'],
  },
  brightfen_approach: {
    width: 1700, depth: 850,
    outline: [[-840, -230], [-680, -405], [-300, -325], [-95, -405], [180, -330], [490, -400], [835, -205], [800, 200], [540, 390], [250, 300], [80, 405], [-170, 300], [-530, 405], [-820, 210]],
    village: [-680, -190, 6],
    main: [[-430, -95, 8], [-280, -35, 8], [-125, 25, 9], [-60, 60, 10], [5, 95, 12], [75, 70, 11], [140, 25, 10], [280, -25, 9], [430, -75, 8]],
    upper: [[-430, -95, 8], [-325, 135, 10], [-60, 215, 16], [75, 210, 15], [305, 145, 12], [430, -75, 8]],
    lower: [[-430, -95, 8], [-285, -200, 7], [-60, -160, 9], [75, -155, 9], [310, -180, 8], [430, -75, 8]],
    lair: [570, 235, 7], landforms: [[-540, -115, 280, 230, 19], [-100, 95, 290, 245, 23], [375, -85, 340, 240, 20], [570, 270, 170, 140, 34], [0, -340, 700, 100, -5]],
    theme: 'Linked limestone islands, pale causeway and exposed crossings', landmark: 'Causeway watch arch over reflective pools',
    architecture: 'High Elf pale limestone', palette: ['#7d917e', '#bbbdac', '#6d857e'],
  },
  cinderfen_outskirts: {
    width: 1250, depth: 1100,
    outline: [[-610, -280], [-460, -490], [-110, -540], [300, -500], [600, -250], [610, 160], [435, 450], [150, 540], [-130, 440], [-60, 220], [-250, 155], [-490, 300], [-620, 110]],
    village: [380, -290, 12],
    main: [[-420, -160, 12], [-280, -190, 13], [-120, -170, 14], [-60, -125, 16], [5, -80, 18], [75, -55, 20], [140, -30, 21], [275, -65, 18], [420, -115, 16]],
    upper: [[-420, -160, 12], [-300, 20, 25], [-60, 60, 28], [75, 110, 30], [300, 120, 28], [420, -115, 16]],
    lower: [[-420, -160, 12], [-280, -320, 14], [-60, -310, 17], [75, -290, 18], [285, -280, 17], [420, -115, 16]],
    lair: [-395, 210, 20], landforms: [[-300, 55, 230, 160, 54], [230, 310, 310, 210, 70], [-50, -440, 390, 125, 40], [0, -160, 390, 170, -6]],
    theme: 'Crescent geothermal basin, curved causeway, basalt ridges and peat dykes', landmark: 'Mineral chimney beside the Cindermaw track',
    architecture: 'Greenskin heavy timber on basalt with a Dark Elf supply compound', palette: ['#82714a', '#a67544', '#484b49'],
  },
  ashen_steppe: {
    width: 1900, depth: 850,
    outline: [[-940, -220], [-720, -405], [-335, -345], [-85, -415], [240, -350], [660, -405], [940, -200], [905, 220], [650, 405], [310, 335], [105, 405], [-210, 295], [-560, 400], [-880, 220]],
    village: [735, -195, 10],
    main: [[-430, -125, 10], [-275, -80, 8], [-120, -30, 9], [-60, 10, 11], [5, 65, 13], [75, 75, 14], [140, 55, 14], [280, 5, 12], [430, -65, 11]],
    upper: [[-430, -125, 10], [-310, 80, 24], [-60, 215, 27], [75, 225, 26], [290, 150, 25], [430, -65, 11]],
    lower: [[-430, -125, 10], [-300, -250, 14], [-60, -200, 18], [75, -165, 18], [300, -180, 16], [430, -65, 11]],
    lair: [-665, 215, 18], landforms: [[-160, 305, 570, 180, 76], [240, -315, 600, 140, 65], [-700, 90, 250, 200, 42]],
    theme: 'Bending dry wash below layered sandstone plateaus, silver ash and bleached grass', landmark: 'Dark standing monuments above the caravan wash',
    architecture: 'Chaos stone halls and fortified caravan compounds', palette: ['#999789', '#bab6a4', '#625e59'],
  },
};

function length(points: SpatialPoint[]): number {
  return points.slice(1).reduce((sum, p, i) => sum + Math.hypot(p.x - points[i].x, p.z - points[i].z), 0);
}
function moveTree<T>(value: T, old: SpatialPoint, next: Point): T {
  if (Array.isArray(value)) return value.map(v => moveTree(v, old, next)) as T;
  if (!value || typeof value !== 'object') return value;
  const row = value as Record<string, unknown>;
  const result = Object.fromEntries(Object.entries(row).map(([k, v]) => [k, moveTree(v, old, next)]));
  if (typeof row.x === 'number' && typeof row.z === 'number') {
    result.x = row.x + next.x - old.x; result.z = row.z + next.z - old.z;
    result.y = (typeof row.y === 'number' ? row.y : 0) + next.y;
  }
  return result as T;
}
function supplyPath(paths: Point[][], start: Point, finish: Point): Point[] {
  const key = (p: Point) => `${p.x},${p.z}`;
  const nodes = new Map<string, Point>(), edges = new Map<string, Set<string>>();
  for (const path of paths) for (let i = 0;i < path.length;i++) {
    const p = path[i], id = key(p); nodes.set(id, p); if (!edges.has(id)) edges.set(id, new Set());
    if (i) { const previous = key(path[i - 1]); edges.get(id)!.add(previous); edges.get(previous)!.add(id); }
  }
  let best: Point[] | undefined, bestLength = Infinity;
  const visit = (id: string, route: Point[], distance: number, seen: Set<string>) => {
    if (distance > 750 || distance >= bestLength) return;
    if (id === key(finish)) { if (distance >= 350) { best = route; bestLength = distance; } return; }
    for (const next of edges.get(id) ?? []) if (!seen.has(next)) {
      const p = nodes.get(next)!; visit(next, [...route, p], distance + Math.hypot(p.x - route.at(-1)!.x, p.z - route.at(-1)!.z), new Set([...seen, next]));
    }
  };
  visit(key(start), [start], 0, new Set([key(start)]));
  if (!best) throw new Error('No physical supply itinerary in the 350–750 m pacing band');
  return best;
}

/** Creates a review candidate. No source map, asset approval or owner-authored native level is changed. */
export function redesignT1(source: ZoneDefinition): ZoneDefinition {
  const region = T1_REGIONS[source.id]; if (!region) return structuredClone(source);
  const zone = structuredClone(source), old = source.orvrLayout; if (!old) throw new Error('Missing retained RvR layout');
  const main = region.main.map(point), upper = region.upper.map(point), lower = region.lower.map(point), village = point(region.village), lair = point(region.lair);
  zone.size = Math.max(region.width, region.depth) + 200; zone.segments = Math.ceil(zone.size / 6); zone.flatTerrain = false;
  zone.spatial = {
bounds: { minX: -region.width / 2 - 100, maxX: region.width / 2 + 100, minZ: -region.depth / 2 - 100, maxZ: region.depth / 2 + 100 },
    playableOutline: region.outline.map(([x, z]) => ({ x, z })), terrainGrid: { segmentsX: Math.ceil((region.width + 200) / 6), segmentsZ: Math.ceil((region.depth + 200) / 6) }
};
  resolveZoneSpatial(zone);
  const layout = zone.orvrLayout!; layout.spatial = zone.spatial; layout.size = zone.size;
  layout.version = 't1-landscape-candidate-v1'; layout.status = 'layout-ready-art-pending';
  layout.biome.palette = region.palette;
  const targets = main.filter((_, i) => [2, 4, 6].includes(i));
  const oldVillage = { x: source.spawnPoint!.x, z: source.spawnPoint!.z + 40 };
  layout.keeps = old.keeps.map((keep, i) => {
    const delivery = main[i === 0 ? 0 : 8], center = { ...delivery, z: delivery.z + 78 };
    const moved = moveTree(keep, keep, center); moved.heading = 0; return moved;
  });
  layout.battlefieldObjectives = old.battlefieldObjectives.map((bo, i) => ({ ...bo, ...targets[i] }));
  layout.stagingCamps = old.stagingCamps.map((camp, i) => ({ ...camp, x: main[i === 0 ? 0 : 8].x + (i === 0 ? -110 : 110), z: main[i === 0 ? 0 : 8].z + 115, y: main[i === 0 ? 0 : 8].y }));
  const paths = [main, upper, lower, [upper[2], main[3], lower[2]], [upper[3], main[5], lower[3]]];
  zone.paths = paths.map((points, i) => ({ id: `${zone.id}_${['advance', 'ridge_flank', 'outer_flank', 'rotation_1', 'rotation_2'][i]}`, style: 'dirt_trail', width: 12, points }));
  for (const [i, keep] of layout.keeps.entries()) zone.paths.push({ id: `${keep.objectiveId}_approach`, style: 'dirt_trail', width: 6, points: [{ ...keep.deliveryPoint, y: main[i === 0 ? 0 : 8].y }, { x: keep.x, z: keep.z - 13.9, y: main[i === 0 ? 0 : 8].y }, { x: keep.x, z: keep.z, y: main[i === 0 ? 0 : 8].y }] });
  for (const [i, camp] of layout.stagingCamps.entries()) zone.paths.push({ id: `${camp.id}_road`, style: 'dirt_trail', width: 12, points: [camp, main[i === 0 ? 0 : 8]] });
  const home = source.campaign?.realm === 'aegis' ? 0 : 1;
  zone.paths.push({ id: `${zone.id}_village_road`, style: 'dirt_trail', width: 12, points: [village, layout.stagingCamps[home], main[home === 0 ? 0 : 8]] });
  const capitalCourt = { ...village, x: village.x + (home === 0 ? 55 : -55), z: village.z - 40 };
  for (const trigger of zone.zoneTriggers ?? []) {
    const destination = trigger.targetZoneId;
    const pos = destination.endsWith('_capital') ? capitalCourt : destination.endsWith('_pit') || destination.endsWith('_den') || destination === 'wardens_hollow' ? lair :
      { ...main[home === 0 ? 8 : 0], x: home === 0 ? region.width / 2 - 100 : -region.width / 2 + 100 };
    const entrance = destination.endsWith('_capital') ? village : destination === 'wardens_hollow' || destination.endsWith('_pit') || destination.endsWith('_den') ?
      (lair.x < 0 ? upper[1] : upper[4]) : main[home === 0 ? 8 : 0];
    Object.assign(trigger, pos, { radius: 12 });
    const dx = entrance.x - pos.x, dz = entrance.z - pos.z, mag = Math.hypot(dx, dz);
    trigger.arrivalPoint = { x: pos.x + dx / mag * 26, z: pos.z + dz / mag * 26, y: pos.y };
    zone.paths.push({ id: `${trigger.id}_road`, style: 'dirt_trail', width: 12, points: [entrance, pos] });
  }
  layout.caravanRoutes = old.caravanRoutes.map(route => {
    const index = suffixes.findIndex(suffix => route.objectiveId === `${zone.id}_${suffix}`), side = route.realm === 'aegis' ? 0 : 8;
    const points = supplyPath(paths, targets[index], main[side]);
    return { ...route, points, width: 12, clearanceRadius: 9, lengthMetres: Math.round(length(points) * 100) / 100 };
  });
  layout.terrain = {
...layout.terrain, sourceVersion: 't1-landscape-candidate-v1', gradedRoutes: true, chunkSize: 0,
    landforms: region.landforms.map(([x, z, radiusX, radiusZ, height], i) => ({ id: `${zone.id}_relief_${i}`, kind: height < 0 ? 'basin' : 'ridge', x, z, radiusX, radiusZ, height })),
    flattenAreas: [{ id: 'village', ...village, radius: 95, height: village.y, feather: 35 },
    { id: 'arrival_court', ...capitalCourt, radius: 27, height: village.y, feather: 20 },
    ...layout.keeps.map((k, i) => ({ id: k.objectiveId, x: k.x, z: k.z, radius: 58, height: main[i === 0 ? 0 : 8].y, feather: 25 })),
    ...targets.map((p, i) => ({ id: suffixes[i], ...p, radius: 24, height: p.y, feather: 15 })),
    ...layout.stagingCamps.map((p, i) => ({ ...p, radius: 34, height: main[i === 0 ? 0 : 8].y, feather: 20 }))],
    clearCorridors: zone.paths.map(path => ({ id: path.id, points: path.points.map(p => ({ ...p, y: 'y' in p ? Number(p.y) : main.find(m => m.x === p.x)?.y ?? 0 })), radius: path.width / 2 + 7, height: 0, feather: 18 })), chunks: []
};
  const b = zone.spatial.bounds;
  for (let z = 0;z < 3;z++)for (let x = 0;x < 4;x++)layout.terrain.chunks.push({
id: `${zone.id}_candidate_${x}_${z}`, x: b.minX + (x + .5) * (b.maxX - b.minX) / 4, z: b.minZ + (z + .5) * (b.maxZ - b.minZ) / 3,
    width: (b.maxX - b.minX) / 4, depth: (b.maxZ - b.minZ) / 3, assetKey: `t1_${zone.id}_terrain_${x}_${z}`, collisionAssetKey: `t1_${zone.id}_collision_${x}_${z}`, lodDistances: [150, 350], status: 'planned'
});
  for (const objective of zone.rvrObjectives ?? []) { const target = layout.keeps.find(k => k.objectiveId === objective.id) ?? layout.battlefieldObjectives.find(k => k.objectiveId === objective.id); if (!target) throw new Error('Missing retained objective'); Object.assign(objective, { x: target.x, z: target.z }); }
  const moveRoot = <T extends SpatialPoint>(row: T, from: SpatialPoint, to: SpatialPoint): T => ({ ...row, x: row.x + to.x - from.x, z: row.z + to.z - from.z });
  const relocate = <T extends SpatialPoint & { id?: string }>(row: T): T => {
    const keep = old.keeps.find(k => row.id?.startsWith(k.objectiveId));
    if (keep) return moveRoot(row, keep, layout.keeps.find(k => k.objectiveId === keep.objectiveId)!);
    const bo = old.battlefieldObjectives.find(k => row.id?.startsWith(k.objectiveId));
    if (bo) return moveRoot(row, bo, layout.battlefieldObjectives.find(k => k.objectiveId === bo.objectiveId)!);
    if (Math.hypot(row.x - oldVillage.x, row.z - oldVillage.z) < 170) return moveRoot(row, oldVillage, village);
    const next = { ...row, x: row.x * region.width / 1200, z: row.z * region.depth / 1200 };
    if (containsSpatialPoint(zone.spatial!, next, 12)) return next;
    // Retained service/encounter identity is moved to connected ground, never discarded.
    const nearest = [...main, ...upper, ...lower].reduce((a, p) => Math.hypot(p.x - next.x, p.z - next.z) < Math.hypot(a.x - next.x, a.z - next.z) ? p : a, main[0]);
    return { ...row, x: nearest.x, z: nearest.z + 35 };
  };
  for (const key of ['npcs', 'enemies', 'resourceNodes', 'craftingStations'] as const) zone[key] = zone[key]?.map(row => relocate(row)) as never;
  zone.props = zone.props?.map(prop => {
    const portal = source.zoneTriggers?.find(t => prop.id === `${zone.id}_portal_${t.targetZoneId}`);
    if (portal) return moveRoot(prop, portal, zone.zoneTriggers!.find(t => t.id === portal.id)!);
    return relocate(prop);
  });
  for (const prop of zone.props ?? []) {
    if (!prop.colliders?.length || layout.keeps.some(keep => prop.id?.startsWith(keep.objectiveId))) continue;
    const footprint = Math.max(...prop.colliders.map(c => Math.hypot((c.x ?? 0) * (prop.scaleX ?? 1), (c.z ?? 0) * (prop.scaleZ ?? 1))
      + Math.hypot(c.width * (prop.scaleX ?? 1), c.depth * (prop.scaleZ ?? 1)) / 2)) * (prop.scale ?? 1);
    const clear = (p: SpatialPoint) => containsSpatialPoint(zone.spatial!, p, footprint + 1) && (zone.paths ?? []).every(path => path.points.slice(1).every((end, i) =>
      distanceToSpatialSegment(p, path.points[i], end) > footprint + path.width / 2 + 3));
    if (clear(prop)) continue;
    const original = { x: prop.x, z: prop.z }; let placed = false;
    for (let radius = 8;radius <= 180 && !placed;radius += 8)for (let i = 0;i < 16 && !placed;i++) {
      const angle = i * Math.PI / 8, candidate = { x: original.x + Math.cos(angle) * radius, z: original.z + Math.sin(angle) * radius };
      if (clear(candidate)) { Object.assign(prop, candidate); placed = true; }
    }
    if (!placed) throw new Error(`No clear retained scenery placement: ${prop.id}`);
    for (const resource of zone.resourceNodes ?? []) if (resource.visualPropId === prop.id) { resource.x += prop.x - original.x; resource.z += prop.z - original.z; }
    for (const station of zone.craftingStations ?? []) if (prop.id === station.id) { station.x += prop.x - original.x; station.z += prop.z - original.z; }
  }
  if (zone.ambientLife) { zone.ambientLife.actors = zone.ambientLife.actors.map(actor => ({ ...relocate(actor), route: actor.route?.map(p => moveTree(p, oldVillage, village)) })); zone.ambientLife.emitters = zone.ambientLife.emitters.map(relocate); }
  zone.spawnPoint = { ...village };
  const villageModules = villagePlan(zone);
  layout.terrain.flattenAreas.push(...villageModules.modules.map(module => ({
id: module.id, x: module.x, z: module.z,
    radius: Math.hypot(module.reservation.width, module.reservation.depth) / 2 + 2, height: village.y, feather: 8
})));
  const height = createOrvrGridHeightSampler(layout.terrain, zone.size, zone.segments, zone.spatial);
  const oldHeight = createOrvrGridHeightSampler(old.terrain, source.size, source.segments, source.spatial);
  for (const prop of zone.props ?? []) if (prop.heightMode === 'absolute') {
    const prior = source.props?.find(p => p.id === prop.id);
    if (prior) prop.y = (prior.y ?? 0) - oldHeight(prior.x, prior.z) + height(prop.x, prop.z);
  }
  zone.spawnPoint = { ...village, y: height(village.x, village.z) };
  for (const trigger of zone.zoneTriggers ?? []) { trigger.y = height(trigger.x, trigger.z); trigger.arrivalPoint!.y = height(trigger.arrivalPoint!.x, trigger.arrivalPoint!.z); }
  layout.biome.placements = [];
  layout.assetPolicy.mode = 'authored-required';
  layout.assetPolicy.requiredAssetKeys = [...layout.assetPolicy.requiredAssetKeys.filter(key => !key.includes('_terrain_') && !key.includes('_collision_')),
  ...layout.terrain.chunks.flatMap(tile => [tile.assetKey, tile.collisionAssetKey])];
  validateT1(zone);
  return zone;
}

export function validateT1(zone: ZoneDefinition): void {
  const spatial = resolveZoneSpatial(zone), layout = zone.orvrLayout!;
  if (layout.keeps.length !== 2 || layout.battlefieldObjectives.length !== 3 || layout.stagingCamps.length !== 2 || layout.caravanRoutes.length !== 6) throw new Error('Retained RvR composition changed');
  for (const path of zone.paths ?? []) for (let i = 1;i < path.points.length;i++)if (!spatialSegmentInside(spatial, path.points[i - 1], path.points[i], path.width / 2 + 3)) throw new Error(`Unsupported full-width route: ${path.id}`);
  for (const route of layout.caravanRoutes) if (length(route.points) < 350 || length(route.points) > 750) throw new Error('Supply pacing outside target band');
  for (const trigger of zone.zoneTriggers ?? []) if (!trigger.arrivalPoint || !containsSpatialPoint(spatial, trigger, trigger.radius) || !spatialSegmentInside(spatial, trigger, trigger.arrivalPoint, 1)) throw new Error(`Unsafe authored arrival: ${trigger.id}`);
  const terrain = layout.terrain;
  if (Math.max(...terrain.landforms.map(p => orvrHeightAt(terrain, p.x, p.z))) < 25) throw new Error('Terrain relief is insufficient');
}
