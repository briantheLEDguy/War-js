import * as THREE from 'three';
import { cityHeightAt, type CityElevation } from './CityElevation';

/** Clip road strips against ground triangles, preserving the exact ground plane.
 * Resampling a rotated ribbon on another grid cuts through convex slopes. */
export function cityRoadGeometry(field: CityElevation, size: number, x: number, z: number, rotation: number, width: number, depth: number, baseY: number, lift: number): THREE.BufferGeometry {
  const step = size / field.segments, half = size / 2;
  const cos = Math.cos(rotation), sin = Math.sin(rotation);
  const reach = Math.hypot(width, depth) / 2 + step;
  const startX = Math.max(0, Math.floor((x - reach + half) / step));
  const endX = Math.min(field.segments, Math.ceil((x + reach + half) / step));
  const startZ = Math.max(0, Math.floor((z - reach + half) / step));
  const endZ = Math.min(field.segments, Math.ceil((z + reach + half) / step));
  type Point = { x: number; y: number; z: number };
  const local = (wx: number, wz: number): Point => ({ x: (wx - x) * cos - (wz - z) * sin, z: (wx - x) * sin + (wz - z) * cos, y: cityHeightAt(field, size, wx, wz) - baseY + lift });
  const positions: number[] = [], uvs: number[] = [];
  for (let ix = startX; ix < endX; ix++) for (let iz = startZ; iz < endZ; iz++) {
    const x0 = ix * step - half, z0 = iz * step - half;
    const a = local(x0, z0), b = local(x0, z0 + step), c = local(x0 + step, z0 + step), d = local(x0 + step, z0);
    for (const triangle of [[a, b, c], [a, c, d]]) {
      let polygon = triangle;
      for (const [axis, sign, bound] of [['x', 1, width / 2], ['x', -1, width / 2], ['z', 1, depth / 2], ['z', -1, depth / 2]] as const) {
        const clipped: Point[] = [];
        for (let i = 0; i < polygon.length; i++) {
          const p = polygon[i], q = polygon[(i + 1) % polygon.length];
          const dp = p[axis] * sign - bound, dq = q[axis] * sign - bound;
          if (dp <= 0) clipped.push(p);
          if ((dp <= 0) !== (dq <= 0)) {
            const t = dp / (dp - dq);
            clipped.push({ x: p.x + (q.x - p.x) * t, y: p.y + (q.y - p.y) * t, z: p.z + (q.z - p.z) * t });
          }
        }
        polygon = clipped;
      }
      for (let i = 1; i < polygon.length - 1; i++) for (const p of [polygon[0], polygon[i], polygon[i + 1]]) {
        positions.push(p.x, p.y, p.z);
        uvs.push((x + p.x * cos + p.z * sin) / 4, (z - p.x * sin + p.z * cos) / 4);
      }
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.computeVertexNormals();
  return geometry;
}
