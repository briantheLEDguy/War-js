/** Check the published bytes and signed texture lists without compiling the global registry. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { validateQcForBlueprint } from '../../../../scripts/blender-character-pipeline/tools/pipeline-lib.mjs';
import { validateApprovedManifest } from '../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),root=path.resolve(work,'../../..');
const read=async p=>JSON.parse(await fs.readFile(p,'utf8'));
const hash=async p=>crypto.createHash('sha256').update(await fs.readFile(p)).digest('hex');
const report=await read(path.join(work,'build-report.json')),models=path.join(root,'public/assets/models');
let lodCount=0;const textures=new Set();
for(const asset of report){
  const stem=asset.asset_id;
  const blueprint=await read(path.join(root,'scripts/blender-character-pipeline/data/asset-blueprints',stem+'.asset.json'));
  const approved=validateApprovedManifest(await read(path.join(root,'scripts/blender-character-pipeline/data/approved-assets',stem+'.approved.json')));
  assert.equal(blueprint.lifecycle.status,'approved',stem);
  const qcPath=path.join(models,approved.qc),qc=await read(qcPath);
  assert.deepEqual(validateQcForBlueprint(blueprint,path.join(models,approved.model),qcPath,true),[],stem);
  assert.equal(await hash(qcPath),approved.hashes.qcSha256,stem+' signed QC');
  assert.equal(await hash(path.join(models,approved.model)),approved.hashes.modelSha256,stem+' signed GLB');
  for(const lod of qc.builtLods){
    const modelPath=path.join(models,lod.model),bytes=await fs.readFile(modelPath);
    assert.equal(await hash(modelPath),lod.sha256,lod.model);
    const gltf=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
    assert.ok((gltf.buffers??[]).every(buffer=>!buffer.uri),lod.model+' no external geometry buffers');
    const uris=[...new Set((gltf.images??[]).map(image=>image.uri))].sort();
    const refs=lod.externalTextures;
    assert.equal(refs.length,new Set(refs.map(ref=>ref.uri)).size,lod.model+' unique texture signatures');
    assert.deepEqual(refs.map(ref=>ref.uri).sort(),uris,lod.model+' every image URI signed');
    assert.deepEqual(qc.lods.find(entry=>entry.model===lod.model).externalTextures,refs,lod.model+' both LOD schemas');
    const ownQc=await read(modelPath.replace(/\.glb$/,'.qc.json'));
    assert.deepEqual(ownQc.externalTextures,refs,lod.model+' per-model signatures');
    assert.equal(ownQc.modelSha256,lod.sha256,lod.model+' per-model QC hash');
    for(const ref of refs){
      assert.match(ref.uri,/^\.\.\/textures\/sunmeadow_architecture\/[a-f0-9]{64}\.png$/);
      assert.equal(await hash(path.resolve(models,ref.uri)),ref.sha256,ref.uri);
      textures.add(ref.uri);
    }
    lodCount++;
  }
}
console.log(`Published package verified: ${report.length} approved records, ${lodCount} GLBs, ${textures.size} distinct signed texture resources. Registry unchanged.`);
