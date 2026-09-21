import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { getSalvageOutputs } from '../../src/data/crafting';
import type { InventoryItem } from '../../src/services/types';
import { repoRoot } from './toolchain';

const source = 'src/data/crafting.ts';
const cases = (['weapon', 'chest', 'shoulders', 'legs', 'neck'] as const).flatMap(kind =>
  [0, 1, 2, 3, 7].map(strength => {
    const item: InventoryItem = { key: 'fixture_gear', name: 'Fixture gear', slot: 0, qty: 1,
      kind: kind === 'weapon' ? 'weapon' : 'armor', equipSlot: kind === 'weapon' ? 'mainHand' : kind,
      ...(strength ? { affix: { strengthBonus: strength } } : {}) };
    return { name: `${kind}_strength_${strength}`, item, expected: getSalvageOutputs(item) };
  }));
writeFileSync(path.join(repoRoot, 'migration/fixtures/salvage.json'), JSON.stringify({ schemaVersion: 1, source,
  sourceSha256: createHash('sha256').update(readFileSync(path.join(repoRoot, source), 'utf8').replace(/\r\n/g, '\n')).digest('hex'), cases }, null, 2) + '\n');
console.log(`Captured ${cases.length} browser salvage cases.`);
