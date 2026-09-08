/** Publish the independent corner's reviewed builder defaults into the scanned package. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const root=path.resolve(work,'../../..');
const read=async name=>JSON.parse(await fs.readFile(name,'utf8'));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const main=await read(path.join(work,'builder-metadata.json'));
const corner=await read(path.join(work,'junction/builder-metadata.json'));
if(!main.runtimeReady||!corner.runtimeReady)throw Error('Both independent packages require visual acceptance and publication first.');
for(const [key,entry] of Object.entries(corner.assets)){
  const approved=await read(path.join(root,'scripts/blender-character-pipeline/data/approved-assets',key+'.approved.json'));
  const bytes=await fs.readFile(path.join(root,'public/assets/models',entry.model));
  if(!entry.runtimeReady||approved.approvalState!=='approved'||approved.hashes.modelSha256!==entry.modelSha256||sha(bytes)!==entry.modelSha256)throw Error('Corner builder metadata does not match its approved actual model.');
  main.assets[key]=entry;
}
main.companionPackages=[{path:'junction/builder-metadata.json',sha256:sha(await fs.readFile(path.join(work,'junction/builder-metadata.json')))}];
await fs.writeFile(path.join(work,'builder-metadata.json'),JSON.stringify(main,null,2)+'\n');
console.log('All eight accepted Cinderfen entries now expose their measured GM builder defaults.');
