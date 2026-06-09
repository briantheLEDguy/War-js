import { create } from 'zustand';
import {
  createDefaultCraftingState,
  type EnemyGatheringState,
} from '../data/crafting';
import { normalizeClassName } from '../data/careers';
import { normalizeBodyVariant } from '../data/playableAssets.generated';
import { getItemDefinition, INVENTORY_CAPACITY } from '../data/items';
import {
  createAbilityResourceState,
  HOTBAR_SLOT_COUNT,
  type AbilityResourceState,
} from '../game/abilities/abilityData';
import type {
  CharacterState,
  CharacterSummary,
  ChatMessage,
  CraftingState,
  CraftingStationKind,
  InventoryItem,
  QuestProgress,
  User,
} from '../services/types';
import type { WorldEditorSettings, WorldEditorTool } from '../world/editor/WorldEditorRuntime';
import type { NpcState } from '../world/NpcSpawner';

export type Screen = 'login' | 'character-select' | 'world';

export interface GameplaySettings {
  invertCameraX: boolean;
  invertCameraY: boolean;
  mouseLookSensitivity: number;
  touchLookSensitivity: number;
  zoomSensitivity: number;
}

export const DEFAULT_GAMEPLAY_SETTINGS: GameplaySettings = {
  invertCameraX: false,
  invertCameraY: false,
  mouseLookSensitivity: 1,
  touchLookSensitivity: 1,
  zoomSensitivity: 1,
};

const SETTINGS_STORAGE_KEY = 'war-js:gameplay-settings';

const DEFAULT_WORLD_EDITOR_SETTINGS: WorldEditorSettings = {
  brushSize: 4,
  brushStrength: 0.5,
  material: 'cobblestone',
  prefabKind: 'building',
  snapGrid: 1,
  snapAngleDeg: 15,
};

function clampNumber(value: unknown, min: number, max: number, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value)
    ? Math.max(min, Math.min(max, value))
    : fallback;
}

function normalizeGameplaySettings(value: unknown): GameplaySettings {
  const partial = value && typeof value === 'object'
    ? value as Partial<GameplaySettings>
    : {};
  return {
    invertCameraX: partial.invertCameraX === true,
    invertCameraY: partial.invertCameraY === true,
    mouseLookSensitivity: clampNumber(
      partial.mouseLookSensitivity,
      0.25,
      3,
      DEFAULT_GAMEPLAY_SETTINGS.mouseLookSensitivity,
    ),
    touchLookSensitivity: clampNumber(
      partial.touchLookSensitivity,
      0.25,
      3,
      DEFAULT_GAMEPLAY_SETTINGS.touchLookSensitivity,
    ),
    zoomSensitivity: clampNumber(
      partial.zoomSensitivity,
      0.25,
      3,
      DEFAULT_GAMEPLAY_SETTINGS.zoomSensitivity,
    ),
  };
}

function loadGameplaySettings(): GameplaySettings {
  if (typeof window === 'undefined') return DEFAULT_GAMEPLAY_SETTINGS;
  try {
    const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
    return raw
      ? normalizeGameplaySettings(JSON.parse(raw))
      : DEFAULT_GAMEPLAY_SETTINGS;
  } catch {
    return DEFAULT_GAMEPLAY_SETTINGS;
  }
}

function persistGameplaySettings(settings: GameplaySettings): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // Browser storage can be unavailable in privacy modes; settings still work in memory.
  }
}

export interface FloatingDamage {
  id: string;
  amount: number;
  worldPos: { x: number; y: number; z: number };
  spawnedAt: number;
  kind: 'damage' | 'heal' | 'miss';
}

export interface CombatStatusEffect {
  id: string;
  label: string;
  kind: 'burn' | 'bleed' | 'slow' | 'root' | 'silence' | 'stagger' | 'mark' | 'debuff';
  expiresAt: number;
  magnitude?: number;
  sourceAbilityId: string;
}

export interface EnemyState {
  id: string;
  name: string;
  level: number;
  health: number;
  maxHealth: number;
  position: { x: number; y: number; z: number };
  alive: boolean;
  statusEffects?: CombatStatusEffect[];
  gathering?: EnemyGatheringState;
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
  characterSheetOpen: boolean;
  toggleCharacterSheet: () => void;
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
  abilityResource: AbilityResourceState | null;
  setAbilityResource: (resource: AbilityResourceState | null) => void;

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

  // ------- zone transitions -------
  /** Set by Game.ts when the player walks into a ZoneTrigger. Consumed by GameScreen. */
  pendingZoneTransition: { targetZoneId: string; targetSpawn?: { x: number; y: number; z: number } } | null;
  setPendingZoneTransition: (t: { targetZoneId: string; targetSpawn?: { x: number; y: number; z: number } } | null) => void;

  // ------- npcs -------
  npcs: NpcState[];
  setNpcs: (n: NpcState[]) => void;

  // ------- quests -------
  quests: QuestProgress[];
  setQuests: (q: QuestProgress[]) => void;
  upsertQuest: (q: QuestProgress) => void;
  questLogOpen: boolean;
  toggleQuestLog: () => void;
  /** Set when the player interacts with a quest-giver; the HUD opens a dialog. */
  activeQuestDialogNpcId: string | null;
  setActiveQuestDialogNpcId: (id: string | null) => void;

  // ------- crafting -------
  craftingState: CraftingState;
  setCraftingState: (state: CraftingState) => void;
  craftingOpen: boolean;
  activeCraftingStation: { kind: CraftingStationKind; label: string } | null;
  openCrafting: (station: { kind: CraftingStationKind; label: string }) => void;
  closeCrafting: () => void;

  // ------- touch abilities -------
  /** Set by the touch hotbar buttons; consumed once per game-loop frame. */
  pendingTouchAbility: number | null;
  setPendingTouchAbility: (slot: number | null) => void;

  // ------- settings -------
  settingsOpen: boolean;
  setSettingsOpen: (b: boolean) => void;
  toggleSettings: () => void;
  settings: GameplaySettings;
  updateSettings: (patch: Partial<GameplaySettings>) => void;
  resetSettings: () => void;

  // ------- debug -------
  debugOpen: boolean;
  toggleDebug: () => void;
  fps: number;
  setFps: (n: number) => void;
  assetFallbacks: number;
  incAssetFallbacks: () => void;

  // ------- GM world editor -------
  gmBuildMode: boolean;
  setGmBuildMode: (enabled: boolean) => void;
  worldEditorTool: WorldEditorTool;
  setWorldEditorTool: (tool: WorldEditorTool) => void;
  worldEditorSettings: WorldEditorSettings;
  updateWorldEditorSettings: (patch: Partial<WorldEditorSettings>) => void;
  worldEditorStatus: string;
  setWorldEditorStatus: (status: string) => void;
  worldEditorSelectedObjectId: string | null;
  setWorldEditorSelectedObjectId: (id: string | null) => void;
}

export const useGameStore = create<GameStore>((set) => ({
  screen: 'login',
  setScreen: (screen) => set({ screen }),

  user: null,
  setUser: (user) => set({ user }),

  characterList: [],
  setCharacterList: (characterList) => set({ characterList }),
  character: null,
  setCharacter: (character) => {
    const normalizedCharacter = character
      ? {
          ...character,
          className: normalizeClassName(character.className),
          bodyVariant: normalizeBodyVariant(character.bodyVariant),
        }
      : null;
    return set({
      character: normalizedCharacter,
      abilityResource: normalizedCharacter ? createAbilityResourceState(normalizedCharacter.className) : null,
      hotbarCooldowns: Array.from({ length: HOTBAR_SLOT_COUNT }, () => 0),
    });
  },
  updateCharacter: (patch) =>
    set((s) => ({
      character: s.character
        ? {
            ...s.character,
            ...patch,
            className: normalizeClassName(patch.className ?? s.character.className),
            bodyVariant: normalizeBodyVariant(patch.bodyVariant ?? s.character.bodyVariant),
          }
        : s.character,
    })),

  inventory: [],
  setInventory: (inventory) => set({ inventory }),
  inventoryOpen: false,
  toggleInventory: () => set((s) => ({ inventoryOpen: !s.inventoryOpen })),
  characterSheetOpen: false,
  toggleCharacterSheet: () => set((s) => ({ characterSheetOpen: !s.characterSheetOpen })),

  addInventoryItem: (item) =>
    set((s) => {
      const def = getItemDefinition(item.key);
      const resolved = {
        ...item,
        name: item.name || def?.name || item.key,
        icon: item.icon ?? def?.icon,
        kind: item.kind ?? def?.kind,
        equipSlot: item.equipSlot ?? def?.equipSlot,
      };
      const canStack =
        !resolved.affix &&
        !resolved.equipSlot &&
        resolved.kind !== 'weapon' &&
        resolved.kind !== 'armor';

      // Try to stack onto an existing slot first
      const existing = canStack
        ? s.inventory.find((i) => i.key === resolved.key && i.qty < 99)
        : undefined;
      if (existing) {
        return {
          inventory: s.inventory.map((i) =>
            i.slot === existing.slot ? { ...i, qty: i.qty + (resolved.qty ?? 1) } : i,
          ),
        };
      }
      // Find first empty slot
      const usedSlots = new Set(s.inventory.map((i) => i.slot));
      for (let slot = 0; slot < INVENTORY_CAPACITY; slot++) {
        if (!usedSlots.has(slot)) {
          return { inventory: [...s.inventory, { ...resolved, slot }] };
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
  abilityResource: null,
  setAbilityResource: (abilityResource) => set({ abilityResource }),

  playerDead: false,
  setPlayerDead: (playerDead) => set({ playerDead }),
  respawnPoint: { x: 0, y: 0, z: 0 },
  setRespawnPoint: (respawnPoint) => set({ respawnPoint }),
  pendingRespawn: false,
  setPendingRespawn: (pendingRespawn) => set({ pendingRespawn }),

  hotbarCooldowns: Array.from({ length: HOTBAR_SLOT_COUNT }, () => 0),
  setHotbarCooldown: (slot, seconds) =>
    set((s) => {
      const next = normalizeCooldowns(s.hotbarCooldowns);
      next[slot] = Math.max(0, seconds);
      return { hotbarCooldowns: next };
    }),
  tickCooldowns: (dt) =>
    set((s) => ({
      hotbarCooldowns: normalizeCooldowns(s.hotbarCooldowns).map((c) => Math.max(0, c - dt)),
    })),

  chat: [],
  appendChat: (m) => set((s) => ({ chat: [...s.chat, m].slice(-200) })),
  setChat: (chat) => set({ chat }),
  chatFocused: false,
  setChatFocused: (chatFocused) => set({ chatFocused }),

  pendingZoneTransition: null,
  setPendingZoneTransition: (pendingZoneTransition) => set({ pendingZoneTransition }),

  npcs: [],
  setNpcs: (npcs) => set({ npcs }),

  quests: [],
  setQuests: (quests) => set({ quests }),
  upsertQuest: (q) =>
    set((s) => {
      const existing = s.quests.findIndex((x) => x.questId === q.questId);
      if (existing >= 0) {
        const next = s.quests.slice();
        next[existing] = q;
        return { quests: next };
      }
      return { quests: [...s.quests, q] };
    }),
  questLogOpen: false,
  toggleQuestLog: () => set((s) => ({ questLogOpen: !s.questLogOpen })),
  activeQuestDialogNpcId: null,
  setActiveQuestDialogNpcId: (activeQuestDialogNpcId) => set({ activeQuestDialogNpcId }),

  craftingState: createDefaultCraftingState(),
  setCraftingState: (craftingState) => set({ craftingState }),
  craftingOpen: false,
  activeCraftingStation: null,
  openCrafting: (activeCraftingStation) => set({
    activeCraftingStation,
    craftingOpen: true,
  }),
  closeCrafting: () => set({
    activeCraftingStation: null,
    craftingOpen: false,
  }),

  pendingTouchAbility: null,
  setPendingTouchAbility: (pendingTouchAbility) => set({ pendingTouchAbility }),

  settingsOpen: false,
  setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
  toggleSettings: () => set((s) => ({ settingsOpen: !s.settingsOpen })),
  settings: loadGameplaySettings(),
  updateSettings: (patch) =>
    set((s) => {
      const settings = normalizeGameplaySettings({ ...s.settings, ...patch });
      persistGameplaySettings(settings);
      return { settings };
    }),
  resetSettings: () =>
    set(() => {
      persistGameplaySettings(DEFAULT_GAMEPLAY_SETTINGS);
      return { settings: DEFAULT_GAMEPLAY_SETTINGS };
    }),

  debugOpen: false,
  toggleDebug: () => set((s) => ({ debugOpen: !s.debugOpen })),
  fps: 0,
  setFps: (fps) => set({ fps }),
  assetFallbacks: 0,
  incAssetFallbacks: () => set((s) => ({ assetFallbacks: s.assetFallbacks + 1 })),

  gmBuildMode: false,
  setGmBuildMode: (gmBuildMode) => set({ gmBuildMode }),
  worldEditorTool: 'select',
  setWorldEditorTool: (worldEditorTool) => set({ worldEditorTool }),
  worldEditorSettings: DEFAULT_WORLD_EDITOR_SETTINGS,
  updateWorldEditorSettings: (patch) =>
    set((s) => ({
      worldEditorSettings: {
        ...s.worldEditorSettings,
        ...patch,
        brushSize: clampNumber(patch.brushSize ?? s.worldEditorSettings.brushSize, 1, 32, 4),
        brushStrength: clampNumber(patch.brushStrength ?? s.worldEditorSettings.brushStrength, 0.05, 1, 0.5),
        snapGrid: clampNumber(patch.snapGrid ?? s.worldEditorSettings.snapGrid, 0, 32, 1),
        snapAngleDeg: clampNumber(patch.snapAngleDeg ?? s.worldEditorSettings.snapAngleDeg, 0, 90, 15),
      },
    })),
  worldEditorStatus: '',
  setWorldEditorStatus: (worldEditorStatus) => set({ worldEditorStatus }),
  worldEditorSelectedObjectId: null,
  setWorldEditorSelectedObjectId: (worldEditorSelectedObjectId) => set({ worldEditorSelectedObjectId }),
}));

function normalizeCooldowns(cooldowns: number[]): number[] {
  const next = Array.from({ length: HOTBAR_SLOT_COUNT }, (_, index) => cooldowns[index] ?? 0);
  return next;
}
