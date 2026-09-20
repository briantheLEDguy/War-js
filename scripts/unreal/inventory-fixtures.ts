import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { placeRewardItems, type RewardInventoryItem } from '../../src/game/RewardInventory';
import type { InventoryItem } from '../../src/services/types';
import { repoRoot } from './toolchain';

const material = (qty: number, key = 'ore'): RewardInventoryItem => ({ key, name: key, qty, kind: 'misc' });
const gear = (qty: number): RewardInventoryItem => ({ key: 'test_blade', name: 'Test blade', qty,
  kind: 'weapon', equipSlot: 'mainHand', affix: { strengthBonus: 7 } });
const full = Array.from({ length: 24 }, (_, slot) => ({ ...material(99, `material_${slot}`), slot }));
const cases: { name: string; inventory: InventoryItem[]; rewards: RewardInventoryItem[] }[] = [
  { name: 'empty_rewards_preserve_inventory', inventory: [{ ...material(4), slot: 7 }], rewards: [] },
  { name: 'fill_existing_stacks_then_lowest_hole', inventory: [{ ...material(98), slot: 7 }, { ...material(95), slot: 3 }], rewards: [material(110)] },
  { name: 'gear_instances_never_stack', inventory: [], rewards: [gear(3)] },
  { name: 'full_bag_defers_exact_rolled_gear', inventory: full, rewards: [gear(2)] },
  { name: 'full_bag_can_top_up_matching_stack', inventory: full.map(row => row.slot === 4 ? { ...row, qty: 97 } : row), rewards: [material(5, 'material_4')] },
  { name: 'one_hole_preserves_remaining_gear_and_materials', inventory: full.filter(row => row.slot !== 9), rewards: [gear(2), material(40)] },
  { name: 'affixed_material_is_an_individual_instance', inventory: [], rewards: [{ ...material(3), affix: { strengthBonus: 2 } }] },
];
const source = 'src/game/RewardInventory.ts';
const sourceText = readFileSync(path.join(repoRoot, source), 'utf8').replace(/\r\n/g, '\n');
const result = { schemaVersion: 1, source, sourceHashEncoding: 'utf8-lf', sourceSha256: createHash('sha256').update(sourceText).digest('hex'),
  cases: cases.map(test => ({ ...test, expected: placeRewardItems(test.rewards, test.inventory) })) };
const destination = path.join(repoRoot, 'migration/fixtures/inventory.json');
mkdirSync(path.dirname(destination), { recursive: true });
writeFileSync(destination, JSON.stringify(result, null, 2) + '\n');
console.log(`Captured ${cases.length} inventory scenarios from the browser implementation.`);
