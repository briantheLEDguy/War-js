import {readFile,writeFile,copyFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
const {default:validator}=await import('gltf-validator').catch(()=>import('../../aegis-city/.deps/node_modules/gltf-validator/index.js'));
const work=fileURLToPath(new URL('../',import.meta.url)),root=path.resolve(work,'../../..');
const read=async p=>JSON.parse(await readFile(p,'utf8')),hash=b=>createHash('sha256').update(b).digest('hex');
const write=(p,v)=>writeFile(p,JSON.stringify(v,null,2)+'\n');
const results=[];
for(const kind of ['chaos','dark_elf','greenskin']) {
  const asset=await read(path.join(work,`population_${kind}-report.json`)),textures=new Set();
  for(const lod of asset.lods) {
    const bytes=await readFile(path.join(work,'runtime',lod.model));assert.equal(hash(bytes),lod.sha256);
    const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
    assert(doc.skins?.length);assert(doc.animations?.some(a=>a.name==='idle'));assert(lod.triangles<=30000);
    for(const image of doc.images??[]) {
      assert(/^\.\.\/textures\/riftspire_city\/[a-f0-9]+\.png$/.test(image.uri));textures.add(image.uri);
      const png=await readFile(path.resolve(work,'runtime',image.uri));assert.equal(png.readUInt32BE(16),2048);assert.equal(png.readUInt32BE(20),2048);
      assert.equal(hash(png).slice(0,20),path.basename(image.uri,'.png'),'Texture content hash mismatch');
    }
    const result=await validator.validateBytes(new Uint8Array(bytes),{uri:lod.model,externalResourceFunction:async uri=>new Uint8Array(await readFile(path.resolve(work,'runtime',uri)))});
    results.push({model:lod.model,triangles:lod.triangles,errors:result.issues.messages.filter(m=>m.severity===0),warnings:result.issues.numWarnings});
  }
  if(!process.argv.includes('--publish'))continue;
  assert(results.every(r=>r.errors.length===0),JSON.stringify(results));
  const reviewPath=path.join(work,'review',`population_${kind}-review.json`),review=await read(reviewPath);
  assert.deepEqual(review.modelSha256s,asset.lods.map(l=>l.sha256));
  for(const [file,sha] of Object.entries(review.previewSha256s))assert.equal(hash(await readFile(path.join(work,'review',file))),sha);
  const reviewHash=hash(await readFile(reviewPath));
  await mkdir(path.join(root,'public/assets/textures/riftspire_city'),{recursive:true});
  for(const uri of textures)await copyFile(path.resolve(work,'runtime',uri),path.resolve(root,'public/assets/models',uri));
  for(const lod of asset.lods) {
    await copyFile(path.join(work,'runtime',lod.model),path.join(root,'public/assets/models',lod.model));
    await write(path.join(root,'public/assets/models',lod.model.replace('.glb','.qc.json')),{qcPassed:true,modelSha256:lod.sha256,lods:asset.lods,validationErrors:0,textureMaxDimension:2048,reviewHash});
  }
  const chosen=asset.lods[1],qc=chosen.model.replace('.glb','.qc.json'),preview=`population_${kind}-lod0.png`;
  const compatibility=kind==='dark_elf'?{bodyFamily:'aegis_people',bodyVariant:'m',skeletonId:'aegis_people_v1',bindPoseId:'civic_relaxed_v1'}
    :{bodyFamily:kind==='chaos'?'aegis_city_guard':'mire_brutish_v1',bodyVariant:'m',skeletonId:'humanoid_game_v2',bindPoseId:'a_pose_v2'};
  await write(path.join(root,'scripts/blender-character-pipeline/data/approved-assets',`chr_riftspire_${kind}.approved.json`),{
    schemaVersion:1,assetId:`chr.riftspire.${kind}`,displayName:`Riftspire ${kind.replaceAll('_',' ')} inhabitant`,category:'character',model:chosen.model,qc,
    runtime:{profileKey:`npc_riftspire_${kind}`},compatibility,approvalState:'approved',
    hashes:{modelSha256:chosen.sha256,qcSha256:hash(await readFile(path.join(root,'public/assets/models',qc))),previews:{front:review.previewSha256s[preview]}},
    previews:{front:`authoring/blender/riftspire-city/review/${preview}`},review:{reviewedBy:review.reviewedBy,reviewedAt:review.reviewedAt,reviewHash},
    provenance:{sourcePackage:'authoring/blender/riftspire-city',sourceModel:asset.source,sourceSha256:hash(await readFile(path.join(root,'public/assets/models',asset.source))),
      geometry:'Adapted reviewed anatomy and rig with fitted Riftbound apparel, headgear and faction features. Original upstream anatomy licenses and provenance remain applicable.',
      limitations:'Middle LOD used for residents. Dark Elf uses the existing civic idle and generated walking cycle.'}
  });
}
await write(path.join(work,'population-validation.json'),results);
assert(results.every(r=>r.errors.length===0),JSON.stringify(results.filter(r=>r.errors.length)));
console.log(`${results.length} population GLBs checked; no validation errors.`);
