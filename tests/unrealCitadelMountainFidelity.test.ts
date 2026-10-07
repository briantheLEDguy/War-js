import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expect,test } from 'vitest';

test('CPU mountain fidelity geometry preserves native inputs and protected terrain',()=>{
  const run=spawnSync(process.env.PYTHON ?? 'python',['-B',fileURLToPath(new URL('./unrealCitadelMountainFidelity.test.py',import.meta.url))],{
    encoding:'utf8',windowsHide:true,
  });
  expect(run.error,run.error?.message).toBeUndefined();
  expect(run.status,run.stdout+run.stderr).toBe(0);
},30_000);
