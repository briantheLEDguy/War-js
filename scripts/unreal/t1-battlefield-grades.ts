import type { TerrainPoint } from '../../shared/orvrTerrain';

export interface GradeRoute { id?: string; width: number; points: TerrainPoint[] }
/** Check local surface slope in both directions, including lane edges and the centres of turns. */
export function battlefieldGrades(paths: GradeRoute[], height: (x: number, z: number) => number) {
  return paths.map(path => {
    if (!Number.isFinite(path.width) || path.width <= 0 || path.points.length < 2) throw new Error('Invalid graded route');
    let maximumGrade = 0, maximumLongitudinalGrade = 0, maximumCrossGrade = 0, samples = 0;
    let worstLocation: { x: number; z: number } | undefined;
    for (let i = 1; i < path.points.length; i++) {
      const a = path.points[i - 1], b = path.points[i], dx = b.x - a.x, dz = b.z - a.z, length = Math.hypot(dx, dz);
      if (!Number.isFinite(length) || length <= .001) throw new Error('Invalid graded segment');
      const steps = Math.ceil(length / 2), lanes = Math.ceil(path.width / 2);
      for (let lane = 0; lane <= lanes; lane++) for (let j = 0; j <= steps; j++) {
        const side = -path.width / 2 + lane / lanes * path.width;
        const x = a.x + dx * j / steps - dz / length * side, z = a.z + dz * j / steps + dx / length * side;
        const gx = (height(x + .05, z) - height(x - .05, z)) / .1;
        const gz = (height(x, z + .05) - height(x, z - .05)) / .1;
        if (!Number.isFinite(gx) || !Number.isFinite(gz)) throw new Error('Invalid graded surface');
        if (Math.hypot(gx, gz) > maximumGrade) { maximumGrade = Math.hypot(gx, gz); worstLocation = { x, z }; }
        maximumLongitudinalGrade = Math.max(maximumLongitudinalGrade, Math.abs(gx * dx / length + gz * dz / length));
        maximumCrossGrade = Math.max(maximumCrossGrade, Math.abs(-gx * dz / length + gz * dx / length)); samples++;
      }
    }
    return { id: path.id, maximumGrade, maximumLongitudinalGrade, maximumCrossGrade, worstLocation, samples };
  });
}
