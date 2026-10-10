import { terrainSurfaceHeight, validateTerrainSurface, type TerrainSurface } from './terrainSurface';
import { sampleTerrainRelief, validateTerrainRelief, type TerrainRelief } from './terrainRelief';

/** Serializable metre-space landforms. Native meshes and Node grounding evaluate the same field. */
export interface TerrainField {
  version: 1;
  baseHeight: number;
  seed: number;
  /** Bounded authored weathering; absent recipes preserve their original field exactly. */
  weathering?: { warpMetres: number; warpScale: number; detailScale: number; detailAmplitude: number; terraceHeight: number; terraceStrength: number };
  /** Optional private source-derived relief; evaluated before graded routes and footing supports. */
  relief?: TerrainRelief;
  /** Optional absolute source-derived landform, applied before route and footing supports. */
  surface?: TerrainSurface;
  rolls: Array<{ scale: number; amplitude: number }>;
  ridges: Array<{ id: string; profile: 'rounded' | 'shelf' | 'escarpment'; points: FieldPoint[] }>;
  channels: Array<{ id: string; points: FieldPoint[] }>;
  /** Compact, bounded drainage-inspired cuts; omitted on legacy fields. */
  incisions?: Array<{ id: string; points: FieldPoint[] }>;
}
export interface FieldPoint { x: number; z: number; width: number; height: number }

const smooth = (t: number) => t * t * (3 - 2 * t);
function lattice(x: number, z: number, seed: number): number {
  let n = Math.imul(x, 374761393) ^ Math.imul(z, 668265263) ^ seed;
  n = Math.imul(n ^ (n >>> 13), 1274126177);
  return ((n ^ (n >>> 16)) >>> 0) / 4294967295 * 2 - 1;
}
function roll(x: number, z: number, seed: number): number {
  const ix = Math.floor(x), iz = Math.floor(z), u = smooth(x - ix), v = smooth(z - iz);
  const a = lattice(ix, iz, seed), b = lattice(ix + 1, iz, seed);
  const c = lattice(ix, iz + 1, seed), d = lattice(ix + 1, iz + 1, seed);
  return (a + (b - a) * u) * (1 - v) + (c + (d - c) * u) * v;
}
function ribbon(x: number, z: number, points: FieldPoint[], profile: 'rounded' | 'shelf' | 'escarpment'): number {
  let result = 0;
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1], b = points[i], dx = b.x - a.x, dz = b.z - a.z;
    const t = Math.max(0, Math.min(1, ((x - a.x) * dx + (z - a.z) * dz) / (dx * dx + dz * dz)));
    let q = Math.hypot(x - a.x - t * dx, z - a.z - t * dz) / (a.width + (b.width - a.width) * t);
    // Directed scarps have a shorter exposed face and a broader back; graded counters remain separate.
    if (profile === 'escarpment') {
      const length = Math.hypot(dx, dz), across = (dx * (z - a.z) - dz * (x - a.x)) / length;
      const along = ((x - a.x) * dx + (z - a.z) * dz) / length - t * length;
      // Scale only the cross-section: radial end caps stay continuous across the extended crest.
      q = Math.hypot(along, across / (across < 0 ? .5 : 1.65)) / (a.width + (b.width - a.width) * t);
    }
    // Long shoulders join into a mass; variable-width spurs and cut drainage break its silhouette.
    const section = profile === 'rounded' ? 1 / (1 + q * q) ** 2 : 1 / (1 + q ** 6);
    result = Math.max(result, (a.height + (b.height - a.height) * t) * section);
  }
  return result;
}
/** Compact drainage cuts have no tails outside their authored width. */
function incision(x: number, z: number, points: FieldPoint[]): number {
  let result = 0;
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1], b = points[i], dx = b.x - a.x, dz = b.z - a.z;
    const t = Math.max(0, Math.min(1, ((x - a.x) * dx + (z - a.z) * dz) / (dx * dx + dz * dz)));
    const q = Math.hypot(x - a.x - t * dx, z - a.z - t * dz) / (a.width + (b.width - a.width) * t);
    if (q < 1) result = Math.max(result, (a.height + (b.height - a.height) * t) * (1 - q * q) ** 3);
  }
  return result;
}
export function terrainFieldHeight(field: TerrainField, x: number, z: number): number {
  let height = field.baseHeight;
  for (const [i, layer] of field.rolls.entries()) height += roll(x / layer.scale, z / layer.scale, field.seed + i * 1013) * layer.amplitude;
  // Adjacent branches share a watershed instead of stacking into conical mounds.
  const w = field.weathering;
  let px = x, pz = z;
  if (w) {
    // Warp the whole watershed together so spurs and their drainage remain related.
    px += roll(x / w.warpScale, z / w.warpScale, field.seed + 701) * w.warpMetres;
    pz += roll(x / w.warpScale, z / w.warpScale, field.seed + 1301) * w.warpMetres;
  }
  let ridge = 0, cut = 0;
  for (const row of field.ridges) ridge = Math.max(ridge, ribbon(px, pz, row.points, row.profile));
  for (const row of field.channels) cut = Math.max(cut, ribbon(px, pz, row.points, 'rounded'));
  if (w) {
    const detail = .6 * roll(px / w.detailScale, pz / w.detailScale, field.seed + 1901)
      + .4 * roll(px / (w.detailScale * .43), pz / (w.detailScale * .43), field.seed + 2503);
    ridge = Math.max(0, ridge + detail * w.detailAmplitude * Math.min(1, ridge / 22));
    if (w.terraceStrength > 0) {
      const layer = ridge / w.terraceHeight, base = Math.floor(layer), fraction = layer - base;
      // Smooth bedding ledges give basalt shelves a different section from limestone downs.
      const ledge = smooth(Math.max(0, Math.min(1, (fraction - .22) / .56)));
      ridge += ((base + ledge) * w.terraceHeight - ridge) * w.terraceStrength;
    }
  }
  let erosion = 0;
  for (const row of field.incisions ?? []) erosion = Math.max(erosion, incision(x, z, row.points));
  const relief = field.relief ? sampleTerrainRelief(field.relief, x, z) * Math.min(1, Math.max(0, ridge - cut) / field.relief.ridgeMaskHeight) : 0;
  const underlying=height + ridge - cut - erosion + relief;
  return field.surface ? terrainSurfaceHeight(field.surface,x,z,underlying) : underlying;
}

/** Reject malformed/unbounded recipes before sampling or admitting a candidate revision. */
export function validateTerrainField(field: TerrainField): void {
  const finite = (n: number, min: number, max: number) => Number.isFinite(n) && n >= min && n <= max;
  if (field.version !== 1 || !finite(field.baseHeight, -100, 250) || !Number.isInteger(field.seed)
    || !finite(field.seed, 0, 2147483647) || !Array.isArray(field.rolls) || field.rolls.length > 6
    || field.rolls.some(r => !finite(r.scale, 12, 2000) || !finite(r.amplitude, 0, 20))) throw new Error('Invalid terrain field controls');
  if (field.weathering) {
    const w = field.weathering;
    if (!finite(w.warpMetres, 0, 40) || !finite(w.warpScale, 30, 300)
      || !finite(w.detailScale, 16, 150) || !finite(w.detailAmplitude, 0, 12)
      || !finite(w.terraceHeight, 2, 15) || !finite(w.terraceStrength, 0, .85)) throw new Error('Invalid terrain weathering');
  }
  if (field.relief) validateTerrainRelief(field.relief);
  if (field.surface) validateTerrainSurface(field.surface);
  const ids = new Set<string>();
  for (const [rows, maximum] of [[field.ridges, 250], [field.channels, 50], [field.incisions ?? [], 24]] as const) {
    if (!Array.isArray(rows) || rows.length > 64) throw new Error('Invalid terrain ribbon inventory');
    for (const row of rows) {
      if (!row.id || ids.has(row.id) || !Array.isArray(row.points) || row.points.length < 2 || row.points.length > 64
        || ('profile' in row && row.profile !== 'rounded' && row.profile !== 'shelf' && row.profile !== 'escarpment')) throw new Error('Invalid terrain ribbon identity');
      ids.add(row.id);
      for (const [i, p] of row.points.entries()) {
        if (!finite(p.x, -10000, 10000) || !finite(p.z, -10000, 10000) || !finite(p.width, 6, 500)
          || !finite(p.height, 0, maximum) || (i && p.x === row.points[i - 1].x && p.z === row.points[i - 1].z)) throw new Error('Invalid terrain ribbon point');
      }
    }
  }
}
