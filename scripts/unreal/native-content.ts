import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { copyFileSync, existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, realpathSync, renameSync, unlinkSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { isMain, repoRoot } from './toolchain';

export interface ContentFile { path: string; sha256: string; bytes: number; distributable: boolean }
export interface NativeContentManifest {
  schemaVersion: 1;
  engineVersion: string;
  sourceCodeCommit: string;
  sourceCodeDirty: boolean;
  files: ContentFile[];
  ready: boolean;
}
interface Policy { engineVersion: string; approvedRoots: Array<{ root: string; evidence: string }> }
const hash = (data: Buffer) => createHash('sha256').update(data).digest('hex');

/** Reject traversal, NTFS alternate streams, and links across the package boundary. */
export function contentPath(root: string, relative: string): string {
  if (!relative || relative.includes('\\') || relative.includes(':') || path.isAbsolute(relative)
    || relative.split('/').some(part => !part || part === '.' || part === '..')) throw new Error('Unsafe content path');
  const base = path.resolve(root), target = path.resolve(base, relative);
  if (existsSync(base) && lstatSync(base).isSymbolicLink()) throw new Error('Linked content roots are forbidden');
  if (!target.startsWith(base + path.sep)) throw new Error('Content escapes root');
  let current = base;
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    if (existsSync(current) && lstatSync(current).isSymbolicLink()) throw new Error('Linked content is forbidden');
  }
  return target;
}

export function validateContentFiles(manifest: NativeContentManifest): void {
  if (manifest.schemaVersion !== 1 || manifest.engineVersion !== '5.8.2' || !Array.isArray(manifest.files)
    || !/^[a-f0-9]{40}$/.test(manifest.sourceCodeCommit) || typeof manifest.sourceCodeDirty !== 'boolean') throw new Error('Invalid native content manifest');
  const paths = new Set<string>();
  for (const file of manifest.files) {
    contentPath(repoRoot, file.path);
    if (!file.path.startsWith('Content/') || !/\.(uasset|umap|png|json|txt)$/i.test(file.path)
      || !/^[a-f0-9]{64}$/.test(file.sha256) || !Number.isSafeInteger(file.bytes) || file.bytes < 0
      || typeof file.distributable !== 'boolean' || paths.has(file.path.toLowerCase())) throw new Error('Invalid or duplicate native content entry');
    paths.add(file.path.toLowerCase());
  }
  if (manifest.ready !== (manifest.files.length > 0 && manifest.files.every(file => file.distributable)))
    throw new Error('Native content readiness does not match license coverage');
}

export function inventoryNativeContent(projectRoot: string, policy: Policy): NativeContentManifest {
  const files: ContentFile[] = [];
  for (const approval of policy.approvedRoots) {
    contentPath(projectRoot, `Content/${approval.root}`);
    const evidence = contentPath(repoRoot, approval.evidence);
    if (!existsSync(evidence) || !readFileSync(evidence, 'utf8').trim()) throw new Error('Missing distribution-rights evidence');
  }
  function walk(relative: string): void {
    for (const entry of readdirSync(contentPath(projectRoot, relative), { withFileTypes: true })) {
      const child = `${relative}/${entry.name}`, location = contentPath(projectRoot, child);
      if (entry.isSymbolicLink()) throw new Error('Linked native assets cannot be snapshotted');
      if (entry.isDirectory()) walk(child);
      else {
        const bytes = readFileSync(location);
        files.push({ path: child, sha256: hash(bytes), bytes: bytes.length,
          distributable: policy.approvedRoots.some(approval => child.startsWith(`Content/${approval.root}/`)) });
      }
    }
  }
  walk('Content');
  const manifest: NativeContentManifest = { schemaVersion: 1, engineVersion: policy.engineVersion,
    sourceCodeCommit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repoRoot, encoding: 'utf8' }).trim(),
    sourceCodeDirty: Boolean(execFileSync('git', ['status', '--porcelain', '--untracked-files=normal'], { cwd: repoRoot, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()),
    files: files.sort((a, b) => a.path.localeCompare(b.path)), ready: files.length > 0 && files.every(file => file.distributable) };
  validateContentFiles(manifest);
  return manifest;
}

interface ContentCopy { source: string; destination: string; sha256: string; previousHash: string | null }
export function planContentSync(manifest: NativeContentManifest, source: string, destination: string,
  previous: Record<string, string> = {}): ContentCopy[] {
  validateContentFiles(manifest);
  if (!manifest.ready) throw new Error('Content distribution review is incomplete; synchronization is closed');
  if (manifest.sourceCodeDirty) throw new Error('Content was captured from uncommitted code; recreate it from a clean revision');
  if (realpathSync(source) === realpathSync(destination)) throw new Error('Source and destination must differ');
  const actions = [];
  for (const file of manifest.files) {
    const input = contentPath(source, file.path), output = contentPath(destination, file.path);
    if (!existsSync(input) || lstatSync(input).size !== file.bytes || hash(readFileSync(input)) !== file.sha256) throw new Error(`Missing/corrupt source: ${file.path}`);
    let previousHash: string | null = null;
    if (existsSync(output)) {
      const current = hash(readFileSync(output));
      if (current === file.sha256) continue;
      if (current !== previous[file.path]) throw new Error(`Preserve local edit before synchronization: ${file.path}`);
      previousHash = current;
    }
    actions.push({ source: input, destination: output, sha256: file.sha256, previousHash });
  }
  return actions;
}

/** Stage bytes before replacement and recheck local edits made after preflight. */
export function applyContentSync(actions: ContentCopy[]): void {
  for (const action of actions) {
    mkdirSync(path.dirname(action.destination), { recursive: true });
    const temporary = path.join(path.dirname(action.destination), `.aegis-sync-${randomUUID()}.tmp`);
    try {
      copyFileSync(action.source, temporary);
      if (hash(readFileSync(temporary)) !== action.sha256) throw new Error('Source changed during content installation');
      const current = existsSync(action.destination) ? hash(readFileSync(action.destination)) : null;
      if (current !== action.previousHash) throw new Error('Local content changed after preflight; refusing overwrite');
      renameSync(temporary, action.destination);
    } finally {
      if (existsSync(temporary)) unlinkSync(temporary);
    }
  }
}

if (isMain(import.meta.url)) {
  const [mode, directory] = process.argv.slice(2);
  const project = path.join(repoRoot, 'unreal/AegisWar');
  if (mode === 'inventory') {
    const policy = JSON.parse(readFileSync(path.join(repoRoot, 'migration/native-content-policy.json'), 'utf8')) as Policy;
    const manifest = inventoryNativeContent(project, policy);
    const output = path.join(repoRoot, 'artifacts/native-content-repo');
    mkdirSync(output, { recursive: true });
    for (const file of manifest.files.filter(file => file.distributable)) {
      const target = contentPath(output, file.path);
      if (existsSync(target) && hash(readFileSync(target)) !== file.sha256) throw new Error(`Content snapshot already differs: ${file.path}`);
      mkdirSync(path.dirname(target), { recursive: true });
      copyFileSync(contentPath(project, file.path), target);
      if (hash(readFileSync(target)) !== file.sha256) throw new Error('Native snapshot verification failed');
    }
    writeFileSync(path.join(output, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
    console.log(JSON.stringify({ files: manifest.files.length, distributable: manifest.files.filter(f => f.distributable).length, ready: manifest.ready, output }));
  } else if ((mode === 'check' || mode === 'sync') && directory) {
    const source = path.resolve(directory);
    const lock = JSON.parse(readFileSync(path.join(repoRoot, 'migration/native-content.lock.json'), 'utf8'));
    const revision = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: source, encoding: 'utf8' }).trim();
    const manifestFile = path.join(source, 'manifest.json');
    if (revision !== lock.commit || hash(readFileSync(manifestFile)) !== lock.manifestSha256) throw new Error('Content checkout does not match pinned revision/manifest');
    const manifest = JSON.parse(readFileSync(manifestFile, 'utf8')) as NativeContentManifest;
    const stateFile = path.join(repoRoot, 'artifacts/native-content-installed.json');
    const previous = existsSync(stateFile) ? JSON.parse(readFileSync(stateFile, 'utf8')).files : {};
    const actions = planContentSync(manifest, source, project, previous);
    if (mode === 'sync') {
      applyContentSync(actions);
      mkdirSync(path.dirname(stateFile), { recursive: true });
      writeFileSync(stateFile, JSON.stringify({ commit: revision, files: Object.fromEntries(manifest.files.map(f => [f.path, f.sha256])) }, null, 2) + '\n');
    }
    console.log(JSON.stringify({ mode, requiredWrites: actions.length, ready: true }));
  } else throw new Error('Usage: native-content.ts inventory | check <private-checkout> | sync <private-checkout>');
}
