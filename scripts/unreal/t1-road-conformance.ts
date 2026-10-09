/** Fit cosmetic road ribbons to the exact rectangular terrain triangles, preserving UVs and verge alpha. */
import type { ZoneSpatial } from '../../shared/worldSpatial';

export interface NativeRoadSurface {
  zoneId: string; positions: number[][]; normals: number[][]; uvs: number[][]; colors?: number[][]; indices: number[];
}
type Vertex = { x: number; z: number; uv: number[]; color?: number[] };
const OFFSET_METRES = .045;
const EPSILON = 1e-10;

function clip(input: Vertex[], distance: (v: Vertex) => number): Vertex[] {
  const output: Vertex[] = [];
  for (let i = 0; i < input.length; i++) {
    const a = input[i], b = input[(i + 1) % input.length], da = distance(a), db = distance(b);
    if (da >= -EPSILON) output.push(a);
    if ((da < 0 && db > 0) || (da > 0 && db < 0)) {
      const t = da / (da - db), mix = (a: number[], b: number[]) => a.map((v, j) => v + (b[j] - v) * t);
      output.push({ x: a.x + (b.x - a.x) * t, z: a.z + (b.z - a.z) * t, uv: mix(a.uv, b.uv),
        ...(a.color && b.color ? { color: mix(a.color, b.color) } : {}) });
    }
  }
  return output;
}

export function conformRoadSurface(mesh: NativeRoadSurface, grid: Pick<ZoneSpatial, 'bounds' | 'terrainGrid'>,
  height: (x: number, z: number) => number): NativeRoadSurface {
  const { bounds: b, terrainGrid: g } = grid;
  if (!mesh.zoneId || !Object.values(b).every(Number.isFinite) || b.minX >= b.maxX || b.minZ >= b.maxZ
    || ![g.segmentsX, g.segmentsZ].every(n => Number.isInteger(n) && n > 0 && n <= 512)
    || mesh.positions.length > 500000 || mesh.indices.length > 1500000 || mesh.indices.length % 3
    || mesh.uvs.length !== mesh.positions.length || mesh.normals.length !== mesh.positions.length
    || mesh.colors && mesh.colors.length !== mesh.positions.length
    || mesh.positions.some(p => p.length !== 3 || !p.every(Number.isFinite)
      || p[1] / 100 < b.minX - 1e-7 || p[1] / 100 > b.maxX + 1e-7 || p[0] / 100 < b.minZ - 1e-7 || p[0] / 100 > b.maxZ + 1e-7)
    || mesh.uvs.some(p => p.length !== 2 || !p.every(Number.isFinite))
    || mesh.normals.some(p => p.length !== 3 || !p.every(Number.isFinite))
    || mesh.colors?.some(p => p.length !== 4 || p.some(v => !Number.isFinite(v) || v < 0 || v > 1))
    || mesh.indices.some(i => !Number.isInteger(i) || i < 0 || i >= mesh.positions.length)) throw new Error('Invalid bounded road surface');
  const dx = (b.maxX - b.minX) / g.segmentsX, dz = (b.maxZ - b.minZ) / g.segmentsZ;
  const out: NativeRoadSurface = { zoneId: mesh.zoneId, positions: [], normals: [], uvs: [], indices: [], ...(mesh.colors ? { colors: [] } : {}) };
  const heights = new Map<number, number>(), vertices = new Map<string, number>();
  const at = (x: number, z: number) => {
    const key = z * (g.segmentsX + 1) + x;
    if (!heights.has(key)) {
      const y = height(b.minX + x * dx, b.minZ + z * dz);
      if (!Number.isFinite(y)) throw new Error('Nonfinite road terrain');
      heights.set(key, y);
    }
    return heights.get(key)!;
  };
  const vertex = (v: Vertex, y: number) => {
    // Weld only matching UV/colour seams; separate overlapping ribbons keep their authored alpha.
    const key = [v.x, v.z, ...v.uv, ...(v.color ?? [])].map(n => n.toFixed(8)).join(',');
    const prior = vertices.get(key);
    if (prior !== undefined) return prior;
    const index = out.positions.length;
    if (index >= 2000000) throw new Error('Road overlay exceeds bounded output');
    out.positions.push([v.z * 100, v.x * 100, (y + OFFSET_METRES) * 100]);
    out.normals.push([0, 0, 0]); out.uvs.push(v.uv);
    if (out.colors) out.colors.push(v.color!);
    vertices.set(key, index); return index;
  };
  for (let i = 0; i < mesh.indices.length; i += 3) {
    const tri: Vertex[] = mesh.indices.slice(i, i + 3).map(j => ({ x: mesh.positions[j][1] / 100, z: mesh.positions[j][0] / 100,
      uv: mesh.uvs[j], ...(mesh.colors ? { color: mesh.colors[j] } : {}) }));
    const xmin = Math.max(0, Math.floor((Math.min(...tri.map(v => v.x)) - b.minX) / dx));
    const xmax = Math.min(g.segmentsX - 1, Math.floor((Math.max(...tri.map(v => v.x)) - b.minX) / dx));
    const zmin = Math.max(0, Math.floor((Math.min(...tri.map(v => v.z)) - b.minZ) / dz));
    const zmax = Math.min(g.segmentsZ - 1, Math.floor((Math.max(...tri.map(v => v.z)) - b.minZ) / dz));
    if ((xmax - xmin + 1) * (zmax - zmin + 1) > 64) throw new Error('Road triangle exceeds bounded grid overlay');
    for (let x = xmin; x <= xmax; x++) for (let z = zmin; z <= zmax; z++) {
      const x0 = b.minX + x * dx, z0 = b.minZ + z * dz;
      let cell = tri;
      for (const plane of [(v: Vertex) => v.x - x0, (v: Vertex) => x0 + dx - v.x,
        (v: Vertex) => v.z - z0, (v: Vertex) => z0 + dz - v.z]) cell = clip(cell, plane);
      for (const sign of [1, -1]) {
        const poly = clip(cell, v => sign * (1 - (v.x - x0) / dx - (v.z - z0) / dz));
        const h00 = at(x, z), h10 = at(x + 1, z), h01 = at(x, z + 1), h11 = at(x + 1, z + 1);
        const planeHeight = (v: Vertex) => {
          const tx = (v.x - x0) / dx, tz = (v.z - z0) / dz;
          return sign === 1 ? h00 + tx * (h10 - h00) + tz * (h01 - h00)
            : h11 + (1 - tx) * (h01 - h11) + (1 - tz) * (h10 - h11);
        };
        for (let k = 1; k < poly.length - 1; k++) {
          const p = [poly[0], poly[k], poly[k + 1]];
          const area = (p[1].z - p[0].z) * (p[2].x - p[0].x) - (p[1].x - p[0].x) * (p[2].z - p[0].z);
          // Clipping can create sub-millimetre slivers rejected by the native surface importer.
          if (Math.abs(area) < 1e-7) continue;
          if (area < 0) [p[1], p[2]] = [p[2], p[1]];
          const ids = p.map(v => vertex(v, planeHeight(v))), points = ids.map(j => out.positions[j]);
          const a = points[1].map((v, j) => v - points[0][j]), c = points[2].map((v, j) => v - points[0][j]);
          const normal = [a[1] * c[2] - a[2] * c[1], a[2] * c[0] - a[0] * c[2], a[0] * c[1] - a[1] * c[0]];
          if (normal[2] <= 0) throw new Error('Road overlay lost upward winding');
          for (const id of ids) normal.forEach((v, j) => out.normals[id][j] += v);
          // Unreal surface exports use clockwise indices with upward shading normals.
          out.indices.push(ids[0], ids[2], ids[1]);
          if (out.indices.length > 3000000) throw new Error('Road overlay exceeds bounded triangle inventory');
        }
      }
    }
  }
  out.normals = out.normals.map(n => { const length = Math.hypot(...n); return n.map(v => v / length); });
  return out;
}
