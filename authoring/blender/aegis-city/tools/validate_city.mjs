import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const { default: validator } = await import('gltf-validator').catch(() => import('../.deps/node_modules/gltf-validator/index.js'));

const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const report=JSON.parse(await readFile(path.join(work,'build-report.json'),'utf8'));
const results=[];
for(const asset of report) for(const lod of asset.lods) {
  const filename=path.join(work,'runtime',lod.model);
  const bytes=await readFile(filename);
  const result=await validator.validateBytes(new Uint8Array(bytes),{
    uri:lod.model,
    externalResourceFunction:async uri=>new Uint8Array(await readFile(path.resolve(path.dirname(filename),uri))),
  });
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  const errors=[];
  if(createHash('sha256').update(bytes).digest('hex')!==lod.sha256) errors.push('Build hash mismatch');
  if(lod.triangles>30000) errors.push('Architecture triangle budget exceeded');
  if(lod.level && lod.triangles>asset.lods[lod.level-1].triangles) errors.push('LOD complexity increased');
  for(const mesh of doc.meshes??[]) for(const p of mesh.primitives) {
    if(p.attributes.TEXCOORD_0===undefined) errors.push('Missing UVs');
    if(p.attributes.NORMAL===undefined) errors.push('Missing normals');
  }
  results.push({model:lod.model,errors:[...errors,...result.issues.messages.filter(m=>m.severity===0).map(m=>m.message)],warnings:result.issues.numWarnings});
}
await writeFile(path.join(work,'validation.json'),JSON.stringify(results,null,2)+'\n');
console.log(`${results.length} GLBs; ${results.reduce((n,r)=>n+r.errors.length,0)} errors`);
if(results.some(r=>r.errors.length)) process.exitCode=1;
