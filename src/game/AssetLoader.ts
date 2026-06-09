import * as THREE from 'three';
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js';
import { clone as cloneSkeleton } from 'three/examples/jsm/utils/SkeletonUtils.js';
import { useGameStore } from '../state/gameStore';
import { buildCharacterMesh } from './CharacterMeshes';

export type PrimitiveFactory = () => THREE.Object3D;

interface IndexedModel {
  assetId: string;
  model: string;
  bodyModel?: string;
  runtimeReady?: boolean;
  reviewStatus?: string;
  bodyFamily?: string;
  skeletonId?: string;
  skinned?: boolean;
  coveredRegions?: string[];
}

interface AssetIndex {
  schemaVersion: number;
  assetVersion?: string;
  characterProfiles?: Record<string, IndexedModel>;
  baseBodies?: Record<string, IndexedModel>;
  equipment?: Record<string, IndexedModel>;
  staticProps?: Record<string, IndexedModel>;
}

export interface EquipmentAssetResolution {
  model: string;
  bodyModel: string | null;
  disabled?: boolean;
  bodyFamily?: string;
  skeletonId?: string;
  skinned?: boolean;
  coveredRegions?: string[];
}

const BASE = import.meta.env.BASE_URL; // '/' in dev, '/War-js/' on GH Pages
const PUBLIC_ASSET_VERSION = import.meta.env.VITE_ASSET_VERSION ?? '2026-06-09-playable-modular-roster';
const MODEL_ASSET_TOKEN = import.meta.env.DEV
  ? `${PUBLIC_ASSET_VERSION}-${Date.now()}`
  : PUBLIC_ASSET_VERSION;

function modelUrl(path: string): string {
  return `${BASE}assets/models/${path}?v=${encodeURIComponent(MODEL_ASSET_TOKEN)}`;
}

function prepareLoadedModel(root: THREE.Object3D): void {
  root.traverse((n) => {
    if (!(n as THREE.Mesh).isMesh) return;

    const mesh = n as THREE.Mesh;
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    if ((mesh as THREE.SkinnedMesh).isSkinnedMesh) {
      mesh.frustumCulled = false;

      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const material of materials) {
        if (!material) continue;
        material.side = THREE.DoubleSide;
        material.needsUpdate = true;
      }
    }
  });
}

/**
 * Asset loader with primitive fallbacks. If a file is missing or fails to load,
 * the fallback is returned and a counter in the debug overlay increments.
 *
 * Manifest-backed .glb files are resolved through asset-index.json. If an
 * indexed entry is blocked by QC/runtime review, the loader keeps the primitive
 * fallback path instead of mounting the authored file.
 */
export class AssetLoader {
  private gltfLoader = new GLTFLoader();
  private texLoader = new THREE.TextureLoader();
  private rgbeLoader = new RGBELoader();
  private modelCache = new Map<string, Promise<THREE.Object3D>>();
  private animCache  = new Map<string, Promise<THREE.AnimationClip[]>>();
  private texCache = new Map<string, Promise<THREE.Texture>>();
  private assetProbeCache = new Map<string, Promise<boolean>>();
  private assetIndex: Promise<AssetIndex | null> | null = null;

  private async loadAssetIndex(): Promise<AssetIndex | null> {
    if (this.assetIndex) return this.assetIndex;
    const url = `${BASE}assets/models/asset-index.json?v=${encodeURIComponent(MODEL_ASSET_TOKEN)}`;
    this.assetIndex = fetch(url, { cache: import.meta.env.DEV ? 'no-store' : 'default' })
      .then((res) => (res.ok ? res.json() as Promise<AssetIndex> : null))
      .catch((err) => {
        console.warn('[AssetLoader] asset-index fallback:', err.message);
        return null;
      });
    return this.assetIndex;
  }

  async resolveCharacterModel(profileKey: string): Promise<string | null> {
    const index = await this.loadAssetIndex();
    return index?.characterProfiles?.[profileKey]?.model ?? null;
  }

  async resolveEquipmentModel(
    itemKey: string,
    fallbackModel: string,
  ): Promise<EquipmentAssetResolution> {
    const index = await this.loadAssetIndex();
    const entry = index?.equipment?.[itemKey];
    if (entry?.runtimeReady === false) {
      return { model: fallbackModel, bodyModel: null, disabled: true };
    }
    return {
      model: entry?.model ?? fallbackModel,
      bodyModel: entry?.bodyModel ?? null,
      bodyFamily: entry?.bodyFamily,
      skeletonId: entry?.skeletonId,
      skinned: entry?.skinned,
      coveredRegions: entry?.coveredRegions,
    };
  }

  async resolveEquipmentBaseBodyModel(itemKeys: string[]): Promise<string | null> {
    const index = await this.loadAssetIndex();
    for (const key of itemKeys) {
      const entry = index?.equipment?.[key];
      if (entry?.runtimeReady === false) continue;
      const bodyModel = entry?.bodyModel;
      if (bodyModel) return bodyModel;
    }
    return null;
  }

  async resolveStaticModel(staticKey: string, fallbackModel: string): Promise<string> {
    const index = await this.loadAssetIndex();
    return index?.staticProps?.[staticKey]?.model ?? fallbackModel;
  }

  private async canLoadAsset(url: string, expectedType?: 'image'): Promise<boolean> {
    const cached = this.assetProbeCache.get(url);
    if (cached) return cached;
    const probe = fetch(url, {
      method: 'HEAD',
      cache: import.meta.env.DEV ? 'no-store' : 'default',
    })
      .then((res) => {
        if (!res.ok) return false;
        const contentType = res.headers.get('content-type')?.toLowerCase() ?? '';
        if (contentType.includes('text/html')) return false;
        if (expectedType === 'image' && contentType && !contentType.startsWith('image/')) {
          return false;
        }
        return true;
      })
      .catch(() => false);
    this.assetProbeCache.set(url, probe);
    return probe;
  }

  async loadModel(path: string, fallback: PrimitiveFactory): Promise<THREE.Object3D> {
    const cached = this.modelCache.get(path);
    if (cached) {
      const obj = await cached;
      return cloneSkeleton(obj);
    }
    const url = modelUrl(path);
    const safePromise = this.canLoadAsset(url).then((canLoad) => {
      if (!canLoad) {
        console.warn(`[AssetLoader] model fallback for ${path}: asset missing`);
        useGameStore.getState().incAssetFallbacks();
        return fallback();
      }
      return this.gltfLoader
        .loadAsync(url)
        .then((g: GLTF) => {
          prepareLoadedModel(g.scene);
          return g.scene as THREE.Object3D;
        })
        .catch((err) => {
          console.warn(`[AssetLoader] model fallback for ${path}:`, err.message);
          useGameStore.getState().incAssetFallbacks();
          return fallback();
        });
    });
    this.modelCache.set(path, safePromise);
    const base = await safePromise;
    return cloneSkeleton(base);
  }

  async loadModelWithAnimations(
    path: string,
    fallback: PrimitiveFactory,
  ): Promise<{ object: THREE.Object3D; animations: THREE.AnimationClip[] }> {
    const url = modelUrl(path);
    const canLoad = await this.canLoadAsset(url);
    if (!canLoad) {
      console.warn(`[AssetLoader] model fallback for ${path}: asset missing`);
      useGameStore.getState().incAssetFallbacks();
      return { object: fallback(), animations: [] };
    }

    if (!this.animCache.has(path)) {
      const p = this.gltfLoader
        .loadAsync(url)
        .then((g: GLTF) => {
          prepareLoadedModel(g.scene);
          if (!this.modelCache.has(path)) {
            this.modelCache.set(path, Promise.resolve(g.scene));
          }
          return g.animations ?? [];
        })
        .catch((err) => {
          console.warn(`[AssetLoader] loadModelWithAnimations fallback for ${path}:`, err.message);
          useGameStore.getState().incAssetFallbacks();
          return [] as THREE.AnimationClip[];
        });
      this.animCache.set(path, p);
    }

    const animations = await this.animCache.get(path)!;
    const object = await this.loadModel(path, fallback);
    return { object, animations };
  }

  /**
   * Like loadModel but also returns any AnimationClip[] embedded in the GLB.
   * Used by Player when career-specific rigged models are available.
   *
   * Probe order: primaryPath → raceFallbackPath (optional) → fallback()
   */
  async loadModelFull(
    primaryPath: string,
    fallback: PrimitiveFactory,
    raceFallbackPath?: string,
  ): Promise<{ object: THREE.Object3D; animations: THREE.AnimationClip[] }> {
    const primaryUrl = modelUrl(primaryPath);
    const canLoadPrimary = await this.canLoadAsset(primaryUrl);

    // If career-specific model missing, try the race-level GLB (no animations expected)
    if (!canLoadPrimary && raceFallbackPath) {
      const object = await this.loadModel(raceFallbackPath, fallback);
      return { object, animations: [] };
    }

    if (!canLoadPrimary) {
      useGameStore.getState().incAssetFallbacks();
      return { object: fallback(), animations: [] };
    }

    if (!this.animCache.has(primaryPath)) {
      const p = this.gltfLoader
        .loadAsync(primaryUrl)
        .then((g: GLTF) => {
          prepareLoadedModel(g.scene);
          if (!this.modelCache.has(primaryPath)) {
            this.modelCache.set(primaryPath, Promise.resolve(g.scene));
          }
          return g.animations ?? [];
        })
        .catch((err) => {
          console.warn(`[AssetLoader] loadModelFull fallback for ${primaryPath}:`, err.message);
          useGameStore.getState().incAssetFallbacks();
          return [] as THREE.AnimationClip[];
        });
      this.animCache.set(primaryPath, p);
    }

    const animations = await this.animCache.get(primaryPath)!;
    const object = await this.loadModel(primaryPath, fallback);
    return { object, animations };
  }

  async loadTexture(path: string, fallbackColor = 0x555555): Promise<THREE.Texture | null> {
    const cached = this.texCache.get(path);
    if (cached) return cached;
    const url = `${BASE}assets/textures/${path}`;
    const safePromise = this.canLoadAsset(url, 'image').then((canLoad) => {
      if (!canLoad) {
        console.warn(`[AssetLoader] texture fallback for ${path}: asset missing`);
        useGameStore.getState().incAssetFallbacks();
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
      }
      return this.texLoader
        .loadAsync(url)
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
    });
    this.texCache.set(path, safePromise);
    return safePromise;
  }

  async loadHDRI(path: string): Promise<THREE.Texture | null> {
    const url = `${BASE}assets/hdri/${path}`;
    const canLoad = await this.canLoadAsset(url);
    if (!canLoad) {
      console.warn(`[AssetLoader] HDRI fallback for ${path}: asset missing`);
      useGameStore.getState().incAssetFallbacks();
      return null;
    }
    try {
      const tex = await this.rgbeLoader.loadAsync(url);
      tex.mapping = THREE.EquirectangularReflectionMapping;
      return tex;
    } catch (err) {
      console.warn(`[AssetLoader] HDRI fallback for ${path}:`, (err as Error).message);
      useGameStore.getState().incAssetFallbacks();
      return null;
    }
  }

  /** Common primitive fallbacks — enhanced visuals. */
  static primitives = {
    humanoid(color = 0x7a6425): THREE.Object3D {
      const group = new THREE.Group();
      const bodyMat = new THREE.MeshStandardMaterial({ color, roughness: 0.8 });
      const skinMat = new THREE.MeshStandardMaterial({ color: 0xe0b890, roughness: 0.7 });
      const bootMat = new THREE.MeshStandardMaterial({ color: 0x3a2a18, roughness: 0.9 });

      // Boots
      for (const side of [-0.15, 0.15]) {
        const boot = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.14, 0.45, 8), bootMat);
        boot.position.set(side, 0.22, 0);
        boot.castShadow = true;
        group.add(boot);
      }
      // Legs
      for (const side of [-0.15, 0.15]) {
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.12, 0.5, 8), bodyMat);
        leg.position.set(side, 0.55, 0);
        leg.castShadow = true;
        group.add(leg);
      }
      // Torso
      const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.32, 0.7, 4, 8), bodyMat);
      body.position.y = 1.05;
      body.castShadow = true;
      group.add(body);
      // Shoulders
      const shoulderMat = new THREE.MeshStandardMaterial({ color, roughness: 0.7 });
      for (const side of [-0.42, 0.42]) {
        const shoulder = new THREE.Mesh(new THREE.SphereGeometry(0.14, 8, 8), shoulderMat);
        shoulder.position.set(side, 1.35, 0);
        shoulder.castShadow = true;
        group.add(shoulder);
      }
      // Head
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.2, 12, 12), skinMat);
      head.position.y = 1.65;
      head.castShadow = true;
      group.add(head);
      // forward indicator (nose)
      const nose = new THREE.Mesh(new THREE.ConeGeometry(0.05, 0.1, 8), skinMat);
      nose.rotation.x = Math.PI / 2;
      nose.position.set(0, 1.65, 0.2);
      group.add(nose);
      return group;
    },
    dummy(): THREE.Object3D {
      const group = new THREE.Group();
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x5a3a18, roughness: 0.9 });
      const strawMat = new THREE.MeshStandardMaterial({ color: 0xbda44a, roughness: 0.85 });
      const metalMat = new THREE.MeshStandardMaterial({ color: 0x6a6a6a, metalness: 0.4, roughness: 0.6 });
      // Base
      const base = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.5, 0.15, 12), woodMat);
      base.position.y = 0.07;
      base.castShadow = true;
      group.add(base);
      // Pole
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 1.6, 10), woodMat);
      pole.position.y = 0.87;
      pole.castShadow = true;
      group.add(pole);
      // Cross-arm
      const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.2, 6), woodMat);
      arm.rotation.z = Math.PI / 2;
      arm.position.set(0, 1.3, 0);
      arm.castShadow = true;
      group.add(arm);
      // Body
      const body = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.35, 0.8, 12), strawMat);
      body.position.y = 1.25;
      body.castShadow = true;
      group.add(body);
      // Head
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.22, 10, 10), strawMat);
      head.position.y = 1.82;
      head.castShadow = true;
      group.add(head);
      // Helmet
      const helmet = new THREE.Mesh(new THREE.SphereGeometry(0.24, 10, 5, 0, Math.PI * 2, 0, Math.PI * 0.6), metalMat);
      helmet.position.y = 1.88;
      helmet.castShadow = true;
      group.add(helmet);
      return group;
    },
    tree(): THREE.Object3D {
      const group = new THREE.Group();
      const trunkMat = new THREE.MeshStandardMaterial({ color: 0x3a2210, roughness: 0.95 });
      const leafMat = new THREE.MeshStandardMaterial({ color: 0x2a4a1a, roughness: 0.9 });
      const leafMat2 = new THREE.MeshStandardMaterial({ color: 0x1e3a14, roughness: 0.9 });
      // Trunk with slight taper
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.35, 2.2, 8), trunkMat);
      trunk.position.y = 1.1;
      trunk.castShadow = true;
      group.add(trunk);
      // Root bulge
      const roots = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.5, 0.4, 8), trunkMat);
      roots.position.y = 0.2;
      group.add(roots);
      // Multiple leaf layers for fuller canopy
      const leaves1 = new THREE.Mesh(new THREE.ConeGeometry(1.6, 2.0, 10), leafMat);
      leaves1.position.y = 2.6;
      leaves1.castShadow = true;
      group.add(leaves1);
      const leaves2 = new THREE.Mesh(new THREE.ConeGeometry(1.2, 1.8, 10), leafMat2);
      leaves2.position.y = 3.5;
      leaves2.castShadow = true;
      group.add(leaves2);
      const leaves3 = new THREE.Mesh(new THREE.ConeGeometry(0.7, 1.2, 8), leafMat);
      leaves3.position.y = 4.2;
      leaves3.castShadow = true;
      group.add(leaves3);
      return group;
    },
    rock(): THREE.Object3D {
      const mat = new THREE.MeshStandardMaterial({
        color: 0x5a5a56,
        flatShading: true,
        roughness: 0.95,
      });
      const geo = new THREE.DodecahedronGeometry(0.7, 0);
      // Slightly deform vertices for more natural look
      const pos = geo.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const y = pos.getY(i);
        if (y < 0) pos.setY(i, y * 0.5); // Flatten bottom
      }
      geo.computeVertexNormals();
      const m = new THREE.Mesh(geo, mat);
      m.castShadow = true;
      m.position.y = 0.35;
      m.scale.set(1, 0.6 + Math.random() * 0.4, 1);
      m.rotation.y = Math.random() * Math.PI * 2;
      return m;
    },
    pnw_douglas_fir(): THREE.Object3D {
      const group = new THREE.Group();
      const trunkMat = new THREE.MeshStandardMaterial({ color: 0x4a2b16, roughness: 0.95 });
      const barkDarkMat = new THREE.MeshStandardMaterial({ color: 0x2c1a0f, roughness: 0.98 });
      const needleMat = new THREE.MeshStandardMaterial({ color: 0x1c3f2a, roughness: 0.92 });
      const needleDarkMat = new THREE.MeshStandardMaterial({ color: 0x102a1d, roughness: 0.96 });

      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.38, 5.8, 10), trunkMat);
      trunk.position.y = 2.9;
      trunk.castShadow = true;
      group.add(trunk);

      for (const x of [-0.18, 0.18]) {
        const furrow = new THREE.Mesh(new THREE.BoxGeometry(0.05, 4.8, 0.04), barkDarkMat);
        furrow.position.set(x, 2.8, 0.36);
        group.add(furrow);
      }

      const layers = [
        { radius: 1.75, height: 1.15, y: 2.25, mat: needleDarkMat },
        { radius: 1.55, height: 1.1, y: 3.0, mat: needleMat },
        { radius: 1.28, height: 1.0, y: 3.75, mat: needleDarkMat },
        { radius: 1.0, height: 0.95, y: 4.45, mat: needleMat },
        { radius: 0.72, height: 0.9, y: 5.05, mat: needleDarkMat },
        { radius: 0.42, height: 0.7, y: 5.62, mat: needleMat },
      ];
      for (const [index, layer] of layers.entries()) {
        const needles = new THREE.Mesh(new THREE.ConeGeometry(layer.radius, layer.height, 11), layer.mat);
        needles.position.y = layer.y;
        needles.rotation.y = index * 0.45;
        needles.scale.z = 0.86;
        needles.castShadow = true;
        group.add(needles);
      }

      return group;
    },
    pnw_western_red_cedar(): THREE.Object3D {
      const group = new THREE.Group();
      const trunkMat = new THREE.MeshStandardMaterial({ color: 0x5a3219, roughness: 0.96 });
      const rootMat = new THREE.MeshStandardMaterial({ color: 0x3f2415, roughness: 0.98 });
      const frondMat = new THREE.MeshStandardMaterial({
        color: 0x244d2f,
        roughness: 0.94,
        side: THREE.DoubleSide,
      });
      const deepFrondMat = new THREE.MeshStandardMaterial({
        color: 0x183822,
        roughness: 0.96,
        side: THREE.DoubleSide,
      });

      const flare = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.85, 0.55, 10), rootMat);
      flare.position.y = 0.28;
      flare.castShadow = true;
      group.add(flare);

      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.48, 5.0, 10), trunkMat);
      trunk.position.y = 2.65;
      trunk.castShadow = true;
      group.add(trunk);

      for (let i = 0; i < 6; i++) {
        const radius = 1.55 - i * 0.18;
        const branch = new THREE.Mesh(
          new THREE.ConeGeometry(radius, 1.05, 9),
          i % 2 === 0 ? frondMat : deepFrondMat,
        );
        branch.position.y = 2.15 + i * 0.56;
        branch.rotation.y = i * 0.72;
        branch.scale.set(1.15, 1, 0.72);
        branch.castShadow = true;
        group.add(branch);
      }

      for (let i = 0; i < 10; i++) {
        const angle = (i / 10) * Math.PI * 2;
        const frond = new THREE.Mesh(new THREE.PlaneGeometry(0.38, 1.05), i % 2 === 0 ? frondMat : deepFrondMat);
        frond.position.set(Math.cos(angle) * 0.92, 2.25 + (i % 3) * 0.38, Math.sin(angle) * 0.92);
        frond.rotation.set(0.28, -angle, 0.12);
        frond.castShadow = true;
        group.add(frond);
      }

      return group;
    },
    pnw_hemlock(): THREE.Object3D {
      const group = new THREE.Group();
      const trunkMat = new THREE.MeshStandardMaterial({ color: 0x342012, roughness: 0.96 });
      const needleMat = new THREE.MeshStandardMaterial({ color: 0x163522, roughness: 0.94 });
      const needleLightMat = new THREE.MeshStandardMaterial({ color: 0x2e5b38, roughness: 0.92 });

      const lean = new THREE.Group();
      lean.rotation.z = -0.08;
      group.add(lean);

      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.28, 4.7, 9), trunkMat);
      trunk.position.y = 2.35;
      trunk.castShadow = true;
      lean.add(trunk);

      for (let i = 0; i < 7; i++) {
        const radius = 1.25 - i * 0.13;
        const needles = new THREE.Mesh(
          new THREE.ConeGeometry(radius, 0.74, 8),
          i % 2 === 0 ? needleMat : needleLightMat,
        );
        needles.position.set((i - 2) * 0.03, 1.65 + i * 0.48, 0);
        needles.rotation.y = i * 0.9;
        needles.scale.set(1.0, 1, 0.72);
        needles.castShadow = true;
        lean.add(needles);
      }

      const top = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.58, 8), needleLightMat);
      top.position.set(0.18, 5.15, 0);
      top.rotation.z = 0.18;
      top.castShadow = true;
      lean.add(top);

      return group;
    },
    pnw_sword_fern(): THREE.Object3D {
      const group = new THREE.Group();
      const frondMat = new THREE.MeshStandardMaterial({
        color: 0x2f6b3d,
        roughness: 0.9,
        side: THREE.DoubleSide,
      });
      const stemMat = new THREE.MeshStandardMaterial({ color: 0x385326, roughness: 0.92 });

      const crown = new THREE.Mesh(new THREE.SphereGeometry(0.12, 6, 4), stemMat);
      crown.position.y = 0.08;
      group.add(crown);

      for (let i = 0; i < 14; i++) {
        const angle = (i / 14) * Math.PI * 2;
        const length = 0.72 + (i % 4) * 0.12;
        const stem = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.035, length), stemMat);
        stem.position.set(Math.cos(angle) * length * 0.25, 0.16, Math.sin(angle) * length * 0.25);
        stem.rotation.set(0.34, angle, 0);
        group.add(stem);

        const leaf = new THREE.Mesh(new THREE.PlaneGeometry(0.22, length), frondMat);
        leaf.position.set(Math.cos(angle) * length * 0.38, 0.22, Math.sin(angle) * length * 0.38);
        leaf.rotation.set(1.1, angle, 0);
        leaf.castShadow = true;
        group.add(leaf);
      }

      return group;
    },
    pnw_grass_clump(): THREE.Object3D {
      const group = new THREE.Group();
      const mats = [
        new THREE.MeshStandardMaterial({ color: 0x456f2e, roughness: 0.92, side: THREE.DoubleSide }),
        new THREE.MeshStandardMaterial({ color: 0x6f8b3a, roughness: 0.88, side: THREE.DoubleSide }),
        new THREE.MeshStandardMaterial({ color: 0x2f5c2c, roughness: 0.95, side: THREE.DoubleSide }),
      ];

      for (let i = 0; i < 12; i += 1) {
        const angle = (i / 12) * Math.PI * 2;
        const blade = new THREE.Mesh(new THREE.PlaneGeometry(0.08, 0.55 + (i % 4) * 0.08), mats[i % mats.length]);
        blade.position.set(Math.cos(angle) * 0.12, 0.22, Math.sin(angle) * 0.12);
        blade.rotation.set(0.45 + (i % 3) * 0.1, angle, 0.08);
        blade.castShadow = true;
        group.add(blade);
      }

      return group;
    },
    pnw_wildflower_clump(): THREE.Object3D {
      const group = AssetLoader.primitives.pnw_grass_clump() as THREE.Group;
      const stemMat = new THREE.MeshStandardMaterial({ color: 0x335c2d, roughness: 0.9 });
      const flowerMats = [
        new THREE.MeshStandardMaterial({ color: 0xe0d26b, roughness: 0.82 }),
        new THREE.MeshStandardMaterial({ color: 0xc96b7e, roughness: 0.85 }),
        new THREE.MeshStandardMaterial({ color: 0xb8d8f0, roughness: 0.82 }),
      ];

      for (let i = 0; i < 7; i += 1) {
        const angle = (i / 7) * Math.PI * 2;
        const radius = 0.12 + (i % 3) * 0.08;
        const height = 0.34 + (i % 4) * 0.06;
        const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.014, height, 5), stemMat);
        stem.position.set(Math.cos(angle) * radius, height / 2, Math.sin(angle) * radius);
        group.add(stem);
        const flower = new THREE.Mesh(new THREE.SphereGeometry(0.045, 6, 4), flowerMats[i % flowerMats.length]);
        flower.position.set(Math.cos(angle) * radius, height + 0.035, Math.sin(angle) * radius);
        group.add(flower);
      }

      return group;
    },
    pnw_low_shrub(): THREE.Object3D {
      const group = new THREE.Group();
      const leafMat = new THREE.MeshStandardMaterial({ color: 0x2f5b35, roughness: 0.94 });
      const leafLightMat = new THREE.MeshStandardMaterial({ color: 0x4f7d42, roughness: 0.9 });
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x3b2415, roughness: 0.96 });

      for (let i = 0; i < 7; i += 1) {
        const angle = (i / 7) * Math.PI * 2;
        const branch = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.028, 0.55, 5), woodMat);
        branch.position.set(Math.cos(angle) * 0.16, 0.26, Math.sin(angle) * 0.16);
        branch.rotation.set(0.65, angle, 0);
        group.add(branch);
        const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.28 + (i % 2) * 0.08, 8, 5), i % 2 === 0 ? leafMat : leafLightMat);
        leaf.position.set(Math.cos(angle) * 0.28, 0.45, Math.sin(angle) * 0.28);
        leaf.scale.set(1.15, 0.62, 0.86);
        leaf.castShadow = true;
        group.add(leaf);
      }

      return group;
    },
    pnw_mossy_boulder(): THREE.Object3D {
      const group = new THREE.Group();
      const rockMat = new THREE.MeshStandardMaterial({
        color: 0x555a54,
        flatShading: true,
        roughness: 0.97,
      });
      const mossMat = new THREE.MeshStandardMaterial({ color: 0x31512a, roughness: 0.98 });

      const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(0.72, 0), rockMat);
      rock.position.y = 0.42;
      rock.scale.set(1.15, 0.72, 0.92);
      rock.castShadow = true;
      rock.receiveShadow = true;
      group.add(rock);

      const moss = new THREE.Mesh(new THREE.SphereGeometry(0.58, 8, 4, 0, Math.PI * 2, 0, Math.PI * 0.55), mossMat);
      moss.position.y = 0.78;
      moss.scale.set(1.25, 0.25, 0.95);
      group.add(moss);

      return group;
    },
    pnw_fallen_log(): THREE.Object3D {
      const group = new THREE.Group();
      const barkMat = new THREE.MeshStandardMaterial({ color: 0x553019, roughness: 0.96 });
      const cutMat = new THREE.MeshStandardMaterial({ color: 0x9b7144, roughness: 0.9 });
      const mossMat = new THREE.MeshStandardMaterial({ color: 0x2e4b25, roughness: 0.98 });

      const log = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.31, 3.4, 12), barkMat);
      log.rotation.z = Math.PI / 2;
      log.position.y = 0.33;
      log.castShadow = true;
      log.receiveShadow = true;
      group.add(log);

      for (const x of [-1.72, 1.72]) {
        const cut = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 0.04, 12), cutMat);
        cut.rotation.z = Math.PI / 2;
        cut.position.set(x, 0.33, 0);
        group.add(cut);
      }

      for (const x of [-0.8, 0.1, 0.75]) {
        const moss = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.045, 0.28), mossMat);
        moss.position.set(x, 0.58, -0.05);
        moss.rotation.z = -0.08;
        group.add(moss);
      }

      return group;
    },
    pnw_path_edge_stone(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({
        color: 0x6f7068,
        flatShading: true,
        roughness: 0.95,
      });
      const mossMat = new THREE.MeshStandardMaterial({ color: 0x2e4b25, roughness: 0.98 });
      const stone = new THREE.Mesh(new THREE.DodecahedronGeometry(0.35, 0), stoneMat);
      stone.position.y = 0.22;
      stone.scale.set(1.15, 0.42, 0.72);
      stone.castShadow = true;
      stone.receiveShadow = true;
      group.add(stone);
      const moss = new THREE.Mesh(new THREE.SphereGeometry(0.22, 6, 4, 0, Math.PI * 2, 0, Math.PI * 0.55), mossMat);
      moss.position.y = 0.36;
      moss.scale.set(1.0, 0.18, 0.7);
      group.add(moss);
      return group;
    },
    dirt_path_strip(): THREE.Object3D {
      const group = new THREE.Group();
      const dirtMat = new THREE.MeshStandardMaterial({ color: 0x5f4a31, roughness: 0.96 });
      const grassMat = new THREE.MeshStandardMaterial({ color: 0x3f6330, roughness: 0.92 });
      const path = new THREE.Mesh(new THREE.BoxGeometry(1, 0.09, 1), dirtMat);
      path.position.y = 0.045;
      path.receiveShadow = true;
      group.add(path);
      for (const x of [-0.42, 0.42]) {
        const shoulder = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.095, 1), grassMat);
        shoulder.position.set(x, 0.048, 0);
        shoulder.receiveShadow = true;
        group.add(shoulder);
      }
      return group;
    },
    cobblestone_path_strip(): THREE.Object3D {
      const group = new THREE.Group();
      const baseMat = new THREE.MeshStandardMaterial({ color: 0x716e66, roughness: 0.9 });
      const edgeMat = new THREE.MeshStandardMaterial({ color: 0x4f4d49, roughness: 0.93 });
      const base = new THREE.Mesh(new THREE.BoxGeometry(1, 0.11, 1), baseMat);
      base.position.y = 0.055;
      base.receiveShadow = true;
      group.add(base);
      for (const x of [-0.44, 0.44]) {
        const curb = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.15, 1), edgeMat);
        curb.position.set(x, 0.075, 0);
        curb.receiveShadow = true;
        group.add(curb);
      }
      for (let z = -0.42; z <= 0.42; z += 0.24) {
        const seam = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.012, 0.018), edgeMat);
        seam.position.set(0, 0.116, z);
        group.add(seam);
      }
      return group;
    },
    building(): THREE.Object3D {
      const group = new THREE.Group();
      const wallMat = new THREE.MeshStandardMaterial({ color: 0xa08a68, roughness: 0.85 });
      const timberMat = new THREE.MeshStandardMaterial({ color: 0x3a2818, roughness: 0.9 });
      const roofMat = new THREE.MeshStandardMaterial({ color: 0x5a2010, roughness: 0.8 });
      // Foundation
      const foundation = new THREE.Mesh(new THREE.BoxGeometry(4.4, 0.3, 3.4), timberMat);
      foundation.position.y = 0.15;
      foundation.receiveShadow = true;
      group.add(foundation);
      // Main structure
      const base = new THREE.Mesh(new THREE.BoxGeometry(4, 2.5, 3), wallMat);
      base.position.y = 1.55;
      base.castShadow = true;
      base.receiveShadow = true;
      group.add(base);
      // Timber frame beams (half-timbered style)
      for (const [px, pz] of [[-2, -1.5], [2, -1.5], [-2, 1.5], [2, 1.5]]) {
        const beam = new THREE.Mesh(new THREE.BoxGeometry(0.15, 2.5, 0.15), timberMat);
        beam.position.set(px, 1.55, pz);
        group.add(beam);
      }
      // Horizontal beam
      const hBeam = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.12, 0.12), timberMat);
      hBeam.position.set(0, 1.55, 1.52);
      group.add(hBeam);
      // Roof
      const roof = new THREE.Mesh(
        new THREE.ConeGeometry(3.2, 1.8, 4),
        roofMat,
      );
      roof.rotation.y = Math.PI / 4;
      roof.position.y = 3.7;
      roof.scale.set(1.05, 1, 0.8);
      roof.castShadow = true;
      group.add(roof);
      // Chimney
      const chimney = new THREE.Mesh(new THREE.BoxGeometry(0.4, 1.2, 0.4), timberMat);
      chimney.position.set(1.2, 4.0, 0.5);
      chimney.castShadow = true;
      group.add(chimney);
      return group;
    },

    // --- WAR city prop primitives ---

    /** City perimeter wall segment — long stone block. */
    wall_segment(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x8a8a80, roughness: 0.9 });
      const capMat = new THREE.MeshStandardMaterial({ color: 0x707068, roughness: 0.9 });
      const wall = new THREE.Mesh(new THREE.BoxGeometry(10, 4, 1.5), stoneMat);
      wall.position.y = 2;
      wall.castShadow = true;
      wall.receiveShadow = true;
      group.add(wall);
      // Crenellations (merlons)
      for (let i = -4; i <= 4; i += 2) {
        const merlon = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1, 1.5), capMat);
        merlon.position.set(i, 4.5, 0);
        merlon.castShadow = true;
        group.add(merlon);
      }
      return group;
    },

    /** City wall tower — tall cylindrical stone tower with crenellations. */
    tower(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x7a7870, roughness: 0.9 });
      const capMat = new THREE.MeshStandardMaterial({ color: 0x606058 });
      const body = new THREE.Mesh(new THREE.CylinderGeometry(1.8, 2.0, 12, 12), stoneMat);
      body.position.y = 6;
      body.castShadow = true;
      body.receiveShadow = true;
      group.add(body);
      const top = new THREE.Mesh(new THREE.CylinderGeometry(2.0, 2.0, 0.5, 12), capMat);
      top.position.y = 12.25;
      group.add(top);
      // Crenellations on top
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        const merlon = new THREE.Mesh(new THREE.BoxGeometry(0.6, 1.2, 0.6), capMat);
        merlon.position.set(Math.cos(a) * 1.8, 13.1, Math.sin(a) * 1.8);
        group.add(merlon);
      }
      return group;
    },

    /** City gate — two flanking towers with portcullis arch. */
    gate(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x7a7870, roughness: 0.9 });
      const archMat = new THREE.MeshStandardMaterial({ color: 0x5a5850 });
      // Left tower
      const tL = new THREE.Mesh(new THREE.CylinderGeometry(2, 2.2, 14, 12), stoneMat);
      tL.position.set(-5, 7, 0);
      tL.castShadow = true;
      group.add(tL);
      // Right tower
      const tR = tL.clone();
      tR.position.set(5, 7, 0);
      group.add(tR);
      // Connecting arch lintel
      const lintel = new THREE.Mesh(new THREE.BoxGeometry(10, 2, 3), stoneMat);
      lintel.position.set(0, 8, 0);
      lintel.castShadow = true;
      group.add(lintel);
      // Arch soffit (dark interior)
      const arch = new THREE.Mesh(new THREE.BoxGeometry(4, 6, 3.1), archMat);
      arch.position.set(0, 4, 0);
      group.add(arch);
      return group;
    },

    /** Altdorf castle fallback - large keep, gatehouse, and hard-surface walls. */
    castle(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x827a6e, roughness: 0.9 });
      const darkStoneMat = new THREE.MeshStandardMaterial({ color: 0x4b4742, roughness: 0.95 });
      const roofMat = new THREE.MeshStandardMaterial({ color: 0x394858, roughness: 0.75 });
      const bannerMat = new THREE.MeshStandardMaterial({ color: 0x9b2020, roughness: 0.85 });
      const goldMat = new THREE.MeshStandardMaterial({ color: 0xd0a33a, metalness: 0.5, roughness: 0.45 });
      const ironMat = new THREE.MeshStandardMaterial({ color: 0x2d3033, metalness: 0.6, roughness: 0.5 });

      const halfW = 75;
      const halfD = 68;
      const wallT = 5;
      const gateGap = 20;
      const outerH = 12;

      const foundation = new THREE.Mesh(new THREE.BoxGeometry(160, 0.8, 148), darkStoneMat);
      foundation.position.y = 0.4;
      foundation.receiveShadow = true;
      group.add(foundation);

      for (const [width, depth, px, pz] of [
        [halfW - gateGap / 2, wallT, -(halfW + gateGap / 2) / 2, halfD],
        [halfW - gateGap / 2, wallT, (halfW + gateGap / 2) / 2, halfD],
        [150, wallT, 0, -halfD],
        [wallT, 136, -halfW, 0],
        [wallT, 136, halfW, 0],
      ] as const) {
        const wall = new THREE.Mesh(new THREE.BoxGeometry(width, outerH, depth), stoneMat);
        wall.position.set(px, 6.8, pz);
        wall.castShadow = true;
        wall.receiveShadow = true;
        group.add(wall);
      }

      const addMerlon = (x: number, z: number, sx = 1, sz = 1) => {
        const merlon = new THREE.Mesh(new THREE.BoxGeometry(sx, 1.45, sz), darkStoneMat);
        merlon.position.set(x, 12.75, z);
        merlon.castShadow = true;
        group.add(merlon);
      };
      for (let x = -75; x <= -10; x += 4) addMerlon(x, halfD, 1.35, 3.6);
      for (let x = 10; x <= 75; x += 4) addMerlon(x, halfD, 1.35, 3.6);
      for (let x = -75; x <= 75; x += 4) addMerlon(x, -halfD, 1.35, 3.6);
      for (let z = -68; z <= 68; z += 4) {
        addMerlon(-halfW, z, 3.6, 1.35);
        addMerlon(halfW, z, 3.6, 1.35);
      }

      for (const x of [-halfW, halfW]) {
        for (const z of [-halfD, halfD]) {
          const tower = new THREE.Mesh(new THREE.CylinderGeometry(8.2, 8.2, 16, 32), stoneMat);
          tower.position.set(x, 8.8, z);
          tower.castShadow = true;
          group.add(tower);
          const cap = new THREE.Mesh(new THREE.CylinderGeometry(8.8, 8.8, 0.85, 32), darkStoneMat);
          cap.position.set(x, 17.15, z);
          group.add(cap);
          const towerRoof = new THREE.Mesh(new THREE.ConeGeometry(8, 6.4, 16), roofMat);
          towerRoof.position.set(x, 20.8, z);
          towerRoof.castShadow = true;
          group.add(towerRoof);
        }
      }

      for (const x of [-14, 14]) {
        const tower = new THREE.Mesh(new THREE.CylinderGeometry(8.2, 8.2, 19, 32), stoneMat);
        tower.position.set(x, 10.3, halfD + 1.8);
        tower.castShadow = true;
        group.add(tower);
        const gateRoof = new THREE.Mesh(new THREE.ConeGeometry(8, 7.6, 16), roofMat);
        gateRoof.position.set(x, 24.3, halfD + 1.8);
        group.add(gateRoof);
      }

      const lintel = new THREE.Mesh(new THREE.BoxGeometry(30, 5.4, 8), stoneMat);
      lintel.position.set(0, 13.8, halfD + 1.8);
      lintel.castShadow = true;
      group.add(lintel);
      const arch = new THREE.Mesh(new THREE.BoxGeometry(16, 9, 8.3), darkStoneMat);
      arch.position.set(0, 5.25, halfD + 2);
      group.add(arch);
      for (const x of [-9, -5.4, -1.8, 1.8, 5.4, 9]) {
        const bar = new THREE.Mesh(new THREE.BoxGeometry(0.22, 9.2, 0.22), ironMat);
        bar.position.set(x, 5.2, halfD + 6.3);
        group.add(bar);
      }

      const keepWall = (width: number, depth: number, x: number, z: number) => {
        const wall = new THREE.Mesh(new THREE.BoxGeometry(width, 12, depth), stoneMat);
        wall.position.set(x, 6.8, z);
        wall.castShadow = true;
        wall.receiveShadow = true;
        group.add(wall);
        return wall;
      };
      const keepLintel = (x: number, z: number) => {
        const lintel = new THREE.Mesh(new THREE.BoxGeometry(14, 4, 3), stoneMat);
        lintel.position.set(x, 10.8, z);
        lintel.castShadow = true;
        lintel.receiveShadow = true;
        group.add(lintel);
      };
      keepWall(24, 3, -18, 10.5);
      keepWall(24, 3, 18, 10.5);
      keepLintel(0, 10.5);
      keepWall(24, 3, -18, -34.5);
      keepWall(24, 3, 18, -34.5);
      keepLintel(0, -34.5);
      for (const x of [-30, 30]) {
        keepWall(3, 18, x, 1);
        keepWall(3, 18, x, -25);
      }
      const keepFloor = new THREE.Mesh(new THREE.BoxGeometry(58, 0.35, 42), darkStoneMat);
      keepFloor.position.set(0, 0.98, -12);
      keepFloor.receiveShadow = true;
      group.add(keepFloor);
      const upper = new THREE.Mesh(new THREE.BoxGeometry(48, 4, 34), stoneMat);
      upper.position.set(0, 14.8, -12);
      upper.castShadow = true;
      group.add(upper);
      const top = new THREE.Mesh(new THREE.BoxGeometry(36, 4, 24), stoneMat);
      top.position.set(0, 18.8, -12);
      top.castShadow = true;
      group.add(top);
      const keepRoof = new THREE.Mesh(new THREE.ConeGeometry(27, 8, 8), roofMat);
      keepRoof.rotation.y = Math.PI / 4;
      keepRoof.position.set(0, 25.2, -12);
      group.add(keepRoof);
      const spire = new THREE.Mesh(new THREE.ConeGeometry(4.5, 10, 16), roofMat);
      spire.position.set(0, 38, -12);
      group.add(spire);

      for (const x of [-43, 43]) {
        const banner = new THREE.Mesh(new THREE.BoxGeometry(3.4, 8, 0.16), bannerMat);
        banner.position.set(x, 7.6, halfD + 2.8);
        group.add(banner);
        const trim = new THREE.Mesh(new THREE.BoxGeometry(3.8, 0.35, 0.18), goldMat);
        trim.position.set(x, 11.45, halfD + 2.95);
        group.add(trim);
      }

      return group;
    },

    /** Reusable two-leaf castle gate fallback. The GLB version carries animation clips. */
    castle_gate(): THREE.Object3D {
      const group = new THREE.Group();
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x4a2d16, roughness: 0.82 });
      const ironMat = new THREE.MeshStandardMaterial({ color: 0x2d3033, metalness: 0.65, roughness: 0.5 });
      for (const side of [-1, 1]) {
        const door = new THREE.Mesh(new THREE.BoxGeometry(8, 9.2, 0.55), woodMat);
        door.position.set(side * 4, 4.7, 0);
        door.castShadow = true;
        group.add(door);
        for (const y of [1.6, 4.6, 7.4]) {
          const strap = new THREE.Mesh(new THREE.BoxGeometry(7.8, 0.35, 0.68), ironMat);
          strap.position.set(side * 4, y, 0.36);
          group.add(strap);
        }
      }
      return group;
    },

    /** Reusable hinged castle door fallback. The GLB version carries animation clips. */
    castle_door(): THREE.Object3D {
      const group = new THREE.Group();
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x4a2d16, roughness: 0.84 });
      const darkWoodMat = new THREE.MeshStandardMaterial({ color: 0x2b1b10, roughness: 0.9 });
      const ironMat = new THREE.MeshStandardMaterial({ color: 0x2d3033, metalness: 0.65, roughness: 0.5 });
      const panel = new THREE.Mesh(new THREE.BoxGeometry(5.2, 6, 0.38), woodMat);
      panel.position.set(0, 3, 0);
      panel.castShadow = true;
      group.add(panel);
      for (const x of [-1.6, 0, 1.6]) {
        const plank = new THREE.Mesh(new THREE.BoxGeometry(0.14, 5.7, 0.44), darkWoodMat);
        plank.position.set(x, 3, 0.08);
        group.add(plank);
      }
      for (const y of [1.3, 3, 4.7]) {
        const strap = new THREE.Mesh(new THREE.BoxGeometry(5, 0.28, 0.5), ironMat);
        strap.position.set(0, y, 0.28);
        group.add(strap);
      }
      return group;
    },

    /** Reusable castle staircase fallback with broad stone treads. */
    castle_stairs(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x827a6e, roughness: 0.9 });
      const trimMat = new THREE.MeshStandardMaterial({ color: 0x4b4742, roughness: 0.95 });
      const steps = 12;
      const stepH = 4 / steps;
      const stepD = 1;
      for (let i = 0; i < steps; i++) {
        const step = new THREE.Mesh(new THREE.BoxGeometry(8, stepH, stepD), stoneMat);
        step.position.set(0, (i + 0.5) * stepH, -5.5 + i * stepD);
        step.castShadow = true;
        step.receiveShadow = true;
        group.add(step);
      }
      for (const x of [-4.4, 4.4]) {
        const rail = new THREE.Mesh(new THREE.BoxGeometry(0.35, 4.2, 12.5), trimMat);
        rail.position.set(x, 2.1, 0);
        rail.castShadow = true;
        group.add(rail);
      }
      return group;
    },

    temple(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0xc8b890, roughness: 0.85 });
      const roofMat = new THREE.MeshStandardMaterial({ color: 0x485868 });
      const goldMat = new THREE.MeshStandardMaterial({ color: 0xd4aa20, metalness: 0.6, roughness: 0.4 });
      // Main nave
      const nave = new THREE.Mesh(new THREE.BoxGeometry(12, 8, 20), stoneMat);
      nave.position.y = 4;
      nave.castShadow = true;
      nave.receiveShadow = true;
      group.add(nave);
      // Nave roof
      const naveRoof = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 7, 4, 4), roofMat);
      naveRoof.position.set(0, 10, 0);
      naveRoof.rotation.y = Math.PI / 4;
      group.add(naveRoof);
      // Central spire
      const spireBase = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.8, 10, 8), stoneMat);
      spireBase.position.set(0, 13, 0);
      spireBase.castShadow = true;
      group.add(spireBase);
      const spire = new THREE.Mesh(new THREE.ConeGeometry(1.2, 8, 8), roofMat);
      spire.position.set(0, 21, 0);
      spire.castShadow = true;
      group.add(spire);
      // Spire tip (gold)
      const tip = new THREE.Mesh(new THREE.ConeGeometry(0.15, 1.2, 6), goldMat);
      tip.position.set(0, 25.5, 0);
      group.add(tip);
      // Side transepts
      for (const side of [-1, 1]) {
        const transept = new THREE.Mesh(new THREE.BoxGeometry(5, 6, 8), stoneMat);
        transept.position.set(side * 8.5, 3, 0);
        transept.castShadow = true;
        group.add(transept);
        const tRoof = new THREE.Mesh(new THREE.ConeGeometry(4, 3, 4), roofMat);
        tRoof.position.set(side * 8.5, 7.5, 0);
        tRoof.rotation.y = Math.PI / 4;
        group.add(tRoof);
      }
      // Buttresses
      for (const dz of [-6, 0, 6]) {
        for (const side of [-1, 1]) {
          const butt = new THREE.Mesh(new THREE.BoxGeometry(1.5, 6, 1.5), stoneMat);
          butt.position.set(side * 7, 3, dz);
          group.add(butt);
        }
      }
      return group;
    },

    /** Decorative statue on a pedestal. */
    statue(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0xb0a890, roughness: 0.8 });
      // Pedestal
      const ped = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.8, 1.6), stoneMat);
      ped.position.y = 0.9;
      ped.castShadow = true;
      group.add(ped);
      // Figure
      const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.3, 1.0, 4, 8), stoneMat);
      body.position.y = 2.6;
      body.castShadow = true;
      group.add(body);
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.2, 8, 8), stoneMat);
      head.position.y = 3.6;
      group.add(head);
      // Raised arm + weapon
      const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 1.0, 6), stoneMat);
      arm.rotation.z = -Math.PI / 3;
      arm.position.set(0.5, 3.0, 0);
      group.add(arm);
      const weapon = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.8, 6), stoneMat);
      weapon.position.set(0.9, 3.5, 0);
      group.add(weapon);
      return group;
    },

    /** Plaza fountain — basin, column, water sphere. */
    fountain(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0xa0a098, roughness: 0.7 });
      const waterMat = new THREE.MeshStandardMaterial({
        color: 0x3a80c0,
        transparent: true,
        opacity: 0.7,
        roughness: 0.1,
        metalness: 0.2,
      });
      // Outer basin
      const basin = new THREE.Mesh(new THREE.CylinderGeometry(2.8, 2.5, 0.6, 16), stoneMat);
      basin.position.y = 0.3;
      basin.castShadow = true;
      group.add(basin);
      // Water surface
      const water = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.4, 0.1, 16), waterMat);
      water.position.y = 0.55;
      group.add(water);
      // Central column
      const col = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.3, 2.5, 10), stoneMat);
      col.position.y = 1.55;
      col.castShadow = true;
      group.add(col);
      // Top bowl
      const topBowl = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 0.8, 0.4, 12), stoneMat);
      topBowl.position.y = 2.8;
      group.add(topBowl);
      // Water sphere (jets)
      const jet = new THREE.Mesh(new THREE.SphereGeometry(0.4, 8, 8), waterMat);
      jet.position.y = 3.5;
      group.add(jet);
      return group;
    },

    /** Empire banner post — red panel with gold trim. */
    banner_post(): THREE.Object3D {
      const group = new THREE.Group();
      const poleMat = new THREE.MeshStandardMaterial({ color: 0x806010, metalness: 0.3 });
      const bannerMat = new THREE.MeshStandardMaterial({
        color: 0xcc1010,
        side: THREE.DoubleSide,
      });
      const trimMat = new THREE.MeshStandardMaterial({ color: 0xd4aa20, metalness: 0.6 });
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.09, 6, 8), poleMat);
      pole.position.y = 3;
      pole.castShadow = true;
      group.add(pole);
      // Banner panel
      const banner = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 2.0), bannerMat);
      banner.position.set(0.6, 5.2, 0);
      group.add(banner);
      // Gold crossbar
      const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.5, 6), trimMat);
      bar.rotation.z = Math.PI / 2;
      bar.position.set(0.6, 6.3, 0);
      group.add(bar);
      // Tip finial
      const finial = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.4, 6), trimMat);
      finial.position.y = 6.2;
      group.add(finial);
      return group;
    },

    /** Market vendor stall — canopy and counter. */
    vendor_stall(): THREE.Object3D {
      const group = new THREE.Group();
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x7a5830 });
      const canopyMat = new THREE.MeshStandardMaterial({ color: 0xb04020, side: THREE.DoubleSide });
      // Counter
      const counter = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.8, 1.0), woodMat);
      counter.position.y = 0.8;
      counter.castShadow = true;
      group.add(counter);
      // Legs
      for (const [px, pz] of [[-1, -0.4], [1, -0.4], [-1, 0.4], [1, 0.4]]) {
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 1.6, 6), woodMat);
        leg.position.set(px, 0.8, pz);
        group.add(leg);
      }
      // Canopy
      const canopy = new THREE.Mesh(new THREE.BoxGeometry(3, 0.15, 1.8), canopyMat);
      canopy.position.y = 2.2;
      canopy.rotation.x = -0.15;
      canopy.castShadow = true;
      group.add(canopy);
      // Support poles
      for (const px of [-1.1, 1.1]) {
        const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 2.2, 6), woodMat);
        pole.position.set(px, 1.1, -0.6);
        group.add(pole);
      }
      return group;
    },

    /** Wide stone steps for temple approaches. */
    steps(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0xb8aa90, roughness: 0.8 });
      for (let i = 0; i < 5; i++) {
        const step = new THREE.Mesh(
          new THREE.BoxGeometry(8 - i * 0.5, 0.3, 1.0),
          stoneMat,
        );
        step.position.set(0, i * 0.3, -i * 1.0);
        step.castShadow = true;
        step.receiveShadow = true;
        group.add(step);
      }
      return group;
    },

    /** Stone arch bridge. */
    bridge(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x9a9280, roughness: 0.9 });
      // Deck
      const deck = new THREE.Mesh(new THREE.BoxGeometry(4, 0.4, 12), stoneMat);
      deck.position.y = 3.2;
      deck.castShadow = true;
      deck.receiveShadow = true;
      group.add(deck);
      // Arch piers
      for (const pz of [-3, 3]) {
        const pier = new THREE.Mesh(new THREE.BoxGeometry(4, 3, 1.5), stoneMat);
        pier.position.set(0, 1.5, pz);
        pier.castShadow = true;
        group.add(pier);
      }
      // Arch (approximated as a cylinder segment)
      const arch = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, 4, 12, 1, true, 0, Math.PI), stoneMat);
      arch.rotation.z = Math.PI / 2;
      arch.position.set(0, 3, 0);
      group.add(arch);
      // Parapets
      for (const px of [-1.8, 1.8]) {
        const parapet = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1.0, 12), stoneMat);
        parapet.position.set(px, 3.9, 0);
        parapet.castShadow = true;
        group.add(parapet);
      }
      return group;
    },

    /** Wooden dock/pier with mooring posts. */
    dock(): THREE.Object3D {
      const group = new THREE.Group();
      const plankMat = new THREE.MeshStandardMaterial({ color: 0x6b4820, roughness: 0.95 });
      const postMat = new THREE.MeshStandardMaterial({ color: 0x4a3010 });
      // Deck planks
      const deck = new THREE.Mesh(new THREE.BoxGeometry(4, 0.2, 14), plankMat);
      deck.position.y = 0.3;
      deck.castShadow = true;
      deck.receiveShadow = true;
      group.add(deck);
      // Support piles
      for (const [px, pz] of [[-1.5, -5], [0, -5], [1.5, -5], [-1.5, 5], [0, 5], [1.5, 5]]) {
        const pile = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.15, 2.5, 8), postMat);
        pile.position.set(px, -0.9, pz);
        group.add(pile);
      }
      // Mooring posts
      for (const pz of [-4, 0, 4]) {
        const post = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 1.2, 8), postMat);
        post.position.set(2.2, 0.9, pz);
        group.add(post);
      }
      return group;
    },

    // --- NPC role-colored humanoids with visual markers ---

    /** City guard fallback with shield and spear. */
    npc_guard(): THREE.Object3D {
      const group = buildCharacterMesh('empire', 'Sunfire Templar') as THREE.Group;
      // Override pauldrons with blue-steel tint via recolor pass
      group.traverse((n) => {
        if ((n as THREE.Mesh).isMesh) {
          const mat = (n as THREE.Mesh).material as THREE.MeshStandardMaterial;
          if (mat.color && mat.metalness > 0.3) {
            mat.color.setHex(0x4a6080);
          }
        }
      });
      // Tall shield
      const shieldMat = new THREE.MeshStandardMaterial({ color: 0xcc1010, roughness: 0.6 });
      const shield = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.65, 0.45), shieldMat);
      shield.position.set(-0.5, 1.1, 0.05);
      shield.castShadow = true;
      group.add(shield);
      // Emblem on shield
      const emblem = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.22, 0.22),
        new THREE.MeshStandardMaterial({ color: 0xd4aa20, metalness: 0.7 }));
      emblem.position.set(-0.52, 1.15, 0.05);
      group.add(emblem);
      // Spear
      const spear = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.028, 2.8, 6),
        new THREE.MeshStandardMaterial({ color: 0x5a3a10, roughness: 0.9 }));
      spear.position.set(0.5, 1.5, 0);
      spear.castShadow = true;
      group.add(spear);
      const speartip = new THREE.Mesh(new THREE.ConeGeometry(0.04, 0.25, 6),
        new THREE.MeshStandardMaterial({ color: 0xa0a0b0, metalness: 0.7 }));
      speartip.position.set(0.5, 2.95, 0);
      group.add(speartip);
      return group;
    },
    /** Vendor NPC — civilian with apron. */
    npc_vendor(): THREE.Object3D {
      const group = new THREE.Group();
      // Use empire base but with civilian/cloth colors
      const base = buildCharacterMesh('empire') as THREE.Group;
      base.traverse((n) => {
        if ((n as THREE.Mesh).isMesh) {
          const mat = (n as THREE.Mesh).material as THREE.MeshStandardMaterial;
          if (mat.metalness > 0.3) mat.metalness = 0;
          if (mat.color) mat.color.setHex(0x8a6040);
        }
      });
      group.add(base);
      const apron = new THREE.Mesh(new THREE.BoxGeometry(0.54, 0.55, 0.06),
        new THREE.MeshStandardMaterial({ color: 0xc8b07a, roughness: 0.95 }));
      apron.position.set(0, 1.0, 0.17);
      group.add(apron);
      return group;
    },
    /** Class trainer NPC fallback with heavier plate styling. */
    npc_trainer(): THREE.Object3D {
      const group = buildCharacterMesh('empire') as THREE.Group;
      group.traverse((n) => {
        if ((n as THREE.Mesh).isMesh) {
          const mat = (n as THREE.Mesh).material as THREE.MeshStandardMaterial;
          if (mat.color) mat.color.multiplyScalar(1.15); // slightly brighter gold
        }
      });
      return group;
    },
    /** Banker NPC — well-dressed merchant with coin purse. */
    npc_banker(): THREE.Object3D {
      const group = new THREE.Group();
      const base = buildCharacterMesh('empire') as THREE.Group;
      base.traverse((n) => {
        if ((n as THREE.Mesh).isMesh) {
          const mat = (n as THREE.Mesh).material as THREE.MeshStandardMaterial;
          if (mat.metalness > 0.3) { mat.metalness = 0.1; mat.color.setHex(0x707878); }
        }
      });
      group.add(base);
      // Coin purse hanging from belt
      const purse = new THREE.Mesh(new THREE.SphereGeometry(0.1, 6, 6),
        new THREE.MeshStandardMaterial({ color: 0x8a7020 }));
      purse.position.set(0.3, 0.85, 0.2);
      group.add(purse);
      return group;
    },
    /** Quest giver NPC (yellow — WAR's exclamation mark equivalent). */
    npc_quest(): THREE.Object3D {
      const group = AssetLoader.primitives.humanoid(0xd0b020);
      // Floating exclamation marker
      const markerMat = new THREE.MeshStandardMaterial({
        color: 0xffdd00,
        emissive: 0xffdd00,
        emissiveIntensity: 0.3,
      });
      const excl = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.06, 0.35, 6), markerMat);
      excl.position.set(0, 2.1, 0);
      group.add(excl);
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.06, 6, 6), markerMat);
      dot.position.set(0, 1.88, 0);
      group.add(dot);
      return group;
    },
  };
}
