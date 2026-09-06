import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { buildCampaignSnapshot, campaignKeepCaptureReward, type CampaignClaimResult } from '../src/data/campaign';
import { createInventoryItem, INVENTORY_CAPACITY } from '../src/data/items';
import {
  campaignRewardInventoryBlocker,
  claimPendingCampaignReward,
  restoreCampaignRewardNotice,
  settleCampaignReward,
} from '../src/game/CampaignRewards';
import { services } from '../src/services';
import { useGameStore } from '../src/state/gameStore';
import { makeCharacter, resetGameStore } from './testUtils';

const characterId = 'campaign-reward-character';

function claim(overrides: Partial<CampaignClaimResult> = {}): CampaignClaimResult {
  const snapshot = buildCampaignSnapshot('brightfen_approach');
  const objective = snapshot.activeZone!.objectives.find((entry) => entry.type === 'keep')!;
  return {
    activity: 'capture',
    snapshot,
    zoneId: 'brightfen_approach',
    objectiveId: objective.id,
    realm: 'aegis',
    objective,
    reward: campaignKeepCaptureReward('brightfen_approach'),
    zoneControlChanged: true,
    ...overrides,
  };
}

function fullInventory() {
  return Array.from({ length: INVENTORY_CAPACITY }, (_, slot) => createInventoryItem('sword_iron', slot));
}

describe('campaign reward settlement', () => {
  let saved: Map<string, string>;

  beforeEach(() => {
    resetGameStore();
    saved = new Map();
    vi.stubGlobal('localStorage', {
      getItem: vi.fn((key: string) => saved.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => { saved.set(key, value); }),
      removeItem: vi.fn((key: string) => { saved.delete(key); }),
    });
    useGameStore.setState({ inventory: [], chat: [], campaignRewardNotice: null });
    useGameStore.getState().setCharacter(makeCharacter({ id: characterId, level: 1, xp: 0, gold: 7 }));
    vi.spyOn(services.inventory, 'update').mockResolvedValue();
    vi.spyOn(services.characters, 'save').mockResolvedValue();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  test('requires one free slot for keep gear, including when an identical amulet is owned', () => {
    const inventory = fullInventory();
    inventory[0] = createInventoryItem('jewel_amulet_bloodglass', 0);
    const reward = claim().reward;
    const before = structuredClone(inventory);
    const random = vi.spyOn(Math, 'random');
    expect(campaignRewardInventoryBlocker(reward, inventory)).toMatch(/Make room/);
    expect(campaignRewardInventoryBlocker(reward, inventory.slice(1))).toBeNull();
    expect(campaignRewardInventoryBlocker({ xp: 50, influence: 35 }, inventory)).toBeNull();
    expect(inventory).toEqual(before);
    expect(random).not.toHaveBeenCalled();
  });

  test('preflight accounts for shared consumable stacks and their limits', () => {
    const inventory = fullInventory();
    inventory[0] = createInventoryItem('potion_health', 0, { qty: 97 });
    const reward = {
      xp: 0, influence: 0,
      items: [{ key: 'potion_health', name: 'Health Potion', qty: 1 }],
    };
    expect(campaignRewardInventoryBlocker({ ...reward, items: [...reward.items, ...reward.items] }, inventory)).toBeNull();
    expect(campaignRewardInventoryBlocker({ ...reward, items: [{ ...reward.items[0], qty: 3 }] }, inventory)).toMatch(/Make room/);
    expect(inventory[0].qty).toBe(97);
  });

  test('awards XP, gold and rolled gear, levels up, and persists the resulting character and inventory', () => {
    const result = claim();
    vi.spyOn(Math, 'random').mockReturnValue(0);
    settleCampaignReward(result, characterId);
    const state = useGameStore.getState();
    expect(state.character).toMatchObject({ level: 2, xp: 50, gold: 37, maxHealth: 200, health: 200 });
    expect(state.inventory).toEqual([expect.objectContaining({
      key: 'jewel_amulet_bloodglass', equipSlot: 'neck', slot: 0, qty: 1, affix: { strengthBonus: 8 },
    })]);
    expect(state.campaignRewardNotice).toEqual({
      characterId,
      title: `Captured ${result.objective.label}`,
      zoneId: result.zoneId,
      xp: 300,
      gold: 30,
      influence: 0,
      itemNames: ["Brightfen Approach Victor's Amulet"],
      zoneControlChanged: true,
      pendingItems: [],
    });
    expect(services.inventory.update).toHaveBeenCalledWith(characterId, state.inventory);
    expect(services.characters.save).toHaveBeenCalledWith(characterId, {
      xp: 50, gold: 37, level: 2, maxHealth: 200, maxMana: 70, health: 200, mana: 70, strength: 16,
    });
    expect(saved.size).toBe(0);
    state.setCampaignRewardNotice(null);
    expect(useGameStore.getState().campaignRewardNotice).toBeNull();
  });

  test('defense creates a receipt without requiring an item or optional gold', () => {
    settleCampaignReward(claim({
      activity: 'defend', reward: { xp: 50, influence: 35 }, zoneControlChanged: false,
    }), characterId);
    expect(useGameStore.getState().character).toMatchObject({ xp: 50, gold: 7 });
    expect(useGameStore.getState().campaignRewardNotice).toMatchObject({
      title: expect.stringMatching(/^Defended /), xp: 50, gold: 0, influence: 35, itemNames: [],
      zoneControlChanged: false, pendingItems: [],
    });
  });

  test('ignores a result for a different or logged-out character without mutation or persistence', () => {
    const result = claim();
    const before = useGameStore.getState().character;
    settleCampaignReward(result, 'different-character');
    expect(useGameStore.getState().character).toBe(before);
    useGameStore.getState().setCharacter(null);
    settleCampaignReward(result, characterId);
    expect(useGameStore.getState().inventory).toEqual([]);
    expect(useGameStore.getState().campaignRewardNotice).toBeNull();
    expect(services.characters.save).not.toHaveBeenCalled();
    expect(services.inventory.update).not.toHaveBeenCalled();
    expect(saved.size).toBe(0);
  });

  test('does not settle the same claim result twice', () => {
    const result = claim();
    settleCampaignReward(result, characterId);
    const state = useGameStore.getState();
    settleCampaignReward(result, characterId);
    expect(useGameStore.getState().character).toEqual(state.character);
    expect(useGameStore.getState().inventory).toEqual(state.inventory);
    expect(services.characters.save).toHaveBeenCalledTimes(1);
    expect(services.inventory.update).toHaveBeenCalledTimes(1);
  });

  test('holds full-bag gear through reload and collects the original roll without repeating XP or gold', () => {
    useGameStore.getState().setInventory(fullInventory());
    vi.spyOn(Math, 'random').mockReturnValue(0.99);
    settleCampaignReward(claim(), characterId);
    const awardedCharacter = useGameStore.getState().character;
    const held = useGameStore.getState().campaignRewardNotice!.pendingItems;
    expect(held).toEqual([expect.objectContaining({ affix: { strengthBonus: 10 } })]);
    expect(useGameStore.getState().inventory).toHaveLength(INVENTORY_CAPACITY);
    expect(claimPendingCampaignReward(characterId)).toBe(false);

    useGameStore.setState({ campaignRewardNotice: null });
    restoreCampaignRewardNotice(characterId);
    expect(useGameStore.getState().campaignRewardNotice!.pendingItems).toEqual(held);
    useGameStore.getState().setInventory(fullInventory().slice(1));
    vi.mocked(Math.random).mockReturnValue(0);
    expect(claimPendingCampaignReward(characterId)).toBe(true);
    expect(useGameStore.getState().inventory.find((item) => item.key === 'jewel_amulet_bloodglass'))
      .toMatchObject({ slot: 0, affix: { strengthBonus: 10 } });
    expect(useGameStore.getState().character).toEqual(awardedCharacter);
    expect(useGameStore.getState().campaignRewardNotice!.pendingItems).toEqual([]);
    expect(claimPendingCampaignReward(characterId)).toBe(false);
    expect(services.characters.save).toHaveBeenCalledTimes(1);
    expect(saved.size).toBe(0);
  });

  test('keeps pending gear separate across characters and does not collect another character’s receipt', () => {
    useGameStore.getState().setInventory(fullInventory());
    settleCampaignReward(claim(), characterId);
    useGameStore.getState().setCharacter(makeCharacter({ id: 'other-character' }));
    useGameStore.getState().setInventory([]);
    expect(claimPendingCampaignReward(characterId)).toBe(false);
    restoreCampaignRewardNotice('other-character');
    expect(useGameStore.getState().campaignRewardNotice).toBeNull();
    settleCampaignReward(claim({ reward: { xp: 50, influence: 35 } }), 'other-character');
    useGameStore.getState().setCharacter(makeCharacter({ id: characterId }));
    restoreCampaignRewardNotice(characterId);
    expect(useGameStore.getState().campaignRewardNotice?.characterId).toBe(characterId);
    expect(claimPendingCampaignReward(characterId)).toBe(true);
    expect(useGameStore.getState().inventory).toHaveLength(1);
  });

  test('retains earlier pending gear if a second completed claim arrives before collection', () => {
    useGameStore.getState().setInventory(fullInventory());
    settleCampaignReward(claim(), characterId);
    settleCampaignReward(claim(), characterId);
    expect(useGameStore.getState().campaignRewardNotice!.pendingItems).toHaveLength(2);
    useGameStore.getState().setInventory(fullInventory().slice(2));
    expect(claimPendingCampaignReward(characterId)).toBe(true);
    expect(useGameStore.getState().inventory.filter((item) => item.key === 'jewel_amulet_bloodglass')).toHaveLength(2);
  });

  test('ignores corrupt saved pending rewards', () => {
    saved.set(`war-js:pending-campaign-reward:${characterId}`, '{malformed');
    restoreCampaignRewardNotice(characterId);
    expect(useGameStore.getState().campaignRewardNotice).toBeNull();
    saved.set(`war-js:pending-campaign-reward:${characterId}`, JSON.stringify({ characterId, pendingItems: [{ key: 'sword_iron', qty: -1 }] }));
    restoreCampaignRewardNotice(characterId);
    expect(useGameStore.getState().campaignRewardNotice).toBeNull();
    saved.set(`war-js:pending-campaign-reward:${characterId}`, JSON.stringify({ characterId, pendingItems: [{ key: 'sword_iron', name: 'Sword', qty: 1 }] }));
    restoreCampaignRewardNotice(characterId);
    expect(useGameStore.getState().campaignRewardNotice).toBeNull();
  });
});
