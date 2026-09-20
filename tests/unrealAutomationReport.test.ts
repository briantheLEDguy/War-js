import { describe, expect, it } from 'vitest';
import { requiredNativeTests, validateAutomationReport } from '../scripts/unreal/editor';

function report() { return { succeeded: requiredNativeTests.length, succeededWithWarnings: 0, failed: 0, notRun: 0, inProcess: 0,
  tests: requiredNativeTests.map(fullTestPath => ({ fullTestPath, state: 'Success', errors: 0 })) }; }

describe('native automation receipt verification', () => {
  it('requires actual completed native tests instead of accepting process exit alone', () => {
    expect(validateAutomationReport(report())).toBe(7);
    expect(() => validateAutomationReport({})).toThrow();
    expect(() => validateAutomationReport({ ...report(), tests: [] })).toThrow('did not run');
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
