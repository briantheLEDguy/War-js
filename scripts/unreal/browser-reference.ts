import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { repoRoot } from './toolchain';

interface ReferenceManifest {
  commit: string;
  contentSha256: string;
  files: Record<string, string>;
}

/** Historical evidence is immutable and never substitutes for native acceptance. */
export function readBrowserReference(relative: string, root = repoRoot): string {
  const manifest = JSON.parse(readFileSync(path.join(root, 'migration/browser-reference.json'), 'utf8')) as ReferenceManifest;
  if (!/^[a-f0-9]{40}$/.test(manifest.commit) || !Object.hasOwn(manifest.files, relative)
    || relative.includes('..') || !/^(src|tests|server)\/[\w/.-]+$/.test(relative)) {
    throw new Error(`Unregistered browser reference: ${relative}`);
  }
  let contents: string;
  try {
    contents = execFileSync('git', ['show', `${manifest.commit}:${relative}`],
      { cwd: root, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'] }).replace(/\r\n/g, '\n');
  } catch {
    throw new Error(`Browser evidence unavailable: ${relative}. Fetch browser-reference-before-retirement-20260922 (full history required).`);
  }
  const actual = createHash('sha256').update(contents).digest('hex');
  if (actual !== manifest.files[relative]) throw new Error(`Browser evidence hash mismatch: ${relative}`);
  return contents;
}
