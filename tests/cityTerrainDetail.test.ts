import { readFileSync } from 'node:fs';
import { describe, expect, test } from 'vitest';
import * as THREE from 'three';
import type { AssetLoader } from '../src/game/AssetLoader';
import { cityHeightAt, type CityElevation } from '../src/world/CityElevation';
import { canalAt, citySurfaceGeometry, type CanalDefinition } from '../src/world/CityWater';
import { Terrain } from '../src/world/Terrain';

const size = 80;
const canal: CanalDefinition = { id: 'outer-channel', x: 22, z: 0, width: 8, depth: 12, bedY: -3, waterY: -1 };
function elevation(): CityElevation {
  const field: CityElevation = { segments: size, detailX: [-12, 12], detailZ: [-16, 16], heights: [] };
  for (let z = -size / 2; z <= size / 2; z++) for (let x = -size / 2; x <= size / 2; x++) {
    const cx = Math.max(-12, Math.min(12, x)), cz = Math.max(-16, Math.min(16, z));
    field.heights.push(cx * .15 + cz * .25 + (12 - Math.abs(cx)) * (16 - Math.abs(cz)) * .02);
  }
  return field;
}
function surface(field: CityElevation): THREE.BufferGeometry {
  return citySurfaceGeometry(size, [canal], 'ground', { ...field, heightAt: (x, z) => cityHeightAt(field, size, x, z) });
}

describe('bounded city terrain detail', () => {
  test('matches movement heights inside detailed and coarse terrain triangles', () => {
    const field = elevation(), geometry = surface(field);
    const positions = geometry.getAttribute('position'), indices = geometry.getIndex()!;
    let coarseSamples = 0, detailedSamples = 0;
    for (let i = 0; i < indices.count; i += 3) {
      const vertices = [0, 1, 2].map(j => new THREE.Vector3().fromBufferAttribute(positions, indices.getX(i + j)));
      for (const weights of [[.2, .3, .5], [.6, .3, .1], [.1, .7, .2]]) {
        const point = vertices.reduce((sum, vertex, j) => sum.addScaledVector(vertex, weights[j]), new THREE.Vector3());
        expect(point.y).toBeCloseTo(cityHeightAt(field, size, point.x, point.z), 4);
        expect(canalAt([canal], point.x, point.z)).toBeUndefined();
        if (Math.abs(point.x) > 12) coarseSamples++;
        else detailedSamples++;
      }
    }
    expect(coarseSamples).toBeGreaterThan(0);
    expect(detailedSamples).toBeGreaterThan(0);
    geometry.dispose();
  });

  test('passes detailX through the actual terrain build without changing floor heights', async () => {
    const field = elevation();
    const terrain = new Terrain({ size, segments: size });
    const mesh = await terrain.build({ loadTexture: async () => null } as unknown as AssetLoader, {
      size, segments: size, flatTerrain: true, canals: [canal], cityElevation: field,
    }) as THREE.Mesh<THREE.BufferGeometry, THREE.Material[]>;
    const reference = surface(field);
    expect(mesh.geometry.getIndex()!.count).toBe(reference.getIndex()!.count);
    for (const [x, z] of [[-35.3, -9.1], [-9.6, 5.1], [31.8, 12.4]])
      expect(terrain.heightAt(x, z)).toBe(cityHeightAt(field, size, x, z));
    mesh.geometry.dispose();
    for (const material of mesh.material) material.dispose();
    reference.dispose();
  });

  test('preserves canal openings and level water and bed geometry outside the detailed band', () => {
    const field = elevation(), geometry = surface(field);
    const ground = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial());
    ground.updateMatrixWorld(true);
    const ray = new THREE.Raycaster(new THREE.Vector3(canal.x, 30, canal.z), new THREE.Vector3(0, -1, 0));
    expect(ray.intersectObject(ground)).toHaveLength(0);
    ray.set(new THREE.Vector3(canal.x - canal.width / 2 - 1, 30, canal.z), new THREE.Vector3(0, -1, 0));
    expect(ray.intersectObject(ground).length).toBeGreaterThan(0);
    for (const kind of ['water', 'bed'] as const) {
      const channel = citySurfaceGeometry(size, [canal], kind);
      const positions = channel.getAttribute('position');
      for (let i = 0; i < positions.count; i++) expect(positions.getY(i)).toBe(kind === 'water' ? canal.waterY : canal.bedY);
      channel.dispose();
    }
    geometry.dispose();
    ground.material.dispose();
  });

  test('keeps the enlarged capital below the old terrain triangle budget', () => {
    const canals: CanalDefinition[] = JSON.parse(readFileSync('public/assets/maps/aegis_capital.json', 'utf8')).canals;
    const previous = citySurfaceGeometry(560, canals, 'ground', { segments: 560, detailZ: [24, 150], heightAt: () => 42 });
    const expanded = citySurfaceGeometry(800, canals, 'ground', { segments: 800, detailX: [-180, 180], detailZ: [24, 150], heightAt: () => 42 });
    expect(expanded.getIndex()!.count).toBeLessThan(previous.getIndex()!.count);
    expect(expanded.getIndex()!.count / 3).toBeLessThan(110_000);
    previous.dispose(); expanded.dispose();
  });

  test('retains the full x grid when legacy elevation data omits detailX', () => {
    const field = elevation();
    delete field.detailX;
    const legacy = surface(field);
    field.detailX = [-size / 2, size / 2];
    const explicit = surface(field);
    expect(Array.from(legacy.getAttribute('position').array)).toEqual(Array.from(explicit.getAttribute('position').array));
    expect(Array.from(legacy.getIndex()!.array)).toEqual(Array.from(explicit.getIndex()!.array));
    legacy.dispose(); explicit.dispose();
  });
});
