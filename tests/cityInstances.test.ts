import * as THREE from 'three';
import { describe, expect, test, vi } from 'vitest';
import { CityInstances } from '../src/world/CityInstances';
import type { SpawnedStaticWorldObject } from '../src/world/Props';
describe('city instance rendering', () => {
  test('membership changes upload only affected batches and retain all shared members', () => {
    const scene = new THREE.Scene();
    const common = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial());
    common.position.z = -10;
    const roots = [common, common.clone(), new THREE.Mesh(new THREE.SphereGeometry(), new THREE.MeshStandardMaterial())];
    roots[2].position.z = -10;
    roots.forEach(root => scene.add(root));
    const instances = new CityInstances(scene, roots.map((object, i) => ({ id: `prop-${i}`, object,
      definition: { kind: 'aegis_wall' } })) as SpawnedStaticWorldObject[]);
    const camera = new THREE.PerspectiveCamera(60, 1, .1, 100);
    instances.update(camera, true, () => false);
    const batches = scene.children.filter(child => child instanceof THREE.InstancedMesh);
    const shared = batches.find(batch => batch.geometry === common.geometry)!;
    const unchanged = batches.find(batch => batch.geometry === roots[2].geometry)!;
    const sharedVersion = shared.instanceMatrix.version;
    const otherVersion = unchanged.instanceMatrix.version;
    instances.update(camera, true, id => id === 'prop-0');
    expect(shared.count).toBe(1);
    expect(shared.instanceMatrix.version).toBeGreaterThan(sharedVersion);
    expect(unchanged.count).toBe(1);
    expect(unchanged.instanceMatrix.version).toBe(otherVersion);
    instances.dispose();
  });

  test('small movements around an LOD boundary do not repeatedly swap geometry', () => {
    const scene = new THREE.Scene();
    const root = new THREE.LOD();
    root.addLevel(new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial()), 0);
    root.addLevel(new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial()), 55);
    scene.add(root);
    const instances = new CityInstances(scene, [{ id: 'house', object: root,
      definition: { kind: 'aegis_house_1' } }] as SpawnedStaticWorldObject[]);
    const camera = new THREE.PerspectiveCamera(60, 1, .1, 200);
    camera.position.z = 54;
    instances.update(camera, true, () => false);
    const batches = scene.children.filter(child => child instanceof THREE.InstancedMesh);
    const version = batches[0].instanceMatrix.version;
    for (const z of [56, 54, 57, 54, 60]) {
      camera.position.z = z;
      instances.update(camera, true, () => false);
    }
    expect(batches[0].instanceMatrix.version).toBe(version);
    camera.position.z = 63;
    instances.update(camera, true, () => false);
    expect(batches[1].count).toBe(1);
    camera.position.z = 54;
    instances.update(camera, true, () => false);
    expect(batches[1].count).toBe(1);
    camera.position.z = 47;
    instances.update(camera, true, () => false);
    expect(batches[0].count).toBe(1);
    instances.dispose();
  });

  test('culls off-screen instances but retains shadow casters, and restores authoring roots for GM mode', () => {
    const scene = new THREE.Scene();
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial());
    mesh.castShadow = true;
    const roots = [mesh, mesh.clone(), mesh.clone()];
    roots[0].position.set(0, 0, -20);
    roots[1].position.set(0, 0, 20);
    roots[2].position.set(30, 0, 20);
    roots.forEach(root => scene.add(root));
    const sun = new THREE.DirectionalLight();
    sun.castShadow = true;
    sun.position.set(30, 30, 20);
    sun.target.position.set(30, 0, 20);
    const lightRig = new THREE.Group(); lightRig.add(sun, sun.target); scene.add(lightRig);
    const entries = roots.map((object, i) => ({ id: `prop-${i}`, object, definition: { kind: 'aegis_wall' } })) as SpawnedStaticWorldObject[];
    const instances = new CityInstances(scene, entries);
    const camera = new THREE.PerspectiveCamera(60, 1, .1, 200);
    instances.update(camera, true, () => false);
    const batch = scene.children.find(child => child instanceof THREE.InstancedMesh) as THREE.InstancedMesh;
    expect(batch.count).toBe(2);
    expect(roots.every(root => root.parent === null)).toBe(true);
    const updates = roots.map(root => vi.spyOn(root, 'updateMatrixWorld'));
    scene.updateMatrixWorld();
    updates.forEach(update => expect(update).not.toHaveBeenCalled());
    camera.rotation.y = Math.PI;
    instances.update(camera, true, () => false);
    expect(batch.count).toBe(2);
    const matrix = new THREE.Matrix4(); batch.getMatrixAt(0, matrix);
    expect(new THREE.Vector3().setFromMatrixPosition(matrix).z).toBe(20);
    instances.update(camera, false, () => false);
    expect(roots.every(root => root.parent === scene && root.visible)).toBe(true);
    instances.update(camera, true, () => false);
    instances.dispose();
    expect(roots.every(root => root.parent === scene && root.visible)).toBe(true);
  });
  test('stationary frames reuse instance buffers and bounds; LOD and suppression changes rebuild them', () => {
    const scene = new THREE.Scene();
    const root = new THREE.LOD();
    root.addLevel(new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial()), 0);
    root.addLevel(new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial()), 55);
    scene.add(root);
    const instances = new CityInstances(scene, [{ id: 'house', object: root, definition: { kind: 'aegis_house_1' } }] as SpawnedStaticWorldObject[]);
    const camera = new THREE.PerspectiveCamera();
    instances.update(camera, true, () => false);
    const batches = scene.children.filter(child => child instanceof THREE.InstancedMesh);
    const spies = batches.map(batch => vi.spyOn(batch, 'computeBoundingSphere'));
    const versions = batches.map(batch => batch.instanceMatrix.version);
    for (let i = 0; i < 60; i++) instances.update(camera, true, () => false);
    expect(batches.map(batch => batch.instanceMatrix.version)).toEqual(versions);
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
    camera.position.z = 80;
    instances.update(camera, true, () => false);
    expect(batches[0].count).toBe(0);
    expect(batches[0].visible).toBe(false);
    expect(batches[1].count).toBe(1);
    expect(batches[1].visible).toBe(true);
    instances.update(camera, true, () => true);
    expect(batches.every(batch => batch.count === 0)).toBe(true);
    expect(batches.every(batch => !batch.visible)).toBe(true);
    instances.dispose();
  });
  test('allocates only actual occurrences, including repeated parts inside one object', () => {
    const scene = new THREE.Scene();
    const common = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial());
    const roots = Array.from({ length: 20 }, () => new THREE.Group());
    for (const root of roots) {
      root.add(common.clone());
      scene.add(root);
    }
    const rare = new THREE.Mesh(new THREE.SphereGeometry(), new THREE.MeshStandardMaterial());
    roots[0].add(rare, rare.clone(), rare.clone());
    const entries = roots.map((object, i) => ({ id: `prop-${i}`, object,
      definition: { kind: 'aegis_house_1' } })) as SpawnedStaticWorldObject[];
    const instances = new CityInstances(scene, entries);
    instances.update(new THREE.PerspectiveCamera(), true, () => false);
    const batches = scene.children.filter(child => child instanceof THREE.InstancedMesh);
    const rareBatch = batches.find(batch => batch.geometry === rare.geometry)!;
    const commonBatch = batches.find(batch => batch.geometry === common.geometry)!;
    expect(rareBatch.instanceMatrix.count).toBe(3);
    expect(rareBatch.count).toBe(3);
    expect(commonBatch.instanceMatrix.count).toBe(20);
    instances.dispose();
  });

  test('shares draws, suppresses overrides and respects transforms after GM editing', () => {
    const scene = new THREE.Scene();
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial());
    const roots = [mesh, mesh.clone()];
    roots.forEach(root => scene.add(root));
    const entries = roots.map((object, i) => ({ id: `house-${i}`, object,
      definition: { kind: 'aegis_house_1' } })) as SpawnedStaticWorldObject[];
    const instances = new CityInstances(scene, entries);
    const camera = new THREE.PerspectiveCamera();
    instances.update(camera, true, () => false);
    const batch = scene.children.find(child => child instanceof THREE.InstancedMesh) as THREE.InstancedMesh;
    expect(batch.count).toBe(2);
    expect(roots.every(root => !root.visible)).toBe(true);
    instances.update(camera, false, id => id === 'house-1');
    expect(roots[0].visible).toBe(true);
    expect(roots[1].visible).toBe(false);
    roots[0].position.x = 17;
    camera.position.set(17, 0, 5);
    instances.update(camera, true, id => id === 'house-1');
    expect(batch.count).toBe(1);
    const matrix = new THREE.Matrix4();
    batch.getMatrixAt(0, matrix);
    expect(new THREE.Vector3().setFromMatrixPosition(matrix).x).toBe(17);
    instances.dispose();
    expect(scene.children).toHaveLength(2);
  });
});
