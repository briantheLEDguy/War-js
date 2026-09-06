// Validate isolated civic exports; promote only against a matching visual review.
import { readFile, writeFile, copyFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const { default: validator } = await import('gltf-validator').catch(() => import('../.deps/node_modules/gltf-validator/index.js'));

const work = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.resolve(work, '../../..');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const json = async file => JSON.parse(await readFile(file, 'utf8'));
const save = (file, data) => writeFile(file, `${JSON.stringify(data, null, 2)}\n`);
const reportFile = path.join(work, 'civic-build-report.json');
const report = await json(reportFile);
const results = [];
for (const asset of report) for (const lod of asset.lods) {
  const bytes = await readFile(path.join(work, 'runtime', lod.model));
  const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: lod.model });
  const doc = JSON.parse(bytes.subarray(20, 20+bytes.readUInt32LE(12)).toString());
  const errors = validation.issues.messages.filter(m => m.severity === 0).map(m => m.message);
  if (sha(bytes) !== lod.sha256) errors.push('Build hash mismatch');
  if (lod.triangles > 30000 || lod.bytes > 3_000_000) errors.push('Decoration budget exceeded');
  if (doc.materials.length > 8) errors.push('Material budget exceeded');
  if (lod.level && lod.triangles >= asset.lods[lod.level-1].triangles) errors.push('LOD did not reduce');
  for (const mesh of doc.meshes) for (const p of mesh.primitives) {
    if (p.attributes.NORMAL === undefined || p.attributes.TEXCOORD_0 === undefined) errors.push('Missing normals or UVs');
  }
  results.push({ model:lod.model, errors, warnings:validation.issues.numWarnings });
}
await save(path.join(work, 'civic-validation.json'), results);
console.log(`${results.length} civic GLBs; ${results.reduce((n,r) => n+r.errors.length,0)} errors`);
if (results.some(r => r.errors.length)) throw new Error('Civic validation failed');
if (process.argv.includes('--publish')) {
  const reviewFile = path.join(work, 'review/civic-review.json');
  const review = await json(reviewFile);
  const preview = 'authoring/blender/aegis-city/review/civic-exports.png';
  if (review.buildSha256 !== sha(await readFile(reportFile)) || review.previewSha256 !== sha(await readFile(path.join(root,preview)))) {
    throw new Error('Visual review no longer matches the build or preview');
  }
  const reviewHash = sha(await readFile(reviewFile));
  const blueprints = path.join(root, 'scripts/blender-character-pipeline/data/asset-blueprints');
  const approved = path.join(root, 'scripts/blender-character-pipeline/data/approved-assets');
  const models = path.join(root, 'public/assets/models');
  const template = await json(path.join(blueprints, 'prop_aegis_lantern.asset.json'));
  for (const asset of report) {
    const name = `prop_aegis_${asset.kind}`, assetId = `prop.aegis.${asset.kind}`;
    const bp = structuredClone(template);
    Object.assign(bp, {assetId, displayName:`Aegis ${asset.kind.replaceAll('_',' ')}`, sets:['aegis_civic_decorations']});
    bp.runtime = {staticKey:`aegis_${asset.kind}`};
    bp.output.model = `${name}.glb`;
    bp.generator.copyFrom = `authoring/blender/aegis-city/runtime/${name}.glb`;
    bp.geometry.originRule = asset.kind === 'civic_wall_lantern' ? 'custom' : 'root_grounded';
    // Wall lanterns are facade-mounted. Placement supplies the mounting height.
    bp.geometry.lods = asset.lods.map(l => ({name:`LOD${l.level}`,triTarget:l.triangles,screenCoverageMin:[.2,.08,0][l.level]}));
    bp.materials = {...bp.materials,master:'MM_AegisCivic',textureSet:'civic_material_factors',channels:['baseColor','roughness','metallic']};
    bp.provenance = {...bp.provenance,source:'authoring/blender/aegis-city/tools/build_civic.py',promptIds:['aegis_rich_civic_v1'],referencePackId:'original_civic_trade_and_canal_motifs'};
    bp.qc.maxTris = 30000;
    bp.qc.maxFileSizeMb = 3;
    for (const lod of asset.lods) {
      await copyFile(path.join(work,'runtime',lod.model),path.join(models,lod.model));
      await save(path.join(models,lod.model.replace('.glb','.qc.json')), {
        qcPassed:true,assetId,modelSha256:lod.sha256,lod,lods:asset.lods,validationErrors:0,reviewHash,
      });
    }
    await save(path.join(blueprints,`${name}.asset.json`),bp);
    await save(path.join(approved,`${name}.approved.json`),{
      schemaVersion:1,assetId,displayName:bp.displayName,category:'prop',model:`${name}.glb`,qc:`${name}.qc.json`,runtime:bp.runtime,
      compatibility:{bodyFamily:'static_architecture',bodyVariant:'neutral',skeletonId:'none',bindPoseId:'none'},
      hashes:{modelSha256:asset.lods[0].sha256,qcSha256:sha(await readFile(path.join(models,`${name}.qc.json`))),previews:{assembly:review.previewSha256}},
      previews:{assembly:preview},review:{reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,reviewHash},provenance:bp.provenance,approvalState:'approved',
    });
  }
  console.log(`Published ${report.length} reviewed civic assets.`);
}
