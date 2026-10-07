import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('citadel arches and glazed bays face their explicit exterior approach', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealAegisCitadelWindowOrientation.test.py'], {
    encoding: 'utf8', windowsHide: true,
  });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 60_000);
