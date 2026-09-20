import { describe, expect, it } from 'vitest';
import { addPlayer, advanceSimulation, createCampaign, defaultZoneConfig, equipmentOperatorPosition, equipmentOperatorSeat, removePlayer, restoreCampaign, submitCommand } from '../src/shared/orvr';
import type { PlayerAction } from '../src/shared/orvr';

function setup() {
  const config = defaultZoneConfig('sunmeadow_march');
  config.collision = []; delete config.terrain; delete config.walkableSurfaces;
  const state = createCampaign({ zones: [config] });
  for (const id of ['a', 'b', 'c']) addPlayer(state, { id, userId: id, characterId: id, realm: 'aegis', zoneId: config.id, avatarProfileKey: 'civic_battle_prelate_m' });
  const zone = state.zones[config.id], keep = zone.config.keeps[0];
  for (const npc of Object.values(zone.npcs)) npc.health = 0;
  zone.keeps[keep.id].supplies = 1000;
  zone.keeps[keep.id].level = 3;
  state.players.a.position = { ...keep.quartermaster };
  const command = (id: string, action: PlayerAction) => submitCommand(state, id, {
    version: 1, sequence: state.players[id].lastSequence + 1, activationId: zone.activationId, action,
  });
  expect(command('a', { type: 'purchase', equipment: 'ram', keepId: keep.id }).ok).toBe(true);
  const machine = Object.values(zone.equipment)[0]; machine.position = { x: 0, y: 0, z: 0 }; machine.facing = 0;
  for (const id of ['a', 'b', 'c']) state.players[id].position = { x: 0, y: 0, z: -2 };
  const board = (id: string) => command(id, { type: 'board', equipmentId: machine.id });
  return { state, zone, machine, command, board };
}

describe('authority-owned ram crew seats', () => {
  it('assigns distinct measured seats and retains physical seats when the first operator leaves', () => {
    const g = setup();
    expect(g.board('a').ok).toBe(true); expect(g.board('b').ok).toBe(true);
    expect(g.state.players.a.position).toEqual({ x: -.71, y: .91, z: .185 });
    expect(g.state.players.b.position).toEqual({ x: .71, y: .91, z: .185 });
    expect(g.board('c').code).toBe('equipment_full');
    expect(g.command('a', { type: 'leaveEquipment' }).ok).toBe(true);
    expect(g.state.players.a.position.y).toBe(0);
    advanceSimulation(g.state, .05);
    expect(equipmentOperatorSeat(g.machine, 'b')).toBe(1);
    expect(g.state.players.b.position.x).toBe(.71);
    expect(g.board('c').ok).toBe(true);
    expect(equipmentOperatorSeat(g.machine, 'c')).toBe(0);
    expect(g.state.players.c.position.x).toBe(-.71);
  });

  it('moves and turns both seats with the authority engine while preventing driver wall traversal', () => {
    const g = setup(); g.board('a'); g.board('b');
    g.command('a', { type: 'move', direction: { x: 1, z: 0 } });
    advanceSimulation(g.state, .1);
    expect(g.machine.position.x).toBeCloseTo(.25); expect(g.machine.facing).toBeCloseTo(Math.PI / 2);
    expect(g.state.players.a.position).toEqual(equipmentOperatorPosition(g.machine, 'a'));
    expect(g.state.players.b.position).toEqual(equipmentOperatorPosition(g.machine, 'b'));
    expect(g.state.players.a.facing.x).toBeCloseTo(0); expect(g.state.players.a.facing.z).toBeCloseTo(-1);
    expect(g.state.players.b.facing.x).toBeCloseTo(0); expect(g.state.players.b.facing.z).toBeCloseTo(1);
    const stopped = g.machine.position.x;
    g.zone.config.collision = [{ minX: stopped + 1.5, maxX: stopped + 2, minZ: -8, maxZ: 8 }];
    g.command('a', { type: 'move', direction: { x: 1, z: 0 } }); advanceSimulation(g.state, .2);
    expect(g.machine.position.x).toBeCloseTo(stopped);
    expect(g.state.players.a.position).toEqual(equipmentOperatorPosition(g.machine, 'a'));
  });

  it('rejects boarding through a wall and grounds occupants when the engine is destroyed', () => {
    const g = setup();
    g.zone.config.collision = [{ minX: -5, maxX: 5, minZ: -.9, maxZ: -.6 }];
    expect(g.board('a').code).toBe('operator_position_blocked'); expect(g.machine.operators).toEqual([]);
    g.zone.config.collision = []; g.board('a'); g.board('b');
    g.machine.health = 0; advanceSimulation(g.state, .05);
    for (const id of ['a', 'b']) { expect(g.state.players[id].equipmentId).toBeNull(); expect(g.state.players[id].position.y).toBe(0); }
  });

  it('checks the whole dismount path and never crosses a wall to a clear endpoint', () => {
    const g = setup(); g.board('a');
    g.zone.config.collision = [{ minX: -1.6, maxX: -1.3, minZ: -20, maxZ: 20 }];
    expect(g.command('a', { type: 'leaveEquipment' }).ok).toBe(true);
    expect(g.state.players.a.position.x).toBeGreaterThan(-1.3);
    expect(g.state.players.a.position.y).toBe(0);
  });

  it('keeps an operator aboard when every ground exit is obstructed, then permits a safe exit', () => {
    const g = setup(); g.board('a'); g.board('b');
    const seated = { ...g.state.players.a.position };
    // A newly introduced obstruction below the footboard leaves the seat clear but every landing blocked.
    g.zone.config.collision = [{ minX: -4, maxX: 4, minZ: -4, maxZ: 4, minY: 0, maxY: .8 }];
    expect(g.command('a', { type: 'leaveEquipment' }).code).toBe('dismount_position_blocked');
    expect(g.state.players.a.position).toEqual(seated);
    expect(g.state.players.a.equipmentId).toBe(g.machine.id);
    expect(g.machine.operators).toEqual(['a', 'b']);
    expect(equipmentOperatorSeat(g.machine, 'a')).toBe(0);
    g.zone.config.collision = [];
    expect(g.command('a', { type: 'leaveEquipment' }).ok).toBe(true);
    expect(g.state.players.a.position.y).toBe(0);
  });

  it('releases disconnected operators without teleporting through obstructed exits', () => {
    const g = setup(); g.board('a');
    const seated = { ...g.state.players.a.position };
    g.zone.config.collision = [{ minX: -4, maxX: 4, minZ: -4, maxZ: 4, minY: 0, maxY: .8 }];
    expect(removePlayer(g.state, 'a').ok).toBe(true);
    expect(g.state.players.a.position).toEqual(seated);
    expect(g.state.players.a.equipmentId).toBeNull();
    expect(g.machine.operators).toEqual([]);
    expect(g.machine.operatorSeats).toEqual({});
  });

  it('repairs partial legacy seats without moving the surviving operator when the other leaves', () => {
    const g = setup(); g.board('a'); g.board('b');
    delete g.machine.operatorSeats;
    expect(g.command('a', { type: 'leaveEquipment' }).ok).toBe(true);
    expect(equipmentOperatorSeat(g.machine, 'b')).toBe(1);
    expect(g.machine.operatorSeats).toEqual({ b: 1 });
    g.machine.operatorSeats = { b: 1, stale: 0 };
    expect(g.board('c').ok).toBe(true);
    expect(g.machine.operatorSeats).toEqual({ b: 1, c: 0 });
    // Invalid or duplicate saved seat assignments cannot index outside the two fitted packs.
    g.machine.operatorSeats = { b: 9 as 0, c: 0 };
    advanceSimulation(g.state, .05);
    expect(g.machine.operatorSeats).toEqual({ b: 1, c: 0 });
    g.machine.operatorSeats = { b: 1, c: 1 };
    advanceSimulation(g.state, .05);
    expect(g.machine.operatorSeats).toEqual({ b: 1, c: 0 });
    g.state.players.b.connected = false;
    advanceSimulation(g.state, .05);
    expect(g.machine.operatorSeats).toEqual({ c: 0 });
    const restored = restoreCampaign(g.state).zones[g.zone.id].equipment[g.machine.id];
    expect(restored.operators).toEqual([]);
    expect(restored.operatorSeats).toBeUndefined();
  });
});
