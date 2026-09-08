/** Apply strict repository manifest rules to this package's measured exports. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateBlueprintRecord} from '../../../../scripts/blender-character-pipeline/tools/pipeline-lib.mjs';
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),repo=path.resolve(work,'../../..');
const assets=JSON.parse(await fs.readFile(path.join(work,'build-report.json'),'utf8'));
for(const asset of assets){
  const file=path.join(repo,'scripts/blender-character-pipeline/data/asset-blueprints',asset.asset_id+'.asset.json'),bp=JSON.parse(await fs.readFile(file,'utf8'));
  assert.deepEqual(validateBlueprintRecord(file,bp,{strict:true}).errors,[],asset.asset_id);
  assert.ok(bp.qc.maxFileSizeMb*1048576>=asset.lods[0].bytes,asset.asset_id+' size budget');
  assert.deepEqual(bp.geometry.lods.map(l=>l.triTarget),asset.lods.map(l=>l.triangles));
}
console.log('Four ecology blueprints pass strict repository validation and measured budgets.');
