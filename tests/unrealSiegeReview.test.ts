import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('siege admission requires current physical and rendered evidence', () => {
  const run = spawnSync('python', ['tests/unrealSiegeReview.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
