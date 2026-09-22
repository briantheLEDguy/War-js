import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { Box3, Ray, Vector3 } from 'three';
import { expect, test } from 'vitest';
import { modelTriangles } from './helpers/staticGlbGeometry';
// @ts-expect-error Campaign generation is executable JavaScript.
import { integrateRegionalWorksites, REGIONAL_WORKSITES, regionalWorksiteReservations } from '../scripts/campaign/regional-worksites.mjs';
// @ts-expect-error Campaign generation is executable JavaScript.
import { composeSunmeadowEnvironment } from '../scripts/campaign/sunmeadow-environment.mjs';
// @ts-expect-error Campaign generation is executable JavaScript.
import { composeCinderfenEnvironment } from '../scripts/campaign/cinderfen-environment.mjs';
// @ts-expect-error Campaign generation is executable JavaScript.
import { composeCinderfenLandscape } from '../scripts/campaign/cinderfen-landscape.mjs';
// @ts-expect-error Campaign generation is executable JavaScript.
import { integrateCinderfen } from '../scripts/campaign/cinderfen-integration.mjs';
import { mapPropNavigation } from '../server/mapNavigation';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { campaignColliderBlocksHeight, campaignColliderContains, campaignGroundHeight } from '../shared/orvr/navigation';
import type { ZoneConfig } from '../shared/orvr/protocol';

const read = (file: string) => JSON.parse(fs.readFileSync(file, 'utf8'));
const registry = read('public/assets/models/asset-index.json');
const metadata = read('authoring/blender/frontier-workshop-items/builder-metadata.json').assets;
const ids = ['sunmeadow_march', 'cinderfen_outskirts'];
const source = (id: string) => read(`public/assets/maps/${id}.json`);
const owned = (zone: ReturnType<typeof source>) => zone.props.filter((p: { id: string }) => p.id?.startsWith(`${zone.id}_worksite_`));


for (const id of ids) {
  test(`${id}: composes two measured service props without moving the village`, () => {
    const before = source(id), zone = integrateRegionalWorksites(structuredClone(before), registry);
    const items = owned(zone);
    expect(items).toHaveLength(2);
    expect(integrateRegionalWorksites(structuredClone(zone), registry)).toEqual(zone);
    const strip = (props: typeof zone.props) => props.filter((p: { id: string }) => !p.id?.startsWith(`${id}_worksite_`))
      .sort((a: { id: string }, b: { id: string }) => a.id.localeCompare(b.id));
    expect(strip(zone.props)).toEqual(strip(before.props));
    for (const key of ['npcs', 'enemies', 'craftingStations', 'paths', 'ambientLife']) expect(zone[key]).toEqual(before[key]);
    const service = zone.craftingStations.find((entry: { id: string }) => entry.id === `${id}_salvage_station`);
    for (const item of items) {
      expect(item.colliders).toEqual(metadata[item.assetKey].colliders);
      const bytes = fs.readFileSync(`public/assets/models/${item.model}`);
      expect(createHash('sha256').update(bytes).digest('hex')).toBe(metadata[item.assetKey].modelSha256);
      const front = regionalWorksiteReservations(item, metadata[item.assetKey])[1];
      expect(Math.hypot(front.x - service.x, front.z - service.z)).toBeLessThan(service.radius);
    }
  });

  test(`${id}: regional road/architecture refresh retains worksite positions and collisions`, () => {
    const refresh = (zone: ReturnType<typeof source>) => id === 'sunmeadow_march'
      ? composeSunmeadowEnvironment(zone, { terrain: true, architecture: true, nature: true })
      : integrateCinderfen(composeCinderfenEnvironment(composeCinderfenLandscape(zone, true), { architecture: true }));
    const zone = integrateRegionalWorksites(refresh(source(id)), registry), items = owned(zone);
    expect(items).toHaveLength(2);
    const refreshed = refresh(structuredClone(zone));
    expect(owned(refreshed)).toEqual(items);
    expect(owned(integrateRegionalWorksites(refreshed, registry))).toEqual(items);
  });

  test(`${id}: feet contact actual delivered floor triangles and visible bodies/fronts clear host geometry`, () => {
    const site = REGIONAL_WORKSITES[id], triangles = modelTriangles(registry.staticProps[site.hostKey].model);
    for (const item of site.items) {
      const contract = metadata[item.key];
      const feet = contract.colliders.filter((box: { minY: number }) => box.minY === 0);
      expect(feet.length).toBeGreaterThanOrEqual(2);
      for (const foot of feet) {
        let contacts = 0;
        for (const dx of [-.3, 0, .3]) for (const dz of [-.3, 0, .3]) {
          const ray = new Ray(new Vector3(item.x + foot.x + dx * foot.width, site.floorY + .2,
            item.z + foot.z + dz * foot.depth), new Vector3(0, -1, 0));
          const hits = triangles.map(triangle => ray.intersectTriangle(triangle.a, triangle.b, triangle.c, false, new Vector3()))
            .filter((point): point is Vector3 => point !== null).map(point => point.y);
          // Narrow seams between deck boards may have no triangle at the ray.
          if (!hits.length) continue;
          expect(Math.abs(Math.max(...hits) - site.floorY), `${item.role} foot contact`).toBeLessThan(.009);
          contacts++;
        }
        expect(contacts, `${item.role} supported foot area`).toBeGreaterThanOrEqual(6);
      }
      const { minimum: lo, maximum: hi } = contract.boundsYUp, front = contract.approachSource;
      const body = new Box3(new Vector3(item.x + lo[0], site.floorY + .02, item.z + lo[2]),
        new Vector3(item.x + hi[0], site.floorY + hi[1], item.z + hi[2]));
      const standing = new Box3(new Vector3(item.x + front.minimum[0], site.floorY + .02, item.z - front.maximum[1]),
        new Vector3(item.x + front.maximum[0], site.floorY + 1.8, item.z - front.minimum[1]));
      expect(triangles.filter(triangle => body.intersectsTriangle(triangle)), `${item.role} host intersection`).toHaveLength(0);
      expect(triangles.filter(triangle => standing.intersectsTriangle(triangle)), `${item.role} clear standing space`).toHaveLength(0);
      const approach = [...site.entrance, ...item.via ?? [],
        [item.x + (front.minimum[0] + front.maximum[0]) / 2, item.z - (front.minimum[1] + front.maximum[1]) / 2]];
      for (let i = 1; i < approach.length; i++) {
        const a = approach[i - 1], b = approach[i], steps = Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / .25);
        for (let j = 0; j <= steps; j++) {
          const x = a[0] + (b[0] - a[0]) * j / steps, z = a[1] + (b[1] - a[1]) * j / steps;
          // Cinderfen's modeled door sill rises 3.4 cm above its supported deck.
          const body = new Box3(new Vector3(x - .43, site.floorY + .05, z - .43),
            new Vector3(x + .43, site.floorY + 1.8, z + .43));
          const hit = triangles.find(triangle => body.intersectsTriangle(triangle));
          expect(hit, `${item.role} visible doorway/approach at ${x},${z}: ${JSON.stringify(hit)}`).toBeUndefined();
        }
      }
    }
  });

  test(`${id}: player reaches both workfronts from the village road while furniture blocks movement`, async () => {
    const zone = integrateRegionalWorksites(source(id), registry), items = owned(zone);
    expect(items).toHaveLength(2);
    const configs = await loadCampaignMapConfigs(), original = configs.find(config => config.id === id)!;
    const terrain = { ...original, walkableSurfaces: [] };
    // Rebuild from the candidate map; published maps may still contain the prior placement.
    const navigation = mapPropNavigation(zone.props, (x, z) => campaignGroundHeight(terrain, { x, y: 0, z }));
    const config: ZoneConfig = { ...original, ...navigation };
    const start = id === 'sunmeadow_march' ? { x: -435, z: -245 } : { x: 477, z: -255 };
    const service = zone.craftingStations.find((entry: { id: string }) => entry.id === `${id}_salvage_station`);
    const goals = [...items.map((item: { assetKey: string }) => regionalWorksiteReservations(item, metadata[item.assetKey])[1]), service];
    const minX = Math.floor(Math.min(start.x, ...goals.map((g: { x: number }) => g.x)) - 5);
    const minZ = Math.floor(Math.min(start.z, ...goals.map((g: { z: number }) => g.z)) - 5);
    const maxX = Math.ceil(Math.max(start.x, ...goals.map((g: { x: number }) => g.x)) + 5);
    const maxZ = Math.ceil(Math.max(start.z, ...goals.map((g: { z: number }) => g.z)) + 5);
    const step = .25, width = Math.round((maxX - minX) / step) + 1, height = Math.round((maxZ - minZ) / step) + 1;
    const blockers = config.collision!.filter(c => c.maxX >= minX && c.minX <= maxX && c.maxZ >= minZ && c.minZ <= maxZ);
    const clear = new Uint8Array(width * height), seen = new Uint8Array(clear.length);
    for (let z = 0; z < height; z++) for (let x = 0; x < width; x++) {
      const point = { x: minX + x * step, y: 0, z: minZ + z * step };
      point.y = campaignGroundHeight(config, point);
      clear[z * width + x] = blockers.some(c => campaignColliderBlocksHeight(c, point.y)
        && campaignColliderContains(c, point, .45)) ? 0 : 1;
    }
    const index = (p: { x: number; z: number }) => Math.round((p.z - minZ) / step) * width + Math.round((p.x - minX) / step);
    const queue = [index(start)]; seen[queue[0]] = 1;
    expect(clear[queue[0]]).toBe(1);
    for (let q = 0; q < queue.length; q++) {
      const at = queue[q], x = at % width, z = Math.floor(at / width);
      for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, nz = z + dz, next = nz * width + nx;
        if (nx < 0 || nz < 0 || nx >= width || nz >= height || seen[next] || !clear[next]) continue;
        seen[next] = 1; queue.push(next);
      }
    }
    for (const goal of goals) expect(seen[index(goal)], 'road to standing front or service center').toBe(1);
    const servicePosition = { x: service.x, y: campaignGroundHeight(config, { ...service, y: 0 }), z: service.z };
    expect(blockers.some(c => campaignColliderBlocksHeight(c, servicePosition.y)
      && campaignColliderContains(c, servicePosition, .5)), 'service origin has full player clearance').toBe(false);
    for (const item of items) {
      const navigation = mapPropNavigation([item], () => 0), body = navigation.collision.find(c => c.maxY! > item.y + .8)!;
      expect(body).toBeDefined();
      expect(campaignColliderBlocksHeight(body, item.y)).toBe(true);
      expect(campaignColliderContains(body, { ...body.footprint!, y: item.y }, .45)).toBe(true);
      const point = { x: item.x, y: item.y, z: item.z };
      expect(Math.abs(campaignGroundHeight(config, point) - item.y)).toBeLessThan(.005);
    }
  }, 15000);
}

test('missing/stale models and missing collision metadata leave no new invisible blockers', () => {
  for (const mutate of [
    (assets: typeof registry, data: typeof metadata) => { assets.staticProps.frontier_siege_repair_bench.runtimeReady = false; },
    (assets: typeof registry, data: typeof metadata) => { assets.staticProps.frontier_siege_repair_bench.model = 'not-delivered.glb'; },
    (assets: typeof registry, data: typeof metadata) => { data.frontier_siege_repair_bench.modelSha256 = 'stale'; },
    (assets: typeof registry, data: typeof metadata) => { data.frontier_siege_repair_bench.colliders = []; },
  ]) {
    const assets = structuredClone(registry), data = structuredClone(metadata); mutate(assets, data);
    const result = integrateRegionalWorksites(source(ids[0]), assets, data);
    expect(owned(result).map((p: { assetKey: string }) => p.assetKey)).toEqual(['frontier_siege_ammunition_cradle']);
  }
  const assets = structuredClone(registry); assets.staticProps.frontier_sunmeadow_supply_post.modelSha256 = 'changed-building';
  expect(owned(integrateRegionalWorksites(source(ids[0]), assets))).toHaveLength(0);
});

test('occupied workfronts, door routes, and model-only scenery suppress conflicting furniture', () => {
  const base = integrateRegionalWorksites(source(ids[0]), registry);
  const bench = owned(base).find((p: { assetKey: string }) => p.assetKey === 'frontier_siege_repair_bench');
  const front = regionalWorksiteReservations(bench, metadata[bench.assetKey])[1];
  const blocked = source(ids[0]);
  blocked.npcs.push({ id: 'new_worker', x: front.x, z: front.z });
  expect(owned(integrateRegionalWorksites(blocked, registry)).some((p: { id: string }) => p.id === bench.id)).toBe(false);
  const door = source(ids[1]);
  door.props.push({ id: 'existing_crate', kind: 'approved_crate', model: 'prop_aegis_crate_stack.glb',
    x: 479.8, z: -255, scale: 1 });
  expect(owned(integrateRegionalWorksites(door, registry))).toHaveLength(0);
});
