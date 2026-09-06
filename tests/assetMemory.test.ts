import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { AssetLoader } from '../src/game/AssetLoader';
import { SharedTextureLoader } from '../src/game/SharedTextureLoader';
import { ResourceDisposer } from '../src/game/ResourceDisposer';

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('decoded texture ownership', () => {
  test('deduplicates pending and completed image loads while keeping texture settings independent', async () => {
    let complete!: (texture: THREE.Texture) => void;
    const decode = vi.spyOn(THREE.TextureLoader.prototype, 'load').mockImplementation((_url, onLoad) => {
      complete = onLoad!;
      return new THREE.Texture();
    });
    const loader = new SharedTextureLoader(new THREE.LoadingManager(), new ResourceDisposer());
    const first = loader.loadAsync('brick.png');
    const second = loader.loadAsync('brick.png');
    const source = new THREE.Texture({ width: 2048, height: 2048 });
    complete(source);
    const [a, b, c] = await Promise.all([first, second, loader.loadAsync('brick.png')]);
    expect(decode).toHaveBeenCalledOnce();
    expect(a).not.toBe(b);
    expect(a.source).toBe(b.source);
    expect(c.source).toBe(a.source);
    a.colorSpace = THREE.SRGBColorSpace;
    a.wrapS = THREE.RepeatWrapping;
    a.offset.x = 0.5;
    expect(b.colorSpace).toBe(THREE.NoColorSpace);
    expect(b.wrapS).toBe(THREE.ClampToEdgeWrapping);
    expect(b.offset.x).toBe(0);
    loader.dispose();
  });

  test('does not share image ownership between scenes and releases late arrivals', async () => {
    const completions: Array<(texture: THREE.Texture) => void> = [];
    vi.spyOn(THREE.TextureLoader.prototype, 'load').mockImplementation((_url, onLoad) => {
      completions.push(onLoad!);
      return new THREE.Texture();
    });
    const first = new SharedTextureLoader(new THREE.LoadingManager(), new ResourceDisposer());
    const second = new SharedTextureLoader(new THREE.LoadingManager(), new ResourceDisposer());
    const a = first.loadAsync('brick.png');
    const b = second.loadAsync('brick.png');
    const rejected = expect(a).rejects.toThrow('disposed');
    first.dispose();
    const oldTexture = new THREE.Texture({ close: vi.fn() });
    const disposed = vi.spyOn(oldTexture, 'dispose');
    completions[0](oldTexture);
    completions[1](new THREE.Texture());
    await rejected;
    await expect(b).resolves.toBeInstanceOf(THREE.Texture);
    expect(disposed).toHaveBeenCalledOnce();
    expect(oldTexture.image.close).toHaveBeenCalledOnce();
    second.dispose();
  });

  test('failed image loads can retry', async () => {
    const decode = vi.spyOn(THREE.TextureLoader.prototype, 'load')
      .mockImplementationOnce((_url, _load, _progress, error) => {
        error!(new Error('missing'));
        return new THREE.Texture();
      }).mockImplementationOnce((_url, load) => {
        const texture = new THREE.Texture();
        load!(texture);
        return texture;
      });
    const loader = new SharedTextureLoader(new THREE.LoadingManager(), new ResourceDisposer());
    await expect(loader.loadAsync('brick.png')).rejects.toThrow('missing');
    await expect(loader.loadAsync('brick.png')).resolves.toBeInstanceOf(THREE.Texture);
    expect(decode).toHaveBeenCalledTimes(2);
    loader.dispose();
  });
});

describe('model ownership', () => {
  test('static and animated requests share one parse, preserving independent skeletons', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 200 })));
    const root = new THREE.Group();
    const mesh = new THREE.SkinnedMesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial());
    const bone = new THREE.Bone();
    mesh.add(bone);
    mesh.bind(new THREE.Skeleton([bone]));
    root.add(mesh);
    const clip = new THREE.AnimationClip('idle', 1, []);
    const parse = vi.spyOn(GLTFLoader.prototype, 'loadAsync').mockResolvedValue({ scene: root, animations: [clip] } as never);
    const loader = new AssetLoader();
    const [a, b] = await Promise.all([
      loader.loadModel('actor.glb', () => new THREE.Group()),
      loader.loadModelWithAnimations('actor.glb', () => new THREE.Group()),
    ]);
    expect(parse).toHaveBeenCalledOnce();
    expect(b.animations).toEqual([clip]);
    const first = a.children[0] as THREE.SkinnedMesh;
    const second = b.object.children[0] as THREE.SkinnedMesh;
    expect(first.geometry).toBe(second.geometry);
    expect(first.skeleton).not.toBe(second.skeleton);
    expect(first.skeleton.bones[0]).not.toBe(second.skeleton.bones[0]);
    loader.dispose(a, b.object);
  });

  test('a model resolving after teardown is disposed and never returned to the caller', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 200 })));
    let finish!: (value: never) => void;
    const parse = vi.spyOn(GLTFLoader.prototype, 'loadAsync').mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    const loader = new AssetLoader();
    const loading = loader.loadModel('late.glb', () => new THREE.Group());
    await vi.waitFor(() => expect(parse).toHaveBeenCalledOnce());
    const rejected = expect(loading).rejects.toThrow('disposed');
    loader.dispose();
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial());
    const disposeGeometry = vi.spyOn(mesh.geometry, 'dispose');
    const disposeMaterial = vi.spyOn(mesh.material, 'dispose');
    finish({ scene: mesh, animations: [] } as never);
    await rejected;
    expect(disposeGeometry).toHaveBeenCalledOnce();
    expect(disposeMaterial).toHaveBeenCalledOnce();
  });

  test('terminal cleanup deduplicates shared geometry, textures and image bitmaps', () => {
    const resources = new ResourceDisposer();
    const image = { close: vi.fn() };
    const texture = new THREE.Texture(image);
    const material = new THREE.MeshStandardMaterial({ map: texture, normalMap: texture.clone() });
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(), material);
    const scene = new THREE.Scene();
    scene.add(mesh, mesh.clone());
    scene.environment = texture;
    const geometryDisposed = vi.spyOn(mesh.geometry, 'dispose');
    const materialDisposed = vi.spyOn(material, 'dispose');
    const textureDisposed = vi.spyOn(texture, 'dispose');
    resources.object(scene);
    resources.object(scene);
    expect(geometryDisposed).toHaveBeenCalledOnce();
    expect(materialDisposed).toHaveBeenCalledOnce();
    expect(textureDisposed).toHaveBeenCalledOnce();
    expect(image.close).toHaveBeenCalledOnce();
    expect(scene.environment).toBeNull();
  });
});
