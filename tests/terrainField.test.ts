import { describe, expect, it } from 'vitest';
import { terrainFieldHeight, validateTerrainField, type TerrainField } from '../shared/terrainField';
import { createOrvrGridHeightSampler, orvrHeightAt } from '../shared/orvrTerrain';
import { readFileSync } from 'node:fs';
import { battlefieldLandscape, offRoadLinks } from '../scripts/unreal/t1-battlefield-landscape';
import { battlefieldGrades } from '../scripts/unreal/t1-battlefield-grades';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';

const field: TerrainField = { version: 1, baseHeight: 3, seed: 91, rolls: [], channels: [],
  ridges: [{ id: 'spur', profile: 'rounded', points: [{ x: 0, z: 0, width: 70, height: 32 }, { x: 200, z: 60, width: 90, height: 48 }] }] };
describe('shared connected terrain field', () => {
  it('joins ridges continuously without stacking overlapping watershed branches', () => {
    const f = { ...field, ridges: [...field.ridges, { ...field.ridges[0], id: 'second' }] };
    expect(terrainFieldHeight(f, 100, 30)).toBe(terrainFieldHeight(field, 100, 30));
    for (const x of [0, 200]) expect(Math.abs(terrainFieldHeight(field, x - .001, 0) - terrainFieldHeight(field, x + .001, 0))).toBeLessThan(.003);
  });
  it('cuts drainage within the ridge mass and survives JSON serialization deterministically', () => {
    const f = { ...field, rolls: [{ scale: 61, amplitude: 2 }], channels: [{ id: 'drain', points: [{ x: 0, z: 0, width: 25, height: 8 }, { x: 200, z: 60, width: 35, height: 10 }] }] };
    expect(terrainFieldHeight(f, 100, 30)).toBeLessThan(terrainFieldHeight({ ...f, channels: [] }, 100, 30));
    for (const p of [[-125, -17], [0, 0], [167, 80], [250, 101]]) expect(terrainFieldHeight(JSON.parse(JSON.stringify(f)), ...p as [number, number])).toBe(terrainFieldHeight(f, ...p as [number, number]));
  });
  it('rejects invalid seeds, duplicate IDs, zero segments and nonfinite controls before grid sampling', () => {
    for (const bad of [{ ...field, seed: .1 }, { ...field, baseHeight: NaN }, { ...field, rolls: [{ scale: 0, amplitude: 1 }] },
      { ...field, ridges: [...field.ridges, field.ridges[0]] }, { ...field, ridges: [{ ...field.ridges[0], points: [field.ridges[0].points[0], field.ridges[0].points[0]] }] }]) {
      expect(() => validateTerrainField(bad)).toThrow();
      expect(() => createOrvrGridHeightSampler({ sourceVersion: 'test', naturalField: bad, landforms: [], flattenAreas: [], clearCorridors: [] }, 100, 10)).toThrow();
    }
  });
  it('keeps untouched legacy terrain exact and explicit-grid Float32 grounding stable', () => {
    const t = { sourceVersion: 'legacy', landforms: [{ id: 'hill', kind: 'ridge' as const, x: 0, z: 0, radiusX: 100, radiusZ: 100, height: 25 }], flattenAreas: [], clearCorridors: [] };
    expect(orvrHeightAt(t, 20, 0)).toBe(25 * .96 ** 2);
    const h = createOrvrGridHeightSampler({ ...t, landforms: [], naturalField: field }, 200, 10,
      { bounds: { minX: -100, maxX: 100, minZ: -60, maxZ: 60 }, terrainGrid: { segmentsX: 10, segmentsZ: 6 }, playableOutline: [{ x: -100, z: -60 }, { x: 100, z: -60 }, { x: 100, z: 60 }, { x: -100, z: 60 }] });
    expect(h(0, 0)).toBe(Math.fround(terrainFieldHeight(field, 0, 0)));
    expect(Number.isFinite(h(17, -12))).toBe(true);
  });
  it('holds an explicit home footing against road shoulders while legacy pads retain their priority', () => {
    const area = { id: 'home', x: 0, z: 0, radius: 10, feather: 20, height: 5 };
    const t = { sourceVersion: 'footing', gradedRoutes: true, landforms: [], flattenAreas: [area],
      clearCorridors: [{ id: 'road', points: [{ x: -30, z: 0, y: 20 }, { x: 30, z: 0, y: 20 }], radius: 13, feather: 20, height: 20 }] };
    expect(orvrHeightAt(t, 0, 0)).toBe(20);
    expect(orvrHeightAt({ ...t, flattenAreas: [{ ...area, preserveFooting: true }] }, 0, 0)).toBe(5);
  });
});

for (const id of ['sunmeadow_march', 'cinderfen_outskirts']) describe(`${id} battlefield relief`, () => {
  const source = redesignT1(JSON.parse(readFileSync(`public/assets/maps/${id}.json`, 'utf8')) as ZoneDefinition);
  it('retains source identities, XY routes, local colliders and complete keep offsets', () => {
    const before = JSON.stringify(source), z = battlefieldLandscape(source);
    expect(JSON.stringify(source)).toBe(before);
    expect(z.paths!.map(p => p.points.map(p => [p.x, p.z]))).toEqual(source.paths!.map(p => p.points.map(p => [p.x, p.z])));
    for (const key of ['npcs', 'enemies', 'resourceNodes', 'craftingStations', 'rvrObjectives', 'zoneTriggers'] as const) expect(z[key]!.map(p => p.id)).toEqual(source[key]!.map(p => p.id));
    expect(z.props!.map(p => p.colliders)).toEqual(source.props!.map(p => p.colliders));
    for (const [i, k] of z.orvrLayout!.keeps.entries()) {
      const old = source.orvrLayout!.keeps[i];
      expect(k.commander.y! - k.y!).toBe(old.commander.y! - old.y!);
      expect(k.deliveryPoint.y! - k.y!).toBe(old.deliveryPoint.y! - old.y!);
      expect(k.gates.map(g => g.y! - k.y!)).toEqual(old.gates.map(g => g.y! - old.y!));
    }
  });
  it('grades full-width roads and deliberate off-road vehicle links below the .22 target', () => {
    const z = battlefieldLandscape(source), h = createOrvrGridHeightSampler(z.orvrLayout!.terrain, z.size, z.segments, z.spatial);
    const paths = [...z.paths!, ...offRoadLinks(id)];
    let maximum = 0;
    for (const path of paths) for (let i = 1; i < path.points.length; i++) {
      const a = path.points[i - 1], b = path.points[i], dx = b.x - a.x, dz = b.z - a.z, length = Math.hypot(dx, dz), steps = Math.ceil(length / 2);
      for (const side of [-path.width / 2, 0, path.width / 2]) {
        let previous: number | undefined;
        for (let j = 0; j <= steps; j++) {
          const y = h(a.x + dx * j / steps - dz / length * side, a.z + dz * j / steps + dx / length * side);
          if (previous !== undefined) maximum = Math.max(maximum, Math.abs(y - previous) / (length / steps));
          previous = y;
        }
      }
    }
    expect(maximum).toBeLessThan(.22);
    expect(Math.max(...battlefieldGrades(paths, h).map(p => p.maximumGrade))).toBeLessThan(.22);
    const main = z.paths![0].points;
    expect(Math.max(...main.map(p => h(p.x, p.z))) - Math.min(...main.map(p => h(p.x, p.z)))).toBeGreaterThan(12);
    // The middle saddle masks a direct ground-level sightline between the outer battle spaces.
    const a = main[2], b = main[6], middle = main[4];
    expect(h(middle.x, middle.z)).toBeGreaterThan(Math.max(h(a.x, a.z), h(b.x, b.z)) + 6);
  });
});

it('keeps the retained Cinderfen home approach on continuous village ground', () => {
  const source = redesignT1(JSON.parse(readFileSync('public/assets/maps/cinderfen_outskirts.json', 'utf8')) as ZoneDefinition);
  const points = [{ x: 380, z: -290, y: 12 }, { x: 314, z: -290, y: 12 }, { x: 314, z: -380, y: 12 }, { x: 311, z: -380, y: 12 }];
  const z = battlefieldLandscape(source, [{ id: 'cinderfen_outskirts_village_furnished_home_0', points }]);
  const h = createOrvrGridHeightSampler(z.orvrLayout!.terrain, z.size, z.segments, z.spatial);
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1], b = points[i], count = Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) / .5);
    for (let j = 0; j <= count; j++) expect(Math.abs(h(a.x + (b.x - a.x) * j / count, a.z + (b.z - a.z) * j / count) - 12)).toBeLessThan(.1);
  }
});
