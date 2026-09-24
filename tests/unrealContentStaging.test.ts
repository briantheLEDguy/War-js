import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { canonicalJson, sha256 } from '../scripts/unreal/content-contract';
import { stageDevelopmentContent } from '../scripts/unreal/stage-content';

describe('native content staging preserves arrival visuals', () => {
  let root: string;
  const previous = { source: { sha256: 'a'.repeat(64) }, maps: [{ id: 'aegis_capital',
    definition: { enemies: [{ id: 'target', model: 'dummy.glb' }] } }], developmentMaps: [] };
  const next = { ...previous, source: { sha256: 'b'.repeat(64) }, abilities: { changed: true } };
  const catalog = { schemaVersion: 1, productionAccepted: false, sourceContentSha256: previous.source.sha256,
    bindings: [{ purpose: 'training_dummy', zone: 'aegis_capital', entity: 'target', visualProp: 'target',
      sourceModel: 'dummy.glb', sourceSha256: sha256('model'), mesh: '/Game/Reviewed/Dummy.Dummy',
      materials: ['/Game/Reviewed/Wood.Wood'], collision: 'NoCollision', reviewState: 'development' }],
    packageHashes: { '/Game/Reviewed/Dummy': sha256('mesh'), '/Game/Reviewed/Wood': sha256('material') } };
  const filename = (name: string) => path.join(root, 'unreal/AegisWar/Content/Migration', name);
  const write = async (relative: string, value: string) => {
    const target = path.join(root, relative);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, value);
  };
  beforeEach(async () => {
    root = await mkdtemp(path.join(os.tmpdir(), 'war-staging-'));
    await write('public/assets/models/dummy.glb', 'model');
    await write('unreal/AegisWar/Content/Reviewed/Dummy.uasset', 'mesh');
    await write('unreal/AegisWar/Content/Reviewed/Wood.uasset', 'material');
    await write('unreal/AegisWar/Content/Migration/content.json', canonicalJson(previous));
    await writeFile(filename('world-visuals.json'), canonicalJson(catalog));
  });
  afterEach(async () => { await rm(root, { recursive: true, force: true }); });

  it('keeps training targets admitted after an unrelated ability export and on repeated staging', async () => {
    await stageDevelopmentContent(next, root);
    await stageDevelopmentContent(next, root);
    expect(JSON.parse(await readFile(filename('content.json'), 'utf8'))).toEqual(next);
    expect(JSON.parse(await readFile(filename('world-visuals.json'), 'utf8')))
      .toEqual({ ...catalog, sourceContentSha256: next.source.sha256 });
  });

  it.each(['map', 'source', 'mesh', 'material', 'missing-package', 'stale', 'missing-hash', 'duplicate', 'production', 'unsafe-path'])
    ('rejects %s drift without replacing either live catalog', async (change) => {
      const candidate = structuredClone(next), review = structuredClone(catalog);
      if (change === 'map') candidate.maps[0].definition.enemies[0].model = 'substitute.glb';
      if (change === 'source') await write('public/assets/models/dummy.glb', 'changed');
      if (change === 'mesh') await write('unreal/AegisWar/Content/Reviewed/Dummy.uasset', 'changed');
      if (change === 'material') await write('unreal/AegisWar/Content/Reviewed/Wood.uasset', 'changed');
      if (change === 'missing-package') await rm(path.join(root, 'unreal/AegisWar/Content/Reviewed/Dummy.uasset'));
      if (change === 'stale') review.sourceContentSha256 = 'c'.repeat(64);
      if (change === 'missing-hash') review.bindings[0].mesh = '/Game/Unreviewed/Dummy.Dummy';
      if (change === 'duplicate') review.bindings.push(review.bindings[0]);
      if (change === 'production') review.productionAccepted = true;
      if (change === 'unsafe-path') review.bindings[0].sourceModel = '../dummy.glb';
      await writeFile(filename('world-visuals.json'), canonicalJson(review));
      await expect(stageDevelopmentContent(candidate, root)).rejects.toThrow();
      expect(await readFile(filename('content.json'), 'utf8')).toBe(canonicalJson(previous));
      expect(await readFile(filename('world-visuals.json'), 'utf8')).toBe(canonicalJson(review));
    });

  it('allows first-time staging without inventing world visual approval', async () => {
    await rm(filename('world-visuals.json'));
    await rm(filename('content.json'));
    await stageDevelopmentContent(next, root);
    expect(JSON.parse(await readFile(filename('content.json'), 'utf8'))).toEqual(next);
    await expect(readFile(filename('world-visuals.json'))).rejects.toMatchObject({ code: 'ENOENT' });
  });
});
