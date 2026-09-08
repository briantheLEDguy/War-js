/** Actual binary validation and explicit, exact-hash internal publication. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import validator from 'gltf-validator';
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const repo=path.resolve(work,'../../..');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const hashFile=async p=>hash(await fs.readFile(p));
const read=async p=>JSON.parse(await fs.readFile(p,'utf8'));
const save=(p,value)=>fs.writeFile(p,JSON.stringify(value,null,2)+'\n');
const sourcePath=path.join(work,'source/nature.json');
const source=await read(sourcePath),sourceHash=await hashFile(sourcePath);
const geometryOnly=process.argv.includes('--geometry-only'),publish=process.argv.includes('--publish');
if(geometryOnly&&publish)throw Error('Publication requires all actual reimport evidence.');
const issues=[],models=[],assets=[];
const check=(value,message)=>{if(!value)issues.push(message);};
const toolHash=await hashFile(path.join(work,'tools/build_nature.py'));
const paintHash=await hashFile(path.join(work,'textures/paint-records.json'));
const paint=await read(path.join(work,'textures/paint-records.json'));
let alderJoins,alderJoinView;
check(paint.painterSha256===await hashFile(path.join(work,'tools/paint_nature.py')),'Stale painter provenance');
for(const item of paint.records)for(const channel of Object.values(item.channels))check(channel.sha256===await hashFile(path.join(work,channel.file)),'Changed painted channel: '+channel.file);
if(!geometryOnly){
  const provenance=await read(path.join(work,'source/provenance.json'));
  check(provenance.sourceSha256===sourceHash,'Stale original mesh provenance');
  for(const [file,digest] of Object.entries({...provenance.tools,...provenance.retainedUtilityReferences,...provenance.retainedExporterSources}))check(digest===await hashFile(path.join(work,file)),'Changed retained tool: '+file);
  alderJoins=await read(path.join(work,'review/alder-joins.json'));
  check(alderJoins.sourceSha256===sourceHash,'Changed source since actual alder join audit');
  check(alderJoins.toolSha256===await hashFile(path.join(work,'tools/audit_alder_joins.py')),'Changed alder join audit tool');
  check(alderJoins.models.length===3&&alderJoins.models.every(m=>m.failed.length===0&&m.sockets.length===15),'Unseated main alder branch/root socket');
  alderJoinView=await read(path.join(work,'review/alder-join-view.json'));
  check(alderJoinView.toolSha256===await hashFile(path.join(work,'tools/review_alder_joins.py')),'Changed lower alder join reviewer');
  check(alderJoinView.imageSha256===await hashFile(path.join(work,'review',alderJoinView.image)),'Changed lower alder join image');
}
for(const [key,definition] of Object.entries(source.assets)){
  const built=await read(path.join(work,'review',key+'_build.json'));
  check(built.source_sha256===sourceHash,key+': changed original source');
  if(built.builder_sha256!==toolHash){
    let retained;try{retained=await hashFile(path.join(work,'review/tool_sources','build_nature_'+built.builder_sha256+'.py'));}catch(error){if(error.code!=='ENOENT')throw error;}
    check(retained===built.builder_sha256,key+': changed exporter without an exact retained source');
  }
  check(built.paint_records_sha256===paintHash,key+': changed painter receipt');
  check(built.master_sha256===await hashFile(path.join(work,built.master)),key+': changed editable master');
  check(JSON.stringify(built.contract)===JSON.stringify(definition.contract),key+': changed placement contract');
  for(const [file,digest] of Object.entries(built.texture_sha256))check(digest===await hashFile(path.join(work,file)),key+': changed texture '+file);
  built.maxTextureResolution=key.includes('alder')?2048:1024;
  check(JSON.stringify(built.lods.map(l=>l.level))==='[0,1,2]',key+': three ordered LODs required');
  for(const lod of built.lods){
    const file=path.join(work,'runtime',lod.model),bytes=await fs.readFile(file);
    const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
    check(hash(bytes)===lod.sha256&&bytes.length===lod.bytes,lod.model+': changed binary');
    const meshTris=doc.meshes.map(mesh=>mesh.primitives.reduce((sum,p)=>sum+doc.accessors[p.indices].count/3,0));
    const triangles=doc.nodes.reduce((sum,node)=>sum+(node.mesh===undefined?0:meshTris[node.mesh]),0);
    check(lod.triangles===triangles,lod.model+': triangle measurement differs');
    check(lod.materials===doc.materials.length,lod.model+': material measurement differs');
    check(lod.level===0||triangles<built.lods[lod.level-1].triangles,lod.model+': LOD must reduce triangles');
    check(triangles<=[110000,40000,8000][lod.level],lod.model+': ecology triangle budget exceeded');
    lod.meshes=doc.meshes.length;lod.drawCalls=doc.meshes.reduce((sum,m)=>sum+m.primitives.length,0);
    check(lod.drawCalls<=3,lod.model+': material batch budget exceeded');
    for(const material of doc.materials){
      check(!!material.pbrMetallicRoughness?.baseColorTexture&&!!material.pbrMetallicRoughness?.metallicRoughnessTexture&&!!material.normalTexture&&!!material.occlusionTexture,lod.model+': incomplete PBR');
      check(!material.alphaMode||material.alphaMode==='OPAQUE',lod.model+': foliage must retain actual opaque geometry');
    }
    for(const mesh of doc.meshes)for(const p of mesh.primitives)for(const semantic of ['POSITION','NORMAL','TANGENT','TEXCOORD_0'])check(p.attributes[semantic]!==undefined,lod.model+': missing '+semantic);
    check(!doc.animations?.length,lod.model+': static ecology must not claim animation');
    check(doc.buffers.length===1&&!doc.buffers[0].uri,lod.model+': external buffers forbidden');
    const uris=[...new Set(doc.images.map(image=>image.uri))].sort();
    check(doc.images.every(image=>image.uri?.startsWith('../textures/cinderfen_nature/')&&image.bufferView===undefined),lod.model+': shared texture reference required');
    check(JSON.stringify(uris)===JSON.stringify(Object.keys(lod.external_textures??{}).sort()),lod.model+': unsigned texture URI');
    lod.externalTextures=[];
    for(const [uri,digest] of Object.entries(lod.external_textures??{})){
      check(/^\.\.\/textures\/cinderfen_nature\/[a-f0-9]{64}\.png$/.test(uri),lod.model+': unsafe texture URI');
      check(digest===await hashFile(path.resolve(path.dirname(file),uri)),lod.model+': changed texture '+uri);
      lod.externalTextures.push({uri,sha256:digest});
    }
    check(lod.texture_packing?.output_glb_sha256===lod.sha256,lod.model+': texture packing receipt mismatch');
    check(lod.texture_packing?.tool_sha256===await hashFile(path.join(work,'tools/share_textures.py')),lod.model+': packing tool changed');
    if(key.includes('alder')){
      const projection=lod.bark_projection;
      check(projection?.toolSha256===await hashFile(path.join(work,'tools/bake_bark_projection.py')),lod.model+': changed continuous bark projection tool');
      check(projection?.geometrySha256Before===projection?.geometrySha256After&&!!projection?.geometrySha256Before,lod.model+': bark projection altered geometry');
      const retained=await read(path.join(work,'review',`alder_bark_projection_lod${lod.level}.json`));
      check(JSON.stringify(retained)===JSON.stringify(projection),lod.model+': changed retained bark projection receipt');
      for(const channel of ['baseColor','normal','orm']){
        const map=projection?.channels?.[channel];check(!!map,lod.model+': missing baked bark '+channel);if(!map)continue;
        const image=await fs.readFile(path.join(work,map.file));
        check(hash(image)===map.sha256,lod.model+': changed baked bark '+channel);
        check(map.resolution===[2048,1024,512][lod.level]&&image.readUInt32BE(16)===map.resolution&&image.readUInt32BE(20)===map.resolution,lod.model+': incorrect bark atlas dimensions');
      }
    }
    const checked=await validator.validateBytes(new Uint8Array(bytes),{uri:lod.model,maxIssues:1000,externalResourceFunction:uri=>fs.readFile(path.resolve(path.dirname(file),uri))});
    check(checked.issues.numErrors===0&&checked.issues.numWarnings===0,lod.model+': Khronos '+checked.issues.numErrors+' errors/'+checked.issues.numWarnings+' warnings');
    await save(path.join(work,'review',lod.model+'.validation.json'),checked);
    if(!geometryOnly){
      const imported=await read(path.join(work,'review',lod.model.replace('.glb','_reimport.json')));
      check(imported.sha256===lod.sha256,lod.model+': reimport depicts old GLB');
      check(imported.reviewer_sha256===await hashFile(path.join(work,'tools/review_nature.py')),lod.model+': changed actual-export reviewer');
      check(imported.audit.totalBoundaryEdges===0&&imported.audit.totalMultiFaceEdges===0&&imported.audit.totalLooseEdges===0,lod.model+': nonmanifold positional topology');
      if(key.includes('alder'))check(alderJoins.models.find(m=>m.model===lod.model)?.sha256===lod.sha256,lod.model+': stale actual trunk join audit');
      lod.topology=imported.audit;lod.reviewImages={};
      for(const mode of ['neutral','gameplay',...(lod.level===0?['detail']:[])]){
        const view=imported.views[mode];check(!!view,lod.model+': missing '+mode+' review');if(!view)continue;
        check(view.sha256===await hashFile(path.join(work,'review',view.image)),lod.model+': changed '+mode+' image');lod.reviewImages[view.image]=view.sha256;
        if(mode==='gameplay')check(view.camera.distance_m===(key.includes('alder')?[18,45,100]:[8,22,50])[lod.level],lod.model+': incorrect measured review distance');
      }
      for(const side of ['minimum','maximum'])for(let axis=0;axis<3;axis++)check(Math.abs(imported.audit.bounds_z_up[side][axis]-lod.bounds_z_up[side][axis])<.0001,lod.model+': exported bounds differ from master');
      lod.preview=imported.views.neutral.image;lod.preview_sha256=imported.views.neutral.sha256;
      if(key.includes('alder')&&lod.level===0){
        check(alderJoinView.modelSha256===lod.sha256,lod.model+': lower join view depicts an old GLB');
        lod.reviewImages[alderJoinView.image]=alderJoinView.imageSha256;
      }
    }
    models.push({model:lod.model,sha256:lod.sha256,triangles,errors:checked.issues.numErrors,warnings:checked.issues.numWarnings});
  }
  assets.push(built);
}
await save(path.join(work,'validation.json'),{passed:issues.length===0,completeReimportReview:!geometryOnly,issues,models});
await save(path.join(work,'build-report.json'),assets);
console.log(JSON.stringify({models:models.length,issues,completeReimportReview:!geometryOnly},null,2));
if(issues.length)throw Error('Nature package validation failed.');
const note='Original botanical paths, asymmetrical section records, thick blade outlines and basalt fracture surveys remain editable in the Blender masters. The main alder bark is one joined shell; small closed organs overlap at seated shoot attachments; no canopy cards or primitive constructors are used. Positional topology welds only glTF material/UV/normal seam splits at one micrometre and requires zero boundary/multi-face/loose edges. Shared painted fields intentionally overlap UVs across repeated botanical organs and stone faces. Three original LODs reduce organs and surface detail while retaining primary planted forms. Static models have no wind or skeletal animation. Internal actual-export visual acceptance is required before publication.';
const blueprint=asset=>({assetId:'prop.frontier.'+asset.asset_id.replace('frontier_',''),displayName:asset.displayName,category:'prop',version:'1.0.0',sets:['cinderfen_authored_nature'],runtime:{staticKey:asset.asset_id},output:{model:asset.lods[0].model,artifactDir:'authoring/blender/cinderfen-nature/runtime'},generator:{kind:'copyExisting',copyFrom:'authoring/blender/cinderfen-nature/runtime/'+asset.lods[0].model},geometry:{originRule:'root_grounded',upAxis:'+Y',forwardAxis:'+Z',lods:asset.lods.map(l=>({name:'LOD'+l.level,triTarget:l.triangles,screenCoverageMin:[.15,.05,0][l.level]}))},materials:{master:'MM_CinderfenNature',textureSet:'cinderfen_authored_nature',channels:['baseColor','roughness','metallic','normal','occlusion'],maxTextureResolution:asset.maxTextureResolution},rigging:{skinned:false,requiredClips:[]},collision:{policy:asset.contract.colliders.length?'authored_mass_segments':'nonblocking_foliage',primitives:[]},compatibility:{occupiesSlots:['prop'],requires:[],conflictsWith:[]},provenance:{createdBy:'original_authored_mesh_control_cages',aiAssisted:true,aiStages:['art_direction','literal_control_cage_authoring','material_painting','blender_finishing','lod_authoring','technical_validation'],referencePackId:'original_cinderfen_nature_v1',similarityReview:'not_required',author:'Codex ecology authoring',source:'authoring/blender/cinderfen-nature/source/nature.json',sourceSha256:sourceHash},qc:{allowNonManifold:false,allowUvOverlap:true,maxTris:asset.lods[0].triangles,maxFileSizeMb:Math.ceil(asset.lods[0].bytes/1048576)+1,maxDrawCalls:asset.lods[0].drawCalls,maxMeshObjects:asset.lods[0].meshes,requiresSkinnedMeshes:false,requiresPreview:true,expectedHeightM:asset.lods[0].bounds_z_up.maximum[2]-asset.lods[0].bounds_z_up.minimum[2],heightToleranceM:.03},lifecycle:{status:'review_pending',notes:note}});
const blueprintDir=path.join(repo,'scripts/blender-character-pipeline/data/asset-blueprints');
if(publish){
  const reviewPath=path.join(work,'review/review.json'),review=await read(reviewPath);
  if(review.approved!==true||!review.reviewedBy||!review.reviewedAt||Number.isNaN(Date.parse(review.reviewedAt)))throw Error('Named, dated internal visual acceptance is required.');
  if(review.buildSha256!==await hashFile(path.join(work,'build-report.json')))throw Error('Review belongs to a different build.');
  if(review.alderJoinsSha256!==await hashFile(path.join(work,'review/alder-joins.json')))throw Error('Review must bind the actual alder join audit.');
  for(const name of ['all-exports.png','gameplay-exports.png'])if(review.contactSheets?.[name]!==await hashFile(path.join(work,'review',name)))throw Error('Unreviewed contact sheet: '+name);
  for(const asset of assets)for(const lod of asset.lods)for(const [name,digest] of Object.entries(lod.reviewImages))if(review.images?.[name]!==digest)throw Error('Unreviewed actual-export image: '+name);
  const reviewHash=await hashFile(reviewPath),modelsDir=path.join(repo,'public/assets/models'),approvedDir=path.join(repo,'scripts/blender-character-pipeline/data/approved-assets');
  await fs.mkdir(path.join(modelsDir,'previews'),{recursive:true});await fs.mkdir(path.join(repo,'public/assets/textures/cinderfen_nature'),{recursive:true});
  const textureNames=new Set(assets.flatMap(a=>a.lods.flatMap(l=>l.externalTextures.map(t=>path.basename(t.uri)))));
  for(const name of textureNames)await fs.copyFile(path.join(work,'textures/cinderfen_nature',name),path.join(repo,'public/assets/textures/cinderfen_nature',name));
  for(const asset of assets){
    const bp=blueprint(asset);bp.lifecycle={status:'approved',reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,notes:note.replace('Internal actual-export visual acceptance is required before publication.','Accepted internally at the exact retained build/model/image hashes.')};
    const preview='public/assets/models/previews/'+asset.asset_id+'.png';await fs.copyFile(path.join(work,'review',asset.lods[0].preview),path.join(repo,preview));
    for(const lod of asset.lods){
      await fs.copyFile(path.join(work,'runtime',lod.model),path.join(modelsDir,lod.model));
      await save(path.join(modelsDir,lod.model.replace('.glb','.qc.json')),{qcPassed:true,assetId:bp.assetId,modelSha256:lod.sha256,validationErrors:0,validationWarnings:0,reviewHash,totalTris:lod.triangles,meshCount:lod.drawCalls,nonManifoldEdges:0,missingRequiredClips:[],pbrChannels:bp.materials.channels,maxTextureResolution:asset.maxTextureResolution,lods:asset.lods.map(l=>({level:l.level,model:l.model,sha256:l.sha256,triangles:l.triangles,externalTextures:l.externalTextures})),externalTextures:lod.externalTextures,previewImages:[preview],bounds:lod.bounds_z_up,placementContract:asset.contract,topologyPolicy:note});
    }
    await save(path.join(blueprintDir,asset.asset_id+'.asset.json'),bp);
    const qc=asset.lods[0].model.replace('.glb','.qc.json');await save(path.join(approvedDir,asset.asset_id+'.approved.json'),{schemaVersion:1,assetId:bp.assetId,displayName:bp.displayName,category:'prop',model:asset.lods[0].model,qc,runtime:bp.runtime,compatibility:{bodyFamily:'static_architecture',bodyVariant:'neutral',skeletonId:'none',bindPoseId:'none'},hashes:{modelSha256:asset.lods[0].sha256,qcSha256:await hashFile(path.join(modelsDir,qc)),previews:{assembly:asset.lods[0].preview_sha256}},previews:{assembly:preview},review:{reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,reviewHash},provenance:bp.provenance,approvalState:'approved'});
  }
  console.log('Published four internally accepted ecology assets; global registry untouched.');
}else for(const asset of assets){
  const file=path.join(blueprintDir,asset.asset_id+'.asset.json');let old;try{old=await read(file);}catch(error){if(error.code!=='ENOENT')throw error;}
  if(old?.lifecycle?.status!=='approved')await save(file,blueprint(asset));
}
const buildHash=await hashFile(path.join(work,'build-report.json'));
// A validation-only rerun must not withdraw unchanged accepted GM entries.
// Preserve readiness only when the previous package and published manifests
// still bind these exact models, QC files and the same review receipt.
let runtimeReady=publish;
if(!publish&&!geometryOnly){
  try{
    const previous=await read(path.join(work,'builder-metadata.json'));
    if(previous.runtimeReady===true&&previous.buildSha256===buildHash&&previous.sourceSha256===sourceHash){
      const reviewHash=await hashFile(path.join(work,'review/review.json'));let valid=true;
      for(const asset of assets){
        const approved=await read(path.join(repo,'scripts/blender-character-pipeline/data/approved-assets',asset.asset_id+'.approved.json'));
        valid&&=approved.approvalState==='approved'&&approved.hashes.modelSha256===asset.lods[0].sha256&&approved.review.reviewHash===reviewHash;
        valid&&=approved.hashes.qcSha256===await hashFile(path.join(repo,'public/assets/models',approved.qc));
        for(const lod of asset.lods)valid&&=lod.sha256===await hashFile(path.join(repo,'public/assets/models',lod.model));
      }
      runtimeReady=valid;
    }
  }catch(error){if(error.code!=='ENOENT')throw error;}
}
const metadata={schemaVersion:1,units:'metres',upAxis:'+Y',frontAxis:'+Z',sourceSha256:sourceHash,buildSha256:buildHash,runtimeReady,assets:{}};
for(const asset of assets){
  const bounds=asset.lods[0].bounds_z_up;const boundsYUp={minimum:[bounds.minimum[0],bounds.minimum[2],-bounds.maximum[1]],maximum:[bounds.maximum[0],bounds.maximum[2],-bounds.minimum[1]]};
  metadata.assets[asset.asset_id]={label:asset.displayName,group:'Cinderfen Nature',kind:asset.contract.kind,model:asset.lods[0].model,modelSha256:asset.lods[0].sha256,runtimeReady,defaultScale:{x:1,y:1,z:1},colliderSpace:'model',footprint:{width:boundsYUp.maximum[0]-boundsYUp.minimum[0],depth:boundsYUp.maximum[2]-boundsYUp.minimum[2],chainAxis:'x'},boundsYUp,placementDatum:'Planted at model Y0; root and stone toes intentionally extend below ground.',colliders:asset.contract.colliders,walkableSurfaces:[],cameraSolid:asset.contract.cameraSolid};
}
await save(path.join(work,'builder-metadata.json'),metadata);
