import { expect, test } from 'vitest';
import type { MeshStandardMaterial } from 'three';
import type { AssetLoader } from '../src/game/AssetLoader';
import { buildRoadSurface } from '../src/world/RoadSurface';

test('road surfaces remain renderable when texture loading returns no textures', async () => {
  const loader = { loadTexture: async () => null } as unknown as AssetLoader;
  const mesh = await buildRoadSurface([{ id: 'road', style: 'dirt_trail', width: 4, points: [{ x: 0, z: 0 }, { x: 10, z: 0 }] }], () => 0, loader);
  const material = mesh.material as MeshStandardMaterial;
  expect(material.map).toBeNull();
  expect(material.normalMap).toBeNull();
  expect(mesh.geometry.getAttribute('position').count).toBeGreaterThan(0);
  mesh.geometry.dispose(); material.dispose();
});
