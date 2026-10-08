import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { battlefieldLandscape } from '../scripts/unreal/t1-battlefield-landscape';
import { battlefieldScenes } from '../scripts/unreal/t1-battlefield-scenes';
import { distanceToSpatialSegment } from '../shared/worldSpatial';
import type { ZoneDefinition } from '../shared/world/ZoneDefinition';
describe('first-pair battlefield scene cells', () => {
  for (const id of ['sunmeadow_march', 'cinderfen_outskirts']) it(`${id} keeps open roads, objective spaces and off-road choices`, () => {
    const z = battlefieldLandscape(redesignT1(JSON.parse(readFileSync(`public/assets/maps/${id}.json`, 'utf8')) as ZoneDefinition)), before = JSON.stringify(z);
    const cells = battlefieldScenes(z);
    expect(JSON.stringify(z)).toBe(before); expect(cells).toHaveLength(2);
    expect(cells.flatMap(c => c.placements).length).toBeGreaterThan(12);
    for (const c of cells) {
      expect(c.visualApproved).toBe(false); expect(c.combatCoverAccepted).toBe(false);
      for (const p of c.placements) for (const corridor of z.orvrLayout!.terrain.clearCorridors) for (let i = 1; i < corridor.points.length; i++) {
        expect(distanceToSpatialSegment(p, corridor.points[i - 1], corridor.points[i])).toBeGreaterThan(Math.hypot(p.width, p.depth) / 2 + 12);
      }
    }
    expect(new Set(cells.flatMap(c => c.placements.map(p => p.id))).size).toBe(cells.flatMap(c => c.placements).length);
  });
});
