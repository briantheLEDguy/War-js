import fs from 'node:fs/promises';
import path from 'node:path';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import { afterEach, expect, test } from 'vitest';
// @ts-expect-error Campaign publication helpers are executable JavaScript.
import { createPublicationEvidence, regionalPublicationAuditPaths } from '../scripts/campaign/regional-publication-evidence.mjs';
// @ts-expect-error These are the production publisher's package-specific gate contracts.
import { REGIONAL_CHARACTER_PACKAGES } from '../scripts/campaign/publish-regional-inhabitant.mjs';

const temporary: string[] = [];
const hash = (value: string) => createHash('sha256').update(value).digest('hex');
async function fixture() {
  const directory = await fs.mkdtemp(path.join(tmpdir(), 'warjs-publication-evidence-'));
  temporary.push(directory);
  const root = path.join(directory, 'repo');
  await fs.mkdir(path.join(root, 'review'), { recursive: true });
  await fs.writeFile(path.join(root, 'review/clearance.json'), '{"passed":true}');
  await fs.writeFile(path.join(root, 'source.txt'), 'original');
  await fs.writeFile(path.join(directory, 'outside.txt'), 'outside');
  return { directory, root, snapshot: createPublicationEvidence(root) };
}

afterEach(async () => {
  for (const directory of temporary.splice(0)) {
    const resolved = path.resolve(directory);
    if (path.dirname(resolved) !== path.resolve(tmpdir()) || !path.basename(resolved).startsWith('warjs-publication-evidence-')) {
      throw new Error('Refusing cleanup outside the test temporary directories');
    }
    await fs.rm(resolved, { recursive: true, force: true });
  }
});

test.each([
  ['sunmeadow-farmer', ['boot_clearance', 'welt']],
  ['cinderfen-peat-worker', ['garment_clearance', 'welt', 'tool_clearance']],
] as const)('%s retains all current package gate inputs for three LODs', (name, requiredReports) => {
  const spec = REGIONAL_CHARACTER_PACKAGES[name];
  const lods = [0, 1, 2].map(level => ({ level, model: `${spec.key}_lod${level}.glb` }));
  const paths = regionalPublicationAuditPaths(spec, lods);
  expect(paths).toContain(`review/${spec.key}_build.json`);
  expect(paths).toContain('review/draft-validation.json');
  expect(paths).toContain('tools/test_exports.py');
  for (const lod of lods) {
    expect(paths).toContain(`runtime/${lod.model}`);
    expect(paths).toContain(`review/${lod.model}.validation.json`);
    expect(paths).toContain(`review/arm-volume-lod${lod.level}.json`);
    expect(paths).toContain(`review/${spec.key}_lod${lod.level}_motion.json`);
    for (const report of requiredReports) expect(paths).toContain(`review/${spec.key}_lod${lod.level}_${report}.json`);
  }
  expect(new Set(paths).size).toBe(paths.length);
  expect(paths).toHaveLength(3 + 3 * (4 + requiredReports.length));
});

test('audit enumeration rejects incomplete or mismatched LOD packages', () => {
  const spec = REGIONAL_CHARACTER_PACKAGES['sunmeadow-farmer'];
  const lods = [0, 1, 2].map(level => ({ level, model: `${spec.key}_lod${level}.glb` }));
  expect(() => regionalPublicationAuditPaths(spec, lods.slice(0, 2))).toThrow('Expected exactly');
  expect(() => regionalPublicationAuditPaths(spec, [lods[0], lods[0], lods[2]])).toThrow('Expected exactly');
  expect(() => regionalPublicationAuditPaths(spec, [lods[0], { ...lods[1], model: '../another.glb' }, lods[2]]))
    .toThrow('LOD model does not match');
  expect(() => regionalPublicationAuditPaths({ ...spec, reports: ['../outside'] }, lods)).toThrow('audit report names');
});

test('evidence retains literal bytes and canonical paths, and rechecks without writing', async () => {
  const { root, snapshot } = await fixture();
  const bytes = await snapshot.retain('review\\clearance.json');
  expect(bytes.toString()).toBe('{"passed":true}');
  await snapshot.retain('review/../review/clearance.json', hash(bytes.toString()));
  await snapshot.retain('source.txt', hash('original'));
  const entries = snapshot.entries();
  expect(entries).toEqual([
    ['review/clearance.json', { sha256: hash('{"passed":true}'), bytes: 15 }],
    ['source.txt', { sha256: hash('original'), bytes: 8 }],
  ]);
  entries[0][1].sha256 = 'changed by caller';
  await expect(snapshot.recheck()).resolves.toBeUndefined();
  expect(snapshot.entries()[0][1].sha256).toBe(hash('{"passed":true}'));
  expect((await fs.readdir(root)).sort()).toEqual(['review', 'source.txt']);
});

test('changed gate input bytes fail the final check even when their size stays identical', async () => {
  const { root, snapshot } = await fixture();
  await snapshot.retain('source.txt');
  const before = snapshot.entries();
  await fs.writeFile(path.join(root, 'source.txt'), 'modified');
  await expect(snapshot.recheck()).rejects.toThrow('Stale evidence: source.txt');
  await expect(snapshot.retain('source.txt')).rejects.toThrow('Changed input: source.txt');
  expect(snapshot.entries()).toEqual(before);
});

test('stale expected hashes and removed inputs cannot become accepted evidence', async () => {
  const { root, snapshot } = await fixture();
  await expect(snapshot.retain('source.txt', hash('earlier version'))).rejects.toThrow('Stale evidence: source.txt');
  expect(snapshot.entries()).toHaveLength(0);
  await snapshot.retain('review/clearance.json');
  await fs.unlink(path.join(root, 'review/clearance.json'));
  await expect(snapshot.recheck()).rejects.toMatchObject({ code: 'ENOENT' });
});

test('evidence paths cannot escape by traversal, absolute names, or directory symlinks', async () => {
  const { directory, root, snapshot } = await fixture();
  for (const file of ['../outside.txt', '..\\outside.txt', '.', path.join(directory, 'outside.txt'),
    'C:\\outside.txt', 'C:outside.txt', '/outside.txt']) {
    await expect(snapshot.retain(file)).rejects.toThrow();
  }
  await fs.symlink(directory, path.join(root, 'outside-link'), process.platform === 'win32' ? 'junction' : 'dir');
  await expect(snapshot.retain('outside-link/outside.txt')).rejects.toThrow('Evidence symlink escapes its source root');
  expect(snapshot.entries()).toHaveLength(0);
});
