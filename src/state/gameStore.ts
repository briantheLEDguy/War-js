import { create } from 'zustand';
import type {
  CharacterState,
  CharacterSummary,
  ChatMessage,
  InventoryItem,
  User,
} from '../services/types';

export type Screen = 'login' | 'character-select' | 'world';

export interface FloatingDamage {
  id: string;
  amount: number;
  worldPos: { x: number; y: number; z: number };
  spawnedAt: number;
  kind: 'damage' | 'heal' | 'miss';
}

export interface EnemyState {
  id: string;
  name: string;
  level: number;
  health: number;
  maxHealth: number;
  position: { x: number; y: number; z: number };
  alive: boolean;
}

interface GameStore {
  // ------- screen -------
  screen: Screen;
  setScreen: (s: Screen) => void;

  // ------- auth -------
  user: User | null;
  setUser: (u: User | null) => void;

  // ------- characters -------
  characterList: CharacterSummary[];
  setCharacterList: (cs: CharacterSummary[]) => void;
  character: CharacterState | null;
  setCharacter: (c: CharacterState | null) => void;
  updateCharacter: (patch: Partial<CharacterState>) => void;

  // ------- inventory -------
  inventory: InventoryItem[];
  setInventory: (items: InventoryItem[]) => void;
  inventoryOpen: boolean;
  toggleInventory: () => void;
  /** Stack onto existing item or place in first empty slot (no-op if full). */
  addInventoryItem: (item: Omit<InventoryItem, 'slot'>) => void;
  /** Decrease qty by amt; removes the slot entirely when qty reaches 0. */
  removeInventoryQty: (slot: number, amt: number) => void;

  // ------- combat -------
  enemies: EnemyState[];
  setEnemies: (e: EnemyState[]) => void;
  updateEnemy: (id: string, patch: Partial<EnemyState>) => void;
  targetId: string | null;
  setTarget: (id: string | null) => void;
  floatingDamage: FloatingDamage[];
  pushDamage: (d: FloatingDamage) => void;
  expireDamage: (id: string) => void;

  // ------- death / respawn -------
  playerDead: boolean;
  setPlayerDead: (b: boolean) => void;
  respawnPoint: { x: number; y: number; z: number };
  setRespawnPoint: (p: { x: number; y: number; z: number }) => void;
  /** Set by the UI "Return to Life" button; consumed by the game loop. */
  pendingRespawn: boolean;
  setPendingRespawn: (b: boolean) => void;

  // ------- hotbar -------
  hotbarCooldowns: number[]; // seconds remaining; 0 = ready
  setHotbarCooldown: (slot: number, seconds: number) => void;
  tickCooldowns: (dt: number) => void;

  // ------- chat -------
  chat: ChatMessage[];
  appendChat: (m: ChatMessage) => void;
  setChat: (m: ChatMessage[]) => void;
  chatFocused: boolean;
  setChatFocused: (b: boolean) => void;

  // ------- debug -------
  debugOpen: boolean;
  toggleDebug: () => void;
  fps: number;
  setFps: (n: number) => void;
  assetFallbacks: number;
  incAssetFallbacks: () => void;
}

export const useGameStore = create<GameStore>((set) => ({
  screen: 'login',
  setScreen: (screen) => set({ screen }),

  user: null,
  setUser: (user) => set({ user }),

  characterList: [],
  setCharacterList: (characterList) => set({ characterList }),
  character: null,
  setCharacter: (character) => set({ character }),
  updateCharacter: (patch) =>
    set((s) => ({ character: s.character ? { ...s.character, ...patch } : s.character })),

  inventory: [],
  setInventory: (inventory) => set({ inventory }),
  inventoryOpen: false,
  toggleInventory: () => set((s) => ({ inventoryOpen: !s.inventoryOpen })),

  addInventoryItem: (item) =>
    set((s) => {
      // Try to stack onto an existing slot first
      const existing = s.inventory.find((i) => i.key === item.key && i.qty < 99);
      if (existing) {
        return {
          inventory: s.inventory.map((i) =>
            i.slot === existing.slot ? { ...i, qty: i.qty + (item.qty ?? 1) } : i,
          ),
        };
      }
      // Find first empty slot
      const usedSlots = new Set(s.inventory.map((i) => i.slot));
      for (let slot = 0; slot < 16; slot++) {
        if (!usedSlots.has(slot)) {
          return { inventory: [...s.inventory, { ...item, slot }] };
        }
      }
      return s; // inventory full — silently discard
    }),

  removeInventoryQty: (slot, amt) =>
    set((s) => ({
      inventory: s.inventory
        .map((i) => (i.slot === slot ? { ...i, qty: i.qty - amt } : i))
        .filter((i) => i.qty > 0),
    })),

  enemies: [],
  setEnemies: (enemies) => set({ enemies }),
  updateEnemy: (id, patch) =>
    set((s) => ({
      enemies: s.enemies.map((e) => (e.id === id ? { ...e, ...patch } : e)),
    })),
  targetId: null,
  setTarget: (targetId) => set({ targetId }),
  floatingDamage: [],
  pushDamage: (d) => set((s) => ({ floatingDamage: [...s.floatingDamage, d] })),
  expireDamage: (id) =>
    set((s) => ({ floatingDamage: s.floatingDamage.filter((x) => x.id !== id) })),

  playerDead: false,
  setPlayerDead: (playerDead) => set({ playerDead }),
  respawnPoint: { x: 0, y: 0, z: 0 },
  setRespawnPoint: (respawnPoint) => set({ respawnPoint }),
  pendingRespawn: false,
  setPendingRespawn: (pendingRespawn) => set({ pendingRespawn }),

  hotbarCooldowns: [0, 0, 0, 0],
  setHotbarCooldown: (slot, seconds) =>
    set((s) => {
      const next = [...s.hotbarCooldowns];
      next[slot] = Math.max(0, seconds);
      return { hotbarCooldowns: next };
    }),
  tickCooldowns: (dt) =>
    set((s) => ({
      hotbarCooldowns: s.hotbarCooldowns.map((c) => Math.max(0, c - dt)),
    })),

  chat: [],
  appendChat: (m) => set((s) => ({ chat: [...s.chat, m].slice(-200) })),
  setChat: (chat) => set({ chat }),
  chatFocused: false,
  setChatFocused: (chatFocused) => set({ chatFocused }),

  debugOpen: false,
  toggleDebug: () => set((s) => ({ debugOpen: !s.debugOpen })),
  fps: 0,
  setFps: (fps) => set({ fps }),
  assetFallbacks: 0,
  incAssetFallbacks: () => set((s) => ({ assetFallbacks: s.assetFallbacks + 1 })),
}));
