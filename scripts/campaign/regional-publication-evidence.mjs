import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';

/** Package-relative gate inputs; sourceFiles and saved previews are retained separately. */
export function regionalPublicationAuditPaths(spec, lods) {
  assert(/^[a-z0-9_]+$/.test(spec?.key ?? ''), 'Expected a regional model key');
  assert(Array.isArray(spec.reports) && spec.reports.length
    && spec.reports.every(name => /^[a-z0-9_]+$/.test(name)), 'Expected package audit report names');
  assert.equal(new Set(spec.reports).size, spec.reports.length, 'Duplicate audit report');
  assert.deepEqual(lods.map(lod => lod.level), [0, 1, 2], 'Expected exactly LOD0, LOD1 and LOD2');
  const paths = [`review/${spec.key}_build.json`, 'review/draft-validation.json', 'tools/test_exports.py'];
  for (const lod of lods) {
    assert.equal(lod.model, `${spec.key}_lod${lod.level}.glb`, 'LOD model does not match its package');
    paths.push(`runtime/${lod.model}`, `review/${lod.model}.validation.json`,
      `review/arm-volume-lod${lod.level}.json`, `review/${spec.key}_lod${lod.level}_motion.json`,
      ...spec.reports.map(report => `review/${spec.key}_lod${lod.level}_${report}.json`));
  }
  return paths;
}

function isWithin(root, target) {
  const relative = path.relative(root, target);
  return relative !== '' && relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

/** Retain before executing gates, then recheck before any publication writes. */
export function createPublicationEvidence(root) {
  const absoluteRoot = path.resolve(root), records = new Map();
  let realRoot;
  const retain = async (relative, expectedSha256) => {
    assert(typeof relative === 'string' && relative.length && !relative.includes('\0')
      && !path.isAbsolute(relative) && !path.win32.isAbsolute(relative) && !/^[a-z]:/i.test(relative),
    'Expected a repository-relative evidence path');
    const target = path.resolve(absoluteRoot, relative.replaceAll('\\', '/'));
    assert(isWithin(absoluteRoot, target), 'Evidence path escapes its source root');
    const canonical = path.relative(absoluteRoot, target).replaceAll('\\', '/');
    if (expectedSha256 !== undefined) assert(/^[a-f0-9]{64}$/.test(expectedSha256), 'Expected a SHA-256 evidence digest');
    realRoot ??= fs.realpath(absoluteRoot);
    const realTarget = await fs.realpath(target);
    assert(isWithin(await realRoot, realTarget), 'Evidence symlink escapes its source root');
    const bytes = await fs.readFile(realTarget), sha256 = createHash('sha256').update(bytes).digest('hex');
    if (expectedSha256 !== undefined) assert.equal(sha256, expectedSha256, `Stale evidence: ${canonical}`);
    const previous = records.get(canonical);
    assert(!previous || previous.sha256 === sha256, `Changed input: ${canonical}`);
    records.set(canonical, { sha256, bytes: bytes.length });
    return bytes;
  };
  return {
    retain,
    entries: () => [...records].sort(([a], [b]) => a.localeCompare(b, 'en'))
      .map(([relative, record]) => [relative, { ...record }]),
    async recheck() {
      for (const [relative, record] of records) await retain(relative, record.sha256);
    },
  };
}
