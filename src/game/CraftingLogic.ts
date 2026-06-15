import {
  addProfessionXp,
  CRAFTING_RECIPES,
  CULTIVATION_SLOT_COUNT,
  getEnemyGatheringDefinition,
  getSalvageOutputs,
  getSeedDefinition,
  hasIngredients,
  isResourceNodeAvailable,
  normalizeCraftingState,
  professionLabel,
  rollGatheringLoot,
  rollGatheringLootTable,
  withResourceNodeCooldown,
  type CraftingRewardItem,
} from '../data/crafting';
import {
  getItemDefinition,
  INVENTORY_CAPACITY,
  resolveInventoryItem,
} from '../data/items';
import { services } from '../services';
import type {
  CraftingState,
  CraftingStationKind,
  InventoryItem,
} from '../services/types';
import { useGameStore } from '../state/gameStore';
import type { ResourceNodeSpawn } from '../world/ZoneLoader';
import { isInventoryItemEquipped } from './Equipment';

export function openCraftingStation(kind: CraftingStationKind, label: string): void {
  useGameStore.getState().openCrafting({ kind, label });
}

export function gatherEnemy(enemyId: string): boolean {
  const store = useGameStore.getState();
  const enemy = store.enemies.find((entry) => entry.id === enemyId);
  if (!enemy || enemy.alive || !enemy.gathering || enemy.gathering.harvested) return false;

  const definition = getEnemyGatheringDefinition(enemy.name);
  if (!definition) return false;

  const rewards = rollGatheringLoot(definition);
  const nextInventory = addRewardsToInventory(store.inventory, rewards);
  if (!nextInventory) {
    appendSystemMessage('Inventory full.');
    return true;
  }

  store.setInventory(nextInventory);
  store.updateEnemy(enemy.id, {
    gathering: {
      ...enemy.gathering,
      harvested: true,
    },
  });

  const nextCrafting = awardXp(store.craftingState, definition.professionId, definition.xp);
  store.setCraftingState(nextCrafting);
  store.completeGuidedTask('gather');
  persistInventoryAndCrafting(nextInventory, nextCrafting);
  appendSystemMessage(`${definition.actionLabel}: ${formatRewards(rewards)}.`);
  return true;
}

export function gatherResourceNode(zoneId: string, node: ResourceNodeSpawn): boolean {
  const store = useGameStore.getState();
  const character = store.character;
  if (!character) return false;

  const now = Date.now();
  if (!isResourceNodeAvailable(store.craftingState, zoneId, node.id, now)) {
    appendSystemMessage(`${node.label} is not ready to gather.`);
    return true;
  }

  const rewards = rollGatheringLootTable(node.loot);
  const nextInventory = addRewardsToInventory(store.inventory, rewards);
  if (!nextInventory) {
    appendSystemMessage('Inventory full.');
    return true;
  }

  const withXp = awardXp(store.craftingState, node.professionId, node.xp);
  const nextCrafting = withResourceNodeCooldown(
    withXp,
    zoneId,
    node.id,
    now + Math.max(1, node.respawnSeconds) * 1000,
    now,
  );

  store.setInventory(nextInventory);
  store.setCraftingState(nextCrafting);
  store.completeGuidedTask('gather');
  persistInventoryAndCrafting(nextInventory, nextCrafting);
  appendSystemMessage(`Gathered ${node.label}: ${formatRewards(rewards)}.`);
  return true;
}

export function craftRecipe(recipeId: string): boolean {
  const recipe = CRAFTING_RECIPES.find((entry) => entry.id === recipeId);
  if (!recipe) return false;

  const store = useGameStore.getState();
  const station = store.activeCraftingStation;
  if (station && station.kind !== 'general' && recipe.station !== station.kind) {
    appendSystemMessage(`${recipe.name} requires ${stationLabel(recipe.station)}.`);
    return false;
  }

  const progress = normalizeCraftingState(store.craftingState)
    .professions.find((entry) => entry.professionId === recipe.professionId);
  if ((progress?.rank ?? 1) < recipe.minRank) {
    appendSystemMessage(`${professionLabel(recipe.professionId)} rank ${recipe.minRank} required.`);
    return false;
  }

  if (!hasIngredients(store.inventory, recipe.inputs)) {
    appendSystemMessage('Missing ingredients.');
    return false;
  }

  const consumed = consumeIngredients(store.inventory, recipe.inputs);
  const nextInventory = addRewardsToInventory(consumed, recipe.outputs);
  if (!nextInventory) {
    appendSystemMessage('Inventory full.');
    return false;
  }

  const nextCrafting = awardXp(store.craftingState, recipe.professionId, recipe.xp);
  store.setInventory(nextInventory);
  store.setCraftingState(nextCrafting);
  store.completeGuidedTask('craft');
  persistInventoryAndCrafting(nextInventory, nextCrafting);
  appendSystemMessage(`Crafted: ${formatRewards(recipe.outputs)}.`);
  return true;
}

export function salvageInventorySlot(slot: number): boolean {
  const store = useGameStore.getState();
  const raw = store.inventory.find((item) => item.slot === slot);
  if (!raw) return false;
  const item = resolveInventoryItem(raw);

  if (isInventoryItemEquipped(raw, store.character?.equipment)) {
    appendSystemMessage('Unequip that item before salvaging.');
    return true;
  }

  const rewards = getSalvageOutputs(item);
  if (rewards.length === 0) {
    appendSystemMessage('That item cannot be salvaged.');
    return true;
  }

  const withoutItem = store.inventory.filter((entry) => entry.slot !== slot);
  const nextInventory = addRewardsToInventory(withoutItem, rewards);
  if (!nextInventory) {
    appendSystemMessage('Inventory full.');
    return true;
  }

  const nextCrafting = awardXp(store.craftingState, 'salvaging', 8);
  store.setInventory(nextInventory);
  store.setCraftingState(nextCrafting);
  store.completeGuidedTask('craft');
  persistInventoryAndCrafting(nextInventory, nextCrafting);
  appendSystemMessage(`Salvaged ${item.name}: ${formatRewards(rewards)}.`);
  return true;
}

export function plantCultivationSeed(seedKey: string, useSoil: boolean): boolean {
  const seed = getSeedDefinition(seedKey);
  if (!seed) return false;

  const store = useGameStore.getState();
  const craftingState = normalizeCraftingState(store.craftingState);
  if (craftingState.cultivationSlots.length >= CULTIVATION_SLOT_COUNT) {
    appendSystemMessage('Cultivation plots are full.');
    return true;
  }

  const inputs = [{ key: seedKey, qty: 1 }];
  if (useSoil && seed.bonusAdditiveKey) inputs.push({ key: seed.bonusAdditiveKey, qty: 1 });
  if (!hasIngredients(store.inventory, inputs)) {
    appendSystemMessage('Missing cultivation materials.');
    return true;
  }

  const now = Date.now();
  const slot = {
    id: `cultivation-${now}-${Math.random().toString(36).slice(2, 7)}`,
    seedKey,
    plantedAt: now,
    readyAt: now + seed.durationMs,
    additives: useSoil && seed.bonusAdditiveKey ? [seed.bonusAdditiveKey] : [],
  };
  const nextInventory = consumeIngredients(store.inventory, inputs);
  const nextCrafting = {
    ...craftingState,
    cultivationSlots: [...craftingState.cultivationSlots, slot],
  };

  store.setInventory(nextInventory);
  store.setCraftingState(nextCrafting);
  store.completeGuidedTask('craft');
  persistInventoryAndCrafting(nextInventory, nextCrafting);
  appendSystemMessage(`Planted: ${seed.name}.`);
  return true;
}

export function harvestCultivationSlot(slotId: string): boolean {
  const store = useGameStore.getState();
  const craftingState = normalizeCraftingState(store.craftingState);
  const slot = craftingState.cultivationSlots.find((entry) => entry.id === slotId);
  if (!slot) return false;
  if (slot.readyAt > Date.now()) {
    appendSystemMessage('The crop is not ready.');
    return true;
  }

  const seed = getSeedDefinition(slot.seedKey);
  if (!seed) return false;
  const rewards = [
    ...seed.outputs,
    ...(seed.bonusAdditiveKey && slot.additives.includes(seed.bonusAdditiveKey)
      ? seed.bonusOutputs ?? []
      : []),
  ];
  const nextInventory = addRewardsToInventory(store.inventory, rewards);
  if (!nextInventory) {
    appendSystemMessage('Inventory full.');
    return true;
  }

  const nextCrafting = awardXp({
    ...craftingState,
    cultivationSlots: craftingState.cultivationSlots.filter((entry) => entry.id !== slotId),
  }, 'cultivation', seed.xp);
  store.setInventory(nextInventory);
  store.setCraftingState(nextCrafting);
  store.completeGuidedTask('craft');
  persistInventoryAndCrafting(nextInventory, nextCrafting);
  appendSystemMessage(`Harvested: ${formatRewards(rewards)}.`);
  return true;
}

function awardXp(
  state: CraftingState,
  professionId: Parameters<typeof addProfessionXp>[1],
  xp: number,
): CraftingState {
  return addProfessionXp(normalizeCraftingState(state), professionId, xp);
}

function consumeIngredients(
  inventory: InventoryItem[],
  ingredients: Array<{ key: string; qty: number }>,
): InventoryItem[] {
  const remaining = new Map(ingredients.map((entry) => [entry.key, entry.qty]));
  const next: InventoryItem[] = [];

  for (const item of inventory) {
    const needed = remaining.get(item.key) ?? 0;
    if (needed <= 0) {
      next.push({ ...item });
      continue;
    }

    const used = Math.min(item.qty, needed);
    remaining.set(item.key, needed - used);
    if (item.qty > used) next.push({ ...item, qty: item.qty - used });
  }

  return next;
}

function addRewardsToInventory(
  inventory: InventoryItem[],
  rewards: CraftingRewardItem[],
): InventoryItem[] | null {
  let next = inventory.map((item) => ({ ...item }));
  for (const reward of rewards) {
    const item = makeInventoryItem(reward);
    const added = addInventoryItem(next, item);
    if (!added) return null;
    next = added;
  }
  return next.sort((a, b) => a.slot - b.slot);
}

function addInventoryItem(
  inventory: InventoryItem[],
  item: Omit<InventoryItem, 'slot'>,
): InventoryItem[] | null {
  const next = inventory.map((entry) => ({ ...entry }));
  const stackable =
    !item.affix &&
    !item.equipSlot &&
    item.kind !== 'weapon' &&
    item.kind !== 'armor';

  if (stackable) {
    let remaining = item.qty;
    for (const existing of next) {
      if (existing.key !== item.key || existing.qty >= 99) continue;
      const amount = Math.min(99 - existing.qty, remaining);
      existing.qty += amount;
      remaining -= amount;
      if (remaining <= 0) return next;
    }
    while (remaining > 0) {
      const slot = firstFreeSlot(next);
      if (slot === null) return null;
      const qty = Math.min(99, remaining);
      next.push({ ...item, slot, qty });
      remaining -= qty;
    }
    return next;
  }

  for (let i = 0; i < item.qty; i += 1) {
    const slot = firstFreeSlot(next);
    if (slot === null) return null;
    next.push({ ...item, slot, qty: 1 });
  }
  return next;
}

function firstFreeSlot(inventory: InventoryItem[]): number | null {
  const used = new Set(inventory.map((item) => item.slot));
  for (let slot = 0; slot < INVENTORY_CAPACITY; slot += 1) {
    if (!used.has(slot)) return slot;
  }
  return null;
}

function makeInventoryItem(reward: CraftingRewardItem): Omit<InventoryItem, 'slot'> {
  const def = getItemDefinition(reward.key);
  return {
    key: reward.key,
    name: reward.name ?? def?.name ?? reward.key,
    qty: reward.qty,
    icon: def?.icon,
    kind: reward.kind ?? def?.kind,
    equipSlot: reward.equipSlot ?? def?.equipSlot,
    affix: reward.strengthRoll
      ? { strengthBonus: randomInt(reward.strengthRoll.min, reward.strengthRoll.max) }
      : undefined,
  };
}

function persistInventoryAndCrafting(inventory: InventoryItem[], craftingState: CraftingState): void {
  const characterId = useGameStore.getState().character?.id;
  if (!characterId) return;
  void services.inventory.update(characterId, inventory).catch(() => {});
  void services.crafting.update(characterId, craftingState).catch(() => {});
}

function appendSystemMessage(body: string): void {
  useGameStore.getState().appendChat({
    id: `crafting-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    channel: 'system',
    from: 'System',
    body,
    timestamp: Date.now(),
  });
}

function formatRewards(rewards: CraftingRewardItem[]): string {
  return rewards
    .map((reward) => {
      const name = reward.name ?? getItemDefinition(reward.key)?.name ?? reward.key;
      return reward.qty > 1 ? `${name} x${reward.qty}` : name;
    })
    .join(', ');
}

function stationLabel(station: CraftingStationKind): string {
  switch (station) {
    case 'apothecary': return 'an apothecary table';
    case 'talisman_making': return 'a talisman workbench';
    case 'cultivation': return 'a cultivation plot';
    case 'salvage': return 'a salvage bench';
    case 'general': return 'a crafting station';
    default: return 'a crafting station';
  }
}

function randomInt(min: number, max: number): number {
  return Math.floor(min + Math.random() * (max - min + 1));
}
