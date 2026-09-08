/** Freeze reviewed authored sources and publish approved fauna; never compile the registry. */
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { validateApprovedManifest } from '../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
import { validateJsonSchema } from '../../../../scripts/blender-character-pipeline/tools/json-schema-validator.mjs';
import { collectEvidence, fileSha, localPath, read, sha } from './review_evidence.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repo = path.resolve(root, '../../..');
const packagePath = path.relative(repo, root).replaceAll('\\', '/');
const selected = process.argv.find(a => a.startsWith('--assets='))?.slice(9).split(',') ?? ['roe_deer_buck'];
if (!process.argv.some(a => a.startsWith('--assets='))) process.argv.push(`--assets=${selected.join(',')}`);
await import('./validate_fauna.mjs');
assert(!process.exitCode, 'Actual fauna export validation must pass');
const source = await read(path.join(root, 'source/anatomy.json'));
const resolve = key => ({ ...(source.assets[key]?.inherits ? resolve(source.assets[key].inherits) : {}), ...source.assets[key] });
const evidence = new Map();
for (const kind of selected) evidence.set(kind, await collectEvidence(root, `frontier_sunmeadow_${kind}`, resolve(kind).clips));
const reviewPath = path.join(root, 'review/visual_review.json');
if (process.argv.includes('--prepare-review')) {
  let previous = { assets: {} };
  try { previous = await read(reviewPath); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  for (const [kind, fresh] of evidence) {
    const key = `frontier_sunmeadow_${kind}`, old = previous.assets[key];
    const same = old && JSON.stringify(old.evidence) === JSON.stringify(fresh);
    previous.assets[key] = { evidence: fresh, status: same ? old.status : 'pending', reviewedBy: same ? old.reviewedBy : '',
      reviewedAt: same ? old.reviewedAt : '', notes: same ? old.notes : 'Review actual anatomy, all LODs, complete motion cycles and close material/face views. Technical validation is not visual approval.' };
  }
  await fs.writeFile(reviewPath, JSON.stringify({ ...previous, schemaVersion: 1, kind: 'actual_glb_fauna_review' }, null, 2) + '\n');
  console.log('Prepared fauna review against exact source, model, motion and rendered-image hashes.');
}
if (!process.argv.includes('--publish')) process.exit(0);

const review = await read(reviewPath);
const blueprintSchema = await read(path.join(repo, 'scripts/blender-character-pipeline/data/asset-blueprint.schema.json'));
const changes = [];
for (const [kind, fresh] of evidence) {
  const key = `frontier_sunmeadow_${kind}`, approved = review.assets[key], definition = resolve(kind);
  assert.equal(approved?.status, 'approved', `${key}: internal visual approval is required`);
  assert(approved.reviewedBy && Number.isFinite(Date.parse(approved.reviewedAt)), 'Reviewer and date required');
  assert.deepEqual(approved.evidence, fresh, `${key}: approved evidence changed`);
  const approvalBytes = Buffer.from(JSON.stringify({ schemaVersion: 1, asset: key, review: approved }, null, 2) + '\n');
  const reviewHash = sha(approvalBytes);
  const build = await read(path.join(root, 'review', `${key}_build.json`));
  const technical = await read(path.join(root, 'review', `${key}_technical.json`));
  const renders = (await read(path.join(root, 'review', `${key}_renders.json`))).renders;
  const releaseId = sha(JSON.stringify(approved)).slice(0, 20), releaseRelative = `releases/${key}/${releaseId}`;
  const releaseRepo = `${packagePath}/${releaseRelative}`, release = localPath(root, releaseRelative);
  const skeletonId = `sunmeadow_${kind}_anatomical_v1`, assetId = `prop.frontier.sunmeadow.${kind}`;
  const lods = build.lods.map(lod => ({ level: lod.level, model: lod.model, sha256: lod.sha256, triangles: lod.triangles, externalTextures: [] }));
  const runtimeBounds = b => ({ min: [b.min[0], b.min[2], -b.max[1]], max: [b.max[0], b.max[2], -b.min[1]] });
  const bounds = runtimeBounds(build.lods[0].bounds_blender);
  const provenance = { createdBy: 'original_authored_anatomical_cages_and_species_rigs', aiAssisted: true,
    aiStages: ['anatomy', 'continuous_surface_authoring', 'uv_and_pbr_painting', 'explicit_skinning', 'motion_authoring', 'actual_export_validation', 'visual_review'],
    referencePackId: 'battle_prelate_craftsmanship_and_sunmeadow_fauna', similarityReview: 'not_required', author: 'Codex Sunmeadow fauna authoring',
    source: `${releaseRepo}/source/anatomy.json`, sourceSha256: build.source_sha256 };
  const blueprint = { assetId, displayName: definition.name, category: 'prop', version: '1.0.0', sets: ['sunmeadow_authored_fauna'],
    runtime: { staticKey: key }, output: { model: lods[0].model, artifactDir: `${releaseRepo}/runtime` },
    generator: { kind: 'copyExisting', copyFrom: `${releaseRepo}/runtime/${lods[0].model}` },
    geometry: { originRule: 'ground_beneath_anatomical_body', upAxis: '+Y', forwardAxis: '+Z', bodyFamily: `fauna_${kind}`, skeletonId, bindPoseId: 'authored_anatomical_rest_v1',
      lods: lods.map((lod, level) => ({ name: `LOD${level}`, triTarget: lod.triangles, screenCoverageMin: [.2, .06, 0][level] })) },
    materials: { master: 'MM_SunmeadowAuthoredPelt', textureSet: key, channels: ['baseColor', 'normal', 'roughness', 'metallic', 'occlusion'], maxTextureResolution: 4096 },
    rigging: { skinned: true, maxInfluences: 4, requiredClips: definition.clips },
    collision: { policy: 'authority_species_body_footprint', primitives: [] },
    compatibility: { occupiesSlots: ['prop'], requires: [], conflictsWith: [] }, provenance,
    qc: { allowNonManifold: true, allowUvOverlap: true, maxDrawCalls: 2, maxMeshObjects: 1, maxFileSizeMb: 12, maxTris: lods[0].triangles,
      requiresSkinnedMeshes: true, requiresPreview: true, expectedHeightM: bounds.max[1] - bounds.min[1], heightToleranceM: .02, groundToleranceM: .012 },
    lifecycle: { status: 'approved', reviewedBy: approved.reviewedBy, reviewedAt: approved.reviewedAt, reviewHash, notes: approved.notes } };
  assert.deepEqual(validateJsonSchema(blueprintSchema, blueprint), [], `${key}: invalid blueprint`);
  const previews = renders.map(r => `${releaseRepo}/${r.image.replaceAll('\\', '/')}`);
  const qcFiles = await Promise.all(build.lods.map(async lod => ({ filename: lod.model.replace('.glb', '.qc.json'), bytes: Buffer.from(JSON.stringify({
    qcPassed: true, assetId, modelSha256: lod.sha256, lod: lod.level, lods, builtLods: lods, externalTextures: [],
    validationErrors: 0, validationWarnings: 0, reviewHash, bounds: runtimeBounds(lod.bounds_blender), previewImages: previews,
    rig: { skeletonId, bones: build.bones.length, maximumInfluences: 4 }, animationClips: build.motion, defaultAnimation: 'idle',
    motionInspection: JSON.parse(await fs.readFile(path.join(root, 'review', `${key}_lod${lod.level}_motion_inspection.json`), 'utf8')),
    limitations: ['In-place motion; world authority uses the measured playback speeds.', 'No runtime fur cards or procedural primitive substitutes.'],
    reviewEvidence: fresh, frozenSource: releaseRepo, technical: technical.lods.find(l => l.level === lod.level),
  }, null, 2) + '\n') })));
  const assembly = renders.find(r => r.level === 0 && r.state === 'rest' && r.view === 'full');
  const detail = renders.find(r => r.level === 0 && r.view === 'head');
  const manifest = { schemaVersion: 1, assetId, displayName: definition.name, category: 'prop', model: lods[0].model, qc: qcFiles[0].filename,
    runtime: { staticKey: key, skinned: true }, compatibility: { bodyFamily: `fauna_${kind}`, bodyVariant: kind.endsWith('_doe') ? 'f' : 'neutral', skeletonId, bindPoseId: 'authored_anatomical_rest_v1' },
    hashes: { modelSha256: lods[0].sha256, qcSha256: sha(qcFiles[0].bytes), previews: { assembly: assembly.image_sha256, detail: detail.image_sha256 } },
    previews: { assembly: `${releaseRepo}/${assembly.image.replaceAll('\\', '/')}`, detail: `${releaseRepo}/${detail.image.replaceAll('\\', '/')}` },
    review: { reviewedBy: approved.reviewedBy, reviewedAt: approved.reviewedAt, reviewHash }, provenance, approvalState: 'approved' };
  validateApprovedManifest(manifest, key);
  changes.push({ key, blueprint, manifest, qcFiles, release, fresh, reviewBytes: approvalBytes, build });
}

// Verify every selected asset first. Frozen copies keep the accepted source and
// review usable while later species continue to evolve in the authoring folder.
for (const change of changes) {
  for (const [file, digest] of Object.entries(change.fresh.files)) {
    const bytes = await fs.readFile(localPath(root, file)); assert.equal(sha(bytes), digest, 'Source changed during publication');
    const target = localPath(change.release, file); await fs.mkdir(path.dirname(target), { recursive: true });
    try { await fs.writeFile(target, bytes, { flag: 'wx' }); } catch (error) { if (error.code !== 'EEXIST') throw error; assert.equal(await fileSha(target), digest, 'Frozen source collision'); }
  }
  const frozenReview = path.join(change.release, 'review/visual_review.json');
  try { await fs.writeFile(frozenReview, change.reviewBytes, { flag: 'wx' }); }
  catch (error) { if (error.code !== 'EEXIST') throw error; assert.equal(await fileSha(frozenReview), sha(change.reviewBytes), 'Frozen approval collision'); }
  const writes = [
    [path.join(repo, 'scripts/blender-character-pipeline/data/asset-blueprints', `${change.key}.asset.json`), Buffer.from(JSON.stringify(change.blueprint, null, 2) + '\n')],
    [path.join(repo, 'scripts/blender-character-pipeline/data/approved-assets', `${change.key}.approved.json`), Buffer.from(JSON.stringify(change.manifest, null, 2) + '\n')],
    ...await Promise.all(change.build.lods.map(async lod => [path.join(repo, 'public/assets/models', lod.model), await fs.readFile(path.join(change.release, 'runtime', lod.model))])),
    ...change.qcFiles.map(qc => [path.join(repo, 'public/assets/models', qc.filename), qc.bytes]),
  ];
  for (const [file, bytes] of writes) {
    try {
      const previous = await fs.readFile(file);
      if (sha(previous) !== sha(bytes)) {
        const archive = path.join(root, 'previous-accepted', `${sha(previous)}-${path.basename(file)}`);
        await fs.mkdir(path.dirname(archive), { recursive: true }); await fs.writeFile(archive, previous);
      }
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
    await fs.writeFile(file, bytes);
  }
}
console.log(`Published ${changes.length} reviewed fauna package(s); registry and GM catalog remain unchanged.`);
