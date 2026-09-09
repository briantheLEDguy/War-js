/** Verify the exact public binaries, signed texture bytes and usable GM defaults. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {publicationSelection} from './publication_selection.mjs';
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),repo=path.resolve(work,'../../..');
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const read=async p=>JSON.parse(await fs.readFile(p,'utf8'));
const source=await read(path.join(work,'source/nature.json'));
const selection=publicationSelection(Object.keys(source.assets),process.argv.find(arg=>arg.startsWith('--assets='))?.slice('--assets='.length));
const built=await read(path.join(work,selection.build)),meta=await read(path.join(work,'builder-metadata.json'));
assert.deepEqual(built.map(asset=>asset.asset_id).sort(),selection.ids);
assert.equal(Object.keys(meta.assets).length,Object.keys(source.assets).length);
assert.equal(meta.runtimeReady,Object.values(meta.assets).every(asset=>asset.runtimeReady));
for(const asset of built){
  const published=await read(path.join(repo,'scripts/blender-character-pipeline/data/approved-assets',asset.asset_id+'.approved.json'));
  assert.equal(published.approvalState,'approved');assert.equal(published.hashes.modelSha256,asset.lods[0].sha256);
  assert.equal(published.hashes.qcSha256,hash(await fs.readFile(path.join(repo,'public/assets/models',published.qc))));
  const metadata=meta.assets[asset.asset_id];assert.equal(metadata.runtimeReady,true);assert.equal(metadata.modelSha256,asset.lods[0].sha256);assert.equal(metadata.colliderSpace,'model');assert.deepEqual(metadata.defaultScale,{x:1,y:1,z:1});assert.deepEqual(metadata.colliders,asset.contract.colliders);assert.deepEqual(metadata.walkableSurfaces,[]);
  for(const lod of asset.lods){
    const filename=path.join(repo,'public/assets/models',lod.model);const bytes=await fs.readFile(filename);
    assert.equal(hash(bytes),lod.sha256);const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
    const qc=await read(filename.replace('.glb','.qc.json'));assert.equal(qc.qcPassed,true);assert.equal(qc.validationErrors,0);assert.equal(qc.modelSha256,lod.sha256);
    assert.deepEqual(qc.lods.map(l=>l.sha256),asset.lods.map(l=>l.sha256));
    assert.deepEqual([...new Set(doc.images.map(i=>i.uri))].sort(),qc.externalTextures.map(t=>t.uri).sort());
    for(const texture of qc.externalTextures)assert.equal(hash(await fs.readFile(path.resolve(path.dirname(filename),texture.uri))),texture.sha256);
  }
}
console.log(`${built.length} published ecology assets / ${built.flatMap(asset=>asset.lods).length} GLBs: model, QC, texture and GM metadata hashes pass.`);
