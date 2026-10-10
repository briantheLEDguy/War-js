import { expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';

it('preserves grounded assemblies and overlay fades while rejecting ambiguous or collapsed geometry', () => {
  const run = spawnSync(process.env.PYTHON ?? 'python', ['-B', 'tests/unrealT1CandidateRebase.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.status, run.stdout + run.stderr).toBe(0);
});
