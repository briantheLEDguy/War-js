import { afterEach, describe, expect, test, vi } from 'vitest';
import {
  createDefaultCraftingState,
  getProfessionProgress,
  normalizeCraftingState,
  resourceNodeCooldownKey,
} from '../src/data/crafting';
import { gatherResourceNode } from '../src/game/CraftingLogic';
import type { InventoryItem } from '../src/services/types';
import { INVENTORY_CAPACITY } from '../src/data/items';
import { useGameStore } from '../src/state/gameStore';
import type { ResourceNodeSpawn } from '../src/world/ZoneLoader';
import { makeCharacter, resetGameStore } from './testUtils';

const node: ResourceNodeSpawn = {
  id: 'test_herb_node',
  label: 'Test Herb Patch',
  kind: 'herb',
  professionId: 'cultivation',
  x: 0,
  z: 0,
  radius: 5,
  xp: 8,
  respawnSeconds: 90,
  visualPropId: 'test_herb_node_visual',
  loot: [
    { key: 'craft_mandrake_root', qty: 1, chance: 1, minQty: 2, maxQty: 2 },
  ],
};

describe('resource node gathering', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('grants loot, profession XP, and a cooldown', () => {
    vi.spyOn(Date, 'now').mockReturnValue(1_000);
    resetGameStore();
    useGameStore.getState().setCharacter(makeCharacter());
    useGameStore.setState({ inventory: [], craftingState: createDefaultCraftingState() });

    expect(gatherResourceNode('dawnline_expanse', node)).toBe(true);

    const state = useGameStore.getState();
    expect(state.inventory).toEqual([
      expect.objectContaining({ key: 'craft_mandrake_root', qty: 2 }),
    ]);
    expect(getProfessionProgress(state.craftingState, 'cultivation').xp).toBe(8);
    expect(
      state.craftingState.resourceNodeCooldowns[resourceNodeCooldownKey('dawnline_expanse', node.id)],
    ).toBe(91_000);
  });

  test('does not gather while the node is still cooling down', () => {
    vi.spyOn(Date, 'now').mockReturnValue(2_000);
    resetGameStore();
    useGameStore.getState().setCharacter(makeCharacter());
    useGameStore.setState({
      inventory: [],
      craftingState: {
        ...createDefaultCraftingState(),
        resourceNodeCooldowns: {
          [resourceNodeCooldownKey('dawnline_expanse', node.id)]: 99_000,
        },
      },
    });

    expect(gatherResourceNode('dawnline_expanse', node)).toBe(true);
    expect(useGameStore.getState().inventory).toHaveLength(0);
  });

  test('does not set a cooldown when inventory is full', () => {
    vi.spyOn(Date, 'now').mockReturnValue(3_000);
    resetGameStore();
    useGameStore.getState().setCharacter(makeCharacter());
    useGameStore.setState({
      inventory: fullInventory(),
      craftingState: createDefaultCraftingState(),
    });

    expect(gatherResourceNode('dawnline_expanse', node)).toBe(true);
    expect(useGameStore.getState().inventory).toHaveLength(INVENTORY_CAPACITY);
    expect(useGameStore.getState().craftingState.resourceNodeCooldowns).toEqual({});
  });

  test('normalizes cooldown persistence backward-compatibly', () => {
    vi.spyOn(Date, 'now').mockReturnValue(10_000);
    const normalized = normalizeCraftingState({
      professions: [],
      cultivationSlots: [],
      resourceNodeCooldowns: {
        expired: 5_000,
        future: 25_000,
        bad: Number.NaN,
      },
    });

    expect(normalized.resourceNodeCooldowns).toEqual({ future: 25_000 });
  });
});

function fullInventory(): InventoryItem[] {
  return Array.from({ length: INVENTORY_CAPACITY }, (_, slot) => ({
    slot,
    key: `full_${slot}`,
    name: `Full ${slot}`,
    qty: 99,
    kind: 'misc',
  }));
}
