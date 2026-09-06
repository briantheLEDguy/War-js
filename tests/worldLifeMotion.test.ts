import { describe, expect, test } from 'vitest';
import { sampleWorldLifeRoute } from '../src/world/worldLifeMotion';
import type { WorldLifePoint } from '../src/world/worldLifeMotion';

const origin: WorldLifePoint = { x: 0, z: 0 };
const destination: WorldLifePoint = { x: 6, z: 8 };

describe('ambient world life route motion', () => {
  test('dwells at the origin and destination for the full configured pause', () => {
    const sample = (time: number) => sampleWorldLifeRoute(origin, [destination], time, 2, 3);

    expect(sample(0)).toMatchObject({ x: 0, z: 0, moving: false });
    expect(sample(2.999)).toMatchObject({ x: 0, z: 0, moving: false });
    expect(sample(3)).toMatchObject({ x: 0, z: 0, moving: true });
    expect(sample(5.5)).toMatchObject({ x: 3, z: 4, moving: true });
    expect(sample(8)).toMatchObject({ x: 6, z: 8, moving: false });
    expect(sample(10.999)).toMatchObject({ x: 6, z: 8, moving: false });
    expect(sample(11)).toMatchObject({ x: 6, z: 8, moving: true });
    expect(sample(13.5)).toMatchObject({ x: 3, z: 4, moving: true });
    expect(sample(16)).toEqual(sample(0));
  });

  test('keeps positions continuous at arrival, departure, and the closed loop seam', () => {
    const sample = (time: number) => sampleWorldLifeRoute(origin, [destination], time, 2, 3);
    const epsilon = 0.00001;

    for (const boundary of [3, 8, 11, 16]) {
      const before = sample(boundary - epsilon);
      const at = sample(boundary);
      const after = sample(boundary + epsilon);
      expect(Math.hypot(before.x - at.x, before.z - at.z)).toBeLessThan(0.00003);
      expect(Math.hypot(after.x - at.x, after.z - at.z)).toBeLessThan(0.00003);
    }
  });

  test('faces the direction of travel and retains incoming heading during a pause', () => {
    const route = [{ x: 6, z: 0 }, { x: 6, z: 8 }];
    const sample = (time: number) => sampleWorldLifeRoute(origin, route, time, 2, 2);

    expect(sample(3).heading).toBeCloseTo(Math.PI / 2);
    expect(sample(5)).toMatchObject({ x: 6, z: 0, moving: false });
    expect(sample(5).heading).toBeCloseTo(Math.PI / 2);
    expect(sample(8).heading).toBe(0);
    expect(sample(14).heading).toBeCloseTo(Math.atan2(-6, -8));
    expect(sample(18)).toEqual(sample(0));
  });

  test.each([0.25, 1, 4])('travels at %s world units per second independent of edge length', (speed) => {
    const route = [{ x: 0, z: 20 }, { x: 15, z: 40 }];
    const sample = (time: number) => sampleWorldLifeRoute(origin, route, time, speed, 1);

    for (const time of [1 + 5 / speed, 2 + 25 / speed]) {
      const before = sample(time);
      const after = sample(time + 0.125);
      expect(before.moving).toBe(true);
      expect(after.moving).toBe(true);
      expect(Math.hypot(after.x - before.x, after.z - before.z)).toBeCloseTo(speed * 0.125);
    }
  });

  test('ignores duplicate waypoints without adding extra pauses', () => {
    const duplicated = [origin, origin, destination, destination, origin, origin];
    for (const time of [0, 3, 5.5, 8, 11, 13.5, 16, 23]) {
      expect(sampleWorldLifeRoute(origin, duplicated, time, 2, 3))
        .toEqual(sampleWorldLifeRoute(origin, [destination], time, 2, 3));
    }
  });

  test('samples long-running loops and repeated reads without accumulating frame state', () => {
    const sample = (time: number) => sampleWorldLifeRoute(origin, [destination], time, 2, 3);
    expect(sample(16 * 10_000_000_000 + 5.5)).toEqual(sample(5.5));

    let elapsed = 0;
    for (let frame = 0; frame < 44; frame++) {
      elapsed += 0.125;
      sample(elapsed);
    }
    expect(sample(elapsed)).toEqual(sample(5.5));
    expect(sample(2)).toEqual(sample(18));
  });

  test('allows a zero pause and passes continuously through each waypoint', () => {
    expect(sampleWorldLifeRoute(origin, [destination], 0, 2, 0))
      .toMatchObject({ x: 0, z: 0, moving: true });
    expect(sampleWorldLifeRoute(origin, [destination], 5, 2, 0))
      .toMatchObject({ x: 6, z: 8, moving: true });
    expect(sampleWorldLifeRoute(origin, [destination], 10, 2, 0))
      .toEqual(sampleWorldLifeRoute(origin, [destination], 0, 2, 0));
  });

  test('keeps empty and all-duplicate routes stationary', () => {
    for (const route of [undefined, [], [origin], [origin, origin]]) {
      expect(sampleWorldLifeRoute(origin, route, 123, 2, 3))
        .toEqual({ x: 0, z: 0, heading: 0, moving: false });
    }
  });

  test.each([0, -1, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    'keeps invalid speed %s stationary',
    (speed) => {
      expect(sampleWorldLifeRoute(destination, [origin], 123, speed, 3))
        .toEqual({ x: 6, z: 8, heading: 0, moving: false });
    },
  );

  test.each([-1, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    'clamps invalid elapsed time %s to route start',
    (time) => {
      expect(sampleWorldLifeRoute(origin, [destination], time, 2, 3))
        .toEqual(sampleWorldLifeRoute(origin, [destination], 0, 2, 3));
    },
  );

  test.each([-1, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    'treats invalid pause %s as zero',
    (pause) => {
      expect(sampleWorldLifeRoute(origin, [destination], 2.5, 2, pause))
        .toEqual(sampleWorldLifeRoute(origin, [destination], 2.5, 2, 0));
    },
  );

  test('repairs invalid origin coordinates and ignores nonfinite route points', () => {
    const badOrigin = { x: Number.NaN, z: Number.POSITIVE_INFINITY };
    const route = [{ x: Number.NaN, z: 2 }, destination, { x: 2, z: Number.NEGATIVE_INFINITY }];

    expect(sampleWorldLifeRoute(badOrigin, route, 5.5, 2, 3))
      .toEqual(sampleWorldLifeRoute(origin, [destination], 5.5, 2, 3));
    expect(sampleWorldLifeRoute(badOrigin, route.slice(0, 1), 5.5, 2, 3))
      .toEqual({ x: 0, z: 0, heading: 0, moving: false });
  });

  test('keeps overflowing coordinates and durations finite without teleporting', () => {
    const farOrigin = { x: -Number.MAX_VALUE, z: 0 };
    const farRoute = [{ x: Number.MAX_VALUE, z: 0 }];
    expect(sampleWorldLifeRoute(farOrigin, farRoute, 1, 2, 3))
      .toEqual({ ...farOrigin, heading: 0, moving: false });
    expect(sampleWorldLifeRoute(origin, [destination], 1, Number.MIN_VALUE, 3))
      .toEqual({ ...origin, heading: 0, moving: false });
    expect(sampleWorldLifeRoute(origin, [destination], 1, 2, Number.MAX_VALUE))
      .toEqual({ ...origin, heading: 0, moving: false });
  });
});
