/** Publish completed workshop exports with the user's standing asset approval. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { validateApprovedManifest } from '../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
import { validateJsonSchema } from '../../../../scripts/blender-character-pipeline/tools/json-schema-validator.mjs';
import { standingWorldAssetApproval } from '../../../../scripts/blender-character-pipeline/tools/world-asset-approval.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repo = path.resolve(root, '../../..');
const relative = path.relative(repo, root).replaceAll('\\', '/');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const hashFile = async file => hash(await fs.readFile(file));
const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));
const save = async (file, value) => {
  const pending = `${file}.${process.pid}.pending`;
  await fs.writeFile(pending, JSON.stringify(value, null, 2) + '\n');
  await fs.rename(pending, file);
};
const copy = async (from, to) => {
  await fs.mkdir(path.dirname(to), { recursive: true });
  const pending = `${to}.${process.pid}.pending`;
  await fs.copyFile(from, pending); await fs.rename(pending, to);
};

await import('./validate_items.mjs');
assert(!process.exitCode, 'Workshop technical checks failed; publication stopped.');
const validation = await read(path.join(root, 'validation.json'));
assert(validation.technicalReady && !validation.issues.length, 'Complete actual-export validation required.');
const contract = await read(path.join(root, 'builder-contract.json'));
assert.equal(contract.sourceSha256, validation.sourceSha256);
assert.equal(contract.measurementToolSha256, await hashFile(path.join(root, 'tools/measure_builder.py')));
const prepared = [];
for (const asset of validation.assets) {
  const key = asset.asset, build = await read(path.join(root, 'review', `${key}_build.json`));
  const measured = contract.assets[key];
  assert(measured?.colliders.length && measured.approachSource, `${key}: measured collision/frontage required`);
  assert.equal(measured.sourceMasterSha256, build.lods[0].source_master_sha256);
  const evidence = { sourceSha256: validation.sourceSha256, buildSha256: asset.buildSha256,
    contractSha256: await hashFile(path.join(root, 'builder-contract.json')),
    validationSha256: await hashFile(path.join(root, 'validation.json')),
    modelSha256s: build.lods.map(lod => lod.sha256), images: {} };
  for (const lod of build.lods) {
    const review = await read(path.join(root, 'review', lod.model.replace('.glb', '_reimport.json')));
    for (const view of Object.values(review.views)) evidence.images[`${relative}/review/${view.image}`] = view.sha256;
  }
  const approval = standingWorldAssetApproval(evidence);
  const reviewHash = hash(Buffer.from(JSON.stringify(approval, null, 2) + '\n'));
  const assetId = `prop.frontier.${key.replace('frontier_', '')}`;
  const provenance = { createdBy: 'original_authored_mesh_control_cages', aiAssisted: true,
    aiStages: ['mesh_authoring', 'material_painting', 'lod_authoring', 'technical_validation'],
    referencePackId: 'original_universal_siege_workshop_v1', similarityReview: 'not_required',
    source: `${relative}/source/items.json`, sourceSha256: validation.sourceSha256 };
  const lods = build.lods.map(({ level, model, sha256, triangles, bytes, external_textures }) => ({ level, model, sha256, triangles, bytes,
    externalTextures: Object.entries(external_textures).map(([uri, sha256]) => ({ uri, sha256 })) }));
  const qc = lods.map(lod => ({ assetId, qcPassed: true, modelSha256: lod.sha256, lod: lod.level, lods,
    totalTris: lod.triangles, validationErrors: 0, validationWarnings: 0, warningCodes: [], reviewHash,
    collisionContractSha256: evidence.contractSha256, previewImages: Object.keys(evidence.images),
    limitations: ['Static scenery; repair and ammunition interactions are not implemented.'] }));
  const preview = `${relative}/review/${key}_lod0_neutral.png`;
  const manifest = { schemaVersion: 1, assetId, displayName: build.displayName, category: 'prop',
    model: lods[0].model, qc: lods[0].model.replace('.glb', '.qc.json'), runtime: { staticKey: key },
    compatibility: { bodyFamily: 'static_architecture', bodyVariant: 'neutral', skeletonId: 'none', bindPoseId: 'none' },
    hashes: { modelSha256: lods[0].sha256, qcSha256: hash(Buffer.from(JSON.stringify(qc[0], null, 2) + '\n')),
      previews: { assembly: evidence.images[preview] } }, previews: { assembly: preview },
    review: { reviewedBy: approval.reviewedBy, reviewedAt: approval.reviewedAt, reviewHash }, provenance, approvalState: 'approved' };
  validateApprovedManifest(manifest, key);
  const blueprint = { assetId, displayName: build.displayName, category: 'prop', version: '1.0.0',
    sets: ['universal_siege_workshop'], runtime: manifest.runtime,
    output: { model: lods[0].model, artifactDir: `${relative}/runtime` },
    generator: { kind: 'copyExisting', copyFrom: `${relative}/runtime/${lods[0].model}` },
    geometry: { originRule: 'root_grounded', upAxis: '+Y', forwardAxis: '+Z',
      lods: lods.map(lod => ({ name: `LOD${lod.level}`, triTarget: lod.triangles, screenCoverageMin: [.15, .05, 0][lod.level] })) },
    materials: { master: 'MM_FrontierWorkshop', textureSet: 'frontier_workshop_items',
      channels: ['baseColor', 'roughness', 'metallic', 'normal', 'occlusion'], maxTextureResolution: 2048 },
    rigging: { skinned: false, requiredClips: [] }, collision: { policy: 'authored_mass_segments', primitives: [] },
    compatibility: { occupiesSlots: ['prop'], requires: [], conflictsWith: [] }, provenance,
    qc: { allowNonManifold: false, allowUvOverlap: false, maxTris: lods[0].triangles,
      maxFileSizeMb: 8, maxDrawCalls: 3, maxMeshObjects: 3, requiresSkinnedMeshes: false, requiresPreview: true,
      expectedHeightM: measured.boundsYUp.maximum[1], heightToleranceM: .03 },
    lifecycle: { status: 'approved', reviewedBy: approval.reviewedBy, reviewedAt: approval.reviewedAt,
      notes: 'Standing user approval; three technically validated original LODs, retained editable masters, full PBR and measured part collision. Static scenery.' } };
  assert.deepEqual(validateJsonSchema(await read(path.join(repo, 'scripts/blender-character-pipeline/data/asset-blueprint.schema.json')), blueprint), []);
  prepared.push({ key, build, manifest, blueprint, qc, approval, measured });
}
if (process.argv.includes('--publish')) {
  const metadata = { schemaVersion: 1, units: 'metres', assets: {} };
  for (const item of prepared) {
    for (const lod of item.build.lods) {
      await copy(path.join(root, 'runtime', lod.model), path.join(repo, 'public/assets/models', lod.model));
      for (const [uri, digest] of Object.entries(lod.external_textures)) {
        const from = path.resolve(root, 'runtime', uri), to = path.resolve(repo, 'public/assets/models', uri);
        assert.equal(await hashFile(from), digest, 'Texture changed during publication'); await copy(from, to);
      }
      await save(path.join(repo, 'public/assets/models', lod.model.replace('.glb', '.qc.json')), item.qc[lod.level]);
    }
    await save(path.join(root, 'review', `${item.key}_publication.json`), item.approval);
    await save(path.join(repo, 'scripts/blender-character-pipeline/data/asset-blueprints', `${item.key}.asset.json`), item.blueprint);
    await save(path.join(repo, 'scripts/blender-character-pipeline/data/approved-assets', `${item.key}.approved.json`), item.manifest);
    metadata.assets[item.key] = { ...item.measured, runtimeReady: true, modelSha256: item.manifest.hashes.modelSha256 };
  }
  await save(path.join(root, 'builder-metadata.json'), metadata);
  console.log(`Published ${prepared.length} universal workshop props with three LODs and measured GM collision. Compile registry, campaign and GM catalog next.`);
} else console.log('Workshop validation passed; pass --publish to update runtime files.');
