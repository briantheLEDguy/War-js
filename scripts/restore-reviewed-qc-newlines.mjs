import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const models = path.join(root, 'public/assets/models');
const registry = JSON.parse(fs.readFileSync(path.join(models, 'asset-index.json'), 'utf8'));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const checked = new Set();
const changes = [];
for (const entry of Object.values(registry.characterProfiles ?? {})) {
  if (!entry.runtimeReady || !entry.qc || checked.has(entry.qc)) continue;
  checked.add(entry.qc);
  const target = path.resolve(models, entry.qc);
  if (!target.startsWith(models + path.sep)) throw new Error('QC path leaves the model directory');
  const bytes = fs.readFileSync(target);
  if (hash(bytes) === entry.qcSha256) continue;
  const original = Buffer.from(bytes.toString('utf8').replaceAll('\r\n', '\n'));
  if (hash(original) !== entry.qcSha256) throw new Error(`QC content differs from its reviewed hash: ${entry.qc}`);
  changes.push({ target, original });
}
// Never rewrite evidence to fit a new hash: restore only bytes proven by the existing approval.
if (process.argv.includes('--write')) for (const { target, original } of changes) fs.writeFileSync(target, original);
console.log(`${process.argv.includes('--write') ? 'Restored' : 'Would restore'} ${changes.length} character QC files to their approved newline bytes.`);
