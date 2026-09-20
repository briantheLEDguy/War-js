/** Publish the literal approved motion dependencies without replacing the engine mesh. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {validateApprovedManifest} from '../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),project=path.resolve(root,'../../..');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=async file=>JSON.parse(await fs.readFile(path.join(root,file),'utf8'));
const save=async(file,value)=>fs.writeFile(file,JSON.stringify(value,null,2)+'\n');
const contract=await read('review/crew_contract.json'),contact=await read('review/actual_contact.json'),validation=await read('review/gltf_validation.json');
assert.equal(contact.status,'passed');assert.equal(validation.status,'passed');
const ramFile=path.join(project,'public/assets/models/frontier_battering_ram_lod0.glb');
assert.equal(hash(await fs.readFile(ramFile)),'b5e79265f4cd65759c6c1c0f60c10f21f11ffe095d4d5e5124ffc742ecb905ef');
const packs={};
for(const output of contract.outputs){
  const bytes=await fs.readFile(path.join(root,output.path));
  assert.equal(hash(bytes),output.sha256);
  assert(validation.assets.some(asset=>asset.sha256===output.sha256&&asset.issues.numErrors===0&&asset.issues.numWarnings===0));
  assert(contact.inputs.some(input=>input.sha256===output.sha256));
  const model=path.basename(output.path.replaceAll('\\','/'));
  packs[output.seat]={model,sha256:output.sha256,skeletonId:'humanoid_game_v2',bindPoseId:'a_pose_v2'};
  await fs.writeFile(path.join(project,'public/assets/models',model),bytes);
}
const approval={status:'approved',reviewedBy:'user standing approval, implemented by Codex',reviewedAt:new Date().toISOString(),
  scope:'Both exact crew animation packs approved for integration; existing canonical avatar/equipment geometry remains unchanged.',
  contractSha256:hash(await fs.readFile(path.join(root,'review/crew_contract.json'))),
  contactSha256:hash(await fs.readFile(path.join(root,'review/actual_contact.json'))),
  validationSha256:hash(await fs.readFile(path.join(root,'review/gltf_validation.json'))),
  actualImageSha256:hash(await fs.readFile(path.join(root,'review/actual_strike_contact.png'))),
  packs};
await save(path.join(root,'review/approved_crew.json'),approval);
const reviewHash=hash(await fs.readFile(path.join(root,'review/approved_crew.json')));
const manifestFile=path.join(project,'scripts/blender-character-pipeline/data/approved-assets/frontier_battering_ram.approved.json');
const manifest=JSON.parse(await fs.readFile(manifestFile,'utf8'));
const qcFile=path.join(project,'public/assets/models',manifest.qc),qc=JSON.parse(await fs.readFile(qcFile,'utf8'));
qc.operatorAnimationPacks=packs;qc.operatorCrewReviewHash=reviewHash;
await save(qcFile,qc);
manifest.runtime.operatorAnimationPacks=packs;
manifest.hashes.qcSha256=hash(await fs.readFile(qcFile));
manifest.review.operatorCrewReviewHash=reviewHash;
manifest.review.operatorCrewReviewedAt=approval.reviewedAt;
validateApprovedManifest(manifest,'ram with approved operator dependencies');
await save(manifestFile,manifest);
await save(path.join(root,'review/publication.json'),{status:'published',packs,reviewHash,
  ramModelSha256:hash(await fs.readFile(ramFile)),ramQcSha256:manifest.hashes.qcSha256,
  manifest:path.relative(project,manifestFile).replaceAll('\\','/')});
console.log('Published both verified crew packs and signed dependencies on the unchanged ram manifest. Compile runtime registry next.');
