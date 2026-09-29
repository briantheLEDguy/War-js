import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('Dutch Bastion frontage and authored mesh contracts', () => {
  const run = spawnSync('python', ['tests/unrealDutchBastion.test.py'], { encoding: 'utf8' });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);

test('city revision exports stable buildings, preserved sites and district venues', () => {
  const run = spawnSync('python', ['tests/unrealDutchRevision.test.py'], { encoding: 'utf8' });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);
