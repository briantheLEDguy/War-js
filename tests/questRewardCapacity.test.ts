import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { QUESTS_BY_ID } from '../src/data/quests';
import { createInventoryItem, INVENTORY_CAPACITY } from '../src/data/items';
import { questRewardInventoryBlocker, turnInQuest } from '../src/game/QuestLogic';
import { canFitRewardItems, placeRewardItems } from '../src/game/RewardInventory';
import { services } from '../src/services';
import type { QuestProgress, QuestRewardItem } from '../src/services/types';
import { useGameStore } from '../src/state/gameStore';
import { makeCharacter, resetGameStore } from './testUtils';

function fullInventory() {
  return Array.from({ length: INVENTORY_CAPACITY }, (_, slot) => createInventoryItem('sword_iron', slot));
}

function ready(questId: string): QuestProgress {
  return {
    questId, status: 'ready_to_turn_in',
    counters: Object.fromEntries(QUESTS_BY_ID[questId].objectives.map((objective) => [objective.id, objective.required])),
  };
}

describe('quest reward capacity', () => {
  beforeEach(() => {
    resetGameStore();
    useGameStore.setState({ inventory: [], quests: [], chat: [] });
    vi.spyOn(services.inventory, 'update').mockResolvedValue();
    vi.spyOn(services.quests, 'update').mockResolvedValue();
    vi.spyOn(services.characters, 'save').mockResolvedValue();
  });

  afterEach(() => vi.restoreAllMocks());

  test.each([
    { questId: 'dawnline-04-keep', race: 'empire' as const, zoneId: 'brightfen_approach' },
    { questId: 'cinderfen-04-keep', race: 'greenskin' as const, zoneId: 'cinderfen_outskirts' },
  ])('$questId remains ready with a full bag and grants its gear exactly once after freeing a slot', ({ questId, race, zoneId }) => {
    useGameStore.getState().setCharacter(makeCharacter({ race, zoneId, level: 8, xp: 0, gold: 7 }));
    useGameStore.getState().setQuests([ready(questId)]);
    const inventory = fullInventory();
    inventory[0] = createInventoryItem('jewel_amulet_bloodglass', 0);
    useGameStore.getState().setInventory(inventory);
    const random = vi.spyOn(Math, 'random').mockReturnValue(0);
    const character = useGameStore.getState().character;
    const before = structuredClone(inventory);
    expect(questRewardInventoryBlocker(QUESTS_BY_ID[questId].reward, inventory)).toMatch(/empty slot/);

    turnInQuest(questId);
    expect(useGameStore.getState().quests).toEqual([ready(questId)]);
    expect(useGameStore.getState().character).toEqual(character);
    expect(useGameStore.getState().inventory).toEqual(before);
    expect(useGameStore.getState().chat.at(-1)?.body).toMatch(/Cannot complete.*Make room.*empty slot/);
    expect(random).not.toHaveBeenCalled();
    expect(services.quests.update).not.toHaveBeenCalled();
    expect(services.inventory.update).not.toHaveBeenCalled();
    expect(services.characters.save).not.toHaveBeenCalled();

    useGameStore.getState().setInventory(inventory.filter((item) => item.slot !== 5));
    turnInQuest(questId);
    expect(useGameStore.getState().quests[0].status).toBe('completed');
    expect(useGameStore.getState().character).toMatchObject({ xp: 650, gold: 67 });
    expect(useGameStore.getState().inventory.find((item) => item.slot === 5)).toMatchObject({
      key: 'jewel_amulet_bloodglass', qty: 1, equipSlot: 'neck', affix: { strengthBonus: 3 },
    });
    expect(random).toHaveBeenCalledTimes(1);
    turnInQuest(questId);
    expect(random).toHaveBeenCalledTimes(1);
    expect(services.quests.update).toHaveBeenCalledTimes(1);
    expect(services.inventory.update).toHaveBeenCalledTimes(1);
    expect(services.characters.save).toHaveBeenCalledTimes(1);
  });

  test('completes a consumable reward in a full bag when its existing stack has enough room', () => {
    const questId = 'dawnline-01-scouting';
    useGameStore.getState().setCharacter(makeCharacter({ zoneId: 'brightfen_approach' }));
    useGameStore.getState().setQuests([ready(questId)]);
    const inventory = fullInventory();
    inventory[0] = createInventoryItem('potion_health', 0, { qty: 96 });
    useGameStore.getState().setInventory(inventory);
    expect(questRewardInventoryBlocker(QUESTS_BY_ID[questId].reward, inventory)).toBeNull();
    turnInQuest(questId);
    expect(useGameStore.getState().quests[0].status).toBe('completed');
    expect(useGameStore.getState().inventory[0].qty).toBe(99);
    expect(useGameStore.getState().inventory).toHaveLength(INVENTORY_CAPACITY);
    expect(inventory[0].qty).toBe(96);
  });

  test('does not partially grant a multi-item quest when only one reward fits', () => {
    const questId = 'dawnline-02-guards';
    useGameStore.getState().setCharacter(makeCharacter({ zoneId: 'brightfen_approach' }));
    useGameStore.getState().setQuests([ready(questId)]);
    const inventory = fullInventory();
    inventory[0] = createInventoryItem('potion_mana', 0, { qty: 96 });
    useGameStore.getState().setInventory(inventory);
    turnInQuest(questId);
    expect(useGameStore.getState().quests[0].status).toBe('ready_to_turn_in');
    expect(useGameStore.getState().inventory[0].qty).toBe(96);
    expect(useGameStore.getState().character).toMatchObject({ xp: 0, gold: 0 });
    useGameStore.getState().setInventory(inventory.slice(0, -1));
    turnInQuest(questId);
    expect(useGameStore.getState().quests[0].status).toBe('completed');
    expect(useGameStore.getState().inventory[0].qty).toBe(99);
    expect(useGameStore.getState().inventory.find((item) => item.key === 'bread')?.qty).toBe(2);
  });
});

describe('shared reward inventory placement', () => {
  test('preflights repeated rewards cumulatively without rolling or mutating stacks', () => {
    const inventory = fullInventory();
    inventory[0] = createInventoryItem('potion_health', 0, { qty: 97 });
    const item: QuestRewardItem = { key: 'potion_health', name: 'Health Potion', qty: 1 };
    expect(canFitRewardItems([item, item], inventory)).toBe(true);
    expect(canFitRewardItems([item, item, item], inventory)).toBe(false);
    expect(inventory[0].qty).toBe(97);
  });

  test('splits consumable overflow into additional slots and preserves every item', () => {
    const inventory = [createInventoryItem('potion_health', 0, { qty: 98 })];
    const placement = placeRewardItems([{ key: 'potion_health', name: 'Health Potion', kind: 'consumable', qty: 102 }], inventory);
    expect(placement.pendingItems).toEqual([]);
    expect(placement.inventory.map((item) => item.qty)).toEqual([99, 99, 2]);
    expect(inventory[0].qty).toBe(98);
  });

  test('requires separate slots for multiple pieces of equipment', () => {
    const reward: QuestRewardItem = { key: 'jewel_amulet_bloodglass', name: 'Amulet', qty: 2 };
    expect(canFitRewardItems([reward], fullInventory().slice(1))).toBe(false);
    expect(canFitRewardItems([reward], fullInventory().slice(2))).toBe(true);
    const placement = placeRewardItems([{ ...reward, equipSlot: 'neck', kind: 'armor' }], []);
    expect(placement.inventory.map((item) => ({ slot: item.slot, qty: item.qty }))).toEqual([{ slot: 0, qty: 1 }, { slot: 1, qty: 1 }]);
    expect(placement.pendingItems).toEqual([]);
  });
});
