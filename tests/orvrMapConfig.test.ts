import { describe, expect, it } from 'vitest';
import { campaignGateNavigation, loadCampaignMapConfigs } from '../server/mapConfig';
import { createCampaign } from '../src/shared/orvr';
import { campaignAbilityRules, recruitCombatProfile } from '../server/abilityCatalog';
import { campaignColliderBlocksHeight, campaignColliderContains } from '../src/shared/orvr/navigation';

describe('generated maps at the authority boundary', () => {
  it('grounds and rotates closed gate collision independently of its animation hinge', () => {
    const gate = { x: 10, z: -30, width: 6, depth: .72, height: 4.8 };
    const prop = { id: 'gate', kind: 'gate', x: 10, z: -30, y: .2, scale: 2,
      rotY: Math.PI, colliderSpace: 'model' as const,
      colliders: [{ x: 0, z: -.3, width: 6, depth: .72, minY: 0, maxY: 4.8, blocksWhen: 'closed' as const }] };
    const result = campaignGateNavigation(gate, prop, () => 3);
    expect(result.position.x).toBeCloseTo(10);
    expect(result.position.z).toBeCloseTo(-29.4);
    expect(result.position.y).toBeCloseTo(3.2);
    expect(result.footprint).toMatchObject({ width: 12, depth: 1.44, rotY: -Math.PI });
    expect(result.footprint.height).toBeCloseTo(9.6);
    expect(prop.z).toBe(-30);
    expect(campaignGateNavigation(gate, undefined, () => 3).position).toEqual({ x: 10, y: 0, z: -30 });
  });
  it('uses all expanded layouts and their real supply destinations', async () => {
    const configs = await loadCampaignMapConfigs();
    expect(configs).toHaveLength(20);
    for (const config of configs.filter(zone => zone.kind !== 'city')) {
      expect(config.bounds.maxX - config.bounds.minX).toBe(1200);
      expect(config.objectives).toHaveLength(3);
      expect(config.keeps.map(keep => keep.realm).sort()).toEqual(['aegis', 'riftbound']);
      for (const keep of config.keeps) {
        for (const objective of config.objectives) expect(objective.routes![keep.realm]!.at(-1)).toEqual(keep.deliveryPoint);
        // A rear barrier can be several joined wall pieces; its coverage matters, not the center of one old prop.
        expect(config.collision?.some(collider => collider.minX <= keep.position.x + .5 && collider.maxX >= keep.position.x - .5
          && collider.minZ > keep.position.z && collider.minZ < keep.position.z + 50), `${keep.id} rear enclosure`).toBe(true);
        for (const gate of [keep.outerGate, keep.innerGate]) {
          // Closed gates are dynamic blockers. Their cleared passages must not remain baked into static collision.
          expect(config.collision?.some(collider => campaignColliderBlocksHeight(collider, gate.y)
            && campaignColliderContains(collider, gate, .5)), `${keep.id} gate passage`).toBe(false);
        }
        expect(keep.gateFootprints?.outer?.width).toBeGreaterThanOrEqual(5.7);
      }
    }
    const state = createCampaign({ zones: configs, abilities: campaignAbilityRules() });
    expect(state.zones.sunmeadow_march.config.terrain).toBeDefined();
    expect(state.zones.riftspire_capital.config.objectives.at(-1)?.position.y).toBe(-105);
    for (const realm of ['aegis', 'riftbound'] as const) expect(recruitCombatProfile(realm).abilityIds?.every(id => state.abilities[id])).toBe(true);
  });
});
