export type RenderResolutionMode = 'auto' | 'native' | 'quality';

export function normalizeRenderResolution(value: unknown): RenderResolutionMode {
  return value === 'native' || value === 'quality' ? value : 'auto';
}

/** Adjust only the 3D drawing buffer. React HUD text stays at display resolution.
 * Long sample windows and slower recovery avoid reallocating buffers every frame. */
export class RenderResolution {
  private mode: RenderResolutionMode = 'auto';
  private deviceRatio = 1;
  private currentScale = 1;
  private warmupMs = 1500;
  private elapsedMs = 0;
  private updateMs = 0;
  private samples = 0;
  private healthyWindows = 0;
  private targetFps = 60;

  get scale(): number { return this.currentScale; }
  get pixelRatio(): number { return this.deviceRatio * this.currentScale; }

  configure(mode: RenderResolutionMode, devicePixelRatio: number): void {
    const ratio = Number.isFinite(devicePixelRatio) ? Math.max(0.5, Math.min(devicePixelRatio, 2)) : 1;
    if (mode === this.mode && ratio === this.deviceRatio) return;
    this.mode = mode;
    this.deviceRatio = ratio;
    this.currentScale = mode === 'native' ? 1 : mode === 'quality' ? 0.75 : Math.min(1, 1.5 / ratio);
    this.resetSamples();
    this.warmupMs = 1500;
  }

  observe(frameMs: number, simulationMs: number, hidden = false, targetFps = 60): void {
    if (this.mode !== 'auto') return;
    if (targetFps !== this.targetFps) {
      this.targetFps = targetFps;
      this.resetSamples();
      this.warmupMs = 1500;
    }
    if (hidden || !Number.isFinite(frameMs) || frameMs <= 0 || frameMs > 250) {
      this.resetSamples();
      this.warmupMs = 1500;
      return;
    }
    if (this.warmupMs > 0) {
      this.warmupMs -= frameMs;
      return;
    }
    this.elapsedMs += frameMs;
    this.updateMs += Math.max(0, simulationMs);
    this.samples++;
    if (this.elapsedMs < 1000 || this.samples < 20) return;
    const mean = this.elapsedMs / this.samples;
    const simulation = this.updateMs / this.samples;
    this.elapsedMs = this.updateMs = this.samples = 0;
    const budget = 1000 / this.targetFps;
    if (mean > budget * 1.17 && simulation < budget * 0.6) {
      this.healthyWindows = 0;
      this.currentScale = Math.max(0.7, Math.round((this.currentScale - 0.05) * 100) / 100);
    } else if (mean <= budget * 1.032) {
      if (++this.healthyWindows >= 5) {
        // A capped frame rate is not evidence of spare GPU time. Keep the
        // balanced mode's high-DPI ceiling instead of spending savings on supersampling.
        const ceiling = this.targetFps === 30 ? Math.min(1, 1.5 / this.deviceRatio) : 1;
        this.currentScale = Math.min(ceiling, Math.round((this.currentScale + 0.05) * 100) / 100);
        this.healthyWindows = 0;
      }
    } else {
      this.healthyWindows = 0;
    }
  }

  private resetSamples(): void {
    this.elapsedMs = this.updateMs = this.samples = this.healthyWindows = 0;
  }
}
