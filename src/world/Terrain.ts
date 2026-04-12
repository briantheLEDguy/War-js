import * as THREE from 'three';
import type { AssetLoader } from '../game/AssetLoader';

export interface TerrainOpts {
  size: number;
  segments: number;
  heightTexture?: string;
  diffuseTexture?: string;
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

  constructor(opts: TerrainOpts) {
    this.size = opts.size;
    this.segments = opts.segments;
    this.heights = new Float32Array((opts.segments + 1) * (opts.segments + 1));
  }

  async build(loader: AssetLoader, opts: TerrainOpts): Promise<THREE.Mesh> {
    const geo = new THREE.PlaneGeometry(opts.size, opts.size, opts.segments, opts.segments);
    geo.rotateX(-Math.PI / 2);
    const pos = geo.attributes.position as THREE.BufferAttribute;

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
    geo.computeVertexNormals();

    const diffuse = opts.diffuseTexture
      ? await loader.loadTexture(opts.diffuseTexture, 0x4a7c3a)
      : null;
    if (diffuse) {
      diffuse.repeat.set(24, 24);
    }
    const mat = new THREE.MeshStandardMaterial({
      color: diffuse ? 0xffffff : 0x4a7c3a,
      map: diffuse ?? null,
      roughness: 0.95,
      metalness: 0.0,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.receiveShadow = true;
    this.mesh = mesh;
    return mesh;
  }

  /** World-space height lookup via bilinear sampling. */
  heightAt(x: number, z: number): number {
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
