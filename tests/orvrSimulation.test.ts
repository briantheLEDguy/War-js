import { describe, expect, it } from 'vitest';
import {
  addPlayer, advanceSimulation, createCampaign, defaultZoneConfig, ORVR_RULES,
  removePlayer, restoreCampaign, snapshotFor, submitCommand,
} from '../src/shared/orvr';
import type { CampaignState, PlayerAction, Realm, ZoneState } from '../src/shared/orvr';

function add(state: CampaignState, id = 'a', realm: Realm = 'aegis', zoneId = 'sunmeadow_march') {
  expect(addPlayer(state, { id, userId: `user-${id}`, characterId: `char-${id}`, realm, zoneId }).ok).toBe(true);
  return state.players[id];
}
function command(state: CampaignState, playerId: string, action: PlayerAction) {
  const player = state.players[playerId];
  return submitCommand(state, playerId, {
    version: 1, sequence: player.lastSequence + 1, activationId: state.zones[player.zoneId].activationId, action,
  });
}
function emptyGuards(zone: ZoneState) {
  for (const npc of Object.values(zone.npcs)) npc.health = 0;
}
function captureObjective(state: CampaignState, playerId = 'a', index = 1) {
  const player = state.players[playerId];
  const zone = state.zones[player.zoneId];
  emptyGuards(zone);
  player.position = { ...zone.config.objectives[index].position };
  const events = advanceSimulation(state, 30);
  expect(events.some(e => e.type === 'objective_captured')).toBe(true);
  return zone.objectives[zone.config.objectives[index].id];
}
function awardZone(state: CampaignState, zoneId: string, realm: Realm, playerId: string) {
  const zone = state.zones[zoneId];
  const player = state.players[playerId] ?? add(state, playerId, realm, zoneId);
  player.zoneId = zoneId;
  player.health = player.maxHealth;
  player.queued = false;
  if (zone.status === 'staging') {
    player.position = { ...zone.config.staging[realm] };
    advanceSimulation(state, zone.stagingRemaining);
  }
  const target = Object.values(zone.keeps).find(k => k.owner !== realm)!;
  expect(target).toBeDefined();
  target.gates.outer.health = 0;
  target.gates.inner.health = 0;
  zone.npcs[target.commanderId].health = 0;
  player.position = { ...zone.config.keeps.find(k => k.id === target.id)!.position };
  for (const p of Object.values(state.players)) if (p.realm !== realm && p.zoneId === zoneId) p.position = { ...zone.config.staging[p.realm] };
  const events = advanceSimulation(state, 30);
  expect(events.some(e => e.type === 'zone_won')).toBe(true);
  return events;
}

describe('authoritative ORvR capture and movement', () => {
  it('starts two opposing fronts, with neutral objectives and one keep per realm', () => {
    const state = createCampaign();
    expect(Object.values(state.zones).filter(z => z.status === 'active').map(z => z.id).sort()).toEqual(['ashen_steppe', 'sunmeadow_march']);
    const zone = state.zones.sunmeadow_march;
    expect(Object.values(zone.objectives).map(o => o.owner)).toEqual([null, null, null]);
    expect(Object.values(zone.keeps).map(k => k.owner)).toEqual(['aegis', 'riftbound']);
    expect(zone.config.bounds.maxX - zone.config.bounds.minX).toBe(1200);
  });

  it('requires guards defeated and thirty uncontested seconds; opposing presence resets progress', () => {
    const state = createCampaign();
    const a = add(state);
    const b = add(state, 'b', 'riftbound');
    const zone = state.zones[a.zoneId];
    const config = zone.config.objectives[1];
    const objective = zone.objectives[config.id];
    a.position = { ...config.position };
    advanceSimulation(state, 5);
    expect(objective.captureSeconds).toBe(0);
    emptyGuards(zone);
    advanceSimulation(state, 20);
    expect(objective.captureSeconds).toBeCloseTo(20);
    b.position = { ...config.position };
    advanceSimulation(state, 0.05);
    expect(objective.captureSeconds).toBe(0);
    b.position = { ...zone.config.staging.riftbound };
    advanceSimulation(state, 29.95);
    expect(objective.owner).toBeNull();
    advanceSimulation(state, 0.05);
    expect(objective.owner).toBe('aegis');
    expect(objective.productionSeconds).toBe(0);
    expect(zone.influence.aegis).toBe(0);
  });

  it('caps diagonal movement, expires old inputs, blocks collision, and rejects stale or malformed commands', () => {
    const config = defaultZoneConfig('sunmeadow_march');
    config.collision = [{ minX: 1, maxX: 3, minZ: -10, maxZ: 10 }];
    const state = createCampaign({ zones: [config] });
    const player = add(state);
    emptyGuards(state.zones[player.zoneId]);
    player.position = { x: 0, y: 0, z: 50 };
    expect(command(state, 'a', { type: 'move', direction: { x: 100, z: 100 } }).ok).toBe(true);
    advanceSimulation(state, 0.1);
    expect(Math.hypot(player.position.x, player.position.z - 50)).toBeCloseTo(0.6);
    advanceSimulation(state, 10);
    expect(Math.hypot(player.position.x, player.position.z - 50)).toBeLessThanOrEqual(2.11);
    player.position = { x: 0, y: 0, z: 0 };
    command(state, 'a', { type: 'move', direction: { x: 1, z: 0 } });
    advanceSimulation(state, 0.3);
    expect(player.position.x).toBeLessThan(0.5);
    expect(command(state, 'a', { type: 'move', direction: { x: Number.NaN, z: 0 } }).code).toBe('invalid_direction');
    expect(submitCommand(state, 'a', { version: 1, sequence: 999, activationId: 'old', action: { type: 'attack', targetId: 'nope' } }).code).toBe('stale_activation');
    expect(command(state, 'a', { type: 'attack', targetId: '__proto__' }).code).toBe('invalid_command');
    expect(addPlayer(state, { id: 'evil', userId: 'evil', characterId: 'evil', realm: 'aegis', zoneId: 'toString' }).code).toBe('invalid_zone');
    expect(submitCommand(state, 'a', { version: 1, sequence: player.lastSequence, activationId: state.zones[player.zoneId].activationId, action: { type: 'leaveEquipment' } }).code).toBe('stale_sequence');
  });

  it('preserves remaining cooldown durations across zones with different clocks', () => {
    const state = createCampaign();
    const player = add(state);
    advanceSimulation(state, 100);
    player.cooldowns.basic_attack = 103;
    expect(command(state, 'a', { type: 'transfer', zoneId: 'ashen_steppe' }).ok).toBe(true);
    expect(player.cooldowns.basic_attack).toBeCloseTo(3);
  });
});

describe('caravans, supply accounting, and persistence', () => {
  it('produces one ready shipment, pauses under hostile presence, and never produces unattended supplies', () => {
    const state = createCampaign();
    const a = add(state);
    const b = add(state, 'b', 'riftbound');
    const zone = state.zones[a.zoneId];
    const objective = captureObjective(state);
    a.position = { ...zone.config.staging.aegis };
    advanceSimulation(state, 100);
    b.position = { ...zone.config.objectives[1].position };
    advanceSimulation(state, 1);
    expect(objective.productionSeconds).toBeCloseTo(100);
    b.position = { ...zone.config.staging.riftbound };
    advanceSimulation(state, 80);
    expect(objective.readyShipment).toBe(true);
    advanceSimulation(state, 500);
    expect(objective.readyShipment).toBe(true);
    expect(Object.keys(zone.caravans)).toHaveLength(0);
    expect(zone.influence.aegis).toBe(0);
    removePlayer(state, 'a'); removePlayer(state, 'b');
    const seconds = zone.seconds;
    advanceSimulation(state, 100);
    expect(zone.seconds).toBe(seconds);
  });

  it('delivers only with a connected escort and credits capped stock but full development/influence exactly once', () => {
    const config = defaultZoneConfig('sunmeadow_march');
    const position = config.objectives[1].position;
    config.keeps[0].quartermaster = { ...position, x: 10 };
    config.objectives[1].routes!.aegis = [{ ...position }, { ...position, x: 10 }];
    const state = createCampaign({ zones: [config] });
    const a = add(state);
    const zone = state.zones[a.zoneId];
    const objective = captureObjective(state);
    advanceSimulation(state, 180);
    const keep = Object.values(zone.keeps).find(k => k.owner === 'aegis')!;
    keep.supplies = 950; keep.deliveredSupplies = 200;
    const result = command(state, 'a', { type: 'dispatch', objectiveId: objective.id });
    expect(result.ok).toBe(true);
    expect(command(state, 'a', { type: 'dispatch', objectiveId: objective.id }).code).toBe('shipment_unavailable');
    const events = advanceSimulation(state, 3);
    expect(events.filter(e => e.type === 'supplies_delivered')).toHaveLength(1);
    expect(keep.supplies).toBe(1000);
    expect(keep.deliveredSupplies).toBe(300);
    expect(keep.level).toBe(2);
    expect(zone.influence.aegis).toBe(100);
    expect(state.contributions['sunmeadow_march:aegis']).toBe(100);
    advanceSimulation(state, 10);
    expect(zone.influence.aegis).toBe(100);
    const restored = restoreCampaign(JSON.parse(JSON.stringify(state)));
    expect(restored.players.a.connected).toBe(false);
    addPlayer(restored, { id: 'a', userId: 'user-a', characterId: 'char-a', realm: 'aegis' });
    advanceSimulation(restored, 1);
    expect(restored.zones.sunmeadow_march.influence.aegis).toBe(100);
  });

  it('destroys abandoned cargo without granting attackers stock or influence', () => {
    const state = createCampaign();
    const player = add(state);
    const zone = state.zones[player.zoneId];
    const objective = captureObjective(state);
    advanceSimulation(state, 180);
    expect(command(state, 'a', { type: 'dispatch', objectiveId: objective.id }).ok).toBe(true);
    const caravan = Object.values(zone.caravans)[0];
    player.position = { ...zone.config.staging.aegis };
    advanceSimulation(state, 239.95);
    expect(caravan.status).toBe('waiting');
    advanceSimulation(state, 0.05);
    expect(caravan.status).toBe('destroyed');
    expect(objective.caravanId).toBeNull();
    expect(zone.influence).toEqual({ aegis: 0, riftbound: 0 });
  });
});

describe('equipment, combat, and population limits', () => {
  it('enforces levels, paid slot limits, operator count, gates, and ram replacement cooldown', () => {
    const state = createCampaign();
    const a = add(state);
    const a2 = add(state, 'a2');
    const zone = state.zones[a.zoneId];
    const config = zone.config.keeps[0];
    const keep = zone.keeps[config.id];
    keep.supplies = 1000;
    a.position = { ...config.quartermaster };
    expect(command(state, 'a', { type: 'purchase', keepId: keep.id, equipment: 'ram' }).code).toBe('keep_level_required');
    keep.level = 2;
    expect(command(state, 'a', { type: 'purchase', keepId: keep.id, equipment: 'ram' }).ok).toBe(true);
    expect(keep.supplies).toBe(900);
    expect(command(state, 'a', { type: 'purchase', keepId: keep.id, equipment: 'ram' }).code).toBe('equipment_capacity');
    const ram = Object.values(zone.equipment)[0];
    a.position = { ...ram.position };
    expect(command(state, 'a', { type: 'board', equipmentId: ram.id }).ok).toBe(true);
    const enemy = zone.keeps[zone.config.keeps[1].id];
    ram.position = { ...zone.config.keeps[1].outerGate, x: 305 };
    expect(command(state, 'a', { type: 'operate', equipmentId: ram.id, targetId: enemy.gates.outer.id }).code).toBe('two_operators_required');
    a2.position = { ...ram.position };
    expect(command(state, 'a2', { type: 'board', equipmentId: ram.id }).ok).toBe(true);
    expect(command(state, 'a', { type: 'operate', equipmentId: ram.id, targetId: enemy.gates.inner.id }).code).toBe('outer_gate_required');
    expect(command(state, 'a', { type: 'operate', equipmentId: ram.id, targetId: enemy.gates.outer.id }).ok).toBe(true);
    expect(enemy.gates.outer.health).toBe(900);
    expect(command(state, 'a2', { type: 'operate', equipmentId: ram.id, targetId: enemy.gates.outer.id }).code).toBe('equipment_cooldown');
    command(state, 'a', { type: 'leaveEquipment' }); command(state, 'a2', { type: 'leaveEquipment' });
    advanceSimulation(state, 240);
    expect(ram.health).toBe(0);
    a.position = { ...config.quartermaster };
    expect(command(state, 'a', { type: 'purchase', keepId: keep.id, equipment: 'ram' }).code).toBe('ram_replacement_cooldown');
    advanceSimulation(state, 180);
    expect(command(state, 'a', { type: 'purchase', keepId: keep.id, equipment: 'ram' }).ok).toBe(true);
  });

  it('repairs after a quiet period and a ten-second channel, charging once at completion', () => {
    const state = createCampaign();
    const a = add(state);
    const zone = state.zones[a.zoneId];
    const config = zone.config.keeps[0];
    const keep = zone.keeps[config.id];
    keep.supplies = 50; keep.gates.outer.health = 500; keep.gates.outer.lastDamagedAt = 0;
    a.position = { ...config.outerGate };
    expect(command(state, 'a', { type: 'repair', keepId: keep.id, gate: 'outer' }).code).toBe('gate_under_attack');
    advanceSimulation(state, 30);
    expect(command(state, 'a', { type: 'repair', keepId: keep.id, gate: 'outer' }).ok).toBe(true);
    advanceSimulation(state, 9.95);
    expect(keep.supplies).toBe(50);
    advanceSimulation(state, 0.05);
    expect(keep.supplies).toBe(25);
    expect(keep.gates.outer.health).toBe(600);
    expect(command(state, 'a', { type: 'repair', keepId: keep.id, gate: 'outer' }).ok).toBe(true);
    command(state, 'a', { type: 'move', direction: { x: -1, z: 0 } });
    advanceSimulation(state, 11);
    expect(keep.supplies).toBe(25);
  });

  it('authorizes hostile damage and allied healing, then respawns defeated players after fifteen seconds', () => {
    const state = createCampaign({ abilities: [{ id: 'strike', damage: 100, range: 10, cooldownSeconds: 1 }, { id: 'heal', healing: 30, range: 10, cooldownSeconds: 2 }] });
    const a = add(state);
    const a2 = add(state, 'a2');
    const b = add(state, 'b', 'riftbound');
    a.abilityIds = ['strike', 'heal'];
    a.position = { x: 0, y: 0, z: 80 }; a2.position = { ...a.position }; b.position = { ...a.position };
    expect(command(state, 'a', { type: 'ability', abilityId: 'strike', targetId: 'a2' }).code).toBe('invalid_target');
    a2.health = 30;
    expect(command(state, 'a', { type: 'ability', abilityId: 'heal', targetId: 'a2' }).ok).toBe(true);
    expect(a2.health).toBe(60);
    expect(command(state, 'a', { type: 'ability', abilityId: 'strike', targetId: 'b' }).ok).toBe(true);
    expect(b.health).toBe(0);
    advanceSimulation(state, 14.95);
    expect(b.health).toBe(0);
    advanceSimulation(state, 0.05);
    expect(b.health).toBe(100);
    expect(b.position).toEqual(state.zones[b.zoneId].config.staging.riftbound);
  });

  it('queues by realm beyond eighteen players and admits the next player on disconnect', () => {
    const state = createCampaign();
    for (let i = 0; i < 20; i += 1) add(state, `a${i}`);
    for (let i = 0; i < 18; i += 1) add(state, `b${i}`, 'riftbound');
    expect(state.players.a17.queued).toBe(false);
    expect(state.players.a18.queued).toBe(true);
    expect(snapshotFor(state, 'a19').queuePosition).toBe(2);
    removePlayer(state, 'a0');
    expect(state.players.a18.queued).toBe(false);
    expect(snapshotFor(state, 'a19').queuePosition).toBe(1);
    expect(command(state, 'a19', { type: 'attack', targetId: 'b0' }).code).toBe('queued');
    const players = snapshotFor(state, 'a1').players;
    expect(players.every(p => !('userId' in p) && !('characterId' in p) && !('cooldowns' in p) && !('mana' in p))).toBe(true);
    expect(addPlayer(state, { id: 'different', userId: 'user-a1', characterId: 'char-other', realm: 'aegis' }).code).toBe('identity_in_use');
  });
});

describe('front movement and city outcomes', () => {
  it('resolves competing keep completions to one committed zone winner', () => {
    const state = createCampaign();
    const a = add(state); const b = add(state, 'b', 'riftbound');
    const zone = state.zones.sunmeadow_march;
    for (const keep of Object.values(zone.keeps)) {
      keep.gates.outer.health = 0; keep.gates.inner.health = 0;
      zone.npcs[keep.commanderId].health = 0;
    }
    a.position = { ...zone.config.keeps[1].position };
    b.position = { ...zone.config.keeps[0].position };
    const events = advanceSimulation(state, 30);
    expect(events.filter(event => event.type === 'zone_won')).toHaveLength(1);
    expect(events.filter(event => event.type === 'front_advanced')).toHaveLength(1);
    expect(zone.status).toBe('secured');
  });
  it('advances, stages for three minutes, and resets a reopened front without deleting history', () => {
    const state = createCampaign();
    add(state); add(state, 'b', 'riftbound');
    const sun = state.zones.sunmeadow_march;
    const oldActivation = sun.activationId;
    sun.influence.aegis = 400;
    state.contributions['sunmeadow_march:aegis'] = 400;
    Object.values(sun.keeps)[0].level = 3;
    awardZone(state, sun.id, 'aegis', 'a');
    const next = state.zones.cinderfen_outskirts;
    expect(next.status).toBe('staging');
    expect(next.stagingRemaining).toBe(180);
    awardZone(state, next.id, 'riftbound', 'b');
    expect(sun.status).toBe('staging');
    expect(sun.activationId).not.toBe(oldActivation);
    expect(sun.victor).toBe('aegis');
    expect(sun.influence.aegis).toBe(0);
    expect(Object.values(sun.keeps).map(k => k.level)).toEqual([1, 1]);
    expect(state.contributions['sunmeadow_march:aegis']).toBe(400);
  });

  it('commits one breakthrough, requires central territory, and supports city attacker victory then campaign reset', () => {
    const state = createCampaign();
    add(state);
    for (const id of ['sunmeadow_march', 'cinderfen_outskirts', 'bleakroot_causeway', 'vilemere_heights']) awardZone(state, id, 'aegis', 'a');
    expect(state.phase).toBe('central');
    expect(state.tracks.west.locked).toBe(true);
    expect(state.tracks.east.locked).toBe(true);
    expect(state.zones.ashen_steppe.status).toBe('inactive');
    for (const id of ['shatterline_expanse', 'rift_crownworks', 'rift_gate_fortress']) awardZone(state, id, 'aegis', 'a');
    expect(state.phase).toBe('city');
    const city = state.zones.riftspire_capital;
    state.players.a.zoneId = city.id;
    state.players.a.position = { ...city.config.staging.aegis };
    advanceSimulation(state, 180);
    emptyGuards(city);
    const final = city.config.objectives[2];
    state.players.a.position = { ...final.position };
    advanceSimulation(state, 30);
    expect(city.objectives[final.id].owner).toBe('riftbound');
    for (let i = 0; i < 3; i += 1) {
      emptyGuards(city);
      state.players.a.position = { ...city.config.objectives[i].position };
      advanceSimulation(state, 30);
    }
    expect(state.phase).toBe('recovery');
    expect(state.results).toEqual([{ round: 1, winner: 'aegis', cityId: 'riftspire_capital', reason: 'city_captured' }]);
    advanceSimulation(state, 300);
    expect(state.round).toBe(2);
    expect(state.phase).toBe('pairings');
    expect(state.results).toHaveLength(1);
  });

  it('supports the opposite breakthrough and defender timeout, pausing an empty city', () => {
    const state = createCampaign();
    add(state, 'b', 'riftbound');
    for (const id of ['sunmeadow_march', 'greybrook_crossing', 'ironwood_redoubt', 'dawnline_expanse', 'aegis_crownworks', 'aegis_gate_fortress']) awardZone(state, id, 'riftbound', 'b');
    const city = state.zones.aegis_capital;
    expect(state.phase).toBe('city');
    advanceSimulation(state, 100);
    expect(city.stagingRemaining).toBe(180);
    state.players.b.zoneId = city.id;
    state.players.b.position = { ...city.config.staging.riftbound };
    advanceSimulation(state, 180);
    expect(city.cityRemaining).toBe(ORVR_RULES.citySeconds);
    removePlayer(state, 'b');
    advanceSimulation(state, 100);
    expect(city.cityRemaining).toBe(ORVR_RULES.citySeconds);
    addPlayer(state, { id: 'b', userId: 'user-b', characterId: 'char-b', realm: 'riftbound', zoneId: city.id });
    advanceSimulation(state, 1800);
    expect(state.results[0]).toMatchObject({ winner: 'aegis', reason: 'city_defended' });
  });
});
