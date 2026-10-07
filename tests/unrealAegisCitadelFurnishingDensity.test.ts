import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('citadel furnishing density protects actual geometry and signed reservations', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealAegisCitadelFurnishingDensity.test.py'], {
    encoding: 'utf8', windowsHide: true,
  });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
