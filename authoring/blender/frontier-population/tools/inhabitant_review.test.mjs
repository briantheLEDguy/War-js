import { test } from 'node:test';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import { INHABITANT_CLIPS, inside, requireCharacterViews, requireCurrentApproval } from './inhabitant_review.mjs';

test('repeated stills cannot replace distinct full-character animation evidence', () => {
  const close = ['front', 'head', 'run_side', 'death:2'].map(view => ({ view }));
  const motion = INHABITANT_CLIPS.flatMap(clip => [0, .5, 1].map(seconds => ({ clip, seconds })));
  requireCharacterViews(close, motion);
  assert.throws(() => requireCharacterViews(close, motion.filter(view => view.clip !== 'jump')));
  assert.throws(() => requireCharacterViews(close, motion.map(view => view.clip === 'death' ? { ...view, seconds: 0 } : view)));
  assert.throws(() => requireCharacterViews(close.filter(view => view.view !== 'head'), motion));
});

test('model, source and image mutations revoke a previous visual decision', () => {
  const evidence = { models: [{ sha256: 'model-a' }], files: { source: 'source-a', image: 'image-a' } };
  const review = { status: 'approved', reviewedBy: 'Reviewer', reviewedAt: '2026-09-09T00:00:00Z', evidence: structuredClone(evidence) };
  requireCurrentApproval(review, evidence);
  for (const changed of [{ ...evidence, models: [{ sha256: 'model-b' }] },
    { ...evidence, files: { ...evidence.files, source: 'source-b' } }, { ...evidence, files: { ...evidence.files, image: 'image-b' } }]) {
    assert.throws(() => requireCurrentApproval(review, changed));
  }
  assert.throws(() => requireCurrentApproval({ ...review, status: 'pending' }, evidence));
});

test('frozen source paths cannot escape into another directory', () => {
  const root = path.join(os.tmpdir(), 'inhabitant-evidence');
  assert.equal(inside(root, 'source/body.blend'), path.join(root, 'source/body.blend'));
  for (const relative of ['../secret', 'source/../../secret', path.resolve(root, '../secret')]) assert.throws(() => inside(root, relative));
});
