import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const work = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.resolve(work, '../../..');
const retained = path.join(work, 'foundations');
fs.mkdirSync(retained, { recursive: true });
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const records = [];
for (const family of ['civic_humanoid_v2_m', 'civic_humanoid_v2_f', 'mire_brutish_v1_m']) {
  const directory = path.join(root, 'artifacts/model-jobs/local-character-batch-20260713-152623', family);
  const model = `body_${family}.glb`, qcName = `body_${family}.qc.json`;
  const qc = JSON.parse(fs.readFileSync(path.join(directory, qcName), 'utf8'));
  if (hash(fs.readFileSync(path.join(directory, model))) !== qc.modelSha256) throw new Error(`Foundation hash mismatch: ${family}`);
  const files = [];
  for (const [name, targetName] of [[model, model], [qcName, qcName], ['source.blend', `${family}.source.blend`]]) {
    const source = path.join(directory, name), target = path.join(retained, targetName), bytes = fs.readFileSync(source);
    if (fs.existsSync(target) && hash(fs.readFileSync(target)) !== hash(bytes)) throw new Error(`Retained source would change: ${targetName}`);
    if (!fs.existsSync(target)) fs.writeFileSync(target, bytes);
    files.push({ file: path.relative(work, target).replaceAll('\\', '/'), source: path.relative(root, source).replaceAll('\\', '/'), sha256: hash(bytes) });
  }
  records.push({ family, status: 'anatomical-input-not-runtime-approval', files });
}
const policyFile = 'scripts/blender-character-pipeline/data/body-families/free-toolchain.json';
const policy = JSON.parse(fs.readFileSync(path.join(root, policyFile), 'utf8'));
fs.writeFileSync(path.join(work, 'foundation-provenance.json'), JSON.stringify({ schemaVersion: 1,
  description: 'Retained local MakeHuman/MPFB anatomy and embedded texture inputs. Each derivative requires its own art, rig and runtime review.',
  license: 'CC0-1.0 for MakeHuman system asset data; original project morphs and canonical rig adapter retained in repository',
  policy: { file: policyFile, sha256: hash(fs.readFileSync(path.join(root, policyFile))), assetPacks: policy.assetPacks },
  foundations: records,
}, null, 2) + '\n');
console.log(`Retained ${records.length} anatomical foundations and their source/QC bytes.`);
