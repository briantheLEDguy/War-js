import { afterEach, describe, expect, test } from 'vitest';
import { RenderResolution, normalizeRenderResolution } from '../src/game/RenderResolution';
import { useGameStore } from '../src/state/gameStore';

function frames(controller: RenderResolution, count: number, frameMs = 1000 / 60, simulationMs = 3): void {
  for (let i = 0; i < count; i++) controller.observe(frameMs, simulationMs);
}

afterEach(() => useGameStore.getState().resetSettings());

describe('adaptive 3D resolution', () => {
  test('a deliberate 30 FPS cap does not reduce resolution or restore expensive supersampling', () => {
    const controller = new RenderResolution();
    controller.configure('auto', 2);
    for (let i = 0; i < 600; i++) controller.observe(1000 / 30, 4, false, 30);
    expect(controller.scale).toBe(0.75);
    expect(controller.pixelRatio).toBe(1.5);
    for (let i = 0; i < 150; i++) controller.observe(50, 4, false, 30);
    expect(controller.scale).toBe(0.7);
  });
  test('starts conservatively on high-DPI screens and preserves native/fixed choices', () => {
    const controller = new RenderResolution();
    controller.configure('auto', 2);
    expect(controller.pixelRatio).toBe(1.5);
    controller.configure('native', 3);
    frames(controller, 300, 40);
    expect(controller.pixelRatio).toBe(2);
    controller.configure('quality', 2);
    frames(controller, 300, 40);
    expect(controller.pixelRatio).toBe(1.5);
    controller.configure('native', Number.NaN);
    expect(controller.pixelRatio).toBe(1);
  });

  test('sustained slow rendering reduces resolution in bounded, infrequent steps', () => {
    const controller = new RenderResolution();
    frames(controller, 50, 30);
    expect(controller.scale).toBe(1);
    frames(controller, 34, 30);
    expect(controller.scale).toBe(0.95);
    frames(controller, 25, 30);
    expect(controller.scale).toBe(0.95);
    frames(controller, 600, 30);
    expect(controller.scale).toBe(0.7);
  });

  test('a single hitch, background pause or CPU-bound simulation does not reduce quality', () => {
    const controller = new RenderResolution();
    frames(controller, 100);
    controller.observe(150, 3);
    frames(controller, 60);
    expect(controller.scale).toBe(1);
    controller.observe(2000, 3);
    frames(controller, 40, 30);
    expect(controller.scale).toBe(1);
    controller.observe(40, 3, true);
    frames(controller, 300, 30, 20);
    expect(controller.scale).toBe(1);
  });

  test('restores quality slowly after sustained recovery and resets on display/mode changes', () => {
    const controller = new RenderResolution();
    controller.configure('auto', 2);
    frames(controller, 95);
    frames(controller, 240);
    expect(controller.scale).toBe(0.75);
    frames(controller, 70);
    expect(controller.scale).toBe(0.8);
    controller.configure('native', 1.25);
    expect(controller.pixelRatio).toBe(1.25);
    controller.configure('auto', 1.25);
    expect(controller.scale).toBe(1);
  });

  test('settings normalize old/invalid saves and keep the rendering choice through other edits', () => {
    expect(normalizeRenderResolution(undefined)).toBe('auto');
    expect(normalizeRenderResolution('unknown')).toBe('auto');
    const store = useGameStore.getState();
    store.updateSettings({ renderResolution: 'quality' });
    store.updateSettings({ zoomSensitivity: 2 });
    expect(useGameStore.getState().settings.renderResolution).toBe('quality');
    store.resetSettings();
    expect(useGameStore.getState().settings.renderResolution).toBe('auto');
    expect(useGameStore.getState().settings.frameRateLimit).toBe(30);
  });
});
