import { expect, test } from 'vitest';
import { addPlayer, advanceSimulation, createCampaign, defaultZoneConfig, equipmentOperatorPosition, submitCommand } from '../src/shared/orvr';
import type { PlayerAction } from '../src/shared/orvr';

function setup() {
  const config = defaultZoneConfig('sunmeadow_march'), keepConfig = config.keeps[0];
  keepConfig.siegePositions!.oil = [{ x: -350, y: 7.5, z: -22 }];
  keepConfig.siegeOperatorPositions = { oil: [{ x: -342, y: 0, z: -16.5 }] };
  const state = createCampaign({ zones: [config] });
  addPlayer(state, { id: 'defender', userId: 'user', characterId: 'character', realm: 'aegis', zoneId: config.id });
  const zone = state.zones[config.id], player = state.players.defender, keep = zone.keeps[keepConfig.id];
  for (const npc of Object.values(zone.npcs)) npc.health = 0;
  keep.supplies = 500;
  player.position = { ...keepConfig.quartermaster };
  const command = (action: PlayerAction) => submitCommand(state, player.id, { version: 1, sequence: player.lastSequence + 1, activationId: zone.activationId, action });
  expect(command({ type: 'purchase', keepId: keep.id, equipment: 'oil' }).ok).toBe(true);
  const machine = Object.values(zone.equipment)[0];
  return { state, zone, player, machine, command };
}

test('raised oil has a copied fixed ground operator position through boarding, movement ticks and dismount', () => {
  const { state, zone, player, machine, command } = setup();
  const anchor = zone.config.keeps[0].siegeOperatorPositions!.oil![0];
  expect(machine.operatorPosition).toEqual(anchor); expect(machine.operatorPosition).not.toBe(anchor);
  player.position = { ...anchor };
  expect(command({ type: 'board', equipmentId: machine.id, operatorPosition: { x: 200, y: 100, z: 200 } } as PlayerAction).ok).toBe(true);
  expect(player.position).toEqual(anchor); expect(machine.position.y).toBe(7.5);
  command({ type: 'move', direction: { x: 1, z: 1 } }); advanceSimulation(state, .3);
  expect(player.position).toEqual(anchor); expect(machine.position).toEqual({ x: -350, y: 7.5, z: -22 });
  expect(command({ type: 'leaveEquipment' }).ok).toBe(true);
  expect(player.position).toEqual(anchor); expect(player.equipmentId).toBeNull();
  command({ type: 'move', direction: { x: -1, z: 0 } }); advanceSimulation(state, .1);
  expect(player.position.x).toBeCloseTo(anchor.x - .6); expect(player.position.y).toBe(0);
});

test('boarding validates three-dimensional distance to ground controls, faction and static clearance', () => {
  const game = setup(), anchor = game.machine.operatorPosition!;
  game.player.position = { ...game.machine.position };
  expect(game.command({ type: 'board', equipmentId: game.machine.id }).code).toBe('out_of_range');
  game.player.position = { ...anchor, y: 6.01 };
  expect(game.command({ type: 'board', equipmentId: game.machine.id }).code).toBe('out_of_range');
  game.player.position = { ...anchor }; game.player.realm = 'riftbound';
  expect(game.command({ type: 'board', equipmentId: game.machine.id }).code).toBe('invalid_equipment');
  game.player.realm = 'aegis';
  game.zone.config.collision = [{ minX: anchor.x - 1, maxX: anchor.x + 1, minZ: anchor.z - 1, maxZ: anchor.z + 1 }];
  expect(game.command({ type: 'board', equipmentId: game.machine.id }).code).toBe('operator_position_blocked');
  expect(game.machine.operators).toEqual([]);
});

test('oil attacks originate at the cauldron while its operator stays at the controls', () => {
  const game = setup();
  game.player.position = { ...game.machine.operatorPosition! };
  expect(game.command({ type: 'board', equipmentId: game.machine.id }).ok).toBe(true);
  addPlayer(game.state, { id: 'attacker', userId: 'other-user', characterId: 'other-character', realm: 'riftbound', zoneId: game.zone.id });
  const attacker = game.state.players.attacker;
  // Outside the oil's 12m visual-origin range, even though beside the ground operator.
  attacker.position = { x: -330, y: 0, z: -16.5 };
  expect(game.command({ type: 'operate', equipmentId: game.machine.id, targetId: attacker.id }).code).toBe('invalid_target');
  attacker.position = { ...game.machine.position, y: 0 };
  expect(game.command({ type: 'operate', equipmentId: game.machine.id, targetId: attacker.id }).ok).toBe(true);
  expect(attacker.health).toBeLessThan(attacker.maxHealth);
  expect(game.player.position).toEqual(game.machine.operatorPosition);
});

test('equipment without fixed controls retains the moving engine position and invalid slot contracts fail startup', () => {
  const position = { x: 10, y: 0, z: 20 };
  expect(equipmentOperatorPosition({ position })).toBe(position);
  const config = defaultZoneConfig('sunmeadow_march');
  config.keeps[0].siegeOperatorPositions = { oil: [{ x: Infinity, y: 0, z: 0 }] };
  expect(() => createCampaign({ zones: [config] })).toThrow('Invalid siege operator positions');
  config.keeps[0].siegeOperatorPositions.oil = [];
  expect(() => createCampaign({ zones: [config] })).toThrow('Invalid siege operator positions');
});
