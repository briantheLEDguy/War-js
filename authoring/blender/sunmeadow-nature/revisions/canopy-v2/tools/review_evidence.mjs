import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

export const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
export const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));
export const fileSha = async file => sha(await fs.readFile(file));

/** Bind every displayed LOD and gameplay-distance view to the delivered bytes. */
export async function collectReviewEvidence(root, asset, allAssets) {
  const renders = await read(path.join(root, 'review', `${asset.asset}_renders.json`));
  assert.deepEqual(renders.renders.map(r => `${r.level}:${r.view}`).sort(),
    ['0:ground', '0:studio', '1:ground', '1:studio', '2:ground', '2:studio'], 'Six actual export views required');
  for (const render of renders.renders) {
    const lod = asset.lods[render.level];
    assert.equal(path.resolve(render.model), path.join(root, 'runtime', lod.model), 'Unexpected rendered model');
    assert.equal(render.model_sha256, lod.sha256, 'A render depicts an older GLB');
    assert.equal(await fileSha(render.model), lod.sha256, 'Rendered binary changed');
    assert.equal(await fileSha(path.join(root, render.image)), render.image_sha256, 'Rendered image changed');
  }
  const groupPath = path.join(root, 'review/gameplay_group_receipt.json');
  const groups = await read(groupPath);
  assert.deepEqual(groups.views.map(v => [v.distance_metres, v.lod]), [[30, 1], [90, 2]], '30m/90m review required');
  for (const view of groups.views) {
    assert.equal(view.camera_height, 1.7, 'Ground-height camera required');
    assert.deepEqual(view.models.map(m => path.basename(m.model)).sort(), allAssets.map(a => a.lods[view.lod].model).sort(), 'Complete tree group required');
    for (const model of view.models) {
      const lod = allAssets.flatMap(a => a.lods).find(l => l.model === path.basename(model.model));
      assert.equal(model.sha256, lod.sha256, 'Group depicts an older GLB');
      assert.equal(await fileSha(path.join(root, model.model)), lod.sha256, 'Group binary changed');
    }
    assert.equal(await fileSha(path.join(root, view.image)), view.image_sha256, 'Group image changed');
  }
  const sheetPath = path.join(root, 'review/exports_contact_sheet.json');
  const sheet = await read(sheetPath);
  assert.equal(await fileSha(path.join(root, 'review', sheet.image)), sheet.image_sha256, 'Contact sheet changed');
  assert.deepEqual(sheet.sources.map(s => `${s.asset}:${s.level}`).sort(), allAssets.flatMap(a => a.lods.map(l => `${a.asset}:${l.level}`)).sort(), 'Complete metric comparison required');
  for (const source of sheet.sources) {
    const lod = allAssets.find(a => a.asset === source.asset).lods[source.level];
    assert.equal(source.model_sha256, lod.sha256, 'Contact sheet depicts an older GLB');
    assert.equal(await fileSha(path.join(root, source.source_image)), source.source_image_sha256, 'Contact source image changed');
    assert(source.pixels_per_metre > 0, 'Metric scale required');
  }
  return {
    buildSha256: await fileSha(path.join(root, 'review', `${asset.asset}_build.json`)),
    modelSha256s: asset.lods.map(l => l.sha256),
    previewSha256s: Object.fromEntries(renders.renders.map(r => [r.image, r.image_sha256])),
    gameplayReceiptSha256: await fileSha(groupPath),
    contactSheetReceiptSha256: await fileSha(sheetPath),
    contactSheetSha256: sheet.image_sha256,
  };
}
