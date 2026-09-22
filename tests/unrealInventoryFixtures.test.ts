import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { placeRewardItems, type RewardInventoryItem } from '../shared/game/RewardInventory';
import type { InventoryItem } from '../shared/services/types';
import { repoRoot } from '../scripts/unreal/toolchain';
import { readBrowserReference } from '../scripts/unreal/browser-reference';

const fixture = JSON.parse(readFileSync(path.join(repoRoot, 'migration/fixtures/inventory.json'), 'utf8')) as {
  schemaVersion: number; source: string; sourceHashEncoding: string; sourceSha256: string;
  cases: { name: string; inventory: InventoryItem[]; rewards: RewardInventoryItem[];
    expected: ReturnType<typeof placeRewardItems> }[];
};

describe('native inventory reference fixtures', () => {
  it('requires fixtures from the current browser implementation', () => {
    expect(fixture.schemaVersion).toBe(1);
    expect(fixture.source).toBe('src/game/RewardInventory.ts');
    expect(fixture.sourceHashEncoding).toBe('utf8-lf');
    expect(fixture.sourceSha256).toBe(createHash('sha256').update(readBrowserReference(fixture.source)).digest('hex'));
    expect(fixture.cases).toHaveLength(7);
    expect(new Set(fixture.cases.map(row => row.name)).size).toBe(fixture.cases.length);
  });
  for (const row of fixture.cases) {
    it(row.name, () => {
      const before = structuredClone(row.inventory);
      expect(placeRewardItems(row.rewards, row.inventory)).toEqual(row.expected);
      expect(row.inventory).toEqual(before);
    });
  }
});
