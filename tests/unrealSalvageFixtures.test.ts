import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { getSalvageOutputs } from '../src/data/crafting';
import type { InventoryItem } from '../src/services/types';
import { repoRoot } from '../scripts/unreal/toolchain';

const fixture = JSON.parse(readFileSync(path.join(repoRoot, 'migration/fixtures/salvage.json'), 'utf8')) as {
  schemaVersion: number; source: string; sourceSha256: string;
  cases: { name: string; item: InventoryItem; expected: ReturnType<typeof getSalvageOutputs> }[];
};
describe('native salvage reference fixtures', () => {
  it('tracks the current browser source and all strength thresholds', () => {
    expect(fixture.schemaVersion).toBe(1);
    expect(fixture.source).toBe('src/data/crafting.ts');
    expect(fixture.sourceSha256).toBe(createHash('sha256').update(readFileSync(path.join(repoRoot, fixture.source), 'utf8').replace(/\r\n/g, '\n')).digest('hex'));
    expect(fixture.cases).toHaveLength(25);
    expect(new Set(fixture.cases.map(row => row.name)).size).toBe(25);
  });
  for (const row of fixture.cases) it(row.name, () => {
    const before = structuredClone(row.item);
    expect(getSalvageOutputs(row.item)).toEqual(row.expected);
    expect(row.item).toEqual(before);
  });
});
