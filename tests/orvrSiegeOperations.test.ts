import { describe, expect, it } from 'vitest';
import { addPlayer, createCampaign, restoreCampaign, snapshotFor, submitCommand } from '../src/shared/orvr';
import type { PlayerAction } from '../src/shared/orvr';

describe('authoritative siege presentation state', () => {
  it.each(['ram', 'oil', 'catapult'] as const)('records only accepted %s operations and retains their immutable target through recovery', kind => {
    const state = createCampaign();
    for (const [id, realm] of [['a', 'aegis'], ['a2', 'aegis'], ['b', 'riftbound']] as const) {
      expect(addPlayer(state, { id, userId: id, characterId: id, realm, zoneId: 'sunmeadow_march' }).ok).toBe(true);
    }
    const zone = state.zones.sunmeadow_march, player = state.players.a, keep = zone.config.keeps[0];
    const command = (id: string, action: PlayerAction) => submitCommand(state, id, {
      version: 1, sequence: state.players[id].lastSequence + 1, activationId: zone.activationId, action,
    });
    zone.seconds = 25;
    zone.keeps[keep.id].level = 3; zone.keeps[keep.id].supplies = 1000;
    player.position = { ...keep.quartermaster };
    expect(command('a', { type: 'purchase', keepId: keep.id, equipment: kind }).ok).toBe(true);
    const machine = Object.values(zone.equipment)[0];
    expect(machine.lastOperation).toBeUndefined();
    if (kind === 'ram') {
      const enemy = zone.config.keeps[1], dx = enemy.outerGate.x - enemy.position.x, dz = enemy.outerGate.z - enemy.position.z;
      const length = Math.hypot(dx, dz);
      machine.position = { ...enemy.outerGate, x: enemy.outerGate.x + dx / length * 8, z: enemy.outerGate.z + dz / length * 8 };
    }
    player.position = { ...(machine.operatorPosition ?? machine.position) };
    expect(command('a', { type: 'board', equipmentId: machine.id }).ok).toBe(true);
    state.players.a2.position = { ...player.position };
    if (kind === 'ram') expect(command('a2', { type: 'board', equipmentId: machine.id }).ok).toBe(true);
    expect(command('a', { type: 'operate', equipmentId: machine.id, targetId: 'missing' }).ok).toBe(false);
    expect(machine.lastOperation).toBeUndefined();
    state.players.b.position = { ...machine.position, x: machine.position.x + 5 };
    const targetId = kind === 'ram' ? zone.keeps[zone.config.keeps[1].id].gates.outer.id : 'b';
    const target = { ...(kind === 'ram' ? zone.config.keeps[1].outerGate : state.players.b.position) };
    const result = command('a', { type: 'operate', equipmentId: machine.id, targetId });
    expect(result.ok).toBe(true);
    expect(result.events.filter(event => event.type === 'equipment_operated')).toHaveLength(1);
    expect(machine.lastOperation).toEqual({ at: 25, target });
    state.players.b.position.x += 50;
    expect(machine.lastOperation?.target).toEqual(target);
    zone.seconds = 25.2;
    const rejected = command('a', { type: 'operate', equipmentId: machine.id, targetId });
    expect(rejected.code).toBe('equipment_cooldown');
    expect(rejected.events).toHaveLength(0);
    expect(machine.lastOperation?.at).toBe(25);
    expect(snapshotFor(state, 'a').zone?.equipment[machine.id].lastOperation).toEqual(machine.lastOperation);
    expect(restoreCampaign(state).zones[zone.id].equipment[machine.id].lastOperation).toEqual(machine.lastOperation);
    delete machine.lastOperation;
    expect(() => restoreCampaign(state)).not.toThrow();
  });
});
