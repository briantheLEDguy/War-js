export interface User {
  id: string;
  email: string;
}

export interface CharacterSummary {
  id: string;
  name: string;
  className: string;
  race: 'empire' | 'greenskin' | 'dwarf' | 'elf';
  level: number;
  zoneId: string;
}

export interface CharacterState extends CharacterSummary {
  xp: number;
  health: number;
  maxHealth: number;
  mana: number;
  maxMana: number;
  position: { x: number; y: number; z: number };
  rotationY: number;
}

export interface InventoryItem {
  slot: number;
  key: string;
  name: string;
  qty: number;
  icon?: string;
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

export interface Services {
  auth: AuthService;
  characters: CharacterService;
  inventory: InventoryService;
  chat: ChatService;
  world: WorldService;
  readonly backend: 'local' | 'supabase';
}

export class NotImplementedError extends Error {
  constructor(where: string) {
    super(`NotImplementedError: ${where}. Supabase backend is stubbed \u2014 implement this method in src/services/supabase/ and configure your Supabase project.`);
    this.name = 'NotImplementedError';
  }
}
