import fs from 'node:fs';
import { Box3, Ray, Vector3 } from 'three';
import { expect, test } from 'vitest';
import { modelTriangles } from './helpers/staticGlbGeometry';
import { mapPropNavigation } from '../server/mapNavigation';
import { campaignGroundHeight } from '../src/shared/orvr/navigation';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { WORLD_EDITOR_PREFABS } from '../src/world/editor/PrefabCatalog';
// @ts-expect-error Executable campaign authoring source.
import { composeSunmeadowEnvironment } from '../scripts/campaign/sunmeadow-environment.mjs';

test('supply-post walkable floors follow the delivered board height and stop at the platform edge', async () => {
  const zone = composeSunmeadowEnvironment(JSON.parse(fs.readFileSync('public/assets/maps/sunmeadow_march.json', 'utf8')));
  const triangles = modelTriangles('frontier_sunmeadow_supply_post_lod0.glb');
  const sites = zone.props.filter((prop: { assetKey: string }) => prop.assetKey === 'frontier_sunmeadow_supply_post');
  expect(sites).toHaveLength(8);
  const original = (await loadCampaignMapConfigs()).find(config => config.id === zone.id)!;
  const boardHeights: number[] = [];
  const boards = triangles.filter(triangle => [triangle.a, triangle.b, triangle.c].every(point => point.y > .06 && point.y < .12));
  const boardBounds = new Box3().setFromPoints(boards.flatMap(triangle => [triangle.a, triangle.b, triangle.c]));
  expect(boardBounds.min.x).toBeLessThan(-3.6); expect(boardBounds.max.x).toBeGreaterThan(3.6);
  expect(boardBounds.min.z).toBeLessThan(-2.1); expect(boardBounds.max.z).toBeGreaterThan(2.1);
  // Sample the exposed central aisle; built-in benches occupy the side bays.
  for (const x of [-2, -1, 0, 1, 2]) for (const z of [-1.75, -.75, .25, 1.25, 1.95]) {
    const ray = new Ray(new Vector3(x, .2, z), new Vector3(0, -1, 0));
    const hits = triangles.map(triangle => ray.intersectTriangle(triangle.a, triangle.b, triangle.c, false, new Vector3()))
      .filter((point): point is Vector3 => point !== null);
    expect(hits.length, `modeled board at ${x},${z}`).toBeGreaterThan(0);
    boardHeights.push(Math.max(...hits.map(point => point.y)));
  }
  // Sculpted timber varies by millimetres around the 86mm floor datum.
  expect(boardHeights.every(y => Math.abs(y - .086) < .009)).toBe(true);
  for (const site of sites) {
    expect(site.walkableSurfaces).toEqual([{ id: `${site.id}_floorboards`, x: 0, z: 0,
      width: 7.2, depth: 4.2, fromY: .086, toY: .086 }]);
    const navigation = mapPropNavigation([site], () => 0), config = { ...original, ...navigation, terrain: undefined };
    const center = { x: site.x, y: 0, z: site.z };
    expect(campaignGroundHeight(config, center)).toBeCloseTo(.086, 6);
    const yaw = site.rotY ?? 0;
    // Leaving by the open front returns to terrain rather than an invisible extension.
    const outside = { x: site.x + Math.sin(yaw) * 2.3, y: 0, z: site.z + Math.cos(yaw) * 2.3 };
    expect(campaignGroundHeight(config, outside)).toBe(0);
  }
});

test('GM supply-post placement includes the same raised floor as campaign shelters', () => {
  const prefabs = WORLD_EDITOR_PREFABS.filter(prefab => prefab.assetKey === 'frontier_sunmeadow_supply_post');
  expect(prefabs.length).toBeGreaterThan(0);
  for (const prefab of prefabs) expect(prefab.walkableSurfaces).toEqual([
    expect.objectContaining({ x: 0, z: 0, width: 7.2, depth: 4.2, fromY: .086, toY: .086 }),
  ]);
});
