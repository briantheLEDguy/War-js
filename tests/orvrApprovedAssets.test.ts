import { createHash, webcrypto } from 'node:crypto';
import { afterEach, describe, expect, test, vi } from 'vitest';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { AssetLoader } from '../src/game/AssetLoader';

const sha = (bytes: string | ArrayBuffer) => createHash('sha256').update(typeof bytes === 'string' ? bytes : new Uint8Array(bytes)).digest('hex');
function modelBytes(level: number, uris: string[] = []): ArrayBuffer {
  const json = JSON.stringify({ asset: { version: '2.0' }, extras: { level }, images: uris.map(uri => ({ uri })) });
  const text = new TextEncoder().encode(json + ' '.repeat((4 - json.length % 4) % 4));
  const bytes = new Uint8Array(20 + text.length), header = new DataView(bytes.buffer);
  [0x46546c67, 2, bytes.length, text.length, 0x4e4f534a].forEach((value, index) => header.setUint32(index * 4, value, true));
  bytes.set(text, 20); return bytes.buffer;
}
const baseEntry = { model: 'frontier_supply_wagon_lod0.glb', qc: 'frontier_supply_wagon.qc.json', lifecycleStatus: 'approved', reviewStatus: 'approved', runtimeReady: true };
const lods = [0, 1, 2].map(level => ({ level, model: `frontier_supply_wagon_lod${level}.glb`, sha256: sha(modelBytes(level)) }));

function install(qc: Record<string, unknown>, entry: Record<string, unknown> = {}, category = 'staticProps', key = 'frontier_supply_wagon', tamperQc = false, bytes: string | ArrayBuffer = modelBytes(0), textureBytes = 'reviewed pixels') {
  const text = JSON.stringify(qc);
  const record = { ...baseEntry, qcSha256: sha(text), ...entry };
  vi.stubGlobal('crypto', webcrypto);
  const fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('asset-index.json')) return new Response(JSON.stringify({ schemaVersion: 2, [category]: { [key]: record } }));
    if (url.includes('.qc.json')) return new Response(tamperQc ? `${text} ` : text);
    if (url.includes('/textures/')) return new Response(textureBytes, { headers: { 'content-type': 'image/png' } });
    return new Response(init?.method === 'HEAD' ? null : bytes, { headers: { 'content-type': 'model/gltf-binary' } });
  });
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('shared-campaign approved asset resolution', () => {
  test('accepts hashed approved level records in increasing LOD order', async () => {
    install({ qcPassed: true, validationErrors: 0, lods: [lods[2], lods[0], lods[1]] });
    const loader = new AssetLoader();
    await expect(loader.resolveApprovedAssetModels('frontier_supply_wagon', 'staticProps')).resolves.toEqual(lods.map(level => level.model));
    loader.dispose();
  });

  test('accepts the Battle Prelate builtLods QC shape without inventing missing validation errors', async () => {
    install({ qcPassed: true, builtLods: lods.map(level => ({ name: `LOD${level.level}`, model: level.model, sha256: level.sha256 })) }, {}, 'characterProfiles', 'civic_battle_prelate_m');
    const loader = new AssetLoader();
    await expect(loader.resolveApprovedAssetModels('civic_battle_prelate_m', 'characterProfiles')).resolves.toEqual(lods.map(level => level.model));
    loader.dispose();
  });

  test('keeps the reviewed NPC delivery as the highest available detail level', async () => {
    install({ qcPassed: true, validationErrors: 0, lods }, { model: lods[1].model }, 'characterProfiles', 'npc_riftspire_chaos');
    const loader = new AssetLoader();
    await expect(loader.resolveApprovedAssetModels('npc_riftspire_chaos', 'characterProfiles')).resolves.toEqual([lods[1].model, lods[2].model]);
    loader.dispose();
  });
  test('loads a published legacy NPC using its final registry approval and retained round-trip QC', async () => {
    const qc = { technicalRoundTripPassed: true, modelSha256: lods[0].sha256, invalidBounds: [],
      lifecycleStatus: 'draft', visualApprovalPassed: false,
      animationClips: ['idle','walk','run','death','jump','cast','combat_idle','attack_melee','attack_ranged'] };
    install(qc, { approvalState: 'approved', modelSha256: lods[0].sha256 }, 'characterProfiles', 'npc_aegis_guard');
    const loader = new AssetLoader();
    await expect(loader.resolveApprovedAssetModels('npc_aegis_guard', 'characterProfiles')).resolves.toEqual([lods[0].model]);
    loader.dispose();
    install({ ...qc, qcPassed: false }, { approvalState: 'approved', modelSha256: lods[0].sha256 }, 'characterProfiles', 'npc_aegis_guard');
    const failed = new AssetLoader();
    await expect(failed.resolveApprovedAssetModels('npc_aegis_guard', 'characterProfiles')).resolves.toEqual([]);
    failed.dispose();
    install(qc, { modelSha256: lods[0].sha256 }, 'characterProfiles', 'npc_aegis_guard');
    const unapproved = new AssetLoader();
    await expect(unapproved.resolveApprovedAssetModels('npc_aegis_guard', 'characterProfiles')).resolves.toEqual([]);
    unapproved.dispose();
  });

  test('resolves equipment aliases and variants without reusing a compatible result for a different skeleton', async () => {
    const qc = { qcPassed: true, validationErrors: 0, lods };
    const text = JSON.stringify(qc);
    const context = { bodyFamily: 'civic_battle_prelate_m', bodyVariant: 'm', skeletonId: 'humanoid_game_v2', bindPoseId: 'a_pose_v2' };
    install(qc, { model: undefined, variants: { m: { ...baseEntry, ...context, qcSha256: sha(text) } } }, 'equipment', 'starter_civic_humanoid_battle_prelate_chest_m');
    const loader = new AssetLoader();
    await expect(loader.resolveApprovedAssetModels('starter_civic_battle_prelate_chest_m', 'equipment', context)).resolves.toEqual(lods.map(level => level.model));
    await expect(loader.resolveApprovedAssetModels('starter_civic_battle_prelate_chest_m', 'equipment', { ...context, skeletonId: 'different' })).resolves.toEqual([]);
    await expect(loader.resolveApprovedAssetModels('starter_civic_battle_prelate_chest_m', 'equipment', { ...context, bodyVariant: 'f' })).resolves.toEqual([]);
    loader.dispose();
  });

  test('rejects a draft equipment variant inside an approved parent entry', async () => {
    const qc = { qcPassed: true, validationErrors: 0, lods };
    install(qc, { model: undefined, variants: { m: { ...baseEntry, reviewStatus: 'draft', qcSha256: sha(JSON.stringify(qc)) } } }, 'equipment', 'draft_armor');
    const loader = new AssetLoader();
    await expect(loader.resolveApprovedAssetModels('draft_armor', 'equipment', { bodyVariant: 'm' })).resolves.toEqual([]);
    loader.dispose();
  });

  test.each([
    { lifecycleStatus: 'draft' }, { reviewStatus: 'review' }, { runtimeReady: false },
    { runtimeReady: undefined }, { reviewStatus: undefined }, { lifecycleStatus: undefined },
  ])('requires every explicit frontier approval field: %j', async entry => {
    const fetch = install({ qcPassed: true, validationErrors: 0, lods }, entry);
    const loader = new AssetLoader();
    await expect(loader.resolveApprovedAssetModels('frontier_supply_wagon', 'staticProps')).resolves.toEqual([]);
    expect(fetch.mock.calls.some(([url]) => String(url).includes('.qc.json'))).toBe(false);
    loader.dispose();
  });

  test.each([
    { qcPassed: false, validationErrors: 0, lods },
    { qcPassed: true, validationErrors: 1, lods },
    { qcPassed: true, validationErrors: 0, lods: [{ ...lods[0], sha256: 'incorrect' }] },
    { qcPassed: true, validationErrors: 0, lods: [{ ...lods[0], model: '../outside.glb' }] },
    { qcPassed: true, validationErrors: 0, lods: [lods[1], lods[2]] },
  ])('rejects invalid or incomplete QC references', async qc => {
    install(qc);
    const loader = new AssetLoader();
    await expect(loader.resolveApprovedAssetModels('frontier_supply_wagon', 'staticProps')).resolves.toEqual([]);
    loader.dispose();
  });

  test('rejects a QC document whose bytes changed after approval', async () => {
    install({ qcPassed: true, validationErrors: 0, lods }, {}, 'staticProps', 'frontier_supply_wagon', true);
    const loader = new AssetLoader();
    await expect(loader.resolveApprovedAssetModels('frontier_supply_wagon', 'staticProps')).resolves.toEqual([]);
    loader.dispose();
  });

  test('registers model hashes so a changed GLB cannot load after valid QC resolution', async () => {
    install({ qcPassed: true, validationErrors: 0, lods }, {}, 'staticProps', 'frontier_supply_wagon', false, 'tampered');
    const parse = vi.spyOn(GLTFLoader.prototype, 'parseAsync');
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    const fallback = vi.fn(() => new THREE.Group());
    const loader = new AssetLoader();
    await loader.resolveApprovedAssetModels('frontier_supply_wagon', 'staticProps');
    const object = await loader.loadModel(lods[0].model, fallback);
    expect(parse).not.toHaveBeenCalled();
    expect(fallback).toHaveBeenCalledOnce();
    expect(object.children).toHaveLength(0);
    loader.dispose(object);
  });

  test('parses matching approved bytes and coalesces concurrent QC requests', async () => {
    const fetch = install({ qcPassed: true, validationErrors: 0, lods });
    const scene = new THREE.Group();
    const parse = vi.spyOn(GLTFLoader.prototype, 'parseAsync').mockResolvedValue({ scene, animations: [] } as never);
    const loader = new AssetLoader();
    await Promise.all([loader.resolveApprovedAssetModels('frontier_supply_wagon', 'staticProps'), loader.resolveApprovedAssetModels('frontier_supply_wagon', 'staticProps')]);
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('.qc.json'))).toHaveLength(1);
    await loader.loadModel(lods[0].model, () => new THREE.Group());
    expect(parse).toHaveBeenCalledOnce();
    loader.dispose();
  });

  test.each([1, 2])('verifies one reviewed texture used by %s image slots once and parses that exact blob', async imageSlots => {
    const uri = '../textures/sunmeadow_terrain/terrain.png', bytes = modelBytes(0, Array.from({ length: imageSlots }, () => uri));
    const externalTextures = [{ uri, sha256: sha('reviewed pixels') }];
    const fetch = install({ qcPassed: true, lods: [{ ...lods[0], sha256: sha(bytes), externalTextures }] }, {}, 'staticProps', 'frontier_supply_wagon', false, bytes);
    const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:reviewed-texture');
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
    const parse = vi.spyOn(GLTFLoader.prototype, 'parseAsync').mockImplementation(async function (this: GLTFLoader, _bytes, directory) {
      expect(this.manager.resolveURL(directory + uri)).toBe('blob:reviewed-texture');
      return { scene: new THREE.Group(), animations: [] } as never;
    });
    const loader = new AssetLoader();
    await loader.resolveApprovedAssetModels('frontier_supply_wagon', 'staticProps');
    await Promise.all([loader.loadModel(lods[0].model, () => new THREE.Group()), loader.loadModel(lods[0].model, () => new THREE.Group())]);
    expect(parse).toHaveBeenCalledOnce(); expect(create).toHaveBeenCalledOnce();
    expect(fetch.mock.calls.filter(([url]) => String(url).includes('/textures/'))).toHaveLength(1);
    loader.dispose(); expect(revoke).toHaveBeenCalledWith('blob:reviewed-texture');
  });

  test.each([true, false])('rejects changed or unreviewed external textures before parsing (declared=%s)', async declared => {
    const uri = '../textures/sunmeadow_terrain/terrain.png', bytes = modelBytes(0, [uri]);
    const externalTextures = declared ? [{ uri, sha256: sha('reviewed pixels') }] : undefined;
    install({ qcPassed: true, lods: [{ ...lods[0], sha256: sha(bytes), externalTextures }] }, {}, 'staticProps', 'frontier_supply_wagon', false, bytes, 'changed pixels');
    const parse = vi.spyOn(GLTFLoader.prototype, 'parseAsync');
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    const loader = new AssetLoader(), fallback = vi.fn(() => new THREE.Group());
    await loader.resolveApprovedAssetModels('frontier_supply_wagon', 'staticProps');
    await loader.loadModel(lods[0].model, fallback);
    expect(parse).not.toHaveBeenCalled(); expect(fallback).toHaveBeenCalledOnce();
    loader.dispose();
  });
});
