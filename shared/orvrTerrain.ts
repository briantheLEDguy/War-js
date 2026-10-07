import { resolveZoneSpatial, type ZoneSpatial } from './worldSpatial';
export interface TerrainPoint { x: number; z: number; y?: number }

export interface OrvrTerrainControls {
  sourceVersion: string;
  /** Graded route graphs blend overlapping supports continuously; legacy authored surfaces retain priority selection. */
  gradedRoutes?: boolean;
  landforms: Array<TerrainPoint & {
    id: string;
    kind: 'ridge' | 'basin' | 'terrace';
    radiusX: number;
    radiusZ: number;
    height: number;
  }>;
  flattenAreas: Array<TerrainPoint & { id: string; radius: number; height: number; feather: number }>;
  clearCorridors: Array<{
    id: string;
    points: TerrainPoint[];
    radius: number;
    height: number;
    feather: number;
  }>;
}

function distanceToSegment(x: number, z: number, a: TerrainPoint, b: TerrainPoint): number {
  const dx = b.x - a.x;
  const dz = b.z - a.z;
  const squareLength = dx * dx + dz * dz;
  const t = squareLength ? Math.max(0, Math.min(1, ((x - a.x) * dx + (z - a.z) * dz) / squareLength)) : 0;
  return Math.hypot(x - a.x - t * dx, z - a.z - t * dz);
}

function flattenWeight(distance: number, radius: number, feather: number): number {
  if (distance <= radius) return 1;
  if (feather <= 0 || distance >= radius + feather) return 0;
  const t = (distance - radius) / feather;
  return 1 - t * t * (3 - 2 * t);
}

/** Pure source-surface evaluation shared by the client and authoritative server. */
export function orvrHeightAt(terrain: OrvrTerrainControls, x: number, z: number): number {
  if (!Number.isFinite(x) || !Number.isFinite(z)) return 0;
  let height = 0;
  for (const landform of terrain.landforms) {
    const d2 = ((x - landform.x) / landform.radiusX) ** 2 + ((z - landform.z) / landform.radiusZ) ** 2;
    if (d2 < 1) height += landform.height * (1 - d2) ** 2;
  }
  let weight = 0;
  let target = 0;
  for (const area of terrain.flattenAreas) {
    const candidate = flattenWeight(Math.hypot(x - area.x, z - area.z), area.radius, area.feather);
    if (candidate > weight) { weight = candidate; target = area.height; }
  }
  let corridorWeight = 0, corridorTotal = 0, corridorTarget = 0;
  for (const corridor of terrain.clearCorridors) {
    for (let index = 1; index < corridor.points.length; index += 1) {
      const candidate = flattenWeight(distanceToSegment(x, z, corridor.points[index - 1], corridor.points[index]), corridor.radius, corridor.feather);
      if (candidate > 0 && (terrain.gradedRoutes || candidate > weight)) {
        const a = corridor.points[index - 1], b = corridor.points[index], dx = b.x - a.x, dz = b.z - a.z;
        const length = dx * dx + dz * dz;
        const t = length ? Math.max(0, Math.min(1, ((x - a.x) * dx + (z - a.z) * dz) / length)) : 0;
        const elevation = a.y === undefined || b.y === undefined ? corridor.height : a.y + (b.y - a.y) * t;
        if (terrain.gradedRoutes) {
          corridorWeight = Math.max(corridorWeight, candidate);
          const influence = candidate ** 4;
          corridorTotal += influence; corridorTarget += influence * elevation;
        } else { weight = candidate; target = elevation; }
      }
    }
  }
  const supported = height + (target - height) * weight;
  return corridorTotal ? supported + (corridorTarget / corridorTotal - supported) * corridorWeight : supported;
}

/** Explicit spatial grids match native triangles; untouched grids retain legacy bilinear grounding. */
export function orvrGridHeightAt(terrain: OrvrTerrainControls, size: number, segments: number, x: number, z: number, spatial?: ZoneSpatial): number {
  return createOrvrGridHeightSampler(terrain, size, segments, spatial)(x, z);
}

/** Lazily sample a fixed terrain revision; callers replace the sampler when its controls change. */
export function createOrvrGridHeightSampler(terrain: OrvrTerrainControls, size: number, segments: number, spatial?: ZoneSpatial): (x: number, z: number) => number {
  if (!spatial && (!Number.isFinite(size) || size <= 0 || !Number.isInteger(segments) || segments < 1)) return () => 0;
  const grid = resolveZoneSpatial({ size, segments, spatial });
  const { bounds: b, terrainGrid: g } = grid;
  const vertices = new Map<number, number>();
  const at = (gx: number, gz: number): number => {
    const index = gz * (g.segmentsX + 1) + gx;
    let height = vertices.get(index);
    if (height === undefined) {
      height = Math.fround(orvrHeightAt(terrain, b.minX + gx / g.segmentsX * (b.maxX - b.minX), b.minZ + gz / g.segmentsZ * (b.maxZ - b.minZ)));
      vertices.set(index, height);
    }
    return height;
  };
  return (x, z) => gridHeightAt(grid, x, z, at, !!spatial);
}

function gridHeightAt(spatial: ZoneSpatial, x: number, z: number, at: (gx: number, gz: number) => number, triangles: boolean): number {
  if (!Number.isFinite(x) || !Number.isFinite(z)) return 0;
  const b = spatial.bounds, g = spatial.terrainGrid;
  const u = (x - b.minX) / (b.maxX - b.minX);
  const v = (z - b.minZ) / (b.maxZ - b.minZ);
  if (u < 0 || u > 1 || v < 0 || v > 1) return 0;
  const fx = u * g.segmentsX;
  const fz = v * g.segmentsZ;
  const ix = Math.floor(fx);
  const iz = Math.floor(fz);
  const nextX = Math.min(ix + 1, g.segmentsX);
  const nextZ = Math.min(iz + 1, g.segmentsZ);
  const tx = fx - ix;
  const tz = fz - iz;
  if (triangles) return tx + tz <= 1 ? at(ix, iz) + tx * (at(nextX, iz) - at(ix, iz)) + tz * (at(ix, nextZ) - at(ix, iz))
    : at(nextX, nextZ) + (1 - tx) * (at(ix, nextZ) - at(nextX, nextZ)) + (1 - tz) * (at(nextX, iz) - at(nextX, nextZ));
  const lower = at(ix, iz) * (1 - tx) + at(nextX, iz) * tx;
  const upper = at(ix, nextZ) * (1 - tx) + at(nextX, nextZ) * tx;
  return lower * (1 - tz) + upper * tz;
}
