import { describe, expect, test } from 'vitest';
import { CRAFTING_RECIPES } from '../src/data/crafting';
import { createInventoryItem, EQUIP_SLOT_LABELS } from '../src/data/items';
import {
  DEFAULT_INVENTORY_FILTERS,
  filterAndSortInventoryItems,
  filterRecipeAvailability,
  getCultivationReadyCount,
  getEquipmentComparisonLines,
  getRecipeAvailability,
} from '../src/ui/hud/inventoryCraftingQoL';

describe('inventory QoL helpers', () => {
  test('filters by search, kind, equipment slot, and material use', () => {
    const inventory = [
      createInventoryItem('sword_iron', 0, { affix: { strengthBonus: 1 } }),
      createInventoryItem('potion_health', 1, { qty: 3 }),
      createInventoryItem('craft_mandrake_root', 2, { qty: 1 }),
      createInventoryItem('seed_mandrake', 3, { qty: 1 }),
      createInventoryItem('crafted_minor_strength_talisman', 4, { affix: { strengthBonus: 3 } }),
    ];

    expect(filterAndSortInventoryItems(inventory, {
      ...DEFAULT_INVENTORY_FILTERS,
      search: 'potion',
    }).map((item) => item.key)).toEqual(['potion_health']);

    expect(filterAndSortInventoryItems(inventory, {
      ...DEFAULT_INVENTORY_FILTERS,
      kind: 'equipment',
    }).map((item) => item.key)).toEqual(['sword_iron', 'crafted_minor_strength_talisman']);

    expect(filterAndSortInventoryItems(inventory, {
      ...DEFAULT_INVENTORY_FILTERS,
      equipSlot: 'neck',
    }).map((item) => item.key)).toEqual(['crafted_minor_strength_talisman']);

    expect(filterAndSortInventoryItems(inventory, {
      ...DEFAULT_INVENTORY_FILTERS,
      material: 'apothecary',
    }).map((item) => item.key)).toEqual(['craft_mandrake_root']);
  });

  test('sorts strength candidates before weaker gear', () => {
    const inventory = [
      createInventoryItem('sword_iron', 0, { affix: { strengthBonus: 1 } }),
      createInventoryItem('crafted_minor_strength_talisman', 1, { affix: { strengthBonus: 4 } }),
      createInventoryItem('armor_chain', 2),
    ];

    expect(filterAndSortInventoryItems(inventory, {
      ...DEFAULT_INVENTORY_FILTERS,
      sort: 'strength',
    }).map((item) => item.key)).toEqual([
      'crafted_minor_strength_talisman',
      'sword_iron',
      'armor_chain',
    ]);
  });

  test('summarizes equipped gear comparison lines', () => {
    const candidate = createInventoryItem('sword_iron', 0, { affix: { strengthBonus: 3 } });

    expect(getEquipmentComparisonLines(candidate, {
      key: 'sword_recruit',
      name: 'Recruit Sword',
      kind: 'weapon',
      equipSlot: 'mainHand',
      affix: { strengthBonus: 1 },
    }, EQUIP_SLOT_LABELS)).toContain('Change: +2 Strength');
  });
});

describe('crafting QoL helpers', () => {
  test('builds recipe availability and filters by craftable, missing, and rank', () => {
    const minorHealth = CRAFTING_RECIPES.find((recipe) => recipe.id === 'apothecary_minor_health');
    const rejuvenation = CRAFTING_RECIPES.find((recipe) => recipe.id === 'apothecary_rejuvenation');
    if (!minorHealth || !rejuvenation) throw new Error('Expected test recipes to exist.');

    const readyInventory = [
      createInventoryItem('craft_vial_cloudy', 0, { qty: 1 }),
      createInventoryItem('craft_mandrake_root', 1, { qty: 2 }),
      createInventoryItem('craft_clear_water', 2, { qty: 1 }),
    ];
    const craftable = getRecipeAvailability(minorHealth, readyInventory, 1, true);
    const missing = getRecipeAvailability(minorHealth, [], 1, true);
    const rankGated = getRecipeAvailability(rejuvenation, readyInventory, 1, true);

    expect(craftable.canCraft).toBe(true);
    expect(missing.missingInputs.map((input) => input.key)).toContain('craft_vial_cloudy');
    expect(rankGated.enoughRank).toBe(false);
    expect(filterRecipeAvailability([craftable, missing, rankGated], 'craftable')).toEqual([craftable]);
    expect(filterRecipeAvailability([craftable, missing, rankGated], 'missing')).toEqual([missing, rankGated]);
    expect(filterRecipeAvailability([craftable, missing, rankGated], 'rank')).toEqual([rankGated]);
  });

  test('counts cultivation slots ready to harvest', () => {
    expect(getCultivationReadyCount([
      { readyAt: 999 },
      { readyAt: 1000 },
      { readyAt: 1500 },
    ], 1000)).toBe(2);
  });
});
