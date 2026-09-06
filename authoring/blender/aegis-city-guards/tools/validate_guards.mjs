import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const validator = require(process.env.GLTF_VALIDATOR_PATH || 'gltf-validator');
const build = JSON.parse(readFileSync(path.join(root, 'runtime/build-report.json')));
const results = [];
for (const [variant, lods] of Object.entries(build.variants)) {
  for (const [lod, record] of Object.entries(lods)) {
    const bytes = readFileSync(path.join(root, 'runtime', record.file));
    const hash = createHash('sha256').update(bytes).digest('hex');
    if (hash !== record.sha256) throw new Error(`Hash mismatch ${record.file}`);
    const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
    if (!json.skins?.length || !json.animations?.some(a => a.name === 'idle')) throw new Error(`Missing rig/idle: ${record.file}`);
    if (json.images?.some(i => i.uri && !i.uri.startsWith('data:'))) throw new Error(`External texture: ${record.file}`);
    const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: record.file, maxIssues: 100 });
    results.push({ variant, lod, file: record.file, sha256: hash, animations: json.animations.map(a => a.name),
      primitives: json.meshes.reduce((sum,m) => sum+m.primitives.length, 0), issues: validation.issues });
  }
}
const report = { files: results.length, errors: results.reduce((s,r) => s+r.issues.numErrors,0), warnings: results.reduce((s,r) => s+r.issues.numWarnings,0), results };
writeFileSync(path.join(root,'runtime/validation.json'), JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({files:report.files,errors:report.errors,warnings:report.warnings}));
if (report.files !== 12 || report.errors) process.exitCode=1;
