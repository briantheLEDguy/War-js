import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { sunmeadowStreetPlan, validateSunmeadowTown } from '../scripts/unreal/sunmeadow-town-plan';
const source = () => redesignT1(JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json', 'utf8')));
describe('Sunmeadow Main Street authoring candidate', () => {
  it('retains gameplay data and reserves a deterministic town with twenty meaningful lots', () => {
    const zone = source(), original = structuredClone(zone), town = sunmeadowStreetPlan(zone);
    expect(zone).toEqual(original); expect(sunmeadowStreetPlan(zone)).toEqual(town);
    expect(town.modules).toHaveLength(20); expect(town.modules.filter(m => m.interiorRequired)).toHaveLength(2);
    expect(new Set(Object.values(town.uses).map(u => u.template)).size).toBeGreaterThan(6);
    expect(town.streets[0].width).toBe(12); expect(town.streets.map(s => s.id)).toContain('sunmeadow_march_town_garrison_court_link');
    expect(town.modules.every(m => m.approach.length > 1 && !m.nativeInteriorAccepted)).toBe(true);
    expect(town.nativeAssetsAccepted).toBe(false); expect(town.visualApproved).toBe(false);
  });
  it('rejects a building obstructing the main street', () => {
    const zone = source(), town = sunmeadowStreetPlan(zone);
    Object.assign(town.modules[0], town.streets[0].points[0]);
    expect(() => validateSunmeadowTown(town, zone)).toThrow();
  });
  it('rejects a building moved onto an existing service', () => {
    const zone = source(), town = sunmeadowStreetPlan(zone);
    Object.assign(town.modules[0], town.serviceReservations[0].point);
    expect(() => validateSunmeadowTown(town, zone)).toThrow();
  });
  it('keeps this authoring recipe out of other regions', () => {
    const zone = source(); zone.id = 'cinderfen_outskirts';
    expect(() => sunmeadowStreetPlan(zone)).toThrow('Sunmeadow');
  });
});