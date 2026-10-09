import { expect, it } from 'vitest';
import { conformRoadSurface, type NativeRoadSurface } from '../scripts/unreal/t1-road-conformance';
const grid = { bounds: { minX: 0, maxX: 1, minZ: 0, maxZ: 1 }, terrainGrid: { segmentsX: 1, segmentsZ: 1 } };
const height = (x: number, z: number) => x + z <= 1 ? x + z : 2 - x - z;
const points = [[.1, .1], [.9, .3], [.3, .9]];
const mesh = (): NativeRoadSurface => ({ zoneId: 'sunmeadow_march',
  positions: points.map(([x, z]) => [z * 100, x * 100, (height(x, z) + .045) * 100]),
  normals: points.map(() => [0, 0, 1]), uvs: points.map(([x, z]) => [x / 2, -z / 2]),
  colors: points.map(([x]) => [1, 1, 1, x]), indices: [0, 1, 2] });
const area = (m: NativeRoadSurface) => {
  let sum = 0;
  for (let i = 0; i < m.indices.length; i += 3) {
    const [a, b, c] = m.indices.slice(i, i + 3).map(j => m.positions[j]);
    sum += Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 20000;
  }
  return sum;
};
it('removes interior terrain penetration across a grid diagonal while preserving covered area', () => {
  const input = mesh(), before = structuredClone(input), out = conformRoadSurface(input, grid, height);
  const center = input.positions.reduce((a, p) => a.map((v, j) => v + p[j] / 300), [0, 0, 0]);
  expect(center[2]).toBeLessThan(height(center[1], center[0]));
  expect(input).toEqual(before); expect(out.indices.length).toBeGreaterThan(input.indices.length);
  expect(area(out)).toBeCloseTo(area(input), 10);
  for (let i = 0; i < out.indices.length; i += 3) {
    const p = out.indices.slice(i, i + 3).map(j => out.positions[j]);
    for (const w of [[1 / 3, 1 / 3, 1 / 3], [.5, .5, 0], [0, .5, .5], [.5, 0, .5]]) {
      const q = [0, 1, 2].map(k => p.reduce((s, v, j) => s + v[k] * w[j] / 100, 0));
      expect(q[2] - height(q[1], q[0])).toBeCloseTo(.045, 9);
    }
  }
});
it('interpolates texture coordinates and soft alpha without adding hard edge seams', () => {
  const out = conformRoadSurface(mesh(), grid, height);
  out.positions.forEach((p, i) => {
    expect(out.uvs[i][0]).toBeCloseTo(p[1] / 200, 9); expect(out.uvs[i][1]).toBeCloseTo(-p[0] / 200, 9);
    expect(out.colors![i][3]).toBeCloseTo(p[1] / 100, 9);
    expect(Math.hypot(...out.normals[i])).toBeCloseTo(1, 9); expect(out.normals[i][2]).toBeGreaterThan(0);
  });
  const input = mesh(); delete input.colors;
  expect(conformRoadSurface(input, grid, height).colors).toBeUndefined();
});
it('supports rectangular cells and deterministic output', () => {
  const rectangular = { bounds: { minX: 0, maxX: 2, minZ: 0, maxZ: 1 }, terrainGrid: { segmentsX: 1, segmentsZ: 1 } };
  const input = mesh(), out = conformRoadSurface(input, rectangular, (x, z) => x * .1 + z * .2);
  expect(out).toEqual(conformRoadSurface(input, rectangular, (x, z) => x * .1 + z * .2));
  expect(area(out)).toBeCloseTo(area(input), 10);
});
it('rejects malformed, escaped, nonfinite and unbounded overlays', () => {
  for (const change of [{ indices: [0, 1, 99] }, { indices: [0, 1] }, { uvs: [] },
    { positions: [[0, 0, NaN], [0, 1, 0], [1, 0, 0]] }, { colors: [[1, 1, 1, 2], [1, 1, 1, 1], [1, 1, 1, 0]] }]) {
    expect(() => conformRoadSurface({ ...mesh(), ...change }, grid, height)).toThrow('Invalid bounded');
  }
  expect(() => conformRoadSurface(mesh(), grid, () => NaN)).toThrow('Nonfinite road');
  expect(() => conformRoadSurface(mesh(), { ...grid, terrainGrid: { segmentsX: 512, segmentsZ: 512 } }, height)).toThrow('bounded grid overlay');
  expect(() => conformRoadSurface(mesh(), { ...grid, bounds: { ...grid.bounds, maxX: .5 } }, height)).toThrow('Invalid bounded');
});


it('filters microscopic clipping slivers before the native near-zero cross-product guard', () => {
  const input = mesh();
  input.positions = [[0, 0, 4.5], [0, 100, 4.5], [1e-7, 1e-7, 4.5]];
  const out = conformRoadSurface(input, grid, () => 0);
  expect(out.indices).toEqual([]); expect(out.positions).toEqual([]);
});


it('retains the native clockwise front face independently of upward shading normals', () => {
  const out = conformRoadSurface(mesh(), grid, height);
  for (let i = 0; i < out.indices.length; i += 3) {
    const [a, b, c] = out.indices.slice(i, i + 3).map(j => out.positions[j]);
    expect((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])).toBeLessThan(0);
  }
  expect(out.normals.every(n => n[2] > 0)).toBe(true);
});
