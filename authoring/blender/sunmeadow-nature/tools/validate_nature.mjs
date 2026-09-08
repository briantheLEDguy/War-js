import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import validator from 'gltf-validator';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const design=JSON.parse(await fs.readFile(path.join(root,'source/design.json'),'utf8'));
const issues=[];const assets=[];
const paintBytes=await fs.readFile(path.join(root,'textures/paint_record.json'));
const paint=JSON.parse(paintBytes);
for(const [filename,hash] of Object.entries(paint.images)){
  if(sha(await fs.readFile(path.join(root,filename)))!==hash)issues.push(`Source surface changed: ${filename}`);
}
for(const kind of Object.keys(design.assets)){
  const key=`frontier_sunmeadow_${kind}`;
  const build=JSON.parse(await fs.readFile(path.join(root,'review',`${key}_build.json`),'utf8'));
  const master=await fs.readFile(path.join(root,build.master));
  if(sha(master)!==build.master_sha256)issues.push(`${key}: master hash changed`);
  if(sha(await fs.readFile(path.join(root,'source/design.json')))!==build.source_sha256)issues.push(`${key}: design changed`);
  if(sha(await fs.readFile(path.join(root,'tools/build_nature.py')))!==build.builder_sha256)issues.push(`${key}: builder changed`);
  if(sha(paintBytes)!==build.paint_record_sha256)issues.push(`${key}: paint provenance changed`);
  const lods=[];
  for(const lod of build.lods){
    const bytes=await fs.readFile(path.join(root,'runtime',lod.model));
    if(sha(bytes)!==lod.sha256)issues.push(`${lod.model}: binary hash changed`);
    const length=bytes.readUInt32LE(12);const doc=JSON.parse(bytes.subarray(20,20+length).toString());
    const primitives=doc.meshes.flatMap(mesh=>mesh.primitives);
    const triangles=primitives.reduce((sum,p)=>sum+doc.accessors[p.indices].count/3,0);
    if(triangles!==lod.triangles)issues.push(`${lod.model}: triangle record differs`);
    for(const primitive of primitives){
      for(const attribute of ['POSITION','NORMAL','TANGENT','TEXCOORD_0'])if(primitive.attributes[attribute]===undefined)issues.push(`${lod.model}: missing ${attribute}`);
    }
    for(const material of doc.materials){
      const pbr=material.pbrMetallicRoughness;
      if(!pbr?.baseColorTexture||!pbr.metallicRoughnessTexture||!material.normalTexture||!material.occlusionTexture)issues.push(`${lod.model}: incomplete PBR material ${material.name}`);
      if(material.alphaMode&&material.alphaMode!=='OPAQUE')issues.push(`${lod.model}: unexpected transparent foliage`);
    }
    if(doc.images.some(image=>image.uri))issues.push(`${lod.model}: external texture dependency`);
    if(doc.materials.length>2||primitives.length>2)issues.push(`${lod.model}: exceeded two material/draw budget`);
    if(bytes.length>10*1024*1024)issues.push(`${lod.model}: exceeded 10 MiB package budget`);
    if(triangles>90000)issues.push(`${lod.model}: exceeded 90k nearest tree budget`);
    const result=await validator.validateBytes(new Uint8Array(bytes),{uri:lod.model,maxIssues:1000});
    await fs.writeFile(path.join(root,'review',`${lod.model}.validation.json`),JSON.stringify(result,null,2)+'\n');
    if(result.issues.numErrors)issues.push(`${lod.model}: ${result.issues.numErrors} Khronos errors`);
    lods.push({...lod,validationErrors:result.issues.numErrors,validationWarnings:result.issues.numWarnings});
  }
  if(lods.length!==3||!(lods[0].triangles>lods[1].triangles&&lods[1].triangles>lods[2].triangles))issues.push(`${key}: all three decreasing LODs required`);
  for(const lod of lods.slice(1))for(const axis of [0,1,2]){
    const baseline=lods[0].bounds_runtime.max[axis]-lods[0].bounds_runtime.min[axis];
    const span=lod.bounds_runtime.max[axis]-lod.bounds_runtime.min[axis];
    if(span<baseline*.84||span>baseline*1.20)issues.push(`${key} LOD${lod.level}: silhouette envelope changed excessively on axis ${axis}`);
  }
  assets.push({asset:key,lods,limitations:build.limitations});
}
const report={passed:issues.length===0,issues,assets,visualApproval:false,note:'Technical validation alone does not approve model quality or publish runtime assets.'};
await fs.writeFile(path.join(root,'review/validation.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({passed:report.passed,issues,assets:assets.map(a=>({asset:a.asset,triangles:a.lods.map(l=>l.triangles),warnings:a.lods.map(l=>l.validationWarnings)}))},null,2));
if(issues.length)process.exitCode=1;
