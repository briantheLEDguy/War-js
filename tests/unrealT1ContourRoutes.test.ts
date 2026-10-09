import { expect, it } from 'vitest';
import { contourRoutes, maximumContourGrade, type ContourSearch } from '../scripts/unreal/t1-contour-routes';
const recipe: ContourSearch = { id: 'test_overlook', bounds: { minX: 0, maxX: 100, minZ: -30, maxZ: 30 },
  starts: [{ x: 4, z: -20 }, { x: 4, z: 20 }], target: { x: 80, z: 0 }, targetRadius: 10,
  minimumRise: 3, width: 4, step: 4, maximumGrade: .21 };
it('finds deterministic full-width counters on gentle ground without mutating the recipe', () => {
  const before = structuredClone(recipe), height = (x: number) => x * .1;
  const result = contourRoutes(recipe, height, () => true);
  expect(result).toEqual(contourRoutes(recipe, height, () => true)); expect(recipe).toEqual(before);
  expect(result.routes).toHaveLength(2); expect(result.goal.y).toBeGreaterThan(8);
  expect(result.routes.map(r => r.points[0])).toEqual(recipe.starts.map(p => ({ ...p, y: height(p.x) })));
  expect(result.routes.every(r => r.points.length >= 2)).toBe(true);
  expect(result.grades.every(g => g.maximumGrade <= .21)).toBe(true); expect(result.terrainChanged).toBe(false);
});
it('rejects unreachable cliffs, unsupported starts and nonfinite terrain', () => {
  expect(() => contourRoutes(recipe, x => x < 40.3 ? 0 : 20, () => true)).toThrow('No shared reachable');
  expect(() => contourRoutes(recipe, x => x * .1, p => p.x > 20)).toThrow('No grounded contour start');
  expect(() => contourRoutes(recipe, () => NaN, () => true)).toThrow('Nonfinite');
});
it('rejects unbounded, invalid or degenerate searches', () => {
  for (const change of [{ step: 0 }, { width: 12 }, { maximumGrade: .3 }, { targetRadius: Infinity },
    { bounds: { minX: 0, maxX: 10000, minZ: 0, maxZ: 10000 } }, { starts: [] }]) {
    expect(() => contourRoutes({ ...recipe, ...change }, () => 0, () => true)).toThrow('Invalid bounded');
  }
});

it('does not average away the steeper native face at a triangle boundary', () => {
  const height = (x: number) => x < 0 ? x * .23 : x * .18;
  expect((height(.05) - height(-.05)) / .1).toBeCloseTo(.205, 8);
  expect(maximumContourGrade(height, { x: 0, z: 0 })).toBeCloseTo(.23, 8);
});
