import fs from 'node:fs';
import path from 'node:path';
import { createHash, webcrypto } from 'node:crypto';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AssetLoader } from '../src/game/AssetLoader';
import { WORLD_EDITOR_PREFABS } from '../src/world/editor/PrefabCatalog';

const assets = ['frontier_siege_repair_bench', 'frontier_siege_ammunition_cradle'] as const;
const modelsRoot = path.resolve('public/assets/models');
const read = (filename: string) => JSON.parse(fs.readFileSync(filename, 'utf8'));
const sha = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
const registry = read(path.join(modelsRoot, 'asset-index.json'));
const contract = read('authoring/blender/frontier-workshop-items/builder-contract.json');
interface TextureReference { uri: string; sha256: string }
interface PublishedLod { level: number; model: string; sha256: string; bytes: number; externalTextures?: TextureReference[] }

afterEach(() => vi.unstubAllGlobals());

describe.each(assets)('%s delivered workshop asset', assetKey => {
  it('signs every actual external image at every published LOD so runtime loading accepts it', () => {
    const approved = read(`scripts/blender-character-pipeline/data/approved-assets/${assetKey}.approved.json`);
    const qcBytes = fs.readFileSync(path.join(modelsRoot, approved.qc));
    const qc = JSON.parse(qcBytes.toString());
    expect(approved.approvalState).toBe('approved');
    expect(sha(qcBytes)).toBe(approved.hashes.qcSha256);
    expect(qc.qcPassed).toBe(true);
    expect(qc.lods.map((lod: PublishedLod) => lod.level)).toEqual([0, 1, 2]);
    expect(qc.lods[0].model).toBe(approved.model);
    expect(qc.lods[0].sha256).toBe(approved.hashes.modelSha256);

    for (const lod of qc.lods as PublishedLod[]) {
      const bytes = fs.readFileSync(path.join(modelsRoot, lod.model));
      expect(bytes.byteLength, lod.model).toBe(lod.bytes);
      expect(sha(bytes), lod.model).toBe(lod.sha256);
      const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
      const imageUris = gltf.images.map((image: { uri?: string; bufferView?: number }) => {
        expect(image.bufferView, lod.model).toBeUndefined();
        expect(image.uri, lod.model).toMatch(/^\.\.\/textures\/frontier_workshop_items\/[a-f0-9]{64}\.png$/);
        return image.uri as string;
      });
      expect(imageUris.length).toBeGreaterThan(0);
      // This is the runtime trust boundary that previously rejected all six GLBs.
      expect(Array.isArray(lod.externalTextures), `${lod.model}: missing signed runtime texture references`).toBe(true);
      const references = lod.externalTextures!;
      expect(references.map(reference => reference.uri).sort()).toEqual([...new Set(imageUris)].sort());
      for (const reference of references) {
        const texture = fs.readFileSync(path.resolve(modelsRoot, reference.uri));
        expect(sha(texture), `${lod.model}: ${reference.uri}`).toBe(reference.sha256);
      }
      const ownQc = read(path.join(modelsRoot, lod.model.replace(/\.glb$/, '.qc.json')));
      expect(ownQc.qcPassed).toBe(true);
      expect(ownQc.modelSha256).toBe(lod.sha256);
      expect(ownQc.lods.find((entry: PublishedLod) => entry.level === lod.level)?.externalTextures).toEqual(lod.externalTextures);
    }
  });

  it('resolves approved LODs through AssetLoader and exposes the same measured collision in GM', async () => {
    const publicRoot = path.resolve('public');
    vi.stubGlobal('crypto', webcrypto);
    vi.stubGlobal('fetch', async (input: RequestInfo | URL) => {
      const url = new URL(String(input), 'http://localhost');
      const filename = path.resolve(publicRoot, '.' + decodeURIComponent(url.pathname));
      if (!filename.startsWith(publicRoot + path.sep) || !fs.existsSync(filename)) return new Response(null, { status: 404 });
      return new Response(fs.readFileSync(filename));
    });
    const entry = registry.staticProps[assetKey];
    expect(entry).toMatchObject({ approvalState: 'approved', lifecycleStatus: 'approved', reviewStatus: 'approved', runtimeReady: true });
    const qc = read(path.join(modelsRoot, entry.qc));
    const loader = new AssetLoader();
    try {
      expect(await loader.resolveApprovedAssetModels(assetKey, 'staticProps')).toEqual(qc.lods.map((lod: PublishedLod) => lod.model));
    } finally { loader.dispose(); }
    const prefabs = WORLD_EDITOR_PREFABS.filter(prefab => prefab.assetKey === assetKey);
    expect(prefabs).toHaveLength(1);
    const prefab = prefabs[0], measured = contract.assets[assetKey];
    expect(prefab.assetCategory).toBe('staticProps');
    expect(prefab.model).toBe(entry.model);
    expect([prefab.model, ...prefab.lodModels ?? []]).toEqual(qc.lods.map((lod: PublishedLod) => lod.model));
    expect(prefab.defaultScale).toEqual({ x: 1, y: 1, z: 1 });
    expect(prefab.colliderSpace).toBe('model');
    expect(prefab.colliders!.length).toBeGreaterThan(1);
    // JSON generation canonicalizes measured negative zero to ordinary zero.
    expect(prefab.colliders).toEqual(JSON.parse(JSON.stringify(measured.colliders)));
    expect(prefab.footprint).toEqual(measured.footprint);
  });
});
