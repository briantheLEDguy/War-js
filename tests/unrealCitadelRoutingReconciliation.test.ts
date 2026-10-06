import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('private routing reconciliation preserves saved packages and requires matching streaming evidence', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealCitadelRoutingReconciliation.test.py'], {
    encoding: 'utf8', windowsHide: true,
  });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
