/** Validate hash-bound technical and visual evidence; publish only with explicit --publish. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {validateApprovedManifest} from '../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const repo=path.resolve(root,'../../..');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const read=async file=>JSON.parse(await fs.readFile(file,'utf8'));
const save=(file,value)=>fs.writeFile(file,JSON.stringify(value,null,2)+'\n');
await import('./validate_nature.mjs');
assert(!process.exitCode,'Technical validation failed; nothing can be published.');
const validation=await read(path.join(root,'review/validation.json'));
const wanted=process.argv.find(arg=>arg.startsWith('--assets='))?.slice(9).split(',').map(kind=>kind.startsWith('frontier_')?kind:`frontier_sunmeadow_${kind}`);
const selected=validation.assets.filter(asset=>!wanted||wanted.includes(asset.asset));
assert(selected.length>0,'No matching Sunmeadow assets');
if(wanted)assert(selected.length===new Set(wanted).size,'An asset selector is unknown.');
const reviewPath=path.join(root,'review/visual_review.json');
const packageRelative=path.relative(repo,root).replaceAll('\\','/');

if(process.argv.includes('--prepare-review')){
  let previous={assets:{}};try{previous=await read(reviewPath);}catch(error){if(error.code!=='ENOENT')throw error;}
  const assets={...previous.assets};
  for(const asset of selected){
    const buildPath=path.join(root,'review',`${asset.asset}_build.json`);
    const renders=await read(path.join(root,'review',`${asset.asset}_renders.json`));
    assert.deepEqual(renders.renders.map(render=>render.level),[0,1,2],`${asset.asset}: complete reimport renders required`);
    for(const render of renders.renders){
      assert.equal(render.model_sha256,asset.lods[render.level].sha256,'Reimport model hash changed');
      assert.equal(sha(await fs.readFile(path.join(root,render.image))),render.image_sha256,'Reimport image hash changed');
    }
    const evidence={buildSha256:sha(await fs.readFile(buildPath)),modelSha256s:asset.lods.map(lod=>lod.sha256),previewSha256s:Object.fromEntries(renders.renders.map(render=>[render.image,render.image_sha256]))};
    const old=assets[asset.asset];
    const unchanged=old&&old.buildSha256===evidence.buildSha256&&JSON.stringify(old.modelSha256s)===JSON.stringify(evidence.modelSha256s)&&JSON.stringify(old.previewSha256s)===JSON.stringify(evidence.previewSha256s);
    assets[asset.asset]={...evidence,status:unchanged?old.status:'pending',reviewedBy:unchanged?old.reviewedBy:'',reviewedAt:unchanged?old.reviewedAt:'',notes:unchanged?old.notes:'Inspect all three actual GLB reimport views, silhouette retention, materials and deployment scale before approval.'};
  }
  await save(reviewPath,{schemaVersion:1,kind:'actual_glb_visual_review',assets});
  console.log('Prepared current review evidence; no asset approval was inferred.');
}

if(process.argv.includes('--publish')){
  const reviewBytes=await fs.readFile(reviewPath);const review=JSON.parse(reviewBytes);const reviewHash=sha(reviewBytes);
  const prepared=[];
  for(const asset of selected){
    const evidence=review.assets?.[asset.asset];assert.equal(evidence?.status,'approved',`${asset.asset}: explicit internal visual approval is required`);
    assert(evidence.reviewedBy&&evidence.reviewedAt&&!Number.isNaN(Date.parse(evidence.reviewedAt)),`${asset.asset}: reviewer identity and date required`);
    assert.equal(evidence.buildSha256,sha(await fs.readFile(path.join(root,'review',`${asset.asset}_build.json`))),'Reviewed build changed');
    assert.deepEqual(evidence.modelSha256s,asset.lods.map(lod=>lod.sha256),'Reviewed binaries changed');
    const renders=await read(path.join(root,'review',`${asset.asset}_renders.json`));
    assert.deepEqual(renders.renders.map(render=>render.level),[0,1,2],'Three reviewed LOD images required');
    for(const render of renders.renders){
      assert.equal(render.model_sha256,asset.lods[render.level].sha256,'A render depicts an older GLB');
      assert.equal(evidence.previewSha256s[render.image],render.image_sha256,'Reviewed image record changed');
      assert.equal(sha(await fs.readFile(path.join(root,render.image))),render.image_sha256,'Reviewed image changed');
    }
    const blueprintPath=path.join(repo,'scripts/blender-character-pipeline/data/asset-blueprints',`${asset.asset}.asset.json`);
    const blueprint=await read(blueprintPath);
    assert.equal(blueprint.runtime.staticKey,asset.asset);assert.equal(blueprint.output.model,asset.lods[0].model);
    const qcFiles=asset.lods.map(lod=>{
      const qc={qcPassed:true,assetId:blueprint.assetId,modelSha256:lod.sha256,lod:lod.level,lods:asset.lods.map(item=>({level:item.level,model:item.model,sha256:item.sha256,triangles:item.triangles})),validationErrors:0,validationWarnings:lod.validationWarnings,reviewHash,bounds:lod.bounds_runtime,limitations:asset.limitations,
        previewImages:renders.renders.map(render=>`${packageRelative}/${render.image.replaceAll('\\','/')}`)};
      return {model:lod.model,filename:lod.model.replace('.glb','.qc.json'),bytes:Buffer.from(JSON.stringify(qc,null,2)+'\n')};
    });
    const preview=renders.renders[0];
    const manifest={schemaVersion:1,assetId:blueprint.assetId,displayName:blueprint.displayName,category:'prop',model:asset.lods[0].model,qc:qcFiles[0].filename,runtime:blueprint.runtime,
      compatibility:{bodyFamily:'static_architecture',bodyVariant:'neutral',skeletonId:'none',bindPoseId:'none'},
      hashes:{modelSha256:asset.lods[0].sha256,qcSha256:sha(qcFiles[0].bytes),previews:{assembly:preview.image_sha256}},
      previews:{assembly:`${packageRelative}/${preview.image.replaceAll('\\','/')}`},
      review:{reviewedBy:evidence.reviewedBy,reviewedAt:evidence.reviewedAt,reviewHash},provenance:blueprint.provenance,approvalState:'approved'};
    validateApprovedManifest(manifest,`${asset.asset} publication candidate`);
    prepared.push({asset,blueprint,blueprintPath,qcFiles,manifest});
  }
  // All selected packages passed before any approved record or public binary is changed.
  const modelDir=path.join(repo,'public/assets/models');const approvedDir=path.join(repo,'scripts/blender-character-pipeline/data/approved-assets');
  await fs.mkdir(modelDir,{recursive:true});await fs.mkdir(approvedDir,{recursive:true});
  for(const item of prepared){
    for(const qc of item.qcFiles){
      await fs.copyFile(path.join(root,'runtime',qc.model),path.join(modelDir,qc.model));
      await fs.writeFile(path.join(modelDir,qc.filename),qc.bytes);
    }
    item.blueprint.lifecycle={status:'approved',reviewedBy:item.manifest.review.reviewedBy,reviewedAt:item.manifest.review.reviewedAt,notes:`Internal actual-export visual review ${item.manifest.review.reviewedAt}; ${item.asset.limitations.join(' ')}`};
    await save(item.blueprintPath,item.blueprint);
    await save(path.join(approvedDir,`${item.asset.asset}.approved.json`),item.manifest);
  }
  console.log(`Published ${prepared.length} reviewed Sunmeadow assets. Textures are embedded in the GLBs; no external texture copies are needed. Runtime registry was not compiled.`);
}else console.log('Validation only. Global approved records, public models and runtime registry remain unchanged.');
