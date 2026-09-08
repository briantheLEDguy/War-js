export interface FrameSample {
  intervalMs: number;
  simulationMs: number;
  cameraMs: number;
  submissionMs: number;
  calls: number;
  triangles: number;
  programs: number;
}

/** Explicitly enabled, bounded diagnostics. Submission is CPU time, not GPU time. */
export class FrameDiagnostics {
  readonly enabled = typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('performance');
  private samples: FrameSample[] = [];
  private cursor = 0;
  private api = { reset: () => { this.samples = []; this.cursor = 0; }, snapshot: () => this.samples.length < 18_000
    ? this.samples.slice() : [...this.samples.slice(this.cursor), ...this.samples.slice(0, this.cursor)] };

  get latest(): FrameSample | undefined { return this.samples[(this.cursor + 17_999) % 18_000]; }

  constructor() {
    if (this.enabled) window.__warPerformance = this.api;
  }

  record(sample: FrameSample): void {
    if (!this.enabled) return;
    this.samples[this.cursor] = sample;
    this.cursor = (this.cursor + 1) % 18_000;
  }

  dispose(): void {
    if (typeof window !== 'undefined' && window.__warPerformance === this.api) delete window.__warPerformance;
    this.samples = [];
  }
}

declare global {
  interface Window {
    __warPerformance?: { reset(): void; snapshot(): FrameSample[] };
  }
}
