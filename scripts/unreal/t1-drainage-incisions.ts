/** Isolated first-pair terrain authoring. Gameplay routes remain retained and independently checked. */
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { validateTerrainField } from '../../shared/terrainField';
import { battlefieldGrades } from './t1-battlefield-grades';
import { traceDrainage, type DrainageSeed } from './t1-drainage-trace';
import { validateT1 } from './t1-layouts';

export function drainageSeeds(id: string): DrainageSeed[] {
  const rows = id === 'sunmeadow_march'
    ? [[140,-115],[185,-115],[150,120],[-620,450],[-435,440],[-445,395],[-15,450],[50,420],[435,385],[-355,-520],[355,-500],[395,-460]]
    : id === 'cinderfen_outskirts'
      ? [[140,-205],[185,-210],[155,35],[-525,395],[-400,350],[-410,310],[-20,485],[10,435],[460,420],[485,350],[-355,-550],[255,-550]]
      : undefined;
  if (!rows) throw new Error('Drainage authoring requires a first-pair region');
  return rows.map(([x,z],i) => ({ id: id + '_drainage_' + i, x, z, depth: i < 3 ? 3.6 : id === 'sunmeadow_march' ? 14 : 18,
    width: i < 3 ? 24 : 22, maximumLength: i < 3 ? 160 : 320 }));
}

export function drainageIncisions(original: ZoneDefinition) {
  if (!original.spatial || !original.paths || !original.orvrLayout?.terrain.naturalField) throw new Error('Drainage authoring requires explicit terrain');
  const zone = structuredClone(original), terrain = zone.orvrLayout!.terrain, bounds = zone.spatial!.bounds;
  if (terrain.naturalField!.incisions?.length) throw new Error('Preserve existing terrain incision revision');
  const before = createOrvrGridHeightSampler(original.orvrLayout.terrain, zone.size, zone.segments, zone.spatial);
  const courses: NonNullable<ReturnType<typeof traceDrainage>>[] = [], rejectedSeeds: string[] = [];
  for (const seed of drainageSeeds(zone.id)) {
    const row = traceDrainage(seed, before, (x,z,r) => x-r >= bounds.minX && x+r <= bounds.maxX && z-r >= bounds.minZ && z+r <= bounds.maxZ);
    if (row) courses.push(row); else rejectedSeeds.push(seed.id);
  }
  if (!courses.length) throw new Error('No bounded downhill incision courses');
  terrain.naturalField!.incisions = courses.map(row => ({ id: row.id, points: row.points }));
  validateTerrainField(terrain.naturalField!);
  const height = createOrvrGridHeightSampler(terrain, zone.size, zone.segments, zone.spatial);
  const flowChecks = courses.map(row => {
    let previous = height(row.points[0].x, row.points[0].z), maximumRise = 0;
    for (let i = 1; i < row.points.length; i++) {
      const a = row.points[i-1], b = row.points[i];
      for (let j = 1; j <= 8; j++) {
        const y = height(a.x+(b.x-a.x)*j/8, a.z+(b.z-a.z)*j/8);
        maximumRise = Math.max(maximumRise, y-previous); previous = y;
      }
    }
    // Native grid interpolation and intersecting cuts retain small rough steps, never large uphill trenches.
    if (maximumRise > .35) throw new Error('Incision course has an excessive sampled uphill step');
    return { id: row.id, length: row.length, sourceDrop: row.sourceDrop, maximumCentrelineRisePerMetre: maximumRise };
  });
  const anchors = [...zone.orvrLayout!.keeps, ...zone.orvrLayout!.battlefieldObjectives, ...zone.orvrLayout!.stagingCamps,
    ...(zone.spawnPoint ? [zone.spawnPoint] : []), ...(zone.zoneTriggers ?? []).flatMap(t => t.arrivalPoint ? [t,t.arrivalPoint] : [t])];
  if (anchors.some(p => Math.abs(height(p.x,p.z)-before(p.x,p.z)) > .01)) throw new Error('Incisions move a retained gameplay anchor');
  const ids = new Set(zone.paths!.map(p => p.id));
  const grades = battlefieldGrades([...zone.paths!, ...zone.orvrLayout!.caravanRoutes,
    ...terrain.clearCorridors.filter(c => !ids.has(c.id)).map(c => ({ id:c.id, points:c.points, width:c.id.includes('_pocket_') ? 6 : 12 }))],height);
  if (grades.some(g => g.maximumGrade > .22)) throw new Error('Incisions exceed retained full-width route grades');
  for (const prop of zone.props ?? []) if (prop.heightMode === 'absolute') prop.y = (prop.y ?? 0) + height(prop.x,prop.z)-before(prop.x,prop.z);
  terrain.sourceVersion = 't1-drainage-incisions-v1'; zone.orvrLayout!.version = terrain.sourceVersion;
  validateT1(zone);
  return { zone, flowChecks, rejectedSeeds, grades, nativeBuilt:false, appearanceApproved:false, drivingAccepted:false };
}
