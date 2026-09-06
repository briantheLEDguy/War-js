import * as THREE from 'three';
import { describe, expect, test, vi } from 'vitest';
import { resolveCameraCollision } from '../src/game/CameraCollision';

describe('static camera broad phase', () => {
  test('distant static geometry is cached, while moving a GM object into the sweep invalidates its bounds', () => {
    const root = new THREE.Group();
    root.userData.cameraStaticGeometry = true;
    const wall = new THREE.Mesh(new THREE.BoxGeometry(4, 4, 1), new THREE.MeshBasicMaterial());
    root.add(wall);
    root.position.set(100, 2, 5);
    const focus = new THREE.Vector3(0, 2, 0), desired = new THREE.Vector3(0, 2, 10);
    resolveCameraCollision(focus, desired, [], undefined, [root]);
    const update = vi.spyOn(wall, 'updateWorldMatrix');
    expect(resolveCameraCollision(focus, desired, [], undefined, [root]).z).toBe(10);
    expect(update).not.toHaveBeenCalled();
    root.position.x = 0;
    expect(resolveCameraCollision(focus, desired, [], undefined, [root]).z).toBeLessThan(5);
    expect(update).toHaveBeenCalled();
  });
  test('animated children remain live when their parent has not moved', () => {
    const root = new THREE.Group();
    const wall = new THREE.Mesh(new THREE.BoxGeometry(4, 4, 1), new THREE.MeshBasicMaterial());
    root.add(wall);
    wall.position.set(100, 2, 5);
    const focus = new THREE.Vector3(0, 2, 0), desired = new THREE.Vector3(0, 2, 10);
    expect(resolveCameraCollision(focus, desired, [], undefined, [root]).z).toBe(10);
    wall.position.x = 0;
    expect(resolveCameraCollision(focus, desired, [], undefined, [root]).z).toBeLessThan(5);
  });
  test('benchmark a dense city camera sweep with and without cached static bounds', () => {
    const geometry = new THREE.BoxGeometry(2, 4, 2), material = new THREE.MeshBasicMaterial();
    const roots = Array.from({ length: 1200 }, (_, i) => {
      const root = new THREE.Group();
      root.position.set(30 + (i % 40) * 5, 0, 30 + Math.floor(i / 40) * 5);
      for (let j = 0; j < 8; j++) { const mesh = new THREE.Mesh(geometry, material); mesh.position.y = j * 3; root.add(mesh); }
      return root;
    });
    const focus = new THREE.Vector3(0, 2, 0), desired = new THREE.Vector3(0, 3, 12);
    const run = () => {
      const start = performance.now();
      for (let i = 0; i < 40; i++) resolveCameraCollision(focus, desired, [], undefined, roots);
      return (performance.now() - start) / 40;
    };
    run();
    const uncached = run();
    roots.forEach(root => { root.userData.cameraStaticGeometry = true; });
    run();
    const cached = run();
    console.log(`Camera sweep, 1,200 scenery roots / 9,600 meshes: ${uncached.toFixed(2)} ms uncached, ${cached.toFixed(2)} ms cached (CPU fixture, not game FPS).`);
    geometry.dispose(); material.dispose();
  });
});
