import { execFileSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';

describe('citadel decor placement contracts', () => {
  it('rejects blocked, unsupported and unreviewed placements', () => {
    expect(() => execFileSync('python', ['tests/unrealCitadelDecor.test.py'], {
      cwd: process.cwd(), encoding: 'utf8', stdio: 'pipe', timeout: 60_000,
    })).not.toThrow();
  });
});
