import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { validateTerrain, assertRenderReceipt, requiredViews, textureFile, sha } from './validate.mjs';
import { validateApprovedManifest } from '../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
const work=path.dirname(fileURLToPath(import.meta.url)), root=path.resolve(work,'../../..');
const read=async p=>JSON.parse(await readFile(p,'utf8'));
const save=(p,value)=>writeFile(p,JSON.stringify(value,null,2)+'\n');
const { report, evidence } = await validateTerrain();
const reportFile=path.join(work,'build-report.json');
const reviewFile=path.join(work,'review/visual_review.json');
async function renderEvidence() {
  const receiptBytes=await readFile(path.join(work,'review/render_receipt.json'));
  const previewSha256s={};
  for(const file of requiredViews)previewSha256s[file]=sha(await readFile(path.join(work,'review',file)));
  assertRenderReceipt(JSON.parse(receiptBytes),evidence,previewSha256s);
  return {buildSha256:evidence.buildSha256,sourceSha256:evidence.sourceSha256,renderReceiptSha256:sha(receiptBytes),previewSha256s};
}
if(process.argv.includes('--prepare-review')) {
  const current=await renderEvidence();
  let previous;try{previous=await read(reviewFile);}catch(error){if(error.code!=='ENOENT')throw error;}
  const unchanged=previous&&Object.entries(current).every(([key,value])=>JSON.stringify(previous[key])===JSON.stringify(value));
  await save(reviewFile,{...current,status:unchanged?previous.status:'pending',reviewedBy:unchanged?previous.reviewedBy:'',reviewedAt:unchanged?previous.reviewedAt:'',notes:unchanged?previous.notes:''});
}
if(process.argv.includes('--publish')) {
  const reviewBytes=await readFile(reviewFile),review=JSON.parse(reviewBytes),reviewHash=sha(reviewBytes);
  assert.equal(review.status,'approved');assert(review.reviewedBy && review.reviewedAt && !Number.isNaN(Date.parse(review.reviewedAt)));
  for(const [key,value]of Object.entries(await renderEvidence()))assert.deepEqual(review[key],value,`Reviewed ${key} changed`);
  const blueprintDir=path.join(root,'scripts/blender-character-pipeline/data/asset-blueprints');
  const template=await read(path.join(blueprintDir,'prop_aegis_lantern.asset.json'));
  const models=path.join(root,'public/assets/models'),textures=path.join(root,'public/assets/textures/cinderfen_terrain');
  const preview='authoring/blender/cinderfen-terrain/review/terrain_overview_lod0.png';
  const writes=[];
  const copied=new Set();
  for(const asset of report) {
    const assetId=`prop.${asset.key.replaceAll('_','.')}`;
    const bp=structuredClone(template);
    Object.assign(bp,{assetId,displayName:asset.key.replaceAll('_',' '),sets:['cinderfen_terrain'],runtime:{staticKey:asset.key},lifecycle:{status:'approved',reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,notes:'Reviewed authored terrain; authoritative ground uses the exact source Float32 survey.'}});
    bp.output={model:asset.lods[0].model,artifactDir:'authoring/blender/cinderfen-terrain/runtime'};
    bp.generator={kind:'copyExisting',copyFrom:`authoring/blender/cinderfen-terrain/runtime/${asset.lods[0].model}`};
    bp.geometry.lods=asset.lods.map(lod=>({name:`LOD${lod.level}`,triTarget:lod.triangles,screenCoverageMin:[.2,.08,0][lod.level]}));
    bp.materials={master:'MM_CinderfenTerrain',textureSet:'cinderfen_terrain',channels:['baseColor','roughness','metallic','normal'],maxTextureResolution:1024};
    bp.qc={...bp.qc,maxDrawCalls:3,maxMeshObjects:3,maxTris:150000,maxFileSizeMb:16,requiresPreview:true};
    bp.collision={policy:'none',primitives:[]};
    bp.provenance={...bp.provenance,createdBy:'original_authored_blender_meshes',source:'authoring/blender/cinderfen-terrain/build_terrain.py',promptIds:['cinderfen_peat_albedo_v1','cinderfen_causeway_albedo_v1'],referencePackId:'original_cinderfen_survey',aiStages:['art_direction','texture_source','mesh_authoring']};
    const lods=asset.lods.map(lod=>({...lod,externalTextures:evidence.models.find(model=>model.model===lod.model).externalTextures}));
    let primaryQcBytes;
    for(const lod of lods) {
      const bytes=await readFile(path.join(work,'runtime',lod.model));
      assert.equal(sha(bytes),lod.sha256,'Export changed during publication preparation');
      for(const image of lod.externalTextures) {
        const filename=path.basename(image.uri);
        if(!copied.has(filename)){
          const imageBytes=await readFile(textureFile(image.uri));assert.equal(sha(imageBytes),image.sha256,'Texture changed during publication preparation');
          writes.push([path.join(textures,filename),imageBytes]);copied.add(filename);
        }
      }
      writes.push([path.join(models,lod.model),bytes]);
      const qcBytes=Buffer.from(JSON.stringify({qcPassed:true,assetId,modelSha256:lod.sha256,lod:lod.level,lods,externalTextures:lod.externalTextures,validationErrors:0,validationWarnings:0,reviewHash,sourceSha256:review.sourceSha256,renderReceiptSha256:review.renderReceiptSha256,previewImages:requiredViews.map(file=>'authoring/blender/cinderfen-terrain/review/'+file)},null,2)+'\n');
      writes.push([path.join(models,lod.model.replace('.glb','.qc.json')),qcBytes]);
      if(lod.level===0)primaryQcBytes=qcBytes;
    }
    writes.push([path.join(blueprintDir,asset.key+'.asset.json'),Buffer.from(JSON.stringify(bp,null,2)+'\n')]);
    const qc=asset.lods[0].model.replace('.glb','.qc.json');
    const manifest={
      schemaVersion:1,assetId,displayName:bp.displayName,category:'prop',model:asset.lods[0].model,qc,runtime:bp.runtime,
      compatibility:{bodyFamily:'static_architecture',bodyVariant:'neutral',skeletonId:'none',bindPoseId:'none'},
      hashes:{modelSha256:asset.lods[0].sha256,qcSha256:sha(primaryQcBytes),previews:{assembly:review.previewSha256s['terrain_overview_lod0.png']}},
      previews:{assembly:preview},review:{reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,reviewHash},provenance:bp.provenance,approvalState:'approved',
    };
    validateApprovedManifest(manifest,asset.key+' publication candidate');
    writes.push([path.join(root,'scripts/blender-character-pipeline/data/approved-assets',asset.key+'.approved.json'),Buffer.from(JSON.stringify(manifest,null,2)+'\n')]);
  }
  assert.equal(sha(await readFile(reportFile)),evidence.buildSha256,'Build changed during publication preparation');
  assert.equal(sha(await readFile(path.join(work,'terrain-source.json'))),evidence.sourceSha256,'Survey changed during publication preparation');
  for(const [file,bytes]of writes){await mkdir(path.dirname(file),{recursive:true});await writeFile(file,bytes);}
  console.log(`Published ${report.length} reviewed terrain sectors and ${copied.size} shared textures. Compile the runtime registry separately.`);
}
