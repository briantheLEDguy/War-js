/** Deliver existing user-approved fauna without rebuilding or inventing missing motion. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import validator from 'gltf-validator';
import { Box3, Matrix4, Quaternion, Vector3 } from 'three';
import { standingWorldAssetApproval } from '../../../../scripts/blender-character-pipeline/tools/world-asset-approval.mjs';
import { validateApprovedManifest } from '../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
import { validateJsonSchema } from '../../../../scripts/blender-character-pipeline/tools/json-schema-validator.mjs';

const repo = process.cwd();
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const read = async file => JSON.parse(await fs.readFile(path.join(repo, file), 'utf8'));
const write = async (file, bytes) => { const target = path.join(repo, file); await fs.mkdir(path.dirname(target), { recursive: true });
  await fs.writeFile(target + '.pending', bytes); await fs.rename(target + '.pending', target); };
const json = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');
const schema = await read('scripts/blender-character-pipeline/data/asset-blueprint.schema.json');
const definitions = [
  ['red_fox', 'Sunmeadow red fox', 'sunmeadow-fauna', 3],
  ['brown_hare', 'Sunmeadow brown hare', 'sunmeadow-fauna', 3],
  ['barrow_wolf', 'Sunmeadow barrow wolf', 'sunmeadow-fauna', 3],
  ['skylark', 'Sunmeadow skylark', 'sunmeadow-skylark', 1],
];
for (const [species, name, packageName, count] of definitions) {
  const key = `frontier_sunmeadow_${species}`, work = `authoring/blender/${packageName}`;
  const files = new Map(), lods = [], diagnostics = [];
  const retain = async file => { const bytes = await fs.readFile(path.join(repo, file)); files.set(file, { sha256: hash(bytes), bytes: bytes.length }); return bytes; };
  const receipt = species === 'skylark' ? 'review/skylark_v2_build.json' : `review/${key}_build.json`;
  const build = JSON.parse(await retain(`${work}/${receipt}`));
  await retain(`${work}/${build.master}`);
  let bounds, clips = [];
  for (let level = 0; level < count; level++) {
    const model = `${key}_lod${level}.glb`, bytes = await retain(`${work}/runtime/${model}`);
    const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
    const checked = await validator.validateBytes(new Uint8Array(bytes), { uri: model });
    assert.equal(checked.issues.numErrors, 0, `${model}: invalid glTF`);
    assert((doc.images ?? []).every(image => !image.uri), 'Backlog delivery requires embedded textures');
    assert(doc.meshes?.length && doc.skins?.length, 'Actual authored meshes and rig required');
    // Retain the historic non-root skin warning honestly. These exports have
    // identity armature parents and are displayed in their exported rest pose.
    assert(checked.issues.messages.filter(m => m.severity === 1).every(m => m.code === 'NODE_SKINNED_MESH_NON_ROOT'), 'Unresolved export warning');
    const triangles = doc.meshes.flatMap(mesh => mesh.primitives).reduce((n, p) => n + doc.accessors[p.indices].count / 3, 0);
    lods.push({ level, model, sha256: hash(bytes), triangles, externalTextures: [] });
    diagnostics.push({ model, errors: checked.issues.numErrors, warnings: checked.issues.numWarnings,
      messages: checked.issues.messages.filter(m => m.severity <= 1) });
    if (level === 0) {
      clips = (doc.animations ?? []).map(clip => clip.name);
      const box = new Box3();
      const visit = (index, parent) => { const node = doc.nodes[index];
        const matrix = node.matrix ? new Matrix4().fromArray(node.matrix) : new Matrix4().compose(
          new Vector3().fromArray(node.translation ?? [0,0,0]), new Quaternion().fromArray(node.rotation ?? [0,0,0,1]), new Vector3().fromArray(node.scale ?? [1,1,1]));
        matrix.premultiply(parent);
        for (const p of doc.meshes[node.mesh]?.primitives ?? []) { const a = doc.accessors[p.attributes.POSITION];
          box.union(new Box3(new Vector3().fromArray(a.min), new Vector3().fromArray(a.max)).applyMatrix4(matrix)); }
        for (const child of node.children ?? []) visit(child, matrix);
      };
      for (const node of doc.scenes[doc.scene ?? 0].nodes) visit(node, new Matrix4());
      bounds = { min: box.min.toArray(), max: box.max.toArray() };
    }
  }
  const preview = `${work}/review/${species === 'skylark' ? 'runtime_lod0_idle_0_quarter.png' : `${key}_lod0_reimport.png`}`;
  await retain(preview);
  await retain('scripts/blender-character-pipeline/data/world-asset-approval.json');
  const review = standingWorldAssetApproval({ asset: key, files: Object.fromEntries(files), diagnostics,
    limitations: ['Rest-pose scenery; locomotion/combat behavior is unfinished.', ...(count === 1 ? ['Only the current LOD0 exists; use short-distance culling.'] : [])] });
  const reviewHash = hash(json(review)), release = `${work}/releases/${key}/${reviewHash.slice(0,20)}`;
  for (const [file, expected] of files) {
    const bytes = await fs.readFile(path.join(repo, file)); assert.equal(hash(bytes), expected.sha256);
    await write(`${release}/files/${file}`, bytes);
  }
  await write(`${release}/approval.json`, json(review));
  const frozen = file => `${release}/files/${file}`;
  const assetId = `prop.frontier.sunmeadow.${species}`, skeletonId = `sunmeadow_${species}_anatomical_v1`;
  const provenance = { createdBy: 'original_authored_fauna', author: 'Codex regional world authoring', aiAssisted: true,
    aiStages: ['anatomy', 'mesh_authoring', 'materials', 'export_validation'],
    source: frozen(`${work}/${build.master}`), sourceSha256: files.get(`${work}/${build.master}`).sha256,
    referencePackId: 'sunmeadow_fauna', similarityReview: 'not_required' };
  const blueprint = { assetId, displayName: name, category: 'prop', version: '1.0.0', sets: ['sunmeadow_authored_fauna'],
    runtime: { staticKey: key }, output: { model: lods[0].model, artifactDir: frozen(`${work}/runtime`) },
    generator: { kind: 'copyExisting', copyFrom: frozen(`${work}/runtime/${lods[0].model}`) },
    geometry: { originRule: 'ground_beneath_body', upAxis: '+Y', forwardAxis: '+Z', bodyFamily: `fauna_${species}`, skeletonId,
      bindPoseId: 'authored_anatomical_rest_v1', lods: lods.map(l => ({ name: `LOD${l.level}`, triTarget: l.triangles, screenCoverageMin: [.2,.06,0][l.level] })) },
    materials: { master: 'MM_SunmeadowAuthoredPelt', textureSet: key, channels: ['baseColor','normal','roughness','metallic'], maxTextureResolution: 4096 },
    rigging: { skinned: true, maxInfluences: 4, requiredClips: [] }, compatibility: { occupiesSlots: ['prop'], requires: [], conflictsWith: [] }, provenance,
    qc: { allowNonManifold: true, allowUvOverlap: true, maxDrawCalls: 32, maxMeshObjects: 32, maxFileSizeMb: 32,
      maxTris: lods[0].triangles, requiresSkinnedMeshes: true, requiresPreview: true },
    lifecycle: { status: 'approved', reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash, notes: review.notes } };
  assert.deepEqual(validateJsonSchema(schema, blueprint), []);
  const qcRecords = lods.map(lod => ({ name: lod.model.replace('.glb','.qc.json'), bytes: json({
    qcPassed: true, assetId, modelSha256: lod.sha256, builtLods: lods, externalTextures: [], bounds,
    validationErrors: 0, validationWarnings: diagnostics[lod.level].warnings, animationClips: clips,
    reviewHash, previewImages: [frozen(preview)], limitations: review.evidence.limitations, validation: diagnostics[lod.level],
  }) }));
  const manifest = { schemaVersion: 1, assetId, displayName: name, category: 'prop', model: lods[0].model, qc: qcRecords[0].name,
    runtime: { staticKey: key, skinned: true }, compatibility: { bodyFamily: `fauna_${species}`, bodyVariant: 'neutral', skeletonId, bindPoseId: 'authored_anatomical_rest_v1' },
    hashes: { modelSha256: lods[0].sha256, qcSha256: hash(qcRecords[0].bytes), previews: { front: files.get(preview).sha256 } },
    previews: { front: frozen(preview) }, review: { reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash }, provenance, approvalState: 'approved' };
  validateApprovedManifest(manifest);
  for (const lod of lods) await write(`public/assets/models/${lod.model}`, await fs.readFile(path.join(repo, frozen(`${work}/runtime/${lod.model}`))));
  for (const qc of qcRecords) await write(`public/assets/models/${qc.name}`, qc.bytes);
  await write(`scripts/blender-character-pipeline/data/asset-blueprints/${key}.asset.json`, json(blueprint));
  await write(`scripts/blender-character-pipeline/data/approved-assets/${key}.approved.json`, json(manifest));
  const metadataPath = `${work}/builder-metadata.json`; let metadata = { schemaVersion: 1, assets: {} };
  try { metadata = await read(metadataPath); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  metadata.assets[key] = { runtimeReady: true, modelSha256: lods[0].sha256, defaultAnimation: '', defaultScale: { x: 1, y: 1, z: 1 },
    group: 'Frontier Wildlife', colliders: [], cameraSolid: false };
  await write(metadataPath, json(metadata));
  console.log(`Published ${name}: ${lods.length} saved LODs, rest-pose placement, ${diagnostics.reduce((n,d) => n+d.warnings,0)} recorded glTF warnings.`);
}
