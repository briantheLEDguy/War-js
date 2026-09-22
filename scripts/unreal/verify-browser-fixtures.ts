import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { readBrowserReference } from './browser-reference';
import { isMain, repoRoot } from './toolchain';

export function verifyBrowserFixture(name: string): void {
  if (!['inventory', 'salvage', 'progression', 'quests'].includes(name)) throw new Error('Unknown reference fixture');
  const fixture = JSON.parse(readFileSync(path.join(repoRoot, 'migration/fixtures', `${name}.json`), 'utf8'));
  const manifest = JSON.parse(readFileSync(path.join(repoRoot, 'migration/browser-reference.json'), 'utf8'));
  const fingerprint = createHash('sha256').update(JSON.stringify(fixture)).digest('hex');
  if (fingerprint !== manifest.fixtures[name]) throw new Error(`Frozen ${name} fixture changed`);
  const sources = fixture.sources ?? [{ source: fixture.source, sha256: fixture.sourceSha256 }];
  for (const source of sources) {
    if (createHash('sha256').update(readBrowserReference(source.source)).digest('hex') !== source.sha256)
      throw new Error(`Historical fixture source changed: ${source.source}`);
  }
}

if (isMain(import.meta.url)) {
  const names = process.argv.slice(2);
  for (const name of names.length ? names : ['inventory', 'salvage', 'progression', 'quests']) {
    verifyBrowserFixture(name);
    console.log(`Verified immutable ${name} reference; regenerate only in the tagged browser checkout.`);
  }
}
