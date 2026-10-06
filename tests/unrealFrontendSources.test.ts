import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('frontend and siege bindings resolve the same shared cities and reject stale content', () => {
  const run = spawnSync('python', ['tests/unrealFrontendSources.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
