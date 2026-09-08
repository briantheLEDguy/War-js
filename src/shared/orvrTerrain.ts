export interface TerrainPoint { x: number; z: number }

export interface OrvrTerrainControls {
  sourceVersion: string;
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
  for (const corridor of terrain.clearCorridors) {
    for (let index = 1; index < corridor.points.length; index += 1) {
      const candidate = flattenWeight(distanceToSegment(x, z, corridor.points[index - 1], corridor.points[index]), corridor.radius, corridor.feather);
      if (candidate > weight) { weight = candidate; target = corridor.height; }
    }
  }
  return height + (target - height) * weight;
}

/** Match the Float32 grid and bilinear grounding used by the transitional renderer. */
export function orvrGridHeightAt(terrain: OrvrTerrainControls, size: number, segments: number, x: number, z: number): number {
  return gridHeightAt(size, segments, x, z, (gx, gz) => Math.fround(orvrHeightAt(terrain,
    gx / segments * size - size / 2, gz / segments * size - size / 2)));
}

/** Lazily sample a fixed terrain revision; callers replace the sampler when its controls change. */
export function createOrvrGridHeightSampler(terrain: OrvrTerrainControls, size: number, segments: number): (x: number, z: number) => number {
  const vertices = new Map<number, number>();
  const at = (gx: number, gz: number): number => {
    const index = gz * (segments + 1) + gx;
    let height = vertices.get(index);
    if (height === undefined) {
      height = Math.fround(orvrHeightAt(terrain, gx / segments * size - size / 2, gz / segments * size - size / 2));
      vertices.set(index, height);
    }
    return height;
  };
  return (x, z) => gridHeightAt(size, segments, x, z, at);
}

function gridHeightAt(size: number, segments: number, x: number, z: number, at: (gx: number, gz: number) => number): number {
  if (!(size > 0) || !Number.isInteger(segments) || segments < 1 || !Number.isFinite(x) || !Number.isFinite(z)) return 0;
  const u = (x + size / 2) / size;
  const v = (z + size / 2) / size;
  if (u < 0 || u > 1 || v < 0 || v > 1) return 0;
  const fx = u * segments;
  const fz = v * segments;
  const ix = Math.floor(fx);
  const iz = Math.floor(fz);
  const nextX = Math.min(ix + 1, segments);
  const nextZ = Math.min(iz + 1, segments);
  const tx = fx - ix;
  const tz = fz - iz;
  const lower = at(ix, iz) * (1 - tx) + at(nextX, iz) * tx;
  const upper = at(ix, nextZ) * (1 - tx) + at(nextX, nextZ) * tx;
  return lower * (1 - tz) + upper * tz;
}
