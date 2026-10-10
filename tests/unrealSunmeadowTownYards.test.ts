import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { sunmeadowStreetPlan } from '../scripts/unreal/sunmeadow-town-plan';
import { sunmeadowYardPlan, validateSunmeadowYards } from '../scripts/unreal/sunmeadow-town-yards';
const source = () => redesignT1(JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json', 'utf8')));
describe('Sunmeadow rear working yards', () => {
  it('adds deterministic purposeful yards without changing the town or gameplay', () => {
    const zone = source(), town = sunmeadowStreetPlan(zone), before = structuredClone({ zone, town });
    const plan = sunmeadowYardPlan(zone, town);
    expect({ zone, town }).toEqual(before); expect(sunmeadowYardPlan(zone, town)).toEqual(plan);
    expect(plan.yards).toHaveLength(6); expect(new Set(plan.yards.map(y => y.lotId)).size).toBe(6);
    expect(plan.yards.flatMap(y => y.props)).toHaveLength(28);
    expect(plan.appearanceApproved).toBe(false); expect(plan.nativeIntegrated).toBe(false);
  });
  it('rejects props obstructing a street, service, courtyard or door approach', () => {
    for (const kind of ['street', 'service', 'court', 'door']) {
      const zone = source(), town = sunmeadowStreetPlan(zone), plan = sunmeadowYardPlan(zone, town);
      const yard = plan.yards[0], prop = yard.props[0];
      if (kind === 'street') Object.assign(prop, { x: yard.x + 4.3, z: yard.z });
      if (kind === 'service') town.serviceReservations[0].point = { x: prop.x, z: prop.z };
      if (kind === 'court') town.arrivalCourt = { point: { x: prop.x, z: prop.z }, radius: 3 };
      if (kind === 'door') town.modules[0].approach = [{ x: prop.x - .5, z: prop.z }, { x: prop.x + .5, z: prop.z }];
      expect(() => validateSunmeadowYards(plan, zone, town), kind).toThrow('Yard prop blocks retained circulation');
    }
  });
  it('rejects invalid extents and unbounded prop sizes', () => {
    const zone = source(), town = sunmeadowStreetPlan(zone), plan = sunmeadowYardPlan(zone, town);
    plan.yards[0].radiusX = Infinity; expect(() => validateSunmeadowYards(plan, zone, town)).toThrow();
    const second = sunmeadowYardPlan(zone, town); second.yards[0].props[0].radius = -1;
    expect(() => validateSunmeadowYards(second, zone, town)).toThrow();
  });
  it('rejects a boundary crossing a reserved road', () => {
    const zone = source(), town = sunmeadowStreetPlan(zone), plan = sunmeadowYardPlan(zone, town), yard = plan.yards[0];
    yard.boundary.from = { x: -660, z: -374 }; yard.boundary.to = { x: -660, z: -366 };
    expect(() => validateSunmeadowYards(plan, zone, town)).toThrow('circulation');
  });
  it('refuses nonregional authoring', () => {
    const zone = source(), town = sunmeadowStreetPlan(zone); zone.id = 'brightfen_approach';
    expect(() => sunmeadowYardPlan(zone, town)).toThrow('Sunmeadow');
  });
});
