import { describe, expect, it } from 'vitest';
import { buildCapitalTerrain } from '../scripts/unreal/capital-terrain';

const definition = () => ({ id: 'aegis_capital', size: 4, canals: [], cityElevation: { segments: 2,
  heights: [0, 0, 0, 0, 1, 0, 0, 0, 0] } });

describe('capital terrain conversion', () => {
  it('retains authored heights, centimeter axes, winding and UV scale', () => {
    const ground = buildCapitalTerrain(definition()).surfaces[0];
    expect(ground.positions).toContainEqual([0, 0, 100]);
    expect(ground.positions[0]).toEqual([-200, -200, 0]);
    expect(ground.indices.slice(0, 6)).toEqual([0, 2, 1, 0, 3, 2]);
    expect(ground.uvs[0]).toEqual([0, 0]);
    expect(ground.positions.length).toBe(16);
    expect(ground.collision).toBe(true);
  });
  it('preserves canal openings with separate non-solid water and solid beds', () => {
    const map = { ...definition(), canals: [{ id: 'canal', x: 0, z: 0, width: 2, depth: 4, bedY: -3, waterY: -1 }] };
    const [ground, water, bed] = buildCapitalTerrain(map).surfaces;
    for (let i = 0; i < ground.indices.length; i += 3) {
      const y = ground.indices.slice(i, i + 3).reduce((sum, index) => sum + ground.positions[index][1], 0) / 3;
      expect(Math.abs(y)).toBeGreaterThanOrEqual(100);
    }
    expect(water.collision).toBe(false);
    expect(water.positions.every(p => p[2] === -100)).toBe(true);
    expect(bed.collision).toBe(true);
    expect(bed.positions.every(p => p[2] === -300)).toBe(true);
    expect(water.indices.length).toBeGreaterThan(0);
  });
  it('rejects malformed elevation instead of flattening it or inventing Riftspire ground', () => {
    expect(() => buildCapitalTerrain({ ...definition(), id: 'riftspire_capital' })).toThrow('crater');
    expect(() => buildCapitalTerrain({ ...definition(), cityElevation: { segments: 2, heights: [0] } })).toThrow('samples');
    expect(() => buildCapitalTerrain({ ...definition(), cityElevation: { segments: 2, heightRuns: [[8, 0]] } })).toThrow('Incomplete');
    expect(() => buildCapitalTerrain({ ...definition(), cityElevation: { segments: 2, heightRuns: [[8, 0], [7, 1], [9, 0]] } })).toThrow('Invalid');
    const dense = definition();
    const compact = { ...dense, cityElevation: { segments: 2, heightRuns: [[4, 0], [5, 1], [9, 0]] as [number, number][] } };
    expect(buildCapitalTerrain(compact).surfaces).toEqual(buildCapitalTerrain(dense).surfaces);
  });
});
