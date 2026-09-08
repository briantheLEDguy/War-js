import { afterEach, expect, test, vi } from 'vitest';
import { FrameDiagnostics, type FrameSample } from '../src/game/FrameDiagnostics';

afterEach(() => vi.unstubAllGlobals());
const sample = (intervalMs: number): FrameSample => ({ intervalMs, simulationMs: 1, cameraMs: .2,
  submissionMs: 2, calls: 5, triangles: 100, programs: 3 });

test('diagnostics are opt-in and never expose an API by default', () => {
  const window = { location: { search: '' } }; vi.stubGlobal('window', window);
  const diagnostics = new FrameDiagnostics(); diagnostics.record(sample(20));
  expect(diagnostics.latest).toBeUndefined(); expect(window).not.toHaveProperty('__warPerformance');
});

test('bounded samples retain rendered intervals in order, reset and respect replacement ownership', () => {
  vi.stubGlobal('window', { location: { search: '?performance' } });
  const diagnostics = new FrameDiagnostics();
  for (let i = 0; i < 18_010; i++) diagnostics.record(sample(i));
  expect(window.__warPerformance!.snapshot()).toHaveLength(18_000);
  expect(window.__warPerformance!.snapshot()[0].intervalMs).toBe(10);
  expect(diagnostics.latest?.intervalMs).toBe(18_009);
  window.__warPerformance!.reset(); expect(diagnostics.latest).toBeUndefined();
  const replacement = new FrameDiagnostics(); diagnostics.dispose();
  expect(window.__warPerformance).toBeDefined();
  replacement.dispose(); expect(window.__warPerformance).toBeUndefined();
});
