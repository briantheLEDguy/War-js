import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { regionalSceneModules } from '../scripts/unreal/t1-scene-modules';
import { containsSpatialPoint, distanceToSpatialSegment } from '../shared/worldSpatial';

describe('regional scenery assemblies', () => {
  for (const id of ['sunmeadow_march', 'cinderfen_outskirts']) it(`${id} preserves travel and combat reservations`, () => {
    const zone = redesignT1(JSON.parse(readFileSync(`public/assets/maps/${id}.json`, 'utf8')) as ZoneDefinition), before = JSON.stringify(zone);
    const modules = regionalSceneModules(zone);
    expect(JSON.stringify(zone)).toBe(before);
    expect(regionalSceneModules(zone)).toEqual(modules);
    expect(modules).toHaveLength(3);
    expect(modules.every(m => !m.visualApproved && !m.combatCoverAccepted)).toBe(true);
    const placements = modules.flatMap(m => m.placements);
    expect(placements.length).toBeGreaterThan(40);
    expect(new Set(placements.map(p => p.id)).size).toBe(placements.length);
    for (const placement of placements) {
      const radius = Math.hypot(placement.reservation.width, placement.reservation.depth) / 2;
      expect(containsSpatialPoint(zone.spatial!, placement, radius + 2)).toBe(true);
      for (const path of zone.paths!) for (let i = 1;i < path.points.length;i++)
        expect(distanceToSpatialSegment(placement, path.points[i - 1], path.points[i])).toBeGreaterThanOrEqual(radius + path.width / 2 + 3);
    }
  });
  it('leaves the later native batch untouched', () => {
    const zone = redesignT1(JSON.parse(readFileSync('public/assets/maps/brightfen_approach.json', 'utf8')) as ZoneDefinition);
    expect(regionalSceneModules(zone)).toEqual([]);
  });
});
