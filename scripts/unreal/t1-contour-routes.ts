/** Bounded contour searches author walking counters without changing the sampled ground. */
import { battlefieldGrades, type GradeRoute } from './t1-battlefield-grades';
import type { SpatialPoint } from '../../shared/worldSpatial';

export interface ContourSearch {
  id: string;
  bounds: { minX: number; maxX: number; minZ: number; maxZ: number };
  starts: SpatialPoint[];
  target: SpatialPoint;
  targetRadius: number;
  minimumRise: number;
  width: number;
  step: number;
  maximumGrade: number;
}

export function maximumContourGrade(height: (x: number, z: number) => number, p: SpatialPoint): number {
    let maximum = 0;
    // A centred derivative averages adjacent faces at grid/diagonal boundaries.
    // Inspect nearby faces too, matching native collision normals conservatively.
    for (const dx of [-.12, 0, .12]) for (const dz of [-.12, 0, .12]) {
      const x = p.x + dx, z = p.z + dz;
      const gx = (height(x + .05, z) - height(x - .05, z)) / .1;
      const gz = (height(x, z + .05) - height(x, z - .05)) / .1;
      if (!Number.isFinite(gx) || !Number.isFinite(gz)) throw new Error('Nonfinite contour ground');
      maximum = Math.max(maximum, Math.hypot(gx, gz));
    }
    return maximum;
}

export function contourRoutes(recipe: ContourSearch, height: (x: number, z: number) => number,
  admitted: (point: SpatialPoint, radius: number) => boolean) {
  const b = recipe.bounds;
  const finite = [b.minX, b.maxX, b.minZ, b.maxZ, recipe.target.x, recipe.target.z,
    recipe.targetRadius, recipe.minimumRise, recipe.width, recipe.step, recipe.maximumGrade,
    ...recipe.starts.flatMap(p => [p.x, p.z])].every(Number.isFinite);
  const nx = Math.floor((b.maxX - b.minX) / recipe.step) + 1;
  const nz = Math.floor((b.maxZ - b.minZ) / recipe.step) + 1;
  if (!finite || !recipe.id || b.maxX <= b.minX || b.maxZ <= b.minZ || recipe.starts.length !== 2
    || recipe.width < 2 || recipe.width > 6 || recipe.step < 2 || recipe.step > 6
    || recipe.targetRadius < 8 || recipe.targetRadius > 60 || recipe.minimumRise < 0 || recipe.minimumRise > 30
    || recipe.maximumGrade < .05 || recipe.maximumGrade > .22 || nx * nz > 20000) {
    throw new Error('Invalid bounded contour search');
  }
  const position = (i: number): SpatialPoint => ({ x: b.minX + i % nx * recipe.step, z: b.minZ + Math.floor(i / nx) * recipe.step });
  const grade = (p: SpatialPoint) => maximumContourGrade(height, p);
  const walkable = Array.from({ length: nx * nz }, (_, i) => {
    const p = position(i), radius = recipe.width / 2;
    return admitted(p, radius + 1) && [-radius, 0, radius].every(dx => [-radius, 0, radius].every(dz =>
      grade({ x: p.x + dx, z: p.z + dz }) <= recipe.maximumGrade));
  });
  const segmentClear = (a: SpatialPoint, b: SpatialPoint) => {
    const length = Math.hypot(b.x - a.x, b.z - a.z), count = Math.ceil(length / 2);
    if (length < .001) return true;
    let previous = height(a.x, a.z);
    for (let i = 0; i <= count; i++) {
      const p = { x: a.x + (b.x - a.x) * i / count, z: a.z + (b.z - a.z) * i / count };
      const y = height(p.x, p.z);
      if (!Number.isFinite(y)) throw new Error('Nonfinite contour footing');
      if (!admitted(p, recipe.width / 2 + 1) || i && Math.abs(y - previous) / (length / count) > recipe.maximumGrade) return false;
      const sideX = -(b.z - a.z) / length, sideZ = (b.x - a.x) / length;
      for (const side of [-recipe.width / 2, 0, recipe.width / 2]) {
        if (grade({ x: p.x + sideX * side, z: p.z + sideZ * side }) > recipe.maximumGrade) return false;
      }
      previous = y;
    }
    return battlefieldGrades([{ width: recipe.width, points: [a, b] }], height)[0].maximumGrade <= recipe.maximumGrade;
  };
  const nearest = (start: SpatialPoint) => {
    const options = walkable.flatMap((yes, i) => yes ? [{ i, distance: Math.hypot(position(i).x - start.x, position(i).z - start.z) }] : [])
      .filter(p => p.distance <= recipe.step * 2).sort((a, b) => a.distance - b.distance || a.i - b.i);
    const chosen = options.find(p => segmentClear(start, position(p.i)));
    if (!chosen) throw new Error('No grounded contour start: ' + recipe.id);
    return chosen.i;
  };
  const searches = recipe.starts.map(start => {
    const root = nearest(start), visited = new Map<number, number | null>([[root, null]]), queue = [root];
    for (let j = 0; j < queue.length; j++) {
      const i = queue[j], x = i % nx, z = Math.floor(i / nx);
      for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, 1], [1, -1], [-1, -1]]) {
        const xx = x + dx, zz = z + dz, next = zz * nx + xx;
        if (xx < 0 || xx >= nx || zz < 0 || zz >= nz || !walkable[next] || visited.has(next)) continue;
        if (dx && dz && (!walkable[z * nx + xx] || !walkable[zz * nx + x])) continue;
        if (!segmentClear(position(i), position(next))) continue;
        visited.set(next, i); queue.push(next);
      }
    }
    return visited;
  });
  const minimum = Math.max(...recipe.starts.map(p => height(p.x, p.z))) + recipe.minimumRise;
  const goals = walkable.flatMap((yes, i) => {
    const p = position(i), y = height(p.x, p.z);
    return yes && searches.every(s => s.has(i)) && Math.hypot(p.x - recipe.target.x, p.z - recipe.target.z) <= recipe.targetRadius
      && y >= minimum ? [{ i, ...p, y }] : [];
  }).sort((a, b) => b.y - a.y || a.i - b.i);
  if (!goals.length) throw new Error('No shared reachable contour overlook: ' + recipe.id);
  const goal = goals[0];
  const routes: GradeRoute[] = searches.map((search, index) => {
    const reversed: SpatialPoint[] = []; let i: number | null = goal.i;
    while (i !== null) { reversed.push(position(i)); i = search.get(i)!; }
    const raw = [recipe.starts[index], ...reversed.reverse()].filter((p, j, all) => !j || Math.hypot(p.x - all[j - 1].x, p.z - all[j - 1].z) > .001);
    if (raw.length > 512) throw new Error('Contour counter exceeds its bounded authoring length');
    const points = [raw[0]];
    for (let cursor = 0; cursor < raw.length - 1;) {
      let next = raw.length - 1;
      while (next > cursor + 1 && !segmentClear(raw[cursor], raw[next])) next--;
      points.push(raw[next]); cursor = next;
    }
    return { id: recipe.id + '_counter_' + index, width: recipe.width,
      points: points.map(p => ({ ...p, y: height(p.x, p.z) })) };
  });
  const grades = battlefieldGrades(routes, height);
  if (grades.some(g => g.maximumGrade > recipe.maximumGrade)) throw new Error('Smoothed contour route grade failed');
  return { goal: { x: goal.x, z: goal.z, y: goal.y }, routes, grades, terrainChanged: false };
}
