import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('private material studies preserve original graphs and require visible sculpture bindings', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealCitadelPrivateSurfaceStudy.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
