/** Stage review evidence; replace accepted trees only after explicit hash-bound approval. */
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { validateApprovedManifest } from '../../../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
import { collectReviewEvidence, sha, read, fileSha } from './review_evidence.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repo = path.resolve(root, '../../../../..');
const relative = path.relative(repo, root).replaceAll('\\', '/');
const save = (file, value) => fs.writeFile(file, JSON.stringify(value, null, 2) + '\n');
await import('./validate_nature.mjs');
assert(!process.exitCode, 'Technical validation failed');
const { assets } = await read(path.join(root, 'review/validation.json'));
const evidence = new Map();
for (const asset of assets) evidence.set(asset.asset, await collectReviewEvidence(root, asset, assets));
const reviewPath = path.join(root, 'review/visual_review.json');
if (process.argv.includes('--prepare-review')) {
  let previous = { assets: {} };
  try { previous = await read(reviewPath); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const records = {};
  for (const asset of assets) {
    const fresh = evidence.get(asset.asset), old = previous.assets[asset.asset];
    const unchanged = old && Object.entries(fresh).every(([key, value]) => JSON.stringify(old[key]) === JSON.stringify(value));
    records[asset.asset] = { ...fresh, status: unchanged ? old.status : 'pending', reviewedBy: unchanged ? old.reviewedBy : '',
      reviewedAt: unchanged ? old.reviewedAt : '', notes: unchanged ? old.notes : 'Inspect all LODs plus 30m/90m ground-height continuity; no approval inferred from technical validation.' };
  }
  await save(reviewPath, { schemaVersion: 1, kind: 'actual_glb_canopy_revision_review', assets: records });
  console.log('Prepared hash-bound canopy revision review. Original accepted package remains unchanged.');
}
if (!process.argv.includes('--publish')) process.exit(0);

const reviewBytes = await fs.readFile(reviewPath), review = JSON.parse(reviewBytes), reviewHash = sha(reviewBytes);
const changes = [];
for (const asset of assets) {
  const approved = review.assets[asset.asset];
  assert.equal(approved?.status, 'approved', `${asset.asset}: explicit internal visual approval required`);
  assert(approved.reviewedBy && Number.isFinite(Date.parse(approved.reviewedAt)), 'Reviewer and date required');
  for (const [key, value] of Object.entries(evidence.get(asset.asset))) assert.deepEqual(approved[key], value, `Reviewed ${key} changed`);
  const blueprintPath = path.join(repo, 'scripts/blender-character-pipeline/data/asset-blueprints', `${asset.asset}.asset.json`);
  const blueprint = await read(blueprintPath), renders = await read(path.join(root, 'review', `${asset.asset}_renders.json`));
  assert.equal(blueprint.runtime.staticKey, asset.asset);
  blueprint.version = '1.1.0';
  blueprint.output.artifactDir = `${relative}/runtime`;
  blueprint.generator.copyFrom = `${relative}/runtime/${asset.lods[0].model}`;
  blueprint.provenance.source = `${relative}/source/design.json`;
  blueprint.provenance.sourceSha256 = await fileSha(path.join(root, 'source/design.json'));
  blueprint.provenance.referencePackId = 'sunmeadow_canopy_v2_ground_view';
  blueprint.geometry.lods.forEach((lod, level) => { lod.triTarget = asset.lods[level].triangles; });
  blueprint.qc.maxTris = asset.lods[0].triangles;
  blueprint.qc.expectedHeightM = asset.lods[0].bounds_runtime.max[1] - asset.lods[0].bounds_runtime.min[1];
  blueprint.lifecycle = { status: 'approved', reviewedBy: approved.reviewedBy, reviewedAt: approved.reviewedAt,
    notes: `Canopy revision reviewed at 30m/90m and all delivered LODs. ${asset.limitations.join(' ')}` };
  const lods = asset.lods.map(l => ({ level: l.level, model: l.model, sha256: l.sha256, triangles: l.triangles }));
  const previews = renders.renders.map(r => `${relative}/${r.image.replaceAll('\\', '/')}`);
  previews.push(`${relative}/review/gameplay_group_30m_lod1.png`, `${relative}/review/gameplay_group_90m_lod2.png`, `${relative}/review/exports_contact_sheet.png`);
  const qcFiles = asset.lods.map(lod => ({ filename: lod.model.replace('.glb', '.qc.json'), bytes: Buffer.from(JSON.stringify({
    qcPassed: true, assetId: blueprint.assetId, modelSha256: lod.sha256, lod: lod.level, lods, builtLods: lods,
    validationErrors: 0, validationWarnings: lod.validationWarnings, reviewHash, bounds: lod.bounds_runtime,
    limitations: asset.limitations, previewImages: previews, reviewEvidence: evidence.get(asset.asset),
  }, null, 2) + '\n') }));
  const preview = renders.renders.find(r => r.level === 0 && r.view === 'studio');
  const manifest = { schemaVersion: 1, assetId: blueprint.assetId, displayName: blueprint.displayName, category: 'prop',
    model: asset.lods[0].model, qc: qcFiles[0].filename, runtime: blueprint.runtime,
    compatibility: { bodyFamily: 'static_architecture', bodyVariant: 'neutral', skeletonId: 'none', bindPoseId: 'none' },
    hashes: { modelSha256: asset.lods[0].sha256, qcSha256: sha(qcFiles[0].bytes), previews: { assembly: preview.image_sha256 } },
    previews: { assembly: `${relative}/${preview.image.replaceAll('\\', '/')}` },
    review: { reviewedBy: approved.reviewedBy, reviewedAt: approved.reviewedAt, reviewHash }, provenance: blueprint.provenance, approvalState: 'approved' };
  validateApprovedManifest(manifest, `${asset.asset} canopy revision`);
  changes.push({ asset, blueprintPath, blueprint, qcFiles, manifest });
}

// Preserve old public bytes and their approval records as a content-addressed
// archive before replacing them. Original Blender sources remain untouched.
const publicDir = path.join(repo, 'public/assets/models');
const approvedDir = path.join(repo, 'scripts/blender-character-pipeline/data/approved-assets');
const writes = [];
for (const item of changes) {
  for (const lod of item.asset.lods) writes.push([path.join(publicDir, lod.model), await fs.readFile(path.join(root, 'runtime', lod.model))]);
  for (const qc of item.qcFiles) writes.push([path.join(publicDir, qc.filename), qc.bytes]);
  writes.push([item.blueprintPath, Buffer.from(JSON.stringify(item.blueprint, null, 2) + '\n')]);
  writes.push([path.join(approvedDir, `${item.asset.asset}.approved.json`), Buffer.from(JSON.stringify(item.manifest, null, 2) + '\n')]);
}
const archive = path.join(root, 'previous-accepted');
await fs.mkdir(archive, { recursive: true });
const archiveEntries = [];
for (const [file] of writes) {
  const bytes = await fs.readFile(file), hash = sha(bytes), target = `${hash}-${path.basename(file)}`;
  try { await fs.writeFile(path.join(archive, target), bytes, { flag: 'wx' }); } catch (error) { if (error.code !== 'EEXIST') throw error; }
  archiveEntries.push({ path: path.relative(repo, file).replaceAll('\\', '/'), archived: target, sha256: hash });
}
await save(path.join(archive, `publication-${reviewHash}.json`), archiveEntries);
for (const [file, bytes] of writes) await fs.writeFile(file, bytes);
console.log('Published three approved canopy revisions; old public bytes/records archived. Registry remains uncompiled.');
