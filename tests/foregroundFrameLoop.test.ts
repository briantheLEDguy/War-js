import { afterEach, describe, expect, test, vi } from 'vitest';
import { ForegroundFrameLoop, normalizeFrameRateLimit } from '../src/game/ForegroundFrameLoop';

function browser() {
  const win = new EventTarget();
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible', hasFocus: () => focused });
  let focused = true;
  let id = 0;
  const pending = new Map<number, FrameRequestCallback>();
  vi.stubGlobal('window', win);
  vi.stubGlobal('document', doc);
  vi.stubGlobal('requestAnimationFrame', (frame: FrameRequestCallback) => { pending.set(++id, frame); return id; });
  vi.stubGlobal('cancelAnimationFrame', (key: number) => pending.delete(key));
  return {
    pending,
    tick(time: number) {
      const frames = [...pending.values()];
      pending.clear();
      for (const frame of frames) frame(time);
    },
    focus(value: boolean) { focused = value; win.dispatchEvent(new Event(value ? 'focus' : 'blur')); },
    visible(value: boolean) { doc.visibilityState = value ? 'visible' : 'hidden'; doc.dispatchEvent(new Event('visibilitychange')); },
  };
}

afterEach(() => vi.unstubAllGlobals());

describe('foreground frame scheduling', () => {
  test.each([60, 120, 144, 165])('caps actual work to 30 FPS on a %i Hz display', hz => {
    const env = browser();
    const render = vi.fn();
    const loop = new ForegroundFrameLoop(render);
    loop.start();
    for (let t = 0; t < 1000; t += 1000 / hz) env.tick(t);
    expect(render.mock.calls.length).toBeGreaterThanOrEqual(29);
    expect(render.mock.calls.length).toBeLessThanOrEqual(31);
    expect(env.pending.size).toBe(1);
    loop.dispose();
    expect(env.pending.size).toBe(0);
  });

  test('blur/hidden cancel pending work and focus resumes without a catch-up delta', () => {
    const env = browser();
    const render = vi.fn();
    const loop = new ForegroundFrameLoop(render);
    loop.start();
    env.tick(100);
    env.focus(false);
    expect(env.pending.size).toBe(0);
    env.tick(60_000);
    expect(render).toHaveBeenCalledOnce();
    env.visible(false);
    env.focus(true);
    expect(env.pending.size).toBe(0);
    env.visible(true);
    env.tick(120_000);
    expect(render).toHaveBeenCalledTimes(2);
    expect(render.mock.calls[1][1]).toBeCloseTo(1000 / 30);
    loop.dispose();
  });

  test('starting while unfocused does no work; repeated start/focus cannot duplicate loops', () => {
    const env = browser();
    env.focus(false);
    const render = vi.fn();
    const loop = new ForegroundFrameLoop(render);
    loop.start();
    loop.start();
    expect(env.pending.size).toBe(0);
    env.focus(true);
    env.focus(true);
    expect(env.pending.size).toBe(1);
    env.tick(100);
    expect(render).toHaveBeenCalledOnce();
    loop.dispose();
    env.focus(true);
    env.visible(true);
    expect(env.pending.size).toBe(0);
  });

  test('live limit changes take effect and stalls never create catch-up bursts', () => {
    const env = browser();
    let limit = 30;
    const render = vi.fn();
    const loop = new ForegroundFrameLoop(render, () => limit);
    loop.start();
    env.tick(0);
    env.tick(16.67);
    expect(render).toHaveBeenCalledOnce();
    limit = 60;
    env.tick(33.34);
    env.tick(50.01);
    expect(render).toHaveBeenCalledTimes(3);
    env.tick(5000);
    expect(render).toHaveBeenCalledTimes(4);
    expect(render.mock.calls[3][1]).toBe(100);
    env.tick(5001);
    expect(render).toHaveBeenCalledTimes(4);
    loop.dispose();
  });

  test('disposing from inside a frame cannot resurrect its animation loop', () => {
    const env = browser();
    const loop = new ForegroundFrameLoop(() => loop.dispose());
    loop.start();
    env.tick(0);
    expect(env.pending.size).toBe(0);
    env.focus(true);
    expect(env.pending.size).toBe(0);
  });

  test('old settings opt into the resource-saving cap and invalid values cannot uncap it', () => {
    expect(normalizeFrameRateLimit(undefined)).toBe(30);
    expect(normalizeFrameRateLimit(144)).toBe(30);
    expect(normalizeFrameRateLimit(60)).toBe(60);
  });
});
