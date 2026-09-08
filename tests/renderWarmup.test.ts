import * as THREE from 'three';
import { expect, test, vi } from 'vitest';
import { warmScene } from '../src/game/RenderWarmup';

test('uploads shared textures once and restores room visibility/render target after warmup failure', async () => {
  const texture = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
  const material = new THREE.MeshBasicMaterial({ map: texture });
  const scene = new THREE.Scene();
  const room = new THREE.Group(); room.visible = false;
  room.add(new THREE.Mesh(new THREE.SphereGeometry(), material));
  scene.add(room, new THREE.Mesh(new THREE.SphereGeometry(), material));
  const previous = new THREE.WebGLRenderTarget(1, 1);
  const renderer = { initTexture: vi.fn(), compile: vi.fn(() => new Set()),
    getRenderTarget: () => previous, setRenderTarget: vi.fn(), render: vi.fn().mockImplementationOnce(() => {}).mockImplementationOnce(() => { throw new Error('test'); }) };
  await expect(warmScene(renderer as unknown as THREE.WebGLRenderer, scene, new THREE.PerspectiveCamera(), () => false, [room])).rejects.toThrow('test');
  expect(renderer.initTexture).toHaveBeenCalledTimes(1);
  expect(room.visible).toBe(false);
  expect(renderer.setRenderTarget).toHaveBeenLastCalledWith(previous);
});

test('disposal during asynchronous compilation prevents rendering', async () => {
  vi.useFakeTimers();
  let cancelled = false;
  const properties = { get: vi.fn(() => ({ currentProgram: { isReady: () => false } })) };
  const renderer = { getRenderTarget: () => null, setRenderTarget: vi.fn(), render: vi.fn(),
    compile: vi.fn(() => new Set([new THREE.MeshBasicMaterial()])), properties };
  try {
    const pending = warmScene(renderer as unknown as THREE.WebGLRenderer, new THREE.Scene(), new THREE.PerspectiveCamera(), () => cancelled);
    expect(properties.get).toHaveBeenCalledOnce();
    cancelled = true;
    properties.get.mockImplementation(() => { throw new Error('renderer already disposed'); });
    await vi.advanceTimersByTimeAsync(10); await pending;
    expect(renderer.render).not.toHaveBeenCalled();
    expect(renderer.setRenderTarget).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  } finally { vi.useRealTimers(); }
});
