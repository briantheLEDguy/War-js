import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { sunmeadowStreetPlan } from '../scripts/unreal/sunmeadow-town-plan';
import { compactSunmeadowTown } from '../scripts/unreal/sunmeadow-compact-town';
import { sunmeadowYardPlan } from '../scripts/unreal/sunmeadow-town-yards';
import { connectVillageStreets } from '../scripts/unreal/village-street-connections';
import { moduleLocalPoint, segmentCrossesModule } from '../scripts/unreal/t1-modules';

const source = () => redesignT1(JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json', 'utf8')));
describe('Sunmeadow compact frontage', () => {
  it('keeps the original plan and gameplay immutable while bringing seven frontages closer', () => {
    const zone = source(), original = sunmeadowStreetPlan(zone), snapshot = structuredClone({ zone, original });
    const town = compactSunmeadowTown(zone, original);
    expect({ zone, original }).toEqual(snapshot); expect(compactSunmeadowTown(zone, original)).toEqual(town);
    expect(town.modules.filter((m, i) => m.x !== original.modules[i].x || m.z !== original.modules[i].z)).toHaveLength(7);
    expect(town.modules).toHaveLength(20); expect(town.modules.filter(m => m.interiorRequired)).toHaveLength(2);
    expect(town.streets).toEqual(original.streets); expect(town.serviceReservations).toEqual(original.serviceReservations);
    expect(town.arrivalCourt).toEqual(original.arrivalCourt); expect(town.uses).toEqual(original.uses);
    expect(town.nativeAssetsAccepted).toBe(false); expect(town.traversalAccepted).toBe(false); expect(town.visualApproved).toBe(false);
  });
  it('retains all six working yards and connects each door without crossing reserved shells', () => {
    const zone = source(), town = compactSunmeadowTown(zone);
    expect(sunmeadowYardPlan(zone, town).yards).toHaveLength(6);
    for (const lot of town.modules) {
      expect(lot.entry).toEqual(moduleLocalPoint(lot, { x: 0, z: -10 }));
      expect(lot.approach[0]).toEqual(lot.entry); expect(lot.approach.at(-1)).toEqual({ x: zone.spawnPoint!.x, z: zone.spawnPoint!.z });
      for (let i = 1; i < lot.approach.length; i++) expect(town.modules.some(m => segmentCrossesModule(lot.approach[i - 1], lot.approach[i], m))).toBe(false);
    }
  });
  it('rejects an obstructed or foreign study without partially replacing existing connections', () => {
    const zone = source(), town = compactSunmeadowTown(zone);
    Object.assign(town.modules[0].entry, { x: town.modules[0].x, z: town.modules[0].z });
    const approaches = structuredClone(town.modules.map(m => m.approach));
    expect(() => connectVillageStreets(town, zone)).toThrow('no connected approach');
    expect(town.modules.map(m => m.approach)).toEqual(approaches);
    expect(() => compactSunmeadowTown({ ...zone, id: 'ashen_steppe' }, town)).toThrow('Sunmeadow');
  });
  it('rejects retained military routes that would cross a moved frontage', () => {
    const zone = source(), town = compactSunmeadowTown(zone), lot = town.modules[0];
    zone.paths!.push({ id: 'retained_route', width: 8, style: 'dirt_trail', points: [{ x: lot.x - 30, z: lot.z }, { x: lot.x + 30, z: lot.z }] });
    expect(() => compactSunmeadowTown(zone)).toThrow('blocks retained route');
  });
});
