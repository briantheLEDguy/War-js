import { expect, it } from 'vitest';
import { battlefieldBaseline } from '../scripts/unreal/prepare-t1-battlefield';

const baseline = { name: 'review-123456789abc.json', receipt: { signature: '123456789abc' + '1'.repeat(52),
  parentSignature: 'relief', sourcePackagesUnchanged: true, ownerDocumentsPreserved: true, inputs: { createdUtc: '2026-10-08T08:00:00Z' } } };

it('retains the frozen baseline after a newer battlefield walkthrough is staged', () => {
  const newer = { name: 'review-abcdef123456.json', receipt: { ...baseline.receipt,
    signature: 'abcdef123456' + '2'.repeat(52), parentSignature: 'battlefield', inputs: { createdUtc: '2026-10-08T12:00:00Z' } } };
  expect(battlefieldBaseline([newer, baseline], 'relief')).toEqual(baseline);
});

it('rejects mutable names, mismatched revisions and unpreserved source/owner receipts', () => {
  for (const row of [{ ...baseline, name: 'review-latest.json' }, { ...baseline, name: 'review-abcdef123456.json' },
    { ...baseline, receipt: { ...baseline.receipt, sourcePackagesUnchanged: false } },
    { ...baseline, receipt: { ...baseline.receipt, ownerDocumentsPreserved: false } }]) expect(battlefieldBaseline([row], 'relief')).toBeUndefined();
});
