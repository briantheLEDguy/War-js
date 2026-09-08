/** Shared, JSON-safe authority contract. Clients request actions; only the simulation emits outcomes. */
import type { OrvrTerrainControls } from '../orvrTerrain';
import type { WalkableSurface } from '../worldNavigation';
export const ORVR_PROTOCOL_VERSION = 1 as const;
export type Realm = 'aegis' | 'riftbound';
export type Position = { x: number; y: number; z: number };
export type EquipmentKind = 'ram' | 'oil' | 'catapult';
export type GateKind = 'outer' | 'inner';
export type Pairing = 'west' | 'east' | 'central';
export type ZoneStatus = 'inactive' | 'staging' | 'active' | 'secured';

export interface ObjectiveConfig {
  id: string;
  position: Position;
  captureRadius?: number;
  guardCount?: number;
  /** Ordered, traversable points from this objective to each realm's keep. */
  routes?: Partial<Record<Realm, Position[]>>;
  requiresObjectiveIds?: string[];
}
export interface KeepConfig {
  id: string;
  realm: Realm;
  position: Position;
  outerGate: Position;
  innerGate: Position;
  gateFootprints?: Partial<Record<GateKind, { width: number; depth: number; height?: number; rotY?: number }>>;
  quartermaster: Position;
  deliveryPoint?: Position;
  siegePositions?: Partial<Record<EquipmentKind, Position[]>>;
  /** Fixed ground controls for stationary engines, in the corresponding siege slot order. */
  siegeOperatorPositions?: Partial<Record<'oil' | 'catapult', Position[]>>;
  postern?: PosternConfig;
  posterns?: Array<PosternConfig & { id: string }>;
}
export interface PosternConfig {
  id?: string;
  label?: string;
  outside: Position;
  inside: Position;
  interactionRadius: number;
}
export interface ZoneConfig {
  id: string;
  kind: 'battlefield' | 'fortress' | 'city';
  bounds: { minX: number; maxX: number; minZ: number; maxZ: number };
  staging: Record<Realm, Position>;
  objectives: ObjectiveConfig[];
  keeps: KeepConfig[];
  /** Invisible server collision footprints; independent of visual mesh topology. */
  collision?: { minX: number; maxX: number; minZ: number; maxZ: number; minY?: number; maxY?: number; walkableTop?: boolean;
    footprint?: { x: number; z: number; width: number; depth: number; rotY: number } }[];
  walkableSurfaces?: WalkableSurface[];
  defender?: Realm;
  terrain?: OrvrTerrainControls;
  terrainSize?: number;
  terrainSegments?: number;
}
export type StatusKind = 'burn' | 'bleed' | 'slow' | 'root' | 'silence' | 'stagger' | 'mark' | 'debuff' | 'guard' | 'shield' | 'empower' | 'haste';
export interface SharedAbilityEffect {
  kind: 'damage' | 'heal' | 'status' | 'player_status' | 'cleanse' | 'movement';
  amount?: { min: number; max: number; statScale?: number; resourceScale?: number; levelScale?: number };
  status?: { id: string; label: string; kind: StatusKind; durationSec: number; magnitude?: number; damageModifier?: 'damage_taken' | 'damage_dealt' };
  playerStatus?: { kind: 'guard' | 'shield' | 'empower' | 'haste'; durationSec: number; magnitude: number; stackGroup?: string };
  cleanse?: { kinds: StatusKind[] };
  movement?: { mode: 'forward' | 'backward' | 'toward_target'; distance: number };
}
export interface AbilityRule {
  id: string;
  cooldownSeconds: number;
  range: number;
  damage?: number;
  healing?: number;
  effects?: SharedAbilityEffect[];
  targeting?: { target: 'enemy' | 'self' | 'ally'; shape: 'melee' | 'projectile' | 'beam' | 'cone' | 'area' | 'self' | 'dash' | 'deployable' | 'pet'; range: number; radius?: number; projectileSpeed?: number };
  resource?: { manaCost?: number; careerBuild?: number; careerCost?: number; spendAllCareer?: boolean; minCareer?: number };
  gcdSeconds?: number;
  impactDelaySeconds?: number;
  unavailableReason?: string;
}
export interface ActiveStatus {
  id: string;
  kind: StatusKind;
  expiresAt: number;
  magnitude: number;
  sourceId: string;
  damageModifier?: 'damage_taken' | 'damage_dealt';
  nextTickAt?: number;
  tickDamage?: number;
  shieldRemaining?: number;
}
export interface PendingImpact {
  id: string;
  sourceId: string;
  abilityId: string;
  targetId: string;
  center: Position;
  origin: Position;
  facing: { x: number; z: number };
  dueAt: number;
  resourceSpent: number;
  strength: number;
  level: number;
}
export interface CampaignConfig {
  id?: string;
  zones?: ZoneConfig[];
  abilities?: AbilityRule[];
}
export interface PlayerIdentity {
  id: string;
  userId: string;
  characterId: string;
  displayName?: string;
  realm: Realm;
  zoneId?: string;
  /** Trusted server configuration only; clients must never supply their own unlocks. */
  abilityIds?: string[];
  avatarProfileKey?: string;
  className?: string;
  combatProfile?: { level: number; strength: number; maxHealth: number; maxMana: number; careerMax: number; careerInitial: number };
}
export interface PlayerState extends Omit<PlayerIdentity, 'zoneId'> {
  zoneId: string;
  connected: boolean;
  queued: boolean;
  position: Position;
  health: number;
  maxHealth: number;
  respawnRemaining: number;
  lastSequence: number;
  direction: { x: number; z: number };
  movementExpiresAt: number;
  cooldowns: Record<string, number>;
  equipmentId: string | null;
  repair: { keepId: string; gate: GateKind; remaining: number; start: Position } | null;
  mana: number;
  maxMana: number;
  careerResource: number;
  careerMax: number;
  facing: { x: number; z: number };
  statuses: ActiveStatus[];
}
export interface ObjectiveState {
  id: string;
  owner: Realm | null;
  capturingRealm: Realm | null;
  captureSeconds: number;
  contested: boolean;
  productionSeconds: number;
  readyShipment: boolean;
  caravanId: string | null;
  guardIds: string[];
}
export interface GateState {
  id: string;
  health: number;
  maxHealth: number;
  lastDamagedAt: number | null;
}
export interface KeepState {
  id: string;
  owner: Realm;
  deliveredSupplies: number;
  supplies: number;
  level: 1 | 2 | 3;
  gates: Record<GateKind, GateState>;
  commanderId: string;
  capturingRealm: Realm | null;
  captureSeconds: number;
}
export interface NpcState {
  id: string;
  kind: 'guard' | 'commander';
  realm: Realm | null;
  objectiveId?: string;
  keepId?: string;
  position: Position;
  home: Position;
  health: number;
  maxHealth: number;
  nextAttackAt: number;
  statuses: ActiveStatus[];
}
export interface CaravanState {
  id: string;
  realm: Realm;
  objectiveId: string;
  keepId: string;
  activationId: string;
  position: Position;
  route: Position[];
  routeIndex: number;
  health: number;
  maxHealth: number;
  unescortedSeconds: number;
  status: 'moving' | 'waiting' | 'delivered' | 'destroyed';
}
export interface EquipmentState {
  id: string;
  kind: EquipmentKind;
  realm: Realm;
  keepId: string;
  position: Position;
  operatorPosition?: Position;
  health: number;
  maxHealth: number;
  operators: string[];
  nextOperationAt: number;
  abandonedSeconds: number;
}
export interface ZoneState {
  id: string;
  config: ZoneConfig;
  activationId: string;
  activation: number;
  status: ZoneStatus;
  victor: Realm | null;
  seconds: number;
  stagingRemaining: number;
  cityRemaining: number | null;
  cityAttacker: Realm | null;
  objectives: Record<string, ObjectiveState>;
  keeps: Record<string, KeepState>;
  npcs: Record<string, NpcState>;
  caravans: Record<string, CaravanState>;
  equipment: Record<string, EquipmentState>;
  ramAvailableAt: Record<Realm, number>;
  influence: Record<Realm, number>;
  queue: string[];
  pendingImpacts: PendingImpact[];
}
export interface CampaignEvent {
  id: number;
  type: string;
  campaignId: string;
  zoneId?: string;
  activationId?: string;
  data: Record<string, string | number | boolean | null>;
}
export interface CampaignResult {
  round: number;
  winner: Realm;
  cityId: string;
  reason: 'city_captured' | 'city_defended';
}
export interface CampaignState {
  version: typeof ORVR_PROTOCOL_VERSION;
  id: string;
  round: number;
  phase: 'pairings' | 'central' | 'city' | 'recovery';
  seconds: number;
  recoveryRemaining: number;
  serial: number;
  eventSequence: number;
  tracks: Record<Pairing, { zoneIds: string[]; activeIndex: number; locked: boolean }>;
  zones: Record<string, ZoneState>;
  players: Record<string, PlayerState>;
  abilities: Record<string, AbilityRule>;
  /** Cumulative across reactivations and rounds, distinct from spendable keep stock. */
  contributions: Record<string, number>;
  results: CampaignResult[];
}
export type PlayerAction =
  | { type: 'move'; direction: { x: number; z: number } }
  | { type: 'attack'; targetId: string }
  | { type: 'ability'; abilityId: string; targetId: string }
  | { type: 'dispatch'; objectiveId: string }
  | { type: 'purchase'; keepId: string; equipment: EquipmentKind }
  | { type: 'board'; equipmentId: string }
  | { type: 'leaveEquipment' }
  | { type: 'operate'; equipmentId: string; targetId?: string }
  | { type: 'repair'; keepId: string; gate: GateKind }
  | { type: 'postern'; keepId: string; posternId?: string }
  | { type: 'transfer'; zoneId: string };
export interface PlayerCommand {
  version: typeof ORVR_PROTOCOL_VERSION;
  sequence: number;
  activationId: string;
  action: PlayerAction;
}
export interface CommandResult {
  ok: boolean;
  code?: string;
  events: CampaignEvent[];
}
export interface WorldSnapshot {
  version: typeof ORVR_PROTOCOL_VERSION;
  campaignId: string;
  round: number;
  phase: CampaignState['phase'];
  sequence: number;
  seconds: number;
  self: PlayerState | null;
  /** Only this zone is transmitted; distant moving entities are interest-filtered. */
  zone: ZoneState | null;
  players: RemotePlayerState[];
  fronts: { pairing: Pairing; zoneId: string | null; locked: boolean }[];
  queuePosition: number | null;
  result: CampaignResult | null;
}
/** Network-visible opponent/ally identity never includes account IDs, unlocks, resources, or private cooldowns. */
export type RemotePlayerState = Pick<PlayerState,
  'id' | 'displayName' | 'realm' | 'position' | 'health' | 'maxHealth' | 'avatarProfileKey' | 'className' | 'equipmentId' | 'facing' | 'statuses'>;
export type WorldUpdate = Omit<WorldSnapshot, 'zone'> & { zone: Omit<ZoneState, 'config'> | null };
export type ClientMessage =
  | { type: 'hello'; version: typeof ORVR_PROTOCOL_VERSION; token: string; characterId: string; zoneId?: string }
  | { type: 'command'; command: PlayerCommand }
  | { type: 'ping'; nonce: string };
export type ServerMessage =
  | { type: 'snapshot'; snapshot: WorldSnapshot }
  | { type: 'update'; snapshot: WorldUpdate }
  | { type: 'result'; sequence: number; result: CommandResult }
  | { type: 'error'; code: string; message: string }
  | { type: 'pong'; nonce: string };
