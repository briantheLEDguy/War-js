import type { ZoneDefinition, PathDefinition } from '../../shared/world/ZoneDefinition';
import { containsSpatialPoint, distanceToSpatialSegment, resolveZoneSpatial, type SpatialPoint } from '../../shared/worldSpatial';
import { moduleLocalPoint, segmentCrossesModule, validateVillagePlan, villagePlan, type VillagePlan } from './t1-modules';

export type SunmeadowTownPlan = VillagePlan & {
  streets: PathDefinition[];
  uses: Record<string, { template: string; purpose: string }>;
  nativeAssetsAccepted: false;
};

// Lot coordinates are metres relative to the retained village green. Back lots face
// service lanes; the main street opens into the existing military frontage.
const lots: Array<[number, number, string, string]> = [
  [-27, -70, 'aegis_interior_00_home', 'Farm family home beside the quiet southern approach'],
  [-60, -90, 'aegis_interior_01_home', 'Furnished household on the rear residential lane'],
  [-60, -60, 'aegis_compact_00', 'Housing for seasonal field workers'],
  [25, -100, 'aegis_compact_02', 'Carters household near the southern street'],
  [60, -90, 'aegis_compact_03', 'Stable workers household with a rear yard'],
  [-90, -60, 'aegis_compact_05', 'Orchard workers household on the outer lane'],
  [-27, -30, 'aegis_interior_04_shop', 'General provisions facing the market green'],
  [-27, 25, 'aegis_interior_04_shop', 'Arms shop on the outgoing military street'],
  [-60, 0, 'aegis_interior_04_shop', 'Apothecary with a quiet preparation yard'],
  [-60, -30, 'aegis_interior_06_workshop', 'Forge behind the shop fronts with a delivery yard'],
  [30, 30, 'aegis_interior_07_workshop', 'Joinery and wagon repairs beside the service lane'],
  [-27, -50, 'aegis_interior_04_shop', 'Cloth and tailoring beside the residential street'],
  [-27, 50, 'aegis_interior_09_inn', 'Inn facing arriving travellers and the military frontage'],
  [25, -70, 'aegis_interior_07_workshop', 'Bakery supplying the street and garrison courtyard'],
  [-60, 30, 'aegis_interior_06_workshop', 'Harvest storage behind the civilian street'],
  [60, 30, 'aegis_interior_06_workshop', 'Requisition warehouse with a rear loading court'],
  [-60, 60, 'aegis_interior_06_workshop', 'Barracks near the outgoing frontier road'],
  [-27, 75, 'aegis_compact_10', 'Watchhouse overlooking the street entrance'],
  [30, 60, 'aegis_interior_07_workshop', 'Stable and tack building beside the wagon lane'],
  [60, 90, 'aegis_interior_07_workshop', 'Command hall at the northern garrison edge'],
];

/** Separate authoring candidate: never relocates gameplay identities or regenerates accepted maps. */
export function sunmeadowStreetPlan(zone: ZoneDefinition): SunmeadowTownPlan {
  if (zone.id !== 'sunmeadow_march' || !zone.spawnPoint) throw new Error('Sunmeadow street plan requires its regional village');
  const base = villagePlan(zone), center = zone.spawnPoint;
  const point = (x: number, z: number): SpatialPoint => ({ x: center.x + x, z: center.z + z });
  const street = (id: string, width: number, points: number[][]): PathDefinition => ({
    id: `${zone.id}_town_${id}`, style: 'dirt_trail', autoConnect: false, width,
    points: points.map(([x, z]) => point(x, z)),
  });
  const plan: SunmeadowTownPlan = {
    ...base, layout: 'Main Street, market green, rear working lanes and attached garrison court',
    streets: [
      street('main_street', 12, [[0, -105], [0, -85], [0, -70], [0, -45], [0, -40], [0, -20], [0, 0], [3.509, 25], [7.018, 50], [10.526, 75], [13.333, 95]]),
      street('west_service_lane', 3, [[-48, -90], [-48, -60], [-48, -30], [-48, 0], [-48, 30], [-48, 60], [-48, 75]]),
      street('east_service_lane', 4, [[45, -100], [45, -85], [55, -40], [45, 10], [45, 30], [45, 60], [45, 90]]),
      street('south_west_lane', 3, [[0, -105], [-48, -105], [-75, -105], [-75, -60]]),
      street('south_east_lane', 4, [[0, -85], [45, -85]]),
      street('market_west_lane', 3, [[0, 0], [-48, 0]]),
      street('market_east_lane', 4, [[0, 10], [45, 10]]),
      street('garrison_court_link', 8, [[0, -40], [55, -40]]),
      street('north_lane', 4, [[11.93, 85], [45, 85]]),
    ], uses: {}, nativeAssetsAccepted: false,
  };
  for (let index = 0; index < plan.modules.length; index++) {
    const module = plan.modules[index], [x, z, template, purpose] = lots[index];
    Object.assign(module, point(x, z), { rotY: x < 0 ? -Math.PI / 2 : Math.PI / 2 });
    module.entry = moduleLocalPoint(module, { x: 0, z: -10 });
    module.approach = [];
    if (module.practical) Object.assign(module.practical, moduleLocalPoint(module, { x: 2, z: -8 }), { rotY: module.rotY + Math.PI });
    plan.uses[module.id] = { template, purpose };
  }
  connectTownDoors(plan, zone);
  validateSunmeadowTown(plan, zone);
  return plan;
}

function connectTownDoors(plan: SunmeadowTownPlan, zone: ZoneDefinition): void {
  // Bounded visibility graph joins door targets to explicit street vertices. Every
  // candidate edge respects all lot envelopes and low fixtures, including concavity.
  const spatial = resolveZoneSpatial(zone), root = { x: zone.spawnPoint!.x, z: zone.spawnPoint!.z };
  const nodes = [root, ...plan.streets.flatMap(s => s.points), ...plan.modules.map(m => m.entry)];
  const clear = (a: SpatialPoint, b: SpatialPoint) => {
    const count = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.z - a.z)));
    return Array.from({ length: count + 1 }, (_, i) => ({ x: a.x + (b.x - a.x) * i / count, z: a.z + (b.z - a.z) * i / count }))
      .every(p => containsSpatialPoint(spatial, p, .6))
      && !plan.modules.some(m => segmentCrossesModule(a, b, m)
        || (m.practical && m.practical.y < 2 && distanceToSpatialSegment(m.practical, a, b) < 1.3));
  };
  const distances = nodes.map(() => Infinity), previous = nodes.map(() => -1), remaining = new Set(nodes.map((_, i) => i));
  distances[0] = 0;
  while (remaining.size) {
    const index = [...remaining].reduce((a, b) => distances[a] < distances[b] ? a : b);
    if (!Number.isFinite(distances[index])) break;
    remaining.delete(index);
    for (const next of remaining) {
      const length = Math.hypot(nodes[next].x - nodes[index].x, nodes[next].z - nodes[index].z);
      if (length > 55 || distances[index] + length >= distances[next] || !clear(nodes[index], nodes[next])) continue;
      distances[next] = distances[index] + length; previous[next] = index;
    }
  }
  for (const module of plan.modules) {
    let index = nodes.indexOf(module.entry);
    if (!Number.isFinite(distances[index])) throw new Error(`Town door has no connected approach: ${module.id}`);
    while (index >= 0) { module.approach.push(nodes[index]); index = previous[index]; }
  }
}

export function validateSunmeadowTown(plan: SunmeadowTownPlan, zone: ZoneDefinition): void {
  validateVillagePlan(plan, zone);
  if (plan.streets.length !== 9 || Object.keys(plan.uses).length !== 20 || plan.nativeAssetsAccepted !== false)
    throw new Error('Town streets, uses or acceptance changed');
  const spatial = resolveZoneSpatial(zone);
  for (const street of plan.streets) for (let i = 1; i < street.points.length; i++) {
    const a = street.points[i - 1], b = street.points[i];
    if (!containsSpatialPoint(spatial, a, street.width / 2 + .6) || !containsSpatialPoint(spatial, b, street.width / 2 + .6)
      || plan.modules.some(m => segmentCrossesModule(a, b, m, street.width / 2 + .6)))
      throw new Error(`Town lot blocks full-width street: ${street.id}`);
  }
  for (const module of plan.modules) {
    if (!plan.uses[module.id]?.purpose || !plan.uses[module.id]?.template.startsWith('aegis_')) throw new Error('Town lot has no regional use');
    // Existing interaction points remain independently reachable beside the buildings.
    for (const service of plan.serviceReservations) if (segmentCrossesModule(service.point, service.point, module, service.radius))
      throw new Error(`Town lot blocks retained service: ${service.id}`);
    const dxCourt = plan.arrivalCourt.point.x - module.x, dzCourt = plan.arrivalCourt.point.z - module.z;
    const localX = dxCourt * Math.cos(module.rotY) - dzCourt * Math.sin(module.rotY);
    const localZ = dzCourt * Math.cos(module.rotY) + dxCourt * Math.sin(module.rotY);
    if (Math.hypot(Math.max(0, Math.abs(localX) - module.reservation.width / 2),
      Math.max(0, Math.abs(localZ) - module.reservation.depth / 2)) < plan.arrivalCourt.radius)
      throw new Error('Town lot blocks retained capital courtyard');
    for (const other of plan.modules) if (other !== module) {
      const c = Math.cos(module.rotY), s = Math.sin(module.rotY);
      const dx = other.x - module.x, dz = other.z - module.z;
      // All lots face the street axis, so their world envelopes are axis-aligned.
      if (Math.abs(dx * c - dz * s) < (module.reservation.width + other.reservation.width) / 2 + 2
        && Math.abs(dz * c + dx * s) < (module.reservation.depth + other.reservation.depth) / 2 + 2)
        throw new Error('Town lots overlap');
    }
  }
}