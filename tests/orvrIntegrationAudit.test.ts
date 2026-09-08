import { afterEach, describe, expect, it, vi } from 'vitest';
import { access, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { SupabaseClient } from '@supabase/supabase-js';
import { SupabaseAuthenticator, DevelopmentAuthenticator } from '../server/auth';
import { campaignAbilityRules, recruitCombatProfile } from '../server/abilityCatalog';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { startAuthority } from '../server/authority';
import { FileCampaignRepository } from '../server/persistence';
import { addPlayer, advanceSimulation, createCampaign, submitCommand } from '../src/shared/orvr';
import { orvrGridHeightAt } from '../src/shared/orvrTerrain';
import { CAREER_ABILITY_KITS } from '../src/game/abilities/abilityData';
import type { CampaignState, Position, Realm } from '../src/shared/orvr';

afterEach(() => { vi.unstubAllGlobals(); });

describe('authoritative authentication integration', () => {
  it('uses Auth-verified ownership and fixed recruit profiles rather than editable metadata', async () => {
    const userId = '10000000-0000-4000-8000-000000000001';
    const characterId = '20000000-0000-4000-8000-000000000002';
    const fetch = vi.fn(async () => new Response(JSON.stringify({ id: userId, aud: 'authenticated',
      user_metadata: { realm: 'riftbound', ability_ids: ['admin'], strength: 100000 } }), { status: 200 }));
    vi.stubGlobal('fetch', fetch);
    let row = { id: characterId, user_id: userId, name: 'Lysa', realm: 'aegis', ability_ids: ['admin'] };
    const query = { select: vi.fn(), eq: vi.fn(), single: vi.fn(async () => ({ data: row, error: null })) };
    query.select.mockReturnValue(query); query.eq.mockReturnValue(query);
    const repository = { from: vi.fn(() => query) } as unknown as SupabaseClient;
    const auth = new SupabaseAuthenticator('https://example.supabase.co', 'publishable-test-key', repository);
    const identity = await auth.verify('server-validated-token', characterId);
    expect(identity.realm).toBe('aegis');
    expect(identity.abilityIds).toEqual(recruitCombatProfile('aegis').abilityIds);
    expect(identity.combatProfile?.strength).toBe(10);
    expect(query.eq).toHaveBeenCalledWith('id', characterId);
    expect(query.eq).toHaveBeenCalledWith('user_id', userId);
    row = { ...row, user_id: 'another-user' };
    await expect(auth.verify('server-validated-token', characterId)).rejects.toThrow('Character access denied');
  });

  it('rejects Auth failures before querying any character', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ message: 'Token expired' }), { status: 401 })));
    const from = vi.fn();
    const auth = new SupabaseAuthenticator('https://example.supabase.co', 'publishable-test-key', { from } as unknown as SupabaseClient);
    await expect(auth.verify('expired-token', 'character')).rejects.toThrow('invalid or expired');
    expect(from).not.toHaveBeenCalled();
  });

  it('retains canonical ability impact timing', () => {
    const rules = campaignAbilityRules();
    for (const ability of Object.values(CAREER_ABILITY_KITS).flatMap(kit => kit.abilities)) {
      const release = ability.animation.notifyWindows.find(window => window.name === 'release')
        ?? ability.animation.notifyWindows.find(window => window.name === 'active') ?? ability.animation.notifyWindows[0];
      const expected = ability.animation.contactSec ?? ability.animation.durationSec * (release ? (release.start + release.end) / 2 : .35);
      expect(rules.find(rule => rule.id === ability.id)?.impactDelaySeconds).toBe(expected);
    }
  });

  it('releases the file lease when a version-valid but corrupted checkpoint cannot be restored', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'war-orvr-corrupt-'));
    const filename = join(directory, 'campaign.json');
    const repository = new FileCampaignRepository(filename);
    try {
      await writeFile(filename, JSON.stringify({ revision: 1, state: { version: 1, id: 'corrupt' } }));
      await expect(startAuthority({ port: 0, auth: new DevelopmentAuthenticator(), repository, automaticTicks: false })).rejects.toThrow('Invalid campaign save');
      await expect(access(`${filename}.lock`)).rejects.toMatchObject({ code: 'ENOENT' });
    } finally { await repository.close(); await rm(directory, { recursive: true, force: true }); }
  });
});

function move(state: CampaignState, id: string, direction: { x: number; z: number }, dt: number) {
  const player = state.players[id];
  const result = submitCommand(state, id, { version: 1, sequence: player.lastSequence + 1,
    activationId: state.zones[player.zoneId].activationId, action: { type: 'move', direction } });
  expect(result.ok).toBe(true);
  return advanceSimulation(state, dt);
}
function flatDistance(a: Position, b: Position) { return Math.hypot(a.x - b.x, a.z - b.z); }

describe('generated campaign navigation and supply routes', () => {
  it('escorts all six real routes in both opening zones and delivers each shipment exactly once', async () => {
    const configs = await loadCampaignMapConfigs();
    for (const zoneId of ['sunmeadow_march', 'ashen_steppe']) for (const realm of ['aegis', 'riftbound'] as Realm[]) {
      for (let objectiveIndex = 0; objectiveIndex < 3; objectiveIndex += 1) {
        const state = createCampaign({ zones: configs });
        addPlayer(state, { id: 'escort', userId: 'escort', characterId: 'escort', realm, zoneId });
        const player = state.players.escort;
        const zone = state.zones[zoneId];
        for (const npc of Object.values(zone.npcs)) npc.health = 0;
        const config = zone.config.objectives[objectiveIndex];
        const objective = zone.objectives[config.id];
        objective.owner = realm; objective.readyShipment = true;
        const route = config.routes![realm]!;
        player.position = { ...route[0] };
        const dispatch = submitCommand(state, player.id, { version: 1, sequence: 1, activationId: zone.activationId,
          action: { type: 'dispatch', objectiveId: objective.id } });
        expect(dispatch.ok, `${zoneId} ${realm} ${objective.id}: ${dispatch.code}`).toBe(true);
        const caravan = Object.values(zone.caravans)[0];
        let deliveries = 0;
        for (let steps = 0; steps < 4_000 && caravan.status !== 'delivered'; steps += 1) {
          const waypoint = route[Math.min(caravan.routeIndex, route.length - 1)];
          const d = flatDistance(player.position, waypoint);
          const speed = 3.5 / 6;
          const direction = d < .02 ? { x: 0, z: 0 } : { x: (waypoint.x - player.position.x) / d * speed, z: (waypoint.z - player.position.z) / d * speed };
          const events = move(state, player.id, direction, .1);
          deliveries += events.filter(event => event.type === 'supplies_delivered').length;
          expect(flatDistance(player.position, caravan.position), `${zoneId}: escort blocked at ${JSON.stringify(player.position)}`).toBeLessThan(5);
          expect(player.position.y).toBeCloseTo(orvrGridHeightAt(zone.config.terrain!, zone.config.terrainSize!, zone.config.terrainSegments!, player.position.x, player.position.z));
        }
        expect(caravan.status, `${zoneId} ${realm} ${objective.id}`).toBe('delivered');
        expect(deliveries).toBe(1);
        expect(zone.influence[realm]).toBe(100);
        expect(Object.values(zone.keeps).find(keep => keep.owner === realm)!.supplies).toBe(100);
      }
    }
  }, 15_000);

  it('blocks actual keep gates until breached and preserves permanent rear-door collision', async () => {
    const configs = await loadCampaignMapConfigs();
    const state = createCampaign({ zones: configs });
    addPlayer(state, { id: 'a', userId: 'a', characterId: 'a', realm: 'aegis', zoneId: 'sunmeadow_march' });
    const zone = state.zones.sunmeadow_march;
    for (const npc of Object.values(zone.npcs)) npc.health = 0;
    const config = zone.config.keeps.find(keep => keep.realm === 'riftbound')!;
    const keep = zone.keeps[config.id];
    const gate = config.outerGate;
    state.players.a.position = { ...gate, z: gate.z - 4 };
    for (let i = 0; i < 20; i += 1) move(state, 'a', { x: 0, z: 1 }, .1);
    expect(state.players.a.position.z).toBeLessThan(gate.z);
    keep.gates.outer.health = 0;
    for (let i = 0; i < 15; i += 1) move(state, 'a', { x: 0, z: 1 }, .1);
    expect(state.players.a.position.z).toBeGreaterThan(gate.z + 2);
    expect(zone.config.collision!.some(box => box.minX <= config.position.x && box.maxX >= config.position.x && box.minZ > config.innerGate.z)).toBe(true);
  });
});
