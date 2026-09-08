import { describe, expect, it } from 'vitest';
import { addPlayer, advanceSimulation, createCampaign, defaultZoneConfig, submitCommand } from '../src/shared/orvr';
import type { AbilityRule, CampaignState, PlayerAction } from '../src/shared/orvr';

function command(state: CampaignState, id: string, action: PlayerAction) {
  return submitCommand(state, id, { version: 1, sequence: state.players[id].lastSequence + 1, activationId: state.zones[state.players[id].zoneId].activationId, action });
}
const abilities: AbilityRule[] = [
  { id: 'burn', cooldownSeconds: 2, range: 20, gcdSeconds: 1.2, impactDelaySeconds: 0.5,
    resource: { manaCost: 10, careerBuild: 12 }, targeting: { target: 'enemy', shape: 'projectile', range: 20 },
    effects: [{ kind: 'damage', amount: { min: 10, max: 10 } }, { kind: 'status', status: { id: 'burn', label: 'Burn', kind: 'burn', durationSec: 3, magnitude: 0.5 } }] },
  { id: 'shield', cooldownSeconds: 2, range: 0, gcdSeconds: 1.2, targeting: { target: 'self', shape: 'self', range: 0 },
    effects: [{ kind: 'player_status', playerStatus: { kind: 'shield', durationSec: 10, magnitude: 0.5 } }] },
  { id: 'cleave', cooldownSeconds: 2, range: 8, targeting: { target: 'enemy', shape: 'cone', range: 8 },
    effects: [{ kind: 'damage', amount: { min: 20, max: 20 } }] },
  { id: 'heal', cooldownSeconds: 2, range: 20, targeting: { target: 'ally', shape: 'beam', range: 20 },
    effects: [{ kind: 'heal', amount: { min: 30, max: 30 } }] },
  { id: 'dash', cooldownSeconds: 2, range: 20, resource: { manaCost: 8 }, targeting: { target: 'enemy', shape: 'dash', range: 20 },
    effects: [{ kind: 'movement', movement: { mode: 'toward_target', distance: 10 } }] },
  { id: 'cleanse', cooldownSeconds: 2, range: 0, targeting: { target: 'self', shape: 'self', range: 0 },
    effects: [{ kind: 'cleanse', cleanse: { kinds: ['root', 'stagger'] } }] },
];
function setup(config = defaultZoneConfig('sunmeadow_march')) {
  const state = createCampaign({ zones: [config], abilities });
  for (const [id, realm] of [['a', 'aegis'], ['a2', 'aegis'], ['b', 'riftbound'], ['b2', 'riftbound']] as const) {
    addPlayer(state, { id, userId: id, characterId: id, realm, zoneId: config.id, abilityIds: abilities.map(a => a.id) });
  }
  for (const npc of Object.values(state.zones[config.id].npcs)) npc.health = 0;
  state.players.a.position = { x: 0, y: 0, z: 80 };
  state.players.a2.position = { x: 1, y: 0, z: 80 };
  state.players.b.position = { x: 5, y: 0, z: 80 };
  state.players.b2.position = { x: -5, y: 0, z: 80 };
  return state;
}

describe('shared class ability effects', () => {
  it('pays server resources, observes impact delay and GCD, and ticks damage-over-time', () => {
    const state = setup();
    expect(command(state, 'a', { type: 'ability', abilityId: 'burn', targetId: 'b' }).ok).toBe(true);
    expect(state.players.a.mana).toBe(90);
    expect(state.players.a.careerResource).toBe(12);
    expect(state.players.b.health).toBe(100);
    expect(command(state, 'a', { type: 'ability', abilityId: 'shield', targetId: 'a' }).code).toBe('global_cooldown');
    advanceSimulation(state, 0.5);
    expect(state.players.b.health).toBe(90);
    expect(state.players.b.statuses[0].kind).toBe('burn');
    advanceSimulation(state, 1);
    expect(state.players.b.health).toBe(84);
    advanceSimulation(state, 2);
    expect(state.players.b.health).toBe(72);
    expect(state.players.b.statuses).toHaveLength(0);
  });

  it('selects hostile cone targets by facing, allows allied healing, and absorbs damage with shields', () => {
    const state = setup();
    expect(command(state, 'b', { type: 'ability', abilityId: 'shield', targetId: 'b' }).ok).toBe(true);
    expect(command(state, 'a', { type: 'ability', abilityId: 'cleave', targetId: 'b' }).ok).toBe(true);
    advanceSimulation(state, 0.05);
    expect(state.players.b.health).toBe(100);
    expect(state.players.b.statuses[0].shieldRemaining).toBe(30);
    expect(state.players.b2.health).toBe(100);
    expect(state.players.a2.health).toBe(100);
    state.players.a2.health = 20;
    expect(command(state, 'a', { type: 'ability', abilityId: 'heal', targetId: 'a2' }).ok).toBe(true);
    advanceSimulation(state, 0.05);
    expect(state.players.a2.health).toBe(50);
  });

  it('rejects collision-crossing movement before payment and allows a cleanse while rooted', () => {
    const config = defaultZoneConfig('sunmeadow_march');
    config.collision = [{ minX: 2, maxX: 3, minZ: 70, maxZ: 90 }];
    const state = setup(config);
    expect(command(state, 'a', { type: 'ability', abilityId: 'dash', targetId: 'b' }).code).toBe('movement_blocked');
    expect(state.players.a.mana).toBe(100);
    expect(state.players.a.cooldowns.dash).toBeUndefined();
    state.players.a.statuses.push({ id: 'root', kind: 'root', expiresAt: 100, magnitude: 0, sourceId: 'b' });
    expect(command(state, 'a', { type: 'ability', abilityId: 'dash', targetId: 'b' }).code).toBe('controlled_player');
    expect(command(state, 'a', { type: 'ability', abilityId: 'cleanse', targetId: 'a' }).ok).toBe(true);
    expect(state.players.a.statuses).toHaveLength(0);
  });

  it('grounds authoritative movement on the same controlled terrain surface as the renderer', () => {
    const config = defaultZoneConfig('sunmeadow_march');
    config.terrain = { sourceVersion: 'test', landforms: [], clearCorridors: [], flattenAreas: [{ id: 'highground', x: 0, z: 80, radius: 100, height: 15, feather: 10 }] };
    config.terrainSize = 1200; config.terrainSegments = 128;
    const state = setup(config);
    command(state, 'a', { type: 'move', direction: { x: 1, z: 0 } });
    advanceSimulation(state, 0.1);
    expect(state.players.a.position.y).toBeCloseTo(15);
  });
});
