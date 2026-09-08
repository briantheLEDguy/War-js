/** Technical draft validation; this does not confer visual approval. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const clips = ['attack_melee', 'attack_ranged', 'cast', 'combat_idle', 'death', 'idle', 'jump', 'run', 'walk'];
const records = [];
const failures = [];
for (const filename of (await fs.readdir(path.join(root, 'review'))).filter(name => name.endsWith('_build.json'))) {
  const build = JSON.parse(await fs.readFile(path.join(root, 'review', filename), 'utf8'));
  if (build.lods.length !== 3) failures.push(`${build.key}: expected three LODs`);
  for (const lod of build.lods) {
    const bytes = await fs.readFile(path.join(root, 'runtime', lod.model));
    const document = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
    const result = await validator.validateBytes(new Uint8Array(bytes), { uri: lod.model });
    const observed = document.animations.map(animation => animation.name).sort();
    if (JSON.stringify(observed) !== JSON.stringify(clips)) failures.push(`${lod.model}: animation contract mismatch`);
    if (hash(bytes) !== lod.sha256) failures.push(`${lod.model}: build hash mismatch`);
    if (result.issues.numErrors) failures.push(`${lod.model}: ${result.issues.numErrors} glTF errors`);
    if (document.images.some(image => image.uri)) failures.push(`${lod.model}: external image not retained in GLB`);
    await fs.writeFile(path.join(root, 'review', `${lod.model}.validation.json`), JSON.stringify(result, null, 2) + '\n');
    records.push({ model: lod.model, sha256: hash(bytes), triangles: lod.triangles,
      errors: result.issues.numErrors, warnings: result.issues.numWarnings,
      warningCodes: [...new Set(result.issues.messages.filter(issue => issue.severity === 1).map(issue => issue.code))] });
  }
}
const report = { passed: failures.length === 0, visualApproval: false, records, failures };
await fs.writeFile(path.join(root, 'review', 'draft-validation.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
if (failures.length) process.exitCode = 1;
