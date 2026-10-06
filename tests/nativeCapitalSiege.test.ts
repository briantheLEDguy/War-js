import { createHash } from 'node:crypto';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createCampaign, advanceSimulation, addPlayer, submitCommand, snapshotFor, restoreCampaign, type CampaignState } from '../shared/orvr';
import type { ScenarioCharacter } from '../shared/scenarios/types';
import { initialCapitalSiegeSnapshot, validateCapitalSiegeSnapshot, type CapitalSiegeSnapshot, type NativeCapitalSiegeLease } from '../shared/siege/contract';
import { nativeSiegeRequest, nativeAegisSiegeEligible, safeNativeEvacuationZones } from '../server/nativeSiege';
import { startAuthority } from '../server/authority';
import { DevelopmentAuthenticator } from '../server/auth';
import { MemoryCampaignRepository } from '../server/persistence';

function readyCampaign(): CampaignState {
  const state = createCampaign({ id: 'native-proof' });
  state.phase = 'city';
  for (const key of ['dawnline_expanse', 'aegis_crownworks', 'aegis_gate_fortress']) state.zones[key].victor = 'riftbound';
  const city = state.zones.aegis_capital;
  city.cityAttacker = 'riftbound'; city.status = 'staging'; city.stagingRemaining = 180;
  city.activationId = `${state.id}:${state.round}:aegis_capital:1`; city.activation = 1; city.cityRemaining = 1800;
  return state;
}
const snapshot = (completed: number[], stage: 0 | 1 | 2 = 1): CapitalSiegeSnapshot => ({
  ...initialCapitalSiegeSnapshot(), stage, phase: 'active', elapsed: 200, remaining: 700, completed,
});
const character = (id: string, realm: 'aegis' | 'riftbound' = 'aegis', revision = 1): ScenarioCharacter => ({
  id, name: id, realm, visual: '/Game/Characters/Test', returnMap: '/Game/World', returnPosition: [10, 20, 30],
  document: { zone: 'aegis_capital', inventory: { revision, characterProgression: { level: 12, xp: 900, gold: 87 },
    items: [{ bagSlot: 0, key: 'earned_sword' }], equipment: [{ slot: 'weapon', bagSlot: 0 }], quests: ['active'] },
  runtime: { health: 1500, mana: 400, abilities: { resource: 20, globalCooldown: 1, cooldowns: [] },
    rewards: ['reward_receipt'], questKills: ['quest_receipt'], dead: false } },
});
describe('native live-capital siege contract', () => {
  it('accepts right-first permanent captures and rejects center before both sides', () => {
    const right = snapshot([0, 1, 2, 3, 5]);
    expect(() => validateCapitalSiegeSnapshot(right)).not.toThrow();
    expect(() => validateCapitalSiegeSnapshot(snapshot([0, 1, 2, 3, 5, 6]))).toThrow('prerequisites');
    const both = snapshot([0, 1, 2, 3, 4, 5]);
    validateCapitalSiegeSnapshot(both, right);
    expect(() => validateCapitalSiegeSnapshot(right, both)).toThrow('rolled back');
    expect(() => validateCapitalSiegeSnapshot({ ...both, overtimeRemaining: 121 })).toThrow('Invalid');
    expect(() => validateCapitalSiegeSnapshot({ ...right, phase: 'transition' })).toThrow('prerequisites');
  });
  it('suspends legacy city movement, combat, objectives and timers while native owns the activation', () => {
    const state = readyCampaign(), options = { bootstrapKey: 'b'.repeat(64), verifyContent: () => 'reviewed', now: () => 1000 };
    const registration = nativeSiegeRequest(state, 'register', { hostId: 'live-aegis' }, options.bootstrapKey, options).response as { token: string };
    const identity = { id: 'visitor', characterId: 'visitor', userId: 'visitor', realm: 'riftbound' as const, zoneId: 'aegis_capital' };
    addPlayer(state, identity);
    nativeSiegeRequest(state, 'activate', { hostId: 'live-aegis', requestId: 'lease', rulesVersion: 2, contentRevision: 'reviewed' }, registration.token, options);
    const before = structuredClone(state.zones.aegis_capital);
    advanceSimulation(state, 1810);
    expect(state.zones.aegis_capital).toEqual(before);
    expect(submitCommand(state, 'visitor', { version: 1, sequence: 1, activationId: before.activationId,
      action: { type: 'move', direction: { x: 1, z: 0 } } }).code).toBe('native_city_authority');
  });
  it('offers evacuation only through canonical adjacent territory explicitly secured by that realm', () => {
    const state = readyCampaign();
    expect(safeNativeEvacuationZones(state)).toEqual({ aegis: [], riftbound: [] });
    state.zones.sunmeadow_march.victor = 'aegis'; state.zones.sunmeadow_march.status = 'secured';
    state.zones.aegis_gate_fortress.victor = 'riftbound'; state.zones.aegis_gate_fortress.status = 'secured';
    state.zones.greybrook_crossing.victor = 'aegis'; state.zones.greybrook_crossing.status = 'secured';
    state.zones.brightfen_approach.victor = 'aegis'; state.zones.brightfen_approach.status = 'active';
    expect(safeNativeEvacuationZones(state)).toEqual({ aegis: ['sunmeadow_march'], riftbound: ['aegis_gate_fortress'] });
  });
  it('bounds the native milestone substep budget without extending stage or overtime clocks', () => {
    const finished = { ...snapshot([0, 1, 2, 3, 4, 5, 6, 7], 2), phase: 'finished' as const,
      attackersWon: true, elapsed: 3000.5, remaining: 0, overtimeRemaining: 0 };
    expect(() => validateCapitalSiegeSnapshot(finished)).not.toThrow();
    expect(() => validateCapitalSiegeSnapshot({ ...finished, elapsed: 3001.1 })).toThrow('Invalid');
    expect(() => validateCapitalSiegeSnapshot({ ...finished, overtimeRemaining: 120.1 })).toThrow('Invalid');
  });
  it('rejects returning a completed stage to active or rewinding the preparation clock', () => {
    const transition: CapitalSiegeSnapshot = { ...snapshot([0, 1, 2, 3], 0), phase: 'transition',
      remaining: 0, transitionRemaining: 60, overtimeRemaining: 0 };
    const rewound: CapitalSiegeSnapshot = { ...transition, phase: 'active', elapsed: 201,
      remaining: 840, transitionRemaining: 0, overtimeRemaining: 120 };
    expect(() => validateCapitalSiegeSnapshot(rewound, transition)).toThrow(/rolled back/);
    const preparing = { ...initialCapitalSiegeSnapshot(), preparationRemaining: 60 };
    expect(() => validateCapitalSiegeSnapshot({ ...preparing, preparationRemaining: 180 }, preparing)).toThrow(/rolled back/);
  });
  it('preserves recorded milestone times and permits only chronological appended captures', () => {
    const previous = { ...snapshot([0], 0), milestoneSeconds: [50] };
    const next = { ...snapshot([0, 1], 0), elapsed: 201, remaining: 699, milestoneSeconds: [50, 150] };
    expect(() => validateCapitalSiegeSnapshot(next, previous)).not.toThrow();
    for (const milestoneSeconds of [undefined, [], [10], [50, 40], [50, 150, 140]])
      expect(() => validateCapitalSiegeSnapshot({ ...next, milestoneSeconds }, previous)).toThrow(/milestone/i);
    expect(() => validateCapitalSiegeSnapshot({ ...next, milestoneSeconds: [150, 50] })).toThrow(/milestone/i);
    // Missing fields in historical documents keep their recorded representation.
    expect(() => validateCapitalSiegeSnapshot(snapshot([0], 0))).not.toThrow();
    expect(() => validateCapitalSiegeSnapshot(snapshot([0, 1], 0), snapshot([0], 0))).not.toThrow();
    expect(() => validateCapitalSiegeSnapshot(next, snapshot([0], 0))).not.toThrow();
  });
});

describe('trusted native capital HTTP authority', () => {
  const servers: Awaited<ReturnType<typeof startAuthority>>[] = [];
  afterEach(async () => { await Promise.all(servers.splice(0).map(server => server.close())); });
  async function fixture(state = readyCampaign()) {
    let time = 1000, verified = true;
    const repository = new MemoryCampaignRepository(); repository.checkpoint = { revision: 1, state };
    const options = { port: 0, auth: new DevelopmentAuthenticator(), repository, automaticTicks: false,
      nativeSiege: { bootstrapKey: 'b'.repeat(64), verifyContent: () => { if (!verified) throw new Error('unreviewed'); return 'reviewed'; }, now: () => time } };
    let server = await startAuthority(options); servers.push(server);
    const call = async (route: string, token: string, body: Record<string, unknown> = {}) => {
      body = { ...body };
      if (route === 'membership' && ['join', 'leave'].includes(String(body.action)) && body.character === undefined)
        body.character = character(String(body.characterId), body.realm as 'aegis' | 'riftbound');
      if (route === 'update' && body.characters === undefined) body.characters = server.inspect().zones.aegis_capital.nativeSiege?.participants
        .filter(p => p.connected !== false).map(p => character(p.characterId, p.realm)) ?? [];
      const response = await fetch(`${server.httpUrl}/native/siege/${route}`, { method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ hostId: 'live-aegis', ...body }) });
      return { status: response.status, ...(await response.json()) };
    };
    const registration = await call('register', options.nativeSiege.bootstrapKey);
    let token = registration.data.token as string;
    const activate = (requestId = 'activate') => call('activate', token, { requestId, rulesVersion: 2, contentRevision: 'reviewed' });
    return { call, get token() { return token; }, activate, repository, options, server: () => server,
      nativeRestart: async () => { token = (await call('register', options.nativeSiege.bootstrapKey)).data.token; },
      recoverCharacter: async (characterId: string) => {
        const recovered = await call('restore', token, { characterId, requestId: `restore_${time}_${characterId}` });
        return call('restored', token, { characterId, revision: recovered.data.revision, requestId: `restored_${time}_${characterId}` });
      },
      advance: (ms: number) => { time += ms; }, verified: (value: boolean) => { verified = value; },
      restart: async () => { await server.close(); servers.splice(servers.indexOf(server), 1); server = await startAuthority(options); servers.push(server); } };
  }
  it('requires actual territorial readiness, host authentication and fresh full-siege content proof', async () => {
    const state = readyCampaign(); state.zones.aegis_crownworks.victor = 'aegis';
    expect(nativeAegisSiegeEligible(state)).toBe(false);
    const f = await fixture(state);
    expect((await f.activate()).status).toBe(409);
    expect((await f.call('activate', 'scenario-instance-key', { requestId: 'forge', rulesVersion: 2, contentRevision: 'reviewed' })).status).toBe(403);
    expect(f.server().inspect().results).toHaveLength(0);
    const good = await fixture(); good.verified(false);
    expect((await good.activate()).status).toBe(503);
    expect((await fetch(`${good.server().httpUrl}/health`)).status).toBe(200);
    good.verified(true);
    expect((await good.activate()).data).toMatchObject({ stats: 'campaign', capacity: 18, preparationSeconds: 180,
      stageSeconds: 840, transitionSeconds: 60, overtimeSeconds: 120, rulesVersion: 2 });
  });
  it('rejects malformed or forged registration without pausing the campaign authority', async () => {
    const f = await fixture();
    const malformed = await fetch(`${f.server().httpUrl}/native/siege/register`, { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: 'null' });
    expect(malformed.status).toBe(400);
    expect((await f.call('register', 'é'.repeat(64))).status).toBe(403);
    expect((await f.call('status', 'forged-token', { hostId: 'toString' })).status).toBe(403);
    expect((await fetch(`${f.server().httpUrl}/health`)).status).toBe(200);
  });
  it('settles defense only after the trusted native timeout snapshot', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const body = { activationId: lease.activationId, requestId: 'finish', reason: 'stage_timeout' };
    expect((await f.call('finish', f.token, body)).status).toBe(409);
    const failed = { ...snapshot([0], 0), phase: 'finished' as const, attackersWon: false, elapsed: 840, remaining: 0, overtimeRemaining: 0 };
    await f.call('update', f.token, { activationId: lease.activationId, requestId: 'timeout', sequence: 1, snapshot: failed });
    expect((await f.call('finish', f.token, body)).data.result).toBe('city_defended');
    expect(f.server().inspect().results[0].winner).toBe('aegis');
  });
  it('admits eighteen opt-in humans per realm and journals right-first progress plus one conquest result', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    for (let i = 0; i < 18; i++) expect((await f.call('membership', f.token, { activationId: lease.activationId,
      requestId: `join_${i}`, characterId: `human_${i}`, realm: 'riftbound', action: 'join' })).status).toBe(200);
    expect((await f.call('membership', f.token, { activationId: lease.activationId, requestId: 'overflow', characterId: 'extra', realm: 'riftbound', action: 'join' })).status).toBe(409);
    const right = { activationId: lease.activationId, requestId: 'right', sequence: 1, snapshot: snapshot([0, 1, 2, 3, 5]) };
    expect((await f.call('update', f.token, right)).status).toBe(200);
    expect((await f.call('update', f.token, { ...right, requestId: 'center_early', sequence: 2, snapshot: snapshot([0, 1, 2, 3, 5, 6]) })).status).toBe(400);
    expect((await f.call('update', f.token, right)).data.sequence).toBe(1);
    expect((await f.call('update', f.token, { ...right, sequence: 2 })).status).toBe(409);
    const victory = { ...snapshot([0, 1, 2, 3, 4, 5, 6, 7], 2), elapsed: 1800, phase: 'finished' as const, attackersWon: true };
    expect((await f.call('update', f.token, { activationId: lease.activationId, requestId: 'commander', sequence: 2, snapshot: victory })).status).toBe(200);
    const finish = { activationId: lease.activationId, requestId: 'finish', reason: 'commander_defeated' };
    expect((await f.call('finish', f.token, finish)).data.result).toBe('city_captured');
    expect((await f.call('finish', f.token, finish)).status).toBe(200);
    expect(f.repository.checkpoint!.state.results).toHaveLength(1);
    expect((await f.call('finish', f.token, { ...finish, requestId: 'finish_lost_ack' })).status).toBe(200);
    expect((await f.call('status', f.token)).data.lease).toBeNull();
    expect((await f.call('finish', f.token, { ...finish, requestId: 'wrong_finish', reason: 'stage_timeout' })).status).toBe(409);
    await f.restart();
    expect((await f.call('finish', f.token, finish)).status).toBe(200);
    expect(f.server().inspect().results).toHaveLength(1);
  });
  it('pauses expired ownership and recovers original milestones without restarting legacy city clocks', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    await f.call('update', f.token, { activationId: lease.activationId, requestId: 'right', sequence: 1, snapshot: snapshot([0, 1, 2, 3, 5]) });
    f.advance(16_000); await f.server().step(1);
    expect((await f.call('status', f.token)).data.lease.paused).toBe(true);
    expect((await f.call('heartbeat', f.token, { activationId: lease.activationId, requestId: 'late' })).status).toBe(409);
    await f.restart();
    const recovered = await f.activate('recover');
    expect(recovered.data.snapshot.completed).toEqual([0, 1, 2, 3, 5]);
    expect(recovered.data.sequence).toBe(1);
    expect(recovered.data.paused).toBe(false);
    expect(f.server().inspect().zones.aegis_capital.cityRemaining).toBe(1800);
  });
  it('reserves disconnected human seats for 120 seconds, resumes the same realm and bounds repeated disconnects', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const member = { activationId: lease.activationId, characterId: 'human', realm: 'aegis' };
    await f.call('membership', f.token, { ...member, requestId: 'join', action: 'join' });
    const disconnected = await f.call('membership', f.token, { ...member, requestId: 'disconnect', action: 'disconnect' });
    expect(disconnected.data.participants[0]).toMatchObject({ connected: false, reconnectUntil: 121_000 });
    f.advance(10_000);
    const repeated = await f.call('membership', f.token, { ...member, requestId: 'disconnect_again', action: 'disconnect' });
    expect(repeated.data.participants[0].reconnectUntil).toBe(121_000);
    expect((await f.call('membership', f.token, { ...member, realm: 'riftbound', requestId: 'wrong_realm', action: 'join' })).status).toBe(409);
    expect((await f.call('membership', f.token, { ...member, requestId: 'pending_reconnect', action: 'join' })).status).toBe(409);
    expect((await f.recoverCharacter('human')).status).toBe(200);
    const resumed = await f.call('membership', f.token, { ...member, requestId: 'reconnect', action: 'join' });
    expect(resumed.data.participants[0].connected).toBe(true);
    expect(resumed.data.participants[0].reconnectUntil).toBeUndefined();
    await f.call('membership', f.token, { ...member, requestId: 'disconnect_final', action: 'disconnect' });
    f.advance(120_000); await f.server().step(1);
    expect((await f.call('status', f.token)).data.lease.participants).toEqual([]);
    await f.restart();
    const recovered = await f.activate('after_reservation');
    expect(recovered.data.participants).toEqual([]);
  });
  it('rolls back failed persistence before acknowledging native membership', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const log = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const commit = vi.spyOn(f.repository, 'commit').mockRejectedValue(new Error('disk unavailable'));
    try {
      expect((await f.call('membership', f.token, { activationId: lease.activationId, requestId: 'join', characterId: 'human', realm: 'aegis', action: 'join' })).status).toBe(503);
      expect(f.server().inspect().zones.aegis_capital.nativeSiege!.participants).toEqual([]);
    } finally { commit.mockRestore(); log.mockRestore(); }
  });
  it('recovers the last acknowledged full character after a native crash without accepting fresh defaults', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const member = { activationId: lease.activationId, characterId: 'human', realm: 'aegis', action: 'join' };
    const joined = await f.call('membership', f.token, { ...member, requestId: 'join' });
    expect(joined.data.characterAcks[0].revision).toBe(1);
    const earned = character('human', 'aegis', 2);
    (earned.document.inventory as Record<string, unknown>).pendingRewards = [{ key: 'earned_rune' }];
    (earned.document.runtime as Record<string, unknown>).health = 0;
    (earned.document.runtime as Record<string, unknown>).dead = true;
    const update = { activationId: lease.activationId, requestId: 'earned', sequence: 1,
      snapshot: snapshot([0], 0), characters: [earned] };
    const saved = await f.call('update', f.token, update);
    expect(saved.data.characterAcks[0]).toMatchObject({ revision: 2, respawnPending: true });
    expect((await f.call('update', f.token, update)).data.characterAcks[0].revision).toBe(2);
    await f.restart(); await f.nativeRestart();
    expect((await f.call('status', f.token)).data.characterRecovery[0]).toMatchObject({ characterId: 'human', revision: 2, recoveryPending: true });
    await f.activate('recovery');
    expect((await f.call('membership', f.token, { ...member, requestId: 'empty_ps', character: character('human') })).status).toBe(409);
    const restored = await f.call('restore', f.token, { requestId: 'restore', characterId: 'human' });
    expect(restored.data.character).toEqual(earned);
    expect(restored.data).toMatchObject({ version: 1, revision: 2, recoveryPending: true, respawnPending: true });
    expect((await f.call('restored', f.token, { requestId: 'stale_restore', characterId: 'human', revision: 1 })).status).toBe(409);
    expect((await f.call('restored', f.token, { requestId: 'restored', characterId: 'human', revision: 2 })).status).toBe(200);
    expect((await f.call('membership', f.token, { ...member, requestId: 'restored_join', character: earned })).status).toBe(200);
    expect((await f.call('restore', f.token, { requestId: 'missing', characterId: 'unknown_character' })).status).toBe(409);
  });
  it('rejects nonmember, mismatched and missing documents before changing clocks or private character state', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const member = { activationId: lease.activationId, characterId: 'human', realm: 'aegis', action: 'join' };
    expect((await f.call('membership', f.token, { ...member, requestId: 'no_baseline', character: null })).status).toBe(400);
    expect((await f.call('membership', f.token, { ...member, requestId: 'wrong_id', character: character('other') })).status).toBe(400);
    expect((await f.call('membership', f.token, { ...member, requestId: 'wrong_side', character: character('human', 'riftbound') })).status).toBe(400);
    await f.call('membership', f.token, { ...member, requestId: 'join' });
    const body = { activationId: lease.activationId, sequence: 1, snapshot: snapshot([0], 0) };
    expect((await f.call('update', f.token, { ...body, requestId: 'nonmember', characters: [character('intruder')] })).status).toBe(409);
    expect((await f.call('update', f.token, { ...body, requestId: 'mismatched', characters: [character('human', 'riftbound')] })).status).toBe(409);
    expect((await f.call('update', f.token, { ...body, requestId: 'missing_barrier', characters: [] })).status).toBe(409);
    expect((await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'forged_snapshot',
      scope: 'participant', character: character('intruder') })).status).toBe(409);
    expect(f.server().inspect().zones.aegis_capital.nativeSiege!.sequence).toBe(0);
    const records = f.server().inspect().nativeSiegeJournal!.characters!;
    expect(Object.keys(records)).toEqual(['live-aegis:human']);
    expect(records['live-aegis:human'].revision).toBe(1);
  });
  it('CAS-replays only the owning character WAL, rejects gaps/conflicts and keeps crash recovery protected', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const member = { activationId: lease.activationId, characterId: 'human', realm: 'aegis' };
    const joined = await f.call('membership', f.token, { ...member, requestId: 'join', action: 'join' });
    expect(joined.data.characterAcks[0]).toMatchObject({ revision: 1, walSequence: 0 });
    const earned = character('human', 'aegis', 2);
    (earned.document.inventory as Record<string, unknown>).characterProgression = { level: 13, gold: 999, xp: 1200 };
    const wal = { activationId: lease.activationId, characterId: 'human', baseRevision: 1, walSequence: 1, character: earned };
    const other = await f.call('register', f.options.nativeSiege.bootstrapKey, { hostId: 'other-host' });
    expect((await f.call('replay', other.data.token, { ...wal, hostId: 'other-host', requestId: 'forged_host' })).status).toBe(403);
    expect((await f.call('replay', f.token, { ...wal, character: character('intruder'), requestId: 'wrong_id' })).status).toBe(409);
    expect((await f.call('replay', f.token, { ...wal, walSequence: 2, requestId: 'gap' })).status).toBe(409);
    expect((await f.call('replay', f.token, { ...wal, baseRevision: 2, requestId: 'stale_base' })).status).toBe(409);
    const replayed = await f.call('replay', f.token, { ...wal, requestId: 'replay' });
    expect(replayed.data).toMatchObject({ revision: 2, walSequence: 1, recoveryPending: false });
    expect((await f.call('replay', f.token, { ...wal, requestId: 'lost_ack' })).data.revision).toBe(2);
    expect((await f.call('replay', f.token, { ...wal, character: character('human', 'aegis', 3), requestId: 'conflicting_doc' })).status).toBe(409);
    expect((await f.call('replay', f.token, { ...wal, baseRevision: 2, walSequence: 2,
      character: character('human', 'aegis', 1), requestId: 'inventory_rollback' })).status).toBe(409);
    await f.restart(); await f.nativeRestart();
    expect((await f.call('replay', f.token, { ...wal, requestId: 'replay' })).data).toMatchObject({ revision: 2, recoveryPending: true });
    expect((await f.call('membership', f.token, { ...member, character: earned, action: 'join', requestId: 'skip_restore' })).status).toBe(409);
    const recovered = await f.call('restore', f.token, { requestId: 'restore_wal', characterId: 'human' });
    expect(recovered.data).toMatchObject({ character: earned, revision: 2, walSequence: 1, recoveryPending: true });
    expect((await f.call('restored', f.token, { requestId: 'restored_wal', characterId: 'human', revision: 2 })).status).toBe(200);
  });
  it('does not acknowledge or overwrite a native mutation WAL when durable storage fails', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    await f.call('membership', f.token, { activationId: lease.activationId, requestId: 'join',
      characterId: 'human', realm: 'aegis', action: 'join' });
    vi.spyOn(f.repository, 'commit').mockRejectedValueOnce(new Error('WAL disk unavailable'));
    const earned = character('human', 'aegis', 2);
    expect((await f.call('replay', f.token, { activationId: lease.activationId, characterId: 'human', requestId: 'wal',
      baseRevision: 1, walSequence: 1, character: earned })).status).toBe(503);
    const saved = f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:human'];
    expect(saved).toMatchObject({ revision: 1, walSequence: 0, character: character('human') });
    expect((await fetch(`${f.server().httpUrl}/health`)).status).toBe(503);
  });
  it('rejects cached historical restore and WAL payloads after durable return and host restart', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const member = { activationId: lease.activationId, characterId: 'human', realm: 'aegis' };
    await f.call('membership', f.token, { ...member, requestId: 'join', action: 'join' });
    const earned = character('human', 'aegis', 2);
    const wal = { activationId: lease.activationId, characterId: 'human', baseRevision: 1, walSequence: 1,
      character: earned, requestId: 'successful_old_wal' };
    expect((await f.call('replay', f.token, wal)).status).toBe(200);
    const restore = { characterId: 'human', requestId: 'successful_old_restore' };
    expect((await f.call('restore', f.token, restore)).status).toBe(200);
    await f.call('restored', f.token, { characterId: 'human', requestId: 'restored', revision: 2 });
    await f.call('membership', f.token, { ...member, requestId: 'leave', action: 'leave', character: earned });
    await f.call('checkpoint', f.token, { activationId: lease.activationId, scope: 'participant', returned: true,
      character: earned, requestId: 'returned' });
    await f.restart(); await f.nativeRestart();
    expect((await f.call('restore', f.token, restore)).status).toBe(409);
    expect((await f.call('replay', f.token, wal)).status).toBe(409);
    expect((await f.call('restore', f.token, { ...restore, requestId: 'new_restore' })).status).toBe(409);
    expect((await f.call('replay', f.token, { ...wal, requestId: 'new_wal' })).status).toBe(409);
    expect((await f.call('characters', f.token, { activationId: lease.activationId })).data.characters).toEqual([earned]);
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:human']).toMatchObject({ returned: true,
      recoveryPending: false, character: earned });
  });
  it('keeps full documents private to the owning host and snapshots evacuees before safe return', async () => {
    const state = readyCampaign(); state.zones.aegis_gate_fortress.status = 'secured';
    addPlayer(state, { id: 'visitor', characterId: 'visitor', userId: 'visitor', realm: 'riftbound', zoneId: 'aegis_capital' });
    const f = await fixture(state), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const checkpoint = await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'evac_baseline',
      scope: 'evacuation', character: character('visitor', 'riftbound') });
    expect(checkpoint.data.revision).toBe(1);
    expect(JSON.stringify(snapshotFor(f.server().inspect(), 'visitor'))).not.toContain('earned_sword');
    const other = await f.call('register', f.options.nativeSiege.bootstrapKey, { hostId: 'other-host' });
    expect((await f.call('characters', other.data.token, { hostId: 'other-host', activationId: lease.activationId })).status).toBe(403);
    expect((await f.call('restore', other.data.token, { hostId: 'other-host', requestId: 'read_forgery', characterId: 'visitor' })).status).toBe(409);
    const restored = await f.call('restore', f.token, { requestId: 'evac_recover', characterId: 'visitor' });
    expect(restored.data).toMatchObject({ activationId: lease.activationId, scope: 'evacuation' });
    expect((await f.call('restored', f.token, { requestId: 'evac_restored', characterId: 'visitor', revision: restored.data.revision })).status).toBe(200);
    const returned = character('visitor', 'riftbound'); returned.document.zone = 'aegis_gate_fortress';
    expect((await f.call('checkpoint', f.token, { requestId: 'evac_returned', activationId: lease.activationId,
      scope: 'evacuation', returned: true, character: returned })).status).toBe(200);
    expect((await f.call('status', f.token)).data.characterRecovery).toEqual([]);
  });
  it('keeps recovery return custody until the relocated post-respawn full document is durable', async () => {
    const state = readyCampaign(); state.zones.aegis_gate_fortress.status = 'secured';
    const f = await fixture(state), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const defeated = character('visitor', 'riftbound');
    Object.assign(defeated.document.runtime, { dead: true, health: 0, mana: 0 });
    await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'baseline', scope: 'evacuation', character: defeated });
    await f.nativeRestart();
    const restored = await f.call('restore', f.token, { requestId: 'restore_visitor', characterId: 'visitor' });
    expect(restored.data).toMatchObject({ activationId: lease.activationId, scope: 'evacuation', revision: 1,
      recoveryPending: true, returned: false, respawnPending: true, character: defeated });
    const flagOnly = { hostId: 'live-aegis', requestId: 'flag_only_return', characterId: 'visitor', revision: 1, returned: true };
    expect((await f.call('restored', f.token, flagOnly)).status).toBe(409);
    // A pre-fix receipt must not release custody through the idempotence shortcut.
    const historical = f.server().inspect();
    historical.nativeSiegeJournal!.receipts['live-aegis:flag_only_return'] = {
      hash: createHash('sha256').update(JSON.stringify({ route: 'restored', data: flagOnly })).digest('hex'),
      response: { version: 1, characterId: 'visitor', revision: 1, recoveryPending: false, respawnPending: true, walSequence: 0 }, kind: 'character_ack' };
    expect(() => nativeSiegeRequest(historical, 'restored', flagOnly, f.token, f.options.nativeSiege)).toThrow(/full.*checkpoint/i);
    expect(historical.nativeSiegeJournal!.characters!['live-aegis:visitor']).toMatchObject({ returned: false, recoveryPending: true, character: defeated });
    expect((await f.call('restored', f.token, { requestId: 'restore_ack', characterId: 'visitor', revision: 1 })).status).toBe(200);
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:visitor']).toMatchObject({ returned: false,
      recoveryPending: false, respawnPending: true, character: defeated });
    const respawned = structuredClone(defeated); respawned.document.zone = 'aegis_gate_fortress';
    respawned.returnPosition = [300, 400, 500];
    Object.assign(respawned.document.runtime, { dead: false, health: 1500, mana: 400 });
    const completed = await f.call('checkpoint', f.token, { activationId: restored.data.activationId, scope: restored.data.scope,
      requestId: 'full_return', returned: true, character: respawned });
    expect(completed.status).toBe(200);
    expect(completed.data).toMatchObject({ revision: 2, recoveryPending: false, respawnPending: false, walSequence: 0 });
    await f.restart(); await f.nativeRestart();
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:visitor']).toMatchObject({ activationId: lease.activationId,
      scope: 'evacuation', returned: true, recoveryPending: false, respawnPending: false, character: respawned });
    expect((await f.call('status', f.token)).data.characterRecovery).toEqual([]);
  });
  it('reserves remote opt-in characters without rewriting their canonical zone or campaign state', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const remote = character('remote'); remote.document.zone = 'sunmeadow_march';
    const joined = await f.call('membership', f.token, { activationId: lease.activationId, requestId: 'remote',
      characterId: 'remote', realm: 'aegis', action: 'join', character: remote });
    expect(joined.status).toBe(200);
    const saved = f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:remote'];
    expect(saved.character.document.zone).toBe('sunmeadow_march');
    expect(saved.character.returnPosition).toEqual([10, 20, 30]);
    const unrecognized = character('intruder'); unrecognized.document.zone = 'fabricated_zone';
    expect((await f.call('membership', f.token, { activationId: lease.activationId, requestId: 'unknown_zone',
      characterId: 'intruder', realm: 'aegis', action: 'join', character: unrecognized })).status).toBe(400);
    expect((await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'remote_evac',
      scope: 'evacuation', character: remote })).status).toBe(409);
  });
  it('does not acknowledge a recovered full-document return when its durable commit fails', async () => {
    const state = readyCampaign(); state.zones.sunmeadow_march.status = 'secured'; state.zones.sunmeadow_march.victor = 'aegis';
    const f = await fixture(state), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const baseline = character('visitor');
    await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'baseline', scope: 'evacuation', character: baseline });
    await f.nativeRestart(); await f.recoverCharacter('visitor');
    const returned = structuredClone(baseline); returned.document.zone = 'sunmeadow_march'; returned.returnPosition = [700, 800, 900];
    const before = structuredClone(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:visitor']);
    vi.spyOn(f.repository, 'commit').mockRejectedValueOnce(new Error('Return storage unavailable'));
    expect((await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'full_return',
      scope: 'evacuation', returned: true, character: returned })).status).toBe(503);
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:visitor']).toEqual(before);
    expect(f.repository.checkpoint!.state.nativeSiegeJournal!.characters!['live-aegis:visitor']).toEqual(before);
    await f.restart(); await f.nativeRestart();
    expect((await f.call('status', f.token)).data.characterRecovery).toContainEqual(expect.objectContaining({ characterId: 'visitor', recoveryPending: true }));
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:visitor'].character).toEqual(baseline);
  });
  it('acknowledges evacuation return only from a saved baseline into current secured adjacent territory', async () => {
    const state = readyCampaign(); state.zones.sunmeadow_march.status = 'secured'; state.zones.sunmeadow_march.victor = 'aegis';
    const f = await fixture(state), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const safe = character('visitor'); safe.document.zone = 'sunmeadow_march'; safe.returnPosition = [300, 400, 500];
    const body = { activationId: lease.activationId, scope: 'evacuation', returned: true, character: safe };
    expect((await f.call('checkpoint', f.token, { ...body, requestId: 'no_initial_baseline' })).status).toBe(409);
    await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'baseline', scope: 'evacuation', character: character('visitor') });
    const unsafe = structuredClone(safe); unsafe.document.zone = 'brightfen_approach';
    expect((await f.call('checkpoint', f.token, { ...body, requestId: 'unsafe', character: unsafe })).status).toBe(409);
    const returned = await f.call('checkpoint', f.token, { ...body, requestId: 'return' });
    expect(returned.status).toBe(200);
    expect(returned.data.revision).toBe(2);
    expect((await f.call('checkpoint', f.token, { ...body, requestId: 'return_lost_ack' })).data.revision).toBe(2);
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:visitor']).toMatchObject({ returned: true, character: safe });
    expect((await f.call('status', f.token)).data.characterRecovery).toEqual([]);
    await f.restart();
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:visitor'].character).toEqual(safe);
  });
  it('budgets eighteen remote participants and eighteen evacuated visitors independently per realm', async () => {
    const state = readyCampaign(); state.zones.sunmeadow_march.status = 'secured'; state.zones.sunmeadow_march.victor = 'aegis';
    const f = await fixture(state), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    for (let i = 0; i < 18; i++) {
      const remote = character(`remote_${i}`); remote.document.zone = 'sunmeadow_march';
      expect((await f.call('membership', f.token, { activationId: lease.activationId, requestId: `join_remote_${i}`,
        characterId: remote.id, realm: 'aegis', action: 'join', character: remote })).status).toBe(200);
    }
    expect((await f.call('membership', f.token, { activationId: lease.activationId, requestId: 'nineteenth_participant',
      characterId: 'remote_18', realm: 'aegis', action: 'join' })).status).toBe(409);
    for (let i = 0; i < 18; i++) expect((await f.call('checkpoint', f.token, { activationId: lease.activationId,
      requestId: `visitor_${i}`, scope: 'evacuation', character: character(`visitor_${i}`) })).status).toBe(200);
    const overflow = { activationId: lease.activationId, scope: 'evacuation', character: character('visitor_18') };
    expect((await f.call('checkpoint', f.token, { ...overflow, requestId: 'nineteenth_visitor' })).status).toBe(409);
    const saved = f.server().inspect(), records = Object.values(saved.nativeSiegeJournal!.characters!);
    expect(records.filter(c => c.realm === 'aegis' && !c.returned)).toHaveLength(36);
    for (const scope of ['participant', 'evacuation'] as const) {
      const corrupt = structuredClone(saved), extra = structuredClone(records.find(c => c.scope === scope)!);
      extra.characterId = `overflow_${scope}`; extra.character.id = extra.characterId;
      corrupt.nativeSiegeJournal!.characters![`live-aegis:${extra.characterId}`] = extra;
      expect(() => restoreCampaign(corrupt)).toThrow(/durable character capacity/);
    }
    await f.restart();
    expect(f.server().inspect().nativeSiegeJournal!.characters).toEqual(saved.nativeSiegeJournal!.characters);
    const returned = character('visitor_0'); returned.document.zone = 'sunmeadow_march';
    expect((await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'visitor_0_returned',
      scope: 'evacuation', returned: true, character: returned })).status).toBe(200);
    expect((await f.call('checkpoint', f.token, { ...overflow, requestId: 'visitor_after_return' })).status).toBe(200);
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:visitor_0']).toMatchObject({ returned: true, character: returned });
    expect(Object.values(f.server().inspect().nativeSiegeJournal!.characters!).filter(c => !c.returned)).toHaveLength(36);
  });
  it('commits participant return after leaving and excludes released characters from crash rewind', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const member = { activationId: lease.activationId, characterId: 'human', realm: 'aegis' };
    await f.call('membership', f.token, { ...member, requestId: 'join', action: 'join' });
    expect((await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'member_evac',
      scope: 'evacuation', character: character('human') })).status).toBe(409);
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:human'].scope).toBe('participant');
    const body = { activationId: lease.activationId, scope: 'participant', returned: true, character: character('human') };
    expect((await f.call('checkpoint', f.token, { ...body, requestId: 'premature_return' })).status).toBe(409);
    await f.call('membership', f.token, { ...member, requestId: 'leave', action: 'leave' });
    expect((await f.call('checkpoint', f.token, { ...body, requestId: 'returned' })).status).toBe(200);
    await f.restart(); await f.nativeRestart();
    expect((await f.call('status', f.token)).data.characterRecovery).toEqual([]);
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:human']).toMatchObject({ returned: true, recoveryPending: false });
  });
  it('preserves an unreturned departure against evacuation or another activation, then permits a new visitor lifecycle', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    const member = { activationId: lease.activationId, characterId: 'human', realm: 'aegis' };
    await f.call('membership', f.token, { ...member, requestId: 'join', action: 'join' });
    const departure = character('human', 'aegis', 2);
    (departure.document.inventory as Record<string, unknown>).characterProgression = { level: 12, xp: 925, gold: 94 };
    (departure.document.runtime as Record<string, unknown>).rewards = ['reward_receipt', 'departure_reward'];
    await f.call('membership', f.token, { ...member, requestId: 'leave', action: 'leave', character: departure });
    const original = structuredClone(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:human']);
    expect(original.character).toEqual(departure);
    const raced = await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'raced_evacuation',
      scope: 'evacuation', character: character('human') });
    expect(raced.status).toBe(409); expect(raced.error).toMatch(/durable character return/);
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:human']).toEqual(original);
    // A hypothetical later owned lease cannot replace this still-unreturned canonical document.
    const state = f.server().inspect(), other = { ...structuredClone(lease), activationId: 'later_activation', participants: [] };
    state.nativeSiegeJournal!.leases[other.activationId] = other;
    expect(() => nativeSiegeRequest(state, 'checkpoint', { hostId: 'live-aegis', activationId: other.activationId,
      requestId: 'different_activation', scope: 'participant', character: character('human') }, f.token, f.options.nativeSiege))
      .toThrow(/scope or activation/);
    expect(state.nativeSiegeJournal!.characters!['live-aegis:human']).toEqual(original);
    expect((await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'departure_ack',
      scope: 'participant', returned: true, character: departure })).status).toBe(200);
    const visitor = await f.call('checkpoint', f.token, { activationId: lease.activationId, requestId: 'new_visitor',
      scope: 'evacuation', character: departure });
    expect(visitor.status).toBe(200);
    expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:human']).toMatchObject({
      scope: 'evacuation', returned: false, revision: original.revision + 2, character: departure });
    // A cached former evacuation ACK cannot bypass the canonical lifecycle check either.
    const changedLifecycle = f.server().inspect();
    changedLifecycle.nativeSiegeJournal!.characters!['live-aegis:human'].scope = 'participant';
    const beforeRetry = structuredClone(changedLifecycle.nativeSiegeJournal!.characters!['live-aegis:human']);
    expect(() => nativeSiegeRequest(changedLifecycle, 'checkpoint', { hostId: 'live-aegis', activationId: lease.activationId,
      requestId: 'new_visitor', scope: 'evacuation', character: departure }, f.token, f.options.nativeSiege))
      .toThrow(/durable character return/);
    expect(changedLifecycle.nativeSiegeJournal!.characters!['live-aegis:human']).toEqual(beforeRetry);
  });
  it('rolls back character progression and siege clocks together when the checkpoint write fails', async () => {
    const f = await fixture(), lease = (await f.activate()).data as NativeCapitalSiegeLease;
    await f.call('membership', f.token, { activationId: lease.activationId, requestId: 'baseline', characterId: 'human', realm: 'aegis', action: 'join' });
    const earned = character('human', 'aegis', 2);
    (earned.document.inventory as Record<string, unknown>).characterProgression = { level: 13, xp: 1200, gold: 999 };
    const log = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const commit = vi.spyOn(f.repository, 'commit').mockRejectedValue(new Error('disk unavailable'));
    try {
      expect((await f.call('update', f.token, { activationId: lease.activationId, requestId: 'earned', sequence: 1,
        snapshot: snapshot([0], 0), characters: [earned] })).status).toBe(503);
      expect(f.server().inspect().zones.aegis_capital.nativeSiege!.sequence).toBe(0);
      expect(f.server().inspect().nativeSiegeJournal!.characters!['live-aegis:human'].character).toEqual(character('human'));
    } finally { commit.mockRestore(); log.mockRestore(); }
    await f.restart();
    const restored = await f.call('restore', f.token, { requestId: 'restore_baseline', characterId: 'human' });
    expect(restored.data.character).toEqual(character('human'));
    expect(restored.data.revision).toBe(1);
  });
});
