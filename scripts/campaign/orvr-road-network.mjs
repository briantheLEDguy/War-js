import { naturalRoadCurve } from './sunmeadow-road-network.mjs';

const round = value => Math.round(value * 1000) / 1000;
const point = (x, z) => ({ x: round(x), z: round(z) });
const distance = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
const lengthOf = points => Math.round(points.slice(1).reduce((sum, p, i) => sum + distance(p, points[i]), 0) * 100) / 100;

/** Matches the authority's conservative world-space collision footprints. */
export function roadPropFootprints(prop) {
  const scale = prop.scale ?? 1, sx = scale * (prop.scaleX ?? 1), sz = scale * (prop.scaleZ ?? 1);
  const sign = prop.colliderSpace === 'model' ? -1 : 1, rotation = sign * (prop.rotY ?? 0);
  return (prop.colliders ?? []).map(box => {
    const yaw = sign * ((prop.rotY ?? 0) + (box.rotY ?? 0));
    const x = prop.x + (box.x ?? 0) * sx * Math.cos(rotation) - (box.z ?? 0) * sz * Math.sin(rotation);
    const z = prop.z + (box.x ?? 0) * sx * Math.sin(rotation) + (box.z ?? 0) * sz * Math.cos(rotation);
    const halfX = (Math.abs(Math.cos(yaw)) * box.width * sx + Math.abs(Math.sin(yaw)) * box.depth * sz) / 2;
    const halfZ = (Math.abs(Math.sin(yaw)) * box.width * sx + Math.abs(Math.cos(yaw)) * box.depth * sz) / 2;
    return { minX: x - halfX, maxX: x + halfX, minZ: z - halfZ, maxZ: z + halfZ };
  });
}

const boxDistance = (p, box) => Math.hypot(Math.max(0, box.minX - p.x, p.x - box.maxX), Math.max(0, box.minZ - p.z, p.z - box.maxZ));
function roadSamples(paths) {
  return paths.flatMap(path => path.points.slice(1).flatMap((b, i) => {
    const a = path.points[i], count = Math.max(1, Math.ceil(distance(a, b)));
    return Array.from({ length: count }, (_, index) => ({ x: a.x + (b.x - a.x) * index / count, z: a.z + (b.z - a.z) * index / count, radius: path.width / 2 + .25 }));
  }).concat([{ ...path.points.at(-1), radius: path.width / 2 + .25 }]));
}

function clearIncidentalProps(zone) {
  const samples = roadSamples(zone.paths), layout = zone.orvrLayout;
  const visualRadius = prop => /^(tree|pnw_.*tree)/.test(prop.kind) ? 5 : /^(rock|pnw_.*rock)/.test(prop.kind) ? 3 : prop.kind === 'banner_post' ? .6 : 0;
  const blocked = prop => {
    const boxes = roadPropFootprints(prop), radius = visualRadius(prop) * (prop.scale ?? 1);
    return samples.some(sample => boxes.some(box => boxDistance(sample, box) < sample.radius)
      || (radius > 0 && distance(prop, sample) < sample.radius + radius));
  };
  const keepProp = prop => layout.keeps.some(keep => prop.id?.startsWith(`${keep.objectiveId}_`));
  const fixed = (zone.props ?? []).filter(prop => keepProp(prop) || (zone.craftingStations ?? []).some(station => prop.id?.startsWith(station.id)));
  const occupied = new Map((zone.props ?? []).map(prop => [prop, roadPropFootprints(prop)]));
  for (const prop of zone.props ?? []) {
    if (keepProp(prop) || !blocked(prop)) continue;
    if (fixed.includes(prop)) throw new Error(`Road intersects crafting station geometry: ${prop.id}`);
    const original = { x: prop.x, z: prop.z };
    const objective = layout.battlefieldObjectives.find(objective => prop.id === `${objective.objectiveId}_banner`);
    let target = null;
    // Search the nearest verge in stable order. IDs, services, and travel triggers never change.
    for (let radius = 2; radius <= 120 && !target; radius += 2) for (let step = 0; step < 32 && !target; step++) {
      const angle = step * Math.PI / 16, candidate = { ...prop, ...point(original.x + Math.cos(angle) * radius, original.z + Math.sin(angle) * radius) };
      if (Math.abs(candidate.x) > 578 || Math.abs(candidate.z) > 578 || blocked(candidate)) continue;
      if (objective && distance(candidate, objective) > objective.captureRadius - 1) continue;
      if (layout.keeps.some(keep => distance(candidate, keep) < 76)) continue;
      const boxes = roadPropFootprints(candidate);
      if (boxes.some(box => [...occupied].some(([other, footprints]) => other !== prop && footprints.some(other =>
        box.minX < other.maxX + .25 && box.maxX > other.minX - .25 && box.minZ < other.maxZ + .25 && box.maxZ > other.minZ - .25)))) continue;
      if ((zone.npcs ?? []).some(npc => boxes.some(box => boxDistance(npc, box) < 1.2))) continue;
      target = candidate;
    }
    if (!target) throw new Error(`No clear roadside placement for ${prop.id}`);
    prop.x = target.x; prop.z = target.z;
    occupied.set(prop, roadPropFootprints(prop));
    for (const node of zone.resourceNodes ?? []) if (node.visualPropId === prop.id) { node.x = prop.x; node.z = prop.z; }
  }
}

/** Connected outdoor roads; supply itineraries share the spine and keep branches exactly. */
export function composeOrvrRoads(zone) {
  const layout = zone.orvrLayout;
  if (!layout || zone.id === 'sunmeadow_march') return zone;
  const paths = [], edges = new Map();
  const style = zone.paths?.some(path => path.style === 'cobblestone_avenue') ? 'cobblestone_avenue' : 'dirt_trail';
  const road = (name, width, controls) => {
    const points = naturalRoadCurve(controls);
    paths.push({ id: `${zone.id}_${name}`, style, width, points, autoConnect: false }); edges.set(name, points);
  };
  // Small deterministic bends give each climate region its own alignment without duplicating routes.
  const seed = [...zone.id].reduce((sum, char) => sum + char.charCodeAt(0), 0), bend = (seed % 13) - 6;
  road('march_road_south', 12, [[0,-260],[-15-bend,-205],[14+bend,-133],[20,-65],[0,0]]);
  road('march_road_north', 12, [[0,0],[-18,65],[-25-bend,145],[-8,212],[0,260]]);
  for (const keep of layout.keeps) {
    const sign = keep.x < 0 ? -1 : 1;
    road(`${keep.realm}_keep_road`, 12, [[0,0],[sign*75,-8],[sign*150,-38-bend],[sign*225,-70],[sign*290,-82],[keep.deliveryPoint.x,keep.deliveryPoint.z]]);
    road(`${keep.realm}_keep_approach`, 5, [[keep.deliveryPoint.x,keep.deliveryPoint.z],[keep.x,-48],[keep.x,0]]);
    road(`${keep.realm}_support_link`, 8, [[keep.deliveryPoint.x,keep.deliveryPoint.z],[sign*375,-83],[sign*395,-92]]);
    road(`${keep.realm}_staging_road`, 7, [[sign*395,-92],[sign*432,-62],[sign*450,5],[sign*477,52],[sign*505,80]]);
  }
  const settlement = layout.terrain.flattenAreas.find(area => area.id.endsWith('_settlement'));
  if (settlement) {
    const sign = settlement.x < 0 ? -1 : 1;
    road('settlement_road', 8, [[sign*395,-92],[sign*417,-142],[sign*425,-190],[settlement.x,settlement.z]]);
  }
  for (const trigger of [...zone.zoneTriggers ?? []].sort((a, b) => a.id.localeCompare(b.id))) {
    // Join the closest existing road, including earlier portal branches, instead of fanning from the central BO.
    const candidates = paths.flatMap(path => path.points).filter(p => distance(p, trigger) > 16 && layout.keeps.every(keep => distance(p, keep) > 94));
    candidates.sort((a, b) => distance(a, trigger) - distance(b, trigger));
    let points;
    for (const start of candidates) {
      const dx = trigger.x - start.x, dz = trigger.z - start.z, length = Math.hypot(dx, dz), curve = Math.min(12, length * .07);
      const controls = [[start.x,start.z],[start.x+dx*.35-dz/length*curve,start.z+dz*.35+dx/length*curve],
        [start.x+dx*.7-dz/length*curve*.6,start.z+dz*.7+dx/length*curve*.6],[trigger.x,trigger.z]];
      const proposed = naturalRoadCurve(controls);
      if (proposed.every(p => Math.abs(p.x) < 585 && Math.abs(p.z) < 585 && layout.keeps.every(keep => distance(p, keep) > 90))) { points = proposed; break; }
    }
    if (!points) throw new Error(`No safe portal road for ${trigger.id}`);
    const optional = /_den$|_lair$|_pit$|_hollow$|_warrens$|_sanctum$|_depths$|_maw$/.test(trigger.targetZoneId);
    paths.push({ id: `${zone.id}_portal_road_${trigger.targetZoneId}`, style, width: optional ? 4 : 8, points, autoConnect: false });
  }
  for (const route of layout.caravanRoutes) {
    const prefix = route.objectiveId.endsWith('_west_objective') ? edges.get('march_road_south')
      : route.objectiveId.endsWith('_east_objective') ? [...edges.get('march_road_north')].reverse() : [point(0,0)];
    route.points = [...prefix, ...edges.get(`${route.realm}_keep_road`).slice(1)];
    route.lengthMetres = lengthOf(route.points);
  }
  zone.paths = paths;
  layout.terrain.clearCorridors = paths.map(path => ({ id: path.id, points: structuredClone(path.points), radius: path.width / 2 + 3, height: 0, feather: 20 }));
  clearIncidentalProps(zone);
  return zone;
}
