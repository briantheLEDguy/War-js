import type { ZoneDefinition, PathDefinition } from '../../shared/world/ZoneDefinition';
import { containsSpatialPoint, distanceToSpatialSegment, resolveZoneSpatial, type SpatialPoint } from '../../shared/worldSpatial';
import { segmentCrossesModule, type VillagePlan } from './t1-modules';

type StreetVillage = VillagePlan & { streets: PathDefinition[] };
type Segment = { a: SpatialPoint; b: SpatialPoint; width: number; nodes: SpatialPoint[] };
const distance = (a: SpatialPoint, b: SpatialPoint) => Math.hypot(a.x - b.x, a.z - b.z);
const cross = (a: SpatialPoint, b: SpatialPoint) => a.x * b.z - a.z * b.x;
const subtract = (a: SpatialPoint, b: SpatialPoint) => ({ x: a.x - b.x, z: a.z - b.z });
function project(p: SpatialPoint, a: SpatialPoint, b: SpatialPoint): SpatialPoint {
  const dx = b.x - a.x, dz = b.z - a.z;
  const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.z - a.z) * dz) / (dx * dx + dz * dz)));
  return { x: a.x + dx * t, z: a.z + dz * t };
}

/** Short door accesses join a real shared street graph; yards and other doors are never transit nodes. */
export function connectedStreetVillage<T extends StreetVillage>(original: T, zone: ZoneDefinition,
  height?: (point: SpatialPoint) => number): { town: T; access: Array<{ lotId: string; streetPoint: SpatialPoint; length: number }>; authoringGradesChecked: boolean; nativeTraversalAccepted: false } {
  if (original.zoneId !== zone.id || !zone.spawnPoint || original.streets.length > 40 || original.modules.length > 40
    || ![zone.spawnPoint.x, zone.spawnPoint.z, ...original.modules.flatMap(m => [m.entry.x, m.entry.z])].every(Number.isFinite))
    throw new Error('Street network requires a matching bounded village');
  const spatial = resolveZoneSpatial(zone), root = { x: zone.spawnPoint.x, z: zone.spawnPoint.z };
  const clear = (a: SpatialPoint, b: SpatialPoint, margin: number) => {
    const length = distance(a, b);
    if (!Number.isFinite(length) || length > 500) return false;
    const steps = Math.max(1, Math.ceil(length));
    const nx = length ? -(b.z - a.z) / length : 0, nz = length ? (b.x - a.x) / length : 0;
    const previous: Array<number | undefined> = [];
    for (let i = 0; i <= steps; i++) for (const [lane, offset] of [0, -margin, margin].entries()) {
      const p = { x: a.x + (b.x - a.x) * i / steps + nx * offset, z: a.z + (b.z - a.z) * i / steps + nz * offset };
      if (!containsSpatialPoint(spatial, p)) return false;
      if (height) {
        const y = height(p);
        if (!Number.isFinite(y) || (previous[lane] !== undefined && Math.abs(y - previous[lane]!) > length / steps * .12 + 1e-6)) return false;
        if (lane && previous[0] !== undefined && Math.abs(y - previous[0]!) > margin * .12 + 1e-6) return false;
        previous[lane] = y;
      }
    }
    return !original.modules.some(m => segmentCrossesModule(a, b, m, margin)
      || (m.practical && m.practical.y < 2 && distanceToSpatialSegment(m.practical, a, b) < margin + .7));
  };
  const segments: Segment[] = [];
  for (const street of original.streets) {
    if (!Number.isFinite(street.width) || street.width < 1 || street.width > 20 || street.points.length < 2 || street.points.length > 100)
      throw new Error('Invalid authored street');
    for (let i = 1; i < street.points.length; i++) {
      const a = street.points[i - 1], b = street.points[i];
      if (![a.x, a.z, b.x, b.z].every(Number.isFinite) || distance(a, b) < .01 || !clear(a, b, street.width / 2 + .6))
        throw new Error('Authored street is blocked, outside ground or too steep');
      segments.push({ a, b, width: street.width, nodes: [a, b] });
    }
  }
  if (!segments.length || segments.length > 600) throw new Error('Street graph is empty or unbounded');
  for (let i = 0; i < segments.length; i++) for (let j = i + 1; j < segments.length; j++) {
    const a = segments[i], b = segments[j], u = subtract(a.b, a.a), v = subtract(b.b, b.a), w = subtract(b.a, a.a), denominator = cross(u, v);
    if (Math.abs(denominator) > 1e-9) {
      const t = cross(w, v) / denominator, s = cross(w, u) / denominator;
      if (t >= -1e-9 && t <= 1 + 1e-9 && s >= -1e-9 && s <= 1 + 1e-9) {
        const point = { x: a.a.x + u.x * t, z: a.a.z + u.z * t }; a.nodes.push(point); b.nodes.push(point);
      }
    } else for (const p of [a.a, a.b, b.a, b.b]) {
      if (distanceToSpatialSegment(p, a.a, a.b) < 1e-6 && distanceToSpatialSegment(p, b.a, b.b) < 1e-6) { a.nodes.push(p); b.nodes.push(p); }
    }
  }
  const targets = [root, ...original.modules.map(m => m.entry)];
  const choices = targets.map(target => segments.flatMap(segment => {
    const point = project(target, segment.a, segment.b), length = distance(target, point);
    if (length > 30 || !clear(target, point, .6)) return [];
    segment.nodes.push(point); return [{ point, length }];
  }));
  const nodes: SpatialPoint[] = [], edges: Array<Map<number, number>> = [];
  const node = (p: SpatialPoint) => {
    let id = nodes.findIndex(n => distance(n, p) < 1e-6);
    if (id < 0) { id = nodes.length; nodes.push({ ...p }); edges.push(new Map()); }
    return id;
  };
  const link = (a: SpatialPoint, b: SpatialPoint) => {
    const from = node(a), to = node(b), length = distance(a, b);
    if (from !== to) { edges[from].set(to, length); edges[to].set(from, length); }
  };
  for (const segment of segments) {
    segment.nodes.sort((a, b) => distance(segment.a, a) - distance(segment.a, b));
    for (let i = 1; i < segment.nodes.length; i++) link(segment.nodes[i - 1], segment.nodes[i]);
  }
  node(root);
  // One nearest clear root access preserves a connected street component. Remote roads remain disconnected.
  const rootChoice = choices[0].sort((a, b) => a.length - b.length)[0];
  if (!rootChoice) throw new Error('Village centre has no short street access');
  link(root, rootChoice.point);
  const distances = nodes.map(() => Infinity), previous = nodes.map(() => -1), remaining = new Set(nodes.map((_, i) => i));
  distances[node(root)] = 0;
  while (remaining.size) {
    const current = [...remaining].reduce((a, b) => distances[a] < distances[b] ? a : b);
    if (!Number.isFinite(distances[current])) break;
    remaining.delete(current);
    for (const [next, length] of edges[current]) if (distances[current] + length < distances[next]) {
      distances[next] = distances[current] + length; previous[next] = current;
    }
  }
  const access: Array<{ lotId: string; streetPoint: SpatialPoint; length: number }> = [];
  const town = structuredClone(original);
  town.modules.forEach((lot, i) => {
    const selected = choices[i + 1].filter(c => Number.isFinite(distances[node(c.point)]))
      .sort((a, b) => a.length - b.length || distances[node(a.point)] - distances[node(b.point)])[0];
    if (!selected) throw new Error(`Door has no short access to connected streets: ${lot.id}`);
    access.push({ lotId: lot.id, streetPoint: { ...selected.point }, length: selected.length });
    const points = [{ ...lot.entry }]; let current = node(selected.point);
    while (current >= 0) { if (distance(points.at(-1)!, nodes[current]) > 1e-6) points.push({ ...nodes[current] }); current = previous[current]; }
    lot.approach = points;
  });
  return { town, access, authoringGradesChecked: Boolean(height), nativeTraversalAccepted: false };
}
