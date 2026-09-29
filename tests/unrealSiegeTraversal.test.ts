import { expect, test } from 'vitest';
import { validateSiegeTraversal } from '../scripts/unreal/siege-traversal-proof';

test('traversal requires all twelve characters, seven routes and actual movement', () => {
  const valid = { passed: true, routesCompleted: 7, traversalReviewGranted: false, gameplayVerified: false,
    walkers: Array.from({ length: 12 }, (_, walker) => ({ walker, jumped: true, distanceCm: 2000 })) };
  expect(() => validateSiegeTraversal(valid)).not.toThrow();
  for (const change of [{ passed: false }, { routesCompleted: 6 }, { gameplayVerified: true },
    { walkers: valid.walkers.slice(1) }, { walkers: valid.walkers.map(w => ({ ...w, jumped: false })) },
    { walkers: valid.walkers.map(w => ({ ...w, distanceCm: NaN })) },
    { walkers: valid.walkers.map(w => ({ ...w, walker: 1 })) }]) {
    expect(() => validateSiegeTraversal({ ...valid, ...change })).toThrow();
  }
});
