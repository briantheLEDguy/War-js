import type { InventoryItem, InventoryService } from '../types';

const STORAGE_KEY = 'war-js:local-inventory';

const DEFAULT_ITEMS: InventoryItem[] = [
  { slot: 0, key: 'sword_iron', name: 'Iron Sword', qty: 1 },
  { slot: 1, key: 'shield_wood', name: 'Wooden Shield', qty: 1 },
  { slot: 2, key: 'potion_health', name: 'Health Potion', qty: 5 },
  { slot: 3, key: 'potion_mana', name: 'Mana Potion', qty: 3 },
  { slot: 4, key: 'bread', name: 'Hunk of Bread', qty: 2 },
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
    if (!this.store[characterId]) {
      this.store[characterId] = DEFAULT_ITEMS.map((i) => ({ ...i }));
      this.persist();
    }
    return this.store[characterId].map((i) => ({ ...i }));
  }

  async update(characterId: string, items: InventoryItem[]): Promise<void> {
    this.store[characterId] = items.map((i) => ({ ...i }));
    this.persist();
  }
}
