import * as THREE from 'three';
export interface CanalDefinition {
  id: string;
  x: number;
  z: number;
  width: number;
  depth: number;
  bedY: number;
  waterY: number;
}
export function canalAt(canals: CanalDefinition[], x: number, z: number): CanalDefinition | undefined {
  return canals.find(c => Math.abs(x - c.x) < c.width / 2 && Math.abs(z - c.z) < c.depth / 2);
}
/** Partition at channel boundaries so ground and water meet exactly, without overlapping water planes. */
export function citySurfaceGeometry(size: number, canals: CanalDefinition[], surface: 'ground' | 'water' | 'bed', elevation?: { segments: number; detailX?: [number, number]; detailZ?: [number, number]; heightAt: (x: number, z: number) => number }): THREE.BufferGeometry {
  const half = size / 2;
  const grid = elevation ? Array.from({ length: elevation.segments + 1 }, (_, i) => -half + size * i / elevation.segments) : [];
  const xGrid = elevation?.detailX ? grid.filter(x => x >= elevation.detailX![0] && x <= elevation.detailX![1]) : grid;
  const xs = [...new Set([-half, half, ...xGrid, ...canals.flatMap(c => [c.x - c.width / 2, c.x + c.width / 2])])].sort((a, b) => a - b);
  const zGrid = elevation?.detailZ ? grid.filter(z => z >= elevation.detailZ![0] && z <= elevation.detailZ![1]) : grid;
  const zs = [...new Set([-half, half, ...zGrid, ...canals.flatMap(c => [c.z - c.depth / 2, c.z + c.depth / 2])])].sort((a, b) => a - b);
  const positions: number[] = [], uv: number[] = [], indices: number[] = [];
  for (let i = 1; i < xs.length; i++)
    for (let j = 1; j < zs.length; j++) {
      const x0 = xs[i - 1], x1 = xs[i], z0 = zs[j - 1], z1 = zs[j];
      const canal = canalAt(canals, (x0 + x1) / 2, (z0 + z1) / 2);
      if ((surface === 'ground') === Boolean(canal))
        continue;
      const y = surface === 'ground' ? 0 : surface === 'water' ? canal!.waterY : canal!.bedY;
      const n = positions.length / 3;
      const h = (x: number, z: number) => surface === 'ground' && elevation ? elevation.heightAt(x, z) : y;
      positions.push(x0, h(x0, z0), z0, x0, h(x0, z1), z1, x1, h(x1, z1), z1, x1, h(x1, z0), z0);
      uv.push((x0 + half) / size, (z0 + half) / size, (x0 + half) / size, (z1 + half) / size, (x1 + half) / size, (z1 + half) / size, (x1 + half) / size, (z0 + half) / size);
      indices.push(n, n + 1, n + 2, n, n + 2, n + 3);
    }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}
export function createCanalWater(size: number, canals: CanalDefinition[]): THREE.Group {
  const group = new THREE.Group();
  group.name = 'city-canals';
  const water = new THREE.Mesh(citySurfaceGeometry(size, canals, 'water'), new THREE.MeshStandardMaterial({
    color: 0x234344, roughness: .28, metalness: .28, transparent: true, opacity: .9,
  }));
  water.receiveShadow = true;
  group.add(water);
  group.add(new THREE.Mesh(citySurfaceGeometry(size, canals, 'bed'), new THREE.MeshStandardMaterial({ color: 0x242b26, roughness: 1 })));
  return group;
}
