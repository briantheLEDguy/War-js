import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { compactSunmeadowTown } from '../scripts/unreal/sunmeadow-compact-town';
import { connectedStreetVillage } from '../scripts/unreal/village-street-network';
import { distanceToSpatialSegment } from '../shared/worldSpatial';
const source = () => redesignT1(JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json', 'utf8')));

describe('shared village street topology', () => {
  it('connects twenty entrances to actual streets without changing the caller or gameplay', () => {
    const zone = source(), original = compactSunmeadowTown(zone), snapshot = structuredClone({ zone, original });
    const result = connectedStreetVillage(original, zone);
    expect({ zone, original }).toEqual(snapshot); expect(connectedStreetVillage(original, zone)).toEqual(result);
    expect(result.access).toHaveLength(20); expect(result.town.streets).toEqual(original.streets);
    expect(result.town.modules.filter(m => m.interiorRequired)).toHaveLength(2);
    expect(result.nativeTraversalAccepted).toBe(false); expect(result.authoringGradesChecked).toBe(false);
    const segments = original.streets.flatMap(s => s.points.slice(1).map((b, i) => [s.points[i], b]));
    for (const [index, lot] of result.town.modules.entries()) {
      expect(lot.approach[0]).toEqual(lot.entry); expect(lot.approach.at(-1)).toEqual({ x: zone.spawnPoint!.x, z: zone.spawnPoint!.z });
      expect(result.access[index].length).toBeLessThanOrEqual(30);
      // After the short doorstep connection, all travel follows a declared street segment.
      for (let i = 2; i < lot.approach.length; i++) {
        const a = lot.approach[i - 1], b = lot.approach[i];
        expect(segments.some(([start, end]) => distanceToSpatialSegment(a, start, end) < 1e-5
          && distanceToSpatialSegment(b, start, end) < 1e-5), lot.id).toBe(true);
      }
    }
  });
  it('does not rescue disconnected roads by drawing shortcuts through empty yards', () => {
    const zone = source(), town = compactSunmeadowTown(zone), root = zone.spawnPoint!;
    town.streets.push({ id: 'disconnected', style: 'dirt_trail', width: 3, points: [{ x: root.x + 150, z: root.z }, { x: root.x + 150, z: root.z + 25 }] });
    town.modules[0].entry = { x: root.x + 155, z: root.z + 10 };
    const before = structuredClone(town);
    expect(() => connectedStreetVillage(town, zone)).toThrow('no short access to connected streets');
    expect(town).toEqual(before);
  });
  it('rejects steep authored walking routes and never substitutes a flat height', () => {
    const zone = source(), town = compactSunmeadowTown(zone);
    expect(() => connectedStreetVillage(town, zone, p => p.z * .2)).toThrow('too steep');
    expect(() => connectedStreetVillage(town, zone, () => NaN)).toThrow('too steep');
    expect(() => connectedStreetVillage(town, zone, p => Math.abs(p.x - zone.spawnPoint!.x) < 1 ? 0 : p.z * .2)).toThrow('too steep');
    const crossSlope = structuredClone(town); crossSlope.streets = [structuredClone(town.streets[0])];
    crossSlope.streets[0].points = crossSlope.streets[0].points.slice(0, 2);
    expect(() => connectedStreetVillage(crossSlope, zone, p => p.x * .2)).toThrow('too steep');
    expect(connectedStreetVillage(town, zone, () => 12).authoringGradesChecked).toBe(true);
  });
  it('rejects road width obstruction, invalid coordinates and foreign villages', () => {
    const zone = source(), town = compactSunmeadowTown(zone);
    const blocked = structuredClone(town); blocked.streets[0].points[0] = { x: town.modules[0].x, z: town.modules[0].z };
    expect(() => connectedStreetVillage(blocked, zone)).toThrow('blocked');
    const invalid = structuredClone(town); invalid.streets[0].points[0].x = Infinity;
    expect(() => connectedStreetVillage(invalid, zone)).toThrow('blocked');
    const unbounded = structuredClone(town); unbounded.streets[0].points[0].x += 1e9;
    expect(() => connectedStreetVillage(unbounded, zone)).toThrow('blocked');
    expect(() => connectedStreetVillage(town, { ...zone, id: 'ashen_steppe' })).toThrow('matching');
  });
});
