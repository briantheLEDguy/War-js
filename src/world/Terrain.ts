import * as THREE from 'three';
import { citySurfaceGeometry, type CanalDefinition } from './CityWater';
import { applyCityWeathering } from './CityWeathering';
import { cityHeightAt, type CityElevation } from './CityElevation';
import type { AssetLoader } from '../game/AssetLoader';

export interface TerrainOpts {
  size: number;
  segments: number;
  /** Optional .glb terrain mesh under /public/assets/models/. */
  model?: string;
  heightTexture?: string;
  diffuseTexture?: string;
  /** If true, skip height variation — all y = 0. Use for city/indoor zones. */
  flatTerrain?: boolean;
  canals?: CanalDefinition[];
  cityElevation?: CityElevation;
}

/**
 * Procedural terrain using multi-octave noise. If a heightmap texture is
 * provided and loads, we sample that instead. This stays runnable without
 * any external files.
 */
export class Terrain {
  mesh!: THREE.Object3D;
  private size: number;
  private segments: number;
  private heights: Float32Array;
  private flat = false;
  private cityElevation?: CityElevation;
  get cityHeightField(): CityElevation | undefined { return this.cityElevation; }
  get worldSize(): number { return this.size; }
  private modelHeightMeshes: THREE.Mesh[] = [];
  private modelBounds = new THREE.Box3();
  private modelRaycaster = new THREE.Raycaster();
  private modelHeightCache = new Map<string, number>();
  private readonly down = new THREE.Vector3(0, -1, 0);

  constructor(opts: TerrainOpts) {
    this.size = opts.size;
    this.segments = opts.segments;
    this.heights = new Float32Array((opts.segments + 1) * (opts.segments + 1));
  }

  async build(loader: AssetLoader, opts: TerrainOpts): Promise<THREE.Object3D> {
    this.size = opts.size;
    this.segments = opts.segments;
    this.flat = opts.flatTerrain ?? false;
    this.cityElevation = opts.cityElevation;
    this.heights = new Float32Array((opts.segments + 1) * (opts.segments + 1));
    this.modelHeightMeshes = [];
    this.modelBounds.makeEmpty();
    this.modelHeightCache.clear();

    if (opts.model) {
      const terrainModel = await loader.loadModel(opts.model, () => this.buildModelFallbackPlane(opts));
      this.prepareModelTerrain(terrainModel);
      this.mesh = terrainModel;
      return terrainModel;
    }

    const geo = opts.canals?.length
      ? citySurfaceGeometry(opts.size, opts.canals, 'ground', opts.cityElevation ? { segments: opts.cityElevation.segments, detailX: opts.cityElevation.detailX, detailZ: opts.cityElevation.detailZ, heightAt: (x, z) => this.heightAt(x, z) } : undefined)
      : new THREE.PlaneGeometry(opts.size, opts.size, opts.segments, opts.segments).rotateX(-Math.PI / 2);
    const pos = geo.attributes.position as THREE.BufferAttribute;
    const vertCount = pos.count;

    if (!this.flat && !this.cityElevation) {
      // Procedural height. Later: sample from heightmap if provided.
      const s = opts.segments;
      for (let iy = 0; iy <= s; iy++) {
        for (let ix = 0; ix <= s; ix++) {
          const u = ix / s - 0.5;
          const v = iy / s - 0.5;
          const r = Math.sqrt(u * u + v * v);
          // Rolling hills + a central flat-ish clearing
          const hills =
            Math.sin(u * 5.2) * 0.6 +
            Math.cos(v * 4.7) * 0.5 +
            Math.sin((u + v) * 8.1) * 0.3;
          const ringDown = Math.max(0, 1 - r * 4);
          const h = (hills - ringDown * hills * 0.9) * 2.0;
          const i = iy * (s + 1) + ix;
          this.heights[i] = h;
          pos.setY(i, h);
        }
      }
    }
    // flatTerrain: heights array stays all-zero, positions stay at y=0

    geo.computeVertexNormals();

    // Add vertex colors for natural terrain appearance
    const colors = new Float32Array(vertCount * 3);
    const color = new THREE.Color();

    if (this.flat) {
      // City zones: cobblestone-like color variation
      for (let i = 0; i < vertCount; i++) {
        const variation = 0.85 + deterministicVertexNoise(i, opts.size, opts.segments) * 0.15;
        color.setRGB(0.45 * variation, 0.42 * variation, 0.38 * variation);
        if (this.cityElevation && pos.getZ(i) > 250) color.setRGB(.24 * variation, .27 * variation, .29 * variation);
        colors[i * 3] = color.r;
        colors[i * 3 + 1] = color.g;
        colors[i * 3 + 2] = color.b;
      }
    } else {
      // Outdoor zones: height-based coloring (grass → dirt → rock)
      const s = opts.segments;
      for (let i = 0; i < vertCount; i++) {
        const y = pos.getY(i);
        const norm = geo.attributes.normal;
        const ny = norm ? norm.getY(i) : 1;
        const slope = 1.0 - ny;

        // Height-based gradient with some noise
        const noise = (deterministicVertexNoise(i, opts.size, opts.segments) - 0.5) * 0.06;
        if (y < -0.5) {
          // Low ground: darker grass / mud
          color.setRGB(0.18 + noise, 0.28 + noise, 0.12 + noise);
        } else if (y < 0.5) {
          // Mid: healthy grass
          const t = (y + 0.5) / 1.0;
          color.setRGB(
            0.18 + t * 0.1 + noise,
            0.30 + t * 0.08 + noise,
            0.12 + t * 0.04 + noise,
          );
        } else {
          // High ground: earthy brown
          const t = Math.min((y - 0.5) / 1.5, 1);
          color.setRGB(
            0.3 + t * 0.12 + noise,
            0.25 + t * 0.05 + noise,
            0.15 + t * 0.02 + noise,
          );
        }

        // Steep slopes get rocky gray
        if (slope > 0.3) {
          const t = Math.min((slope - 0.3) / 0.4, 1);
          color.lerp(new THREE.Color(0.4, 0.38, 0.35), t);
        }

        // Edge darkening for path-like appearance around center
        const ix = i % (s + 1);
        const iy = Math.floor(i / (s + 1));
        const u = ix / s - 0.5;
        const v = iy / s - 0.5;
        const distFromCenter = Math.sqrt(u * u + v * v);
        if (distFromCenter < 0.08) {
          color.lerp(new THREE.Color(0.3, 0.25, 0.18), 0.4);
        }

        colors[i * 3] = color.r;
        colors[i * 3 + 1] = color.g;
        colors[i * 3 + 2] = color.b;
      }
    }

    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // City zones use stone gray fallback; outdoor zones use grass green
    const fallbackColor = this.flat ? 0x7a7a7a : 0x4a7c3a;
    const diffuse = opts.diffuseTexture
      ? await loader.loadTexture(opts.diffuseTexture, fallbackColor)
      : null;
    if (diffuse) {
      const repeat = opts.canals?.length ? opts.size / 4 : this.flat ? 32 : 24;
      diffuse.repeat.set(repeat, repeat);
      if (opts.canals?.length) diffuse.anisotropy = 8;
    }
    const mat = new THREE.MeshStandardMaterial({
      color: diffuse ? 0xffffff : 0xffffff,
      map: diffuse ?? null,
      vertexColors: true,
      roughness: 0.92,
      metalness: 0.0,
    });
    if (opts.canals?.length) applyCityWeathering(mat);
    const materials = [mat];
    if (opts.cityElevation) {
      const rock = new THREE.MeshStandardMaterial({ color: 0x697078, vertexColors: true, roughness: 1, flatShading: true });
      materials.push(rock);
      applyCityWeathering(rock);
      const index = geo.getIndex()!;
      const paved: number[] = [], mountain: number[] = [];
      for (let i = 0; i < index.count; i += 3) {
        const group = [0, 1, 2].every(j => pos.getZ(index.getX(i + j)) >= 250) ? mountain : paved;
        group.push(index.getX(i), index.getX(i + 1), index.getX(i + 2));
      }
      geo.setIndex([...paved, ...mountain]);
      geo.addGroup(0, paved.length, 0);
      geo.addGroup(paved.length, mountain.length, 1);
    }
    const mesh = new THREE.Mesh(geo, opts.cityElevation ? materials : mat);
    mesh.receiveShadow = true;
    this.mesh = mesh;
    return mesh;
  }

  /** World-space height lookup via bilinear sampling. Returns 0 for flat terrain. */
  heightAt(x: number, z: number): number {
    if (this.cityElevation) return cityHeightAt(this.cityElevation, this.size, x, z);
    const modelHeight = this.heightAtModel(x, z);
    if (modelHeight !== null) return modelHeight;

    if (this.flat) return 0;
    const half = this.size / 2;
    const u = (x + half) / this.size;
    const v = (z + half) / this.size;
    if (u < 0 || u > 1 || v < 0 || v > 1) return 0;
    const s = this.segments;
    const fx = u * s;
    const fy = v * s;
    const ix = Math.floor(fx);
    const iy = Math.floor(fy);
    const tx = fx - ix;
    const ty = fy - iy;
    const idx = (y: number, x: number) => y * (s + 1) + x;
    const ixc = Math.min(ix + 1, s);
    const iyc = Math.min(iy + 1, s);
    const h00 = this.heights[idx(iy, ix)];
    const h10 = this.heights[idx(iy, ixc)];
    const h01 = this.heights[idx(iyc, ix)];
    const h11 = this.heights[idx(iyc, ixc)];
    const hx0 = h00 * (1 - tx) + h10 * tx;
    const hx1 = h01 * (1 - tx) + h11 * tx;
    return hx0 * (1 - ty) + hx1 * ty;
  }

  refreshModelTransform(): void {
    if (this.modelHeightMeshes.length === 0 || !this.mesh) return;
    this.mesh.updateMatrixWorld(true);
    this.modelBounds.setFromObject(this.mesh);
    this.modelHeightCache.clear();
  }

  private prepareModelTerrain(root: THREE.Object3D): void {
    root.updateMatrixWorld(true);
    root.traverse((node) => {
      if (!(node as THREE.Mesh).isMesh) return;

      const mesh = node as THREE.Mesh;
      mesh.castShadow = false;
      mesh.receiveShadow = true;
      mesh.geometry.computeBoundingBox();
      mesh.geometry.computeBoundingSphere();

      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const material of materials) {
        if (!material) continue;
        material.side = THREE.DoubleSide;
        if (material instanceof THREE.MeshStandardMaterial) {
          material.roughness = Math.max(material.roughness, 0.88);
          material.metalness = 0;
        }
        material.needsUpdate = true;
      }

      this.modelHeightMeshes.push(mesh);
    });

    root.updateMatrixWorld(true);
    this.modelBounds.setFromObject(root);
  }

  private heightAtModel(x: number, z: number): number | null {
    if (this.modelHeightMeshes.length === 0 || this.modelBounds.isEmpty() || !this.mesh.visible) return null;

    const quantizedX = Math.round(x * 2) / 2;
    const quantizedZ = Math.round(z * 2) / 2;
    const cacheKey = `${quantizedX}:${quantizedZ}`;
    const cached = this.modelHeightCache.get(cacheKey);
    if (cached !== undefined) return cached;

    if (
      quantizedX < this.modelBounds.min.x ||
      quantizedX > this.modelBounds.max.x ||
      quantizedZ < this.modelBounds.min.z ||
      quantizedZ > this.modelBounds.max.z
    ) {
      return null;
    }

    const origin = new THREE.Vector3(quantizedX, this.modelBounds.max.y + 80, quantizedZ);
    this.modelRaycaster.set(origin, this.down);
    this.modelRaycaster.near = 0;
    this.modelRaycaster.far = (this.modelBounds.max.y - this.modelBounds.min.y) + 160;
    const hits = this.modelRaycaster.intersectObjects(this.modelHeightMeshes, false);
    const height = hits[0]?.point.y;
    if (height === undefined) return null;

    if (this.modelHeightCache.size > 20000) this.modelHeightCache.clear();
    this.modelHeightCache.set(cacheKey, height);
    return height;
  }

  private buildModelFallbackPlane(opts: TerrainOpts): THREE.Mesh {
    const geo = opts.canals?.length
      ? citySurfaceGeometry(opts.size, opts.canals, 'ground')
      : new THREE.PlaneGeometry(opts.size, opts.size, opts.segments, opts.segments).rotateX(-Math.PI / 2);
    const mat = new THREE.MeshStandardMaterial({
      color: opts.flatTerrain ? 0x7a7a7a : 0x4a7c3a,
      roughness: 0.92,
      metalness: 0,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.receiveShadow = true;
    return mesh;
  }
}

function deterministicVertexNoise(index: number, size: number, segments: number): number {
  let state = Math.imul(index + 1, 374761393)
    ^ Math.imul(Math.round(size * 10) + 17, 668265263)
    ^ Math.imul(segments + 101, 2246822519);
  state = Math.imul(state ^ (state >>> 13), 1274126177);
  return ((state ^ (state >>> 16)) >>> 0) / 4294967295;
}
