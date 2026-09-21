import { describe, expect, it } from 'vitest';
import { requiredNativeTests, validateAutomationReport, validateImportReceipt } from '../scripts/unreal/editor';

function report() { return { succeeded: requiredNativeTests.length, succeededWithWarnings: 0, failed: 0, notRun: 0, inProcess: 0,
  tests: requiredNativeTests.map(fullTestPath => ({ fullTestPath, state: 'Success', errors: 0 })) }; }

describe('native automation receipt verification', () => {
  it('rejects missing and stale import evidence even if the editor exited successfully', () => {
    const receipt = { schemaVersion: 1, profileKey: 'character', importSucceeded: true,
      status: 'editor-import-succeeded-unreviewed', conversionSha256: 'current', artApproved: false,
      unrealApproved: false, unrealVersion: '5.8.2-test', meshes: [{}] };
    expect(() => validateImportReceipt(receipt, 'character', 'current')).not.toThrow();
    for (const invalid of [null, {}, { ...receipt, conversionSha256: 'old' }, { ...receipt, meshes: [] },
      { ...receipt, profileKey: 'different' }, { ...receipt, artApproved: true }, { ...receipt, unrealVersion: '5.7.0' }]) {
      expect(() => validateImportReceipt(invalid, 'character', 'current')).toThrow('evidence');
    }
  });
  it('requires source skinning comparisons for character imports', () => {
    const receipt = { schemaVersion: 1, profileKey: 'character', kind: 'characterProfiles', importSucceeded: true,
      status: 'editor-import-succeeded-unreviewed', conversionSha256: 'current', artApproved: false,
      unrealApproved: false, unrealVersion: '5.8.2-test', meshes: [{}], animations: [{}] };
    expect(() => validateImportReceipt(receipt, 'character', 'current')).toThrow('skinning');
    const verified = { ...receipt, materials: [{ skeletalMeshUsage: true }], poseParity: { status: 'passed', toleranceCm: 0.1, clips: [{}, {}] } };
    expect(() => validateImportReceipt(verified, 'character', 'current')).not.toThrow();
    expect(() => validateImportReceipt({ ...verified, animations: [{}, {}] }, 'character', 'current')).toThrow('skinning');
    for (const materials of [undefined, [], [{}], [{ skeletalMeshUsage: false }], [{ skeletalMeshUsage: true }, null]]) {
      expect(() => validateImportReceipt({ ...verified, materials }, 'character', 'current')).toThrow('shader usage');
    }
  });
  it('requires actual completed native tests instead of accepting process exit alone', () => {
    expect(validateAutomationReport(report())).toBe(19);
    expect(() => validateAutomationReport({})).toThrow();
    expect(() => validateAutomationReport({ ...report(), tests: [] })).toThrow('did not run');
  });
  it('requires quest marker and camera regressions in every foundation run', () => {
    for (const suffix of ['QuestMarkerVisibility', 'CameraControls', 'MovementInput']) {
      const incomplete = report();
      incomplete.tests = incomplete.tests.filter(test => test.fullTestPath !== `AegisWar.Foundation.${suffix}`);
      incomplete.succeeded--;
      expect(() => validateAutomationReport(incomplete)).toThrow('did not run');
    }
  });
  it('rejects failed, incomplete and unrelated automation reports', () => {
    expect(() => validateAutomationReport({ ...report(), failed: 1 })).toThrow('did not finish');
    expect(() => validateAutomationReport({ ...report(), inProcess: 1 })).toThrow('did not finish');
    const unrelated = report(); unrelated.tests[0].fullTestPath = 'Engine.Other.Test';
    expect(() => validateAutomationReport(unrelated)).toThrow('Unexpected');
    const hiddenError = report(); hiddenError.tests[0].errors = 1;
    expect(() => validateAutomationReport(hiddenError)).toThrow('unsuccessful');
    const duplicate = report(); duplicate.tests[0].fullTestPath = duplicate.tests[1].fullTestPath;
    expect(() => validateAutomationReport(duplicate)).toThrow('exactly once');
  });
});
