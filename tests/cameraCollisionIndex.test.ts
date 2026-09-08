import * as THREE from 'three';
import { describe, expect, test, vi } from 'vitest';
import { CameraCollisionIndex } from '../src/game/CameraCollisionIndex';
import { resolveCameraCollision } from '../src/game/CameraCollision';

describe('camera spatial index', () => {
  test('indexed sweep matches original padding, terrain and inside-out surface probes', () => {
    const wall = new THREE.Mesh(new THREE.BoxGeometry(8, 8, 1, 12, 12, 4), new THREE.MeshBasicMaterial());
    wall.position.set(1, 3, -4); wall.rotation.y = .3; wall.scale.set(1.4, .8, 1);
    wall.userData.cameraStaticGeometry = true;
    const original = wall.clone(); original.geometry = wall.geometry.clone();
    const index = new CameraCollisionIndex(); index.rebuild([wall]);
    for (const x of [-6, -2, 0, 2, 6]) for (const reverse of [false, true]) {
      const focus = new THREE.Vector3(x, 3, reverse ? -10 : 2);
      const desired = new THREE.Vector3(x + .5, 1, reverse ? 2 : -10);
      const expected = resolveCameraCollision(focus, desired, [], () => .2, [original]);
      const actual = resolveCameraCollision(focus, desired, [], () => .2, { index, dynamic: [] });
      expect(actual.distanceTo(expected)).toBeLessThan(1e-7);
    }
    index.dispose(); wall.geometry.dispose(); original.geometry.dispose();
  });
  test('steady queries skip distant geometry and rebuild after an editor revision', () => {
    const roots = Array.from({ length: 1200 }, (_, index) => {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(2, 4, 2), new THREE.MeshBasicMaterial());
      mesh.position.set(50 + index * 3, 0, 0);
      mesh.userData.cameraStaticGeometry = true;
      return mesh;
    });
    const index = new CameraCollisionIndex();
    index.rebuild(roots);
    const updates = roots.map(mesh => vi.spyOn(mesh, 'updateWorldMatrix'));
    const query = new THREE.Box3(new THREE.Vector3(-2, -2, -2), new THREE.Vector3(2, 2, 2));
    const result: THREE.Mesh[] = [];
    index.query(query, result);
    expect(result).toHaveLength(0);
    updates.forEach(update => expect(update).not.toHaveBeenCalled());
    roots[0].position.x = 0;
    index.rebuild(roots);
    index.query(query, result);
    expect(result).toEqual([roots[0]]);
    index.rebuild(roots.slice(1));
    index.query(query, result);
    expect(result).toHaveLength(0);
    index.dispose();
    roots.forEach(mesh => { mesh.geometry.dispose(); (mesh.material as THREE.Material).dispose(); });
  });

  test('dynamic children move without a static index rebuild; hidden LOD sources remain queryable', () => {
    const gate = new THREE.Group();
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial());
    gate.add(mesh);
    mesh.position.x = 20;
    const lod = new THREE.LOD();
    const near = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial());
    lod.addLevel(near, 0); lod.addLevel(near.clone(), 10);
    lod.userData.cameraStaticGeometry = true;
    lod.visible = false; near.visible = false;
    const index = new CameraCollisionIndex();
    index.rebuild([gate, lod]);
    const result: THREE.Mesh[] = [];
    const query = new THREE.Box3(new THREE.Vector3(-2, -2, -2), new THREE.Vector3(2, 2, 2));
    index.query(query, result);
    expect(result).toEqual([near]);
    mesh.position.x = 0;
    index.query(query, result);
    expect(result).toEqual([near, mesh]);
  });

  test('BVH construction preserves render indices and accelerated raycast results at nonuniform scale', () => {
    const geometry = new THREE.SphereGeometry(3, 32, 24);
    const material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide });
    const original = new THREE.Mesh(geometry.clone(), material);
    const accelerated = new THREE.Mesh(geometry, material);
    for (const mesh of [original, accelerated]) {
      mesh.position.set(2, 1, -4); mesh.scale.set(2, .5, 1.3); mesh.rotation.y = .8;
      mesh.updateMatrixWorld(true);
    }
    accelerated.userData.cameraStaticGeometry = true;
    const indices = Array.from(geometry.index!.array);
    const index = new CameraCollisionIndex(); index.rebuild([accelerated]);
    expect(Array.from(geometry.index!.array)).toEqual(indices);
    for (const reverse of [false, true]) {
      const ray = new THREE.Raycaster(new THREE.Vector3(2, 1, reverse ? -20 : 20), new THREE.Vector3(0, 0, reverse ? 1 : -1), 0, 40);
      const expected = ray.intersectObject(original).map(hit => hit.distance).sort((a, b) => a - b);
      const actual = ray.intersectObject(accelerated).map(hit => hit.distance).sort((a, b) => a - b);
      expect(actual.length).toBe(expected.length);
      actual.forEach((distance, i) => expect(distance).toBeCloseTo(expected[i], 8));
    }
    geometry.dispose();
    expect(geometry.boundsTree).toBeUndefined();
  });
});
