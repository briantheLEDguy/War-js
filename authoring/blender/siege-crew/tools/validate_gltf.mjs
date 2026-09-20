import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(import.meta.url);
let validator;
try { validator=require('gltf-validator'); }
catch(error) {
  if(error.code!=='MODULE_NOT_FOUND') throw error;
  validator=require(path.join(root,'../battle-prelate-novitiate-set/tmp/gltf-validation/node_modules/gltf-validator'));
}
const contract=JSON.parse(await readFile(path.join(root,'review/crew_contract.json'),'utf8'));
const reports=[];
for(const record of contract.outputs) {
  const bytes=await readFile(path.join(root,record.path));
  const sha256=createHash('sha256').update(bytes).digest('hex');
  if(sha256!==record.sha256) throw Error('Candidate changed');
  const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  if(gltf.meshes?.length) throw Error('Animation-only candidate contains meshes');
  const result=await validator.validateBytes(new Uint8Array(bytes),{uri:record.path,maxIssues:100});
  reports.push({path:record.path,sha256,bytes:bytes.length,animations:gltf.animations.map(a=>a.name),
    nodes:gltf.nodes.length,issues:result.issues});
}
const report={validator:validator.version(),errors:reports.reduce((n,r)=>n+r.issues.numErrors,0),
  warnings:reports.reduce((n,r)=>n+r.issues.numWarnings,0),assets:reports};
report.status=report.errors===0&&report.warnings===0?'passed':'failed';
await writeFile(path.join(root,'review/gltf_validation.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
process.exitCode=report.status==='passed'?0:1;
