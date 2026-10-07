import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expect, test } from 'vitest';

test('portable retained-mountain bridge preserves the exact native callback contract', () => {
  const file = fileURLToPath(new URL('./unrealCitadelRetainedMountainBridge.test.py', import.meta.url));
  const run = spawnSync(process.env.PYTHON ?? 'python', ['-B', file], {
    encoding: 'utf8', windowsHide: true,
  });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
