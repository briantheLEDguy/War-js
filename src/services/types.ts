import type { BodyVariant, PlayableRace } from '../data/careers';
import type { CampaignClaimResult, CampaignRealm, CampaignSnapshot } from '../data/campaign';

export interface User {
  id: string;
  email: string;
}

export interface CharacterSummary {
  id: string;
  name: string;
  className: string;
  race: PlayableRace;
  bodyVariant: BodyVariant;
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
  /**
   * Equipped gear keyed by slot. String entries are legacy item keys from
   * older localStorage saves; object entries preserve the exact item instance
   * that was equipped.
   */
  equipment?: EquipmentState;
}

export type EquipSlot =
  | 'head'
  | 'neck'
  | 'shoulders'
  | 'chest'
  | 'hands'
  | 'waist'
  | 'legs'
  | 'feet'
  | 'back'
  | 'tabard'
  | 'mainHand'
  | 'offHand';

export type ItemKind = 'consumable' | 'weapon' | 'armor' | 'material' | 'seed' | 'talisman' | 'misc';

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

export interface EquippedGear {
  key: string;
  name: string;
  icon?: string;
  kind?: ItemKind;
  equipSlot: EquipSlot;
  /** Inventory slot the item came from, used to disambiguate duplicate keys. */
  inventorySlot?: number;
  /** Snapshot of the equipped item's rolled stats. */
  affix?: EquipmentAffix;
}

export type EquipmentEntry = string | EquippedGear;
export type EquipmentState = { [slot in EquipSlot]?: EquipmentEntry };

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

export interface ZonePlayerPresence extends ZonePlayerBroadcast {
  zoneId: string;
}

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface WorldTransform {
  position: Vec3;
  rotation: Vec3;
  scale: Vec3;
}

export type WorldEditStatus = 'draft' | 'published';
export type WorldObjectType = 'prop' | 'collider' | 'walkableSurface';
export type VoxelMaterialId = 'grass' | 'dirt' | 'cobblestone' | 'stone' | 'wood' | 'water' | string;

export interface VoxelMaterialDefinition {
  id: VoxelMaterialId;
  label: string;
  color: string;
}

export interface VoxelMaterialPalette {
  schemaVersion: number;
  materials: VoxelMaterialDefinition[];
}

export interface VoxelCell {
  density: number;
  material: VoxelMaterialId;
}

export interface VoxelTerrainChunk {
  key: string;
  origin: Vec3;
  size: number;
  voxelSize: number;
  cells: Record<string, VoxelCell>;
  updatedAt: number;
}

export interface WorldObjectBase {
  id: string;
  type: WorldObjectType;
  label?: string;
  /** Used by GM world edits to hide a static zone object without removing the source JSON. */
  hidden?: boolean;
  transform: WorldTransform;
  createdAt: number;
  updatedAt: number;
}

export interface WorldPropObject extends WorldObjectBase {
  type: 'prop';
  kind: string;
  model?: string;
  assetKey?: string;
  colliders?: Array<{
    id?: string;
    x?: number;
    z?: number;
    width: number;
    depth: number;
    rotY?: number;
    minY?: number;
    maxY?: number;
    blocksWhen?: 'always' | 'closed';
    interactionId?: string;
  }>;
  walkableSurfaces?: Array<{
    id?: string;
    x?: number;
    z?: number;
    width: number;
    depth: number;
    rotY?: number;
    fromY?: number;
    toY?: number;
    axis?: 'x' | 'z';
  }>;
  interaction?: WorldPropInteraction;
}

export interface WorldPropInteraction {
  id: string;
  type: 'gate';
  label?: string;
  maxDistance?: number;
  openClip?: string;
  closeClip?: string;
  startsOpen?: boolean;
}

export interface WorldColliderObject extends WorldObjectBase {
  type: 'collider';
  width: number;
  depth: number;
  minY?: number;
  maxY?: number;
  blocksWhen?: 'always' | 'closed';
  interactionId?: string;
}

export interface WorldWalkableSurfaceObject extends WorldObjectBase {
  type: 'walkableSurface';
  width: number;
  depth: number;
  fromY: number;
  toY: number;
  axis?: 'x' | 'z';
}

export type WorldObject = WorldPropObject | WorldColliderObject | WorldWalkableSurfaceObject;

export interface WorldEditDocument {
  schemaVersion: number;
  versionId: string;
  zoneId: string;
  status: WorldEditStatus;
  parentVersionId?: string;
  authorUserId?: string;
  authorEmail?: string;
  notes?: string;
  createdAt: number;
  updatedAt: number;
  publishedAt?: number;
  palette: VoxelMaterialPalette;
  objects: WorldObject[];
  voxelChunks: VoxelTerrainChunk[];
}

export interface WorldEditVersionSummary {
  versionId: string;
  zoneId: string;
  status: WorldEditStatus;
  parentVersionId?: string;
  notes?: string;
  authorUserId?: string;
  authorEmail?: string;
  createdAt: number;
  updatedAt: number;
  publishedAt?: number;
  objectCount: number;
  chunkCount: number;
}

export interface WorldEditPatch {
  replaceDocument?: WorldEditDocument;
  upsertObjects?: WorldObject[];
  removeObjectIds?: string[];
  upsertVoxelChunks?: VoxelTerrainChunk[];
  removeVoxelChunkKeys?: string[];
  notes?: string;
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
  findByName(name: string): Promise<CharacterState[]>;
}

export interface InventoryService {
  get(characterId: string): Promise<InventoryItem[]>;
  update(characterId: string, items: InventoryItem[]): Promise<void>;
}

// ---------------------------------------------------------------------------
// Gathering + crafting
// ---------------------------------------------------------------------------

export type CraftingProfessionId =
  | 'scavenging'
  | 'butchering'
  | 'salvaging'
  | 'cultivation'
  | 'apothecary'
  | 'talisman_making';

export type CraftingStationKind =
  | 'apothecary'
  | 'talisman_making'
  | 'cultivation'
  | 'salvage'
  | 'general';

export interface ProfessionProgress {
  professionId: CraftingProfessionId;
  rank: number;
  xp: number;
}

export interface CultivationSlot {
  id: string;
  seedKey: string;
  plantedAt: number;
  readyAt: number;
  additives: string[];
}

export interface CraftingState {
  professions: ProfessionProgress[];
  cultivationSlots: CultivationSlot[];
  /** resource node cooldown key -> unix timestamp in ms when the node can be gathered again. */
  resourceNodeCooldowns: Record<string, number>;
}

export interface CraftingService {
  get(characterId: string): Promise<CraftingState>;
  update(characterId: string, state: CraftingState): Promise<void>;
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
  findPlayerByName(name: string): Promise<ZonePlayerPresence | null>;
}

export interface WorldEditService {
  getPublished(zoneId: string): Promise<WorldEditDocument | null>;
  getDraft(zoneId: string): Promise<WorldEditDocument | null>;
  saveDraft(zoneId: string, patch: WorldEditPatch): Promise<WorldEditDocument>;
  publishDraft(zoneId: string, notes: string): Promise<WorldEditDocument>;
  listVersions(zoneId: string): Promise<WorldEditVersionSummary[]>;
  restoreVersion(zoneId: string, versionId: string): Promise<WorldEditDocument>;
}

export interface CampaignService {
  getSnapshot(currentZoneId?: string | null): Promise<CampaignSnapshot>;
  subscribeSnapshot(cb: (snapshot: CampaignSnapshot) => void, currentZoneId?: string | null): Unsubscribe;
  claimObjective(zoneId: string, objectiveId: string, realm: CampaignRealm): Promise<CampaignClaimResult>;
  resetCampaign(): Promise<CampaignSnapshot>;
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
  crafting: CraftingService;
  chat: ChatService;
  world: WorldService;
  worldEdits: WorldEditService;
  campaign: CampaignService;
  quests: QuestService;
  readonly backend: 'local' | 'supabase';
}

export class NotImplementedError extends Error {
  constructor(where: string) {
    super(`NotImplementedError: ${where}. Supabase backend is stubbed \u2014 implement this method in src/services/supabase/ and configure your Supabase project.`);
    this.name = 'NotImplementedError';
  }
}
