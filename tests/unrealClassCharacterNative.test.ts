import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';

test('native class-body conversion preserves exact roster identity and verified candidate selection', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealClassCharacterNative.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.error, String(run.error)).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
});
