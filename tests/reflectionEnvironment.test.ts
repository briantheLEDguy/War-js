import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { afterEach, describe, expect, test, vi } from 'vitest';
import type { AssetLoader } from '../src/game/AssetLoader';
import { setupPreviewReflections } from '../src/game/PreviewReflections';
import { setupSky } from '../src/world/Skybox';

const renderer = { compile: vi.fn() } as unknown as THREE.WebGLRenderer;

afterEach(() => vi.restoreAllMocks());

describe('outdoor reflection fallback', () => {
  test('missing HDRI captures sky within the cube camera range in every direction', async () => {
    const scene = new THREE.Scene();
    const target = new THREE.WebGLRenderTarget(4, 4);
    const geometryDisposed = vi.fn();
    const materialDisposed = vi.fn();
    const generatorDisposed = vi.spyOn(THREE.PMREMGenerator.prototype, 'dispose');
    const capture = vi.spyOn(THREE.PMREMGenerator.prototype, 'fromScene')
      .mockImplementation((environment, _sigma, near = 0.1, far = 100) => {
        const sky = environment.children[0] as THREE.Mesh<THREE.SphereGeometry, THREE.ShaderMaterial>;
        sky.geometry.addEventListener('dispose', geometryDisposed);
        sky.material.addEventListener('dispose', materialDisposed);
        environment.updateMatrixWorld(true);
        for (const direction of [
          [1, 0, 0], [-1, 0, 0], [0.01, 1, 0.01], [0.01, -1, 0.01], [0, 0, 1], [0, 0, -1], [1, 1, 1],
        ]) {
          const ray = new THREE.Raycaster(new THREE.Vector3(), new THREE.Vector3(...direction).normalize(), near, far);
          expect(ray.intersectObject(sky).length).toBeGreaterThan(0);
        }
        return target;
      });
    const loader = { loadHDRI: vi.fn(async () => null) } as unknown as AssetLoader;

    await setupSky(scene, loader, renderer, 'missing.hdr');

    expect(loader.loadHDRI).toHaveBeenCalledWith('missing.hdr');
    expect(capture).toHaveBeenCalledOnce();
    expect(scene.environment).toBe(target.texture);
    expect(geometryDisposed).toHaveBeenCalledOnce();
    expect(materialDisposed).toHaveBeenCalledOnce();
    expect(generatorDisposed).toHaveBeenCalledOnce();
    target.dispose();
  });

  test('available HDRI remains authoritative and skips fallback capture', async () => {
    const scene = new THREE.Scene();
    const hdri = new THREE.Texture();
    const capture = vi.spyOn(THREE.PMREMGenerator.prototype, 'fromScene');
    const loader = { loadHDRI: vi.fn(async () => hdri) } as unknown as AssetLoader;

    await setupSky(scene, loader, renderer, 'available.hdr');

    expect(scene.environment).toBe(hdri);
    expect(capture).not.toHaveBeenCalled();
    hdri.dispose();
  });
});

describe('character preview reflections', () => {
  test('retains the themed background and owns its reflection target until cleanup', () => {
    const scene = new THREE.Scene();
    const background = new THREE.Color(0x15100d);
    scene.background = background;
    const target = new THREE.WebGLRenderTarget(4, 4);
    const targetDisposed = vi.spyOn(target, 'dispose');
    const roomDisposed = vi.spyOn(RoomEnvironment.prototype, 'dispose');
    const generatorDisposed = vi.spyOn(THREE.PMREMGenerator.prototype, 'dispose');
    const capture = vi.spyOn(THREE.PMREMGenerator.prototype, 'fromScene').mockReturnValue(target);

    const cleanup = setupPreviewReflections(scene, renderer);

    expect(capture.mock.calls[0][0]).toBeInstanceOf(RoomEnvironment);
    expect(scene.environment).toBe(target.texture);
    expect(scene.background).toBe(background);
    expect(roomDisposed).toHaveBeenCalledOnce();
    expect(generatorDisposed).toHaveBeenCalledOnce();
    expect(targetDisposed).not.toHaveBeenCalled();
    cleanup();
    cleanup();
    expect(scene.environment).toBeNull();
    expect(scene.background).toBe(background);
    expect(targetDisposed).toHaveBeenCalledOnce();
  });

  test('old preview cleanup does not clear a replacement environment', () => {
    const scene = new THREE.Scene();
    const target = new THREE.WebGLRenderTarget(4, 4);
    vi.spyOn(THREE.PMREMGenerator.prototype, 'fromScene').mockReturnValue(target);
    const cleanup = setupPreviewReflections(scene, renderer);
    const replacement = new THREE.Texture();
    scene.environment = replacement;
    cleanup();
    expect(scene.environment).toBe(replacement);
    replacement.dispose();
  });

  test('capture failure releases temporary room and generator resources', () => {
    const scene = new THREE.Scene();
    const roomDisposed = vi.spyOn(RoomEnvironment.prototype, 'dispose');
    const generatorDisposed = vi.spyOn(THREE.PMREMGenerator.prototype, 'dispose');
    vi.spyOn(THREE.PMREMGenerator.prototype, 'fromScene').mockImplementation(() => {
      throw new Error('capture failed');
    });

    expect(() => setupPreviewReflections(scene, renderer)).toThrow('capture failed');
    expect(roomDisposed).toHaveBeenCalledOnce();
    expect(generatorDisposed).toHaveBeenCalledOnce();
    expect(scene.environment).toBeNull();
  });
});
