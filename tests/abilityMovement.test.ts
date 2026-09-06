import { describe, expect, test } from 'vitest';
import { resolveAbilityMovement } from '../src/game/AbilityMovement';

describe('collision-safe ability movement', () => {
  const origin = { x: 0, y: 0, z: 0 };
  test('follows a gentle slope and preserves the final ground height', () => {
    expect(resolveAbilityMovement(origin, { x: 5, y: 0, z: 0 }, (x) => x * 0.1, () => {}))
      .toEqual({ x: 5, y: 0.5, z: 0 });
  });
  test('blocks a thin wall along the path even when the destination is clear', () => {
    const result = resolveAbilityMovement(origin, { x: 8, y: 0, z: 0 }, () => 0, (point) => {
      if (point.x >= 3 && point.x <= 3.5) point.x = 2.99;
    });
    expect(result).toBeNull();
    expect(origin).toEqual({ x: 0, y: 0, z: 0 });
  });
  test.each([3, -3])('blocks a sudden height change of %s metres', (height) => {
    expect(resolveAbilityMovement(origin, { x: 8, y: 0, z: 0 }, (x) => x < 3 ? 0 : height, () => {})).toBeNull();
  });
  test('rejects invalid and oversized moves', () => {
    expect(resolveAbilityMovement(origin, { x: 13, y: 0, z: 0 }, () => 0, () => {})).toBeNull();
    expect(resolveAbilityMovement(origin, { x: NaN, y: 0, z: 0 }, () => 0, () => {})).toBeNull();
    expect(resolveAbilityMovement(origin, origin, () => 0, () => {})).toBeNull();
  });
});
