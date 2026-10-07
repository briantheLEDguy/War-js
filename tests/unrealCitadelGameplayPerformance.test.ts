import { execFileSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';

describe('citadel gameplay performance diagnostics', () => {
  it('requires comparable uncapped rendered windows and keeps isolation separate from delivered improvements', () => {
    const result = execFileSync('python', ['-B', 'tests/unrealCitadelGameplayPerformance.test.py'], {
      encoding: 'utf8', timeout: 30000, stdio: 'pipe',
    });
    expect(result).toBe('');
  });
});
