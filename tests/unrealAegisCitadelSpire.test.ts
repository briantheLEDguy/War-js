import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('detailed upper spires retain their bounded envelope and valid authored surfaces', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealAegisCitadelSpire.test.py'], {
    encoding: 'utf8', windowsHide: true,
  });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
