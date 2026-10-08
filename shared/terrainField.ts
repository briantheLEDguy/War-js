/** Serializable metre-space landforms. Native meshes and Node grounding evaluate the same field. */
export interface TerrainField {
  version: 1;
  baseHeight: number;
  seed: number;
  rolls: Array<{ scale: number; amplitude: number }>;
  ridges: Array<{ id: string; profile: 'rounded' | 'shelf'; points: FieldPoint[] }>;
  channels: Array<{ id: string; points: FieldPoint[] }>;
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
function ribbon(x: number, z: number, points: FieldPoint[], shelf: boolean): number {
  let result = 0;
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1], b = points[i], dx = b.x - a.x, dz = b.z - a.z;
    const t = Math.max(0, Math.min(1, ((x - a.x) * dx + (z - a.z) * dz) / (dx * dx + dz * dz)));
    const q = Math.hypot(x - a.x - t * dx, z - a.z - t * dz) / (a.width + (b.width - a.width) * t);
    // Long shoulders join into a mass; variable-width spurs and cut drainage break its silhouette.
    const profile = shelf ? 1 / (1 + q ** 6) : 1 / (1 + q * q) ** 2;
    result = Math.max(result, (a.height + (b.height - a.height) * t) * profile);
  }
  return result;
}
export function terrainFieldHeight(field: TerrainField, x: number, z: number): number {
  let height = field.baseHeight;
  for (const [i, layer] of field.rolls.entries()) height += roll(x / layer.scale, z / layer.scale, field.seed + i * 1013) * layer.amplitude;
  // Adjacent branches share a watershed instead of stacking into conical mounds.
  let ridge = 0, cut = 0;
  for (const row of field.ridges) ridge = Math.max(ridge, ribbon(x, z, row.points, row.profile === 'shelf'));
  for (const row of field.channels) cut = Math.max(cut, ribbon(x, z, row.points, false));
  return height + ridge - cut;
}

/** Reject malformed/unbounded recipes before sampling or admitting a candidate revision. */
export function validateTerrainField(field: TerrainField): void {
  const finite = (n: number, min: number, max: number) => Number.isFinite(n) && n >= min && n <= max;
  if (field.version !== 1 || !finite(field.baseHeight, -100, 250) || !Number.isInteger(field.seed)
    || !finite(field.seed, 0, 2147483647) || !Array.isArray(field.rolls) || field.rolls.length > 6
    || field.rolls.some(r => !finite(r.scale, 12, 2000) || !finite(r.amplitude, 0, 20))) throw new Error('Invalid terrain field controls');
  const ids = new Set<string>();
  for (const [rows, maximum] of [[field.ridges, 250], [field.channels, 50]] as const) {
    if (!Array.isArray(rows) || rows.length > 64) throw new Error('Invalid terrain ribbon inventory');
    for (const row of rows) {
      if (!row.id || ids.has(row.id) || !Array.isArray(row.points) || row.points.length < 2 || row.points.length > 64
        || ('profile' in row && row.profile !== 'rounded' && row.profile !== 'shelf')) throw new Error('Invalid terrain ribbon identity');
      ids.add(row.id);
      for (const [i, p] of row.points.entries()) {
        if (!finite(p.x, -10000, 10000) || !finite(p.z, -10000, 10000) || !finite(p.width, 6, 500)
          || !finite(p.height, 0, maximum) || (i && p.x === row.points[i - 1].x && p.z === row.points[i - 1].z)) throw new Error('Invalid terrain ribbon point');
      }
    }
  }
}
