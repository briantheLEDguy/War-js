import { expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';

it('rejects mixed source atlases and keeps bounded rock channels coherent', () => {
  const run = spawnSync(process.env.PYTHON ?? 'python', ['-B', 'tests/unrealT1BuildingMaterials.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.status, run.stdout + run.stderr).toBe(0);
});
