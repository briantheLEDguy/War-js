import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { Box3, Matrix4, Quaternion, Ray, Vector3 } from 'three';
import { expect, test } from 'vitest';
import { modelTriangles } from './helpers/staticGlbGeometry';
import { mapPropNavigation } from '../server/mapNavigation';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { campaignColliderBlocksHeight, campaignColliderContains, campaignGroundHeight } from '../src/shared/orvr/navigation';
import { WORLD_EDITOR_PREFABS } from '../src/world/editor/PrefabCatalog';
// @ts-expect-error Executable campaign authoring source.
import { integrateRegionalApothecaries, REGIONAL_APOTHECARIES, regionalWorksiteReservations } from '../scripts/campaign/regional-worksites.mjs';

const key = 'frontier_field_apothecary', packagePath = 'authoring/blender/field-apothecary';
const read = (file: string) => JSON.parse(fs.readFileSync(file, 'utf8'));
const sha = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
const registry = read('public/assets/models/asset-index.json');
const metadata = read(`${packagePath}/builder-metadata.json`).assets;
const owned = (zone: { id: string; props: Array<{ id: string }> }) => zone.props.filter(prop => prop.id.startsWith(`${zone.id}_delivered_apothecary_`));

test('the delivered preparation table has matching source, three LODs, packed materials and GM collision', () => {
  const approved = read(`scripts/blender-character-pipeline/data/approved-assets/${key}.approved.json`);
  const entry = registry.staticProps[key], qc = read(`public/assets/models/${approved.qc}`);
  expect(entry).toMatchObject({ assetId: 'prop.frontier.field_apothecary', runtimeReady: true,
    approvalState: 'approved', modelSha256: approved.hashes.modelSha256, qcSha256: approved.hashes.qcSha256 });
  expect(sha(fs.readFileSync(`public/assets/models/${approved.qc}`))).toBe(approved.hashes.qcSha256);
  expect(qc.lods.map((lod: { level: number }) => lod.level)).toEqual([0, 1, 2]);
  for (const lod of qc.lods) {
    const bytes = fs.readFileSync(`public/assets/models/${lod.model}`);
    expect(sha(bytes)).toBe(lod.sha256);
    const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
    expect(gltf.meshes).toHaveLength(9); expect(gltf.materials).toHaveLength(9);
    expect(gltf.images.length).toBeGreaterThanOrEqual(18);
    expect(gltf.images.every((image: { uri?: string; bufferView?: number }) => !image.uri && Number.isInteger(image.bufferView))).toBe(true);
    expect(gltf.skins ?? []).toHaveLength(0); expect(gltf.animations ?? []).toHaveLength(0);
    for (const material of gltf.materials) {
      expect(material.pbrMetallicRoughness.baseColorTexture).toBeDefined();
      expect(material.pbrMetallicRoughness.metallicRoughnessTexture).toBeDefined();
      expect(material.normalTexture).toBeDefined();
    }
  }
  expect(qc.lods[1].triangles).toBeLessThan(qc.lods[0].triangles * .75);
  expect(qc.lods[2].triangles).toBeLessThan(qc.lods[1].triangles * .75);
  for (const [relative, receipt] of Object.entries(qc.reviewEvidence.files) as [string, { sha256: string; bytes: number }][]) {
    const bytes = fs.readFileSync(`${qc.frozenSource}/files/${relative}`);
    expect(sha(bytes), relative).toBe(receipt.sha256); expect(bytes.length, relative).toBe(receipt.bytes);
  }
  const prefab = WORLD_EDITOR_PREFABS.filter(entry => entry.assetKey === key);
  expect(prefab).toHaveLength(1);
  expect([prefab[0].model, ...prefab[0].lodModels ?? []]).toEqual(qc.lods.map((lod: { model: string }) => lod.model));
  expect(prefab[0].colliders).toEqual(metadata[key].colliders);
  expect(prefab[0].walkableSurfaces).toEqual([]); expect(prefab[0].cameraSolid).toBe(true);
});

for (const id of ['sunmeadow_march', 'cinderfen_outskirts']) {
  test(`${id}: both keep tables clear the actual authored walls, stairs and furnishings`, () => {
    const zone = read(`public/assets/maps/${id}.json`);
    const tables = zone.props.filter((prop: { id: string }) => new RegExp(`^${id}_delivered_(aegis|riftbound)_apothecary$`).test(prop.id));
    expect(tables).toHaveLength(2);
    const meshes = new Map<string, ReturnType<typeof modelTriangles>>();
    for (const table of tables) {
      const bounds = metadata[key].boundsYUp;
      const volume = new Box3(new Vector3(table.x + bounds.minimum[0], (table.y ?? 0) + .02, table.z + bounds.minimum[2]),
        new Vector3(table.x + bounds.maximum[0], (table.y ?? 0) + bounds.maximum[1], table.z + bounds.maximum[2]));
      for (const prop of zone.props) {
        if (prop.id === table.id || prop.visible === false || !prop.colliders?.length
          || Math.hypot(prop.x - table.x, prop.z - table.z) > 40) continue;
        const model = prop.model ?? registry.staticProps[prop.assetKey]?.model;
        if (!model || !fs.existsSync(`public/assets/models/${model}`)) continue;
        if (!meshes.has(model)) meshes.set(model, modelTriangles(model));
        const scale = prop.scale ?? 1;
        const transform = new Matrix4().compose(new Vector3(prop.x, prop.y ?? 0, prop.z),
          new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), prop.rotY ?? 0),
          new Vector3(scale * (prop.scaleX ?? 1), scale * (prop.scaleY ?? 1), scale * (prop.scaleZ ?? 1)));
        expect(meshes.get(model)!.some(source => {
          const triangle = source.clone();
          triangle.a.applyMatrix4(transform); triangle.b.applyMatrix4(transform); triangle.c.applyMatrix4(transform);
          return volume.intersectsTriangle(triangle);
        }), `${table.id} clears visible ${prop.id}`).toBe(false);
      }
    }
  });

  test(`${id}: fits one shared table without changing its themed shelter, services or routes`, () => {
    const source = read(`public/assets/maps/${id}.json`);
    const zone = integrateRegionalApothecaries(structuredClone(source), registry);
    expect(owned(zone)).toHaveLength(1);
    expect(integrateRegionalApothecaries(structuredClone(zone), registry)).toEqual(zone);
    const without = (props: typeof zone.props) => props.filter((prop: { id: string }) => !prop.id.startsWith(`${id}_delivered_apothecary_`))
      .sort((a: { id: string }, b: { id: string }) => a.id.localeCompare(b.id));
    expect(without(zone.props)).toEqual(without(source.props));
    for (const field of ['npcs', 'craftingStations', 'paths', 'enemies', 'zoneTriggers']) expect(zone[field]).toEqual(source[field]);
    const item = owned(zone)[0], contract = metadata[key], site = REGIONAL_APOTHECARIES[id];
    expect(item).toMatchObject({ assetKey: key, colliderSpace: 'model', y: site.floorY, colliders: contract.colliders });
    const hostTriangles = modelTriangles(registry.staticProps[site.hostKey].model);
    const local = site.items[0], [lo, hi] = [contract.boundsYUp.minimum, contract.boundsYUp.maximum];
    const volume = new Box3(new Vector3(local.x + lo[0], site.floorY + .02, local.z + lo[2]),
      new Vector3(local.x + hi[0], site.floorY + hi[1], local.z + hi[2]));
    expect(hostTriangles.some(triangle => volume.intersectsTriangle(triangle)), 'visible table clears walls, roof and built-ins').toBe(false);
    const front = contract.workingFront;
    const standing = new Box3(new Vector3(local.x + front.minimum[0], site.floorY + .04, local.z + front.minimum[2]),
      new Vector3(local.x + front.maximum[0], site.floorY + 1.8, local.z + front.maximum[2]));
    expect(hostTriangles.some(triangle => standing.intersectsTriangle(triangle)), 'standing body clears host geometry').toBe(false);
    const feet = contract.colliders.filter((collider: { minY: number }) => collider.minY === 0);
    expect(feet).toHaveLength(4);
    for (const foot of feet) {
      let hits = 0;
      for (const dx of [-.3, 0, .3]) for (const dz of [-.3, 0, .3]) {
        const ray = new Ray(new Vector3(local.x + foot.x + foot.width * dx, site.floorY + .2,
          local.z + foot.z + foot.depth * dz), new Vector3(0, -1, 0));
        const points = hostTriangles.map(triangle => ray.intersectTriangle(triangle.a, triangle.b, triangle.c, false, new Vector3()))
          .filter((point): point is Vector3 => point !== null);
        if (!points.length) continue;
        expect(Math.abs(Math.max(...points.map(point => point.y)) - site.floorY)).toBeLessThan(.009);
        hits++;
      }
      expect(hits, 'foot supported across its area').toBeGreaterThanOrEqual(6);
    }
  });

  test(`${id}: player can reach the preparation front and station while the table stops movement`, async () => {
    const zone = integrateRegionalApothecaries(read(`public/assets/maps/${id}.json`), registry), item = owned(zone)[0];
    expect(item).toBeDefined();
    const original = (await loadCampaignMapConfigs()).find(config => config.id === id)!;
    const terrain = { ...original, walkableSurfaces: [] };
    const config = { ...original, ...mapPropNavigation(zone.props, (x, z) => campaignGroundHeight(terrain, { x, y: 0, z })) };
    const site = REGIONAL_APOTHECARIES[id], host = zone.props.find((prop: { id: string }) => prop.id === `${id}_apothecary_station_visual`);
    const front = regionalWorksiteReservations(item, metadata[key])[1];
    const station = zone.craftingStations.find((station: { id: string }) => station.id === `${id}_apothecary_station`);
    const goals = [...site.entrance.map(([x, z]: number[]) => ({ x: host.x + x, z: host.z + z })), front, station];
    for (let segment = 1; segment < goals.length; segment++) {
      const a = goals[segment - 1], b = goals[segment], steps = Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) / .05);
      for (let i = 0; i <= steps; i++) {
        const t = steps ? i / steps : 0, point = { x: a.x + (b.x - a.x) * t, y: 0, z: a.z + (b.z - a.z) * t };
        point.y = campaignGroundHeight(config, point);
        expect(config.collision.some(collider => campaignColliderBlocksHeight(collider, point.y)
          && campaignColliderContains(collider, point, .5)), 'half-metre actor route').toBe(false);
      }
    }
    expect(campaignGroundHeight(config, { ...front, y: 0 })).toBeCloseTo(site.floorY, 5);
    const table = mapPropNavigation([item], () => 0).collision.find(collider => collider.maxY! > site.floorY + .8)!;
    expect(table).toBeDefined(); expect(campaignColliderBlocksHeight(table, site.floorY)).toBe(true);
    expect(campaignColliderContains(table, { ...table.footprint!, y: site.floorY }, .5)).toBe(true);
  });
}

test('stale or missing table/collision evidence leaves no invisible new blockers', () => {
  for (const id of ['sunmeadow_march', 'cinderfen_outskirts']) for (const fault of ['missing', 'stale', 'no-collision', 'changed-host']) {
    const assets = structuredClone(registry), data = structuredClone(metadata), site = REGIONAL_APOTHECARIES[id];
    if (fault === 'missing') assets.staticProps[key].model = 'unavailable-table.glb';
    if (fault === 'stale') data[key].modelSha256 = 'old';
    if (fault === 'no-collision') data[key].colliders = [];
    if (fault === 'changed-host') assets.staticProps[site.hostKey].modelSha256 = 'changed';
    const zone = integrateRegionalApothecaries(read(`public/assets/maps/${id}.json`), assets, data);
    expect(owned(zone)).toHaveLength(0);
  }
});
