import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test.each([
  ['wing hierarchy and window crown clearance', 'tests/unrealAegisCitadelWingHierarchy.test.py'],
  ['versioned native wing ground evidence', 'tests/unrealCitadelWingSupport.test.py'],
])('%s', (_description, file) => {
  const run = spawnSync('python', ['-B', file], { encoding: 'utf8', windowsHide: true });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
