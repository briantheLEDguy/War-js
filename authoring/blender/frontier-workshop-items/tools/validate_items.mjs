/** Local technical readiness only; root owns publication and registry writes. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import validator from 'gltf-validator';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const hashFile=async file=>hash(await fs.readFile(file));
const read=async file=>JSON.parse(await fs.readFile(file,'utf8'));
const save=async(file,value)=>{const temporary=file+'.tmp';await fs.writeFile(temporary,JSON.stringify(value,null,2)+'\n');await fs.rename(temporary,file);};
const geometryOnly=process.argv.includes('--geometry-only');
const issues=[],assets=[];const check=(condition,message)=>{if(!condition)issues.push(message);};
const source=await read(path.join(root,'source/items.json'));const sourceHash=await hashFile(path.join(root,'source/items.json'));
for(const [key,definition] of Object.entries(source.assets)){
  const record=await read(path.join(root,'review',key+'_build.json'));
  check(record.source_sha256===sourceHash,key+': changed source');
  // An exporter fix for another LOD must not invalidate untouched approved geometry.
  // Require the exact retained generating tool, separately from this current checker.
  check(record.builder_sha256===await hashFile(path.join(root,'review/tool_sources',`export_items_${record.builder_sha256}.py`)),key+': missing exact recorded exporter');
  check(record.material_tool_sha256===await hashFile(path.join(root,'tools/materials_items.py')),key+': changed material fields');
  check(JSON.stringify(record.contract)===JSON.stringify(definition.contract),key+': changed placement contract');
  check(JSON.stringify(record.lods.map(l=>l.level))==='[0,1,2]',key+': three ordered LODs required');
  for(const lod of record.lods){
    check(lod.exporter_sha256===await hashFile(path.join(root,'review/tool_sources',`export_items_${lod.exporter_sha256}.py`)),key+': missing exact retained exporter');
    const file=path.join(root,'runtime',lod.model),bytes=await fs.readFile(file);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
    check(hash(bytes)===lod.sha256&&bytes.length===lod.bytes,lod.model+': changed GLB');
    check(lod.master_sha256===await hashFile(path.join(root,lod.master)),lod.model+': changed master');
    check(lod.source_receipt_sha256===await hashFile(path.join(root,'review',`${key}_lod${lod.level}_source.json`)),lod.model+': changed source proof');
    const counts=doc.meshes.map(m=>m.primitives.reduce((sum,p)=>sum+doc.accessors[p.indices].count/3,0));const triangles=doc.nodes.reduce((sum,n)=>sum+(n.mesh===undefined?0:counts[n.mesh]),0);
    check(triangles===lod.triangles&&triangles<=[35000,15000,4000][lod.level],lod.model+': triangle count/budget');
    check(!lod.level||triangles<record.lods[lod.level-1].triangles,lod.model+': LOD does not reduce');
    const drawCalls=doc.meshes.reduce((sum,m)=>sum+m.primitives.length,0);check(drawCalls<=3,lod.model+': draw budget');
    for(const material of doc.materials)check(material.pbrMetallicRoughness?.baseColorTexture&&material.pbrMetallicRoughness?.metallicRoughnessTexture&&material.normalTexture&&material.occlusionTexture,lod.model+': incomplete PBR');
    for(const mesh of doc.meshes)for(const primitive of mesh.primitives)for(const semantic of ['POSITION','NORMAL','TANGENT','TEXCOORD_0'])check(primitive.attributes[semantic]!==undefined,lod.model+': missing '+semantic);
    check(!doc.animations?.length,lod.model+': unexpected animation');
    for(const projection of lod.material_projections){
      check(projection.geometrySha256Before===projection.geometrySha256After&&!!projection.geometrySha256Before,lod.model+': bake changed geometry');
      for(const repair of projection.atlas.cornerNormalRepairs??[])check(repair.changeDegrees>0&&repair.changeDegrees<1
        &&repair.faceAlignmentBefore>0&&repair.faceAlignmentBefore<.01&&repair.faceAlignmentAfter>repair.faceAlignmentBefore,
        lod.model+': grazing-normal repair exceeded its narrow shading tolerance');
      for(const channel of ['baseColor','normal','orm']){
        const map=projection.channels[channel],png=await fs.readFile(path.join(root,map.file));const resolution=[2048,1024,512][lod.level];check(hash(png)===map.sha256&&map.resolution===resolution&&png.readUInt32BE(16)===resolution&&png.readUInt32BE(20)===resolution,lod.model+': changed/wrong '+channel);
      }
    }
    check(lod.texture_packing?.output_glb_sha256===lod.sha256,lod.model+': missing texture packing receipt');
    check(lod.texture_packing?.tool_sha256===await hashFile(path.join(root,'tools/share_textures.py')),lod.model+': changed texture packing tool');
    const uris=[...new Set(doc.images.map(i=>i.uri))].sort();check(JSON.stringify(uris)===JSON.stringify(Object.keys(lod.external_textures??{}).sort()),lod.model+': changed texture inventory');
    for(const [uri,digest] of Object.entries(lod.external_textures??{})){
      check(/^\.\.\/textures\/frontier_workshop_items\/[a-f0-9]{64}\.png$/.test(uri),lod.model+': unsafe texture URI');check(digest===await hashFile(path.resolve(path.dirname(file),uri)),lod.model+': changed exported texture');
    }
    const validation=await validator.validateBytes(new Uint8Array(bytes),{uri:lod.model,externalResourceFunction:async uri=>new Uint8Array(await fs.readFile(path.resolve(path.dirname(file),uri)))});
    await save(path.join(root,'review',lod.model+'.validation.json'),validation);check(validation.issues.numErrors===0&&validation.issues.numWarnings===0,lod.model+': Khronos errors/warnings');
    if(!geometryOnly){
      const review=await read(path.join(root,'review',lod.model.replace('.glb','_reimport.json')));check(review.sha256===lod.sha256,lod.model+': stale actual reimport');
      check(review.reviewerSha256===await hashFile(path.join(root,'tools/review_exports.py'))&&review.cameraToolSha256===await hashFile(path.join(root,'tools/review_items.py')),lod.model+': changed reviewer');
      for(const counter of ['totalBoundaryEdges','totalMultiFaceEdges','totalLooseEdges'])check(review.audit[counter]===0,lod.model+': actual topology '+counter);
      for(const mode of ['neutral','gameplay',...(lod.level===0?['detail']:[])]){const view=review.views[mode];check(view&&view.sha256===await hashFile(path.join(root,'review',view.image)),lod.model+': changed/missing '+mode);}
    }
    console.log('WORKSHOP_VALIDATED',lod.model,triangles,drawCalls,validation.issues.numErrors,validation.issues.numWarnings);
  }
  assets.push({asset:key,buildSha256:await hashFile(path.join(root,'review',key+'_build.json')),lods:record.lods.map(l=>({model:l.model,sha256:l.sha256,triangles:l.triangles}))});
}
await save(path.join(root,'validation.json'),{schemaVersion:1,sourceSha256:sourceHash,
  validatorSha256:await hashFile(fileURLToPath(import.meta.url)),technicalReady:issues.length===0&&!geometryOnly,geometryOnly,issues,assets});
if(issues.length){console.error(issues.join('\n'));process.exitCode=1;}
