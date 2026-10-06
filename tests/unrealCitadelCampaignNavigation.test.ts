import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('private campaign navigation receipts require unchanged baked data in a fresh native reload', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealCitadelCampaignNavigation.test.py'], {
    encoding: 'utf8', windowsHide: true,
  });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
