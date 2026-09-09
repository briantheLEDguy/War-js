/** Promote only the visually accepted cauldron, preserving every sibling asset. */
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { validateApprovedManifest } from '../../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
import { work, repo, key, hash, hashFile, read, save, validateRepair } from './validate_repair.mjs';

const inventory = await validateRepair(), inventoryHash = await hashFile(path.join(work, 'review/validated-inventory.json'));
const reviewFile = path.join(work, 'review/accepted-review.json');
if (process.argv.includes('--prepare')) {
  try { await fs.access(reviewFile); throw Error('A review already exists; retain its decision instead of overwriting it.'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  await save(reviewFile, { approved: false, reviewedBy: '', reviewedAt: '', inventorySha256: inventoryHash, images: inventory.images, notes: '' });
}
if (!process.argv.includes('--publish')) process.exit(0);
const review = await read(reviewFile), reviewHash = await hashFile(reviewFile);
assert.equal(review.approved, true); assert(review.reviewedBy && Number.isFinite(Date.parse(review.reviewedAt)));
assert.equal(review.inventorySha256, inventoryHash); assert.deepEqual(review.images, inventory.images);
const manifestFile = path.join(repo, 'scripts/blender-character-pipeline/data/approved-assets', key + '.approved.json');
const blueprintFile = path.join(repo, 'scripts/blender-character-pipeline/data/asset-blueprints', key + '.asset.json');
const manifest = await read(manifestFile), blueprint = await read(blueprintFile);
const original = await read(path.join(work, '../review/final_inventory.json'));
const baseline = original.assets.find(asset => asset.asset_id === key);
const lods = inventory.models.map(({ errors, warnings, ...lod }) => lod), primary = lods[0];
assert([baseline.lods[0].sha256, primary.sha256].includes(manifest.hashes.modelSha256), 'A different cauldron revision is already published');
for (const lod of lods) {
  const existing = await hashFile(path.join(repo, 'public/assets/models', lod.model));
  assert([baseline.lods[lod.level].sha256, lod.sha256].includes(existing), 'Public model changed outside this repair');
}
const relativeWork = path.relative(repo, work).replaceAll('\\', '/');
const provenance = { ...manifest.provenance, source: relativeWork + '/review/validated-inventory.json', sourceSha256: inventoryHash };
const preview = relativeWork + '/review/cauldron_lod0_ready.png';
const oldQc = await read(path.join(repo, 'public/assets/models', manifest.qc));
let qcHash;
for (const lod of lods) {
  const qc = { ...oldQc, modelSha256: lod.sha256, lod: lod.level, lods, validationErrors: 0, validationWarnings: 0,
    warningCodes: [], reviewHash, inventorySha256: inventoryHash, totalTris: lod.triangles,
    previewImages: Object.keys(inventory.images).map(image => relativeWork + '/' + image),
    fitReview: relativeWork + '/review/actual-export-review.json' };
  const bytes = Buffer.from(JSON.stringify(qc, null, 2) + '\n');
  await fs.copyFile(path.join(work, 'runtime', lod.model), path.join(repo, 'public/assets/models', lod.model));
  await save(path.join(repo, 'public/assets/models', lod.model.replace('.glb', '.qc.json')), qc);
  if (lod.level === 0) qcHash = hash(bytes);
}
blueprint.output.artifactDir = relativeWork + '/runtime';
blueprint.generator.copyFrom = relativeWork + '/runtime/' + primary.model;
blueprint.geometry.lods = blueprint.geometry.lods.map((lod, i) => ({ ...lod, triTarget: lods[i].triangles }));
blueprint.qc.maxTris = primary.triangles; blueprint.provenance = provenance;
blueprint.lifecycle = { status: 'approved', reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt,
  notes: 'Six original forged ornaments fitted to the final bowl at every LOD. Actual contacts, ready/pour views and unchanged animation/pivots/sockets verified. No liquid effects or crew added.' };
manifest.hashes = { modelSha256: primary.sha256, qcSha256: qcHash, previews: { assembly: inventory.images['review/cauldron_lod0_ready.png'] } };
manifest.previews = { assembly: preview }; manifest.review = { reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash };
manifest.provenance = provenance;
validateApprovedManifest(manifest, key);
await save(blueprintFile, blueprint); await save(manifestFile, manifest);
const metadataFile = path.join(work, '../builder-metadata.json'), metadata = await read(metadataFile);
metadata.assets[key] = { ...metadata.assets[key], modelSha256: primary.sha256, runtimeReady: true };
await save(metadataFile, metadata);
console.log('Published one reviewed cauldron with all three LODs; compile the registry and GM catalog next.');
