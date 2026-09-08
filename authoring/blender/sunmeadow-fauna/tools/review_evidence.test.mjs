import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { localPath, verifyFiles, requireViews, sha } from './review_evidence.mjs';

test('signed render bytes cannot change while retaining their receipt', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'fauna-evidence-'));
  try {
    await fs.writeFile(path.join(root, 'render.png'), 'actual-glb-render');
    const files = { 'render.png': sha('actual-glb-render') };
    await verifyFiles(root, files);
    await fs.writeFile(path.join(root, 'render.png'), 'different-model');
    await assert.rejects(verifyFiles(root, files), /Changed evidence/);
  } finally {
    assert(path.resolve(root).startsWith(path.resolve(os.tmpdir()) + path.sep + 'fauna-evidence-'));
    await fs.rm(root, { recursive: true, force: true });
  }
});
test('package evidence rejects paths outside its source snapshot', () => {
  assert.throws(() => localPath(path.resolve('package'), '../private.json'), /escapes/);
});
test('a resting proof cannot approve motion and repeated phases do not count', () => {
  const renders = [0, 1, 2].map(level => ({ level, state: 'rest', view: 'full' }));
  renders.push({ level: 0, state: 'rest', view: 'head' });
  assert.throws(() => requireViews(renders, ['run']), /incomplete/);
  renders.push(...Array.from({ length: 8 }, () => ({ level: 0, state: 'run@0', view: 'profile' })));
  assert.throws(() => requireViews(renders, ['run']), /incomplete/);
  renders.push(...Array.from({ length: 8 }, (_, i) => ({ level: 0, state: `run@${i / 8}`, view: 'profile' })));
  requireViews(renders, ['run']);
});
test('death review includes the held terminal pose', () => {
  const renders = [0, 1, 2].map(level => ({ level, state: 'rest', view: 'full' }));
  renders.push({ level: 0, state: 'rest', view: 'head' });
  renders.push(...[0, .25, .5, .75].map(t => ({ level: 0, state: `death@${t}`, view: 'profile' })));
  assert.throws(() => requireViews(renders, ['death']), /final pose/);
});
