import {
  CRAFTING_RECIPES,
  CULTIVATION_SEEDS,
  hasIngredients,
  inventoryQty,
  type CraftingItemStack,
  type CraftingRecipe,
} from '../../data/crafting';
import { resolveInventoryItem } from '../../data/items';
import type {
  EquippedGear,
  EquipSlot,
  InventoryItem,
  ItemKind,
} from '../../services/types';

export type InventoryKindFilter =
  | 'all'
  | 'equipment'
  | 'weapon'
  | 'armor'
  | 'consumable'
  | 'material'
  | 'seed';
export type InventoryMaterialFilter =
  | 'all'
  | 'apothecary'
  | 'talisman_making'
  | 'cultivation'
  | 'salvage';
export type InventorySortMode = 'slot' | 'name' | 'kind' | 'quantity' | 'strength';
export type RecipeFilterMode = 'all' | 'craftable' | 'missing' | 'rank';

export interface InventoryFilters {
  search: string;
  kind: InventoryKindFilter;
  equipSlot: 'all' | EquipSlot;
  material: InventoryMaterialFilter;
  sort: InventorySortMode;
}

export interface RecipeAvailability {
  recipe: CraftingRecipe;
  enoughRank: boolean;
  enoughItems: boolean;
  stationAllowed: boolean;
  canCraft: boolean;
  missingInputs: Array<CraftingItemStack & { owned: number; missing: number }>;
}

export const DEFAULT_INVENTORY_FILTERS: InventoryFilters = {
  search: '',
  kind: 'all',
  equipSlot: 'all',
  material: 'all',
  sort: 'slot',
};

const MATERIAL_KEYS_BY_USE: Record<Exclude<InventoryMaterialFilter, 'all'>, Set<string>> = {
  apothecary: new Set(
    CRAFTING_RECIPES
      .filter((recipe) => recipe.professionId === 'apothecary')
      .flatMap((recipe) => recipe.inputs.map((input) => input.key)),
  ),
  talisman_making: new Set(
    CRAFTING_RECIPES
      .filter((recipe) => recipe.professionId === 'talisman_making')
      .flatMap((recipe) => recipe.inputs.map((input) => input.key)),
  ),
  cultivation: new Set(
    CULTIVATION_SEEDS.flatMap((seed) => [
      seed.seedKey,
      seed.bonusAdditiveKey,
      ...seed.outputs.map((output) => output.key),
      ...(seed.bonusOutputs ?? []).map((output) => output.key),
    ]).filter((key): key is string => !!key),
  ),
  salvage: new Set([
    'craft_scrap_iron',
    'craft_torn_cloth',
    'craft_ragged_leather',
    'craft_talisman_fragment',
    'craft_essence_minor',
  ]),
};

export function isDefaultInventoryFilters(filters: InventoryFilters): boolean {
  return (
    filters.search.trim() === '' &&
    filters.kind === DEFAULT_INVENTORY_FILTERS.kind &&
    filters.equipSlot === DEFAULT_INVENTORY_FILTERS.equipSlot &&
    filters.material === DEFAULT_INVENTORY_FILTERS.material &&
    filters.sort === DEFAULT_INVENTORY_FILTERS.sort
  );
}

export function filterAndSortInventoryItems(
  items: InventoryItem[],
  filters: InventoryFilters,
): InventoryItem[] {
  const query = normalize(filters.search);
  const filtered = items
    .map(resolveInventoryItem)
    .filter((item) => matchesSearch(item, query))
    .filter((item) => matchesKindFilter(item, filters.kind))
    .filter((item) => filters.equipSlot === 'all' || item.equipSlot === filters.equipSlot)
    .filter((item) => matchesMaterialFilter(item, filters.material));

  return filtered.sort((a, b) => compareInventoryItems(a, b, filters.sort));
}

export function getRecipeAvailability(
  recipe: CraftingRecipe,
  inventory: InventoryItem[],
  rank: number,
  stationAllowed = true,
): RecipeAvailability {
  const missingInputs = recipe.inputs
    .map((input) => {
      const owned = inventoryQty(inventory, input.key);
      return {
        ...input,
        owned,
        missing: Math.max(0, input.qty - owned),
      };
    })
    .filter((input) => input.missing > 0);
  const enoughRank = rank >= recipe.minRank;
  const enoughItems = hasIngredients(inventory, recipe.inputs);

  return {
    recipe,
    enoughRank,
    enoughItems,
    stationAllowed,
    canCraft: stationAllowed && enoughRank && enoughItems,
    missingInputs,
  };
}

export function filterRecipeAvailability(
  recipes: RecipeAvailability[],
  filter: RecipeFilterMode,
): RecipeAvailability[] {
  return recipes.filter((entry) => {
    if (filter === 'craftable') return entry.canCraft;
    if (filter === 'missing') return !entry.enoughItems;
    if (filter === 'rank') return !entry.enoughRank;
    return true;
  });
}

export function countCraftableRecipes(recipes: RecipeAvailability[]): number {
  return recipes.filter((entry) => entry.canCraft).length;
}

export function getCultivationReadyCount(slots: Array<{ readyAt: number }>, now: number): number {
  return slots.filter((slot) => slot.readyAt <= now).length;
}

export function getEquipmentComparisonLines(
  candidate: InventoryItem,
  equipped: EquippedGear | null,
  slotLabels: Record<EquipSlot, string>,
): string[] {
  const item = resolveInventoryItem(candidate);
  if (!item.equipSlot || (item.kind !== 'weapon' && item.kind !== 'armor')) return [];

  const candidateStrength = item.affix?.strengthBonus ?? 0;
  const equippedStrength = equipped?.affix?.strengthBonus ?? 0;
  const delta = candidateStrength - equippedStrength;
  const lines = [`${slotLabels[item.equipSlot]}: +${candidateStrength} Strength`];

  if (!equipped) {
    lines.push('Currently empty');
    return lines;
  }

  const sameItem =
    equipped.key === item.key &&
    (equipped.inventorySlot === undefined || equipped.inventorySlot === item.slot);
  lines.push(`Equipped: ${equipped.name} (+${equippedStrength} Strength)`);
  lines.push(sameItem ? 'Currently equipped' : `Change: ${formatSigned(delta)} Strength`);
  return lines;
}

function compareInventoryItems(
  a: InventoryItem,
  b: InventoryItem,
  sort: InventorySortMode,
): number {
  if (sort === 'name') return a.name.localeCompare(b.name) || a.slot - b.slot;
  if (sort === 'kind') {
    return (
      kindRank(a.kind) - kindRank(b.kind) ||
      (a.equipSlot ?? '').localeCompare(b.equipSlot ?? '') ||
      a.name.localeCompare(b.name) ||
      a.slot - b.slot
    );
  }
  if (sort === 'quantity') return b.qty - a.qty || a.name.localeCompare(b.name) || a.slot - b.slot;
  if (sort === 'strength') {
    return (
      (b.affix?.strengthBonus ?? 0) - (a.affix?.strengthBonus ?? 0) ||
      a.name.localeCompare(b.name) ||
      a.slot - b.slot
    );
  }
  return a.slot - b.slot;
}

function matchesSearch(item: InventoryItem, query: string): boolean {
  if (!query) return true;
  return normalize(`${item.name} ${item.key} ${item.kind ?? ''} ${item.equipSlot ?? ''}`).includes(query);
}

function matchesKindFilter(item: InventoryItem, filter: InventoryKindFilter): boolean {
  if (filter === 'all') return true;
  if (filter === 'equipment') return !!item.equipSlot || item.kind === 'weapon' || item.kind === 'armor';
  return item.kind === filter;
}

function matchesMaterialFilter(item: InventoryItem, filter: InventoryMaterialFilter): boolean {
  if (filter === 'all') return true;
  return MATERIAL_KEYS_BY_USE[filter].has(item.key);
}

function kindRank(kind: ItemKind | undefined): number {
  if (kind === 'weapon') return 0;
  if (kind === 'armor') return 1;
  if (kind === 'consumable') return 2;
  if (kind === 'material') return 3;
  if (kind === 'seed') return 4;
  return 5;
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function formatSigned(value: number): string {
  if (value > 0) return `+${value}`;
  return `${value}`;
}
