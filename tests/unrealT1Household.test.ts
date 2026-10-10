import { expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';

it('reserves household door aisles and preserves source bed component pivots', () => {
  const run = spawnSync(process.env.PYTHON ?? 'python', ['-B', 'tests/unrealT1Household.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.status, run.stdout + run.stderr).toBe(0);
});
