import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('reference citadel preserves topology, physical stairs and stage gate coverage', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealAegisCitadel.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 75_000);
