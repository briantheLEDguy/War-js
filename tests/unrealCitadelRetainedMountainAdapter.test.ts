import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('retained mountain adapter preserves measured instance and parent contracts', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealCitadelRetainedMountainAdapter.test.py'], {
    encoding: 'utf8', windowsHide: true,
  });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
