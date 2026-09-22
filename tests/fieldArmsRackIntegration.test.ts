import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { Box3, Matrix4, Quaternion, Vector3 } from 'three';
import { expect, test } from 'vitest';
import { WORLD_EDITOR_PREFABS } from '../shared/world/editor/PrefabCatalog';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { campaignGroundHeight } from '../shared/orvr/navigation';
import type { PropSpawn } from '../shared/world/ZoneDefinition';
import { modelTriangles } from './helpers/staticGlbGeometry';

const key = 'frontier_field_arms_rack', packagePath = 'authoring/blender/field-arms-rack';
const read = (file: string) => JSON.parse(fs.readFileSync(file, 'utf8'));
const sha = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
const registry = read('public/assets/models/asset-index.json');
const owned = (zone: { id: string; props: PropSpawn[] }) => zone.props.filter(prop =>
  prop.assetKey === key && prop.id?.startsWith(`${zone.id}_delivered_`));

test('the arms rack retains literal three-LOD exports, editable masters and matching GM collision', () => {
  const approved = read(`scripts/blender-character-pipeline/data/approved-assets/${key}.approved.json`);
  const qc = read(`public/assets/models/${approved.qc}`), metadata = read(`${packagePath}/builder-metadata.json`).assets[key];
  expect(registry.staticProps[key]).toMatchObject({ assetId: 'prop.frontier.field_arms_rack',
    runtimeReady: true, approvalState: 'approved', modelSha256: approved.hashes.modelSha256,
    qcSha256: approved.hashes.qcSha256 });
  expect(sha(fs.readFileSync(`public/assets/models/${approved.qc}`))).toBe(approved.hashes.qcSha256);
  expect(qc.lods.map((lod: { level: number }) => lod.level)).toEqual([0, 1, 2]);
  for (const lod of qc.lods) {
    const bytes = fs.readFileSync(`public/assets/models/${lod.model}`);
    expect(sha(bytes)).toBe(lod.sha256);
    const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
    expect(gltf.meshes).toHaveLength(5); expect(gltf.materials).toHaveLength(5);
    expect(gltf.images.length).toBeGreaterThanOrEqual(15);
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
  const frozen = (relative: string) => read(`${qc.frozenSource}/files/${packagePath}/${relative}`);
  expect(frozen('review/master-audit.json').records).toHaveLength(6);
  const construction = frozen('review/construction-contacts.json');
  expect(construction.passed).toBe(true);
  expect(construction.records.flatMap((record: { contacts: unknown[] }) => record.contacts)).toHaveLength(162);
  const prefabs = WORLD_EDITOR_PREFABS.filter(entry => entry.assetKey === key);
  expect(prefabs).toHaveLength(1);
  expect([prefabs[0].model, ...prefabs[0].lodModels ?? []]).toEqual(qc.lods.map((lod: { model: string }) => lod.model));
  expect(prefabs[0].colliders).toEqual(metadata.colliders);
  expect(prefabs[0].walkableSurfaces).toEqual([]); expect(prefabs[0].cameraSolid).toBe(true);
  expect(prefabs[0].defaultScale).toEqual({ x: 1, y: 1, z: 1 });
});

test('all 36 keeps have the universal rack with supported skids and the published collider contract', async () => {
  const metadata = read(`${packagePath}/builder-metadata.json`).assets[key];
  const configs = await loadCampaignMapConfigs();
  let total = 0;
  for (const config of configs.filter(config => config.keeps.length)) {
    const zone = read(`public/assets/maps/${config.id}.json`), racks = owned(zone);
    expect(racks, config.id).toHaveLength(2);
    for (const keep of config.keeps) {
      const rack = racks.find(rack => rack.id === `${config.id}_delivered_${keep.realm}_arms_rack`)!;
      expect(rack).toBeDefined(); expect(rack.model).toBe(registry.staticProps[key].model);
      expect(rack.colliders).toEqual(metadata.colliders); expect(rack.colliderSpace).toBe('model');
      const y = rack.heightMode === 'absolute' ? rack.y ?? 0 : campaignGroundHeight(config, { ...rack, y: 0 });
      for (const dx of [-.71, .71]) for (const dz of [-.34, .34]) {
        const ground = campaignGroundHeight(config, { x: rack.x + dx, y, z: rack.z + dz });
        expect(Math.abs(ground - y), `${rack.id} skid ${dx}/${dz}`).toBeLessThan(.009);
      }
      total++;
    }
  }
  expect(total).toBe(36);
});

for (const id of ['sunmeadow_march', 'cinderfen_outskirts']) {
  test(`${id}: arms racks clear actual nearby wall, stair and furnishing triangles`, () => {
    const zone = read(`public/assets/maps/${id}.json`), racks = owned(zone);
    const metadata = read(`${packagePath}/builder-metadata.json`).assets[key];
    expect(racks).toHaveLength(2);
    const meshes = new Map<string, ReturnType<typeof modelTriangles>>();
    for (const rack of racks) {
      const { minimum: lo, maximum: hi } = metadata.boundsYUp;
      const volume = new Box3(new Vector3(rack.x + lo[0], (rack.y ?? 0) + .02, rack.z + lo[2]),
        new Vector3(rack.x + hi[0], (rack.y ?? 0) + hi[1], rack.z + hi[2]));
      for (const prop of zone.props as PropSpawn[]) {
        if (prop.id === rack.id || prop.visible === false || !prop.colliders?.length
          || Math.hypot(prop.x - rack.x, prop.z - rack.z) > 40) continue;
        const model = prop.model ?? (prop.assetKey ? registry.staticProps[prop.assetKey]?.model : undefined);
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
        }), `${rack.id} clears ${prop.id}`).toBe(false);
      }
    }
  });
}
