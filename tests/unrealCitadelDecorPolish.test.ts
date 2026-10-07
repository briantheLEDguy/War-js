import { execFileSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';

describe('private citadel decor polish', () => {
  it('preserves fixture geometry while bounding lighting and paint changes', () => {
    const result = execFileSync('python', ['tests/unrealCitadelDecorPolish.test.py'], {
      encoding: 'utf8', timeout: 30000, stdio: 'pipe',
    });
    expect(result).toBe('');
  });
});
