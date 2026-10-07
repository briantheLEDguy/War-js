import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('highland relief keeps low terrain and shared edges intact', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealCitadelAlpineRelief.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
