export type FrameRateLimit = 30 | 60;

export function normalizeFrameRateLimit(value: unknown): FrameRateLimit {
  return value === 60 ? 60 : 30;
}

/** Owns one capped animation loop and schedules nothing while the page is
 * hidden or unfocused. Resuming resets delta time instead of catching up. */
export class ForegroundFrameLoop {
  private raf: number | null = null;
  private running = false;
  private lastTime: number | null = null;
  private nextTime = 0;
  private limit = 0;

  constructor(
    private frame: (timeMs: number, deltaMs: number) => void,
    private frameRate: () => number = () => 30,
  ) {}

  start(): void {
    if (this.running) return;
    this.running = true;
    window.addEventListener('focus', this.resume);
    window.addEventListener('blur', this.suspend);
    document.addEventListener('visibilitychange', this.resume);
    this.resume();
  }

  dispose(): void {
    this.running = false;
    this.suspend();
    window.removeEventListener('focus', this.resume);
    window.removeEventListener('blur', this.suspend);
    document.removeEventListener('visibilitychange', this.resume);
  }

  private foreground(): boolean {
    return document.visibilityState === 'visible' && document.hasFocus();
  }

  private suspend = (): void => {
    if (this.raf !== null) cancelAnimationFrame(this.raf);
    this.raf = null;
    this.lastTime = null;
    this.nextTime = 0;
  };

  private resume = (): void => {
    this.suspend();
    if (this.running && this.foreground()) this.raf = requestAnimationFrame(this.tick);
  };

  private tick = (time: number): void => {
    this.raf = null;
    if (!this.running || !this.foreground()) {
      this.suspend();
      return;
    }
    const requested = this.frameRate();
    const limit = Number.isFinite(requested) ? Math.max(1, Math.min(60, requested)) : 30;
    const interval = 1000 / limit;
    if (limit !== this.limit) {
      this.limit = limit;
      this.nextTime = time;
    }
    if (time + 0.5 >= this.nextTime) {
      const delta = this.lastTime === null ? interval : Math.min(100, Math.max(0, time - this.lastTime));
      this.lastTime = time;
      this.nextTime += interval;
      if (this.nextTime <= time) this.nextTime = time + interval;
      try {
        this.frame(time, delta);
      } finally {
        if (this.running && this.foreground() && this.raf === null) this.raf = requestAnimationFrame(this.tick);
      }
    } else {
      this.raf = requestAnimationFrame(this.tick);
    }
  };
}

export function startForegroundLoop(
  frame: (timeMs: number, deltaMs: number) => void,
  frameRate?: () => number,
): () => void {
  const loop = new ForegroundFrameLoop(frame, frameRate);
  loop.start();
  return () => loop.dispose();
}
