import { getItemDefinition, INVENTORY_CAPACITY } from '../data/items';
import type { InventoryItem, QuestRewardItem } from '../services/types';

export type RewardInventoryItem = Omit<InventoryItem, 'slot'>;

/** Check capacity without consuming random gear rolls or changing existing stacks. */
export function canFitRewardItems(rewards: readonly QuestRewardItem[], inventory: readonly InventoryItem[]): boolean {
  const items = rewards.map((reward): RewardInventoryItem => {
    const definition = getItemDefinition(reward.key);
    return {
      key: reward.key,
      name: reward.name || definition?.name || reward.key,
      qty: reward.qty,
      kind: reward.kind ?? definition?.kind,
      equipSlot: reward.equipSlot ?? definition?.equipSlot,
      affix: reward.strengthRoll ? { strengthBonus: reward.strengthRoll.min } : undefined,
    };
  });
  return placeRewardItems(items, inventory).pendingItems.length === 0;
}

/** Simulate and commit the same placement rules so a full bag cannot discard a reward. */
export function placeRewardItems(items: readonly RewardInventoryItem[], inventory: readonly InventoryItem[]): {
  inventory: InventoryItem[];
  pendingItems: RewardInventoryItem[];
} {
  const next = inventory.map((item) => ({ ...item }));
  const pendingItems: RewardInventoryItem[] = [];
  const usedSlots = new Set(next.map((item) => item.slot));
  for (const item of items) {
    let remaining = item.qty;
    const stackable = !item.affix && !item.equipSlot && item.kind !== 'weapon' && item.kind !== 'armor';
    if (stackable) {
      for (const stack of next) {
        if (stack.key !== item.key || stack.affix || stack.equipSlot || stack.qty >= 99) continue;
        const amount = Math.min(99 - stack.qty, remaining);
        stack.qty += amount;
        remaining -= amount;
        if (remaining === 0) break;
      }
    }
    for (let slot = 0; slot < INVENTORY_CAPACITY && remaining > 0; slot++) {
      if (usedSlots.has(slot)) continue;
      const qty = stackable ? Math.min(99, remaining) : 1;
      next.push({ ...item, qty, slot });
      usedSlots.add(slot);
      remaining -= qty;
    }
    if (remaining > 0) pendingItems.push({ ...item, qty: remaining });
  }
  return { inventory: next, pendingItems };
}
