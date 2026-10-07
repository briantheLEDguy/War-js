export interface SpatialPoint { x: number; z: number }
export interface SpatialBounds { minX: number; maxX: number; minZ: number; maxZ: number }
/** Content ownership includes backdrop scenery; the outline limits playable destinations. */
export interface ZoneSpatial {
  bounds: SpatialBounds;
  playableOutline: SpatialPoint[];
  terrainGrid: { segmentsX: number; segmentsZ: number };
}
export interface SpatialZone { size: number; segments: number; spatial?: ZoneSpatial }

export function containsZoneDestination(zone: { bounds: SpatialBounds; spatial?: ZoneSpatial }, p: SpatialPoint, margin = .5): boolean {
  const b = zone.bounds;
  return zone.spatial ? containsSpatialPoint(zone.spatial, p, margin) : finite(p.x) && finite(p.z)
    && p.x >= b.minX + margin && p.x <= b.maxX - margin && p.z >= b.minZ + margin && p.z <= b.maxZ - margin;
}

const finite = Number.isFinite;
const cross = (a: SpatialPoint, b: SpatialPoint, c: SpatialPoint) =>
  (b.x - a.x) * (c.z - a.z) - (b.z - a.z) * (c.x - a.x);

export function distanceToSpatialSegment(p: SpatialPoint, a: SpatialPoint, b: SpatialPoint): number {
  const dx = b.x - a.x, dz = b.z - a.z, length = dx * dx + dz * dz;
  const t = length ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.z - a.z) * dz) / length)) : 0;
  return Math.hypot(p.x - a.x - t * dx, p.z - a.z - t * dz);
}

export function containsSpatialPoint(spatial: Pick<ZoneSpatial, 'bounds' | 'playableOutline'>,
  p: SpatialPoint, margin = 0, playable = true): boolean {
  const b = spatial.bounds;
  if (!finite(p.x) || !finite(p.z) || !finite(margin) || margin < 0
    || p.x < b.minX + margin || p.x > b.maxX - margin || p.z < b.minZ + margin || p.z > b.maxZ - margin) return false;
  if (!playable) return true;
  const outline = spatial.playableOutline;
  let inside = false;
  for (let i = 0, j = outline.length - 1;i < outline.length;j = i++) {
    const a = outline[j], c = outline[i], distance = distanceToSpatialSegment(p, a, c);
    if (distance < margin - 1e-7) return false;
    if (distance < 1e-7) return margin === 0;
    if ((a.z > p.z) !== (c.z > p.z) && p.x < (c.x - a.x) * (p.z - a.z) / (c.z - a.z) + a.x) inside = !inside;
  }
  return inside;
}

export function resolveZoneSpatial(zone: SpatialZone): ZoneSpatial {
  const half = zone.size / 2;
  const spatial = zone.spatial ?? {
    bounds: { minX: -half, maxX: half, minZ: -half, maxZ: half },
    playableOutline: [{ x: -half, z: -half }, { x: half, z: -half }, { x: half, z: half }, { x: -half, z: half }],
    terrainGrid: { segmentsX: zone.segments, segmentsZ: zone.segments },
  };
  const b = spatial.bounds, g = spatial.terrainGrid, points = spatial.playableOutline;
  if (!b || !Object.values(b).every(finite) || b.minX >= b.maxX || b.minZ >= b.maxZ
    || !g || ![g.segmentsX, g.segmentsZ].every(n => Number.isInteger(n) && n > 0 && n <= 512)
    || !Array.isArray(points) || points.length < 3 || points.length > 256
    || points.some(p => !p || !containsSpatialPoint(spatial, p, 0, false))) throw new Error('Invalid zone spatial definition');
  let area = 0;
  for (let i = 0;i < points.length;i++) {
    const a = points[i], c = points[(i + 1) % points.length];
    if (Math.hypot(c.x - a.x, c.z - a.z) < 1e-6) throw new Error('Duplicate spatial outline vertex');
    area += a.x * c.z - c.x * a.z;
    for (let j = i + 2;j < points.length;j++) {
      if (i === 0 && j === points.length - 1) continue;
      const d = points[j], e = points[(j + 1) % points.length];
      if ((cross(a, c, d) * cross(a, c, e) < 0 && cross(d, e, a) * cross(d, e, c) < 0)
        || distanceToSpatialSegment(d, a, c) < 1e-7 || distanceToSpatialSegment(e, a, c) < 1e-7
        || distanceToSpatialSegment(a, d, e) < 1e-7 || distanceToSpatialSegment(c, d, e) < 1e-7)
        throw new Error('Self-intersecting spatial outline');
    }
  }
  if (Math.abs(area) < 1e-6) throw new Error('Empty spatial outline');
  return spatial;
}

/** Endpoints alone cannot validate an arrival corridor across a concave boundary. */
export function spatialSegmentInside(spatial: ZoneSpatial, a: SpatialPoint, b: SpatialPoint, margin = 0): boolean {
  if (!containsSpatialPoint(spatial, a, margin) || !containsSpatialPoint(spatial, b, margin)) return false;
  const dx = b.x - a.x, dz = b.z - a.z, cuts = [0, 1];
  for (let i = 0;i < spatial.playableOutline.length;i++) {
    const c = spatial.playableOutline[i], d = spatial.playableOutline[(i + 1) % spatial.playableOutline.length];
    const ex = d.x - c.x, ez = d.z - c.z, denominator = dx * ez - dz * ex;
    if (Math.abs(denominator) < 1e-9) continue;
    const t = ((c.x - a.x) * ez - (c.z - a.z) * ex) / denominator;
    const u = ((c.x - a.x) * dz - (c.z - a.z) * dx) / denominator;
    if (t > 0 && t < 1 && u >= 0 && u <= 1) cuts.push(t);
  }
  cuts.sort((x, y) => x - y);
  return cuts.slice(1).every((t, i) => containsSpatialPoint(spatial,
    { x: a.x + dx * (t + cuts[i]) / 2, z: a.z + dz * (t + cuts[i]) / 2 }, margin))
    && spatial.playableOutline.every((p, i) => margin === 0
      || Math.min(distanceToSpatialSegment(p, a, b), distanceToSpatialSegment(a, p, spatial.playableOutline[(i + 1) % spatial.playableOutline.length]),
        distanceToSpatialSegment(b, p, spatial.playableOutline[(i + 1) % spatial.playableOutline.length])) >= margin - 1e-7);
}
