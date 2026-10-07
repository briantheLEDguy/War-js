import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expect, test } from 'vitest';

test('private owned architecture rebuilding preserves source occurrences and rejects unsafe transport', () => {
  const testFile = fileURLToPath(new URL('./unrealCitadelPrivateArchitectureRebuild.test.py', import.meta.url));
  const output = execFileSync('python', [testFile], { encoding: 'utf8', timeout: 30_000, stdio: 'pipe' });
  expect(output).not.toContain('FAILED');
});
