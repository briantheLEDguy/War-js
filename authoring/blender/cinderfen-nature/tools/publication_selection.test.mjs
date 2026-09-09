import test from 'node:test';
import assert from 'node:assert/strict';
import { publicationSelection, verifySelectionReview } from './publication_selection.mjs';

const known = ['alder', 'basalt', 'reeds', 'sedge'];
test('selection is exact, order-independent and never overwrites the complete build report', () => {
  assert.deepEqual(publicationSelection(known, 'reeds,basalt'), publicationSelection(known, 'basalt,reeds'));
  const selected = publicationSelection(known, 'basalt,reeds');
  assert.notEqual(selected.build, 'build-report.json');
  assert.notEqual(selected.review, publicationSelection(known).review);
  assert.deepEqual(selected.ids, ['basalt', 'reeds']);
  for (const value of ['', 'typo', 'reeds,reeds', 'reeds,']) assert.throws(() => publicationSelection(known, value));
});
test('scope, current build, every reviewed view and named visual decision are all required', () => {
  const selection = publicationSelection(known, 'basalt,reeds');
  const receipt = { approved: true, reviewedBy: 'reviewer', reviewedAt: '2026-09-09T12:00:00Z',
    assetIds: selection.ids, buildSha256: 'exact-build', images: { 'neutral.png': 'hash1', 'gameplay.png': 'hash2' } };
  const verify = changed => verifySelectionReview(changed, selection, 'exact-build', receipt.images);
  assert.doesNotThrow(() => verify(receipt));
  for (const change of [{ approved:false }, { reviewedBy:'' }, { reviewedAt:'invalid' },
    { assetIds: [...selection.ids, 'alder'] }, { assetIds:['basalt'] }, { buildSha256:'old' },
    { images:{'neutral.png':'hash1'} }, { images:{...receipt.images,'gameplay.png':'changed'} }]) {
    assert.throws(() => verify({...receipt,...change}));
  }
});
