/** Promote only the exact eight-model inventory accepted by the integration review. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { validateApprovedManifest } from '../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),root=path.resolve(work,'../../..');
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const bytes=file=>fs.readFile(path.join(work,file));
const read=async file=>JSON.parse(await bytes(file));
const save=async(file,value)=>{await fs.mkdir(path.dirname(file),{recursive:true});await fs.writeFile(file,JSON.stringify(value,null,2)+'\n');};
const inventoryBytes=await bytes('review/final_inventory.json'),inventory=JSON.parse(inventoryBytes);
const contractBytes=await bytes('source/runtime_contract.json'),contract=JSON.parse(contractBytes);
const validation=await read('review/package_validation.json');
assert(validation.passed);assert.equal(inventory.assets.length,8);
assert.equal(hash(await bytes(inventory.contact_sheet)),inventory.contact_sheet_sha256);
for(const asset of inventory.assets){
  assert.equal(hash(await bytes(asset.master)),asset.master_sha256);
  assert.deepEqual(asset.lods.map(lod=>lod.level),[0,1,2]);
  for(const lod of asset.lods){
    assert.equal(hash(await bytes(lod.model)),lod.sha256);
    assert.equal(hash(await bytes(lod.image)),lod.image_sha256);
    const check=validation.records.find(record=>record.sha256===lod.sha256);
    assert(check && check.errors===0);assert.equal(check.warnings,lod.validation_warnings);
  }
}
const animation=contract.assets.frontier_teamster_animations;
assert.equal(hash(await bytes('runtime/'+animation.model)),animation.sha256);
const evidence={inventorySha256:hash(inventoryBytes),contractSha256:hash(contractBytes),contactSheetSha256:inventory.contact_sheet_sha256,
  animationSha256:animation.sha256};
const reviewFile=path.join(work,'review/accepted_review.json');
if(process.argv.includes('--prepare'))await save(reviewFile,{...evidence,status:'pending',reviewedBy:'',reviewedAt:'',notes:''});
if(!process.argv.includes('--publish'))process.exit(0);
const reviewBytes=await fs.readFile(reviewFile),review=JSON.parse(reviewBytes),reviewHash=hash(reviewBytes);
assert.equal(review.status,'approved');assert(review.reviewedBy && !Number.isNaN(Date.parse(review.reviewedAt)));
for(const [key,value]of Object.entries(evidence))assert.equal(review[key],value,`Changed ${key}`);
const template=JSON.parse(await fs.readFile(path.join(root,'scripts/blender-character-pipeline/data/asset-blueprints/frontier_cinderfen_dwelling.asset.json'),'utf8'));
const metadata={};
for(const asset of inventory.assets){
  const key=asset.asset_id,definition=contract.assets[key],assetId=`prop.frontier.${key.slice(9)}`;
  const lods=asset.lods.map(lod=>({level:lod.level,model:path.basename(lod.model),sha256:lod.sha256,triangles:lod.triangles,bytes:lod.bytes}));
  const primary=lods[0],bp=structuredClone(template),horse=key==='frontier_draft_horse';
  const pack=key==='frontier_supply_wagon'?{model:animation.model,sha256:animation.sha256,skeletonId:animation.skeletonId,bindPoseId:animation.bindPoseId}:undefined;
  bp.assetId=assetId;bp.displayName=definition.builder.displayName;bp.sets=['orvr_frontier_authored_siege'];
  bp.runtime={staticKey:key};
  bp.output={model:primary.model,artifactDir:'authoring/blender/orvr-frontier/runtime'};
  bp.generator={kind:'copyExisting',copyFrom:`authoring/blender/orvr-frontier/runtime/${primary.model}`};
  bp.geometry={originRule:'authored_assembly_anchor',upAxis:'+Y',forwardAxis:'+Z',lods:lods.map(lod=>({name:`LOD${lod.level}`,triTarget:lod.triangles,screenCoverageMin:[.2,.08,0][lod.level]}))};
  bp.materials={master:'MM_FrontierAuthoredPbr',textureSet:key,channels:['baseColor','roughness','metallic','normal','occlusion'],maxTextureResolution:2048};
  const primaryValidation=validation.records.find(record=>record.sha256===primary.sha256);
  bp.rigging={skinned:horse,requiredClips:primaryValidation.clips};
  bp.collision={policy:'authoritative_orvr_hull',primitives:[]};
  bp.qc={allowNonManifold:true,allowUvOverlap:true,maxDrawCalls:40,maxMeshObjects:40,
    maxTris:Math.max(...lods.map(lod=>lod.triangles)),maxFileSizeMb:Math.ceil(Math.max(...lods.map(lod=>lod.bytes))/1e6),requiresPreview:true,requiresSkinnedMeshes:horse};
  bp.provenance={createdBy:'original_authored_mesh_control_cages',aiAssisted:true,aiStages:['art_direction','mesh_authoring','material_painting','animation_authoring','actual_export_review'],
    referencePackId:'original_frontier_siege_v1',similarityReview:'not_required',source:'authoring/blender/orvr-frontier/review/final_inventory.json',sourceSha256:evidence.inventorySha256};
  bp.lifecycle={status:'approved',reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,notes:`Exact inventory accepted. ${asset.limitations.join(' ')}`};
  let qcHash;
  for(const lod of lods){
    const record=validation.records.find(row=>row.sha256===lod.sha256);
    const qc={assetId,qcPassed:true,modelSha256:lod.sha256,lod:lod.level,lods,validationErrors:record.errors,validationWarnings:record.warnings,
      warningCodes:record.warningCodes,reviewHash,inventorySha256:evidence.inventorySha256,contractSha256:evidence.contractSha256,
      previewImages:asset.lods.map(item=>'authoring/blender/orvr-frontier/'+item.image),...(pack?{animationPack:pack}:{})};
    const qcBytes=Buffer.from(JSON.stringify(qc,null,2)+'\n');
    await fs.writeFile(path.join(root,'public/assets/models',lod.model),await bytes('runtime/'+lod.model));
    await fs.writeFile(path.join(root,'public/assets/models',lod.model.replace('.glb','.qc.json')),qcBytes);
    if(lod.level===0)qcHash=hash(qcBytes);
  }
  const manifest={schemaVersion:1,assetId,displayName:bp.displayName,category:'prop',model:primary.model,qc:primary.model.replace('.glb','.qc.json'),
    runtime:{...bp.runtime,...(horse?{skinned:true}:{}),...(pack?{animationPack:pack}:{})},
    compatibility:{bodyFamily:horse?'draft_horse':'static_architecture',bodyVariant:'neutral',skeletonId:horse?'draft_horse_rig':'none',bindPoseId:horse?'draft_horse_rest_v1':'none'},
    hashes:{modelSha256:primary.sha256,qcSha256:qcHash,previews:{assembly:asset.lods[0].image_sha256}},
    previews:{assembly:'authoring/blender/orvr-frontier/'+asset.lods[0].image},review:{reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,reviewHash},
    provenance:bp.provenance,approvalState:'approved'};
  validateApprovedManifest(manifest,key);
  await save(path.join(root,'scripts/blender-character-pipeline/data/asset-blueprints',key+'.asset.json'),bp);
  await save(path.join(root,'scripts/blender-character-pipeline/data/approved-assets',key+'.approved.json'),manifest);
  metadata[key]={runtimeReady:true,modelSha256:primary.sha256,label:bp.displayName,group:horse?'Frontier Wildlife':key.includes('kit')?'Frontier Equipment':'Frontier Siege and Supplies',
    defaultScale:1,colliderSpace:'model',defaultAnimation:horse?'idle':key==='frontier_field_catapult'?'catapult_fire':undefined};
}
await fs.writeFile(path.join(root,'public/assets/models',animation.model),await bytes('runtime/'+animation.model));
await save(path.join(work,'builder-metadata.json'),{assets:metadata});
console.log('Published eight reviewed models, 24 LODs, the signed driver animation and GM metadata. Compile the registry separately.');
