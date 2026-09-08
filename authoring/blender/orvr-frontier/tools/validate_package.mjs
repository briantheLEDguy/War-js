/** Hash-bound binary inventory; visual approval is an independent decision. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
import { readGlb } from './inspect_mechanical_glb.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const source=JSON.parse(await fs.readFile(path.join(root,'source/frontier_collection.json'),'utf8'));
const keys=[...Object.keys(source.assets),'frontier_draft_horse','frontier_caravan_reins','frontier_supply_officer_kit'];
const records=[];const issues=[];
for(const key of [...keys,'frontier_teamster_animations']){
 const report=JSON.parse(await fs.readFile(path.join(root,`review/${key}_build.json`),'utf8'));
 const lods=report.lods??[{...report,level:null}];
 for(const lod of lods){
  const file=lod.path.replaceAll('\\','/'),bytes=await fs.readFile(path.join(root,file));
  if(hash(bytes)!==lod.sha256)issues.push(`${file}: build hash mismatch`);
  const result=await validator.validateBytes(new Uint8Array(bytes),{uri:path.basename(file)});
  if(result.issues.numErrors)issues.push(`${file}: ${result.issues.numErrors} glTF errors`);
  const {document}=readGlb(bytes);
  const triangles=(document.meshes??[]).reduce((sum,mesh)=>sum+mesh.primitives.reduce((count,primitive)=>count+document.accessors[primitive.indices].count/3,0),0);
  // Shared wheel meshes are counted once by glTF; build reports count instances.
  const instanceTriangles=(document.nodes??[]).reduce((sum,node)=>sum+(node.mesh===undefined?0:document.meshes[node.mesh].primitives.reduce((n,p)=>n+document.accessors[p.indices].count/3,0)),0);
  if(lod.triangles!==undefined && lod.triangles!==instanceTriangles)issues.push(`${file}: measured instance triangles differ`);
  for(const material of document.materials??[]){
   if(!material.pbrMetallicRoughness?.baseColorTexture||!material.normalTexture||!material.pbrMetallicRoughness.metallicRoughnessTexture)issues.push(`${file}: missing PBR channel`);
  }
  const record={assetId:key,level:lod.level,path:file,sha256:hash(bytes),bytes:bytes.length,triangles:instanceTriangles,uniqueMeshTriangles:triangles,
   materials:document.materials?.length??0,clips:document.animations?.map(clip=>clip.name)??[],errors:result.issues.numErrors,warnings:result.issues.numWarnings,
   warningCodes:[...new Set(result.issues.messages.filter(message=>message.severity===1).map(message=>message.code))]};
  records.push(record);
  await fs.writeFile(path.join(root,'review',path.basename(file).replace('.glb','.validation.json')),JSON.stringify(result,null,2)+'\n');
 }
}
const inventory={passed:issues.length===0,visualApproval:false,status:'review_pending',issues,records};
await fs.writeFile(path.join(root,'review/package_validation.json'),JSON.stringify(inventory,null,2)+'\n');
console.log(JSON.stringify({files:records.length,passed:inventory.passed,errors:records.reduce((sum,row)=>sum+row.errors,0),warnings:records.reduce((sum,row)=>sum+row.warnings,0),issues}));
if(issues.length)process.exitCode=1;
