import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { describe, expect, test } from 'vitest';
import { cityHeightAt, type CityElevation } from '../src/world/CityElevation';
import { compactCityElevation } from '../scripts/campaign/compact-city-elevation.mjs';

function expand(field: CityElevation): number[] {
  if (field.heights) return field.heights;
  const heights: number[] = [];
  for (const [end, height] of field.heightRuns) {
    while (heights.length < end) heights.push(height);
  }
  return heights;
}

describe('lossless city elevation runs', () => {
  test('keeps dense fields when runs would increase the sample count', () => {
    const field = { segments: 1, heights: [0, 1, 2, 3] };
    expect(compactCityElevation(field)).toBe(field);
  });

  test('preserves negative heights, row transitions, triangle diagonals and clamped edges', () => {
    const dense = { segments: 3, heights: [-2, -2, -2, -2, 0, 0, 0, 0, 5, 5, 5, 5, 5, 5, 5, 5] };
    const packed = compactCityElevation(dense);
    expect(packed.heightRuns).toEqual([[4, -2], [8, 0], [16, 5]]);
    expect(expand(packed)).toEqual(dense.heights);
    expect(compactCityElevation(packed)).toBe(packed);
    for (let x = -3; x <= 3; x += .125) for (let z = -3; z <= 3; z += .125) {
      expect(cityHeightAt(packed, 3, x, z)).toBe(cityHeightAt(dense, 3, x, z));
    }
  });

  test('rejects incomplete or nonfinite authored grids', () => {
    expect(() => compactCityElevation({ segments: 1, heights: [0] })).toThrow('grid sample');
    expect(() => compactCityElevation({ segments: 1, heights: [0, NaN, 0, 0] })).toThrow('grid sample');
  });

  test('retains every original Aegis sample and uses a small random-access representation', () => {
    const zone = JSON.parse(readFileSync('public/assets/maps/aegis_capital.json', 'utf8'));
    const field: CityElevation = zone.cityElevation;
    expect(field.heights).toBeUndefined();
    const heights = expand(field);
    expect(heights).toHaveLength((field.segments + 1) ** 2);
    // Digest of all 641,601 pre-cleanup heights, before any representation change.
    expect(createHash('sha256').update(JSON.stringify(heights)).digest('hex'))
      .toBe('05f6c97d44486b18b8a5dfd1f0f42f6c4fe40792f96cde69729ab9b8edbb8ede');
    expect(JSON.stringify(field).length).toBeLessThan(JSON.stringify(heights).length * .09);
    const dense = { segments: field.segments, heights };
    for (let x = -zone.size / 2; x <= zone.size / 2; x += 7.25) {
      for (let z = -zone.size / 2; z <= zone.size / 2; z += 7.75) {
        expect(cityHeightAt(field, zone.size, x, z)).toBe(cityHeightAt(dense, zone.size, x, z));
      }
    }
    expect(field.heights).toBeUndefined();
  });
});
