/** Publish the universal field supply chest after literal export and collision checks. */
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
import { validateApprovedManifest } from '../blender-character-pipeline/tools/runtime-registry.mjs';
import { validateJsonSchema } from '../blender-character-pipeline/tools/json-schema-validator.mjs';
import { standingWorldAssetApproval } from '../blender-character-pipeline/tools/world-asset-approval.mjs';
import { createPublicationEvidence } from './regional-publication-evidence.mjs';
import { inside } from '../../authoring/blender/frontier-population/tools/inhabitant_review.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const packagePath = 'authoring/blender/field-supply-chest', key = 'frontier_field_supply_chest';
const assetId = 'prop.frontier.field_supply_chest', name = 'Field Supply Chest';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const jsonBytes = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');

export async function publishFieldSupplyChest(publish = false) {
  const snapshot = createPublicationEvidence(repo);
  const local = (relative, expected) => snapshot.retain(`${packagePath}/${relative}`, expected);
  const read = async relative => JSON.parse(await local(relative));
  const build = await read(`review/${key}_build.json`), contract = await read('builder-contract.json');
  assert.equal(build.key, key); assert.deepEqual(build.lods.map(lod => lod.level), [0, 1, 2]);
  assert(build.sourceFiles?.length, 'Consolidated authoring and inspection evidence required');
  for (const file of build.sourceFiles) {
    const bytes = await local(file.path, file.sha256);
    if (file.bytes !== undefined) assert.equal(bytes.length, file.bytes);
  }
  const validation = await read('validation.json');
  assert(validation.passed && validation.key === key, 'Current technical validation required');
  const measured = contract.assets?.[key];
  assert(measured?.colliders?.length && measured.boundsYUp && measured.approachSource, 'Measured collision/frontage required');
  assert.equal(measured.sourceMasterSha256, build.lods[0].sourceMasterSha256);
  const textureReceipt = await read('textures/sources.json');
  for (const [file, receipt] of Object.entries(textureReceipt.textures)) await local(file, receipt.sha256);
  await local('tools/make_textures.py', textureReceipt.generatorSha256);
  for (const file of await fs.readdir(inside(repo, `${packagePath}/tools`))) {
    if (/\.(py|mjs)$/.test(file)) await local(`tools/${file}`);
  }
  for (const file of ['scripts/campaign/publish-field-supply-chest.mjs', 'scripts/campaign/regional-publication-evidence.mjs',
    'scripts/blender-character-pipeline/data/world-asset-approval.json',
    'scripts/blender-character-pipeline/tools/world-asset-approval.mjs']) await snapshot.retain(file);
  const previews = [], lods = [];
  for (const lod of build.lods) {
    assert.equal(lod.model, `${key}_lod${lod.level}.glb`);
    const bytes = await local(`runtime/${lod.model}`, lod.sha256);
    assert.equal(bytes.length, lod.bytes);
    await local(lod.master, lod.masterSha256); await local(lod.sourceMaster, lod.sourceMasterSha256);
    const source = await read(`review/${key}_lod${lod.level}_build.json`);
    assert.equal(source.sha256, lod.sha256); assert.equal(source.masterSha256, lod.masterSha256);
    assert(source.sourceFiles?.length, 'Retained generating inputs required');
    for (const file of source.sourceFiles) await local(file.path, file.sha256);
    await local(`review/${key}_lod${lod.level}_source-audit.json`);
    const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
    assert(!gltf.skins?.length && !gltf.animations?.length, 'Static chest must not add a character rig');
    assert(gltf.images?.length && gltf.images.every(image => !image.uri && Number.isInteger(image.bufferView)), 'Embedded PBR maps required');
    const result = await validator.validateBytes(new Uint8Array(bytes), { uri: lod.model });
    assert.equal(result.issues.numErrors, 0); assert.equal(result.issues.numWarnings, 0);
    const review = await read(`review/${key}_lod${lod.level}_reimport.json`);
    assert.equal(review.sha256, lod.sha256);
    await local('tools/review_chest.py', review.reviewerSha256);
    for (const view of lod.level === 0 ? ['neutral', 'gameplay', 'rear', 'detail', 'joinery'] : ['neutral', 'gameplay']) {
      assert(review.views?.[view], `Missing LOD${lod.level} ${view} review`);
    }
    for (const [view, image] of Object.entries(review.views)) {
      await local(`review/${image.image}`, image.sha256);
      previews.push({ lod: lod.level, view, path: `review/${image.image}`, sha256: image.sha256 });
    }
    lods.push({ level: lod.level, model: lod.model, sha256: lod.sha256, triangles: lod.triangles,
      bytes: lod.bytes, externalTextures: [] });
  }
  assert(lods[0].triangles > lods[1].triangles && lods[1].triangles > lods[2].triangles, 'Three decreasing detail levels required');
  execFileSync(process.execPath, [inside(repo, `${packagePath}/tools/validate_chest.mjs`), '--check'], { cwd: repo, stdio: 'pipe' });
  const evidence = { assetId, models: lods, files: Object.fromEntries(snapshot.entries()) };
  const review = standingWorldAssetApproval(evidence), reviewBytes = jsonBytes(review), reviewHash = hash(reviewBytes);
  const release = `${packagePath}/releases/${key}/${reviewHash.slice(0, 20)}`;
  const frozen = relative => `${release}/files/${packagePath}/${relative}`;
  const provenance = { createdBy: 'original_authored_mesh_control_cages', aiAssisted: true,
    aiStages: ['mesh_authoring', 'material_painting', 'lod_authoring', 'technical_validation'],
    referencePackId: 'original_universal_field_supply_chest_v1', similarityReview: 'not_required',
    source: frozen(build.lods[0].sourceMaster), sourceSha256: build.lods[0].sourceMasterSha256 };
  const qcFiles = lods.map(lod => ({ file: lod.model.replace('.glb', '.qc.json'), bytes: jsonBytes({
    qcPassed: true, assetId, modelSha256: lod.sha256, lod: lod.level, lods, builtLods: lods,
    totalTris: lod.triangles, validationErrors: 0, validationWarnings: 0, externalTextures: [],
    bounds: { min: measured.boundsYUp.minimum, max: measured.boundsYUp.maximum },
    collisionContractSha256: evidence.files[`${packagePath}/builder-contract.json`].sha256,
    reviewHash, reviewEvidence: evidence, frozenSource: release,
    previewImages: previews.filter(view => view.lod === lod.level).map(view => frozen(view.path)),
    limitations: ['Static closed chest; no loot inventory or opening interaction claimed.'],
  }) }));
  const assembly = previews.find(view => view.lod === 0 && view.view === 'neutral');
  const manifest = { schemaVersion: 1, assetId, displayName: name, category: 'prop',
    model: lods[0].model, qc: qcFiles[0].file, runtime: { staticKey: key },
    compatibility: { bodyFamily: 'static_architecture', bodyVariant: 'neutral', skeletonId: 'none', bindPoseId: 'none' },
    hashes: { modelSha256: lods[0].sha256, qcSha256: hash(qcFiles[0].bytes), previews: { assembly: assembly.sha256 } },
    previews: { assembly: frozen(assembly.path) },
    review: { reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash }, provenance, approvalState: 'approved' };
  validateApprovedManifest(manifest, key);
  const blueprint = { assetId, displayName: name, category: 'prop', version: '1.0.0', sets: ['universal_town_logistics'],
    runtime: manifest.runtime, output: { model: lods[0].model, artifactDir: frozen('runtime') },
    generator: { kind: 'copyExisting', copyFrom: frozen(`runtime/${lods[0].model}`) },
    geometry: { originRule: 'root_grounded', upAxis: '+Y', forwardAxis: '+Z',
      lods: lods.map(lod => ({ name: `LOD${lod.level}`, triTarget: lod.triangles, screenCoverageMin: [.15, .05, 0][lod.level] })) },
    materials: { master: 'MM_FieldSupplyChest', textureSet: key,
      channels: ['baseColor', 'roughness', 'metallic', 'normal', 'occlusion'], maxTextureResolution: 1024 },
    rigging: { skinned: false, requiredClips: [] }, collision: { policy: 'authored_mass_segments', primitives: [] },
    compatibility: { occupiesSlots: ['prop'], requires: [], conflictsWith: [] }, provenance,
    qc: { allowNonManifold: false, allowUvOverlap: true, maxTris: lods[0].triangles,
      maxFileSizeMb: 12, maxDrawCalls: 4, maxMeshObjects: 4, requiresSkinnedMeshes: false, requiresPreview: true,
      expectedHeightM: measured.boundsYUp.maximum[1] - measured.boundsYUp.minimum[1], heightToleranceM: .01 },
    lifecycle: { status: 'approved', reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash, notes: review.notes } };
  const schema = JSON.parse(await fs.readFile(inside(repo, 'scripts/blender-character-pipeline/data/asset-blueprint.schema.json'), 'utf8'));
  assert.deepEqual(validateJsonSchema(schema, blueprint), []);
  await snapshot.recheck();
  if (!publish) return { assetId, lods, checked: true, published: false };
  for (const [relative, record] of snapshot.entries()) {
    const target = inside(repo, `${release}/files/${relative}`), bytes = await snapshot.retain(relative, record.sha256);
    await fs.mkdir(path.dirname(target), { recursive: true });
    try { await fs.writeFile(target, bytes, { flag: 'wx' }); }
    catch (error) { if (error.code !== 'EEXIST') throw error; assert.equal(hash(await fs.readFile(target)), record.sha256); }
  }
  await fs.mkdir(inside(repo, `${release}/review`), { recursive: true });
  await fs.writeFile(inside(repo, `${release}/review/visual_review.json`), reviewBytes);
  const metadata = { schemaVersion: 1, units: 'metres', assets: { [key]: { ...measured,
    runtimeReady: true, modelSha256: lods[0].sha256 } } };
  const writes = [[`${packagePath}/review/visual_review.json`, reviewBytes], [`${packagePath}/builder-metadata.json`, jsonBytes(metadata)],
    [`scripts/blender-character-pipeline/data/asset-blueprints/${key}.asset.json`, jsonBytes(blueprint)],
    [`scripts/blender-character-pipeline/data/approved-assets/${key}.approved.json`, jsonBytes(manifest)],
    ...await Promise.all(lods.map(async lod => [`public/assets/models/${lod.model}`, await fs.readFile(inside(repo, frozen(`runtime/${lod.model}`)))])),
    ...qcFiles.map(qc => [`public/assets/models/${qc.file}`, qc.bytes])];
  for (const [relative, bytes] of writes) {
    const target = inside(repo, relative);
    try { const old = await fs.readFile(target); if (hash(old) !== hash(bytes)) {
      const backup = inside(repo, `${packagePath}/previous-accepted/${hash(old)}-${path.basename(target)}`);
      await fs.mkdir(path.dirname(backup), { recursive: true }); await fs.writeFile(backup, old);
    } } catch (error) { if (error.code !== 'ENOENT') throw error; }
    await fs.writeFile(`${target}.chest-pending`, bytes); await fs.rename(`${target}.chest-pending`, target);
  }
  return { assetId, lods, checked: true, published: true, release };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  assert(process.argv.includes('--check') || process.argv.includes('--publish'), 'Choose --check or --publish');
  console.log(JSON.stringify(await publishFieldSupplyChest(process.argv.includes('--publish')), null, 2));
}
