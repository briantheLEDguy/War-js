import { execFileSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';

describe('citadel development repair reconciliation', () => {
  it('requires a separate cold reload and preserves unrelated hashes, proofs and closed acceptance', () => {
    const result = execFileSync('python', ['-B', 'tests/unrealCitadelDevelopmentRepair.test.py'], {
      encoding: 'utf8', timeout: 30000, windowsHide: true, stdio: 'pipe',
    });
    expect(result).toBe('');
  });
});
