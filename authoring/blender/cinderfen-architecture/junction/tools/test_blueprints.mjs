/** Exercise the repository's strict manifest checks for this package only. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateBlueprintRecord } from '../../../../../scripts/blender-character-pipeline/tools/pipeline-lib.mjs';
const work=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const root=path.resolve(work,'../../../..');
const report=JSON.parse(await fs.readFile(path.join(work,'build-report.json'),'utf8'));
for(const asset of report){
  const file=path.join(root,'scripts/blender-character-pipeline/data/asset-blueprints',asset.asset_id+'.asset.json');
  const blueprint=JSON.parse(await fs.readFile(file,'utf8'));
  const result=validateBlueprintRecord(file,blueprint,{strict:true});
  assert.deepEqual(result.errors,[],asset.asset_id);
  assert.ok(blueprint.qc.maxFileSizeMb*1048576>=asset.lods[0].bytes,asset.asset_id+' file-size budget');
  assert.deepEqual(blueprint.geometry.lods.map(lod=>lod.triTarget),asset.lods.map(lod=>lod.triangles),asset.asset_id+' LOD measurements');
}
console.log(`${report.length} architecture blueprints passed strict repository validation and measured-budget checks.`);
