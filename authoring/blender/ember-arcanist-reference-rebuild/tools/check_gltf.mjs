// Run the installed Khronos validator on the actual staged binary assets.
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
let validator;
try {
  validator = require('gltf-validator');
} catch (error) {
  if (error.code !== 'MODULE_NOT_FOUND') throw error;
  validator = require(path.join(root, 'tmp/gltf-validation/node_modules/gltf-validator'));
}
const stage = JSON.parse(await readFile(path.join(root, 'runtime/runtime_report.json'), 'utf8'));
const results = [];
for (const [lod, data] of Object.entries(stage.lods)) {
  for (const [slot, record] of Object.entries(data.modules)) {
    if (!record.model) throw new Error(`Missing exported model: LOD${lod}/${slot}`);
    const bytes = await readFile(path.join(root, 'runtime', record.model));
    const sha256 = createHash('sha256').update(bytes).digest('hex');
    if (sha256 !== record.sha256) throw new Error(`Changed export: ${record.model}`);
    const result = await validator.validateBytes(new Uint8Array(bytes), { uri: record.model, maxIssues: 200 });
    results.push({ lod: Number(lod), slot, model: record.model, sha256, issues: result.issues, info: result.info });
  }
}
const report = {
  validatorVersion: validator.version(),
  createdAt: new Date().toISOString(),
  completeBundle: results.length === 33,
  errors: results.reduce((sum, record) => sum + record.issues.numErrors, 0),
  warnings: results.reduce((sum, record) => sum + record.issues.numWarnings, 0),
  assets: results,
};
report.status = report.completeBundle && report.errors === 0 ? 'passed' : 'failed';
await writeFile(path.join(root, 'runtime/gltf_validation_report.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({ status: report.status, files: results.length, errors: report.errors, warnings: report.warnings }));
process.exitCode = report.status === 'passed' ? 0 : 1;
