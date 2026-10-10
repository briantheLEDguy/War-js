import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { containsSpatialPoint, distanceToSpatialSegment, resolveZoneSpatial, type SpatialPoint } from '../../shared/worldSpatial';
import { segmentCrossesModule, type VillagePlan } from './t1-modules';

/** Connect door targets through authored street vertices without crossing reserved buildings. */
export function connectVillageStreets(plan: VillagePlan & { streets: Array<{ points: SpatialPoint[] }> }, zone: ZoneDefinition): void {
  if (plan.zoneId !== zone.id || !zone.spawnPoint) throw new Error('Street connections require the matching village');
  const spatial = resolveZoneSpatial(zone), nodes = [zone.spawnPoint, ...plan.streets.flatMap(s => s.points), ...plan.modules.map(m => m.entry)];
  const clear = (a: SpatialPoint, b: SpatialPoint) => {
    const steps = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.z - a.z)));
    return Array.from({ length: steps + 1 }, (_, i) => ({ x: a.x + (b.x - a.x) * i / steps, z: a.z + (b.z - a.z) * i / steps }))
      .every(p => containsSpatialPoint(spatial, p, .6))
      && !plan.modules.some(m => segmentCrossesModule(a, b, m)
        || (m.practical && m.practical.y < 2 && distanceToSpatialSegment(m.practical, a, b) < 1.3));
  };
  const distances = nodes.map(() => Infinity), previous = nodes.map(() => -1), remaining = new Set(nodes.map((_, i) => i));
  distances[0] = 0;
  while (remaining.size) {
    const current = [...remaining].reduce((a, b) => distances[a] < distances[b] ? a : b);
    if (!Number.isFinite(distances[current])) break;
    remaining.delete(current);
    for (const next of remaining) {
      const length = Math.hypot(nodes[next].x - nodes[current].x, nodes[next].z - nodes[current].z);
      if (length > 55 || distances[current] + length >= distances[next] || !clear(nodes[current], nodes[next])) continue;
      distances[next] = distances[current] + length; previous[next] = current;
    }
  }
  // Resolve the whole graph before committing so a failed study cannot partially rewrite its caller.
  const approaches = plan.modules.map(module => {
    let current = nodes.indexOf(module.entry);
    if (!Number.isFinite(distances[current])) throw new Error(`Village door has no connected approach: ${module.id}`);
    const points: SpatialPoint[] = [];
    while (current >= 0) { points.push({ x: nodes[current].x, z: nodes[current].z }); current = previous[current]; }
    return points;
  });
  plan.modules.forEach((module, index) => { module.approach = approaches[index]; });
}
