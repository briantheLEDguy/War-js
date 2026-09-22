import { readFile } from 'node:fs/promises';
import { describe, expect, it } from 'vitest';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { createKeepEnclosureAudit } from '../scripts/audit-keep-enclosures';
import { addPlayer, advanceSimulation, createCampaign, keepPosterns, submitCommand } from '../shared/orvr/index';
import type { Position, ZoneConfig } from '../shared/orvr/index';
import { campaignGroundHeight } from '../shared/orvr/navigation';

const configs = (await loadCampaignMapConfigs()).filter(config => config.keeps.length);
const keeps = configs.flatMap(config => config.keeps.map(keep => ({ config, keep, name: keep.id })));

// Activate each real generated layout as the opening zone; campaign unlocking is tested separately.
function activeLayout(config: ZoneConfig) {
  const state = createCampaign({ zones: [{ ...config, id: 'sunmeadow_march' }] });
  const zone = state.zones.sunmeadow_march;
  addPlayer(state, { id: 'walker', userId: 'walker', characterId: 'walker', realm: 'aegis', zoneId: zone.id });
  for (const npc of Object.values(zone.npcs)) npc.health = 0;
  const player = state.players.walker;
  const command = (action: Parameters<typeof submitCommand>[2]['action']) => submitCommand(state, player.id, {
    version: 1, sequence: player.lastSequence + 1, activationId: zone.activationId, action,
  });
  return { state, zone, player, command };
}

describe('generated keep enclosures', () => {
  it('covers both keeps in all sixteen battlefields and two fortresses', () => {
    expect(configs).toHaveLength(18);
    expect(keeps).toHaveLength(36);
  });

  it.each(keeps)('$name closes every ground approach and requires both breaches', ({ config, keep }) => {
    const audit = createKeepEnclosureAudit(config, keep);
    const courtyard: Position = { x: keep.position.x, y: 0, z: (keep.outerGate.z + keep.innerGate.z) / 2 };
    expect(audit({ target: courtyard }).reachable, 'closed outer enclosure').toBe(false);
    expect(audit().reachable, 'closed commander enclosure').toBe(false);
    expect(audit({ breachedGates: ['outer'], target: courtyard }).reachable, 'breached outer gate opens courtyard').toBe(true);
    expect(audit({ breachedGates: ['outer'] }).reachable, 'inner gate still protects commander').toBe(false);
    expect(audit({ breachedGates: ['outer', 'inner'] }).reachable, 'both breaches open commander approach').toBe(true);
  });

  it.each(keeps)('$name blocks walking through closed leaves and permits breached passage', ({ config, keep }) => {
    const { state, zone, player, command } = activeLayout(config);
    for (const stage of ['outer', 'inner'] as const) {
      const gate = stage === 'outer' ? keep.outerGate : keep.innerGate;
      player.position = { ...gate, z: gate.z - 4 };
      player.position.y = campaignGroundHeight(zone.config, player.position);
      for (let tick = 0; tick < 16; tick += 1) {
        expect(command({ type: 'move', direction: { x: 0, z: 1 } }).ok).toBe(true);
        advanceSimulation(state, .1);
      }
      expect(player.position.z, `${stage} closed leaf`).toBeLessThan(gate.z);
      zone.keeps[keep.id].gates[stage].health = 0;
      for (let tick = 0; tick < 12; tick += 1) {
        expect(command({ type: 'move', direction: { x: 0, z: 1 } }).ok).toBe(true);
        advanceSimulation(state, .1);
      }
      expect(player.position.z, `${stage} breached leaf`).toBeGreaterThan(gate.z + 2);
    }
  });

  it('keeps visible generic wall spans flush with all four leaf apertures', async () => {
    const generic = configs.filter(config => !['sunmeadow_march', 'cinderfen_outskirts'].includes(config.id));
    for (const config of generic) {
      const map = JSON.parse(await readFile(`public/assets/maps/${config.id}.json`, 'utf8'));
      for (const keep of config.keeps) {
        for (const [wallPrefix, doorSuffix, modelWidth] of [
          ['outer_front', 'front_gate', 16], ['outer_rear', 'rear_postern', 5.2],
          ['inner_front', 'inner_front_door', 5.2], ['inner_rear', 'inner_rear_door', 5.2],
        ] as const) {
          const prefix = `${keep.id}_keep`;
          const leaf = map.props.find((prop: { id: string }) => prop.id === `${prefix}_${doorSuffix}`);
          expect(leaf.colliders[0].width).toBe(modelWidth);
          for (const [side, direction] of [['left', -1], ['right', 1]] as const) {
            const wall = map.props.find((prop: { id: string }) => prop.id === `${prefix}_${wallPrefix}_${side}_wall`);
            const wallEdge = wall.x - direction * 5 * wall.scale * wall.scaleX;
            const leafEdge = leaf.x + direction * modelWidth * leaf.scale / 2;
            // Expanded placement rounds world coordinates to centimetres.
            expect(Math.abs(wallEdge - leafEdge), `${keep.id} ${wallPrefix} ${side}`).toBeLessThan(.011);
          }
        }
      }
    }
  });

  it('preserves owner-only use of every authored postern without opening siege gates', () => {
    let entrances = 0;
    for (const { config, keep } of keeps) for (const postern of keepPosterns(keep)) {
      entrances += 1;
      const { zone, player, command } = activeLayout(config);
      player.realm = keep.realm;
      player.position = { ...postern.outside };
      const action = { type: 'postern' as const, keepId: keep.id, ...(postern.id ? { posternId: postern.id } : {}) };
      expect(command(action).ok, `${keep.id} ${postern.id} inward`).toBe(true);
      expect(player.position).toEqual(postern.inside);
      zone.seconds += 1.1;
      expect(command(action).ok, `${keep.id} ${postern.id} outward`).toBe(true);
      expect(player.position).toEqual(postern.outside);
      player.realm = keep.realm === 'aegis' ? 'riftbound' : 'aegis';
      expect(command(action).code).toBe('invalid_keep');
      expect(zone.keeps[keep.id].gates.outer.health).toBe(1000);
      expect(zone.keeps[keep.id].gates.inner.health).toBe(1000);
    }
    expect(entrances).toBe(6);
  });
});
