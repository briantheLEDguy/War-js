import * as THREE from 'three';
import { expect, test } from 'vitest';
import { CharacterVisibility } from '../src/game/CharacterVisibility';

test('offscreen NPCs are hidden unless a shadow camera needs them; turning restores them', () => {
  const scene = new THREE.Scene();
  const actor = new THREE.Mesh(new THREE.BoxGeometry(1, 2, 1), new THREE.MeshBasicMaterial());
  actor.position.set(0, 0, 30); actor.frustumCulled = false;
  scene.add(actor);
  const camera = new THREE.PerspectiveCamera(60, 1, .1, 100);
  const visibility = new CharacterVisibility(scene, [actor]);
  visibility.update(camera); expect(actor.visible).toBe(false);
  camera.rotation.y = Math.PI;
  visibility.update(camera); expect(actor.visible).toBe(true);
  visibility.dispose(); expect(actor.visible).toBe(true);
  camera.rotation.y = 0;
  const light = new THREE.DirectionalLight(); light.castShadow = true;
  light.position.set(0, 10, 30); light.target.position.set(0, 0, 30);
  scene.add(light, light.target);
  const shadows = new CharacterVisibility(scene, [actor]);
  shadows.update(camera); expect(actor.visible).toBe(true);
  const frustum = new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4()
    .multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
  expect(actor.frustumCulled).toBe(true);
  expect(frustum.intersectsObject(actor)).toBe(false);
  expect(light.shadow.getFrustum().intersectsObject(actor)).toBe(true);
  shadows.dispose(); expect(actor.frustumCulled).toBe(false);
  expect(actor).not.toHaveProperty('boundingSphere');
});
