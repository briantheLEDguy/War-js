/** Validate the staged binaries; publishing additionally requires a matching art review. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const root=path.resolve(work,'../../..');
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const read=async name=>JSON.parse(await fs.readFile(name,'utf8'));
const save=(name,data)=>fs.writeFile(name,JSON.stringify(data,null,2)+'\n');
const hashFile=async name=>hash(await fs.readFile(name));
const sourcePath=path.join(work,'source/architecture.json');
const source=await read(sourcePath),sourceHash=await hashFile(sourcePath);
const builderHash=await hashFile(path.join(work,'tools/build_architecture.py'));
const paintHash=await hashFile(path.join(work,'textures/paint_records.json'));
const geometryOnly=process.argv.includes('--geometry-only');
const publishing=process.argv.includes('--publish');
if(geometryOnly&&publishing)throw Error('Publishing requires complete reimport review.');
const geometryAudit=geometryOnly?null:await read(path.join(work,'review/geometry_audit.json'));
const issues=[],report=[],validation=[];
const add=(condition,message)=>{if(!condition)issues.push(message);};
let keepAssembly;
if(!geometryOnly){
  add(geometryAudit.source_sha256===sourceHash,'Changed navigation contract since actual-export geometry audit');
  const provenance=await read(path.join(work,'source/source-provenance.json'));
  add(provenance.source_sha256===sourceHash,'Changed original source since provenance freeze');
  for(const [file,digest] of Object.entries(provenance.tools))add(digest===await hashFile(path.join(work,file)),'Changed tool since provenance freeze: '+file);
  for(const reference of provenance.pipeline_references)add(reference.sha256===await hashFile(path.join(work,reference.retained_copy)),'Changed retained utility reference: '+reference.utility);
  keepAssembly=await read(path.join(work,'review/keep-assembly.json'));
  add(keepAssembly.tool_sha256===await hashFile(path.join(work,'tools/review_keep_assembly.py')),'Changed complete keep review tool');
  add(keepAssembly.source_sha256===await hashFile(path.join(work,'review/keep-assembly-source.json')),'Changed reviewed keep placements');
  add(keepAssembly.placement_source_sha256===await hashFile(path.join(root,'scripts/campaign/cinderfen-environment.mjs')),'Changed Cinderfen environment composer');
  for(const input of keepAssembly.models)add(input.sha256===await hashFile(path.join(work,input.model)),'Changed actual keep assembly model: '+input.model);
  for(const [name,digest] of Object.entries(keepAssembly.previews))add(digest===await hashFile(path.join(work,'review',name)),'Changed complete keep review image: '+name);
  add(keepAssembly.head_hits===0&&keepAssembly.missing_support===0,'Complete keep has obstructed or unsupported walking routes');
  const navigation=await read(path.join(work,'review/placement-navigation.json'));
  add(navigation.placementSourceSha256===keepAssembly.placement_source_sha256&&navigation.missing.length===0,'Missing or stale measured keep access');
  add(navigation.village?.missing.length===0,'Missing measured village service and dwelling access');
  add(navigation.maximumGroundError<=.025,'Architecture ground datum differs from the sampled regional terrain');
  add(navigation.landscapeSourceSha256===await hashFile(path.join(root,'scripts/campaign/cinderfen-landscape.mjs')),'Changed landscape since measured architecture placement');
  add(navigation.toolSha256===await hashFile(path.join(work,'tools/test_placement.mjs')),'Changed navigation review tool');
  for(const input of navigation.sharedMovementSources)add(input.sha256===await hashFile(path.join(root,input.file)),'Changed shared movement since placement review: '+input.file);
  for(const input of navigation.navigationContracts)add(input.assetsSha256===hash(JSON.stringify((await read(path.join(work,input.file))).assets)),'Changed measured navigation asset contract: '+input.file);
}
for(const [assetId,definition] of Object.entries(source.assets)){
  const built=await read(path.join(work,'review',assetId+'_build.json'));
  add(built.source_sha256===sourceHash,assetId+': stale original source');
  add(built.builder_sha256===builderHash,assetId+': stale builder');
  add(built.paint_records_sha256===paintHash,assetId+': stale painted surfaces');
  add(built.master_sha256===await hashFile(path.join(work,built.master)),assetId+': changed Blender master');
  for(const [texture,digest] of Object.entries(built.texture_sha256))add(digest===await hashFile(path.join(work,texture)),assetId+': changed '+texture);
  add(built.lods.length===3,assetId+': requires three LODs');
  for(const lod of built.lods){
    const file=path.join(work,'runtime',lod.model),bytes=await fs.readFile(file);
    const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
    add(hash(bytes)===lod.sha256,lod.model+': changed binary');
    add(bytes.length===lod.bytes,lod.model+': changed file size');
    const counts=doc.meshes.map(mesh=>mesh.primitives.reduce((sum,p)=>sum+(p.indices===undefined?doc.accessors[p.attributes.POSITION].count:doc.accessors[p.indices].count)/3,0));
    const triangles=doc.nodes.reduce((sum,node)=>sum+(node.mesh===undefined?0:counts[node.mesh]),0);
    add(lod.triangles===triangles,lod.model+': triangle count mismatch');
    add(lod.materials===doc.materials.length,lod.model+': material count mismatch');
    add(lod.level===0||lod.triangles<built.lods[lod.level-1].triangles,lod.model+': LOD must reduce');
    lod.meshes=doc.meshes.length;lod.drawCalls=doc.meshes.reduce((n,m)=>n+m.primitives.length,0);
    for(const material of doc.materials){
      add(!!material.pbrMetallicRoughness?.baseColorTexture&&!!material.pbrMetallicRoughness?.metallicRoughnessTexture&&!!material.normalTexture&&!!material.occlusionTexture,lod.model+': incomplete PBR channels');
    }
    add(doc.images.every(image=>image.uri?.startsWith('../textures/cinderfen_architecture/')&&image.bufferView===undefined),lod.model+': image must use the shared texture set');
    add(JSON.stringify([...new Set(doc.images.map(image=>image.uri))].sort())===JSON.stringify(Object.keys(lod.external_textures??{}).sort()),lod.model+': unsigned or extra external texture URI');
    for(const [uri,digest] of Object.entries(lod.external_textures??{}))add(digest===await hashFile(path.resolve(path.dirname(file),uri)),lod.model+': stale shared texture');
    lod.externalTextures=Object.entries(lod.external_textures??{}).map(([uri,sha256])=>({uri,sha256}));
    add(lod.texture_packing?.output_glb_sha256===lod.sha256,lod.model+': missing texture packing provenance');
    add(lod.texture_packing?.tool_sha256===await hashFile(path.join(work,'tools/share_textures.py')),lod.model+': changed texture packing tool');
    for(const mesh of doc.meshes)for(const primitive of mesh.primitives){
      for(const semantic of ['POSITION','NORMAL','TEXCOORD_0','TANGENT'])add(primitive.attributes[semantic]!==undefined,lod.model+': missing '+semantic);
    }
    if(assetId.endsWith('gate_leaves')){
      for(const name of ['gate_open','gate_close']){
        const animation=doc.animations?.find(a=>a.name===name);
        add(animation?.channels.length===2,lod.model+': missing paired '+name+' animation');
        add(animation?.channels.every(channel=>channel.target.path==='rotation'),lod.model+': gate clips must rotate rigid leaves');
      }
      for(const [name,x] of [['gate_leaf_left',-3],['gate_leaf_right',3]]){
        const node=doc.nodes.find(node=>node.name===name);add(node?.translation?.[0]===x,lod.model+': incorrect '+name+' hinge');
      }
    }
    const checked=await validator.validateBytes(new Uint8Array(bytes),{uri:lod.model,maxIssues:1000,externalResourceFunction:uri=>fs.readFile(path.resolve(path.dirname(file),uri))});
    add(checked.issues.numErrors===0,lod.model+': '+checked.issues.numErrors+' Khronos errors');
    add(checked.issues.numWarnings===0,lod.model+': '+checked.issues.numWarnings+' Khronos warnings');
    await save(path.join(work,'review',lod.model+'.validation.json'),checked);
    if(!geometryOnly){
      const topology=geometryAudit.models.find(item=>item.model===lod.model);
      add(topology?.sha256===lod.sha256,lod.model+': missing or stale positional topology audit');
      add(topology?.audit_tool_sha256===await hashFile(path.join(work,'tools/audit_geometry.py')),lod.model+': changed topology audit tool');
      add(topology?.boundary_edges_after_positional_weld===0,lod.model+': exported construction shell has an open boundary');
      const joins=topology?.coincident_join_segments??[];
      add(joins.length===0,lod.model+': unexpected coincident multi-face topology');
      if(topology?.doorway)add(topology.doorway.blocked_rays.length===0,lod.model+': obstructed front opening');
      if(topology?.defense_crosswalk)add(topology.defense_crosswalk.blocked_rays.length===0,lod.model+': obstructed defense crosswalk');
      for(const surface of topology?.walkable_surfaces??[])add(surface.missing===0&&surface.max_error<=.025,lod.model+': support mismatch '+surface.surface);
      lod.topology=topology;
      const imported=await read(path.join(work,'review',lod.model.replace('.glb','_reimport.json')));
      add(imported.sha256===lod.sha256,lod.model+': stale GLB reimport');
      add(imported.preview_sha256===await hashFile(path.join(work,'review',imported.preview)),lod.model+': stale reimport image');
      lod.reviewImages={[imported.preview]:imported.preview_sha256};
      if(lod.level===0&&assetId.endsWith('gatehouse'))Object.assign(lod.reviewImages,keepAssembly.previews);
      add(!!imported.gameplay_preview&&[40,90,160][lod.level]===imported.gameplay_camera?.distance_m,lod.model+': missing measured gameplay-distance view');
      for(const prefix of ['front','open','gameplay','side','material','reed'])if(imported[prefix+'_preview']){
        const name=imported[prefix+'_preview'],digest=imported[prefix+'_preview_sha256'];
        add(digest===await hashFile(path.join(work,'review',name)),lod.model+': stale '+prefix+' review image');
        lod.reviewImages[name]=digest;
      }
      if(lod.level===0&&/workshop|gatehouse/.test(assetId))add(!!imported.material_preview,lod.model+': missing actual-export material close-up');
      if(lod.level===0&&assetId.endsWith('workshop'))add(!!imported.reed_preview,lod.model+': missing actual-export reed edge close-up');
      const currentReviewer=await hashFile(path.join(work,'tools/review_exports.py'));
      if(imported.reviewer_sha256!==currentReviewer){
        let archived;try{archived=await hashFile(path.join(work,'review/tool_sources','review_exports_'+imported.reviewer_sha256+'.py'));}catch{}
        add(archived===imported.reviewer_sha256,lod.model+': missing exact historical review source');
      }
      if(imported.passage)add(imported.passage.blocked_rays.length===0,lod.model+': obstructed six-metre passage');
      if(imported.opened_passage)add(imported.opened_passage.blocked_rays.length===0,lod.model+': opened leaves obstruct the six-metre passage');
      if(imported.clips){
        for(const name of ['gate_leaf_left','gate_leaf_right']){
          const matrix=imported.clips.gate_open.end[name].world_matrix;
          add(Math.abs(matrix[0][0])<1e-4&&Math.abs(Math.abs(matrix[1][0])-1)<1e-4,lod.model+': leaf did not open ninety degrees');
          add(Math.abs(imported.clips.gate_close.end[name].world_matrix[0][0]-1)<1e-4,lod.model+': leaf did not close');
        }
      }
      lod.preview=imported.preview;lod.preview_sha256=imported.preview_sha256;
    }
    validation.push({model:lod.model,sha256:lod.sha256,triangles,errors:checked.issues.numErrors,warnings:checked.issues.numWarnings});
  }
  report.push({...built,displayName:definition.name});
}
const reportPath=path.join(work,'build-report.json');
await save(reportPath,report);
await save(path.join(work,'validation.json'),{passed:issues.length===0,issues,models:validation,completeReimportReview:!geometryOnly});
console.log(JSON.stringify({models:validation.length,issues,completeReimportReview:!geometryOnly},null,2));
if(issues.length)throw Error('Architecture validation failed.');

const blueprintDir=path.join(root,'scripts/blender-character-pipeline/data/asset-blueprints');
const makeBlueprint=asset=>({
  assetId:'prop.frontier.'+asset.asset_id.replace('frontier_',''),displayName:asset.displayName,category:'prop',version:'1.0.0',sets:['cinderfen_authored_architecture'],
  runtime:{staticKey:asset.asset_id},output:{model:asset.lods[0].model,artifactDir:'authoring/blender/cinderfen-architecture/runtime'},
  generator:{kind:'copyExisting',copyFrom:'authoring/blender/cinderfen-architecture/runtime/'+asset.lods[0].model},
  geometry:{originRule:'root_grounded',upAxis:'+Y',forwardAxis:'+Z',lods:asset.lods.map(lod=>({name:'LOD'+lod.level,triTarget:lod.triangles,screenCoverageMin:[.2,.08,0][lod.level]}))},
  materials:{master:'MM_CinderfenArchitecture',textureSet:'cinderfen_authored_architecture',channels:['baseColor','roughness','metallic','normal','occlusion'],maxTextureResolution:1024},
  rigging:{skinned:false,requiredClips:asset.asset_id.endsWith('gate_leaves')?['gate_open','gate_close']:[]},
  collision:{policy:asset.asset_id.endsWith('gate_leaves')?'dynamic_gate_hinge':'authored_wall_segments',primitives:[]},
  compatibility:{occupiesSlots:['prop'],requires:[],conflictsWith:[]},
  provenance:{createdBy:'original_authored_mesh_control_cages',aiAssisted:true,aiStages:['art_direction','literal_control_cage_authoring','material_painting','blender_finishing','lod_authoring','technical_validation'],referencePackId:'original_cinderfen_architecture_v1',similarityReview:'not_required',author:'Codex architecture authoring',source:'authoring/blender/cinderfen-architecture/source/architecture.json',sourceSha256:sourceHash},
  qc:{allowNonManifold:false,allowUvOverlap:true,maxTris:asset.lods[0].triangles,maxFileSizeMb:Math.ceil(asset.lods[0].bytes/1048576)+1,maxDrawCalls:asset.lods[0].drawCalls,maxMeshObjects:asset.lods[0].meshes,requiresSkinnedMeshes:false,requiresPreview:true,expectedHeightM:asset.lods[0].bounds_z_up.maximum[2]-asset.lods[0].bounds_z_up.minimum[2],heightToleranceM:.03},
  lifecycle:{status:'review_pending',notes:'Original fitted construction cages remain editable in the Blender master. Closed construction pieces deliberately share metre-scaled tiled material UVs for reeds, basalt, alder and hardware; these are reusable material fields rather than a unique atlas. Positional audit welds glTF material/UV/normal seam splits at one micrometre and requires zero boundary and multi-face edges on every LOD. Coarse authored roof and deck courses preserve the curved envelope and support height while reducing distant seams. Exact bounds, raised floors, ramps, treads, colliders and keep passage contracts are retained in authoring/blender/cinderfen-architecture/build-report.json. Internal visual acceptance is required before package publication.'},
});
for(const asset of report){
  const file=path.join(blueprintDir,asset.asset_id+'.asset.json');
  let existing;try{existing=await read(file);}catch(error){if(error.code!=='ENOENT')throw error;}
  if(existing?.lifecycle?.status!=='approved'&&!publishing)await save(file,makeBlueprint(asset));
}

if(publishing){
  const reviewPath=path.join(work,'review/review.json'),review=await read(reviewPath);
  const previewPath=path.join(work,'review/all-exports.png');
  if(review.buildSha256!==await hashFile(reportPath)||review.previewSha256!==await hashFile(previewPath))throw Error('Visual acceptance does not match the exact final build and contact sheet.');
  if(!review.reviewedBy||!review.reviewedAt||review.approved!==true)throw Error('A named, dated internal visual acceptance is required.');
  for(const asset of report)for(const lod of asset.lods){
    for(const [name,digest] of Object.entries(lod.reviewImages))if(review.heroSha256?.[name]!==digest)throw Error('Visual acceptance must cover every actual reimport and mechanical review PNG: '+name);
  }
  const reviewHash=await hashFile(reviewPath),modelsDir=path.join(root,'public/assets/models');
  const approvedDir=path.join(root,'scripts/blender-character-pipeline/data/approved-assets');
  const previewDir=path.join(modelsDir,'previews');await fs.mkdir(previewDir,{recursive:true});
  const texturesDir=path.join(root,'public/assets/textures/cinderfen_architecture');await fs.mkdir(texturesDir,{recursive:true});
  const textureNames=new Set(report.flatMap(asset=>asset.lods.flatMap(lod=>Object.keys(lod.external_textures).map(uri=>path.basename(uri)))));
  for(const name of textureNames)await fs.copyFile(path.join(work,'textures/cinderfen_architecture',name),path.join(texturesDir,name));
  await fs.copyFile(previewPath,path.join(previewDir,'cinderfen_architecture.png'));
  for(const asset of report){
    const bp=makeBlueprint(asset);bp.lifecycle={...bp.lifecycle,status:'approved',reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,notes:bp.lifecycle.notes.replace('Internal visual acceptance is required before package publication.','Accepted internally against the exact build and all reimport previews; the approval record retains review hashes.')};
    const preview='public/assets/models/previews/'+asset.asset_id+'.png';
    await fs.copyFile(path.join(work,'review',asset.lods[0].preview),path.join(root,preview));
    for(const lod of asset.lods){
      await fs.copyFile(path.join(work,'runtime',lod.model),path.join(modelsDir,lod.model));
      await save(path.join(modelsDir,lod.model.replace('.glb','.qc.json')),{
        qcPassed:true,assetId:bp.assetId,modelSha256:lod.sha256,validationErrors:0,reviewHash,totalTris:lod.triangles,meshCount:lod.drawCalls,nonManifoldEdges:lod.topology.boundary_edges_after_positional_weld+lod.topology.multi_face_edges_after_positional_weld,missingRequiredClips:[],pbrChannels:bp.materials.channels,maxTextureResolution:1024,
        builtLods:asset.lods.map(l=>({name:'LOD'+l.level,level:l.level,model:l.model,triangles:l.triangles,sha256:l.sha256,externalTextures:l.externalTextures})),lods:asset.lods,externalTextures:lod.externalTextures,
        previewImages:[preview],heightM:lod.bounds_z_up.maximum[2]-lod.bounds_z_up.minimum[2],bounds:lod.bounds_z_up,placementContract:asset.contract,
        topologyPolicy:bp.lifecycle.notes,
      });
    }
    await save(path.join(blueprintDir,asset.asset_id+'.asset.json'),bp);
    const qc=asset.lods[0].model.replace('.glb','.qc.json');
    await save(path.join(approvedDir,asset.asset_id+'.approved.json'),{
      schemaVersion:1,assetId:bp.assetId,displayName:bp.displayName,category:'prop',model:asset.lods[0].model,qc,runtime:bp.runtime,
      compatibility:{bodyFamily:'static_architecture',bodyVariant:'neutral',skeletonId:'none',bindPoseId:'none'},
      hashes:{modelSha256:asset.lods[0].sha256,qcSha256:await hashFile(path.join(modelsDir,qc)),previews:{assembly:asset.lods[0].preview_sha256}},
      previews:{assembly:preview},review:{reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,reviewHash},provenance:bp.provenance,approvalState:'approved',
    });
  }
  console.log('Published '+report.length+' internally accepted architecture models; compile the global registry separately.');
}

{
  const navigation=report.map(asset=>({assetId:asset.asset_id,model:asset.lods[0].model,modelSha256:asset.lods[0].sha256,
    lods:asset.lods.map(lod=>({level:lod.level,model:lod.model,sha256:lod.sha256})),
    boundsYUp:{minimum:[asset.lods[0].bounds_z_up.minimum[0],asset.lods[0].bounds_z_up.minimum[2],-asset.lods[0].bounds_z_up.maximum[1]],maximum:[asset.lods[0].bounds_z_up.maximum[0],asset.lods[0].bounds_z_up.maximum[2],-asset.lods[0].bounds_z_up.minimum[1]]},
    ...asset.contract}));
  const meta={schemaVersion:1,units:'metres',upAxis:'+Y',frontAxis:'+Z',sourceSha256:sourceHash,buildSha256:await hashFile(reportPath),runtimeReady:publishing,completeReimportReview:!geometryOnly,assets:navigation};
  await save(path.join(work,'navigation-contract.json'),meta);
  await save(path.join(work,'builder-metadata.json'),{...meta,assets:Object.fromEntries(navigation.map(asset=>[asset.assetId,{
    assetId:asset.assetId,label:source.assets[asset.assetId].name,group:'Cinderfen Buildings',model:asset.model,modelSha256:asset.modelSha256,runtimeReady:publishing,defaultScale:{x:1,y:1,z:1},rotY:0,colliderSpace:'model',
    kind:asset.assetId.endsWith('gate_leaves')?'keep_gate':'structure',
    footprint:{width:/curtain_walk|gatehouse|gate_leaves/.test(asset.assetId)?asset.footprint[0]:asset.boundsYUp.maximum[0]-asset.boundsYUp.minimum[0],depth:asset.boundsYUp.maximum[2]-asset.boundsYUp.minimum[2],chainAxis:/curtain_walk|gatehouse|gate_leaves/.test(asset.assetId)?'x':'z'},
    placementDatum:'Ground datum at localY0; footings and ramp stringers extend below ground intentionally.',
    boundsYUp:asset.boundsYUp,colliders:asset.assetId.endsWith('gate_leaves')?[{...asset.closed_collision_runtime,blocksWhen:'closed'}]:asset.colliders??[],walkableSurfaces:asset.walkableSurfaces??[],cameraSolid:true,
    sockets:Object.fromEntries(Object.entries(asset).filter(([key])=>key.endsWith('_runtime'))),
    ...(asset.assetId.endsWith('gate_leaves')?{interaction:{type:'gate',label:'Cinderfen gate',maxDistance:5,openClip:'gate_open',closeClip:'gate_close',startsOpen:false},defaultAnimation:'gate_close',gateDefaults:{initialState:'closed',closedCollider:asset.closed_collision_runtime,openColliders:[],closedClip:'gate_close',openClip:'gate_open',leftNode:'gate_leaf_left',rightNode:'gate_leaf_right',hinges:[[-3,0,0],[3,0,0]],swingDegrees:90,interactionPolicy:'Campaign authority controls ownership, damage and state; the builder supplies geometry and clips only.'}}:{}),
  }]))});
}
