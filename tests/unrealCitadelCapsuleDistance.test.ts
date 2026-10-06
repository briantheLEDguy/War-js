import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('independent capsule contact diagnostics cover full size, slopes, degeneracy and translated triangles', () => {
  const run=spawnSync('python',['-B','tests/unrealCitadelCapsuleDistance.test.py'],{encoding:'utf8',windowsHide:true});
  expect(run.error,run.error?.message).toBeUndefined();
  expect(run.status,run.stdout+run.stderr).toBe(0);
});
