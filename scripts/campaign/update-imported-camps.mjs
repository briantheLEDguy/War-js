/** Update just the four camp maps; never regenerate owner-authored scenery. */
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { applyImportedCamps, importedPopulation } from './imported-population.mjs';

const root = new URL('../../', import.meta.url);
const generatedPath = new URL('shared/data/campaign.generated.ts', root);
let generated = readFileSync(generatedPath, 'utf8');
const updates = [];
for (const camp of importedPopulation.camps) {
  const path = new URL(`public/assets/maps/${camp.zone}.json`, root);
  const zone = applyImportedCamps(JSON.parse(readFileSync(path, 'utf8')));
  const previous = zone.staticMapHash;
  const normalized = { ...zone }; delete normalized.staticMapHash;
  zone.staticMapHash = createHash('sha256').update(JSON.stringify(normalized)).digest('hex').slice(0, 16);
  const before = `"${camp.zone}": "${previous}"`;
  if (!generated.includes(before)) throw new Error(`Generated map hash is stale: ${camp.zone}`);
  generated = generated.replace(before, `"${camp.zone}": "${zone.staticMapHash}"`);
  updates.push([path, `${JSON.stringify(zone, null, 2)}\n`]);
}
for (const [path, content] of updates) writeFileSync(path, content);
writeFileSync(generatedPath, generated);
