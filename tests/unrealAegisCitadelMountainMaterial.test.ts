import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('alpine snow slope follows bound native render normals and rejects substituted evidence', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealAegisCitadelMountainMaterial.test.py'], {
    encoding: 'utf8', windowsHide: true,
  });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
