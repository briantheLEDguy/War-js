import * as THREE from 'three';
import { ResourceDisposer } from './ResourceDisposer';

/** Share decoded external images across GLB parsers, without a global cache.
 * Texture clones share their Source but keep independent samplers and UV transforms. */
export class SharedTextureLoader extends THREE.TextureLoader {
  private cache = new Map<string, Promise<THREE.Texture>>();
  private disposed = false;

  constructor(manager: THREE.LoadingManager, private resources: ResourceDisposer) {
    super(manager);
  }

  override load(
    url: string,
    onLoad?: (texture: THREE.Texture) => void,
    _onProgress?: (event: ProgressEvent) => void,
    onError?: (err: unknown) => void,
  ): THREE.Texture {
    const result = new THREE.Texture();
    if (this.disposed) {
      queueMicrotask(() => onError?.(new Error('Asset loader disposed')));
      return result;
    }
    let pending = this.cache.get(url);
    if (!pending) {
      pending = new Promise<THREE.Texture>((resolve, reject) => {
        super.load(url, resolve, undefined, reject);
      });
      this.cache.set(url, pending);
      void pending.then(texture => {
        if (this.disposed) this.resources.texture(texture);
      }, () => { this.cache.delete(url); });
    }
    void pending.then(texture => {
      if (this.disposed) throw new Error('Asset loader disposed');
      result.copy(texture);
      result.needsUpdate = true;
      onLoad?.(result);
    }).catch(error => onError?.(error));
    return result;
  }

  dispose(): void {
    this.disposed = true;
    for (const pending of this.cache.values()) {
      void pending.then(texture => this.resources.texture(texture), () => {});
    }
    this.cache.clear();
  }
}
