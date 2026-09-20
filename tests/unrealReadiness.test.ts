import { describe, expect, it } from 'vitest';
import { releaseBlockers } from '../scripts/unreal/migration';
import { inspectToolchain } from '../scripts/unreal/toolchain';

describe('Unreal release acceptance', () => {
  it('refuses missing content even when asset approval booleans are accidentally true', () => {
    const result = releaseBlockers({ assets: { assignmentCount: 0, ready: 0, blocked: 0, packagingReady: true }, features: [], toolchain: inspectToolchain(undefined) });
    expect(result.some(value => value.startsWith('Model coverage'))).toBe(true);
    expect(result).toContain('The feature parity ledger is empty.');
  });
  it('does not equate passing JSON/asset existence checks with native release acceptance', () => {
    const result = releaseBlockers({ assets: { assignmentCount: 48, ready: 48, blocked: 0, packagingReady: true },
      features: [{ id: 'combat', unrealStatus: 'verified' }], toolchain: { ...inspectToolchain(undefined), blockers: [] } });
    expect(result).toHaveLength(2);
    expect(result.join(' ')).toContain('packaged build/playtest');
    expect(result.join(' ')).toContain('Steam ownership');
  });
  it('reports incomplete features and models without removing them from the contract', () => {
    const result = releaseBlockers({ assets: { assignmentCount: 48, ready: 5, blocked: 43, packagingReady: false },
      features: [{ id: 'gm-terrain', unrealStatus: 'pending' }], toolchain: { ...inspectToolchain(undefined), blockers: [] } });
    expect(result.join(' ')).toContain('5/48');
    expect(result.join(' ')).toContain('gm-terrain');
  });
});
