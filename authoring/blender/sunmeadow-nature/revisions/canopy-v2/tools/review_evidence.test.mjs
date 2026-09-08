import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { collectReviewEvidence, sha } from './review_evidence.mjs';

async function fixture(t) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'canopy-review-'));
  t.after(() => fs.rm(root, { recursive: true }));
  await fs.mkdir(path.join(root, 'review')); await fs.mkdir(path.join(root, 'runtime'));
  const save = (file, value) => fs.writeFile(path.join(root, file), JSON.stringify(value));
  const asset = { asset: 'tree', lods: [] }, renders = [];
  for (const level of [0, 1, 2]) {
    const bytes = Buffer.from(`model ${level}`), model = `tree_lod${level}.glb`;
    await fs.writeFile(path.join(root, 'runtime', model), bytes);
    asset.lods.push({ level, model, sha256: sha(bytes) });
    for (const view of ['studio', 'ground']) {
      const image = `review/${level}_${view}.png`, imageBytes = Buffer.from(image);
      await fs.writeFile(path.join(root, image), imageBytes);
      renders.push({ level, view, model: path.join(root, 'runtime', model), model_sha256: sha(bytes), image, image_sha256: sha(imageBytes) });
    }
  }
  await save('review/tree_build.json', { original: true }); await save('review/tree_renders.json', { renders });
  const groups = { views: [] };
  for (const [distance, lod] of [[30, 1], [90, 2]]) {
    const image = `review/group_${distance}.png`, bytes = Buffer.from(image);
    await fs.writeFile(path.join(root, image), bytes);
    groups.views.push({ distance_metres: distance, lod, camera_height: 1.7,
      models: [{ model: `runtime/${asset.lods[lod].model}`, sha256: asset.lods[lod].sha256 }], image, image_sha256: sha(bytes) });
  }
  await save('review/gameplay_group_receipt.json', groups);
  const sheetBytes = Buffer.from('sheet'); await fs.writeFile(path.join(root, 'review/sheet.png'), sheetBytes);
  const sheet = { image: 'sheet.png', image_sha256: sha(sheetBytes), sources: renders.filter(r => r.view === 'studio').map(r => ({
    asset: 'tree', level: r.level, model_sha256: r.model_sha256, source_image: r.image, source_image_sha256: r.image_sha256, pixels_per_metre: 20,
  })) };
  await save('review/exports_contact_sheet.json', sheet);
  return { root, asset, renders, groups, sheet, save, collect: () => collectReviewEvidence(root, asset, [asset]) };
}

test('complete actual-model and metric-distance evidence can be prepared', async t => {
  const f = await fixture(t), evidence = await f.collect();
  assert.equal(evidence.modelSha256s.length, 3); assert.equal(Object.keys(evidence.previewSha256s).length, 6);
});
test('rejects a replaced model behind unchanged review images', async t => {
  const f = await fixture(t); await fs.writeFile(path.join(f.root, 'runtime/tree_lod1.glb'), 'replaced');
  await assert.rejects(f.collect(), /Rendered binary changed/);
});
test('rejects a ground-group image altered after rendering', async t => {
  const f = await fixture(t); await fs.writeFile(path.join(f.root, f.groups.views[1].image), 'edited');
  await assert.rejects(f.collect(), /Group image changed/);
});
test('rejects missing ground LOD views even when studio views exist', async t => {
  const f = await fixture(t); await f.save('review/tree_renders.json', { renders: f.renders.filter(r => r.view !== 'ground') });
  await assert.rejects(f.collect(), /Six actual export views required/);
});
test('rejects stale contact-sheet source bindings', async t => {
  const f = await fixture(t); f.sheet.sources[1].model_sha256 = 'old'; await f.save('review/exports_contact_sheet.json', f.sheet);
  await assert.rejects(f.collect(), /Contact sheet depicts an older GLB/);
});
