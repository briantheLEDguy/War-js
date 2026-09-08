import { afterEach, expect, test, vi } from 'vitest';
import * as THREE from 'three';
import { StaticPropInstances } from '../src/game/StaticPropInstances';

afterEach(() => vi.restoreAllMocks());
function template() {
  const geometry = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0, 0, 2, 0], 3));
  return new THREE.Mesh(geometry, new THREE.MeshStandardMaterial());
}
function batchesIn(root: THREE.Object3D): THREE.InstancedMesh[] {
  return root.children.filter(child => (child as THREE.InstancedMesh).isInstancedMesh) as THREE.InstancedMesh[];
}

test('500 repeated nature placements use one batch and retain nested transforms in a translated chunk', () => {
  const container = new THREE.Group(); container.position.set(100, 3, -40); container.rotation.y = .6;
  const leaf = template(); leaf.position.set(.5, 2, 0); leaf.castShadow = true; leaf.receiveShadow = true;
  const roots = Array.from({ length: 500 }, (_, index) => {
    const root = new THREE.Group(); root.position.set(index % 25, index / 500, Math.floor(index / 25));
    root.rotation.y = index / 10; root.scale.set(1, 1.2, .9); root.add(leaf.clone()); container.add(root); return root;
  });
  container.updateMatrixWorld(true);
  const expected = container.matrixWorld.clone().invert().multiply(roots[87].children[0].matrixWorld);
  const instances = new StaticPropInstances(container); instances.update(roots);
  const batches = batchesIn(container);
  expect(batches).toHaveLength(1); expect(batches[0].count).toBe(500);
  expect(roots.every(root => !root.visible)).toBe(true);
  const actual = new THREE.Matrix4(); batches[0].getMatrixAt(87, actual);
  actual.elements.forEach((value, index) => expect(value).toBeCloseTo(expected.elements[index], 5));
  expect(batches[0].castShadow).toBe(true); expect(batches[0].receiveShadow).toBe(true);
  expect(batches[0].geometry).toBe(leaf.geometry); expect(batches[0].material).toBe(leaf.material);
  expect(batches[0].boundingSphere!.radius).toBeGreaterThan(10);
  const version = batches[0].instanceMatrix.version;
  instances.update(roots);
  expect(batchesIn(container)[0]).toBe(batches[0]);
  expect(batches[0].instanceMatrix.version).toBe(version);
  instances.dispose(); leaf.geometry.dispose(); (leaf.material as THREE.Material).dispose();
});

test('only active LOD parts are batched and switching releases the previous instance buffer', () => {
  const container = new THREE.Group(), root = new THREE.Group(); container.add(root);
  const near = template(), far = template(); root.add(near, far); far.visible = false;
  const instances = new StaticPropInstances(container); instances.update([root]);
  const old = batchesIn(container)[0]; const disposed = vi.spyOn(old, 'dispose');
  near.visible = false; far.visible = true; instances.update([root]);
  expect(disposed).toHaveBeenCalledOnce();
  expect(batchesIn(container)).toHaveLength(1);
  expect(batchesIn(container)[0].geometry).toBe(far.geometry);
  instances.dispose();
  expect(root.visible).toBe(true); expect(near.visible).toBe(false); expect(far.visible).toBe(true);
});

test('keeps animated, mirrored, transparent, hidden and mixed light-bearing props in their original render paths', () => {
  const container = new THREE.Group();
  const skin = new THREE.SkinnedMesh(template().geometry, new THREE.MeshStandardMaterial());
  const mirrored = template(); mirrored.scale.x = -1;
  const transparent = template(); (transparent.material as THREE.Material).transparent = true;
  const hidden = template(); hidden.visible = false;
  const lit = new THREE.Group(); lit.add(template(), new THREE.PointLight());
  const morph = template(); morph.morphTargetInfluences = [0];
  const roots = [skin, mirrored, transparent, hidden, lit, morph]; container.add(...roots);
  const instances = new StaticPropInstances(container); instances.update(roots);
  expect(batchesIn(container)).toHaveLength(0);
  expect([skin, mirrored, transparent, lit, morph].every(root => root.visible)).toBe(true);
  expect(hidden.visible).toBe(false); instances.dispose();
});

test('disposing batches releases GPU instance buffers while preserving shared assets and original authoring objects', () => {
  const container = new THREE.Group(), root = new THREE.Group(), mesh = template(); root.add(mesh); container.add(root);
  const geometryDispose = vi.spyOn(mesh.geometry, 'dispose'), materialDispose = vi.spyOn(mesh.material as THREE.Material, 'dispose');
  const instances = new StaticPropInstances(container); instances.update([root]);
  const disposed = vi.spyOn(batchesIn(container)[0], 'dispose');
  instances.update([root], false);
  expect(disposed).toHaveBeenCalledOnce(); expect(root.visible).toBe(true);
  expect(geometryDispose).not.toHaveBeenCalled(); expect(materialDispose).not.toHaveBeenCalled();
  instances.dispose(); expect(root.parent).toBe(container);
});
