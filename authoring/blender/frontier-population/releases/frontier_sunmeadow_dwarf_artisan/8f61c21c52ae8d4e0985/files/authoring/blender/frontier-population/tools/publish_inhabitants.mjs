/** Freeze and publish the reviewed dwarf's literal exports; never rebuild a model. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
import { validateApprovedManifest } from '../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
import { validateJsonSchema } from '../../../../scripts/blender-character-pipeline/tools/json-schema-validator.mjs';
import { INHABITANT_CLIPS, inside, requireCharacterViews, requireCurrentApproval } from './inhabitant_review.mjs';
import { standingWorldAssetApproval } from '../../../../scripts/blender-character-pipeline/tools/world-asset-approval.mjs';

const work = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repo = path.resolve(work, '../../..');
const packagePath = path.relative(repo, work).replaceAll('\\', '/');
const key = 'frontier_sunmeadow_dwarf_artisan';
const profile = `npc_${key}`;
const assetId = 'chr.frontier.sunmeadow.dwarf_artisan';
const name = 'Sunmeadow Dwarf Artisan';
const skeletonId = 'frontier_dwarf_artisan_v1';
const bindPoseId = 'frontier_dwarf_artisan_rest_v1';
const suffix = process.argv.find(arg => arg.startsWith('--review-suffix='))?.split('=')[1];
const standingApproval = process.argv.includes('--standing-approval');
assert(suffix && /^_[a-z0-9_]+$/i.test(suffix), 'Specify the exact --review-suffix of the final three-LOD close views');
assert(process.argv.includes('--prepare-review') || process.argv.includes('--publish'), 'Choose --prepare-review or --publish');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));
const files = new Map();
async function retain(relative, expected) {
  relative = relative.replaceAll('\\', '/');
  const bytes = await fs.readFile(inside(repo, relative));
  const sha256 = hash(bytes);
  if (expected) assert.equal(sha256, expected, `Changed evidence: ${relative}`);
  assert(!files.has(relative) || files.get(relative).sha256 === sha256, `Evidence changed during collection: ${relative}`);
  files.set(relative, { sha256, bytes: bytes.length });
  return bytes;
}
const local = (relative, expected) => retain(`${packagePath}/${relative}`, expected);
const build = JSON.parse(await local(`review/${key}_build.json`));
assert.equal(build.key, key);
assert.deepEqual(build.lods.map(lod => lod.level), [0, 1, 2]);
assert(Array.isArray(build.sourceFiles) && build.sourceFiles.length, 'Final build must enumerate its actual repository-relative authoring inputs');
for (const source of build.sourceFiles) {
  const bytes = await retain(source.path, source.sha256);
  assert.equal(bytes.length, source.bytes, `Source size mismatch: ${source.path}`);
}
await local(`sources/${key}.blend`, build.masterSha256);
await local('foundation-provenance.json');
// Generating inputs are frozen above. Inspection helpers may improve without
// rebaking the model; keep their current, separately recorded validation revision.
for (const source of build.validationSourceFiles ?? []) {
  const bytes = await retain(source.path, source.sha256);
  if (source.bytes !== undefined) assert.equal(bytes.length, source.bytes);
}
for (const helper of ['publish_inhabitants.mjs', 'inhabitant_review.mjs', 'validate_inhabitants.mjs']) await local(`tools/${helper}`);
if (standingApproval) await retain('scripts/blender-character-pipeline/data/world-asset-approval.json');

// Use the existing actual-geometry gates, including the final welt extension,
// instead of creating a weaker second set of tolerances for publication.
execFileSync('python', [path.join(work, 'tools/test_inhabitant_exports.py')], { cwd: repo, stdio: 'pipe' });
const technical = JSON.parse(await local('review/draft-validation.json'));
assert(technical.passed, 'Current technical validation failed');
const previews = [];
let bounds;
for (const lod of build.lods) {
  const bytes = await local(`runtime/${lod.model}`, lod.sha256);
  assert.equal(bytes.length, lod.bytes);
  const document = JSON.parse(bytes.subarray(20, 20+bytes.readUInt32LE(12)));
  assert.deepEqual(document.animations.map(clip => clip.name).sort(), INHABITANT_CLIPS);
  assert(document.skins?.length && document.images?.every(image => !image.uri), 'Embedded skinned character required');
  const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: lod.model });
  assert.equal(validation.issues.numErrors, 0, `${lod.model}: glTF errors`);
  assert.equal(validation.issues.numWarnings, 0, `${lod.model}: unresolved glTF warnings`);
  const recorded = technical.records.find(record => record.model === lod.model);
  assert.equal(recorded?.sha256, lod.sha256, 'Technical report is stale');
  assert.equal(recorded.errors, 0); assert.equal(recorded.warnings, 0);
  for (const report of [`${lod.model}.validation.json`, `arm-volume-lod${lod.level}.json`,
    `${key}_lod${lod.level}_motion.json`, `${key}_lod${lod.level}_garment_clearance.json`]) await local(`review/${report}`);
  if (standingApproval) {
    // Saved previews document the accepted appearance. Technical all-LOD motion
    // checks above still run, without requiring another aesthetic review cycle.
    if (lod.level === 0) {
      const close = JSON.parse(await local(`review/${key}_lod0_review${suffix}.json`));
      assert.equal(close.modelSha256, lod.sha256);
      for (const name of ['front', 'head']) assert(close.images.some(view => view.view === name), `Missing ${name} preview`);
      for (const view of close.images) { await local(view.image, view.sha256); previews.push({ lod: 0, ...view }); }
      bounds = { min: [close.bounds.min[0], close.bounds.min[2], -close.bounds.max[1]], max: [close.bounds.max[0], close.bounds.max[2], -close.bounds.min[1]] };
    }
    continue;
  }
  const close = JSON.parse(await local(`review/${key}_lod${lod.level}_review${suffix}.json`));
  const motion = JSON.parse(await local(`review/${key}_lod${lod.level}_motion_sheet.json`));
  assert.equal(close.modelSha256, lod.sha256, 'Close views show a different model');
  assert.equal(motion.modelSha256, lod.sha256, 'Motion views show a different model');
  requireCharacterViews(close.images, motion.images);
  for (const view of [...close.images, ...motion.images]) {
    await local(view.image, view.sha256);
    previews.push({ lod: lod.level, ...view });
  }
  const sheets = JSON.parse(await local(`review/${key}_lod${lod.level}_sheets.json`));
  assert.equal(sheets.modelSha256, lod.sha256, 'Motion sheets are stale');
  for (const sheet of sheets.sheets) await local(`review/${sheet.image}`, sheet.sha256);
  if (lod.level === 0) bounds = { min: [close.bounds.min[0], close.bounds.min[2], -close.bounds.max[1]], max: [close.bounds.max[0], close.bounds.max[2], -close.bounds.min[1]] };
}
const evidence = { assetId, profileKey: profile, models: build.lods.map(lod => ({ level: lod.level, model: lod.model, sha256: lod.sha256 })),
  files: Object.fromEntries([...files].sort(([a], [b]) => a.localeCompare(b))) };
const reviewPath = path.join(work, 'review/visual_review.json');
if (standingApproval) await fs.writeFile(reviewPath, JSON.stringify(standingWorldAssetApproval(evidence), null, 2)+'\n');
if (process.argv.includes('--prepare-review')) {
  let previous;
  try { previous = await read(reviewPath); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const same = previous && JSON.stringify(previous.evidence) === JSON.stringify(evidence);
  const review = { status: same ? previous.status : 'pending', reviewedBy: same ? previous.reviewedBy : '',
    reviewedAt: same ? previous.reviewedAt : '', notes: same ? previous.notes : 'Review the complete character, three LODs, fitted clothing/equipment, and actual motion under neutral/game lighting.', evidence };
  await fs.writeFile(reviewPath, JSON.stringify(review, null, 2)+'\n');
  console.log('Prepared the exact dwarf review; no runtime publication.');
  process.exit(0);
}
const review = await read(reviewPath);
requireCurrentApproval(review, evidence);
const reviewBytes = Buffer.from(JSON.stringify(review, null, 2)+'\n');
const reviewHash = hash(reviewBytes);
const release = `${packagePath}/releases/${key}/${reviewHash.slice(0, 20)}`;
const frozen = relative => `${release}/files/${packagePath}/${relative.replaceAll('\\', '/')}`;
const provenance = { createdBy: 'original_fitted_garments_on_retained_anatomical_foundation', aiAssisted: true,
  author: 'Codex regional character authoring', source: frozen(`sources/${key}.blend`), sourceSha256: build.masterSha256,
  referencePackId: 'battle_prelate_craftsmanship', similarityReview: 'not_required',
  aiStages: ['racial_anatomy', 'garment_construction', 'equipment_fitting', 'pbr_materials', 'rig_and_motion', 'export_review'] };
const lods = build.lods.map(lod => ({ level: lod.level, model: lod.model, sha256: lod.sha256, triangles: lod.triangles, externalTextures: [] }));
const blueprint = { assetId, displayName: name, category: 'character', version: '1.0.0', sets: ['regional_inhabitants'],
  runtime: { profileKey: profile, bodyFamily: 'frontier_dwarf_artisan', bodyVariant: 'm', skeletonId, bindPoseId },
  output: { model: lods[0].model, artifactDir: frozen('runtime') }, generator: { kind: 'copyExisting', copyFrom: frozen(`runtime/${lods[0].model}`) },
  geometry: { originRule: 'ground_beneath_feet', upAxis: '+Y', forwardAxis: '+Z', bodyFamily: 'frontier_dwarf_artisan', skeletonId, bindPoseId,
    lods: lods.map((lod, index) => ({ name: `LOD${index}`, triTarget: lod.triangles, screenCoverageMin: [.2, .06, 0][index] })) },
  materials: { master: 'MM_FrontierInhabitant', textureSet: key, channels: ['baseColor', 'normal', 'roughness', 'metallic'], maxTextureResolution: 4096 },
  rigging: { skinned: true, maxInfluences: 4, requiredClips: INHABITANT_CLIPS },
  compatibility: { occupiesSlots: ['body'], requires: [], conflictsWith: [] }, provenance,
  qc: { allowNonManifold: true, allowUvOverlap: true, maxDrawCalls: 32, maxMeshObjects: 1, maxFileSizeMb: 32, maxTris: lods[0].triangles,
    requiresSkinnedMeshes: true, requiresPreview: true, expectedHeightM: bounds.max[1]-bounds.min[1], heightToleranceM: .02, groundToleranceM: .004 },
  lifecycle: { status: 'approved', reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash, notes: review.notes } };
assert.deepEqual(validateJsonSchema(await read(path.join(repo, 'scripts/blender-character-pipeline/data/asset-blueprint.schema.json')), blueprint), []);
const qcFiles = lods.map(lod => ({ file: lod.model.replace('.glb', '.qc.json'), bytes: Buffer.from(JSON.stringify({
  qcPassed: true, assetId, modelSha256: lod.sha256, lod: lod.level, builtLods: lods, lods, externalTextures: [],
  validationErrors: 0, validationWarnings: 0, skeletonId, bindPoseId, skinned: true, animationClips: INHABITANT_CLIPS,
  defaultAnimation: 'idle', bounds, reviewHash, reviewEvidence: evidence, frozenSource: release,
  previewImages: previews.filter(view => view.lod === lod.level).map(view => frozen(view.image)),
  limitations: ['Complete fitted outfit; not a modular armor body.', 'Racially morphed rest skeleton and apron joint require this character’s own exported clips.'],
}, null, 2)+'\n') }));
const front = previews.find(view => view.lod === 0 && view.view === 'front');
const head = previews.find(view => view.lod === 0 && view.view === 'head');
const manifest = { schemaVersion: 1, assetId, displayName: name, category: 'character', model: lods[0].model, qc: qcFiles[0].file,
  runtime: { profileKey: profile, skinned: true }, compatibility: { bodyFamily: 'frontier_dwarf_artisan', bodyVariant: 'm', skeletonId, bindPoseId },
  hashes: { modelSha256: lods[0].sha256, qcSha256: hash(qcFiles[0].bytes), previews: { front: front.sha256, head: head.sha256 } },
  previews: { front: frozen(front.image), head: frozen(head.image) }, review: { reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash },
  provenance, approvalState: 'approved' };
validateApprovedManifest(manifest, key);

// Recheck every input before any publication. All accepted inputs keep their
// repository-relative layout inside the frozen release for future reconstruction.
for (const [relative, record] of files) await retain(relative, record.sha256);
for (const [relative, record] of files) {
  const target = inside(repo, `${release}/files/${relative}`);
  const bytes = await fs.readFile(inside(repo, relative));
  assert.equal(hash(bytes), record.sha256);
  await fs.mkdir(path.dirname(target), { recursive: true });
  try { await fs.writeFile(target, bytes, { flag: 'wx' }); }
  catch (error) { if (error.code !== 'EEXIST') throw error; assert.equal(hash(await fs.readFile(target)), record.sha256); }
}
await fs.mkdir(inside(repo, `${release}/review`), { recursive: true });
await fs.writeFile(inside(repo, `${release}/review/visual_review.json`), reviewBytes, { flag: 'wx' }).catch(async error => {
  if (error.code !== 'EEXIST') throw error;
  assert.equal(hash(await fs.readFile(inside(repo, `${release}/review/visual_review.json`))), reviewHash);
});
const writes = [
  [`scripts/blender-character-pipeline/data/asset-blueprints/${key}.asset.json`, Buffer.from(JSON.stringify(blueprint, null, 2)+'\n')],
  [`scripts/blender-character-pipeline/data/approved-assets/${key}.approved.json`, Buffer.from(JSON.stringify(manifest, null, 2)+'\n')],
  ...await Promise.all(lods.map(async lod => [`public/assets/models/${lod.model}`, await fs.readFile(inside(repo, frozen(`runtime/${lod.model}`)))])),
  ...qcFiles.map(qc => [`public/assets/models/${qc.file}`, qc.bytes]),
];
for (const [relative, bytes] of writes) {
  const target = inside(repo, relative);
  try {
    const old = await fs.readFile(target);
    if (hash(old) !== hash(bytes)) {
      const backup = path.join(work, 'previous-accepted', `${hash(old)}-${path.basename(target)}`);
      await fs.mkdir(path.dirname(backup), { recursive: true }); await fs.writeFile(backup, old);
    }
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const temporary = target+'.inhabitant-pending';
  await fs.writeFile(temporary, bytes); await fs.rename(temporary, target);
}
let metadata = { schemaVersion: 1, assets: {} };
try { metadata = await read(path.join(work, 'builder-metadata.json')); } catch (error) { if (error.code !== 'ENOENT') throw error; }
metadata.assets[profile] = { runtimeReady: true, modelSha256: lods[0].sha256, label: name, group: 'Characters and NPCs',
  defaultScale: { x: 1, y: 1, z: 1 }, defaultAnimation: 'idle', footprint: { width: Number((bounds.max[0]-bounds.min[0]).toFixed(3)), depth: Number((bounds.max[2]-bounds.min[2]).toFixed(3)), chainAxis: 'z' },
  colliders: [], walkableSurfaces: [], cameraSolid: false };
await fs.writeFile(path.join(work, 'builder-metadata.json'), JSON.stringify(metadata, null, 2)+'\n');
console.log('Published the exact accepted dwarf character; compile the registry and regenerate the GM catalog to activate it.');
