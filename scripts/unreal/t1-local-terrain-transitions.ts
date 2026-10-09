/** Source-only local terrain studies. New native geometry needs its own complete verification chain. */
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { battlefieldGrades } from './t1-battlefield-grades';
import { validateT1 } from './t1-layouts';

export function localTerrainTransitions(original: ZoneDefinition) {
  const feather = original.id === 'sunmeadow_march' ? 52 : original.id === 'cinderfen_outskirts' ? 48 : undefined;
  if (!feather || !original.spatial || !original.orvrLayout?.terrain.naturalField || !original.paths) {
    throw new Error('Local terrain transitions require a first-pair battlefield source');
  }
  const zone = structuredClone(original), terrain = zone.orvrLayout!.terrain;
  const before = createOrvrGridHeightSampler(original.orvrLayout.terrain, original.size, original.segments, original.spatial);
  const changes: Array<{ id: string; from: number; to: number }> = [];
  for (const corridor of terrain.clearCorridors) {
    // The main advance and first rotation retain the broader blending support
    // required by their crossing elevations. Home/pocket/side-climb recipes stay exact.
    if (corridor.feather === 72 && !corridor.id.endsWith('_advance') && !corridor.id.endsWith('_rotation_1')) {
      changes.push({ id: corridor.id, from: corridor.feather, to: feather });
      corridor.feather = feather;
    }
  }
  if (!changes.length) throw new Error('No retained transition bands are eligible');
  const height = createOrvrGridHeightSampler(terrain, zone.size, zone.segments, zone.spatial);
  // Keep complete military assemblies anchored to their existing level pads.
  for (const anchor of [...zone.orvrLayout!.keeps, ...zone.orvrLayout!.battlefieldObjectives, ...zone.orvrLayout!.stagingCamps]) {
    if (Math.abs(height(anchor.x, anchor.z) - before(anchor.x, anchor.z)) > .01) throw new Error('Local transitions move a military assembly pad');
  }
  for (const prop of zone.props ?? []) if (prop.heightMode === 'absolute') prop.y = (prop.y ?? 0) + height(prop.x, prop.z) - before(prop.x, prop.z);
  if (zone.spawnPoint) zone.spawnPoint.y = height(zone.spawnPoint.x, zone.spawnPoint.z);
  for (const trigger of zone.zoneTriggers ?? []) {
    trigger.y = height(trigger.x, trigger.z);
    if (trigger.arrivalPoint) trigger.arrivalPoint.y = height(trigger.arrivalPoint.x, trigger.arrivalPoint.z);
  }
  const ids = new Set(zone.paths!.map(path => path.id));
  const routes = [...zone.paths!, ...zone.orvrLayout!.caravanRoutes,
    ...terrain.clearCorridors.filter(c => !ids.has(c.id)).map(c => ({ id: c.id, points: c.points, width: c.id.includes('_pocket_') ? 6 : 12 }))];
  const grades = battlefieldGrades(routes, height);
  if (grades.some(g => g.maximumGrade > .22)) throw new Error('Local transitions exceed the retained full-width grade limit');
  terrain.sourceVersion = 't1-local-terrain-transitions-v1'; zone.orvrLayout!.version = terrain.sourceVersion;
  validateT1(zone);
  return { zone, changes, grades, nativeBuilt: false, appearanceApproved: false, drivingAccepted: false };
}
