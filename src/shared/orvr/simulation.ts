import { defaultZoneConfigs, opposite, ORVR_RULES as R, ORVR_TRACKS } from './config';
import { campaignColliderBlocksHeight, campaignColliderContains, campaignGroundHeight } from './navigation';
import { ORVR_PROTOCOL_VERSION } from './protocol';
import { keepPosterns, nearbyKeepPostern, posternExitFor } from './postern';
import { equipmentOperatorPosition } from './equipment';
import type {
  CampaignConfig, CampaignEvent, CampaignState, CaravanState, CommandResult,
  EquipmentKind, EquipmentState, GateKind, GateState, KeepState, NpcState,
  ObjectiveState, Pairing, PlayerCommand, PlayerIdentity, PlayerState, Position,
  Realm, WorldSnapshot, ZoneConfig, ZoneState, ActiveStatus, AbilityRule, PendingImpact, SharedAbilityEffect,
} from './protocol';

const EPSILON = 1e-7;
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const distance = (a: Position, b: Position) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;
const positionValid = (p: Position) => p && finite(p.x) && finite(p.y) && finite(p.z);
const safeId = (id: unknown): id is string => typeof id === 'string' && id.length > 0 && id.length <= 300
  && !Object.hasOwn(Object.prototype, id) && id !== 'prototype';
const live = (p: PlayerState) => p.connected && !p.queued && p.health > 0;
const playersIn = (state: CampaignState, zone: ZoneState) => Object.values(state.players).filter(p => p.zoneId === zone.id);
const fail = (code: string): CommandResult => ({ ok: false, code, events: [] });

function emit(state: CampaignState, events: CampaignEvent[], type: string, zone: ZoneState | null, data: CampaignEvent['data'] = {}): void {
  events.push({ id: ++state.eventSequence, type, campaignId: state.id,
    ...(zone ? { zoneId: zone.id, activationId: zone.activationId } : {}), data });
}

function validateZoneConfig(config: ZoneConfig): void {
  const { bounds } = config;
  if (!config.id || !bounds || ![bounds.minX, bounds.maxX, bounds.minZ, bounds.maxZ].every(finite)
    || bounds.minX >= bounds.maxX || bounds.minZ >= bounds.maxZ) throw new Error(`Invalid bounds: ${config.id}`);
  if (!positionValid(config.staging.aegis) || !positionValid(config.staging.riftbound)) throw new Error(`Invalid staging: ${config.id}`);
  const ids = [...config.objectives.map(o => o.id), ...config.keeps.map(k => k.id)];
  if (new Set(ids).size !== ids.length || config.objectives.length !== 3) throw new Error(`Expected three unique objectives: ${config.id}`);
  if (config.kind !== 'city' && (config.keeps.length !== 2 || new Set(config.keeps.map(k => k.realm)).size !== 2)) {
    throw new Error(`Expected one keep per realm: ${config.id}`);
  }
  for (const objective of config.objectives) {
    if (!positionValid(objective.position) || (objective.captureRadius !== undefined && (!finite(objective.captureRadius) || objective.captureRadius <= 0))) {
      throw new Error(`Invalid objective position/radius: ${objective.id}`);
    }
    if (objective.guardCount !== undefined && (!Number.isSafeInteger(objective.guardCount) || objective.guardCount < 0 || objective.guardCount > 20)) {
      throw new Error(`Invalid guard count: ${objective.id}`);
    }
    for (const route of Object.values(objective.routes ?? {})) {
      if (!route || route.length < 2 || !route.every(positionValid)) throw new Error(`Invalid caravan route: ${objective.id}`);
    }
    if (objective.requiresObjectiveIds?.some(id => id === objective.id || !config.objectives.some(o => o.id === id))) {
      throw new Error(`Invalid objective prerequisite: ${objective.id}`);
    }
  }
  for (const keep of config.keeps) {
    if (![keep.position, keep.outerGate, keep.innerGate, keep.quartermaster].every(positionValid)) throw new Error(`Invalid keep: ${keep.id}`);
    for (const [kind, positions] of Object.entries(keep.siegeOperatorPositions ?? {})) {
      if ((kind !== 'oil' && kind !== 'catapult') || !positions.length || positions.length !== keep.siegePositions?.[kind]?.length
        || positions.some(point => !positionValid(point) || point.x < bounds.minX + .5 || point.x > bounds.maxX - .5 || point.z < bounds.minZ + .5 || point.z > bounds.maxZ - .5)) {
        throw new Error(`Invalid siege operator positions: ${keep.id}`);
      }
    }
    if (keep.posterns && (keep.posterns.length > 8 || keep.posterns.some(postern => !safeId(postern.id))
      || new Set(keep.posterns.map(postern => postern.id)).size !== keep.posterns.length)) {
      throw new Error(`Invalid postern identities: ${keep.id}`);
    }
    for (const postern of keepPosterns(keep)) {
      const { outside, inside, interactionRadius } = postern;
      if (![outside, inside].every(positionValid) || !finite(interactionRadius) || interactionRadius <= 0 || interactionRadius > 4
        || distance(outside, inside) <= interactionRadius * 2 || distance(outside, inside) > 12
        || [outside, inside].some(point => point.x < bounds.minX + .5 || point.x > bounds.maxX - .5 || point.z < bounds.minZ + .5 || point.z > bounds.maxZ - .5)) {
        throw new Error(`Invalid postern: ${keep.id}`);
      }
    }
  }
}

function freshZone(config: ZoneConfig): ZoneState {
  validateZoneConfig(config);
  return {
    id: config.id, config: clone(config), activationId: '', activation: 0, status: 'inactive', victor: null,
    seconds: 0, stagingRemaining: 0, cityRemaining: null, cityAttacker: null, objectives: {}, keeps: {},
    npcs: {}, caravans: {}, equipment: {}, ramAvailableAt: { aegis: 0, riftbound: 0 },
    influence: { aegis: 0, riftbound: 0 }, queue: [], pendingImpacts: [],
  };
}

function activateZone(state: CampaignState, zoneId: string, preparation: number = R.preparationSeconds, attacker: Realm | null = null): ZoneState {
  const zone = state.zones[zoneId];
  if (!zone) throw new Error(`Missing campaign zone: ${zoneId}`);
  zone.activation += 1;
  zone.activationId = `${state.id}:${state.round}:${zone.id}:${zone.activation}`;
  zone.status = preparation > 0 ? 'staging' : 'active';
  zone.seconds = 0;
  zone.stagingRemaining = preparation;
  zone.cityRemaining = zone.config.kind === 'city' ? R.citySeconds : null;
  zone.cityAttacker = attacker;
  zone.objectives = {};
  zone.keeps = {};
  zone.npcs = {};
  zone.caravans = {};
  zone.equipment = {};
  zone.pendingImpacts = [];
  zone.ramAvailableAt = { aegis: 0, riftbound: 0 };
  zone.influence = { aegis: 0, riftbound: 0 };
  for (const config of zone.config.objectives) {
    const owner = zone.config.kind === 'city' ? zone.config.defender ?? opposite(attacker ?? 'aegis') : null;
    const objective: ObjectiveState = {
      id: config.id, owner, capturingRealm: null, captureSeconds: 0, contested: false,
      productionSeconds: 0, readyShipment: false, caravanId: null, guardIds: [],
    };
    for (let index = 0; index < (config.guardCount ?? 2); index += 1) {
      const id = `${config.id}_guard_${index}`;
      const position = { ...config.position, x: config.position.x + (index ? 4 : -4) };
      zone.npcs[id] = { id, kind: 'guard', realm: owner, objectiveId: config.id,
        position, home: { ...position }, health: 80, maxHealth: 80, nextAttackAt: 0, statuses: [] };
      objective.guardIds.push(id);
    }
    zone.objectives[config.id] = objective;
  }
  for (const config of zone.config.keeps) {
    const commanderId = `${config.id}_commander`;
    const gate = (kind: GateKind): GateState => ({ id: `${config.id}_${kind}_gate`, health: 1_000, maxHealth: 1_000, lastDamagedAt: null });
    zone.keeps[config.id] = {
      id: config.id, owner: config.realm, deliveredSupplies: 0, supplies: 0, level: 1,
      gates: { outer: gate('outer'), inner: gate('inner') }, commanderId, capturingRealm: null, captureSeconds: 0,
    };
    zone.npcs[commanderId] = {
      id: commanderId, kind: 'commander', realm: config.realm, keepId: config.id,
      position: { ...config.position }, home: { ...config.position }, health: 600, maxHealth: 600, nextAttackAt: 0, statuses: [],
    };
  }
  for (const player of playersIn(state, zone)) {
    player.position = { ...zone.config.staging[player.realm] };
    player.health = player.maxHealth;
    player.direction = { x: 0, z: 0 };
    player.respawnRemaining = 0;
    player.repair = null;
    player.equipmentId = null;
    player.cooldowns = {};
    player.statuses = [];
    player.mana = player.maxMana;
    player.careerResource = player.combatProfile?.careerInitial ?? 0;
  }
  return zone;
}

export function createCampaign(config: CampaignConfig = {}): CampaignState {
  const definitions = new Map(defaultZoneConfigs().map(zone => [zone.id, zone]));
  for (const zone of config.zones ?? []) definitions.set(zone.id, zone);
  const state: CampaignState = {
    version: ORVR_PROTOCOL_VERSION, id: config.id ?? 'local-campaign', round: 1, phase: 'pairings', seconds: 0,
    recoveryRemaining: 0, serial: 0, eventSequence: 0,
    tracks: {
      west: { zoneIds: [...ORVR_TRACKS.west], activeIndex: 2, locked: false },
      east: { zoneIds: [...ORVR_TRACKS.east], activeIndex: 3, locked: false },
      central: { zoneIds: [...ORVR_TRACKS.central], activeIndex: -1, locked: true },
    },
    zones: Object.fromEntries([...definitions].map(([id, definition]) => [id, freshZone(definition)])),
    players: {}, abilities: {}, contributions: {}, results: [],
  };
  for (const ability of config.abilities ?? []) {
    if (!ability.id || !finite(ability.cooldownSeconds) || ability.cooldownSeconds < 0.25
      || !finite(ability.range) || ability.range < 0 || ability.range > 200
      || [ability.damage ?? 0, ability.healing ?? 0].some(value => !finite(value) || value < 0)) throw new Error('Invalid ability rule');
    state.abilities[ability.id] = clone(ability);
  }
  activateZone(state, 'sunmeadow_march', 0);
  activateZone(state, 'ashen_steppe', 0);
  return state;
}

function unboard(state: CampaignState, player: PlayerState): void {
  if (player.equipmentId) {
    const equipment = state.zones[player.zoneId]?.equipment[player.equipmentId];
    if (equipment) equipment.operators = equipment.operators.filter(id => id !== player.id);
  }
  player.equipmentId = null;
}

function fillQueue(state: CampaignState, zone: ZoneState, events: CampaignEvent[]): void {
  zone.queue = zone.queue.filter(id => state.players[id]?.connected && state.players[id].queued && state.players[id].zoneId === zone.id);
  for (const realm of ['aegis', 'riftbound'] as const) {
    let admitted = playersIn(state, zone).filter(p => p.connected && !p.queued && p.realm === realm).length;
    for (const id of [...zone.queue]) {
      const player = state.players[id];
      if (player.realm !== realm || admitted >= R.realmCapacity) continue;
      player.queued = false;
      player.position = { ...zone.config.staging[realm] };
      zone.queue = zone.queue.filter(queued => queued !== id);
      admitted += 1;
      emit(state, events, 'queue_admitted', zone, { playerId: id });
    }
  }
}

function joinZone(state: CampaignState, player: PlayerState, zone: ZoneState, events: CampaignEvent[]): void {
  const previous = state.zones[player.zoneId];
  if (previous && previous !== zone) {
    const clockOffset = zone.seconds - previous.seconds;
    player.cooldowns = Object.fromEntries(Object.entries(player.cooldowns).map(([id, until]) => [id, Math.max(zone.seconds, until + clockOffset)]));
    for (const status of player.statuses) {
      status.expiresAt += clockOffset;
      if (status.nextTickAt !== undefined) status.nextTickAt += clockOffset;
    }
  }
  unboard(state, player);
  if (previous) previous.queue = previous.queue.filter(id => id !== player.id);
  player.zoneId = zone.id;
  player.position = { ...zone.config.staging[player.realm] };
  player.direction = { x: 0, z: 0 };
  player.repair = null;
  player.movementExpiresAt = 0;
  player.queued = playersIn(state, zone).filter(p => p.id !== player.id && p.connected && !p.queued && p.realm === player.realm).length >= R.realmCapacity;
  if (player.queued) zone.queue.push(player.id);
  if (previous && previous !== zone) fillQueue(state, previous, events);
  emit(state, events, player.queued ? 'zone_queued' : 'zone_joined', zone, { playerId: player.id });
}

export function addPlayer(state: CampaignState, identity: PlayerIdentity): CommandResult {
  if (!identity || !safeId(identity.id) || !safeId(identity.userId) || !safeId(identity.characterId) || !['aegis', 'riftbound'].includes(identity.realm)) return fail('invalid_identity');
  if (identity.zoneId !== undefined && !safeId(identity.zoneId)) return fail('invalid_zone');
  const existing = state.players[identity.id];
  if (identity.combatProfile && Object.values(identity.combatProfile).some(value => !finite(value) || value < 0)) return fail('invalid_combat_profile');
  if (existing && (existing.userId !== identity.userId || existing.characterId !== identity.characterId || existing.realm !== identity.realm)) return fail('identity_mismatch');
  if (existing?.connected) return fail('already_connected');
  if (Object.values(state.players).some(p => p.id !== identity.id && p.connected && (p.characterId === identity.characterId || p.userId === identity.userId))) return fail('identity_in_use');
  const active = Object.values(state.zones).find(zone => zone.status === 'active' || zone.status === 'staging');
  const zone = state.zones[identity.zoneId ?? existing?.zoneId ?? active?.id ?? 'sunmeadow_march'];
  if (!zone) return fail('unknown_zone');
  const player: PlayerState = existing ?? {
    ...identity, zoneId: zone.id, connected: false, queued: false, position: { ...zone.config.staging[identity.realm] },
    health: identity.combatProfile?.maxHealth || R.playerHealth, maxHealth: identity.combatProfile?.maxHealth || R.playerHealth, respawnRemaining: 0, lastSequence: 0,
    direction: { x: 0, z: 0 }, movementExpiresAt: 0, cooldowns: {}, equipmentId: null, repair: null,
    mana: identity.combatProfile?.maxMana ?? 100, maxMana: identity.combatProfile?.maxMana ?? 100,
    careerResource: identity.combatProfile?.careerInitial ?? 0, careerMax: identity.combatProfile?.careerMax ?? 100,
    facing: { x: identity.realm === 'aegis' ? 1 : -1, z: 0 }, statuses: [],
  };
  // A replacement transport resumes the authoritative body. Only a real zone
  // transfer or queue admission starts at staging; session churn cannot reset
  // travel or permit old command sequences to execute again.
  const resumePosition = existing && existing.zoneId === zone.id && !existing.queued
    && positionValid(existing.position) ? { ...existing.position } : null;
  player.connected = true;
  player.abilityIds = identity.abilityIds ?? player.abilityIds ?? [];
  state.players[player.id] = player;
  const events: CampaignEvent[] = [];
  joinZone(state, player, zone, events);
  if (resumePosition && !player.queued) player.position = resumePosition;
  return { ok: true, events };
}

export function removePlayer(state: CampaignState, playerId: string): CommandResult {
  const player = state.players[playerId];
  if (!player) return fail('unknown_player');
  unboard(state, player);
  player.connected = false;
  player.direction = { x: 0, z: 0 };
  player.repair = null;
  const events: CampaignEvent[] = [];
  fillQueue(state, state.zones[player.zoneId], events);
  emit(state, events, 'player_disconnected', state.zones[player.zoneId], { playerId });
  return { ok: true, events };
}

function gateTarget(zone: ZoneState, id: string): { gate: GateState; keep: KeepState; kind: GateKind; position: Position } | null {
  for (const keep of Object.values(zone.keeps)) {
    const config = zone.config.keeps.find(k => k.id === keep.id)!;
    for (const kind of ['outer', 'inner'] as const) {
      if (keep.gates[kind].id === id) return { gate: keep.gates[kind], keep, kind, position: kind === 'outer' ? config.outerGate : config.innerGate };
    }
  }
  return null;
}

type Damageable = PlayerState | NpcState | CaravanState | EquipmentState;
function entity(state: CampaignState, zone: ZoneState, id: string): Damageable | null {
  const player = state.players[id];
  if (player?.zoneId === zone.id) return live(player) ? player : null;
  const found = zone.npcs[id] ?? zone.caravans[id] ?? zone.equipment[id];
  return found?.health > 0 ? found : null;
}

function validTarget(state: CampaignState, zone: ZoneState, player: PlayerState, id: string, range: number, healing = false): Damageable | null {
  const target = entity(state, zone, id);
  if (!target || distance(player.position, target.position) > range) return null;
  if (healing ? target.realm !== player.realm : target.realm === player.realm) return null;
  if ('keepId' in target && 'kind' in target && target.kind === 'commander') {
    const keep = zone.keeps[target.keepId!];
    if (keep.gates.outer.health > 0 || keep.gates.inner.health > 0) return null;
  }
  return target;
}

function destroyEquipment(state: CampaignState, zone: ZoneState, equipment: EquipmentState, events: CampaignEvent[]): void {
  equipment.health = 0;
  for (const id of equipment.operators) if (state.players[id]) state.players[id].equipmentId = null;
  equipment.operators = [];
  if (equipment.kind === 'ram') zone.ramAvailableAt[equipment.realm] = zone.seconds + R.ramReplacementSeconds;
  emit(state, events, 'equipment_destroyed', zone, { equipmentId: equipment.id });
}

function destroyCaravan(state: CampaignState, zone: ZoneState, caravan: CaravanState, events: CampaignEvent[]): void {
  if (caravan.status === 'destroyed' || caravan.status === 'delivered') return;
  caravan.health = 0;
  caravan.status = 'destroyed';
  if (zone.objectives[caravan.objectiveId]?.caravanId === caravan.id) zone.objectives[caravan.objectiveId].caravanId = null;
  emit(state, events, 'caravan_destroyed', zone, { caravanId: caravan.id });
}

function applyDamage(state: CampaignState, zone: ZoneState, target: Damageable, amount: number, sourceId: string, events: CampaignEvent[]): void {
  const source = entity(state, zone, sourceId);
  if (source && 'statuses' in source) {
    for (const status of source.statuses.filter(s => s.expiresAt > zone.seconds)) {
      if (status.kind === 'empower') amount *= 1 + status.magnitude;
      if (status.kind === 'debuff' && status.damageModifier === 'damage_dealt') amount *= Math.max(0.1, 1 - status.magnitude);
    }
  }
  if ('statuses' in target) {
    for (const status of target.statuses.filter(s => s.expiresAt > zone.seconds)) {
      if (status.kind === 'guard') amount *= Math.max(0.1, 1 - status.magnitude);
      if (status.kind === 'mark' || (status.kind === 'debuff' && status.damageModifier === 'damage_taken')) amount *= 1 + status.magnitude;
    }
    for (const status of target.statuses.filter(s => s.expiresAt > zone.seconds && s.kind === 'shield')) {
      const absorbed = Math.min(amount, status.shieldRemaining ?? 0);
      status.shieldRemaining = (status.shieldRemaining ?? 0) - absorbed;
      amount -= absorbed;
    }
  }
  amount = Math.max(0, Math.round(amount));
  target.health = Math.max(0, target.health - amount);
  emit(state, events, 'damage', zone, { targetId: target.id, sourceId, amount });
  if ('userId' in target) {
    target.repair = null;
    if (target.health === 0) {
      target.respawnRemaining = R.respawnSeconds;
      target.direction = { x: 0, z: 0 };
      target.statuses = [];
      unboard(state, target);
      emit(state, events, 'player_defeated', zone, { playerId: target.id });
    }
  } else if (target.health === 0 && 'operators' in target) destroyEquipment(state, zone, target, events);
  else if (target.health === 0 && 'route' in target) destroyCaravan(state, zone, target, events);
}

function movementMultiplier(statuses: ActiveStatus[], seconds: number): number {
  const active = statuses.filter(s => s.expiresAt > seconds);
  if (active.some(s => s.kind === 'root' || s.kind === 'stagger')) return 0;
  const slow = active.filter(s => s.kind === 'slow').reduce((highest, s) => Math.max(highest, s.magnitude), 0);
  const haste = active.filter(s => s.kind === 'haste').reduce((highest, s) => Math.max(highest, s.magnitude), 0);
  return Math.max(0.15, 1 - slow) * (1 + haste);
}

function movementDestination(zone: ZoneState, player: PlayerState, effect: SharedAbilityEffect, target: Damageable): Position | null {
  const movement = effect.movement!;
  let direction = { ...player.facing };
  let length = movement.distance;
  if (movement.mode === 'backward') direction = { x: -direction.x, z: -direction.z };
  if (movement.mode === 'toward_target') {
    const distanceToTarget = Math.hypot(target.position.x - player.position.x, target.position.z - player.position.z);
    if (distanceToTarget < EPSILON) return { ...player.position };
    direction = { x: (target.position.x - player.position.x) / distanceToTarget, z: (target.position.z - player.position.z) / distanceToTarget };
    length = Math.min(length, Math.max(0, distanceToTarget - 2.5));
  }
  let destination = { ...player.position };
  for (let step = 0.25; step <= length + 0.25; step += 0.25) {
    const fraction = Math.min(step, length);
    destination = { ...destination, x: player.position.x + direction.x * fraction, z: player.position.z + direction.z * fraction };
    destination.y = campaignGroundHeight(zone.config, destination);
    if (blocked(zone, destination)) return null;
  }
  return destination;
}

function activateAbility(state: CampaignState, zone: ZoneState, player: PlayerState, ability: AbilityRule, targetId: string, events: CampaignEvent[]): string | null {
  if (ability.unavailableReason) return 'ability_unavailable';
  if (player.equipmentId) return 'operating_equipment';
  const effects = ability.effects ?? [];
  const cleanses = effects.flatMap(effect => effect.cleanse?.kinds ?? []);
  const movement = effects.find(effect => effect.kind === 'movement' && effect.movement);
  if (player.statuses.some(status => status.expiresAt > zone.seconds && !cleanses.includes(status.kind)
    && (status.kind === 'stagger' || status.kind === 'silence' || (status.kind === 'root' && movement)))) return 'controlled_player';
  if ((player.cooldowns[ability.id] ?? 0) > zone.seconds + EPSILON) return 'ability_cooldown';
  if ((ability.gcdSeconds ?? 0) > 0 && (player.cooldowns.$global ?? 0) > zone.seconds + EPSILON) return 'global_cooldown';
  const resource = ability.resource ?? {};
  if (player.mana < (resource.manaCost ?? 0)) return 'insufficient_mana';
  if (player.careerResource < (resource.careerCost ?? 0) || player.careerResource < (resource.minCareer ?? 0)) return 'insufficient_resource';
  const targeting = ability.targeting;
  const target = targeting?.target === 'self' ? player
    : validTarget(state, zone, player, targetId, targeting?.range ?? ability.range, targeting?.target === 'ally');
  if (!target) return 'invalid_target';
  const destination = movement ? movementDestination(zone, player, movement, target) : null;
  if (movement && !destination) return 'movement_blocked';
  const spent = resource.spendAllCareer ? player.careerResource : resource.careerCost ?? 0;
  player.mana -= resource.manaCost ?? 0;
  player.careerResource = Math.max(0, Math.min(player.careerMax, player.careerResource - spent + (resource.careerBuild ?? 0)));
  player.cooldowns[ability.id] = zone.seconds + ability.cooldownSeconds;
  player.cooldowns.$global = zone.seconds + (ability.gcdSeconds ?? 0);
  player.repair = null;
  if (destination) {
    player.position = destination;
    emit(state, events, 'ability_movement', zone, { playerId: player.id, abilityId: ability.id, x: destination.x, y: destination.y, z: destination.z });
  }
  for (const effect of effects) {
    if (effect.kind === 'cleanse' && effect.cleanse) player.statuses = player.statuses.filter(s => !effect.cleanse!.kinds.includes(s.kind));
    if (effect.kind !== 'player_status' || !effect.playerStatus) continue;
    const buff = effect.playerStatus;
    const id = buff.stackGroup ?? `${ability.id}:${buff.kind}`;
    player.statuses = player.statuses.filter(s => s.id !== id && s.expiresAt > zone.seconds);
    player.statuses.push({ id, kind: buff.kind, expiresAt: zone.seconds + buff.durationSec, magnitude: buff.magnitude,
      sourceId: player.id, ...(buff.kind === 'shield' ? { shieldRemaining: player.maxHealth * buff.magnitude } : {}) });
  }
  if (effects.some(effect => ['damage', 'heal', 'status'].includes(effect.kind))) {
    const flight = targeting?.projectileSpeed ? Math.min(0.8, distance(player.position, target.position) / targeting.projectileSpeed) : 0;
    zone.pendingImpacts.push({
      id: `${zone.activationId}:impact:${++state.serial}`, sourceId: player.id, abilityId: ability.id, targetId: target.id,
      center: { ...target.position }, origin: { ...player.position }, facing: { ...player.facing },
      dueAt: zone.seconds + (ability.impactDelaySeconds ?? 0) + flight, resourceSpent: spent,
      strength: player.combatProfile?.strength ?? 10, level: player.combatProfile?.level ?? 1,
    });
  }
  emit(state, events, 'ability_used', zone, { playerId: player.id, abilityId: ability.id, targetId: target.id });
  return null;
}

function impactTargets(state: CampaignState, zone: ZoneState, source: PlayerState, impact: PendingImpact, ability: AbilityRule): Damageable[] {
  const targeting = ability.targeting;
  const target = entity(state, zone, impact.targetId);
  const all: Damageable[] = [
    ...playersIn(state, zone).filter(live), ...Object.values(zone.npcs), ...Object.values(zone.caravans), ...Object.values(zone.equipment),
  ];
  const hostile = all.filter(candidate => candidate.health > 0 && candidate.realm !== source.realm
    && !('kind' in candidate && candidate.kind === 'commander' && candidate.keepId
      && (zone.keeps[candidate.keepId].gates.outer.health > 0 || zone.keeps[candidate.keepId].gates.inner.health > 0)));
  const shape = targeting?.shape ?? 'melee';
  if (shape === 'area' || (shape === 'self' && (targeting?.radius ?? 0) > 0)) {
    return hostile.filter(candidate => distance(candidate.position, impact.center) <= (targeting?.radius ?? 4));
  }
  if (shape === 'cone') {
    const range = targeting?.range ?? ability.range;
    return hostile.filter(candidate => {
      const dx = candidate.position.x - impact.origin.x;
      const dz = candidate.position.z - impact.origin.z;
      const length = Math.hypot(dx, dz);
      return length <= range && (length < EPSILON || (dx / length * impact.facing.x + dz / length * impact.facing.z) >= Math.cos(Math.PI / 4));
    });
  }
  return target && target.realm !== source.realm ? [target] : [];
}

function effectAmount(effect: SharedAbilityEffect, impact: PendingImpact, targetId: string): number {
  const amount = effect.amount;
  if (!amount) return 0;
  // Seeded by the persisted impact identity: replay/recovery cannot reroll a critical transaction.
  let seed = 2166136261;
  for (const character of `${impact.id}:${targetId}`) seed = Math.imul(seed ^ character.charCodeAt(0), 16777619);
  const random = (seed >>> 0) / 0x1_0000_0000;
  return Math.max(1, Math.round(amount.min + random * (amount.max - amount.min)
    + (amount.statScale ?? 0) * impact.strength + (amount.levelScale ?? 0) * impact.level + (amount.resourceScale ?? 0) * impact.resourceSpent));
}

function tickCombatEffects(state: CampaignState, zone: ZoneState, events: CampaignEvent[]): void {
  const pending = zone.pendingImpacts;
  zone.pendingImpacts = [];
  for (const impact of pending) {
    if (impact.dueAt > zone.seconds + EPSILON) { zone.pendingImpacts.push(impact); continue; }
    const source = state.players[impact.sourceId];
    const ability = state.abilities[impact.abilityId];
    if (!source || !live(source) || source.zoneId !== zone.id || !ability) continue;
    const targets = impactTargets(state, zone, source, impact, ability);
    for (const effect of ability.effects ?? []) {
      if (effect.kind === 'heal') {
        const explicit = ability.targeting?.target === 'ally' ? entity(state, zone, impact.targetId) : source;
        if (explicit && explicit.health > 0 && explicit.realm === source.realm && ('statuses' in explicit)) {
          const amount = effectAmount(effect, impact, explicit.id);
          explicit.health = Math.min(explicit.maxHealth, explicit.health + amount);
          emit(state, events, 'healing', zone, { sourceId: source.id, targetId: explicit.id, amount });
        }
      }
      for (const target of targets) {
        if (target.health <= 0) continue;
        if (effect.kind === 'damage') applyDamage(state, zone, target, effectAmount(effect, impact, target.id), source.id, events);
        if (effect.kind !== 'status' || !effect.status || !('statuses' in target)) continue;
        const status = effect.status;
        const id = `${source.id}:${ability.id}:${status.id}`;
        target.statuses = target.statuses.filter(s => s.id !== id && s.expiresAt > zone.seconds);
        const periodic = status.kind === 'burn' || status.kind === 'bleed';
        target.statuses.push({ id, kind: status.kind, expiresAt: zone.seconds + status.durationSec,
          magnitude: status.magnitude ?? 0.15, damageModifier: status.damageModifier, sourceId: source.id,
          ...(periodic ? { nextTickAt: zone.seconds + 1, tickDamage: Math.max(1, Math.round(impact.strength * (status.magnitude ?? 0.15) + impact.level * 0.5)) } : {}) });
        emit(state, events, 'status_applied', zone, { targetId: target.id, sourceId: source.id, kind: status.kind, abilityId: ability.id });
      }
    }
  }
  const actors: (PlayerState | NpcState)[] = [...playersIn(state, zone).filter(live), ...Object.values(zone.npcs).filter(n => n.health > 0)];
  for (const actor of actors) {
    for (const status of actor.statuses) {
      if (status.nextTickAt !== undefined && status.tickDamage && status.nextTickAt <= zone.seconds + EPSILON && status.nextTickAt <= status.expiresAt + EPSILON) {
        applyDamage(state, zone, actor, status.tickDamage, status.sourceId, events);
        status.nextTickAt += 1;
      }
    }
    actor.statuses = actor.statuses.filter(status => status.expiresAt > zone.seconds + EPSILON && (status.kind !== 'shield' || (status.shieldRemaining ?? 0) > 0));
  }
}

function dispatch(state: CampaignState, zone: ZoneState, player: PlayerState, objectiveId: string, events: CampaignEvent[]): string | null {
  const objective = zone.objectives[objectiveId];
  const config = zone.config.objectives.find(o => o.id === objectiveId);
  if (!objective || !config || zone.config.kind === 'city') return 'invalid_objective';
  if (objective.owner !== player.realm || objective.contested) return 'objective_unavailable';
  if (distance(player.position, config.position) > R.interactionRadius) return 'out_of_range';
  if (!objective.readyShipment || objective.caravanId) return 'shipment_unavailable';
  const keep = Object.values(zone.keeps).find(k => k.owner === player.realm);
  if (!keep) return 'no_receiving_keep';
  const route = config.routes?.[player.realm];
  if (!route?.length) return 'route_unavailable';
  if (distance(route[0], config.position) > R.interactionRadius) return 'invalid_route_start';
  const keepConfig = zone.config.keeps.find(k => k.id === keep.id)!;
  if (distance(route[route.length - 1], keepConfig.deliveryPoint ?? keepConfig.quartermaster) > R.interactionRadius) return 'invalid_route_destination';
  const id = `${zone.activationId}:caravan:${++state.serial}`;
  zone.caravans[id] = {
    id, realm: player.realm, objectiveId, keepId: keep.id, activationId: zone.activationId,
    position: { ...route[0] }, route: clone(route), routeIndex: 1, health: 400, maxHealth: 400,
    unescortedSeconds: 0, status: 'waiting',
  };
  objective.readyShipment = false;
  objective.caravanId = id;
  emit(state, events, 'caravan_dispatched', zone, { caravanId: id, objectiveId, keepId: keep.id });
  return null;
}

const EQUIPMENT = {
  ram: { cost: 100, level: 2, cap: 1, health: 1_000 },
  oil: { cost: 50, level: 1, cap: 1, health: 300 },
  catapult: { cost: 150, level: 3, cap: 2, health: 500 },
} as const;

function purchase(state: CampaignState, zone: ZoneState, player: PlayerState, keepId: string, kind: EquipmentKind, events: CampaignEvent[]): string | null {
  const keep = zone.keeps[keepId];
  const config = zone.config.keeps.find(k => k.id === keepId);
  const rule = Object.hasOwn(EQUIPMENT, kind) ? EQUIPMENT[kind] : null;
  if (!keep || !config || !rule || keep.owner !== player.realm) return 'invalid_keep';
  if (distance(player.position, config.quartermaster) > R.interactionRadius) return 'out_of_range';
  if (keep.level < rule.level) return 'keep_level_required';
  if (keep.supplies < rule.cost) return 'insufficient_supplies';
  const existing = Object.values(zone.equipment).filter(e => e.health > 0 && e.kind === kind && (kind === 'ram' ? e.realm === player.realm : e.keepId === keepId));
  if (existing.length >= rule.cap) return 'equipment_capacity';
  if (kind === 'ram' && zone.ramAvailableAt[player.realm] > zone.seconds + EPSILON) return 'ram_replacement_cooldown';
  const positions = config.siegePositions?.[kind];
  const position = positions?.find(p => !existing.some(e => distance(e.position, p) < 1));
  if (!position) return 'siege_position_unavailable';
  const operatorPosition = kind === 'ram' ? undefined : config.siegeOperatorPositions?.[kind]?.[positions!.indexOf(position)];
  const id = `${zone.activationId}:${kind}:${++state.serial}`;
  zone.equipment[id] = {
    id, kind, realm: player.realm, keepId, position: { ...position }, health: rule.health, maxHealth: rule.health,
    ...(operatorPosition ? { operatorPosition: { ...operatorPosition } } : {}),
    operators: [], nextOperationAt: 0, abandonedSeconds: 0,
  };
  keep.supplies -= rule.cost;
  emit(state, events, 'equipment_purchased', zone, { playerId: player.id, equipmentId: id, kind, keepId, cost: rule.cost });
  return null;
}

function operate(state: CampaignState, zone: ZoneState, player: PlayerState, equipmentId: string, targetId: string | undefined, events: CampaignEvent[]): string | null {
  const equipment = zone.equipment[equipmentId];
  if (!equipment || equipment.health <= 0 || equipment.realm !== player.realm || !equipment.operators.includes(player.id)) return 'not_operator';
  if (equipment.nextOperationAt > zone.seconds + EPSILON) return 'equipment_cooldown';
  if (!targetId) return 'target_required';
  if (equipment.kind === 'ram') {
    const operators = equipment.operators.map(id => state.players[id]).filter(p => p && live(p) && p.equipmentId === equipment.id);
    if (operators.length < 2) return 'two_operators_required';
    const gate = gateTarget(zone, targetId);
    if (!gate || gate.keep.owner === player.realm || gate.gate.health <= 0) return 'invalid_gate';
    if (gate.kind === 'inner' && gate.keep.gates.outer.health > 0) return 'outer_gate_required';
    if (distance(equipment.position, gate.position) > 14) return 'out_of_range';
    gate.gate.health = Math.max(0, gate.gate.health - 100);
    gate.gate.lastDamagedAt = zone.seconds;
    equipment.nextOperationAt = zone.seconds + 3;
    emit(state, events, 'gate_damaged', zone, { gateId: gate.gate.id, equipmentId, amount: 100 });
  } else {
    const target = entity(state, zone, targetId);
    const range = equipment.kind === 'oil' ? 18 : 160;
    if (!target || target.realm === player.realm || distance(equipment.position, target.position) > range) return 'invalid_target';
    if ('kind' in target && target.kind === 'commander') return 'invalid_target';
    applyDamage(state, zone, target, equipment.kind === 'oil' ? 45 : 80, equipment.id, events);
    equipment.nextOperationAt = zone.seconds + (equipment.kind === 'oil' ? 4 : 6);
  }
  return null;
}

/** The server must persist the resulting state/events before acknowledging economic or ownership outcomes. */
export function submitCommand(state: CampaignState, playerId: string, command: PlayerCommand): CommandResult {
  const player = state.players[playerId];
  if (!player?.connected) return fail('not_connected');
  if (!command || command.version !== ORVR_PROTOCOL_VERSION || !command.action || typeof command.action.type !== 'string') return fail('invalid_command');
  if (!Number.isSafeInteger(command.sequence) || command.sequence <= player.lastSequence) return fail('stale_sequence');
  const zone = state.zones[player.zoneId];
  if (command.activationId !== zone.activationId) return fail('stale_activation');
  player.lastSequence = command.sequence;
  const action = command.action;
  // Transport validation is defense in depth: the shared authority rejects malformed wire payloads itself.
  const actionRecord = action as unknown as Record<string, unknown>;
  const idFields = ['targetId', 'abilityId', 'objectiveId', 'keepId', 'equipmentId', 'zoneId'];
  if (idFields.some(key => actionRecord[key] !== undefined && !safeId(actionRecord[key]))) return fail('invalid_command');
  const events: CampaignEvent[] = [];
  if (action.type === 'transfer') {
    const destination = state.zones[action.zoneId];
    if (!destination) return fail('unknown_zone');
    if (player.health <= 0) return fail('player_unavailable');
    if (destination.id === zone.id) return fail('already_in_zone');
    if (distance(player.position, zone.config.staging[player.realm]) > 30) return fail('staging_required');
    joinZone(state, player, destination, events);
    return { ok: true, events };
  }
  if (!live(player)) return fail(player.queued ? 'queued' : 'player_defeated');
  if (action.type === 'move') {
    if (!action.direction || !finite(action.direction.x) || !finite(action.direction.z)) return fail('invalid_direction');
    const magnitude = Math.hypot(action.direction.x, action.direction.z);
    player.direction = magnitude > 1 ? { x: action.direction.x / magnitude, z: action.direction.z / magnitude } : { ...action.direction };
    if (magnitude > 0) player.facing = { x: action.direction.x / magnitude, z: action.direction.z / magnitude };
    player.movementExpiresAt = zone.seconds + 0.35;
    if (magnitude > 0) player.repair = null;
    return { ok: true, events };
  }
  if (action.type === 'leaveEquipment') {
    unboard(state, player);
    return { ok: true, events };
  }
  if (zone.status !== 'active') return fail('zone_not_active');
  let error: string | null = null;
  switch (action.type) {
    case 'postern': {
      const keep = zone.keeps[action.keepId];
      const config = zone.config.keeps.find(keep => keep.id === action.keepId);
      if (!keep || !config || !keepPosterns(config).length || keep.owner !== player.realm) return fail('invalid_keep');
      if (player.equipmentId) return fail('operating_equipment');
      if (player.statuses.some(status => status.expiresAt > zone.seconds && ['root', 'stagger'].includes(status.kind))) return fail('controlled_player');
      if ((player.cooldowns.postern ?? 0) > zone.seconds + EPSILON) return fail('postern_cooldown');
      const postern = action.posternId === undefined ? nearbyKeepPostern(config, player.position)
        : keepPosterns(config).find(entry => entry.id === action.posternId);
      if (action.posternId !== undefined && !postern) return fail('invalid_postern');
      const destination = posternExitFor(postern, player.position);
      if (!destination) return fail('out_of_range');
      if (blocked(zone, destination)) return fail('postern_blocked');
      const occupied = playersIn(state, zone).some(other => other.id !== player.id && live(other) && distance(other.position, destination) < 1)
        || Object.values(zone.npcs).some(npc => npc.health > 0 && distance(npc.position, destination) < 1)
        || Object.values(zone.equipment).some(equipment => equipment.health > 0 && distance(equipmentOperatorPosition(equipment), destination) < 1.5);
      if (occupied) return fail('postern_occupied');
      player.position = destination;
      player.direction = { x: 0, z: 0 }; player.movementExpiresAt = zone.seconds; player.repair = null;
      player.cooldowns.postern = zone.seconds + 1;
      emit(state, events, 'postern_used', zone, { playerId, keepId: keep.id, ...(postern?.id ? { posternId: postern.id } : {}) });
      break;
    }
    case 'attack': {
      if (player.equipmentId) return fail('operating_equipment');
      if (player.statuses.some(s => s.expiresAt > zone.seconds && s.kind === 'stagger')) return fail('controlled_player');
      if ((player.cooldowns.basic_attack ?? 0) > zone.seconds + EPSILON) return fail('ability_cooldown');
      const target = validTarget(state, zone, player, action.targetId, 3.5);
      if (!target) return fail('invalid_target');
      applyDamage(state, zone, target, 20, player.id, events);
      player.cooldowns.basic_attack = zone.seconds + 1;
      break;
    }
    case 'ability': {
      const ability = state.abilities[action.abilityId];
      if (!ability || !player.abilityIds?.includes(action.abilityId)) return fail('ability_not_unlocked');
      if (ability.effects) {
        error = activateAbility(state, zone, player, ability, action.targetId, events);
        break;
      }
      if ((player.cooldowns[action.abilityId] ?? 0) > zone.seconds + EPSILON) return fail('ability_cooldown');
      const healing = (ability.healing ?? 0) > 0 && !(ability.damage ?? 0);
      const target = validTarget(state, zone, player, action.targetId, ability.range, healing);
      if (!target) return fail('invalid_target');
      if ((ability.damage ?? 0) > 0) applyDamage(state, zone, target, ability.damage!, player.id, events);
      if ((ability.healing ?? 0) > 0) {
        const recipient = healing ? target : player;
        if (!('userId' in recipient) && !('nextAttackAt' in recipient)) return fail('invalid_healing_target');
        recipient.health = Math.min(recipient.maxHealth, recipient.health + ability.healing!);
        emit(state, events, 'healing', zone, { sourceId: player.id, targetId: recipient.id, amount: ability.healing! });
      }
      player.cooldowns[action.abilityId] = zone.seconds + ability.cooldownSeconds;
      emit(state, events, 'ability_used', zone, { playerId, abilityId: action.abilityId, targetId: action.targetId });
      break;
    }
    case 'dispatch': error = dispatch(state, zone, player, action.objectiveId, events); break;
    case 'purchase': error = purchase(state, zone, player, action.keepId, action.equipment, events); break;
    case 'board': {
      const equipment = zone.equipment[action.equipmentId];
      if (!equipment || equipment.health <= 0 || equipment.realm !== player.realm) return fail('invalid_equipment');
      const operatorPosition = equipmentOperatorPosition(equipment);
      if (distance(player.position, operatorPosition) > 6) return fail('out_of_range');
      if (equipment.operatorPosition && blocked(zone, operatorPosition)) return fail('operator_position_blocked');
      if (player.equipmentId === equipment.id) return fail('already_operator');
      if (equipment.operators.length >= (equipment.kind === 'ram' ? 2 : 1)) return fail('equipment_full');
      unboard(state, player);
      equipment.operators.push(player.id);
      player.equipmentId = equipment.id;
      player.position = { ...operatorPosition };
      player.repair = null;
      emit(state, events, 'equipment_boarded', zone, { playerId, equipmentId: equipment.id });
      break;
    }
    case 'operate': error = operate(state, zone, player, action.equipmentId, action.targetId, events); break;
    case 'repair': {
      const keep = zone.keeps[action.keepId];
      const config = zone.config.keeps.find(k => k.id === action.keepId);
      if (!keep || !config || !['outer', 'inner'].includes(action.gate) || keep.owner !== player.realm) return fail('invalid_keep');
      const gate = keep.gates[action.gate];
      if (gate.health <= 0 || gate.health >= gate.maxHealth) return fail('gate_not_repairable');
      if (gate.lastDamagedAt !== null && zone.seconds - gate.lastDamagedAt < 30 - EPSILON) return fail('gate_under_attack');
      if (distance(player.position, action.gate === 'outer' ? config.outerGate : config.innerGate) > 8) return fail('out_of_range');
      if (keep.supplies < 25) return fail('insufficient_supplies');
      player.repair = { keepId: keep.id, gate: action.gate, remaining: 10, start: { ...player.position } };
      break;
    }
    default: return fail('unknown_action');
  }
  return error ? fail(error) : { ok: true, events };
}

function blocked(zone: ZoneState, position: Position, radius = 0.5): boolean {
  const b = zone.config.bounds;
  if (position.x < b.minX + radius || position.x > b.maxX - radius || position.z < b.minZ + radius || position.z > b.maxZ - radius) return true;
  for (const box of zone.config.collision ?? []) {
    if (!campaignColliderBlocksHeight(box, position.y, radius > 1 ? 3.5 : 1.8)) continue;
    if (campaignColliderContains(box, position, radius)) return true;
  }
  for (const keep of Object.values(zone.keeps)) {
    const config = zone.config.keeps.find(k => k.id === keep.id)!;
    for (const kind of ['outer', 'inner'] as const) {
      const gatePosition = kind === 'outer' ? config.outerGate : config.innerGate;
      const footprint = config.gateFootprints?.[kind] ?? { width: 2, depth: 14 };
      if (footprint.height !== undefined && (position.y >= gatePosition.y + footprint.height
        || position.y + (radius > 1 ? 3.5 : 1.8) <= gatePosition.y)) continue;
      const yaw = footprint.rotY ?? 0;
      const dx = position.x - gatePosition.x, dz = position.z - gatePosition.z;
      const localX = dx * Math.cos(yaw) + dz * Math.sin(yaw);
      const localZ = -dx * Math.sin(yaw) + dz * Math.cos(yaw);
      if (keep.gates[kind].health > 0 && Math.abs(localX) < footprint.width / 2 + radius && Math.abs(localZ) < footprint.depth / 2 + radius) return true;
    }
  }
  return false;
}

function moveBy(zone: ZoneState, position: Position, x: number, z: number, radius = 0.5): Position {
  const next = { ...position };
  const xStep = { ...next, x: next.x + x };
  xStep.y = campaignGroundHeight(zone.config, xStep);
  if (!blocked(zone, xStep, radius)) Object.assign(next, xStep);
  const zStep = { ...next, z: next.z + z };
  zStep.y = campaignGroundHeight(zone.config, zStep);
  if (!blocked(zone, zStep, radius)) Object.assign(next, zStep);
  next.y = campaignGroundHeight(zone.config, next);
  return next;
}

function tickPlayers(state: CampaignState, zone: ZoneState, dt: number, events: CampaignEvent[]): void {
  for (const player of playersIn(state, zone)) {
    if (!player.connected || player.queued) continue;
    if (player.health <= 0) {
      player.respawnRemaining = Math.max(0, player.respawnRemaining - dt);
      if (player.respawnRemaining <= EPSILON) {
        player.health = player.maxHealth;
        player.mana = player.maxMana;
        player.statuses = [];
        player.position = { ...zone.config.staging[player.realm] };
        emit(state, events, 'player_respawned', zone, { playerId: player.id });
      }
      continue;
    }
    if (zone.seconds > player.movementExpiresAt + EPSILON) player.direction = { x: 0, z: 0 };
    if (player.equipmentId) {
      const equipment = zone.equipment[player.equipmentId];
      if (equipment?.health > 0) {
        if (equipment.kind === 'ram' && equipment.operators[0] === player.id) {
          equipment.position = moveBy(zone, equipment.position, player.direction.x * 2.5 * dt, player.direction.z * 2.5 * dt, 1.5);
        }
        player.position = { ...equipmentOperatorPosition(equipment) };
      } else unboard(state, player);
    } else {
      const multiplier = movementMultiplier(player.statuses, zone.seconds);
      const next = moveBy(zone, player.position, player.direction.x * R.playerSpeed * dt * multiplier, player.direction.z * R.playerSpeed * dt * multiplier);
      if (zone.status !== 'staging' || distance(next, zone.config.staging[player.realm]) <= 30) player.position = next;
    }
    player.mana = Math.min(player.maxMana, player.mana + dt * 2);
    if (!player.repair) continue;
    const repair = player.repair;
    const keep = zone.keeps[repair.keepId];
    const gate = keep?.gates[repair.gate];
    if (zone.status !== 'active' || !keep || keep.owner !== player.realm || !gate || gate.health <= 0 || gate.health >= gate.maxHealth
      || distance(player.position, repair.start) > 0.5 || (gate.lastDamagedAt !== null && zone.seconds - gate.lastDamagedAt < 30 - EPSILON)) {
      player.repair = null;
      continue;
    }
    repair.remaining -= dt;
    if (repair.remaining <= EPSILON) {
      if (keep.supplies >= 25) {
        keep.supplies -= 25;
        gate.health = Math.min(gate.maxHealth, gate.health + gate.maxHealth * 0.1);
        emit(state, events, 'gate_repaired', zone, { playerId: player.id, gateId: gate.id, cost: 25 });
      }
      player.repair = null;
    }
  }
}

function tickNpcs(state: CampaignState, zone: ZoneState, dt: number, events: CampaignEvent[]): void {
  const players = playersIn(state, zone).filter(live);
  for (const npc of Object.values(zone.npcs)) {
    if (npc.health <= 0) continue;
    if (npc.kind === 'commander') {
      const keep = zone.keeps[npc.keepId!];
      if (keep.gates.outer.health > 0 || keep.gates.inner.health > 0) continue;
    }
    const target = players.filter(p => p.realm !== npc.realm && distance(p.position, npc.home) < 22)
      .sort((a, b) => distance(a.position, npc.position) - distance(b.position, npc.position) || a.id.localeCompare(b.id))[0];
    const destination = target?.position ?? npc.home;
    const d = distance(npc.position, destination);
    if (d > (target ? 2.5 : 0.2)) {
      const step = Math.min(d, 2.8 * dt * movementMultiplier(npc.statuses, zone.seconds));
      npc.position = moveBy(zone, npc.position, (destination.x - npc.position.x) / d * step, (destination.z - npc.position.z) / d * step);
    }
    if (target && d <= 3.5 && npc.nextAttackAt <= zone.seconds + EPSILON && !npc.statuses.some(s => s.kind === 'stagger' && s.expiresAt > zone.seconds)) {
      applyDamage(state, zone, target, npc.kind === 'commander' ? 12 : 5, npc.id, events);
      npc.nextAttackAt = zone.seconds + 1.5;
    }
  }
}

function presentRealms(state: CampaignState, zone: ZoneState, point: Position, radius: number): Set<Realm> {
  return new Set(playersIn(state, zone).filter(p => live(p) && distance(p.position, point) <= radius).map(p => p.realm));
}

function tickObjectives(state: CampaignState, zone: ZoneState, dt: number, events: CampaignEvent[]): void {
  for (const config of zone.config.objectives) {
    const objective = zone.objectives[config.id];
    const present = presentRealms(state, zone, config.position, config.captureRadius ?? 18);
    objective.contested = present.size > 1 || (objective.owner !== null && present.has(opposite(objective.owner)));
    const candidate = present.size === 1 ? [...present][0] : null;
    const hostileGuards = candidate && objective.guardIds.some(id => zone.npcs[id]?.health > 0 && zone.npcs[id].realm !== candidate);
    const prerequisites = candidate && (config.requiresObjectiveIds ?? []).every(id => zone.objectives[id]?.owner === candidate);
    if (!candidate || candidate === objective.owner || hostileGuards || !prerequisites) {
      objective.capturingRealm = null;
      objective.captureSeconds = 0;
    } else {
      if (objective.capturingRealm !== candidate) objective.captureSeconds = 0;
      objective.capturingRealm = candidate;
      objective.captureSeconds += dt;
      if (objective.captureSeconds + EPSILON >= R.captureSeconds) {
        objective.owner = candidate;
        objective.capturingRealm = null;
        objective.captureSeconds = 0;
        objective.productionSeconds = 0;
        objective.readyShipment = false;
        for (const id of objective.guardIds) {
          const guard = zone.npcs[id];
          guard.realm = candidate;
          guard.health = guard.maxHealth;
          guard.statuses = [];
          guard.position = { ...guard.home };
        }
        emit(state, events, 'objective_captured', zone, { objectiveId: objective.id, realm: candidate });
        continue;
      }
    }
    if (zone.config.kind !== 'city' && objective.owner && !objective.contested && !objective.readyShipment) {
      objective.productionSeconds += dt;
      if (objective.productionSeconds + EPSILON >= R.shipmentSeconds) {
        objective.readyShipment = true;
        objective.productionSeconds = 0;
        emit(state, events, 'shipment_ready', zone, { objectiveId: objective.id, realm: objective.owner });
      }
    }
  }
}

function tickCaravans(state: CampaignState, zone: ZoneState, dt: number, events: CampaignEvent[]): void {
  for (const caravan of Object.values(zone.caravans)) {
    if (caravan.status === 'delivered' || caravan.status === 'destroyed') continue;
    if (caravan.activationId !== zone.activationId || caravan.health <= 0) { destroyCaravan(state, zone, caravan, events); continue; }
    const escorts = playersIn(state, zone).filter(p => live(p) && p.realm === caravan.realm && distance(p.position, caravan.position) <= R.escortRadius);
    if (!escorts.length) {
      caravan.status = 'waiting';
      caravan.unescortedSeconds += dt;
      if (caravan.unescortedSeconds + EPSILON >= R.abandonmentSeconds) destroyCaravan(state, zone, caravan, events);
      continue;
    }
    caravan.status = 'moving';
    caravan.unescortedSeconds = 0;
    let remaining = R.caravanSpeed * dt;
    while (remaining > EPSILON && caravan.routeIndex < caravan.route.length) {
      const waypoint = caravan.route[caravan.routeIndex];
      const d = distance(caravan.position, waypoint);
      if (d <= remaining + EPSILON) {
        caravan.position = { ...waypoint };
        caravan.routeIndex += 1;
        remaining -= d;
      } else {
        const fraction = remaining / d;
        caravan.position = { x: caravan.position.x + (waypoint.x - caravan.position.x) * fraction,
          y: caravan.position.y + (waypoint.y - caravan.position.y) * fraction,
          z: caravan.position.z + (waypoint.z - caravan.position.z) * fraction };
        remaining = 0;
      }
    }
    if (caravan.routeIndex < caravan.route.length) continue;
    const keep = zone.keeps[caravan.keepId];
    if (!keep || keep.owner !== caravan.realm) { destroyCaravan(state, zone, caravan, events); continue; }
    caravan.status = 'delivered';
    caravan.health = 0;
    if (zone.objectives[caravan.objectiveId].caravanId === caravan.id) zone.objectives[caravan.objectiveId].caravanId = null;
    keep.deliveredSupplies += R.shipmentSupplies;
    keep.supplies = Math.min(R.supplyCap, keep.supplies + R.shipmentSupplies);
    keep.level = keep.deliveredSupplies >= 600 ? 3 : keep.deliveredSupplies >= 300 ? 2 : 1;
    zone.influence[caravan.realm] += R.shipmentSupplies;
    const realmKey = `${zone.id}:${caravan.realm}`;
    state.contributions[realmKey] = (state.contributions[realmKey] ?? 0) + R.shipmentSupplies;
    emit(state, events, 'supplies_delivered', zone, {
      transactionId: caravan.id, caravanId: caravan.id, keepId: keep.id, realm: caravan.realm,
      amount: R.shipmentSupplies, supplies: keep.supplies, deliveredSupplies: keep.deliveredSupplies, level: keep.level,
    });
  }
}

function tickEquipment(state: CampaignState, zone: ZoneState, dt: number, events: CampaignEvent[]): void {
  for (const equipment of Object.values(zone.equipment)) {
    if (equipment.health <= 0) continue;
    equipment.operators = equipment.operators.filter(id => {
      const player = state.players[id];
      return player && live(player) && player.zoneId === zone.id && player.equipmentId === equipment.id;
    });
    for (const id of equipment.operators) state.players[id].position = { ...equipmentOperatorPosition(equipment) };
    if (equipment.kind !== 'ram') continue;
    equipment.abandonedSeconds = equipment.operators.length ? 0 : equipment.abandonedSeconds + dt;
    if (equipment.abandonedSeconds + EPSILON >= R.abandonmentSeconds) destroyEquipment(state, zone, equipment, events);
  }
}

function tickKeeps(state: CampaignState, zone: ZoneState, dt: number, events: CampaignEvent[]): void {
  for (const keep of Object.values(zone.keeps)) {
    const config = zone.config.keeps.find(k => k.id === keep.id)!;
    const present = presentRealms(state, zone, config.position, 18);
    const candidate = present.size === 1 ? [...present][0] : null;
    if (!candidate || candidate === keep.owner || keep.gates.outer.health > 0 || keep.gates.inner.health > 0 || zone.npcs[keep.commanderId].health > 0) {
      keep.captureSeconds = 0;
      keep.capturingRealm = null;
      continue;
    }
    if (keep.capturingRealm !== candidate) keep.captureSeconds = 0;
    keep.capturingRealm = candidate;
    keep.captureSeconds += dt;
    if (keep.captureSeconds + EPSILON < R.captureSeconds) continue;
    keep.owner = candidate;
    keep.captureSeconds = 0;
    keep.capturingRealm = null;
    emit(state, events, 'keep_captured', zone, { keepId: keep.id, realm: candidate });
    // Resolve immediately so a later claim in this tick cannot overwrite the first committed victory.
    if (Object.values(zone.keeps).every(k => k.owner === candidate)) {
      winZone(state, zone, candidate, events);
      return;
    }
  }
}

function endCampaign(state: CampaignState, zone: ZoneState, winner: Realm, captured: boolean, events: CampaignEvent[]): void {
  if (state.phase === 'recovery') return;
  state.phase = 'recovery';
  state.recoveryRemaining = R.recoverySeconds;
  zone.status = 'secured';
  zone.victor = winner;
  const result = { round: state.round, winner, cityId: zone.id, reason: captured ? 'city_captured' as const : 'city_defended' as const };
  state.results.push(result);
  for (const track of Object.values(state.tracks)) track.locked = true;
  emit(state, events, 'campaign_ended', zone, { winner, reason: result.reason, round: state.round });
}

function winZone(state: CampaignState, zone: ZoneState, winner: Realm, events: CampaignEvent[]): void {
  if (zone.status !== 'active' || state.phase === 'recovery') return;
  zone.status = 'secured';
  zone.victor = winner;
  for (const caravan of Object.values(zone.caravans)) destroyCaravan(state, zone, caravan, events);
  emit(state, events, 'zone_won', zone, { realm: winner });
  const pairing = (Object.keys(state.tracks) as Pairing[]).find(key => {
    const track = state.tracks[key];
    return !track.locked && track.zoneIds[track.activeIndex] === zone.id;
  });
  if (!pairing) return;
  const track = state.tracks[pairing];
  const nextIndex = track.activeIndex + (winner === 'aegis' ? 1 : -1);
  if (nextIndex >= 0 && nextIndex < track.zoneIds.length) {
    track.activeIndex = nextIndex;
    const next = activateZone(state, track.zoneIds[nextIndex]);
    emit(state, events, 'front_advanced', next, { pairing, realm: winner, from: zone.id, to: next.id });
    return;
  }
  track.locked = true;
  if (pairing !== 'central') {
    if (state.phase !== 'pairings') return;
    state.phase = 'central';
    state.tracks.west.locked = true;
    state.tracks.east.locked = true;
    for (const other of Object.values(state.zones)) {
      if (other.status === 'active' || other.status === 'staging') other.status = 'inactive';
    }
    const central = state.tracks.central;
    central.locked = false;
    central.activeIndex = winner === 'aegis' ? 3 : 2;
    const next = activateZone(state, central.zoneIds[central.activeIndex]);
    emit(state, events, 'central_breakthrough', next, { realm: winner, pairing });
    return;
  }
  const prerequisites = winner === 'aegis' ? ['shatterline_expanse', 'rift_crownworks', 'rift_gate_fortress']
    : ['dawnline_expanse', 'aegis_crownworks', 'aegis_gate_fortress'];
  if (!prerequisites.every(id => state.zones[id].victor === winner)) {
    // Recover to the earliest unmet territorial prerequisite; never open a city from a malformed save.
    const missing = prerequisites.find(id => state.zones[id].victor !== winner)!;
    track.locked = false;
    track.activeIndex = track.zoneIds.indexOf(missing);
    activateZone(state, missing);
    return;
  }
  state.phase = 'city';
  const city = activateZone(state, winner === 'aegis' ? 'riftspire_capital' : 'aegis_capital', R.preparationSeconds, winner);
  emit(state, events, 'city_siege_opened', city, { realm: winner });
}

function startNextRound(state: CampaignState, events: CampaignEvent[]): void {
  state.round += 1;
  state.phase = 'pairings';
  state.recoveryRemaining = 0;
  for (const zone of Object.values(state.zones)) {
    zone.status = 'inactive';
    zone.victor = null;
    zone.caravans = {};
    zone.equipment = {};
    zone.influence = { aegis: 0, riftbound: 0 };
    for (const keep of Object.values(zone.keeps)) { keep.supplies = 0; keep.deliveredSupplies = 0; keep.level = 1; }
  }
  state.tracks.west.activeIndex = 2;
  state.tracks.east.activeIndex = 3;
  state.tracks.west.locked = false;
  state.tracks.east.locked = false;
  state.tracks.central.activeIndex = -1;
  state.tracks.central.locked = true;
  activateZone(state, 'sunmeadow_march');
  activateZone(state, 'ashen_steppe');
  for (const player of Object.values(state.players)) {
    player.equipmentId = null;
    player.repair = null;
    player.direction = { x: 0, z: 0 };
  }
  emit(state, events, 'campaign_started', null, { round: state.round });
}

/** Fixed substeps prevent client lag or a large scheduler delta from tunnelling through collision/captures. */
export function advanceSimulation(state: CampaignState, deltaSeconds: number): CampaignEvent[] {
  if (!finite(deltaSeconds) || deltaSeconds < 0 || deltaSeconds > 86_400) throw new Error('Invalid simulation delta');
  const events: CampaignEvent[] = [];
  let remaining = deltaSeconds;
  while (remaining > EPSILON) {
    const dt = Math.min(0.05, remaining);
    remaining -= dt;
    state.seconds += dt;
    state.serial += 1;
    if (state.phase === 'recovery') {
      state.recoveryRemaining -= dt;
      if (state.recoveryRemaining <= EPSILON) startNextRound(state, events);
    }
    for (const zone of Object.values(state.zones)) {
      if (!playersIn(state, zone).some(p => p.connected && !p.queued)) continue;
      zone.seconds += dt;
      tickPlayers(state, zone, dt, events);
      if (zone.status === 'staging') {
        zone.stagingRemaining = Math.max(0, zone.stagingRemaining - dt);
        if (zone.stagingRemaining <= EPSILON) {
          zone.status = 'active';
          emit(state, events, 'zone_activated', zone);
        }
        continue;
      }
      if (zone.status !== 'active') continue;
      tickNpcs(state, zone, dt, events);
      tickCombatEffects(state, zone, events);
      tickObjectives(state, zone, dt, events);
      tickCaravans(state, zone, dt, events);
      tickEquipment(state, zone, dt, events);
      tickKeeps(state, zone, dt, events);
      if (zone.config.kind === 'city' && zone.cityAttacker && zone.cityRemaining !== null) {
        const final = zone.config.objectives[zone.config.objectives.length - 1];
        if (zone.objectives[final.id].owner === zone.cityAttacker
          && (final.requiresObjectiveIds ?? []).every(id => zone.objectives[id].owner === zone.cityAttacker)) {
          endCampaign(state, zone, zone.cityAttacker, true, events);
        } else {
          zone.cityRemaining = Math.max(0, zone.cityRemaining - dt);
          if (zone.cityRemaining <= EPSILON) endCampaign(state, zone, opposite(zone.cityAttacker), false, events);
        }
      }
    }
  }
  return events;
}

export function snapshotFor(state: CampaignState, playerId: string): WorldSnapshot {
  const player = state.players[playerId];
  const source = player ? state.zones[player.zoneId] : null;
  const zone = source ? clone(source) : null;
  if (zone && player) {
    const near = (e: { position: Position }) => distance(e.position, player.position) <= R.snapshotRadius;
    zone.npcs = Object.fromEntries(Object.entries(zone.npcs).filter(([, npc]) => near(npc)));
    zone.caravans = Object.fromEntries(Object.entries(zone.caravans).filter(([, caravan]) => near(caravan)));
    zone.equipment = Object.fromEntries(Object.entries(zone.equipment).filter(([, equipment]) => near(equipment)));
    zone.queue = [];
  }
  const visible = source && player ? playersIn(state, source).filter(p => p.id !== playerId && live(p) && distance(p.position, player.position) <= R.snapshotRadius) : [];
  return {
    version: ORVR_PROTOCOL_VERSION, campaignId: state.id, round: state.round, phase: state.phase,
    sequence: state.serial, seconds: state.seconds, self: player ? clone(player) : null, zone,
    players: visible.map(p => ({
      id: p.id, displayName: p.displayName, realm: p.realm, position: { ...p.position }, health: p.health, maxHealth: p.maxHealth,
      avatarProfileKey: p.avatarProfileKey, className: p.className, equipmentId: p.equipmentId, facing: { ...p.facing }, statuses: clone(p.statuses),
    })),
    fronts: (Object.keys(state.tracks) as Pairing[]).map(pairing => {
      const track = state.tracks[pairing];
      return { pairing, zoneId: track.zoneIds[track.activeIndex] ?? null, locked: track.locked };
    }),
    queuePosition: player?.queued && source ? source.queue.filter(id => state.players[id]?.realm === player.realm).indexOf(playerId) + 1 : null,
    result: state.results[state.results.length - 1] ? clone(state.results[state.results.length - 1]) : null,
  };
}

/** Persist full state, not an interest-filtered snapshot. Reconnect requires a fresh verified session. */
export function restoreCampaign(saved: unknown): CampaignState {
  if (!saved || typeof saved !== 'object' || (saved as CampaignState).version !== ORVR_PROTOCOL_VERSION) throw new Error('Unsupported campaign save');
  const state = clone(saved as CampaignState);
  if (!state.id || !state.zones || !state.players || !state.tracks || !Number.isSafeInteger(state.round) || state.round < 1
    || !finite(state.seconds) || !finite(state.serial) || !finite(state.eventSequence)) throw new Error('Invalid campaign save');
  for (const zone of Object.values(state.zones)) {
    validateZoneConfig(zone.config);
    if (zone.id !== zone.config.id || !finite(zone.seconds) || !zone.objectives || !zone.keeps || !zone.equipment || !zone.caravans) throw new Error('Invalid saved zone');
    zone.queue = [];
    for (const equipment of Object.values(zone.equipment)) equipment.operators = [];
  }
  for (const player of Object.values(state.players)) {
    if (!state.zones[player.zoneId] || !positionValid(player.position)) throw new Error('Invalid saved player');
    player.connected = false;
    player.queued = false;
    player.direction = { x: 0, z: 0 };
    player.equipmentId = null;
    player.repair = null;
  }
  return state;
}
