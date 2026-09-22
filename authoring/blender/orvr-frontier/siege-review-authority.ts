import { addPlayer, advanceSimulation, createCampaign, submitCommand } from '../../../shared/orvr';
import type { EquipmentKind, PlayerAction } from '../../../shared/orvr';

/** Isolated review campaign; all boarding, movement and operations use the production authority. */
export function createSiegeReviewAuthority(kind: EquipmentKind) {
  const state = createCampaign();
  for (const [id, realm] of [['driver', 'aegis'], ['crew', 'aegis'], ['target', 'riftbound']] as const) {
    addPlayer(state, { id, userId: id, characterId: id, realm, zoneId: 'sunmeadow_march', avatarProfileKey: 'civic_battle_prelate_m' });
  }
  const zone = state.zones.sunmeadow_march;
  zone.seconds = 10;
  // Keep the review focused on the equipment, without guards interrupting an inspection.
  for (const npc of Object.values(zone.npcs)) npc.health = 0;
  const command = (id: string, action: PlayerAction) => submitCommand(state, id, {
    version: 1, sequence: state.players[id].lastSequence + 1, activationId: zone.activationId, action,
  });
  const keep = zone.config.keeps[0], enemy = zone.config.keeps[1];
  zone.keeps[keep.id].level = 3; zone.keeps[keep.id].supplies = 1000;
  state.players.driver.position = { ...keep.quartermaster };
  const purchase = command('driver', { type: 'purchase', keepId: keep.id, equipment: kind });
  if (!purchase.ok) throw Error(`Review purchase rejected: ${purchase.code}`);
  const machine = Object.values(zone.equipment)[0];
  if (kind === 'ram') {
    const dx = enemy.outerGate.x - enemy.position.x, dz = enemy.outerGate.z - enemy.position.z, length = Math.hypot(dx, dz);
    // Stand outside the closed gate slab; parking inside it invalidates the actual boarding traversal.
    machine.position = { ...enemy.outerGate, x: enemy.outerGate.x + dx / length * 8, z: enemy.outerGate.z + dz / length * 8 };
    machine.facing = Math.atan2(-dx, -dz);
  }
  for (const id of ['driver', 'crew']) {
    state.players[id].position = { ...(machine.operatorPosition ?? machine.position) };
    if (id === 'driver' || kind === 'ram') {
      const result = command(id, { type: 'board', equipmentId: machine.id });
      if (!result.ok) throw Error(`Review ${id} boarding rejected: ${result.code}`);
    }
  }
  state.players.target.position = { ...machine.position, z: machine.position.z + 5 };
  const targetId = kind === 'ram' ? zone.keeps[enemy.id].gates.outer.id : 'target';
  return {
    state, zone, machine, command, origin: { ...machine.position },
    operate() {
      state.players.target.health = state.players.target.maxHealth;
      zone.keeps[enemy.id].gates.outer.health = 1000;
      const operator = machine.operators[0] ?? 'driver';
      return command(operator, { type: 'operate', equipmentId: machine.id, targetId });
    },
    advance(seconds: number, direction = { x: 0, z: 0 }) {
      for (let remaining = seconds; remaining > 1e-7;) {
        const step = Math.min(.1, remaining);
        const driver = machine.operators[0];
        if (driver) command(driver, { type: 'move', direction });
        advanceSimulation(state, step); remaining -= step;
      }
    },
  };
}
