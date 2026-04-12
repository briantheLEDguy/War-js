import * as THREE from 'three';
import type { AssetLoader } from '../game/AssetLoader';

export interface TerrainOpts {
  size: number;
  segments: number;
  heightTexture?: string;
  diffuseTexture?: string;
  /** If true, skip height variation — all y = 0. Use for city/indoor zones. */
  flatTerrain?: boolean;
}

/**
 * Procedural terrain using multi-octave noise. If a heightmap texture is
 * provided and loads, we sample that instead. This stays runnable without
 * any external files.
 */
export class Terrain {
  mesh!: THREE.Mesh;
  private size: number;
  private segments: number;
  private heights: Float32Array;
  private flat = false;

  constructor(opts: TerrainOpts) {
    this.size = opts.size;
    this.segments = opts.segments;
    this.heights = new Float32Array((opts.segments + 1) * (opts.segments + 1));
  }

  async build(loader: AssetLoader, opts: TerrainOpts): Promise<THREE.Mesh> {
    this.size = opts.size;
    this.segments = opts.segments;
    this.flat = opts.flatTerrain ?? false;
    this.heights = new Float32Array((opts.segments + 1) * (opts.segments + 1));

    const geo = new THREE.PlaneGeometry(opts.size, opts.size, opts.segments, opts.segments);
    geo.rotateX(-Math.PI / 2);
    const pos = geo.attributes.position as THREE.BufferAttribute;
    const vertCount = pos.count;

    if (!this.flat) {
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
        const variation = 0.85 + Math.random() * 0.15;
        color.setRGB(0.45 * variation, 0.42 * variation, 0.38 * variation);
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
        const noise = (Math.random() - 0.5) * 0.06;
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
      diffuse.repeat.set(this.flat ? 32 : 24, this.flat ? 32 : 24);
    }
    const mat = new THREE.MeshStandardMaterial({
      color: diffuse ? 0xffffff : 0xffffff,
      map: diffuse ?? null,
      vertexColors: true,
      roughness: 0.92,
      metalness: 0.0,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.receiveShadow = true;
    this.mesh = mesh;
    return mesh;
  }

  /** World-space height lookup via bilinear sampling. Returns 0 for flat terrain. */
  heightAt(x: number, z: number): number {
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
}
