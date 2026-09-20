/** Publish literal character exports after their package-specific technical gates. */
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
import { validateApprovedManifest } from '../blender-character-pipeline/tools/runtime-registry.mjs';
import { validateJsonSchema } from '../blender-character-pipeline/tools/json-schema-validator.mjs';
import { standingWorldAssetApproval } from '../blender-character-pipeline/tools/world-asset-approval.mjs';
import { INHABITANT_CLIPS, inside } from '../../authoring/blender/frontier-population/tools/inhabitant_review.mjs';
import { createPublicationEvidence, regionalPublicationAuditPaths } from './regional-publication-evidence.mjs';

export const REGIONAL_CHARACTER_PACKAGES = {
  'sunmeadow-farmer': {
    key: 'frontier_sunmeadow_empire_farmer', assetId: 'chr.frontier.sunmeadow.empire_farmer',
    name: 'Sunmeadow Empire Farmer', bodyFamily: 'frontier_sunmeadow_empire_farmer_v1_m',
    skeletonId: 'sunmeadow_farmer_humanoid_v1', bindPoseId: 'sunmeadow_farmer_a_pose_v1',
    contract: 'publication-contract.json', reports: ['boot_clearance', 'welt'],
  },
  'cinderfen-peat-worker': {
    key: 'frontier_cinderfen_greenskin_peat_worker', assetId: 'chr.frontier.cinderfen.greenskin_peat_worker',
    name: 'Cinderfen Greenskin Peat Worker', bodyFamily: 'frontier_mire_worker',
    skeletonId: 'frontier_mire_worker_v1', bindPoseId: 'frontier_mire_worker_a_v1',
    contract: 'character-contract.json', reports: ['garment_clearance', 'welt', 'tool_clearance'],
    masterReport: 'master-continuity.json',
  },
  'sunmeadow-herbalist': {
    key: 'frontier_sunmeadow_empire_herbalist', assetId: 'chr.frontier.sunmeadow.empire_herbalist',
    name: 'Sunmeadow Empire Herbalist', bodyFamily: 'frontier_sunmeadow_empire_herbalist_v1_f', bodyVariant: 'f',
    skeletonId: 'sunmeadow_herbalist_humanoid_v1', bindPoseId: 'sunmeadow_herbalist_a_pose_v1',
    contract: 'publication-contract.json', reports: ['boot_clearance', 'welt', 'garment_clearance', 'tool_clearance'],
    masterReport: 'master-continuity.json',
  },
  'cinderfen-supply-officer': {
    key: 'frontier_cinderfen_dark_elf_supply_officer', assetId: 'chr.frontier.cinderfen.dark_elf_supply_officer',
    name: 'Cinderfen Dark Elf Supply Officer', bodyFamily: 'frontier_cinderfen_supply_officer_v1_f', bodyVariant: 'f',
    skeletonId: 'cinderfen_supply_officer_humanoid_v1', bindPoseId: 'cinderfen_supply_officer_a_v1',
    contract: 'character-contract.json', reports: ['garment_clearance', 'welt', 'tool_clearance'],
    masterReport: 'master-continuity.json',
  },
  'sunmeadow-scout': {
    key: 'frontier_sunmeadow_high_elf_scout', assetId: 'chr.frontier.sunmeadow.high_elf_scout',
    name: 'Sunmeadow High Elf Scout', bodyFamily: 'frontier_sunmeadow_high_elf_scout_v1_f', bodyVariant: 'f',
    skeletonId: 'sunmeadow_scout_humanoid_v1', bindPoseId: 'sunmeadow_scout_a_pose_v1',
    contract: 'publication-contract.json', reports: ['boot_clearance', 'welt', 'garment_clearance', 'tool_clearance'],
    masterReport: 'master-continuity.json',
  },
};
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const jsonBytes = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');
const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));

/** The fitted rig identity must agree before export bytes can be published. */
export function regionalPublicationIdentity(spec, contract) {
  const identity = { bodyFamily: spec.bodyFamily, bodyVariant: spec.bodyVariant ?? 'm',
    skeletonId: spec.skeletonId, bindPoseId: spec.bindPoseId };
  assert(['m', 'f'].includes(identity.bodyVariant), 'Unsupported body variant');
  assert.equal(contract.assetId, spec.assetId); assert.equal(contract.profileId, `npc_${spec.key}`);
  for (const [field, expected] of Object.entries(identity)) {
    assert.equal(field === 'bodyVariant' ? contract[field] ?? 'm' : contract[field], expected,
      `Publication ${field} differs from the authored contract`);
  }
  return identity;
}

export async function publishRegionalInhabitant(packageName, suffix, publish = false) {
  const spec = REGIONAL_CHARACTER_PACKAGES[packageName];
  assert(spec, 'Choose a configured regional character package');
  assert(/^_[a-z0-9_]+$/i.test(suffix ?? ''), 'Provide the exact --review-suffix');
  const { key, assetId, name } = spec;
  const packagePath = `authoring/blender/${packageName}`, profile = `npc_${key}`;
  const work = inside(repo, packagePath), snapshot = createPublicationEvidence(repo);
  const { retain } = snapshot;
  const local = (relative, expected) => retain(`${packagePath}/${relative}`, expected);
  const build = JSON.parse(await local(`review/${key}_build.json`));
  const contract = JSON.parse(await local(spec.contract));
  assert.equal(build.key, key);
  const { bodyFamily, bodyVariant, skeletonId, bindPoseId } = regionalPublicationIdentity(spec, contract);
  assert.deepEqual(build.lods.map(lod => lod.level), [0, 1, 2]);
  for (const relative of regionalPublicationAuditPaths(spec, build.lods)) await local(relative);
  assert(build.sourceFiles?.length, 'Build must enumerate actual authoring inputs');
  for (const source of [...build.sourceFiles, ...build.validationSourceFiles ?? []]) {
    const bytes = await retain(source.path, source.sha256);
    if (source.bytes !== undefined) assert.equal(bytes.length, source.bytes);
  }
  await local(`sources/${key}.blend`, build.masterSha256);
  if (spec.masterReport) {
    const master = JSON.parse(await local(`review/${spec.masterReport}`));
    assert.equal(master.masterSha256, build.masterSha256, 'Master continuity audit is stale');
  }
  await local('foundation-provenance.json');
  // Freeze the inspectors too: gates are character-specific, never relaxed here.
  for (const file of await fs.readdir(path.join(work, 'tools'))) {
    if (/\.(py|mjs)$/.test(file)) await local(`tools/${file}`);
  }
  await retain('scripts/campaign/publish-regional-inhabitant.mjs');
  await retain('scripts/campaign/regional-publication-evidence.mjs');
  await retain('scripts/blender-character-pipeline/data/world-asset-approval.json');
  await retain('scripts/blender-character-pipeline/tools/world-asset-approval.mjs');
  await retain('authoring/blender/frontier-population/tools/inhabitant_review.mjs');
  const technical = JSON.parse(await local('review/draft-validation.json'));
  assert(technical.passed, 'Current technical validation failed');
  const previews = [], idleDurations = []; let bounds;
  for (const lod of build.lods) {
    const bytes = await local(`runtime/${lod.model}`, lod.sha256);
    assert.equal(bytes.length, lod.bytes);
    const document = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
    assert.deepEqual(document.animations.map(clip => clip.name).sort(), INHABITANT_CLIPS);
    assert(document.skins?.length && document.images?.every(image => !image.uri), 'Embedded skinned character required');
    const idle = document.animations.find(clip => clip.name === 'idle');
    idleDurations.push(Math.max(...idle.samplers.map(sampler => document.accessors[sampler.input].max[0])));
    const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: lod.model });
    assert.equal(validation.issues.numErrors, 0); assert.equal(validation.issues.numWarnings, 0);
    const recorded = technical.records.find(record => record.model === lod.model);
    assert.equal(recorded?.sha256, lod.sha256); assert.equal(recorded.errors, 0); assert.equal(recorded.warnings, 0);
    if (lod.level === 0) {
      const close = JSON.parse(await local(`review/${key}_lod0_review${suffix}.json`));
      assert.equal(close.modelSha256, lod.sha256, 'Saved previews must show the final export');
      for (const view of ['front', 'head', 'run_side', 'death:2']) assert(close.images.some(image => image.view === view), `Missing ${view} preview`);
      for (const image of close.images) { await local(image.image, image.sha256); previews.push({ lod: 0, ...image }); }
      bounds = { min: [close.bounds.min[0], close.bounds.min[2], -close.bounds.max[1]],
        max: [close.bounds.max[0], close.bounds.max[2], -close.bounds.min[1]] };
    }
  }
  assert(idleDurations.every(duration => duration > 0 && Math.abs(duration - idleDurations[0]) < 1e-6), 'All LODs need synchronized idle duration');
  // Every gate input is retained before execution and rechecked before writing.
  execFileSync('python', [path.join(work, 'tools/test_exports.py')], { cwd: repo, stdio: 'pipe' });
  const evidence = { assetId, profileKey: profile, models: build.lods.map(lod => ({ level: lod.level, model: lod.model, sha256: lod.sha256 })),
    files: Object.fromEntries(snapshot.entries()) };
  const review = standingWorldAssetApproval(evidence), reviewBytes = jsonBytes(review), reviewHash = hash(reviewBytes);
  const release = `${packagePath}/releases/${key}/${reviewHash.slice(0, 20)}`;
  const frozen = relative => `${release}/files/${packagePath}/${relative}`;
  const provenance = { createdBy: 'original_fitted_garments_on_retained_anatomical_foundation', aiAssisted: true,
    author: 'Codex regional character authoring', source: frozen(`sources/${key}.blend`), sourceSha256: build.masterSha256,
    referencePackId: 'battle_prelate_craftsmanship', similarityReview: 'not_required',
    aiStages: ['racial_anatomy', 'garment_construction', 'equipment_fitting', 'pbr_materials', 'rig_and_motion', 'export_review'] };
  const lods = build.lods.map(lod => ({ level: lod.level, model: lod.model, sha256: lod.sha256, triangles: lod.triangles, externalTextures: [] }));
  const blueprint = { assetId, displayName: name, category: 'character', version: '1.0.0', sets: ['regional_inhabitants'],
    runtime: { profileKey: profile, bodyFamily, bodyVariant, skeletonId, bindPoseId },
    output: { model: lods[0].model, artifactDir: frozen('runtime') }, generator: { kind: 'copyExisting', copyFrom: frozen(`runtime/${lods[0].model}`) },
    geometry: { originRule: 'ground_beneath_feet', upAxis: '+Y', forwardAxis: '+Z', bodyFamily, skeletonId, bindPoseId,
      lods: lods.map((lod, index) => ({ name: `LOD${index}`, triTarget: lod.triangles, screenCoverageMin: [.2, .06, 0][index] })) },
    materials: { master: 'MM_FrontierInhabitant', textureSet: key, channels: ['baseColor', 'normal', 'roughness', 'metallic'], maxTextureResolution: 4096 },
    rigging: { skinned: true, maxInfluences: 4, requiredClips: INHABITANT_CLIPS },
    compatibility: { occupiesSlots: ['body'], requires: [], conflictsWith: [] }, provenance,
    qc: { allowNonManifold: true, allowUvOverlap: true, maxDrawCalls: 32, maxMeshObjects: 1, maxFileSizeMb: 32, maxTris: lods[0].triangles,
      requiresSkinnedMeshes: true, requiresPreview: true, expectedHeightM: bounds.max[1] - bounds.min[1], heightToleranceM: .02, groundToleranceM: .004 },
    lifecycle: { status: 'approved', reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash, notes: review.notes } };
  assert.deepEqual(validateJsonSchema(await read(path.join(repo, 'scripts/blender-character-pipeline/data/asset-blueprint.schema.json')), blueprint), []);
  const qcFiles = lods.map(lod => ({ file: lod.model.replace('.glb', '.qc.json'), bytes: jsonBytes({
    qcPassed: true, assetId, modelSha256: lod.sha256, lod: lod.level, builtLods: lods, lods, externalTextures: [],
    validationErrors: 0, validationWarnings: 0, skeletonId, bindPoseId, skinned: true, animationClips: INHABITANT_CLIPS,
    defaultAnimation: 'idle', bounds, reviewHash, reviewEvidence: evidence, frozenSource: release,
    previewImages: previews.filter(view => view.lod === lod.level).map(view => frozen(view.image)),
    limitations: ['Complete fitted outfit; not a modular armor body.', 'Requires its own fitted embedded clips; no siege crew compatibility claim.',
      'Carried tools are visual equipment; no harvesting interaction is claimed.'],
  }) }));
  const front = previews.find(view => view.view === 'front'), head = previews.find(view => view.view === 'head');
  const manifest = { schemaVersion: 1, assetId, displayName: name, category: 'character', model: lods[0].model, qc: qcFiles[0].file,
    runtime: { profileKey: profile, skinned: true }, compatibility: { bodyFamily, bodyVariant, skeletonId, bindPoseId },
    hashes: { modelSha256: lods[0].sha256, qcSha256: hash(qcFiles[0].bytes), previews: { front: front.sha256, head: head.sha256 } },
    previews: { front: frozen(front.image), head: frozen(head.image) }, review: { reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash },
    provenance, approvalState: 'approved' };
  validateApprovedManifest(manifest, key);
  await snapshot.recheck();
  if (!publish) return { assetId, lods, checked: true, published: false };
  // Freeze before registry-facing writes; an interrupted publish has recoverable bytes.
  for (const [relative, record] of snapshot.entries()) {
    const target = inside(repo, `${release}/files/${relative}`), bytes = await retain(relative, record.sha256);
    await fs.mkdir(path.dirname(target), { recursive: true });
    try { await fs.writeFile(target, bytes, { flag: 'wx' }); }
    catch (error) { if (error.code !== 'EEXIST') throw error; assert.equal(hash(await fs.readFile(target)), record.sha256); }
  }
  await fs.mkdir(inside(repo, `${release}/review`), { recursive: true });
  await fs.writeFile(inside(repo, `${release}/review/visual_review.json`), reviewBytes);
  const metadata = { schemaVersion: 1, assets: { [profile]: { runtimeReady: true, modelSha256: lods[0].sha256,
    label: name, group: 'Characters and NPCs', defaultScale: { x: 1, y: 1, z: 1 }, defaultAnimation: 'idle',
    footprint: { width: Number((bounds.max[0] - bounds.min[0]).toFixed(3)), depth: Number((bounds.max[2] - bounds.min[2]).toFixed(3)), chainAxis: 'z' },
    colliders: [], walkableSurfaces: [], cameraSolid: false } } };
  const writes = [[`${packagePath}/review/visual_review.json`, reviewBytes], [`${packagePath}/builder-metadata.json`, jsonBytes(metadata)],
    [`scripts/blender-character-pipeline/data/asset-blueprints/${key}.asset.json`, jsonBytes(blueprint)],
    [`scripts/blender-character-pipeline/data/approved-assets/${key}.approved.json`, jsonBytes(manifest)],
    ...await Promise.all(lods.map(async lod => [`public/assets/models/${lod.model}`, await fs.readFile(inside(repo, frozen(`runtime/${lod.model}`)))])),
    ...qcFiles.map(qc => [`public/assets/models/${qc.file}`, qc.bytes])];
  for (const [relative, bytes] of writes) {
    const target = inside(repo, relative);
    try { const old = await fs.readFile(target); if (hash(old) !== hash(bytes)) {
      const backup = path.join(work, 'previous-accepted', `${hash(old)}-${path.basename(target)}`);
      await fs.mkdir(path.dirname(backup), { recursive: true }); await fs.writeFile(backup, old);
    } } catch (error) { if (error.code !== 'ENOENT') throw error; }
    await fs.writeFile(`${target}.inhabitant-pending`, bytes); await fs.rename(`${target}.inhabitant-pending`, target);
  }
  return { assetId, lods, checked: true, published: true, release };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const suffix = process.argv.find(arg => arg.startsWith('--review-suffix='))?.split('=')[1];
  assert(process.argv.includes('--check') || process.argv.includes('--publish'), 'Choose --check or --publish');
  console.log(JSON.stringify(await publishRegionalInhabitant(process.argv[2], suffix, process.argv.includes('--publish')), null, 2));
}
