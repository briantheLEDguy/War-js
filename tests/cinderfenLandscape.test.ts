import fs from 'node:fs';
import { describe, expect, it } from 'vitest';
import { orvrHeightAt } from '../src/shared/orvrTerrain';
import { mapPropNavigation } from '../server/mapNavigation';
import { campaignColliderContains, campaignColliderBlocksHeight } from '../src/shared/orvr/navigation';
// @ts-expect-error Campaign authoring sources execute in Node.
import { composeCinderfenEnvironment } from '../scripts/campaign/cinderfen-environment.mjs';
// @ts-expect-error Campaign authoring sources execute in Node.
import { composeCinderfenLandscape } from '../scripts/campaign/cinderfen-landscape.mjs';

describe('Cinderfen surveyed landscape', () => {
  it('keeps the full village lane width clear of authored walls', () => {
    const zone = composeCinderfenEnvironment(composeCinderfenLandscape(JSON.parse(
      fs.readFileSync('public/assets/maps/cinderfen_outskirts.json', 'utf8'))), { architecture: true });
    const blockers = mapPropNavigation(zone.props, () => 0).collision
      .filter(collider => campaignColliderBlocksHeight(collider, 0));
    const collisions: string[] = [];
    for (const path of zone.paths.filter((path: { id: string }) => path.id.includes('_village_'))) {
      for (let i = 1; i < path.points.length; i++) {
        const a = path.points[i - 1], b = path.points[i];
        const steps = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) / .25));
        for (let step = 0; step <= steps; step++) {
          const point = { x: a.x + (b.x - a.x) * step / steps, y: 0, z: a.z + (b.z - a.z) * step / steps };
          if (blockers.some(collider => campaignColliderContains(collider, point, path.width / 2))) {
            collisions.push(`${path.id} at ${point.x.toFixed(2)},${point.z.toFixed(2)}`);
            break;
          }
        }
      }
    }
    expect(collisions).toEqual([]);
  });
  it('keeps campaign identities, roads and measured construction sites stable', () => {
    const zone = JSON.parse(fs.readFileSync('public/assets/maps/cinderfen_outskirts.json', 'utf8'));
    const originalPaths = structuredClone(zone.paths.filter((path: { id: string }) => !path.id.includes('_village_')));
    const before = JSON.stringify({ keeps: zone.orvrLayout.keeps, objectives: zone.objectives });
    composeCinderfenLandscape(zone);
    expect(JSON.stringify({ keeps: zone.orvrLayout.keeps, objectives: zone.objectives })).toBe(before);
    expect(zone.paths.slice(0, originalPaths.length)).toEqual(originalPaths);
    expect(zone.paths).toHaveLength(originalPaths.length + 7);
    const lane = zone.paths.find((path: { id: string }) => path.id.endsWith('_village_lane'));
    expect(lane.points[0]).toEqual({ x: 435, z: -245 });
    expect(lane.points.at(-1)).toEqual(lane.points[0]);
    const terrain = zone.orvrLayout.terrain;
    for (const [x,z] of [[390,-287],[494,-203],[-184,48],[184,48],[0,104],[533,-189],[-350,0],[350,0]]) {
      expect(orvrHeightAt(terrain, x, z)).toBe(0);
    }
    expect(orvrHeightAt(terrain, -205, 235)).toBeLessThan(-1);
    expect(orvrHeightAt(terrain, -180, 488)).toBeGreaterThan(15);
    const first = JSON.stringify(terrain);
    composeCinderfenLandscape(zone);
    expect(JSON.stringify(terrain)).toBe(first);
    expect(terrain.chunks.every((chunk: { status: string }) => chunk.status === 'planned')).toBe(true);
  });
});
