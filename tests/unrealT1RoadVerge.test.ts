import { expect, it } from 'vitest';
import { roadSurfaceGeometry } from '../shared/world/RoadSurface';
import { battlefieldGrades } from '../scripts/unreal/t1-battlefield-grades';

it('feathers a wider T1 verge while retaining a solid nine-metre centre and continuous ground support', () => {
  const paths = [{ id: 'road', style: 'dirt_trail' as const, width: 12, points: [{ x: 0, z: 0 }, { x: 50, z: 0 }, { x: 80, z: 30 }] }];
  const g = roadSurfaceGeometry(paths, (x, z) => x * .04 + z * .02, { vergeWidth: 3 });
  const p = g.getAttribute('position'), c = g.getAttribute('color');
  const alphas = Array.from({ length: c.count }, (_, i) => c.getW(i));
  expect(alphas).toContain(0); expect(alphas).toContain(1); expect(alphas.some(a => a > 0 && a < 1)).toBe(true);
  for (let i = 0; i < p.count; i++) {
    expect(p.getY(i)).toBeCloseTo(p.getX(i) * .04 + p.getZ(i) * .02 + .045, 5);
    if (p.getX(i) > 12 && p.getX(i) < 35 && Math.abs(p.getZ(i)) < 4.5) expect(c.getW(i)).toBe(1);
  }
  g.dispose();
  for (const vergeWidth of [0, 7, NaN]) expect(() => roadSurfaceGeometry(paths, () => 0, { vergeWidth })).toThrow(/verge/);
});

it('rejects a steep sideways bank that a centre-line climb check would miss', () => {
  const paths = [{ id: 'road', width: 12, points: [{ x: 0, z: 0 }, { x: 50, z: 0 }] }];
  const [bank] = battlefieldGrades(paths, (x, z) => x * .04 + z * .4);
  expect(bank.maximumLongitudinalGrade).toBeCloseTo(.04, 8);
  expect(bank.maximumCrossGrade).toBeCloseTo(.4, 8);
  expect(bank.maximumGrade).toBeGreaterThan(.4);
  expect(bank.samples).toBe(26 * 7);
});
