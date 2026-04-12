import * as THREE from 'three';
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js';
import { useGameStore } from '../state/gameStore';

export type PrimitiveFactory = () => THREE.Object3D;

/**
 * Asset loader with primitive fallbacks. If a file is missing or fails to load,
 * the fallback is returned and a counter in the debug overlay increments.
 *
 * Phase 2 note: when the WAR asset pipeline lands, converted .glb files drop
 * into /public/assets/models/ using the same names referenced here, no code
 * change required.
 */
export class AssetLoader {
  private gltfLoader = new GLTFLoader();
  private texLoader = new THREE.TextureLoader();
  private rgbeLoader = new RGBELoader();
  private modelCache = new Map<string, Promise<THREE.Object3D>>();
  private texCache = new Map<string, Promise<THREE.Texture>>();

  async loadModel(path: string, fallback: PrimitiveFactory): Promise<THREE.Object3D> {
    const cached = this.modelCache.get(path);
    if (cached) {
      const obj = await cached;
      return obj.clone(true);
    }
    const promise = this.gltfLoader
      .loadAsync(`/assets/models/${path}`)
      .then((g: GLTF) => {
        const scene = g.scene;
        scene.traverse((n) => {
          if ((n as THREE.Mesh).isMesh) {
            n.castShadow = true;
            n.receiveShadow = true;
          }
        });
        return scene as THREE.Object3D;
      })
      .catch((err) => {
        console.warn(`[AssetLoader] model fallback for ${path}:`, err.message);
        useGameStore.getState().incAssetFallbacks();
        return fallback();
      });
    this.modelCache.set(path, promise);
    const base = await promise;
    return base.clone(true);
  }

  async loadTexture(path: string, fallbackColor = 0x555555): Promise<THREE.Texture | null> {
    const cached = this.texCache.get(path);
    if (cached) return cached;
    const promise = this.texLoader
      .loadAsync(`/assets/textures/${path}`)
      .then((t) => {
        t.wrapS = t.wrapT = THREE.RepeatWrapping;
        t.colorSpace = THREE.SRGBColorSpace;
        return t;
      })
      .catch((err) => {
        console.warn(`[AssetLoader] texture fallback for ${path}:`, err.message);
        useGameStore.getState().incAssetFallbacks();
        // Return a 1x1 fallback texture of the requested color
        const data = new Uint8Array([
          (fallbackColor >> 16) & 0xff,
          (fallbackColor >> 8) & 0xff,
          fallbackColor & 0xff,
          255,
        ]);
        const tex = new THREE.DataTexture(data, 1, 1, THREE.RGBAFormat);
        tex.needsUpdate = true;
        tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
        return tex;
      });
    this.texCache.set(path, promise);
    return promise;
  }

  async loadHDRI(path: string): Promise<THREE.Texture | null> {
    try {
      const tex = await this.rgbeLoader.loadAsync(`/assets/hdri/${path}`);
      tex.mapping = THREE.EquirectangularReflectionMapping;
      return tex;
    } catch (err) {
      console.warn(`[AssetLoader] HDRI fallback for ${path}:`, (err as Error).message);
      useGameStore.getState().incAssetFallbacks();
      return null;
    }
  }

  /** Common primitive fallbacks. */
  static primitives = {
    humanoid(color = 0x7a6425): THREE.Object3D {
      const group = new THREE.Group();
      const bodyMat = new THREE.MeshStandardMaterial({ color });
      const skinMat = new THREE.MeshStandardMaterial({ color: 0xe6c29a });
      const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.35, 0.9, 4, 8), bodyMat);
      body.position.y = 0.95;
      body.castShadow = true;
      group.add(body);
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 12), skinMat);
      head.position.y = 1.75;
      head.castShadow = true;
      group.add(head);
      // forward indicator (nose)
      const nose = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.12, 8), skinMat);
      nose.rotation.x = Math.PI / 2;
      nose.position.set(0, 1.75, 0.22);
      group.add(nose);
      return group;
    },
    dummy(): THREE.Object3D {
      const group = new THREE.Group();
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x6b4a25 });
      const strawMat = new THREE.MeshStandardMaterial({ color: 0xbda44a });
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 1.6, 10), woodMat);
      pole.position.y = 0.8;
      pole.castShadow = true;
      group.add(pole);
      const body = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.4, 0.9, 12), strawMat);
      body.position.y = 1.25;
      body.castShadow = true;
      group.add(body);
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.25, 10, 10), strawMat);
      head.position.y = 1.85;
      head.castShadow = true;
      group.add(head);
      return group;
    },
    tree(): THREE.Object3D {
      const group = new THREE.Group();
      const trunkMat = new THREE.MeshStandardMaterial({ color: 0x4a2f15 });
      const leafMat = new THREE.MeshStandardMaterial({ color: 0x2f5a25 });
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.3, 1.8, 8), trunkMat);
      trunk.position.y = 0.9;
      trunk.castShadow = true;
      group.add(trunk);
      const leaves = new THREE.Mesh(new THREE.ConeGeometry(1.2, 2.6, 10), leafMat);
      leaves.position.y = 2.5;
      leaves.castShadow = true;
      group.add(leaves);
      return group;
    },
    rock(): THREE.Object3D {
      const mat = new THREE.MeshStandardMaterial({ color: 0x6a6a66, flatShading: true });
      const geo = new THREE.DodecahedronGeometry(0.7, 0);
      const m = new THREE.Mesh(geo, mat);
      m.castShadow = true;
      m.position.y = 0.5;
      m.scale.set(1, 0.7 + Math.random() * 0.4, 1);
      m.rotation.y = Math.random() * Math.PI * 2;
      return m;
    },
    building(): THREE.Object3D {
      const group = new THREE.Group();
      const wallMat = new THREE.MeshStandardMaterial({ color: 0xa89270 });
      const roofMat = new THREE.MeshStandardMaterial({ color: 0x6a2815 });
      const base = new THREE.Mesh(new THREE.BoxGeometry(4, 2.5, 3), wallMat);
      base.position.y = 1.25;
      base.castShadow = true;
      base.receiveShadow = true;
      group.add(base);
      const roof = new THREE.Mesh(
        new THREE.ConeGeometry(3, 1.6, 4),
        roofMat,
      );
      roof.rotation.y = Math.PI / 4;
      roof.position.y = 3.3;
      roof.scale.set(1.1, 1, 0.85);
      roof.castShadow = true;
      group.add(roof);
      return group;
    },
  };
}
