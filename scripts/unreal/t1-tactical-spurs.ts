/** Tactical spurs and pedestrian counters remain isolated authoring candidates until fresh native proof. */
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { containsSpatialPoint } from '../../shared/worldSpatial';
import { validateTerrainField, type TerrainField } from '../../shared/terrainField';
import { contourRoutes, type ContourSearch } from './t1-contour-routes';
import { battlefieldGrades } from './t1-battlefield-grades';
import { validateT1 } from './t1-layouts';

export function tacticalSpurRecipes(id: string) {
  const sun = id === 'sunmeadow_march';
  if (!sun && id !== 'cinderfen_outskirts') throw new Error('Tactical spurs require a first-pair region');
  const ribbons: TerrainField['ridges'] = (sun ? [
    { id: 'western_barrow_spur', profile: 'rounded', rows: [[-310, 110, 65, 45], [-245, 50, 38, 52], [-205, 10, 30, 40]] },
    { id: 'eastern_field_shoulder', profile: 'rounded', rows: [[245, -280, 95, 32], [210, -170, 58, 29], [180, -90, 32, 32]] },
  ] : [
    { id: 'western_fault_toe', profile: 'shelf', rows: [[-285, 40, 65, 44], [-235, -55, 40, 48], [-210, -115, 29, 39]] },
    { id: 'eastern_dyke_spur', profile: 'rounded', rows: [[200, -430, 85, 37], [175, -300, 55, 35], [140, -205, 32, 40]] },
  ]).map(r => ({ id: r.id, profile: r.profile as 'rounded' | 'shelf', points: r.rows.map(([x, z, width, height]) => ({ x, z, width, height: height * .75 })) }));
  const searches: ContourSearch[] = [{ id: id + '_western_spur', bounds: sun
    ? { minX: -380, maxX: -120, minZ: -120, maxZ: 210 }
    : { minX: -380, maxX: -120, minZ: -240, maxZ: 110 },
    starts: sun ? [{ x: -310, z: 130 }, { x: -280, z: -70 }] : [{ x: -300, z: 20 }, { x: -280, z: -190 }],
    target: sun ? { x: -245, z: 50 } : { x: -235, z: -55 }, targetRadius: 45, minimumRise: 3, width: 4, step: 4, maximumGrade: .215 }];
  return { ribbons, searches };
}

export function tacticalSpurs(original: ZoneDefinition) {
  if (!original.spatial || !original.paths || !original.orvrLayout?.terrain.naturalField) throw new Error('Tactical spurs require explicit terrain and routes');
  const zone = structuredClone(original), terrain = zone.orvrLayout!.terrain;
  const before = createOrvrGridHeightSampler(original.orvrLayout.terrain, original.size, original.segments, original.spatial);
  const recipes = tacticalSpurRecipes(zone.id);
  if (recipes.ribbons.some(r => terrain.naturalField!.ridges.some(p => p.id === r.id))) throw new Error('Preserve existing tactical spur revision');
  terrain.naturalField!.ridges.push(...recipes.ribbons); validateTerrainField(terrain.naturalField!);
  const height = createOrvrGridHeightSampler(terrain, zone.size, zone.segments, zone.spatial);
  for (const anchor of [...zone.orvrLayout!.keeps, ...zone.orvrLayout!.battlefieldObjectives, ...zone.orvrLayout!.stagingCamps]) {
    if (Math.abs(height(anchor.x, anchor.z) - before(anchor.x, anchor.z)) > .01) throw new Error('Tactical spur moves a complete military assembly');
  }
  const counters = recipes.searches.map(recipe => contourRoutes(recipe, height, (p, radius) => containsSpatialPoint(zone.spatial!, p, radius)));
  for (const counter of counters) for (const route of counter.routes) zone.paths!.push({ ...route, id: route.id!, style: 'dirt_trail' });
  const ids = new Set(zone.paths!.map(p => p.id));
  const grades = battlefieldGrades([...zone.paths!, ...zone.orvrLayout!.caravanRoutes,
    ...terrain.clearCorridors.filter(c => !ids.has(c.id)).map(c => ({ id: c.id, points: c.points, width: c.id.includes('_pocket_') ? 6 : 12 }))], height);
  if (grades.some(g => g.maximumGrade > .22)) throw new Error('Tactical spurs exceed full-width route grade limits');
  for (const prop of zone.props ?? []) if (prop.heightMode === 'absolute') prop.y = (prop.y ?? 0) + height(prop.x, prop.z) - before(prop.x, prop.z);
  if (zone.spawnPoint) zone.spawnPoint.y = height(zone.spawnPoint.x, zone.spawnPoint.z);
  for (const trigger of zone.zoneTriggers ?? []) {
    trigger.y = height(trigger.x, trigger.z);
    if (trigger.arrivalPoint) trigger.arrivalPoint.y = height(trigger.arrivalPoint.x, trigger.arrivalPoint.z);
  }
  terrain.sourceVersion = 't1-tactical-spurs-v1'; zone.orvrLayout!.version = terrain.sourceVersion;
  validateT1(zone);
  return { zone, ribbons: recipes.ribbons, counters, grades, nativeBuilt: false, appearanceApproved: false, drivingAccepted: false };
}
