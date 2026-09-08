import * as THREE from 'three';

type Triangle = { a: THREE.Vector3; b: THREE.Vector3; c: THREE.Vector3; denominator: number };
const CELL_SIZE = 8;

/** Index the accepted high-detail terrain surface; visual LOD changes must not change footing. */
export class BuilderGroundSurface {
  private transform = new THREE.Matrix4().makeScale(0, 0, 0);
  private cells = new Map<string, Triangle[]>();

  constructor(private root: THREE.Object3D, private source: THREE.Object3D) {}

  heightAt(x: number, z: number, ceiling: number): number | null {
    this.root.updateWorldMatrix(true, true);
    if (!this.transform.equals(this.root.matrixWorld)) this.rebuild();
    let height: number | null = null;
    for (const { a, b, c, denominator } of this.cells.get(this.key(x, z)) ?? []) {
      const u = ((b.z - c.z) * (x - c.x) + (c.x - b.x) * (z - c.z)) / denominator;
      const v = ((c.z - a.z) * (x - c.x) + (a.x - c.x) * (z - c.z)) / denominator;
      if (u < -1e-6 || v < -1e-6 || u + v > 1 + 1e-6) continue;
      const y = u * a.y + v * b.y + (1 - u - v) * c.y;
      if (y <= ceiling && (height === null || y > height)) height = y;
    }
    return height;
  }

  private key(x: number, z: number): string { return `${Math.floor(x / CELL_SIZE)}:${Math.floor(z / CELL_SIZE)}`; }

  private rebuild(): void {
    this.transform.copy(this.root.matrixWorld);
    this.cells.clear();
    this.source.traverse(node => {
      if (!(node as THREE.Mesh).isMesh || node.userData.noGroundSupport === true) return;
      const mesh = node as THREE.Mesh, geometry = mesh.geometry, positions = geometry.getAttribute('position');
      if (!positions) return;
      const index = geometry.index;
      const count = index?.count ?? positions.count;
      for (let offset = 0; offset + 2 < count; offset += 3) {
        const points = [0, 1, 2].map(corner => new THREE.Vector3().fromBufferAttribute(positions,
          index ? index.getX(offset + corner) : offset + corner).applyMatrix4(mesh.matrixWorld));
        const [a, b, c] = points;
        const normal = b.clone().sub(a).cross(c.clone().sub(a)).normalize();
        if (normal.y < .25) continue;
        const denominator = (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z);
        if (Math.abs(denominator) < 1e-10) continue;
        const triangle = { a, b, c, denominator };
        for (let gx = Math.floor(Math.min(a.x, b.x, c.x) / CELL_SIZE); gx <= Math.floor(Math.max(a.x, b.x, c.x) / CELL_SIZE); gx++) {
          for (let gz = Math.floor(Math.min(a.z, b.z, c.z) / CELL_SIZE); gz <= Math.floor(Math.max(a.z, b.z, c.z) / CELL_SIZE); gz++) {
            const key = `${gx}:${gz}`, cell = this.cells.get(key) ?? [];
            cell.push(triangle); this.cells.set(key, cell);
          }
        }
      }
    });
  }
}
