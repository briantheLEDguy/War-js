import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { applyContentSync, contentPath, planContentSync, validateContentFiles, type NativeContentManifest } from '../scripts/unreal/native-content';

const directories: string[] = [];
const digest = (value: string) => createHash('sha256').update(value).digest('hex');
afterEach(() => directories.splice(0).forEach(dir => rmSync(dir, { recursive: true, force: true })));
function setup() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'aegis-content-')); directories.push(root);
  const source = path.join(root, 'source'), destination = path.join(root, 'project');
  mkdirSync(path.join(source, 'Content'), { recursive: true }); mkdirSync(path.join(destination, 'Content'), { recursive: true });
  writeFileSync(path.join(source, 'Content/Map.umap'), 'new');
  const manifest: NativeContentManifest = { schemaVersion: 1, engineVersion: '5.8.2', sourceCodeCommit: 'a'.repeat(40), sourceCodeDirty: false, ready: true,
    files: [{ path: 'Content/Map.umap', bytes: 3, sha256: digest('new'), distributable: true }] };
  return { source, destination, manifest };
}
describe('private native content synchronization', () => {
  it.each(['../outside', 'Content/../outside', 'C:/outside', 'Content/file:stream', 'Content\\file', '/outside'])('rejects unsafe path %s', value => {
    expect(() => contentPath(os.tmpdir(), value)).toThrow();
  });
  it('fails closed for pending rights and dishonest readiness', () => {
    const { manifest, source, destination } = setup();
    manifest.ready = false; manifest.files[0].distributable = false;
    expect(() => planContentSync(manifest, source, destination)).toThrow('review is incomplete');
    manifest.ready = true;
    expect(() => validateContentFiles(manifest)).toThrow('readiness');
  });
  it('preflights every source without changing the destination', () => {
    const { manifest, source, destination } = setup();
    writeFileSync(path.join(destination, 'Content/Map.umap'), 'local');
    expect(() => planContentSync(manifest, source, destination)).toThrow('Preserve local edit');
    expect(readFileSync(path.join(destination, 'Content/Map.umap'), 'utf8')).toBe('local');
    writeFileSync(path.join(source, 'Content/Map.umap'), 'bad');
    expect(() => planContentSync(manifest, source, destination)).toThrow('corrupt source');
  });
  it('updates an unchanged previously installed file and skips matching files', () => {
    const { manifest, source, destination } = setup();
    writeFileSync(path.join(destination, 'Content/Map.umap'), 'old');
    expect(planContentSync(manifest, source, destination, { 'Content/Map.umap': digest('old') })).toHaveLength(1);
    writeFileSync(path.join(destination, 'Content/Map.umap'), 'new');
    expect(planContentSync(manifest, source, destination)).toHaveLength(0);
  });
  it('rejects case-insensitive duplicate packages and empty ready manifests', () => {
    const { manifest } = setup();
    manifest.files.push({ ...manifest.files[0], path: 'Content/map.umap' });
    expect(() => validateContentFiles(manifest)).toThrow('duplicate');
    manifest.files = [];
    expect(() => validateContentFiles(manifest)).toThrow('readiness');
  });
  it('refuses dirty-code baselines and edits made after preflight', () => {
    const { manifest, source, destination } = setup();
    manifest.sourceCodeDirty = true;
    expect(() => planContentSync(manifest, source, destination)).toThrow('uncommitted code');
    manifest.sourceCodeDirty = false;
    const actions = planContentSync(manifest, source, destination);
    writeFileSync(path.join(destination, 'Content/Map.umap'), 'new local work');
    expect(() => applyContentSync(actions)).toThrow('after preflight');
    expect(readFileSync(path.join(destination, 'Content/Map.umap'), 'utf8')).toBe('new local work');
  });
  it('installs validated source bytes and refuses a changed source without overwriting', () => {
    const { manifest, source, destination } = setup();
    const actions = planContentSync(manifest, source, destination);
    writeFileSync(path.join(source, 'Content/Map.umap'), 'tampered');
    expect(() => applyContentSync(actions)).toThrow('Source changed');
    writeFileSync(path.join(source, 'Content/Map.umap'), 'new');
    applyContentSync(actions);
    expect(readFileSync(path.join(destination, 'Content/Map.umap'), 'utf8')).toBe('new');
  });
});
