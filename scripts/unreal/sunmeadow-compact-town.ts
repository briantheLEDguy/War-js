import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { moduleLocalPoint, segmentCrossesModule } from './t1-modules';
import { connectVillageStreets } from './village-street-connections';
import { sunmeadowStreetPlan, validateSunmeadowTown, type SunmeadowTownPlan } from './sunmeadow-town-plan';

/** A separate compact-frontage candidate; back lots, interaction points and streets remain retained. */
export function compactSunmeadowTown(zone: ZoneDefinition, original = sunmeadowStreetPlan(zone)): SunmeadowTownPlan {
  if (zone.id !== 'sunmeadow_march' || original.zoneId !== zone.id || !zone.spawnPoint) throw new Error('Compact frontage requires Sunmeadow');
  const plan = structuredClone(original), root = zone.spawnPoint;
  const changes: Array<[number, number, number]> = [[0, -18, -83], [11, -18, -63], [6, -18, -43],
    [7, -18, 25], [12, -18, 50], [17, -18, 75], [13, 18, -70]];
  for (const [index, x, z] of changes) {
    const lot = plan.modules[index]; lot.x = root.x + x; lot.z = root.z + z;
    lot.entry = moduleLocalPoint(lot, { x: 0, z: -10 });
    if (lot.practical) Object.assign(lot.practical, moduleLocalPoint(lot, { x: 2, z: -8 }));
  }
  plan.layout = 'Close Main Street frontages, market green, rear working lanes and attached garrison court';
  connectVillageStreets(plan, zone);
  validateSunmeadowTown(plan, zone);
  for (const route of [...(zone.paths ?? []), ...(zone.orvrLayout?.caravanRoutes ?? [])]) {
    for (let i = 1; i < route.points.length; i++) if (plan.modules.some(m => segmentCrossesModule(route.points[i - 1], route.points[i], m, route.width / 2 + .6)))
      throw new Error(`Compact frontage blocks retained route: ${route.id}`);
  }
  return plan;
}
