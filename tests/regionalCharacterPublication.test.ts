import fs from 'node:fs';
import path from 'node:path';
import { createHash, webcrypto } from 'node:crypto';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AssetLoader } from '../src/game/AssetLoader';
import { campaignEquipmentKeys, campaignNpcProfile } from '../src/game/network/CampaignCharacterPresentation';
import { WORLD_EDITOR_PREFABS } from '../src/world/editor/PrefabCatalog';

const publications = [{
  packageName: 'cinderfen-peat-worker', key: 'frontier_cinderfen_greenskin_peat_worker',
  assetId: 'chr.frontier.cinderfen.greenskin_peat_worker', zone: 'cinderfen_outskirts',
  npcId: 'cinderfen_outskirts_inhabitant_peat_worker', name: 'Barrek Reedhauler',
  race: 'greenskin', realm: 'riftbound',
}, {
  packageName: 'sunmeadow-farmer', key: 'frontier_sunmeadow_empire_farmer',
  assetId: 'chr.frontier.sunmeadow.empire_farmer', zone: 'sunmeadow_march',
  npcId: 'sunmeadow_march_inhabitant_homefield_farmer', name: 'Edric Hayward',
  race: 'empire', realm: 'aegis',
}] as const;
const clips = ['attack_melee', 'attack_ranged', 'cast', 'combat_idle', 'death', 'idle', 'jump', 'run', 'walk'];
const modelsRoot = path.resolve('public/assets/models');
const read = (filename: string) => JSON.parse(fs.readFileSync(filename, 'utf8'));
const sha = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
const registry = read(path.join(modelsRoot, 'asset-index.json'));
interface Receipt { sha256: string; bytes: number }
interface PublishedLod { level: number; model: string; sha256: string; triangles: number; externalTextures: unknown[] }

function installPublishedFetch(): AssetLoader {
  const publicRoot = path.resolve('public');
  vi.stubGlobal('crypto', webcrypto);
  vi.stubGlobal('fetch', async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost');
    const filename = path.resolve(publicRoot, '.' + decodeURIComponent(url.pathname));
    if (!filename.startsWith(publicRoot + path.sep) || !fs.existsSync(filename)) return new Response(null, { status: 404 });
    return new Response(init?.method === 'HEAD' ? null : fs.readFileSync(filename));
  });
  return new AssetLoader();
}

afterEach(() => vi.unstubAllGlobals());

describe.each(publications)('$key delivered regional character', publication => {
  const { key, packageName } = publication, profileKey = `npc_${key}`;
  const packagePath = `authoring/blender/${packageName}`;
  const approved = read(`scripts/blender-character-pipeline/data/approved-assets/${key}.approved.json`);
  const entry = registry.characterProfiles[profileKey];
  const qc = read(path.join(modelsRoot, approved.qc));

  it('binds the approved registry to all three literal delivered GLBs and their embedded nine-clip rigs', () => {
    expect(approved).toMatchObject({ approvalState: 'approved', assetId: publication.assetId,
      runtime: { profileKey, skinned: true } });
    expect(entry).toMatchObject({ assetId: publication.assetId, approvalState: 'approved', lifecycleStatus: 'approved',
      reviewStatus: 'approved', runtimeReady: true, skinned: true, model: approved.model, qc: approved.qc,
      modelSha256: approved.hashes.modelSha256, qcSha256: approved.hashes.qcSha256, ...approved.compatibility });
    expect(sha(fs.readFileSync(path.join(modelsRoot, approved.qc)))).toBe(approved.hashes.qcSha256);
    expect(qc.lods.map((lod: PublishedLod) => lod.level)).toEqual([0, 1, 2]);
    expect(qc.lods[0]).toMatchObject({ model: approved.model, sha256: approved.hashes.modelSha256 });
    expect(qc.builtLods).toEqual(qc.lods);
    const idleDurations: number[] = [];
    for (const lod of qc.lods as PublishedLod[]) {
      const bytes = fs.readFileSync(path.join(modelsRoot, lod.model));
      expect(sha(bytes), lod.model).toBe(lod.sha256);
      expect(bytes.readUInt32LE(0), lod.model).toBe(0x46546c67);
      expect(bytes.readUInt32LE(8), lod.model).toBe(bytes.length);
      const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
      expect(gltf.animations.map((clip: { name: string }) => clip.name).sort(), lod.model).toEqual(clips);
      expect(gltf.skins.length, lod.model).toBeGreaterThan(0);
      expect(gltf.nodes.some((node: { mesh?: number; skin?: number }) => node.mesh !== undefined && node.skin !== undefined)).toBe(true);
      expect(gltf.images.length, lod.model).toBeGreaterThan(0);
      for (const image of gltf.images) {
        expect(image.uri, lod.model).toBeUndefined();
        expect(Number.isInteger(image.bufferView), lod.model).toBe(true);
      }
      for (const clip of gltf.animations) {
        expect(clip.channels.length, `${lod.model}: ${clip.name}`).toBeGreaterThan(0);
        for (const channel of clip.channels) expect(gltf.nodes[channel.target.node], clip.name).toBeDefined();
      }
      const idle = gltf.animations.find((clip: { name: string }) => clip.name === 'idle');
      idleDurations.push(Math.max(...idle.samplers.map((sampler: { input: number }) => gltf.accessors[sampler.input].max[0])));
      const ownQc = read(path.join(modelsRoot, lod.model.replace(/\.glb$/, '.qc.json')));
      expect(ownQc).toMatchObject({ qcPassed: true, assetId: publication.assetId, modelSha256: lod.sha256, lod: lod.level,
        skeletonId: entry.skeletonId, bindPoseId: entry.bindPoseId, skinned: true, animationClips: clips,
        defaultAnimation: 'idle', validationErrors: 0, validationWarnings: 0, externalTextures: [] });
      expect(ownQc.lods).toEqual(qc.lods);
      expect(lod.externalTextures).toEqual([]);
    }
    expect(idleDurations[0]).toBeGreaterThan(0);
    for (const duration of idleDurations) expect(duration).toBeCloseTo(idleDurations[0], 6);
    expect(qc.lods[1].triangles).toBeLessThan(qc.lods[0].triangles);
    expect(qc.lods[2].triangles).toBeLessThan(qc.lods[1].triangles);
  });

  it('retains hash-matched authoring inputs, build receipts, source master and review evidence', () => {
    const release = path.resolve(qc.frozenSource);
    expect(qc.frozenSource).toBe(`${packagePath}/releases/${key}/${approved.review.reviewHash.slice(0, 20)}`);
    const reviewBytes = fs.readFileSync(path.join(release, 'review/visual_review.json'));
    expect(sha(reviewBytes)).toBe(approved.review.reviewHash);
    expect(qc.reviewHash).toBe(approved.review.reviewHash);
    const review = JSON.parse(reviewBytes.toString());
    expect(review).toMatchObject({ status: 'approved', evidence: { assetId: publication.assetId, profileKey } });
    expect(review.evidence).toEqual(qc.reviewEvidence);
    expect(review.evidence.models).toEqual(qc.lods.map(({ level, model, sha256 }: PublishedLod) => ({ level, model, sha256 })));
    const receipts = review.evidence.files as Record<string, Receipt>;
    const frozen = (relative: string) => path.join(release, 'files', ...relative.split(/[\\/]/));
    // Verify the retained release, not mutable authoring files that may start the next iteration.
    for (const [relative, receipt] of Object.entries(receipts)) {
      const bytes = fs.readFileSync(frozen(relative));
      expect(bytes.length, relative).toBe(receipt.bytes);
      expect(sha(bytes), relative).toBe(receipt.sha256);
    }
    const buildPath = `${packagePath}/review/${key}_build.json`;
    expect(receipts[buildPath]).toBeDefined();
    const build = read(frozen(buildPath));
    expect(build.key).toBe(key);
    expect(build.sourceFiles.length).toBeGreaterThan(0);
    for (const source of [...build.sourceFiles, ...build.validationSourceFiles ?? []]) {
      expect(receipts[source.path]?.sha256, source.path).toBe(source.sha256);
    }
    const master = `${packagePath}/sources/${key}.blend`;
    expect(receipts[master]?.sha256).toBe(build.masterSha256);
    expect(approved.provenance.sourceSha256).toBe(build.masterSha256);
    expect(path.resolve(approved.provenance.source)).toBe(frozen(master));
    for (const lod of qc.lods as PublishedLod[]) {
      const retained = receipts[`${packagePath}/runtime/${lod.model}`];
      expect(retained?.sha256, lod.model).toBe(lod.sha256);
      expect(build.lods.find((built: PublishedLod) => built.level === lod.level)).toMatchObject({ model: lod.model, sha256: lod.sha256, bytes: retained.bytes });
    }
    for (const [view, relative] of Object.entries(approved.previews) as Array<[string, string]>) {
      expect(sha(fs.readFileSync(path.resolve(...relative.split(/[\\/]/)))), view).toBe(approved.hashes.previews[view]);
    }
  });

  it('resolves the same approved LODs and own-rig metadata through the production loader and GM catalog', async () => {
    const loader = installPublishedFetch();
    try {
      expect(await loader.resolveApprovedAssetModels(profileKey, 'characterProfiles')).toEqual(qc.lods.map((lod: PublishedLod) => lod.model));
      const asset = await loader.resolveCharacterAsset(profileKey);
      expect(asset).toMatchObject({ assetId: publication.assetId, model: approved.model, ...approved.compatibility });
      expect(asset?.animationPack).toBeUndefined();
    } finally { loader.dispose(); }
    expect(campaignEquipmentKeys(profileKey)).toEqual([]);
    const metadata = read(`${packagePath}/builder-metadata.json`).assets[profileKey];
    expect(metadata).toMatchObject({ runtimeReady: true, modelSha256: approved.hashes.modelSha256, defaultAnimation: 'idle' });
    const prefabs = WORLD_EDITOR_PREFABS.filter(prefab => prefab.assetKey === profileKey);
    expect(prefabs).toHaveLength(1);
    const prefab = prefabs[0];
    expect(prefab.assetCategory).toBe('characterProfiles');
    expect([prefab.model, ...prefab.lodModels ?? []]).toEqual(qc.lods.map((lod: PublishedLod) => lod.model));
    expect(prefab.defaultAnimation).toBe('idle');
    expect(prefab.defaultScale).toEqual({ x: 1, y: 1, z: 1 });
    expect(prefab.footprint).toEqual(metadata.footprint);
    expect(prefab.colliders).toEqual(metadata.colliders);
    expect(prefab.cameraSolid).toBe(false);
  });

  it('places the approved character under its intended zone, NPC identity and racial presentation', () => {
    const zone = read(`public/assets/maps/${publication.zone}.json`);
    const matches = zone.npcs.filter((npc: { characterProfileKey?: string }) => npc.characterProfileKey === profileKey);
    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({ id: publication.npcId, name: publication.name, role: 'ambient', approvedOnly: true });
    expect(zone.orvrLayout.populationAssignments.filter((npc: { entityId: string }) => npc.entityId === publication.npcId))
      .toEqual([{ entityId: publication.npcId, race: publication.race, role: 'ambient', desiredProfileKey: profileKey, status: 'approved' }]);
    expect(campaignNpcProfile({ id: publication.npcId, role: 'ambient', profileKey, race: publication.race, realm: publication.realm })).toBe(profileKey);
  });
});
