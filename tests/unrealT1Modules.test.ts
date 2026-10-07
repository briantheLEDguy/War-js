import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';
import { redesignT1, T1_REGIONS } from '../scripts/unreal/t1-layouts';
import { moduleLocalPoint, segmentCrossesModule, validateVillagePlan, villagePlan } from '../scripts/unreal/t1-modules';
import { distanceToSpatialSegment } from '../shared/worldSpatial';

describe('modular T1 village authoring', () => {
  for (const id of Object.keys(T1_REGIONS)) it(`${id} reserves twenty connected assemblies without approving interiors`, () => {
    const zone = redesignT1(JSON.parse(readFileSync(`public/assets/maps/${id}.json`, 'utf8')) as ZoneDefinition);
    const before = JSON.stringify(zone), plan = villagePlan(zone);
    expect(JSON.stringify(zone)).toBe(before);
    expect(villagePlan(zone)).toEqual(plan);
    expect(plan.modules).toHaveLength(20);
    expect(plan.modules.filter(m => m.interiorRequired)).toHaveLength(2);
    expect(plan.modules.every(m => !m.nativeInteriorAccepted)).toBe(true);
    expect(plan.visualApproved).toBe(false);
    expect(plan.modules.map(m => m.role)).toContain('barracks');
    const frontage = zone.paths!.find(p => p.id === `${id}_village_road`)!.points[1], center = zone.spawnPoint!;
    const projection = (m: { x: number; z: number }) => (m.x - center.x) * (frontage.x - center.x) + (m.z - center.z) * (frontage.z - center.z);
    const military = plan.modules.filter(m => ['barracks', 'watchhouse', 'stables', 'command_hall'].includes(m.role));
    const civilian = plan.modules.filter(m => m.role === 'housing' || m.role === 'furnished_home');
    expect(military.reduce((n, m) => n + projection(m), 0) / military.length).toBeGreaterThan(civilian.reduce((n, m) => n + projection(m), 0) / civilian.length);
    for (const module of plan.modules) {
      expect(module.approach.at(-1)).toEqual({ x: zone.spawnPoint!.x, z: zone.spawnPoint!.z });
      for (const path of zone.paths!) for (let i = 1;i < path.points.length;i++)
        expect(distanceToSpatialSegment(module, path.points[i - 1], path.points[i])).toBeGreaterThan(path.width / 2 + Math.hypot(7, 8) + 3);
    }
    expect(() => validateVillagePlan(plan, zone)).not.toThrow();
    const broken = structuredClone(plan); broken.modules[0].approach = [broken.modules[1], zone.spawnPoint!];
    expect(() => validateVillagePlan(broken, zone)).toThrow('blocks village circulation');
  });
  it('reserves rotated envelopes and rejects a crossing between clear endpoints', () => {
    const zone = redesignT1(JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json', 'utf8')) as ZoneDefinition);
    const module = villagePlan(zone).modules[0];
    expect(segmentCrossesModule(moduleLocalPoint(module, { x: -20, z: 0 }), moduleLocalPoint(module, { x: 20, z: 0 }), module)).toBe(true);
    expect(segmentCrossesModule(moduleLocalPoint(module, { x: -20, z: 20 }), moduleLocalPoint(module, { x: 20, z: 20 }), module)).toBe(false);
  });
});
