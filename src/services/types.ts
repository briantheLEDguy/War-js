export interface User {
  id: string;
  email: string;
}

export interface CharacterSummary {
  id: string;
  name: string;
  className: string;
  race: 'empire' | 'dwarf' | 'high_elf' | 'chaos' | 'greenskin' | 'dark_elf';
  level: number;
  zoneId: string;
}

export interface CharacterState extends CharacterSummary {
  xp: number;
  health: number;
  maxHealth: number;
  mana: number;
  maxMana: number;
  /** Base strength stat. Contributes flat damage to attacks. */
  strength: number;
  /** Coin purse. Quests and vendors use this. */
  gold: number;
  position: { x: number; y: number; z: number };
  rotationY: number;
  /** Equipped gear keyed by slot. Each value is an Equipment.key. */
  equipment?: { [slot in EquipSlot]?: string };
}

export type EquipSlot = 'mainHand' | 'offHand' | 'chest' | 'head';

export type ItemKind = 'consumable' | 'weapon' | 'armor' | 'misc';

/**
 * A piece of gear stored in the player's inventory. `strengthBonus` is rolled
 * randomly at drop/reward time — two items with the same `key` may have
 * different bonuses.
 */
export interface EquipmentAffix {
  strengthBonus: number;
}

export interface InventoryItem {
  slot: number;
  key: string;
  name: string;
  qty: number;
  icon?: string;
  kind?: ItemKind;
  /** For weapons/armor. Determines which equipment slot accepts this item. */
  equipSlot?: EquipSlot;
  /** Randomly rolled stats for this specific item instance. */
  affix?: EquipmentAffix;
}

export interface ChatMessage {
  id: string;
  channel: 'say' | 'zone' | 'global' | 'system';
  from: string;
  body: string;
  timestamp: number;
}

export interface ZonePlayerBroadcast {
  userId: string;
  characterId: string;
  name: string;
  position: { x: number; y: number; z: number };
  rotationY: number;
}

// ---------------------------------------------------------------------------
// Service interfaces. Game code imports ONLY from here via `services/index`.
// ---------------------------------------------------------------------------

export interface AuthService {
  signIn(email: string, password: string): Promise<User>;
  signOut(): Promise<void>;
  currentUser(): User | null;
}

export interface CharacterService {
  list(userId: string): Promise<CharacterSummary[]>;
  create(userId: string, data: Omit<CharacterSummary, 'id' | 'level' | 'zoneId'>): Promise<CharacterSummary>;
  load(characterId: string): Promise<CharacterState>;
  save(characterId: string, state: Partial<CharacterState>): Promise<void>;
}

export interface InventoryService {
  get(characterId: string): Promise<InventoryItem[]>;
  update(characterId: string, items: InventoryItem[]): Promise<void>;
}

export type Unsubscribe = () => void;

export interface ChatService {
  history(channel: ChatMessage['channel']): Promise<ChatMessage[]>;
  send(channel: ChatMessage['channel'], from: string, body: string): Promise<void>;
  subscribe(cb: (msg: ChatMessage) => void): Unsubscribe;
}

export interface WorldService {
  joinZone(zoneId: string, me: ZonePlayerBroadcast): Promise<void>;
  leaveZone(zoneId: string): Promise<void>;
  updatePosition(zoneId: string, me: ZonePlayerBroadcast): Promise<void>;
  subscribeToPlayers(zoneId: string, cb: (players: ZonePlayerBroadcast[]) => void): Unsubscribe;
}

// ---------------------------------------------------------------------------
// Quests
// ---------------------------------------------------------------------------

/**
 * A single objective inside a quest. `killTarget` counts enemies matching the
 * enemySpawn.name; `talkTarget` is the id of an NPC the player must interact
 * with to complete the step.
 */
export interface QuestObjective {
  id: string;
  description: string;
  killTarget?: string;
  talkTarget?: string;
  required: number;
}

export type QuestRewardItem = {
  key: string;
  name: string;
  qty: number;
  kind?: ItemKind;
  equipSlot?: EquipSlot;
  /** If true, roll a random strengthBonus in this range on award. */
  strengthRoll?: { min: number; max: number };
};

export interface QuestReward {
  xp: number;
  gold: number;
  items?: QuestRewardItem[];
}

export interface QuestDefinition {
  id: string;
  title: string;
  /** Short lore blurb shown in the quest dialog. */
  description: string;
  /** Minimum character level required to pick up this quest. */
  minLevel: number;
  /** NPC that offers this quest. */
  giverNpcId: string;
  /** NPC the player returns to for reward. Defaults to giverNpcId. */
  turninNpcId?: string;
  /** Previous quest id that must be completed before this one unlocks. */
  prereqQuestId?: string;
  objectives: QuestObjective[];
  reward: QuestReward;
}

export type QuestStatus = 'available' | 'active' | 'ready_to_turn_in' | 'completed';

export interface QuestProgress {
  questId: string;
  status: QuestStatus;
  /** objectiveId → current count */
  counters: Record<string, number>;
}

export interface QuestService {
  /** Returns quest progress for a character. Missing quests are `available`. */
  list(characterId: string): Promise<QuestProgress[]>;
  update(characterId: string, progress: QuestProgress[]): Promise<void>;
}

export interface Services {
  auth: AuthService;
  characters: CharacterService;
  inventory: InventoryService;
  chat: ChatService;
  world: WorldService;
  quests: QuestService;
  readonly backend: 'local' | 'supabase';
}

export class NotImplementedError extends Error {
  constructor(where: string) {
    super(`NotImplementedError: ${where}. Supabase backend is stubbed \u2014 implement this method in src/services/supabase/ and configure your Supabase project.`);
    this.name = 'NotImplementedError';
  }
}
