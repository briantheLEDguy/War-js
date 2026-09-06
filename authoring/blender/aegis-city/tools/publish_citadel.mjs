// Promote only the reviewed keep; leave every other city's asset record untouched.
import { readFile, writeFile, copyFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
const { default: validator } = await import('gltf-validator').catch(() => import('../.deps/node_modules/gltf-validator/index.js'));

const work = fileURLToPath(new URL('../', import.meta.url));
const root = path.resolve(work, '../../..');
const read = async file => JSON.parse(await readFile(file, 'utf8'));
const write = (file, data) => writeFile(file, JSON.stringify(data, null, 2) + '\n');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const sha = async file => hash(await readFile(file));
const asset = (await read(path.join(work, 'build-report.json'))).find(asset => asset.kind === 'citadel');
assert.deepEqual(asset.lods.map(lod => lod.level), [0, 1, 2]);
const results = [];
const textures = new Set();
for (const lod of asset.lods) {
  const source = path.join(work, 'runtime', lod.model);
  const bytes = await readFile(source);
  assert.equal(hash(bytes), lod.sha256, 'Build hash mismatch');
  const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
  const triangles = doc.meshes.reduce((sum, mesh) => sum + mesh.primitives.reduce((n, p) => n + doc.accessors[p.indices].count / 3, 0), 0);
  assert.equal(triangles, lod.triangles);
  assert(triangles <= 30000 && (!lod.level || triangles < asset.lods[lod.level - 1].triangles));
  for (const mesh of doc.meshes) for (const p of mesh.primitives) {
    assert(p.attributes.TEXCOORD_0 !== undefined && p.attributes.NORMAL !== undefined);
  }
  for (const image of doc.images ?? []) {
    assert(/^\.\.\/textures\/aegis_city\/[a-f0-9]+\.png$/.test(image.uri), 'Expected shared city texture');
    textures.add(image.uri);
  }
  const result = await validator.validateBytes(new Uint8Array(bytes), {
    uri: lod.model,
    externalResourceFunction: async uri => new Uint8Array(await readFile(path.resolve(work, 'runtime', uri))),
  });
  results.push({ model: lod.model, sha256: lod.sha256, triangles,
    errors: result.issues.messages.filter(message => message.severity === 0), warnings: result.issues.numWarnings });
}
await write(path.join(work, 'review/citadel-validation.json'), results);
assert(results.every(result => result.errors.length === 0), 'GLB validation failed');
console.log('Validated three citadel LODs:', results.map(r => r.triangles).join(' / '), 'triangles');

if (process.argv.includes('--publish')) {
  const reviewFile = path.join(work, 'review/citadel-gothic-review.json');
  const review = await read(reviewFile);
  assert(review.reviewedBy && review.reviewedAt && review.observations);
  assert.deepEqual(review.modelSha256s, asset.lods.map(lod => lod.sha256), 'Review is stale');
  for (const [name, expected] of Object.entries(review.previewSha256s)) {
    assert.equal(await sha(path.join(work, 'review', name)), expected, 'Preview changed after review');
  }
  assert(review.previewSha256s['citadel-gothic.png'] && review.previewSha256s['citadel-gothic-lod2.png']);
  const reviewHash = await sha(reviewFile);
  for (const uri of textures) {
    await copyFile(path.resolve(work, 'runtime', uri), path.resolve(root, 'public/assets/models', uri));
  }
  for (const lod of asset.lods) {
    await copyFile(path.join(work, 'runtime', lod.model), path.join(root, 'public/assets/models', lod.model));
    await write(path.join(root, 'public/assets/models', lod.model.replace('.glb', '.qc.json')), {
      qcPassed: true, assetId: 'prop.aegis.citadel', modelSha256: lod.sha256,
      lod, lods: asset.lods, validationErrors: 0, reviewHash, textureMaxDimension: 2048,
    });
  }
  const bpFile = path.join(root, 'scripts/blender-character-pipeline/data/asset-blueprints/prop_aegis_citadel.asset.json');
  const bp = await read(bpFile);
  bp.geometry.lods = asset.lods.map(lod => ({ name: `LOD${lod.level}`, triTarget: lod.triangles,
    screenCoverageMin: [.2, .08, 0][lod.level] }));
  bp.provenance.promptIds = [...new Set([...bp.provenance.promptIds, 'citadel_gothic_spires_v2'])];
  await write(bpFile, bp);
  const approvalFile = path.join(root, 'scripts/blender-character-pipeline/data/approved-assets/prop_aegis_citadel.approved.json');
  const approval = await read(approvalFile);
  approval.hashes = { modelSha256: asset.lods[0].sha256,
    qcSha256: await sha(path.join(root, 'public/assets/models/prop_aegis_citadel.qc.json')),
    previews: { assembly: review.previewSha256s['citadel-gothic.png'] } };
  approval.previews = { assembly: 'authoring/blender/aegis-city/review/citadel-gothic.png' };
  approval.review = { reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash };
  approval.provenance = bp.provenance;
  await write(approvalFile, approval);
  const validations = await read(path.join(work, 'validation.json'));
  for (const result of results) {
    const entry = validations.find(entry => entry.model === result.model);
    assert(entry, 'Missing city validation entry');
    Object.assign(entry, { errors: result.errors, warnings: result.warnings });
  }
  await write(path.join(work, 'validation.json'), validations);
  console.log('Published the citadel models, QC, blueprint and approval record. Run npm run models:registry.');
}
