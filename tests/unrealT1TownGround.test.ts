import { expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';

it('preserves regional seams and complete house assemblies on independent terrain foundations', () => {
  const run = spawnSync(process.env.PYTHON ?? 'python', ['-B', 'tests/unrealT1TownGround.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.status, run.stdout + run.stderr).toBe(0);
});

it('selects a new region review without replacing the retained other-region launch', () => {
  const run = spawnSync(process.env.PYTHON ?? 'python', ['-B', 'tests/unrealT1Review.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.status, run.stdout + run.stderr).toBe(0);
});
