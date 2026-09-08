import { readFile, writeFile, copyFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
const {default:validator}=await import('gltf-validator').catch(()=>import('../../aegis-city/.deps/node_modules/gltf-validator/index.js'));
const work=fileURLToPath(new URL('../',import.meta.url)),root=path.resolve(work,'../../..');
const read=async p=>JSON.parse(await readFile(p,'utf8'));
const write=(p,v)=>writeFile(p,JSON.stringify(v,null,2)+'\n');
const hash=b=>createHash('sha256').update(b).digest('hex');
const report=await read(path.join(work,'build-report.json')),results=[];
const wanted=process.argv.find(v=>v.startsWith('--assets='))?.split('=')[1].split(',');
for(const asset of report.filter(a=>!wanted||wanted.includes(a.kind))) {
  const textures=new Set();
  assert.deepEqual(asset.lods.map(l=>l.level),[0,1,2]);
  for(const lod of asset.lods) {
    const bytes=await readFile(path.join(work,'runtime',lod.model));assert.equal(hash(bytes),lod.sha256);
    const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
    const triangles=doc.meshes.reduce((n,m)=>n+m.primitives.reduce((n,p)=>n+doc.accessors[p.indices].count/3,0),0);
    assert.equal(triangles,lod.triangles);assert(triangles<=30000);
    for(const image of doc.images??[]) {
      assert(/^\.\.\/textures\/riftspire_city\/[a-f0-9]+\.png$/.test(image.uri));textures.add(image.uri);
      const png=await readFile(path.resolve(work,'runtime',image.uri));assert.equal(png.readUInt32BE(16),2048);assert.equal(png.readUInt32BE(20),2048);
      assert.equal(hash(png).slice(0,20),path.basename(image.uri,'.png'),'Texture content hash mismatch');
    }
    for(const mesh of doc.meshes)for(const p of mesh.primitives)assert(p.attributes.TEXCOORD_0!==undefined&&p.attributes.NORMAL!==undefined);
    const validation=await validator.validateBytes(new Uint8Array(bytes),{uri:lod.model,externalResourceFunction:async uri=>new Uint8Array(await readFile(path.resolve(work,'runtime',uri)))});
    results.push({model:lod.model,triangles,sha256:lod.sha256,errors:validation.issues.messages.filter(m=>m.severity===0),warnings:validation.issues.numWarnings});
  }
  if(!process.argv.includes('--publish'))continue;
  assert(results.every(r=>r.errors.length===0),'GLB errors prevent publication');
  const reviewPath=path.join(work,'review',`${asset.kind}-review.json`),review=await read(reviewPath);
  assert(review.reviewedBy&&review.observations);assert.deepEqual(review.modelSha256s,asset.lods.map(l=>l.sha256),'Stale visual review');
  for(const [file,sha] of Object.entries(review.previewSha256s))assert.equal(hash(await readFile(path.join(work,'review',file))),sha);
  const preview=Object.keys(review.previewSha256s)[0];assert(preview);
  const reviewHash=hash(await readFile(reviewPath));
  await mkdir(path.join(root,'public/assets/textures/riftspire_city'),{recursive:true});
  for(const uri of textures)await copyFile(path.resolve(work,'runtime',uri),path.resolve(root,'public/assets/models',uri));
  for(const lod of asset.lods) {
    await copyFile(path.join(work,'runtime',lod.model),path.join(root,'public/assets/models',lod.model));
    await write(path.join(root,'public/assets/models',lod.model.replace('.glb','.qc.json')),{qcPassed:true,assetId:`prop.riftspire.${asset.kind}`,modelSha256:lod.sha256,lod,lods:asset.lods,validationErrors:0,reviewHash,textureMaxDimension:2048});
  }
  const bp=await read(path.join(root,'scripts/blender-character-pipeline/data/asset-blueprints/prop_aegis_citadel.asset.json'));
  Object.assign(bp,{assetId:`prop.riftspire.${asset.kind}`,displayName:`Riftspire ${asset.kind.replaceAll('_',' ')}`,sets:['riftspire_crater_city'],runtime:{staticKey:`riftspire_${asset.kind}`},output:{model:asset.lods[0].model,artifactDir:'authoring/blender/riftspire-city/runtime'},generator:{kind:'copyExisting',copyFrom:`authoring/blender/riftspire-city/runtime/${asset.lods[0].model}`}});
  bp.geometry.lods=asset.lods.map(l=>({name:`LOD${l.level}`,triTarget:l.triangles,screenCoverageMin:[.2,.08,0][l.level]}));
  bp.materials={...bp.materials,master:'MM_RiftspirePbr',textureSet:'riftspire_city'};bp.qc.maxTris=30000;bp.qc.maxDrawCalls=10;bp.qc.maxMeshObjects=10;
  bp.provenance={createdBy:'original_procedural_blender_generation',aiAssisted:true,aiStages:['art_direction','procedural_geometry'],promptIds:['riftspire_suspended_crater_v1'],referencePackId:'original_riftspire_crater',similarityReview:'not_required',source:'authoring/blender/riftspire-city/tools/build.py'};
  await write(path.join(root,'scripts/blender-character-pipeline/data/asset-blueprints',`prop_riftspire_${asset.kind}.asset.json`),bp);
  const qc=asset.lods[0].model.replace('.glb','.qc.json');
  await write(path.join(root,'scripts/blender-character-pipeline/data/approved-assets',`prop_riftspire_${asset.kind}.approved.json`),{schemaVersion:1,assetId:bp.assetId,displayName:bp.displayName,category:'prop',model:asset.lods[0].model,qc,runtime:bp.runtime,compatibility:{bodyFamily:'static_architecture',bodyVariant:'neutral',skeletonId:'none',bindPoseId:'none'},hashes:{modelSha256:asset.lods[0].sha256,qcSha256:hash(await readFile(path.join(root,'public/assets/models',qc))),previews:{assembly:review.previewSha256s[preview]}},previews:{assembly:`authoring/blender/riftspire-city/review/${preview}`},review:{reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,reviewHash},provenance:bp.provenance,approvalState:'approved'});
}
await write(path.join(work,'validation.json'),results);
console.log(`${results.length} GLBs checked; ${results.filter(r=>r.errors.length).length} with errors.`);
assert(results.every(r=>r.errors.length===0),JSON.stringify(results.filter(r=>r.errors.length)));
