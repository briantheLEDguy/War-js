import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { repoRoot } from '../scripts/unreal/toolchain';
import { verifyBrowserFixture } from '../scripts/unreal/verify-browser-fixtures';

describe('archived progression reference consumed by native automation', () => {
  it('preserves source provenance and threshold, growth and restoration cases', () => {
    verifyBrowserFixture('progression');
    const fixture = JSON.parse(readFileSync(path.join(repoRoot, 'migration/fixtures/progression.json'), 'utf8'));
    expect(fixture.cases).toHaveLength(9);
    expect(fixture.cases.find((entry: { xpReward: number }) => entry.xpReward === 650).expected)
      .toMatchObject({ level: 3, xp: 0, health: 140, mana: 120, strength: 14 });
    expect(fixture.cases.find((entry: { xpReward: number }) => entry.xpReward === 249).expected)
      .toMatchObject({ level: 1, xp: 249, health: 32, mana: 15 });
  });
});
