import { describe, expect, test } from 'vitest';
import { applyZonePaths } from '../src/world/PathKit';
import type { ZoneDefinition } from '../src/world/ZoneLoader';

describe('path generation', () => {
  test('connects nearby path endpoints without adding walkable shelves', () => {
    const zone: ZoneDefinition = {
      id: 'test-zone',
      name: 'Test Zone',
      size: 100,
      segments: 8,
      props: [],
      enemies: [],
      paths: [
        {
          id: 'west_trail',
          style: 'dirt_trail',
          width: 7,
          points: [{ x: -18, z: 64 }, { x: -30, z: 82 }],
        },
        {
          id: 'north_avenue',
          style: 'cobblestone_avenue',
          width: 9.5,
          points: [{ x: 0, z: 62 }, { x: 0, z: 90 }],
        },
      ],
    };

    const generated = applyZonePaths(zone).props;
    expect(generated.some((prop) => prop.id?.startsWith('west_trail_start_to_north_avenue_start'))).toBe(true);
    expect(generated.some((prop) => prop.id?.startsWith('west_trail_junction_0'))).toBe(true);
    expect(generated.every((prop) => !prop.walkableSurfaces?.length)).toBe(true);
  });
});
