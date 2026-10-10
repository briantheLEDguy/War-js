import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { containsSpatialPoint, distanceToSpatialSegment, resolveZoneSpatial, type SpatialPoint } from '../../shared/worldSpatial';
import { segmentCrossesModule } from './t1-modules';
import { sunmeadowStreetPlan, type SunmeadowTownPlan } from './sunmeadow-town-plan';

export type TownYard = SpatialPoint & {
  id: string; lotId: string; purpose: string; radiusX: number; radiusZ: number;
  boundary: { from: SpatialPoint; to: SpatialPoint; heightMetres: 1 };
  props: Array<SpatialPoint & { id: string; mesh: 'SM_Barrel' | 'SM_Crate' | 'SM_Bench'; yaw: number; radius: number }>;
};
export type SunmeadowYards = { yards: TownYard[]; appearanceApproved: false; nativeIntegrated: false };

/** Separate working-yard study. The original town, routes and interaction identities remain immutable. */
export function sunmeadowYardPlan(zone: ZoneDefinition, town = sunmeadowStreetPlan(zone)): SunmeadowYards {
  if (zone.id !== 'sunmeadow_march' || town.zoneId !== zone.id) throw new Error('Sunmeadow yards require the regional town');
  const definitions: Array<[number, string, Array<['SM_Barrel' | 'SM_Crate' | 'SM_Bench', number, number, number]>]> = [
    [1, 'Household sitting and water-storage yard', [['SM_Bench', -2, 2, 90], ['SM_Barrel', -2, -2, 18]]],
    [9, 'Forge delivery and material-storage yard', [['SM_Crate', -2, -2, 12], ['SM_Crate', -2, -.6, -8], ['SM_Crate', -3, -1.4, 34], ['SM_Barrel', -2, 2, 21], ['SM_Barrel', -3, 2.2, 63]]],
    [14, 'Harvest sorting and requisition storage', [['SM_Crate', -2, -2, 4], ['SM_Crate', -3.2, -2, 19], ['SM_Crate', -2, -.6, -11], ['SM_Crate', -3.2, -.6, 28], ['SM_Barrel', -2, 2, 12], ['SM_Barrel', -3, 2.1, 42], ['SM_Barrel', -2.5, 3.2, 73]]],
    [10, 'Joinery storage and outdoor work rest', [['SM_Crate', 2, -2, -7], ['SM_Crate', 3.2, -2, 14], ['SM_Crate', 2.6, -.7, 31], ['SM_Bench', 2, 2, 90]]],
    [18, 'Stable feed and tack-storage court', [['SM_Barrel', 2, -2, 15], ['SM_Barrel', 3, -2.2, 72], ['SM_Crate', 2, 2, 8], ['SM_Crate', 3.3, 2, -12]]],
    [15, 'Warehouse loading and supply sorting', [['SM_Crate', 2, -2, 0], ['SM_Crate', 3.3, -2, 17], ['SM_Crate', 2, -.6, -13], ['SM_Crate', 3.3, -.6, 26], ['SM_Barrel', 2, 2, 30], ['SM_Barrel', 3, 2.2, 56]]],
  ];
  const yards = definitions.map(([index, purpose, props]) => {
    const lot = town.modules[index], direction = lot.x < zone.spawnPoint!.x ? -1 : 1;
    const sideYard = index === 10 || index === 18;
    const center = { x: sideYard ? lot.x : lot.x + direction * (index === 1 ? 22 : 16), z: lot.z + (sideYard ? 15 : 0) };
    const id = `${lot.id}_rear_yard`;
    return { ...center, id, lotId: lot.id, purpose, radiusX: 4.4, radiusZ: 5.2,
      boundary: { from: sideYard ? { x: center.x - 4, z: center.z + (index === 18 ? -6 : 6) } : { x: center.x + direction * 6, z: center.z - 4 },
        to: sideYard ? { x: center.x + 4, z: center.z + (index === 18 ? -6 : 6) } : { x: center.x + direction * 6, z: center.z + 4 }, heightMetres: 1 as const },
      props: props.map(([mesh, x, z, yaw], i) => ({ id: `${id}_${i}`, mesh, x: center.x + x, z: center.z + z, yaw, radius: mesh === 'SM_Bench' ? 1.7 : .65 })) };
  });
  const plan: SunmeadowYards = { yards, appearanceApproved: false, nativeIntegrated: false };
  validateSunmeadowYards(plan, zone, town);
  return plan;
}

export function validateSunmeadowYards(plan: SunmeadowYards, zone: ZoneDefinition, town: SunmeadowTownPlan): void {
  if (zone.id !== 'sunmeadow_march' || town.zoneId !== zone.id || plan.appearanceApproved !== false || plan.nativeIntegrated !== false || plan.yards.length !== 6) throw new Error('Yard study acceptance or count changed');
  const ids = new Set<string>(), spatial = resolveZoneSpatial(zone);
  const routes = [...(zone.paths ?? []), ...(zone.orvrLayout?.caravanRoutes ?? []), ...town.streets];
  for (const yard of plan.yards) {
    if (ids.has(yard.id) || !town.modules.some(m => m.id === yard.lotId) || !yard.purpose
      || !Number.isFinite(yard.x) || !Number.isFinite(yard.z) || yard.radiusX !== 4.4 || yard.radiusZ !== 5.2
      || !containsSpatialPoint(spatial, yard, Math.max(yard.radiusX, yard.radiusZ) * 1.35)) throw new Error('Invalid bounded town yard');
    ids.add(yard.id);
    const wall = yard.boundary;
    if (!wall || wall.heightMetres !== 1 || ![wall.from.x, wall.from.z, wall.to.x, wall.to.z].every(Number.isFinite)
      || Math.hypot(wall.to.x - wall.from.x, wall.to.z - wall.from.z) !== 8) throw new Error('Invalid bounded yard boundary');
    for (let i = 0; i <= 16; i++) {
      const p = { x: wall.from.x + (wall.to.x - wall.from.x) * i / 16, z: wall.from.z + (wall.to.z - wall.from.z) * i / 16 };
      if (!containsSpatialPoint(spatial, p, 1) || Math.hypot(p.x - yard.x, p.z - yard.z) > 8
        || town.modules.some(m => segmentCrossesModule(p, p, m, 1)
          || m.approach.some((a, j) => j > 0 && distanceToSpatialSegment(p, m.approach[j - 1], a) < 1.6))
        || routes.some(r => r.points.some((a, j) => j > 0 && distanceToSpatialSegment(p, r.points[j - 1], a) < r.width / 2 + 1))
        || town.serviceReservations.some(r => Math.hypot(p.x - r.point.x, p.z - r.point.z) < r.radius + 1)
        || Math.hypot(p.x - town.arrivalCourt.point.x, p.z - town.arrivalCourt.point.z) < town.arrivalCourt.radius + 1)
        throw new Error(`Yard boundary blocks retained circulation: ${yard.id} at ${p.x},${p.z}`);
    }
    for (const p of yard.props) {
      if (ids.has(p.id) || !['SM_Barrel', 'SM_Crate', 'SM_Bench'].includes(p.mesh)
        || ![p.x, p.z, p.yaw, p.radius].every(Number.isFinite) || p.radius !== (p.mesh === 'SM_Bench' ? 1.7 : .65)
        || Math.hypot((p.x - yard.x) / yard.radiusX, (p.z - yard.z) / yard.radiusZ) > 1
        || !containsSpatialPoint(spatial, p, p.radius + .6)) throw new Error('Invalid bounded yard prop');
      ids.add(p.id);
      if (town.modules.some(m => segmentCrossesModule(p, p, m, p.radius + .6)
        || m.approach.some((a, i) => i > 0 && distanceToSpatialSegment(p, m.approach[i - 1], a) < p.radius + 1.2))
        || routes.some(r => r.points.some((a, i) => i > 0 && distanceToSpatialSegment(p, r.points[i - 1], a) < r.width / 2 + p.radius + .6))
        || town.serviceReservations.some(s => Math.hypot(p.x - s.point.x, p.z - s.point.z) < s.radius + p.radius + .6)
        || Math.hypot(p.x - town.arrivalCourt.point.x, p.z - town.arrivalCourt.point.z) < town.arrivalCourt.radius + p.radius + .6)
        throw new Error(`Yard prop blocks retained circulation: ${p.id}`);
    }
  }
}


