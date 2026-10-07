import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('authored furniture preserves original surfaces, facing and gameplay reservations', () => {
  const run=spawnSync('python',['-B','tests/unrealAegisCitadelFurnishings.test.py'],{encoding:'utf8',windowsHide:true});
  expect(run.error,run.error?.message).toBeUndefined();
  expect(run.status,run.stdout+run.stderr).toBe(0);
},30_000);
