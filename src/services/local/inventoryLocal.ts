import type { CharacterSummary, InventoryItem, InventoryService } from '../types';
import { createInventoryItem, INVENTORY_CAPACITY } from '../../data/items';
import { normalizeClassName } from '../../data/careers';
import { normalizeBodyVariant, starterArmorInventoryFor } from '../../data/playableAssets.generated';

const STORAGE_KEY = 'war-js:local-inventory';
const CHARACTER_STORAGE_KEY = 'war-js:local-characters';

type CharacterInventorySeed = Pick<CharacterSummary, 'race' | 'className' | 'bodyVariant'>;

const PREBUILT_CHARACTER_SEEDS: Record<string, CharacterInventorySeed> = {
  'char-sigmund': { race: 'empire', className: 'Battle Prelate', bodyVariant: 'm' },
  'char-grik': { race: 'greenskin', className: 'Bog Hexer', bodyVariant: 'm' },
};

const BASE_DEFAULT_ITEMS: InventoryItem[] = [
  createInventoryItem('sword_iron', 0),
  createInventoryItem('shield_wood', 1),
  createInventoryItem('potion_health', 2, { qty: 5 }),
  createInventoryItem('potion_mana', 3, { qty: 3 }),
  createInventoryItem('bread', 4, { qty: 2 }),
];

const BATTLE_PRELATE_DEFAULT_ITEMS: InventoryItem[] = [
  createInventoryItem('weapon_hammer_reliquary_2h', 0),
  createInventoryItem('potion_health', 2, { qty: 5 }),
  createInventoryItem('potion_mana', 3, { qty: 3 }),
  createInventoryItem('bread', 4, { qty: 2 }),
];

const CRAFTING_DEFAULT_ITEMS: InventoryItem[] = [
  createInventoryItem('craft_vial_cloudy', 14, { qty: 3 }),
  createInventoryItem('craft_clear_water', 15, { qty: 4 }),
  createInventoryItem('craft_fertile_soil', 16, { qty: 2 }),
  createInventoryItem('seed_mandrake', 17, { qty: 2 }),
  createInventoryItem('seed_goldweed', 18, { qty: 1 }),
];

export class InventoryLocal implements InventoryService {
  private store: Record<string, InventoryItem[]>;

  constructor() {
    this.store = {};
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) this.store = JSON.parse(raw);
    } catch {
      /* ignore */
    }
  }

  private persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.store));
    } catch {
      /* ignore */
    }
  }

  async get(characterId: string): Promise<InventoryItem[]> {
    const defaultItems = defaultItemsForCharacter(characterId);
    if (!this.store[characterId]) {
      this.store[characterId] = defaultItems.map((i) => ({ ...i }));
      this.persist();
    } else if (backfillDefaultItems(this.store[characterId], defaultItems)) {
      this.persist();
    }
    return this.store[characterId].map((i) => ({ ...i }));
  }

  async update(characterId: string, items: InventoryItem[]): Promise<void> {
    this.store[characterId] = items.map((i) => ({ ...i }));
    this.persist();
  }
}

function defaultItemsForCharacter(characterId: string): InventoryItem[] {
  const character = characterSeedFor(characterId);
  const baseItems = isBattlePrelate(character)
    ? BATTLE_PRELATE_DEFAULT_ITEMS
    : BASE_DEFAULT_ITEMS;
  return [
    ...baseItems,
    ...starterArmorInventoryFor(character.race, character.className, character.bodyVariant, 5),
    ...CRAFTING_DEFAULT_ITEMS,
  ];
}

function isBattlePrelate(character: CharacterInventorySeed): boolean {
  return character.race === 'empire' && normalizeClassName(character.className) === 'Battle Prelate';
}

function characterSeedFor(characterId: string): CharacterInventorySeed {
  const prebuilt = PREBUILT_CHARACTER_SEEDS[characterId];
  if (prebuilt) return prebuilt;

  try {
    const raw = localStorage.getItem(CHARACTER_STORAGE_KEY);
    if (!raw) throw new Error('missing local character storage');
    const saved = JSON.parse(raw) as Record<string, CharacterSummary>;
    const character = saved[characterId];
    if (!character) throw new Error(`missing local character ${characterId}`);
    return {
      race: character.race,
      className: character.className,
      bodyVariant: normalizeBodyVariant(character.bodyVariant),
    };
  } catch {
    return { race: 'empire', className: 'Battle Prelate', bodyVariant: 'm' };
  }
}

function backfillDefaultItems(items: InventoryItem[], defaultItems: InventoryItem[]): boolean {
  let changed = false;
  const usedSlots = new Set(items.map((item) => item.slot));
  const presentKeys = new Set(items.map((item) => item.key));

  for (const defaultItem of defaultItems) {
    if (presentKeys.has(defaultItem.key)) continue;
    const desiredSlotFree = defaultItem.slot < INVENTORY_CAPACITY && !usedSlots.has(defaultItem.slot);
    const slot = desiredSlotFree
      ? defaultItem.slot
      : firstFreeSlot(usedSlots);
    if (slot === null) continue;

    items.push({ ...defaultItem, slot });
    usedSlots.add(slot);
    presentKeys.add(defaultItem.key);
    changed = true;
  }

  return changed;
}

function firstFreeSlot(usedSlots: Set<number>): number | null {
  for (let slot = 0; slot < INVENTORY_CAPACITY; slot += 1) {
    if (!usedSlots.has(slot)) return slot;
  }
  return null;
}
