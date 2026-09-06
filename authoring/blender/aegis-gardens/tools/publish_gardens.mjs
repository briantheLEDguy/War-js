// Validate delivery geometry, shared PBR textures and reviewed hashes before promotion.
import { readFile, writeFile, copyFile, mkdir, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const { default: validator } = await import('../../aegis-city/.deps/node_modules/gltf-validator/index.js');
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const root=path.resolve(work,'../../..');
const sha=b=>createHash('sha256').update(b).digest('hex');
const json=async p=>JSON.parse(await readFile(p,'utf8'));
const save=(p,d)=>writeFile(p,JSON.stringify(d,null,2)+'\n');
const reportFile=path.join(work,'build-report.json');
const report=await json(reportFile);
const results=[];
const materialSignatures=new Map();
for(const asset of report) for(const lod of asset.lods){
  const file=path.join(work,'runtime',lod.model),bytes=await readFile(file);
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  const validation=await validator.validateBytes(new Uint8Array(bytes),{
    uri:lod.model,externalResourceFunction:uri=>readFile(path.resolve(path.dirname(file),uri)),
  });
  const errors=validation.issues.messages.filter(m=>m.severity===0).map(m=>m.message);
  if(sha(bytes)!==lod.sha256)errors.push('Build hash mismatch');
  if(lod.triangles>30000||bytes.length>4_000_000)errors.push('Decoration budget exceeded');
  if(doc.materials.length>8)errors.push('Material budget exceeded');
  for(const material of doc.materials){
    const signature=JSON.stringify(material);
    if(materialSignatures.has(material.name)&&materialSignatures.get(material.name)!==signature){
      errors.push(`Shared material parameters differ: ${material.name}`);
    }
    materialSignatures.set(material.name,signature);
  }
  if(lod.level&&lod.triangles>=asset.lods[lod.level-1].triangles)errors.push('LOD did not reduce');
  for(const mesh of doc.meshes)for(const p of mesh.primitives){
    if(p.attributes.NORMAL===undefined||p.attributes.TEXCOORD_0===undefined)errors.push('Missing normals or UVs');
  }
  for(const im of doc.images??[]){
    if(!im.uri?.startsWith('../textures/aegis_gardens/'))errors.push('Texture not shared externally');
  }
  results.push({model:lod.model,errors,warnings:validation.issues.numWarnings});
}
await save(path.join(work,'validation.json'),results);
console.log(`${results.length} garden asset GLBs; ${results.reduce((n,r)=>n+r.errors.length,0)} errors`);
if(results.some(r=>r.errors.length))throw new Error('Citadel furnishing validation failed');
if(process.argv.includes('--publish')){
  const reviewFile=path.join(work,'review/review.json'),review=await json(reviewFile);
  const preview='authoring/blender/aegis-gardens/review/all-exports.png';
  if(review.buildSha256!==sha(await readFile(reportFile))||review.previewSha256!==sha(await readFile(path.join(root,preview)))){
    throw new Error('Visual review no longer matches the build or preview');
  }
  for(const [name,hash]of Object.entries(review.heroSha256??{})){
    if(hash!==sha(await readFile(path.join(work,'review',name+'.png'))))throw new Error(`Stale ${name} preview`);
  }
  const reviewHash=sha(await readFile(reviewFile));
  const blueprints=path.join(root,'scripts/blender-character-pipeline/data/asset-blueprints');
  const approved=path.join(root,'scripts/blender-character-pipeline/data/approved-assets');
  const models=path.join(root,'public/assets/models');
  const textureOut=path.join(root,'public/assets/textures/aegis_gardens');
  await mkdir(textureOut,{recursive:true});
  const textures = new Set();
  for(const asset of report) for(const lod of asset.lods) {
    const bytes=await readFile(path.join(work,'runtime',lod.model));
    const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
    for(const image of doc.images ?? []) textures.add(path.basename(image.uri));
  }
  for(const file of textures){
    await copyFile(path.join(work,'textures/aegis_gardens',file),path.join(textureOut,file));
  }
  const template=await json(path.join(blueprints,'prop_aegis_lantern.asset.json'));
  for(const asset of report){
    const name=`prop_aegis_${asset.kind}`,assetId=`prop.aegis.${asset.kind}`;
    const bp=structuredClone(template);
    Object.assign(bp,{assetId,displayName:`Aegis ${asset.kind.replaceAll('_',' ')}`,sets:['aegis_gardens']});
    bp.runtime={staticKey:`aegis_${asset.kind}`};
    bp.output={model:`${name}.glb`,artifactDir:'authoring/blender/aegis-gardens/runtime'};
    bp.generator.copyFrom=`authoring/blender/aegis-gardens/runtime/${name}.glb`;
    bp.geometry.originRule='root_grounded';
    bp.geometry.lods=asset.lods.map(l=>({name:`LOD${l.level}`,triTarget:l.triangles,screenCoverageMin:[.2,.08,0][l.level]}));
    bp.materials={...bp.materials,master:'MM_AegisGardens',textureSet:'aegis_gardens',
      channels:['baseColor','roughness','metallic','normal'],maxTextureResolution:2048};
    bp.provenance={...bp.provenance,source:'authoring/blender/aegis-gardens/tools/build_gardens.py',
      promptIds:['aegis_gardens_v1'],referencePackId:'original_city_horticulture'};
    bp.qc={...bp.qc,maxTris:30000,maxFileSizeMb:4,maxDrawCalls:8,maxMeshObjects:1};
    for(const lod of asset.lods){
      await copyFile(path.join(work,'runtime',lod.model),path.join(models,lod.model));
      await save(path.join(models,lod.model.replace('.glb','.qc.json')),{
        qcPassed:true,assetId,modelSha256:lod.sha256,lod,lods:asset.lods,validationErrors:0,reviewHash,envelope:asset.envelope,
      });
    }
    await save(path.join(blueprints,`${name}.asset.json`),bp);
    await save(path.join(approved,`${name}.approved.json`),{
      schemaVersion:1,assetId,displayName:bp.displayName,category:'prop',model:`${name}.glb`,qc:`${name}.qc.json`,runtime:bp.runtime,
      compatibility:{bodyFamily:'static_architecture',bodyVariant:'neutral',skeletonId:'none',bindPoseId:'none'},
      hashes:{modelSha256:asset.lods[0].sha256,qcSha256:sha(await readFile(path.join(models,`${name}.qc.json`))),previews:{assembly:review.previewSha256}},
      previews:{assembly:preview},review:{reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,reviewHash},
      provenance:bp.provenance,approvalState:'approved',
    });
  }
  console.log(`Published ${report.length} reviewed garden assets.`);
}

