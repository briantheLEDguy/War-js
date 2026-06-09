import {
  createDefaultCraftingState,
  normalizeCraftingState,
} from '../../data/crafting';
import type { CraftingService, CraftingState } from '../types';

const STORAGE_KEY = 'war-js:local-crafting';

export class CraftingLocal implements CraftingService {
  private store: Record<string, CraftingState>;

  constructor() {
    this.store = {};
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const saved = JSON.parse(raw) as Record<string, CraftingState>;
        this.store = Object.fromEntries(
          Object.entries(saved).map(([characterId, state]) => [
            characterId,
            normalizeCraftingState(state),
          ]),
        );
        this.persist();
      }
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

  async get(characterId: string): Promise<CraftingState> {
    if (!this.store[characterId]) {
      this.store[characterId] = createDefaultCraftingState();
      this.persist();
    }
    return normalizeCraftingState(this.store[characterId]);
  }

  async update(characterId: string, state: CraftingState): Promise<void> {
    this.store[characterId] = normalizeCraftingState(state);
    this.persist();
  }
}
