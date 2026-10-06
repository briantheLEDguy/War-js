import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('central standard has supported final-space geometry and real arch clearance', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealAegisCitadelStandard.test.py'], {
    encoding: 'utf8', windowsHide: true,
  });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
