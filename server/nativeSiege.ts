import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import type { CampaignEvent, CampaignState } from '../shared/orvr/protocol';
import { CAMPAIGN_EDGES, CAMPAIGN_NODES } from '../shared/data/campaign.generated';
import { CAPITAL_SIEGE_RULES, CAPITAL_SIEGE_RULES_VERSION, initialCapitalSiegeSnapshot,
  validateCapitalSiegeSnapshot, type NativeCapitalSiegeLease } from '../shared/siege/contract';
import { validateNativeCampaignCharacter, type NativeCampaignCharacterCheckpoint, type NativeCampaignCharacterAck } from '../shared/siege/character';
import type { ScenarioCharacter } from '../shared/scenarios/types';

export interface NativeSiegeOptions {
  /** Private loopback bootstrap credential; never a player or scenario-instance credential. */
  bootstrapKey: string;
  /** Revalidates actual published native packages and full-siege proof at activation. */
  verifyContent: () => string;
  now?: () => number;
}
export class NativeSiegeError extends Error {
  constructor(readonly status: number, message: string) { super(message); }
}
const reject = (message: string, status = 409): never => { throw new NativeSiegeError(status, message); };
const hash = (value: string) => createHash('sha256').update(value).digest('hex');
const id = (value: unknown): value is string => typeof value === 'string' && /^[a-zA-Z0-9_-]{1,100}$/.test(value)
  && !['__proto__', 'constructor', 'prototype'].includes(value);
const same = (a: string, b: string) => {
  const left = Buffer.from(a), right = Buffer.from(b);
  return left.length >= 32 && left.length === right.length && timingSafeEqual(left, right);
};
const prerequisites = ['dawnline_expanse', 'aegis_crownworks', 'aegis_gate_fortress'];
const canonicalZones = new Set<string>(CAMPAIGN_NODES.map(zone => zone.id));
type NativeJournal = NonNullable<CampaignState['nativeSiegeJournal']>;
const characterKey = (hostId: string, characterId: string) => `${hostId}:${characterId}`;
const characterAck = (c: NativeCampaignCharacterCheckpoint): NativeCampaignCharacterAck => ({ version: 1,
  characterId: c.characterId, revision: c.revision, recoveryPending: c.recoveryPending, respawnPending: c.respawnPending,
  walSequence: c.walSequence ?? 0 });
function checkedCharacter(value: unknown): ScenarioCharacter {
  try { validateNativeCampaignCharacter(value); }
  catch (error) { reject(error instanceof Error ? error.message : 'Invalid character state.', 400); }
  return value as ScenarioCharacter;
}
function preventInventoryRollback(previous: NativeCampaignCharacterCheckpoint | undefined, character: ScenarioCharacter): void {
  const oldInventory = previous?.character.document.inventory as Record<string, unknown> | undefined;
  const inventory = character.document.inventory as Record<string, unknown>;
  if (previous && Number.isSafeInteger(oldInventory?.revision) && Number.isSafeInteger(inventory.revision)
    && (inventory.revision as number) < (oldInventory!.revision as number)) reject('Saved inventory revision cannot roll back.');
  const before = previous?.character.document.runtime as Record<string, unknown> | undefined;
  const after = character.document.runtime as Record<string, unknown>;
  if (before?.version === 2 && (after.version !== 2
    || (after.capturedAtUnixMs as number) < (before.capturedAtUnixMs as number)))
    reject('A durable version2 character runtime cannot lose its codec or rewind its capture epoch. Admission must remain protected.');
}
function preserveUnreturnedLifecycle(previous: NativeCampaignCharacterCheckpoint | undefined, scope: unknown, activationId: unknown): void {
  if (previous && !previous.returned && (previous.scope !== scope || previous.activationId !== activationId))
    reject('Complete the durable character return before changing its encounter scope or activation. Admission must remain protected.');
}
function checkpointCharacter(journal: NativeJournal, lease: NativeCapitalSiegeLease, value: unknown,
  scope: 'participant' | 'evacuation', now: number, siegeSequence = lease.sequence, allowBaseline = false,
  returned = false): NativeCampaignCharacterCheckpoint {
  const character = checkedCharacter(value), key = characterKey(lease.hostId, character.id);
  const records = journal.characters ??= {};
  const previous = Object.hasOwn(records, key) ? records[key] : undefined;
  if (previous?.recoveryPending) reject('Restore and acknowledge the last durable character before changing it.');
  if (previous && previous.realm !== character.realm) reject('Character realm cannot change.');
  // A departure ACK must not be superseded by the visitor evacuation or a later lease.
  preserveUnreturnedLifecycle(previous, scope, lease.activationId);
  if (!previous && scope === 'participant' && !allowBaseline) reject('No durable participant baseline exists. Admission must remain protected.');
  const member = lease.participants.find(p => p.characterId === character.id);
  if (scope === 'participant' && !returned && member?.realm !== character.realm) reject('Character snapshot must match an approved participant.');
  if (scope === 'evacuation' && member) reject('An approved participant cannot be checkpointed as an evacuated visitor.');
  if (!canonicalZones.has(String(character.document.zone))) reject('Character checkpoint zone is not canonical.', 400);
  if (scope === 'evacuation' && !returned && character.document.zone !== lease.zoneId) reject('Evacuation checkpoints must originate in the leased capital.');
  // Opt-in seats and protected visitor evacuation are independently bounded by realm capacity.
  if (!returned && (!previous || previous.activationId !== lease.activationId || previous.returned)
    && Object.values(records).filter(c => c.activationId === lease.activationId && c.realm === character.realm
      && c.scope === scope && !c.returned).length >= CAPITAL_SIEGE_RULES.capacity)
    reject(`All ${CAPITAL_SIEGE_RULES.capacity} durable ${scope} slots for this realm are occupied.`);
  preventInventoryRollback(previous, character);
  const runtime = character.document.runtime as Record<string, unknown>;
  const record: NativeCampaignCharacterCheckpoint = { version: 1, characterId: character.id, hostId: lease.hostId,
    activationId: lease.activationId, realm: character.realm, scope, revision: (previous?.revision ?? 0) + 1,
    savedAt: now, siegeSequence, recoveryPending: false, returned,
    respawnPending: runtime.dead === true || runtime.health === 0, walSequence: previous?.walSequence ?? 0,
    ...(previous?.walBaseRevision !== undefined ? { walBaseRevision: previous.walBaseRevision } : {}),
    character: structuredClone(character) };
  records[key] = record; return record;
}
function checkpointParticipants(journal: NativeJournal, lease: NativeCapitalSiegeLease, values: unknown,
  now: number, sequence: number, barrier: boolean): NativeCampaignCharacterAck[] {
  if (values === undefined && lease.participants.every(p => p.connected === false)) values = [];
  if (values === undefined && !barrier) return [];
  if (!Array.isArray(values) || values.length > 36) reject('A bounded participant character snapshot array is required.', 400);
  const characters = (values as unknown[]).map(checkedCharacter), ids = characters.map(c => c.id);
  if (new Set(ids).size !== ids.length) reject('Duplicate character snapshots.', 400);
  if (barrier && lease.participants.some(p => p.connected !== false && !ids.includes(p.characterId)))
    reject('Every connected character must be durable before a siege milestone or return.');
  return characters.map(c => characterAck(checkpointCharacter(journal, lease, c, 'participant', now, sequence)));
}
export function nativeAegisSiegeEligible(state: CampaignState): boolean {
  const zone = state.zones.aegis_capital;
  return state.phase === 'city' && !!zone && ['staging', 'active'].includes(zone.status)
    && zone.cityAttacker === 'riftbound' && prerequisites.every(key => state.zones[key]?.victor === 'riftbound');
}
export function safeNativeEvacuationZones(state: CampaignState): Record<'aegis' | 'riftbound', string[]> {
  const adjacent = new Set(CAMPAIGN_EDGES.flatMap(([left, right]) => left === 'aegis_capital' ? [right] : right === 'aegis_capital' ? [left] : []));
  const safe = (realm: 'aegis' | 'riftbound') => [...adjacent].filter(id => {
    const zone = state.zones[id];
    return zone?.status === 'secured' && zone.victor === realm;
  }).sort();
  return { aegis: safe('aegis'), riftbound: safe('riftbound') };
}
function refreshLease(state: CampaignState, lease: NativeCapitalSiegeLease, now: number): string[] {
  const expired = lease.participants.filter(p => p.connected === false && (p.reconnectUntil ?? 0) <= now).map(p => p.characterId);
  lease.participants = lease.participants.filter(p => !expired.includes(p.characterId));
  lease.safeEvacuationZones = safeNativeEvacuationZones(state);
  return expired;
}
/** Stateless adapter over the authority's existing atomic campaign checkpoint/journal. */
export function nativeSiegeRequest(state: CampaignState, route: string, data: Record<string, unknown>, credential: string,
  options: NativeSiegeOptions): { response: unknown; events: CampaignEvent[] } {
  const now = (options.now ?? Date.now)();
  const journal: NativeJournal = structuredClone(state.nativeSiegeJournal ?? { hosts: {}, leases: {}, receipts: {} });
  if (!id(data.hostId)) reject('A valid native host identity is required.', 400);
  const hostId = data.hostId as string;
  if (route === 'register') {
    if (!options.bootstrapKey || !same(options.bootstrapKey, credential)) reject('Native bootstrap authentication required.', 403);
    const token = randomBytes(32).toString('hex');
    journal.hosts[hostId] = { tokenHash: hash(token) };
    for (const character of Object.values(journal.characters ?? {})) if (character.hostId === hostId && !character.returned) character.recoveryPending = true;
    const owned = state.zones.aegis_capital.nativeSiege;
    if (owned?.hostId === hostId && !owned.result) {
      owned.paused = true; journal.leases[owned.activationId] = owned;
    }
    state.nativeSiegeJournal = journal;
    return { response: { hostId, token, protocol: 1, zoneId: 'aegis_capital', characterRecovery: Object.values(journal.characters ?? {})
      .filter(c => c.hostId === hostId && !c.returned).map(characterAck) }, events: [] };
  }
  const host = Object.hasOwn(journal.hosts, hostId) ? journal.hosts[hostId] : undefined;
  if (!host || !credential || !same(host.tokenHash, hash(credential))) reject('Native host authentication required.', 403);
  if (route === 'status') {
    const lease = state.zones.aegis_capital.nativeSiege;
    const events: CampaignEvent[] = [];
    if (lease && !lease.result) for (const characterId of refreshLease(state, lease, now)) events.push({ id: ++state.eventSequence,
      type: 'native_city_siege_reservation_expired', campaignId: state.id, zoneId: lease.zoneId, activationId: lease.activationId, data: { characterId } });
    if (lease) journal.leases[lease.activationId] = lease;
    state.nativeSiegeJournal = journal;
    const characterSnapshots = lease?.hostId === hostId ? { version: 1, characters: Object.values(journal.characters ?? {})
      .filter(c => c.hostId === hostId && c.activationId === lease.activationId).map(c => structuredClone(c.character)) } : undefined;
    return { response: { eligible: nativeAegisSiegeEligible(state), safeEvacuationZones: safeNativeEvacuationZones(state),
      characterRecovery: Object.values(journal.characters ?? {}).filter(c => c.hostId === hostId && !c.returned).map(characterAck),
      lease: lease && !lease.result ? { ...structuredClone(lease), paused: lease.paused || now >= lease.expiresAt,
        ...(characterSnapshots ? { characterSnapshots } : {}) } : null }, events };
  }
  if (route === 'characters') {
    const lease = typeof data.activationId === 'string' && Object.hasOwn(journal.leases, data.activationId) ? journal.leases[data.activationId] : undefined;
    if (!lease || lease.hostId !== hostId) reject('This host does not own the character recovery activation.', 403);
    return { response: { version: 1, characters: Object.values(journal.characters ?? {}).filter(c => c.hostId === hostId
      && c.activationId === lease!.activationId).map(c => structuredClone(c.character)) }, events: [] };
  }
  if (!id(data.requestId)) reject('A durable request ID is required.', 400);
  // Restore acknowledgement alone cannot persist a relocated or respawned character.
  // Reject historical flag-only receipts before the idempotence shortcut as well.
  if (route === 'restored' && data.returned === true)
    reject('Complete character return with the full current document through its original activation and scope checkpoint.');
  if (route === 'checkpoint' && data.character && typeof data.character === 'object') {
    const characterId = (data.character as Record<string, unknown>).id;
    if (id(characterId)) preserveUnreturnedLifecycle(journal.characters?.[characterKey(hostId, characterId)], data.scope, data.activationId);
  }
  if ((route === 'restore' || route === 'replay') && typeof data.characterId === 'string') {
    const current = journal.characters?.[characterKey(hostId, data.characterId)];
    if (current?.returned) reject('This character completed its durable encounter return. Preserve any stale local WAL for protected recovery; an old encounter document cannot replace later campaign progression.');
  }
  const requestKey = `${hostId}:${data.requestId}`;
  const requestHash = hash(JSON.stringify({ route, data }));
  const prior = journal.receipts[requestKey];
  if (prior) {
    if (prior.hash !== requestHash) reject('Request ID was already used for a different operation.');
    if (route === 'replay' && typeof data.characterId === 'string') {
      const current = journal.characters?.[characterKey(hostId, data.characterId)];
      // A lost ACK can be retried after registration has put this character back into recovery.
      return { response: { ...(structuredClone(prior.response) as NativeCampaignCharacterAck),
        ...(current ? { recoveryPending: current.recoveryPending } : {}) }, events: [] };
    }
    return { response: structuredClone(prior.response), events: [] };
  }
  if (route === 'restore' || route === 'restored' || route === 'checkpoint' || route === 'replay') {
    let record: NativeCampaignCharacterCheckpoint;
    if (route === 'replay') {
      const lease = typeof data.activationId === 'string' && Object.hasOwn(journal.leases, data.activationId) ? journal.leases[data.activationId] : undefined;
      if (!lease || lease.hostId !== hostId) reject('This host does not own the native mutation WAL activation.', 403);
      if (!id(data.characterId) || !Number.isSafeInteger(data.baseRevision) || (data.baseRevision as number) < 1
        || !Number.isSafeInteger(data.walSequence) || (data.walSequence as number) < 1) reject('Invalid native mutation WAL revision or sequence.', 400);
      const character = checkedCharacter(data.character), key = characterKey(hostId, data.characterId as string);
      const previous = journal.characters && Object.hasOwn(journal.characters, key) ? journal.characters[key] : undefined;
      if (!previous || previous.activationId !== lease!.activationId || previous.hostId !== hostId || previous.returned
        || previous.characterId !== character.id || character.id !== data.characterId || previous.realm !== character.realm)
        reject('Native mutation WAL must match an unreturned owning-host character baseline.');
      if (!canonicalZones.has(String(character.document.zone))) reject('Character checkpoint zone is not canonical.', 400);
      if ((previous!.walSequence ?? 0) === data.walSequence && previous!.walBaseRevision === data.baseRevision
        && JSON.stringify(previous!.character) === JSON.stringify(character)) record = previous!;
      else {
        if (previous!.revision !== data.baseRevision || (previous!.walSequence ?? 0) + 1 !== data.walSequence)
          reject('Native mutation WAL conflicts with the latest durable revision or has a sequence gap. Admission must remain protected.');
        preventInventoryRollback(previous, character);
        const runtime = character.document.runtime as Record<string, unknown>;
        record = { ...previous!, revision: previous!.revision + 1, savedAt: now,
          walSequence: data.walSequence as number, walBaseRevision: data.baseRevision as number,
          respawnPending: runtime.dead === true || runtime.health === 0, character: structuredClone(character) };
        journal.characters![key] = record;
      }
    } else if (route === 'checkpoint') {
      const lease = typeof data.activationId === 'string' && Object.hasOwn(journal.leases, data.activationId) ? journal.leases[data.activationId] : undefined;
      if (!lease || lease.hostId !== hostId) reject('This host does not own the character checkpoint activation.', 403);
      if (!['participant', 'evacuation'].includes(String(data.scope))) reject('A character checkpoint scope is required.', 400);
      const character = checkedCharacter(data.character);
      if (data.returned === true) {
        const previous = journal.characters?.[characterKey(hostId, character.id)];
        if (!previous || previous.activationId !== lease!.activationId || previous.scope !== data.scope
          || previous.realm !== character.realm) reject('A matching trusted character baseline is required before completing return.');
        if (data.scope === 'evacuation' && !safeNativeEvacuationZones(state)[character.realm].includes(String(character.document.zone)))
          reject('The evacuation destination is no longer explicitly secured by this realm.');
        if (data.scope === 'participant' && !lease!.result && lease!.participants.some(p => p.characterId === character.id))
          reject('Leave the encounter before completing character return.');
        record = previous!.returned && JSON.stringify(previous!.character) === JSON.stringify(character) ? previous!
          : checkpointCharacter(journal, lease!, character, data.scope as 'participant' | 'evacuation', now, lease!.sequence, false, true);
      } else record = checkpointCharacter(journal, lease!, character, data.scope as 'participant' | 'evacuation', now);
    } else {
      if (!id(data.characterId)) reject('A stable trusted character identity is required.', 400);
      const key = characterKey(hostId, data.characterId as string);
      record = journal.characters && Object.hasOwn(journal.characters, key) ? journal.characters[key] : reject('No durable character exists. Admission must remain protected.');
      if (route === 'restore') record.recoveryPending = true;
      else {
        if (data.revision !== record.revision || !record.recoveryPending) reject('The recovery acknowledgement is stale or was not requested.');
        record.recoveryPending = false;
      }
    }
    const response = route === 'restore' ? structuredClone(record) : characterAck(record);
    journal.receipts[requestKey] = { hash: requestHash, response, kind: route === 'restore' ? 'character_restore' : 'character_ack' };
    const keys = Object.keys(journal.receipts).filter(key => key.startsWith(`${hostId}:`));
    for (const key of keys.slice(0, Math.max(0, keys.length - 256))) delete journal.receipts[key];
    state.nativeSiegeJournal = journal;
    return { response, events: [] };
  }
  let lease: NativeCapitalSiegeLease;
  const events: CampaignEvent[] = [];
  let characterAcks: NativeCampaignCharacterAck[] = [];
  const event = (type: string, values: CampaignEvent['data'] = {}) => events.push({ id: 0,
    type, campaignId: state.id, zoneId: 'aegis_capital', activationId: lease.activationId, data: values });
  if (route === 'activate') {
    if (!nativeAegisSiegeEligible(state)) reject('Enemy T4 front, inner T4 zone and fortress control are required.');
    if (data.rulesVersion !== CAPITAL_SIEGE_RULES_VERSION || typeof data.contentRevision !== 'string') reject('Unsupported native siege rules or content.', 400);
    let verified: string;
    try { verified = options.verifyContent(); } catch { reject('Full capital siege content proof is missing or stale.', 503); }
    if (verified! !== data.contentRevision) reject('Native capital content revision differs from the published proof.');
    const zone = state.zones.aegis_capital;
    const existing = zone.nativeSiege;
    if (existing && existing.round === state.round && existing.activationId === zone.activationId) {
      if (existing.hostId !== hostId) reject('Another native host owns this capital activation.');
      if (existing.contentRevision !== verified!) reject('Recover this activation with its original content revision.');
      lease = structuredClone(existing);
      lease.paused = false; lease.expiresAt = now + 15_000;
    } else {
      if (Object.values(zone.objectives).some(o => o.owner === zone.cityAttacker || o.captureSeconds > 0)
        || Object.values(zone.npcs).some(n => n.health < n.maxHealth)
        || (zone.status === 'active' && zone.cityRemaining !== null && zone.cityRemaining < 1800))
        reject('An existing legacy city round must finish before native activation.');
      lease = { ...CAPITAL_SIEGE_RULES, activationId: zone.activationId, campaignId: state.id, round: state.round,
        zoneId: 'aegis_capital', hostId, contentRevision: verified!, rulesVersion: 2, attacker: 'riftbound', defender: 'aegis',
        stats: 'campaign', expiresAt: now + 15_000, paused: false, sequence: 0,
        snapshot: initialCapitalSiegeSnapshot(), participants: [] };
      zone.nativeSiege = lease; journal.leases[lease.activationId] = lease;
      event('native_city_siege_leased', { hostId, rulesVersion: 2, contentRevision: verified! });
    }
  } else {
    if (typeof data.activationId !== 'string') reject('A capital activation is required.', 400);
    lease = Object.hasOwn(journal.leases, data.activationId as string)
      ? structuredClone(journal.leases[data.activationId as string]) : reject('Unknown native capital activation.');
    if (lease.hostId !== hostId) reject('This host does not own the capital activation.', 403);
    if (lease.result) {
      const reason = lease.result === 'city_captured' ? 'commander_defeated' : 'stage_timeout';
      // Native retries may receive a new request ID after a lost HTTP response.
      if (route === 'finish' && data.reason === reason) return { response: structuredClone(lease), events: [] };
      reject('The native capital result is already settled.');
    }
    if (state.zones.aegis_capital.activationId !== lease.activationId || state.round !== lease.round || state.phase !== 'city') reject('Capital activation is no longer current.');
    if (now >= lease.expiresAt || lease.paused) reject('Native lease expired. Reactivate with its original content to recover.');
    for (const characterId of refreshLease(state, lease, now)) event('native_city_siege_reservation_expired', { characterId });
    if (route === 'heartbeat') { /* Renew only the same authenticated owner. */ }
    else if (route === 'membership') {
      if (!id(data.characterId) || !['aegis', 'riftbound'].includes(String(data.realm)) || !['join', 'leave', 'disconnect'].includes(String(data.action))) reject('Invalid participant request.', 400);
      const index = lease.participants.findIndex(p => p.characterId === data.characterId);
      if (data.action === 'join') {
        if (lease.snapshot.phase === 'finished') reject('The siege has finished.');
        if (index >= 0 && lease.participants[index].realm !== data.realm) reject('Participant realm cannot change.');
        const character = checkedCharacter(data.character);
        if (character.id !== data.characterId || character.realm !== data.realm) reject('Enrollment character identity and realm must match.', 400);
        if (index < 0) {
          if (lease.participants.filter(p => p.realm === data.realm).length >= 18) reject('All eighteen realm seats are occupied.');
          lease.participants.push({ characterId: data.characterId as string, realm: data.realm as 'aegis' | 'riftbound', connected: true });
        }
        else { lease.participants[index].connected = true; delete lease.participants[index].reconnectUntil; }
        const existing = journal.characters?.[characterKey(hostId, character.id)];
        if (existing?.recoveryPending) reject('Restore the last durable character before enrolling.');
        characterAcks = [characterAck(checkpointCharacter(journal, lease, character, 'participant', now, lease.sequence, index < 0))];
      } else if (index >= 0 && data.action === 'disconnect') {
        const participant = lease.participants[index];
        if (participant.realm !== data.realm) reject('Participant realm cannot change.');
        if (participant.connected !== false) { participant.connected = false; participant.reconnectUntil = now + 120_000; }
        const record = journal.characters?.[characterKey(hostId, participant.characterId)];
        if (record) record.recoveryPending = true;
      } else if (index >= 0) {
        if (lease.participants[index].realm !== data.realm) reject('Participant realm cannot change.');
        const character = checkedCharacter(data.character);
        if (character.id !== data.characterId || character.realm !== data.realm) reject('Departure character identity and realm must match.', 400);
        characterAcks = [characterAck(checkpointCharacter(journal, lease, character, 'participant', now))];
        lease.participants.splice(index, 1);
      }
      event('native_city_siege_membership', { characterId: data.characterId as string, realm: String(data.realm), joined: data.action === 'join' });
    } else if (route === 'update') {
      if (!Number.isSafeInteger(data.sequence) || (data.sequence as number) <= lease.sequence) reject('Native snapshot sequence is stale.');
      try { validateCapitalSiegeSnapshot(data.snapshot, lease.snapshot); } catch (error) { reject(error instanceof Error ? error.message : 'Invalid snapshot.', 400); }
      const next = data.snapshot as NativeCapitalSiegeLease['snapshot'];
      characterAcks = checkpointParticipants(journal, lease, data.characters, now, data.sequence as number, true);
      lease.snapshot = structuredClone(next);
      lease.sequence = data.sequence as number;
      const zone = state.zones.aegis_capital;
      zone.status = lease.snapshot.phase === 'preparing' ? 'staging' : 'active';
      zone.stagingRemaining = lease.snapshot.phase === 'preparing' ? lease.snapshot.preparationRemaining ?? 180 : 0;
      event('native_city_siege_progress', { sequence: lease.sequence, stage: lease.snapshot.stage, completed: lease.snapshot.completed.join(',') });
    } else if (route === 'finish') {
      const s = lease.snapshot;
      if (s.phase !== 'finished') reject('A finished native snapshot is required.');
      if (lease.participants.some(p => p.connected !== false && (journal.characters?.[characterKey(hostId, p.characterId)]?.siegeSequence !== lease.sequence
        || journal.characters?.[characterKey(hostId, p.characterId)]?.recoveryPending))) reject('Character state must be durable before campaign settlement.');
      if (data.reason === 'commander_defeated') {
        if (!s.attackersWon || s.stage !== 2 || s.completed.length !== 8) reject('Both sides, center and commander are required for conquest.');
        lease.result = 'city_captured';
      } else if (data.reason === 'stage_timeout') {
        if (s.attackersWon || s.remaining !== 0 || s.overtimeRemaining !== 0 || s.completed.includes(7)) reject('A native stage timeout is required for defense.');
        lease.result = 'city_defended';
      } else reject('Unsupported native result.', 400);
      const zone = state.zones.aegis_capital, winner = lease.result === 'city_captured' ? lease.attacker : lease.defender;
      state.phase = 'recovery'; state.recoveryRemaining = 300; zone.status = 'secured'; zone.victor = winner;
      for (const track of Object.values(state.tracks)) track.locked = true;
      state.results.push({ round: state.round, winner, cityId: zone.id, reason: lease.result! });
      event('campaign_ended', { winner, reason: lease.result!, round: state.round });
    } else reject('Unknown native siege route.', 404);
    lease.expiresAt = now + 15_000;
  }
  state.nativeSiegeJournal = journal;
  refreshLease(state, lease!, now);
  journal.leases[lease!.activationId] = lease!;
  if (state.zones.aegis_capital.activationId === lease!.activationId) state.zones.aegis_capital.nativeSiege = lease!;
  const response = { ...structuredClone(lease!), characterAcks };
  journal.receipts[requestKey] = { hash: requestHash, response };
  // Retry receipts must survive restarts; keep a bounded recent window per host.
  const keys = Object.keys(journal.receipts).filter(key => key.startsWith(`${hostId}:`));
  for (const key of keys.slice(0, Math.max(0, keys.length - 256))) delete journal.receipts[key];
  for (const entry of events) entry.id = ++state.eventSequence;
  return { response, events };
}

export function pauseExpiredNativeSieges(state: CampaignState, now: number): CampaignEvent[] {
  const lease = state.zones.aegis_capital?.nativeSiege;
  if (!lease || lease.result) return [];
  const events: CampaignEvent[] = refreshLease(state, lease, now).map(characterId => ({ id: ++state.eventSequence,
    type: 'native_city_siege_reservation_expired', campaignId: state.id, zoneId: lease.zoneId, activationId: lease.activationId, data: { characterId } }));
  if (!lease.paused && now >= lease.expiresAt) {
    lease.paused = true;
    events.push({ id: ++state.eventSequence, type: 'native_city_siege_paused', campaignId: state.id,
      zoneId: lease.zoneId, activationId: lease.activationId, data: { hostId: lease.hostId } });
  }
  if (state.nativeSiegeJournal) state.nativeSiegeJournal.leases[lease.activationId] = lease;
  return events;
}
